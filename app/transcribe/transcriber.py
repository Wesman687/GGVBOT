import asyncio
from app.irc.irc_bot import send_irc_message
from app.transcribe.event_handler import check_event_trigger, handle_announce_event, handle_cancel_event, handle_start_event
from app.transcribe.intent import detect_high_level_intent
from app.transcribe.other_handlers import handle_ocean_boss, retry_ocean_boss
from app.transcribe.panic_handlers import handle_active_panic, handle_stop_panic, resolve_and_handle_coord_panic, resolve_and_handle_dungeon_panic
from app.transcribe.whisper_modal import transcribe_audio_buffer
from app.utils.helpers import normalize_transcript
from app.websocket import pop_audio_buffer, send_speak_command, user_buffers
from app.state import user_context



async def transcribe_and_check_command(audio_bytes, user, fallback_intent=None, retry_data=None):
    print(f"[Transcribe] 🔝 Transcribing {user} ({len(audio_bytes)} bytes)...")
    raw_text = await transcribe_audio_buffer(audio_bytes)
    text = normalize_transcript(raw_text)
    print(f"[Transcribe] {user} ⏺ '{text}'")
    if not text:
        return None, "silent"

    if not fallback_intent and "jarvis" not in text.lower():
        return None, "silent"

    user_context[user]["last_transcription"] = text
    user_context[user]["last_active"] = asyncio.get_event_loop().time()

    # 🛠️ Handle ongoing panic updates BEFORE intent classification
    panic_type = user_context[user].get("panic_type")
    if panic_type:
        return await handle_active_panic(user, text)

    # 🔁 Retry mode continuation
    if fallback_intent:
        print(f"🔁 [Retry Mode] Handling fallback for intent: {fallback_intent}")
        if fallback_intent == "coord_panic":
            return await resolve_and_handle_coord_panic(user, text, None, None), "silent"
        elif fallback_intent == "dungeon_panic":
            return await resolve_and_handle_dungeon_panic(user, text, None, None), "silent"
        elif fallback_intent == "ocean_boss":
            return await retry_ocean_boss(user, text)

    # 🔍 Detect intent
    result = await detect_high_level_intent(text)
    intent = result.get("intent")
    coords = result.get("coords")
    direction = result.get("direction")
    dungeon = result.get("dungeon")
    level = result.get("level")

    user_context[user]["last_intent"] = intent
    
    if intent == "announce_event":
        return await handle_announce_event(text, user)

    if intent == "cancel_event":
        return await handle_cancel_event(user)

    if intent == "start_event":
        return await handle_start_event(user)

    if intent == "stop_panic":
        return await handle_stop_panic(user), "responded"

    if intent == "coord_panic":
        if coords:
            return await resolve_and_handle_coord_panic(user, text, coords, direction), "silent"
        else:
            await send_speak_command(user, "Repeat the coordinates?")
            return False, "responded"
        
    if intent == "ocean_boss":
        if coords:
            return await handle_ocean_boss(user, text), "silent"
        else:
            await send_speak_command(user, "Where is the Ocean Boss?")
            return False, "responded"
        
    if intent == "red_alert":
        if dungeon and level:
            label = f"{dungeon.title()} level {level}"
            await send_irc_message(f"🚨 RED ALERT from {user} in {label}!")
        else:
            await send_irc_message(f"🚨 RED ALERT from {user}! Dungeon unclear.")
        return True, "silent"  # 🚫 Do NOT run dungeon panic

    if intent in ["dungeon_panic"]:
        return await resolve_and_handle_dungeon_panic(user, text, dungeon, level), "silent"

    if intent == "greet":
        await send_speak_command(user, "Hi, I'm Jarvis. How may I help you?")
        return True, "responded"

    print(f"🗑️ No actionable intent detected from {user}. Full result: {result}")
    return False, "silent"

HOLD_BUFFER_TIME = 2.5

def clear_retry_state(user_id, retry_state, jarvis_watch, jarvis_hold_until):
    retry_state.pop(user_id, None)
    jarvis_watch[user_id] = asyncio.get_event_loop().time()  # ← prime it immediately
    jarvis_hold_until[user_id] = jarvis_watch[user_id] + HOLD_BUFFER_TIME

def should_finalize_buffer(user_id, now, jarvis_watch, jarvis_timeout, jarvis_hold_until, buffer):
    # If we're still within hold window, don't finalize
    if user_id in jarvis_hold_until and now < jarvis_hold_until[user_id]:
        return False

    # Finalize only if buffer has enough speech *after* hold
    return (
        len(buffer) > 160000 and (  # ~2s of audio after wake word
        user_id not in jarvis_watch or
        (user_id in jarvis_watch and now - jarvis_watch[user_id] > jarvis_timeout)
    ))

def should_wait_for_retry(user_id, now, retry_state):
    retry = retry_state.get(user_id)
    return retry and now < retry.get("next_retry", 0)

async def handle_transcription(user_id, buffer, fallback_intent):
    print(f"🔁 Finalizing buffer for {user_id}{' (retry mode)' if fallback_intent else ''}...")
    success, speech_status = await transcribe_and_check_command(
        bytes(buffer), user_id, fallback_intent=fallback_intent
    )
    return success, speech_status

async def handle_retry_logic(user_id, now, success, speech_status, retry_state, jarvis_watch, jarvis_hold_until):
    retry = retry_state.get(user_id)
    delay = 6 if speech_status == "responded" else 2

    if success is None:
        print(f"🔇 No wake word or no clarification. Skipping retry for {user_id}.")
        clear_retry_state(user_id, retry_state, jarvis_watch, jarvis_hold_until)
    elif success:
        print(f"✅ {user_id} fulfilled, clearing retry state.")
        clear_retry_state(user_id, retry_state, jarvis_watch, jarvis_hold_until)
    elif not retry:
        print(f"🔁 Starting retry mode for {user_id}")
        retry_state[user_id] = {
            "attempts": 1,
            "started_at": now,
            "next_retry": now + delay,
            "intent": user_context[user_id].get("last_intent")
        }
    else:
        elapsed = now - retry["started_at"]
        if retry["attempts"] >= 2 or elapsed > 30:
            print(f"❌ Retry limit or timeout for {user_id}.")
            clear_retry_state(user_id, retry_state, jarvis_watch, jarvis_hold_until)
        else:
            retry["attempts"] += 1
            retry["next_retry"] = now + delay
            print(f"🕓 Waiting for retry {retry['attempts']} from {user_id} in {delay:.1f}s")

async def monitor_silence():
    retry_state = {}
    jarvis_watch = {}
    jarvis_hold_until = {}
    processing_users = set()
    jarvis_timeout = 4.0

    while True:
        now = asyncio.get_event_loop().time()
        await check_event_trigger()
        for user_id in list(user_buffers.keys()):
            if user_id in processing_users:
                continue
            processing_users.add(user_id)

            buffer = user_buffers.get(user_id, b"")
            if len(buffer) < 96000:
                processing_users.discard(user_id)
                continue

            # 🔍 Check for "Jarvis"
            if len(buffer) >= 144000:
                preview = await transcribe_audio_buffer(buffer[-144000:])
                if "jarvis" in preview.lower():
                    print(f"👁️ Heard 'Jarvis' early from {user_id}, extending buffer...")
                    jarvis_watch[user_id] = now
                    jarvis_hold_until[user_id] = now + HOLD_BUFFER_TIME
                    retry_state.pop(user_id, None)

            if should_wait_for_retry(user_id, now, retry_state):
                processing_users.discard(user_id)
                continue

            # 🔒 Ensure we don't process users without a wake word or retry
            if user_id not in jarvis_watch and user_id not in retry_state:
                processing_users.discard(user_id)
                continue

            if should_finalize_buffer(user_id, now, jarvis_watch, jarvis_timeout, jarvis_hold_until, buffer):
                buffer = pop_audio_buffer(user_id)
                if buffer:
                    fallback_intent = retry_state.get(user_id, {}).get("intent")
                    success, speech_status = await handle_transcription(user_id, buffer, fallback_intent)
                    await handle_retry_logic(user_id, now, success, speech_status, retry_state, jarvis_watch, jarvis_hold_until)

            processing_users.discard(user_id)

        await asyncio.sleep(1)


async def start_transcriber_loop():
    asyncio.create_task(monitor_silence())
