import asyncio
import re

import ollama
from app.utils.dungeon import DUNGEON_ALIASES, fuzzy_match_dungeon
# from llama4_inference import run_llama4_inference  # 👈 import the new function

async def extract_dungeon_with_llm(text: str) -> tuple[str, str] | None:
    dungeon_list = ", ".join(DUNGEON_ALIASES.keys())
    prompt = f"""
You are a game assistant. Given a chat message from a player in Ultima Online: Outlands, extract the **dungeon name** and **level number**.

Dungeons: {dungeon_list}

Rules:
- Dungeon name must be one from the list above
- Level can be written as "3", "level three", or "third" — convert to a digit
- Reply with ONLY: Dungeon Level (e.g., Pulma 2)
- DO NOT return anything else, not even punctuation

Message: "{text.strip()}"
Dungeon:"""

    try:
        response = await asyncio.to_thread(ollama.chat, model="mistral:7b-instruct", messages=[
            {"role": "user", "content": prompt}
        ])
        result = response["message"]["content"]
        print(f"[LLM JSON Intent] 📦 Raw: {result}")
        # result = run_llama4_inference(prompt)
        # print(f"[LLM Dungeon Extract] 🕸️ Got: {result}")
        match = re.match(r"([a-zA-Z ]+)\s+(\d+)", result)
        if match:
            dungeon_raw = match.group(1).strip().lower()
            level = match.group(2)
            canonical = fuzzy_match_dungeon(dungeon_raw)
            return (canonical or dungeon_raw.title(), level)
    except Exception as e:
        print(f"⚠️ LLM dungeon extraction failed: {e}")
    return None