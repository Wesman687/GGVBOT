# websocket.py
import asyncio
import base64
import json
import websockets
import os
import pyttsx3

user_buffers = {}
last_spoke = {}
ws_clients = set()

# Initialize TTS engine
tts_engine = pyttsx3.init()

def synthesize_response(text, filename="jarvis.wav"):
    tts_engine.save_to_file(text, filename)
    tts_engine.runAndWait()
    return filename

async def send_speak_command(user, text):
    print(f"🟢 Wake word detected from {user}! ✅")
    filepath = synthesize_response(text)
    if os.path.exists(filepath):
        with open(filepath, "rb") as f:
            b64_audio = base64.b64encode(f.read()).decode("utf-8")
        message = json.dumps({
            "type": "speak",
            "user": user,
            "audio": b64_audio,
            "format": "wav"
        })
        for client in ws_clients:
            await client.send(message)

def add_audio_chunk(user_id, audio_bytes):
    if user_id not in user_buffers:
        user_buffers[user_id] = bytearray()
    user_buffers[user_id].extend(audio_bytes)
    last_spoke[user_id] = asyncio.get_event_loop().time()

def pop_audio_buffer(user_id):
    return user_buffers.pop(user_id, None)

async def handle_ws_connection(websocket):
    print("🔌 WebSocket client connected")
    ws_clients.add(websocket)
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                audio_bytes = base64.b64decode(data["audio"])
                speaker_name = data["user"]
                add_audio_chunk(speaker_name, audio_bytes)
                print(f"🕡 Receiving audio from {speaker_name} (buffer: {len(user_buffers[speaker_name])} bytes)")
            except Exception as e:
                print(f"⚠️ Error in WebSocket callback: {e}")
    except websockets.exceptions.ConnectionClosed:
        print("❌ WebSocket client disconnected")
    finally:
        ws_clients.discard(websocket)

async def start_ws_server():
    server = await websockets.serve(handle_ws_connection, "localhost", 8765)
    print("🌐 WebSocket server started on ws://localhost:8765")
    return server