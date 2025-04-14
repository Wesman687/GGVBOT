import discord
import asyncio
import os
import wave
import subprocess
from discord.ext import commands
from lt_app.transcriber import transcribe_wav  # ← assuming this exists in live-transcribe

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 859289210765443112
VC_CHANNEL_ID = 860556245772927026

intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

class PCMRecorder(discord.AudioSink):
    def __init__(self):
        self.user_buffers = {}

    def write(self, user: discord.User, data: bytes):
        if user.bot or not data:
            return

        if user.id not in self.user_buffers:
            self.user_buffers[user.id] = bytearray()

        self.user_buffers[user.id].extend(data)

        if len(self.user_buffers[user.id]) >= 48000 * 2 * 3:  # ~3 seconds of audio
            filename = f"temp_{user.name}.pcm"
            with open(filename, "wb") as f:
                f.write(self.user_buffers[user.id])
            self.user_buffers[user.id].clear()

            wav_filename = f"temp_{user.name}.wav"
            convert_pcm_to_wav(filename, wav_filename)

            transcription = transcribe_wav(wav_filename)
            print(f"[Whisper] {user.name}: {transcription}")

def convert_pcm_to_wav(pcm_path, wav_path):
    subprocess.run([
        "ffmpeg", "-f", "s16le", "-ar", "48000", "-ac", "1",
        "-i", pcm_path, wav_path, "-y"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name}")
    guild = bot.get_guild(GUILD_ID)
    vc_channel = guild.get_channel(VC_CHANNEL_ID)

    if vc_channel:
        vc = await vc_channel.connect()
        print(f"🎙️ Connected to voice channel: {vc_channel.name}")
        vc.listen(PCMRecorder())

@bot.command()
async def leave(ctx):
    await ctx.voice_client.disconnect()

def start_discord_bot():
    bot.run(TOKEN)
