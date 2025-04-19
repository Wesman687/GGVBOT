import asyncio
import difflib
import re
import ollama

from app.config import DUNGEON_ALIASES, FLATTENED_DUNGEONS, ORDINAL_LEVELS


def fuzzy_match_dungeon(raw: str) -> str | None:
    raw = raw.lower().strip()

    # ✅ Direct alias match first
    for canon, aliases in DUNGEON_ALIASES.items():
        if raw in aliases:
            return canon

    # 🔍 Fuzzy fallback only if direct match fails
    all_aliases = list(FLATTENED_DUNGEONS.keys())
    close = difflib.get_close_matches(raw, all_aliases, n=1, cutoff=0.8)
    if close:
        return FLATTENED_DUNGEONS.get(close[0])

    return None
async def extract_dungeon_with_llm(text: str) -> tuple[str, str] | None:
    dungeon_list = ", ".join(DUNGEON_ALIASES.keys())

    def normalize_ordinals(s: str) -> str:
        for word, digit in ORDINAL_LEVELS.items():
            s = re.sub(rf"\b{word}\b", digit, s, flags=re.IGNORECASE)
        return s

    def parse_dungeon_level(raw: str):
        raw = normalize_ordinals(raw)
        raw = re.sub(r"[^a-zA-Z0-9\s]", "", raw)  # Strip weird punctuation

        match = re.search(r"([a-zA-Z ]+?)\s*(?:level\s*)?(\d)", raw, re.IGNORECASE)
        if match:
            dungeon_raw = match.group(1).strip().lower()
            level = match.group(2)
            canonical = fuzzy_match_dungeon(dungeon_raw)
            return (canonical or dungeon_raw.title(), level)
        return None

    prompt = f"""
You are a game assistant for Ultima Online: Outlands. Players may report their dungeon location using voice.

Your job is to extract two things ONLY:
- The dungeon name (must match one of: {dungeon_list})
- The level number (1–8), which may be written as a digit, ordinal (third), or phrase ("level three")

Reply in this format:
Dungeon Level

Examples:
- Pulma 2
- Inferno 3
- Darkmire 1

If the message doesn't contain both, respond with:
Unknown

Message: "{text.strip()}"
Dungeon and Level:
"""

    try:
        # First pass
        response = await asyncio.to_thread(ollama.chat, model="mistral:7b-instruct", messages=[
            {"role": "user", "content": prompt}
        ])
        result = response["message"]["content"].strip()
        print(f"[LLM Dungeon Extract] 🕸️ Raw: {result}")

        parsed = parse_dungeon_level(result)
        if parsed:
            return parsed

        # 🔁 Retry fallback prompt
        fallback_prompt = f"""
Retry: What dungeon and level is this player referring to?
- Known dungeons: {dungeon_list}
- Format: Dungeon Level (e.g., Pulma 2)
- If not clear, respond: Unknown

Text: "{text.strip()}"
Result:
"""
        fallback_response = await asyncio.to_thread(ollama.chat, model="mistral:7b-instruct", messages=[
            {"role": "user", "content": fallback_prompt}
        ])
        fallback_result = fallback_response["message"]["content"].strip()
        print(f"[LLM Dungeon Retry] 🔁 Fallback Raw: {fallback_result}")
        
        # result = run_llama4_inference(prompt)
        # print(f"[LLM Dungeon Extract] 🕸️ Got: {result}")

        return parse_dungeon_level(fallback_result)

    except Exception as e:
        print(f"⚠️ LLM dungeon extraction failed: {e}")

    return None
