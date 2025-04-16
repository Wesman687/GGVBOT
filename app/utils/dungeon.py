
import re

from app.ai.dungeon_llm import extract_dungeon_with_llm

# Canonical dungeon list with aliases
DUNGEON_ALIASES = {
    "Ossuary": ["ossuary", "ossuray"],
    "Inferno": ["inferno", "infero"],
    "Darkmire": ["darkmire", "dm"],
    "Aegis": ["aegis"],
    "Cavernam": ["cavernam", "cav"],
    "Kraul Hive": ["kraul hive", "kraul"],
    "Mount Petram": ["mount petram", "mount p", "mount"],
    "Nusero": ["nusero"],
    "Pulma": ["pulma"],
    "ShadowSpire Cathedral": ["shadowspire cathedral", "ssc"],
    "The Mausoleum": ["the mausoleum", "maus"],
    "Time Dungeon": ["time dungeon", "time"]
}

ORDINAL_LEVELS = {
    "first": "1", "second": "2", "third": "3", "fourth": "4",
    "fifth": "5", "sixth": "6", "seventh": "7", "eighth": "8",
}

# Flatten alias list for reverse lookup
FLATTENED_DUNGEONS = {alias: canon for canon, aliases in DUNGEON_ALIASES.items() for alias in aliases}

def fuzzy_match_dungeon(raw: str) -> str | None:
    raw = raw.lower().strip()
    for canon, aliases in DUNGEON_ALIASES.items():
        if any(alias in raw for alias in aliases):
            return canon
    return None

def extract_dungeon_and_level(text: str) -> tuple[str, str] | tuple[None, None]:
    normalized = text.lower()

    matched_dungeon = None
    for canon, variants in DUNGEON_ALIASES.items():
        if any(alias in normalized for alias in variants):
            matched_dungeon = canon
            break

    level = None
    # Try to find numeric level
    level_match = re.search(r"level\s*(\d)", normalized)
    if level_match:
        level = level_match.group(1)
    else:
        # Try to find ordinal level
        for word, digit in ORDINAL_LEVELS.items():
            if word in normalized:
                level = digit
                break

    if matched_dungeon and level:
        return matched_dungeon, level

    return None, None



async def get_dungeon_from_text(text: str) -> tuple[str, str] | None:
    dungeon, level = extract_dungeon_and_level(text)
    if dungeon and level:
        return dungeon, level

    return await extract_dungeon_with_llm(text)
