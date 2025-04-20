
import asyncio
import json
import re
import ollama

# from app.ai.llama4_inference import run_llama4_inference


async def classify_transcription_intent(text: str) -> dict:
    prompt = f"""
You are Jarvis, a voice assistant for the game Ultima Online: Outlands.

Your job is to analyze player speech and return a JSON object with the following format:

- "intent": one of ["coord_panic", "dungeon_panic", "red_alert", "stop_panic", "greet", "announce_event", "cancel_event", "start_event", "unknown"]

Additionally, include:

- If intent is "coord_panic":
    - "coords": two numbers like "3200 2100"
    - "direction": optional direction (e.g. "north", "southwest") if mentioned

- If intent is "dungeon_panic" or "red_alert":
    - "dungeon": name of the dungeon from this list: Ossuary, Inferno, Darkmire, Aegis, Cavernam, Kraul Hive, Mount Petram, Nusero, Pulma, ShadowSpire Cathedral, The Mausoleum, Time Dungeon
    - "level": a number 1–8 if mentioned (can be written like "third" or "level three")

- If intent is "announce_event":
    - "event_name": short name of the event (e.g., "Ocean Boss", "Corpse Creek")
    - "time_until_start": how many minutes until the event starts (e.g., "10 minutes")

Only include the fields that match the intent. Do not add explanations or any extra content.

Examples:

"Jarvis, help! We're under attack at 3220 2140 moving east"
→ {{"intent": "coord_panic", "coords": "3220 2140", "direction": "east"}}

"Stop panic Jarvis"
→ {{"intent": "stop_panic"}}

"Red alert in Pulma level three"
→ {{"intent": "red_alert", "dungeon": "Pulma", "level": 3}}

"Jarvis announce Ocean Boss happening in 10 minutes"
→ {{"intent": "announce_event", "event_name": "Ocean Boss", "time_until_start": "10 minutes"}}

Transcript: "{text.strip()}"
JSON:
"""

    try:
        response = await asyncio.to_thread(ollama.chat, model="mistral:7b-instruct", messages=[
            {"role": "user", "content": prompt}
        ])
        raw = response["message"]["content"]    
        print(f"[LLM JSON Intent] 📦 Raw: {raw}")

        # Extract valid JSON (even from noisy output)
        match = re.search(r"{.*}", raw, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            return parsed
    except Exception as e:
        print(f"⚠️ LLM intent+extraction failed: {e}")

    return {"intent": "unknown"}


async def extract_coordinates_with_llm(text: str) -> str | None:
    prompt = f"""
Extract the two coordinate numbers (e.g., "3400 2500") from this user message. 
Return ONLY the two numbers separated by a space, nothing else.

Message: "{text.strip()}"
Coords:
"""
    try:
        # response = run_llama4_inference(prompt)
        # coords = response["message"]["content"].strip()
        response = await asyncio.to_thread(ollama.chat, model="mistral:7b-instruct", messages=[
            {"role": "user", "content": prompt}
        ])
        coords = response["message"]["content"]   
        print(f"[LLM Coord Extract] 📍 Got: {coords}")
        if re.match(r"^\d{3,4} \d{3,4}$", coords):
            return coords
    except Exception as e:
        print(f"⚠️ LLM coordinate extraction failed: {e}")
    return None