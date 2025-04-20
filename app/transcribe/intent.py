import difflib
import re
from app.ai.classifier import classify_transcription_intent
from app.utils.helpers import extract_coords, extract_direction

INTENT_KEYWORDS = {
    "announce_event": ["announce", "happening in"],
    "cancel_event": ["cancel event"],
    "start_event": ["start event"],
    "red_alert": ["red alert"],
    "stop_panic": ["stop panic"],
    "coord_panic": ["help", "incoming", "attack", "enemy", "pushed", "danger"],
    "ocean_boss": ["ocean boss", "sea boss", "ocean", "boss"],
    "dungeon_panic": ["dungeon", "level", "dungeons"],
}

def fuzzy_intent(text: str) -> str | None:
    lowered = text.lower()

    for intent, keywords in INTENT_KEYWORDS.items():
        for keyword in keywords:
            # Fuzzy match with slight tolerance
            matches = difflib.get_close_matches(keyword, lowered.split(), n=1, cutoff=0.8)
            if matches:
                return intent
            if keyword in lowered:
                return intent
    return None

async def detect_high_level_intent(text: str) -> dict:
    lowered = text.lower()

    # 📍 Try fuzzy intent matching first
    intent = fuzzy_intent(lowered)
    if intent:
        if intent == "coord_panic":
            coords = extract_coords(text)
            direction = extract_direction(text)
            if coords:
                return {"intent": "coord_panic", "coords": coords, "direction": direction}
        if intent == "ocean_boss":
            coords = extract_coords(text)
            return {"intent": "ocean_boss", "coords": coords}
        return {"intent": intent}

    # 📍 Direct coordinate match fallback
    coords = extract_coords(text)
    if coords:
        direction = extract_direction(text)
        return {"intent": "coord_panic", "coords": coords, "direction": direction}

    # 🤖 Full fallback: classify with LLM
    print("[Intent Detect] 🤖 Falling back to LLM for deeper understanding...")
    return await classify_transcription_intent(text)