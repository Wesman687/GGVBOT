import discord
import asyncio
import os

from discord.ext import commands

from app.transcribe.transcriber import custom_callback
from lt_app.audio import discord_callback
from lt_app.transcriber import transcribe_audio
import lt_app.config as config


TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 859289210765443112
VC_CHANNEL_ID = 860556245772927026

intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name}")

    guild = bot.get_guild(GUILD_ID)
    print(f"🔍 Looking for guild {GUILD_ID}... Found: {guild is not None}")

    vc_channel = guild.get_channel(VC_CHANNEL_ID)
    print(f"🔍 Looking for VC {VC_CHANNEL_ID}... Found: {vc_channel is not None}")

    if vc_channel:
        # Make sure we're not already in another VC
        for vc in bot.voice_clients:
            try:
                print(f"🔌 Disconnecting existing VC in: {vc.channel.name}")
                await vc.disconnect(force=True)
            except Exception as e:
                print(f"⚠️ Failed to disconnect from old VC: {e}")

        try:
            print("🎯 Attempting to join voice channel (timeout in 10s)...")
            vc = await asyncio.wait_for(vc_channel.connect(), timeout=10)
            print(f"🎙️ Connected to voice channel: {vc_channel.name}")

        except asyncio.TimeoutError:
            print("❌ Voice connection timed out!")
        except discord.ClientException as e:
            print(f"❌ Discord client error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error while connecting: {type(e).__name__} - {e}")
    else:
        print("❌ Voice channel not found.")


@bot.command()
async def leave(ctx):
    await ctx.voice_client.disconnect()

async def start_discord_bot():
    await bot.start(TOKEN)