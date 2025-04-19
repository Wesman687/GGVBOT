
from datetime import datetime
import difflib
import re

from app.ai.dungeon_llm import extract_dungeon_with_llm
from app.config import COMMON_MISHEARINGS, FLATTENED_DUNGEONS, ORDINAL_LEVELS


# Build flat lookup
MISHEARING_LOOKUP = {}
for correct_word, wrongs in COMMON_MISHEARINGS.items():
    for wrong in wrongs:
        MISHEARING_LOOKUP[wrong] = correct_word

def log_correction(original: str, corrected: str, score: float):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("panicbot_correction_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] '{original}' → '{corrected}' (score: {score:.2f})\n")

def fuzzy_autocorrect(text: str) -> str:
    text = text.lower()
    words = re.findall(r'\b[a-zA-Z]+\b', text)
    corrected_words = []

    all_mishears = list(MISHEARING_LOOKUP.keys())

    for word in words:
        # ✅ Exact match
        if word in MISHEARING_LOOKUP:
            corrected_words.append(MISHEARING_LOOKUP[word])
            continue

        # 🔍 Fuzzy fallback
        close = difflib.get_close_matches(word, all_mishears, n=1, cutoff=0.75)
        if close:
            corrected = MISHEARING_LOOKUP[close[0]]
            score = difflib.SequenceMatcher(None, word, close[0]).ratio()
            corrected_words.append(corrected)
            log_correction(word, corrected, score)
        else:
            corrected_words.append(word)  # No change

    return " ".join(corrected_words)



def extract_dungeon_and_level(text: str):
    normalized = text.lower()
    words = re.findall(r"[a-zA-Z]+", normalized)
    joined = " ".join(words)

    matched_dungeon = None
    all_aliases = list(FLATTENED_DUNGEONS.keys())

    # 🔥 Try full sentence match first (stricter)
    close = difflib.get_close_matches(joined, all_aliases, n=1, cutoff=0.75)
    if close:
        matched_dungeon = FLATTENED_DUNGEONS[close[0]]

    # 🔥 If no full match, fallback to per-word
    if not matched_dungeon:
        for word in words:
            close = difflib.get_close_matches(word, all_aliases, n=1, cutoff=0.8)
            if close:
                matched_dungeon = FLATTENED_DUNGEONS[close[0]]
                break

    # Parse level
    level = None
    level_match = re.search(r"level\s*(\d)", normalized)
    if level_match:
        level = level_match.group(1)
    else:
        for word, digit in ORDINAL_LEVELS.items():
            if word in normalized:
                level = digit
                break

    if matched_dungeon and level:
        return matched_dungeon, level

    return None, None

async def get_dungeon_from_text(text: str) -> tuple[str, str] | None:
    corrected_text = fuzzy_autocorrect(text)
    dungeon, level = extract_dungeon_and_level(corrected_text)
    if dungeon and level:
        return dungeon, level

    return await extract_dungeon_with_llm(text)