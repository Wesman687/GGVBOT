import asyncio
import json
import subprocess
import signal
import os

from app.transcribe.transcriber import start_transcriber_loop
from app.websocket import start_ws_server
from app.irc.irc_bot import connect_irc, writer as irc_writer  # 👈
from app.websocket import ws_clients 
from app.discord_module.discord_bot import start_discord_bot, stop_discord_bot

# Store global references
node_process = None
ws_server = None
discord_task = None

def start_node_listener():
    global node_process
    node_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "node_audio_listener"))
    node_process = subprocess.Popen(["node", "index.js"], cwd=node_dir, shell=True)
    print("🚀 Node.js Discord listener started")

async def shutdown():
    print("\n🛑 Shutting down gracefully...")

    if ws_server:
        ws_server.close()
        await ws_server.wait_closed()
        print("🌐 WebSocket server stopped")
    try:
        print("📨 Sending shutdown to Node.js client...")
        for ws in ws_clients.copy():
            await ws.send(json.dumps({"type": "shutdown"}))
    except Exception as e:
        print(f"⚠️ WebSocket client shutdown failed: {e}")

    if irc_writer:
        print("📴 Disconnecting from IRC...")
        try:
            irc_writer.write(b"QUIT :Shutting down\r\n")
            await irc_writer.drain()
            irc_writer.close()
            await irc_writer.wait_closed()
        except Exception as e:
            print(f"⚠️ IRC disconnect error: {e}")

    if node_process and node_process.poll() is None:
        print("🧼 Terminating Node.js subprocess...")
        node_process.terminate()
        try:
            node_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            node_process.kill()

    print("✅ Cleanup complete. Exiting.")
    os._exit(0)

async def main():
    global ws_server
    start_node_listener()
    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda s, f: asyncio.create_task(shutdown()))
    except NotImplementedError:
        print("⚠️ Signal handling not supported on this platform (Windows). Ctrl+C may not work cleanly.")
    ws_server = await start_ws_server()
    await connect_irc()
    await start_transcriber_loop()  # ✅ now the transcription monitor loop starts too

    # ✅ Keep the WebSocket server alive
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Ctrl+C received. Exiting...")
