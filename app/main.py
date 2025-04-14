import asyncio
from discord_module.discord_bot import start_discord_bot
from transcribe.transcriber import start_transcriber

async def main():
    # Run all components concurrently
    await asyncio.gather(
        start_discord_bot(),
        asyncio.to_thread(start_transcriber) 
        # start_irc_bot(),
        # start_transcriber()
    )

if __name__ == "__main__":
    asyncio.run(main())