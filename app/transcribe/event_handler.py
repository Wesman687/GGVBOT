import asyncio
import re
from app.irc.irc_bot import send_irc_message
from app.websocket import send_speak_command

# Global active event tracker
active_event = {
    "event_name": None,
    "trigger_time": None,
    "owner": None,
}

async def handle_announce_event(text, user):
    match = re.search(r"announce (.+?) happening in (\d+)", text, re.IGNORECASE)
    if match:
        event_name = match.group(1).strip()
        minutes_until = int(match.group(2))
        trigger_time = asyncio.get_event_loop().time() + (minutes_until * 60)

        active_event["event_name"] = event_name
        active_event["trigger_time"] = trigger_time
        active_event["owner"] = user

        await send_irc_message(f"📢 {event_name} starting in {minutes_until} minutes.")
        await send_speak_command(user, f"{event_name} starting in {minutes_until} minutes.")
        print(f"🛠️ Scheduled event: {event_name} in {minutes_until} minutes.")
        return True, "responded"
    else:
        await send_speak_command(user, "I didn't understand the event announcement.")
        return False, "responded"

async def handle_cancel_event(user):
    if active_event["event_name"]:
        event = active_event["event_name"]
        active_event["event_name"] = None
        active_event["trigger_time"] = None
        await send_irc_message(f"❌ {event} was cancelled.")
        await send_speak_command(user, f"{event} was cancelled.")
        print(f"🚫 Event cancelled: {event}")
    else:
        await send_speak_command(user, "There is no event to cancel.")
    return True, "responded"

async def handle_start_event(user):
    if active_event["event_name"]:
        event = active_event["event_name"]
        active_event["event_name"] = None
        active_event["trigger_time"] = None
        await send_irc_message(f"🚨 {event} is starting now!")
        await send_speak_command(user, f"{event} is starting now!")
        print(f"🚀 Event manually started: {event}")
    else:
        await send_speak_command(user, "There is no event to start.")
    return True, "responded"

async def check_event_trigger():
    """Call this regularly from monitor_silence to check if the event timer has reached."""
    if active_event["event_name"] and active_event["trigger_time"]:
        now = asyncio.get_event_loop().time()
        if now >= active_event["trigger_time"]:
            event = active_event["event_name"]
            await send_irc_message(f"🚨 {event} is starting now!")
            active_event["event_name"] = None
            active_event["trigger_time"] = None
            print(f"🚀 Event auto-started: {event}")
