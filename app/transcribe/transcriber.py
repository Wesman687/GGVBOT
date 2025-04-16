import asyncio
import re
from app.irc.irc_bot import send_irc_message, stop_panic, update_coord_panic, update_dungeon_panic
from app.transcribe.intent import detect_high_level_intent
from app.transcribe.whisper_modal import transcribe_audio_buffer
from app.utils.coords import validate_coords
from app.utils.helpers import normalize_transcript
from app.websocket import pop_audio_buffer, send_speak_command, user_buffers, last_spoke
from app.state import user_context



async def transcribe_and_check_command(audio_bytes, user) -> bool:
    print(f"[Transcribe] 🧐 Transcribing {user} ({len(audio_bytes)} bytes)...")
    raw_text = await transcribe_audio_buffer(audio_bytes)
    text = normalize_transcript(raw_text)
    print(f"[Transcribe] {user} ⏺️ '{text}'")

    if not text or "jarvis" not in text.lower():
        return False

    user_context[user]["last_transcription"] = text
    user_context[user]["last_active"] = asyncio.get_event_loop().time()

    # 🔍 Detect intent via rules + LLM fallback
    result = await detect_high_level_intent(text)

    intent = result.get("intent")
    coords = result.get("coords")
    direction = result.get("direction")
    dungeon = result.get("dungeon")
    level = result.get("level")

    user_context[user]["last_intent"] = intent

    # 🛑 Stop panic
    if intent == "stop_panic":
        if user_context[user].get("panic_type") in ["coords", "dungeon"]:
            print(f"✅ Stopping panic for {user}")
            await stop_panic(user)
            user_context[user].pop("panic_coords", None)
            user_context[user].pop("panic_dungeon", None)
            user_context[user].pop("panic_type", None)
        else:
            print(f"⚠️ {user} tried to stop panic, but none was active.")
        return True

    # 📍 Coordinate panic
    if intent == "coord_panic":
        if coords and validate_coords(coords):
            await update_coord_panic(user, coords, direction)
            return True
        else:
            await send_speak_command(user, "Repeat the coordinates?")
            return False

    # 🏰 Dungeon panic
    elif intent in ["dungeon_panic", "red_alert"]:
        if dungeon and level:
            label = f"{dungeon.title()} level {level}"
            if intent == "red_alert":
                await send_irc_message(f"🚨 RED ALERT from {user} in {label}!")
            await update_dungeon_panic(user, label)
            return True
        else:
            await send_speak_command(user, "What dungeon and level?")
            return False

    # 👋 Greeting
    if intent == "greet":
        await send_speak_command(user, "Hi, I'm Jarvis. How may I help you?")
        return True

    # 🗑️ Unrecognized
    print(f"🗑️ No actionable intent detected from {user}. Full result: {result}")
    return False

            
retry_attempts = {}
pending_intent = {}

async def monitor_silence():
    jarvis_watch = {}
    jarvis_timeout = 4.0

    while True:
        now = asyncio.get_event_loop().time()

        for user_id in list(user_buffers.keys()):
            last_time = last_spoke.get(user_id, 0)
            buffer = user_buffers.get(user_id, b"")

            # Mid-buffer "Jarvis" check
            if len(buffer) >= 144000 and user_id not in jarvis_watch:
                preview = await transcribe_audio_buffer(buffer[-144000:])
                if "jarvis" in preview.lower():
                    print(f"👁️ Heard 'Jarvis' early from {user_id}, extending buffer...")
                    jarvis_watch[user_id] = now

            # Retry loop or finalize normal buffer
            should_finalize = (now - last_time > 2.0 and user_id not in jarvis_watch)
            should_finalize_jarvis = (user_id in jarvis_watch and now - jarvis_watch[user_id] > jarvis_timeout)

            if should_finalize or should_finalize_jarvis:
                buffer = pop_audio_buffer(user_id)
                if buffer:
                    print(f"🔁 Finalizing buffer for {user_id} (retry={retry_attempts.get(user_id, 0)})...")
                    success = await transcribe_and_check_command(bytes(buffer), user_id)

                    if not success:
                        retry_attempts[user_id] = retry_attempts.get(user_id, 0) + 1
                        if retry_attempts[user_id] < 2:
                            print(f"🕓 Waiting for more input from {user_id} (retry {retry_attempts[user_id]})")
                            pending_intent[user_id] = True
                        else:
                            print(f"❌ Max retries reached for {user_id}. Clearing retry state.")
                            retry_attempts.pop(user_id, None)
                            pending_intent.pop(user_id, None)
                    else:
                        retry_attempts.pop(user_id, None)
                        pending_intent.pop(user_id, None)

                jarvis_watch.pop(user_id, None)

        await asyncio.sleep(1)

async def start_transcriber_loop():
    asyncio.create_task(monitor_silence())
