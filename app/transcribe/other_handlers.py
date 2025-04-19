


import base64
from app.irc.irc_bot import send_irc_message
from app.utils.coords import validate_coords
from app.utils.helpers import extract_coords
from app.websocket import send_speak_command


async def handle_ocean_boss(user, text):
    coords = extract_coords(text)
    if coords and validate_coords(coords):
        x, y = map(int, coords.split())
        try:
            raw = "#uooutlands␟vendorlocation␟Daddy␟new item name␟0␟0␟11331355␟0x449BAB01␟1322683753"
            parts = raw.split("␟")
            parts[4] = str(x)
            parts[5] = str(y)
            encoded = base64.b64encode("␟".join(parts).encode("utf-8")).decode("utf-8")

            await send_irc_message(f"🌊 Ocean Boss sighted at {coords}!")
            await send_irc_message(f"{encoded}")
            return True, "silent"
        except Exception as e:
            await send_irc_message(f"❌ Error encoding boss coords: {e}")
            return False, "responded"
    else:
        await send_speak_command(user, "Where is the Ocean Boss?")
        return False, "responded"
    
async def retry_ocean_boss(user, text):
    coords = extract_coords(text)
    if coords and validate_coords(coords):
        return await handle_ocean_boss(user, text)
    return False, "silent"