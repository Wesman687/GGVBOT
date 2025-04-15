import asyncio
from app.transcribe.whisper_modal import transcribe_audio_buffer
from websocket import pop_audio_buffer, send_speak_command, user_buffers, last_spoke

async def transcribe_and_check_command(audio_bytes, user):
    print(f"[Transcribe] 🧠 Transcribing {user} ({len(audio_bytes)} bytes)...")
    text = await transcribe_audio_buffer(audio_bytes)
    print(f"[Transcribe] {user} ⏺️ '{text}'")

    if "jarvis" in text.lower():
        await send_speak_command(user, "Hi, I'm Jarvis. How may I help you?")
    else:
        print("🗑️ Ignored (no wake word)")

async def monitor_silence():
    while True:
        now = asyncio.get_event_loop().time()
        for user_id in list(user_buffers.keys()):
            last_time = last_spoke.get(user_id, 0)
            if now - last_time > 4.0:
                buffer = pop_audio_buffer(user_id)
                if buffer:
                    print(f"⏳ Finalizing {user_id}'s chunk...")
                    await transcribe_and_check_command(bytes(buffer), user_id)
        await asyncio.sleep(1)

async def start_transcriber_loop():
    asyncio.create_task(monitor_silence())
