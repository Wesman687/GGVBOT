import re
from app.ai.classifier import extract_coordinates_with_llm
from app.state import user_context
from app.utils.coords import validate_coords
from app.utils.dungeon import extract_dungeon_and_level, extract_dungeon_with_llm, get_dungeon_from_text
from app.irc.irc_bot import send_irc_message, start_panic, stop_panic, update_coord_panic, update_dungeon_panic
from app.utils.helpers import extract_coords, extract_direction
from app.websocket import send_speak_command

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
        
async def handle_stop_panic(user: str) -> bool:
    if user_context[user].get("panic_type") in ["coords", "dungeon"]:
        print(f"✅ Stopping panic for {user}")
        await stop_panic(user)
        user_context[user].pop("panic_coords", None)
        user_context[user].pop("panic_dungeon", None)
        user_context[user].pop("panic_type", None)
    else:
        print(f"⚠️ {user} tried to stop panic, but none was active.")
    return True

def is_stop_command(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in [
        "stop panic", "cancel panic", "end panic", "stand down", "disregard panic", "call off"
    ])

async def handle_active_panic(user, text):
    if is_stop_command(text):
        print(f"🛑 Stop panic phrase detected from {user}")
        return await handle_stop_panic(user), "responded"

    panic_type = user_context[user].get("panic_type")
    if panic_type == "coords":
        print(f"🔄 Active coord panic — treating input as coord update for {user}")
        return await resolve_and_handle_coord_panic(user, text), "silent"
    if panic_type == "dungeon":
        print(f"🔄 Active dungeon panic — treating input as dungeon update for {user}")
        return await resolve_and_handle_dungeon_panic(user, text, None, None), "silent"
    return None, "silent"

async def resolve_and_handle_coord_panic(user, text, coords=None, direction=None):
    from app.utils.helpers import extract_coords, extract_direction, validate_coords

    # Try regex-based extraction first
    coords = coords or extract_coords(text)
    direction = direction or extract_direction(text)

    # If coords failed, try LLM fallback
    if not coords:
        coords = await extract_coordinates_with_llm(text)

    if coords and validate_coords(coords):
        await update_coord_panic(user, coords, direction)
        return True
    else:
        await send_speak_command(user, "Repeat the coordinates?")
        return False
    
async def resolve_and_handle_dungeon_panic(user: str, text: str, dungeon: str | None, level: str | None) -> bool:
    if not (dungeon and level):
        result = await get_dungeon_from_text(text)
        if result:
            dungeon, level = result
        else:
            await send_speak_command(user, "What dungeon and level?")
            return False

    label = f"{dungeon.title()} level {level}"
    await update_dungeon_panic(user, label)
    return True