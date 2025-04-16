
import asyncio
import json
import re
import ollama

# from app.ai.llama4_inference import run_llama4_inference


async def classify_transcription_intent(text: str) -> dict:
    prompt = f"""
You are Jarvis, a voice assistant for the game Ultima Online: Outlands.

Your job is to analyze player speech and return a JSON object with the following format:

- "intent": one of ["coord_panic", "dungeon_panic", "red_alert", "stop_panic", "greet", "unknown"]

Additionally, include:

- If intent is "coord_panic":
    - "coords": two numbers like "3200 2100"
    - "direction": optional direction (e.g. "north", "southwest") if mentioned

- If intent is "dungeon_panic" or "red_alert":
    - "dungeon": name of the dungeon from this list: Ossuary, Inferno, Darkmire, Aegis, Cavernam, Kraul Hive, Mount Petram, Nusero, Pulma, ShadowSpire Cathedral, The Mausoleum, Time Dungeon
    - "level": a number 1–8 if mentioned (can be written like "third" or "level three")

Only include the fields that match the intent. Do not add explanations or any extra content.

Examples:

"Jarvis, help! We're under attack at 3220 2140 moving east"
→ {"intent": "coord_panic", "coords": "3220 2140", "direction": "east"}

"Stop panic Jarvis"
→ {"intent": "stop_panic"}

"Red alert in Pulma level three"
→ {"intent": "red_alert", "dungeon": "Pulma", "level": 3}

Transcript: "{text.strip()}"
JSON:
"""

    try:
        response = await asyncio.to_thread(ollama.chat, model="mistral:7b-instruct", messages=[
            {"role": "user", "content": prompt}
        ])
        raw = response["message"]["content"]    
        # raw = await asyncio.to_thread(run_llama4_inference, prompt)
        print(f"[LLM JSON Intent] 📦 Raw: {raw}")

        # Extract valid JSON (even from noisy output)
        match = re.search(r"{.*}", raw, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            return parsed
    except Exception as e:
        print(f"⚠️ LLM intent+extraction failed: {e}")

    return {"intent": "unknown"}