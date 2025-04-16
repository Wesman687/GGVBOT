# app/irc/irc_bot.py

import asyncio
import re

from app.utils.coords import validate_coords
from app.state import user_context

IRC_SERVER = "45.79.137.244"
IRC_PORT = 6667
IRC_NICK = "JarvisBot"
IRC_CHANNEL = "#general"

reader = None
writer = None
user_panic_tasks = {}

async def connect_irc():
    global reader, writer

    print(f"🔌 Connecting to IRC at {IRC_SERVER}:{IRC_PORT}")
    reader, writer = await asyncio.open_connection(IRC_SERVER, IRC_PORT)

    writer.write(f"NICK {IRC_NICK}\r\n".encode())
    writer.write(f"USER {IRC_NICK} 0 * :Jarvis the assistant\r\n".encode())
    await writer.drain()

    await asyncio.sleep(2)
    writer.write(f"JOIN {IRC_CHANNEL}\r\n".encode())
    await writer.drain()

    print(f"✅ Joined IRC channel {IRC_CHANNEL}")

    # Optionally handle ping/pong and keepalive
    asyncio.create_task(handle_incoming_irc())


async def handle_incoming_irc():
    global reader, writer
    while True:
        line = await reader.readline()
        if not line:
            print("❌ IRC connection lost.")
            break
        decoded = line.decode(errors="ignore").strip()
        print(f"[IRC] ← {decoded}")

        if decoded.startswith("PING"):
            pong = decoded.replace("PING", "PONG")
            writer.write(f"{pong}\r\n".encode())
            await writer.drain()
            print(f"[IRC] → {pong}")

        # Match: !panic [user] <x> <y> [direction]
        panic_match = re.match(r":(\w+)!.*PRIVMSG.*?:!panic(?:\s+(\w+))?\s+(\d{1,4})[\s,]+(\d{1,4})(?:\s+(\w+))?", decoded)
        if panic_match:
            triggering_user = panic_match.group(1)
            target_user = panic_match.group(2) or triggering_user
            x = panic_match.group(3).replace(",", "")
            y = panic_match.group(4).replace(",", "")
            coords = f"{x} {y}"
            direction = panic_match.group(5)
            await start_panic(target_user, coords, direction)

        # Match: !stoppanic [user]
        stop_match = re.match(r":(\w+)!.*PRIVMSG.*?:!stoppanic(?:\s+(\w+))?", decoded)
        if stop_match:
            requesting_user = stop_match.group(1)
            target_user = stop_match.group(2) or requesting_user
            await stop_panic(target_user)

        # Match: !updatepanic <user> <x> <y> [direction]
        update_match = re.match(r":(\w+)!.*PRIVMSG.*?:!updatepanic(?:\s+(\w+))?\s+(\d{1,4})[\s,]+(\d{1,4})(?:\s+(\w+))?", decoded)
        if update_match:
            requesting_user = update_match.group(1)
            target_user = update_match.group(2) or requesting_user
            x = update_match.group(3).replace(",", "")
            y = update_match.group(4).replace(",", "")
            new_coords = f"{x} {y}"
            direction = update_match.group(5)
            await update_coord_panic(target_user, new_coords, direction)

async def send_irc_message(message: str):
    global writer
    if writer:
        full = f"PRIVMSG {IRC_CHANNEL} :{message}\r\n"
        writer.write(full.encode())
        await writer.drain()
        print(f"[IRC] → {message}")
    else:
        print("❌ Cannot send message. IRC not connected.")

async def start_panic(user: str, coords_or_dungeon: str, direction: str = None):
    if user in user_panic_tasks:
        await stop_panic(user)

    is_dungeon = "level" in coords_or_dungeon.lower()
    direction_msg = f" (moving {direction})" if direction and not is_dungeon else ""

    if is_dungeon:
        await send_irc_message(f"🚨 {user} is panicking in {coords_or_dungeon}!")
    else:
        await send_irc_message(f"🚨 PANIC ACTIVATED at {coords_or_dungeon} by {user}{direction_msg}! 🚨")

    async def spam_panic():
        for _ in range(20):  # 5 minutes at 15s interval
            if is_dungeon:
                await send_irc_message(f"⚠️ {user} is panicking in {coords_or_dungeon}!")
            else:
                await send_irc_message(f"⚠️ {user} is panicking at {coords_or_dungeon}{direction_msg}!")
            await asyncio.sleep(15)

    user_panic_tasks[user] = asyncio.create_task(spam_panic())

async def start_coord_panic(user: str, coords: str, direction: str = None):
    if user in user_panic_tasks:
        await stop_panic(user)

    msg = f"🚨 PANIC ACTIVATED at {coords} by {user}"
    if direction:
        msg += f" (moving {direction})"
    msg += " 🚨"
    await send_irc_message(msg)

    async def spam_loop():
        for _ in range(20):
            alert = f"⚠️ {user} is panicking at {coords}"
            if direction:
                alert += f" (moving {direction})"
            await send_irc_message(alert)
            await asyncio.sleep(15)

    user_context[user]["panic_type"] = "coords"
    user_context[user]["panic_coords"] = coords
    user_panic_tasks[user] = asyncio.create_task(spam_loop())


# 🏰 Dungeon Panic
async def start_dungeon_panic(user: str, dungeon_label: str):
    if user in user_panic_tasks:
        await stop_panic(user)

    await send_irc_message(f"🚨 {user} is panicking in {dungeon_label}!")

    async def spam_loop():
        for _ in range(20):
            await send_irc_message(f"⚠️ {user} is panicking in {dungeon_label}!")
            await asyncio.sleep(15)

    user_context[user]["panic_type"] = "dungeon"
    user_context[user]["panic_dungeon"] = dungeon_label
    user_panic_tasks[user] = asyncio.create_task(spam_loop())


# 🛑 Shared Stop
async def stop_panic(user: str):
    task = user_panic_tasks.pop(user, None)
    if task:
        task.cancel()
        await send_irc_message(f"✅ Panic canceled for {user}.")
    user_context[user]["panic_type"] = None
    user_context[user]["panic_coords"] = None
    user_context[user]["panic_dungeon"] = None


# 📍 Update Coord Panic
async def update_coord_panic(user: str, coords: str, direction: str = None):
    if user not in user_panic_tasks:
        await start_coord_panic(user, coords, direction)
        return

    msg = f"📍 {user} updated panic location to {coords}"
    if direction:
        msg += f" (moving {direction})"
    await send_irc_message(msg)

    user_context[user]["panic_coords"] = coords


# 🏰 Update Dungeon Panic
async def update_dungeon_panic(user: str, dungeon_label: str):
    if user not in user_panic_tasks:
        await start_dungeon_panic(user, dungeon_label)
        return

    await send_irc_message(f"📍 {user} moved deeper in {dungeon_label}.")
    user_context[user]["panic_dungeon"] = dungeon_label