import re
from app.state import user_context
from app.utils.coords import validate_coords
from app.utils.dungeon import extract_dungeon_and_level, extract_dungeon_with_llm
from app.irc.irc_bot import send_irc_message, start_panic, stop_panic, update_panic_coords
from app.utils.helpers import extract_coords, extract_direction
from app.websocket import send_speak_command
from app.ai.classifier import extract_coordinates_with_llm

async def handle_stop_panic(user):
    if user_context[user].get("panic_type") in ["coords", "dungeon"]:
        print(f"✅ Stopping panic for {user}")
        await stop_panic(user)
        user_context[user].pop("panic_coords", None)
        user_context[user].pop("panic_dungeon", None)
        user_context[user].pop("panic_type", None)
    else:
        print(f"⚠️ {user} tried to stop panic, but none was active.")

async def handle_greeting(user):
    await send_speak_command(user, "Hi, I'm Jarvis. How may I help you?")

async def handle_red_alert(user, text):
    coords = extract_coords(text)
    direction = extract_direction(text)
    if coords:
        await send_irc_message(f"🚨 RED ALERT from {user} in {coords}{f' moving {direction}' if direction else ''}!")
    else:
        await send_irc_message(f"🚨 RED ALERT from {user}! (no coords)")

async def handle_coord_panic(user, text):
    coords = extract_coords(text)
    if not coords:
        coords = await extract_coordinates_with_llm(text)
    direction = extract_direction(text)

    if coords and validate_coords(coords):
        user_context[user]["panic_type"] = "coords"
        user_context[user]["panic_coords"] = coords
        print(f"🚨 Coord panic triggered for {user}: {coords}")
        await start_panic(user, coords, direction)
    else:
        await send_speak_command(user, "Please repeat the coordinates.")

async def handle_dungeon_panic(user, text):
    dungeon, level = extract_dungeon_and_level(text)
    if not dungeon or not level:
        result = await extract_dungeon_with_llm(text)
        if result:
            dungeon, level = result

    if dungeon and level:
        label = f"{dungeon.title()} level {level}"
        user_context[user]["panic_type"] = "dungeon"
        user_context[user]["panic_dungeon"] = label
        print(f"🚨 Dungeon panic triggered for {user}: {label}")
        await start_panic(user, label)
    else:
        await send_speak_command(user, "I couldn't understand the dungeon and level. Please repeat.")
