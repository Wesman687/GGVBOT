import re
from app.ai.classifier import classify_transcription_intent
from app.utils.helpers import extract_coords, extract_direction

async def detect_high_level_intent(text: str) -> dict:
    lowered = text.lower()
    
    if "announce" in lowered or "happening in" in lowered:
        return {"intent": "announce_event"}
    if "cancel event" in lowered:
        return {"intent": "cancel_event"}
    if "start event" in lowered:
        return {"intent": "start_event"}


    # 🎯 High-priority override
    if "red alert" in lowered:
        return {"intent": "red_alert"}

    # 🛑 Stop panic command
    if "stop" in lowered and "panic" in lowered:
        return {"intent": "stop_panic"}
    
    # 📍 Direct coordinate match
    coords = extract_coords(text)
    direction = extract_direction(text)
    if coords:
        return {
            "intent": "coord_panic",
            "coords": coords,
            "direction": direction
        }
    if "ocean boss" in lowered or "sea boss" in lowered:
        return {
            "intent": "ocean_boss",
            "coords": coords,
        }
    # 👋 Greeting
    if any(word in lowered for word in ["hello", "hi", "are you there", "hey jarvis"]):
        return {"intent": "greet"}

    # 🏰 Dungeon phrases
    if any(word in lowered for word in ["dungeon", "level", "in the", "we're in", "inside"]):
        return {"intent": "dungeon_panic"}

    # 📍 Coordinate phrase + combat cue
    if re.search(r"\d{3,4}\s+\d{3,4}", lowered):
        if any(phrase in lowered for phrase in [
            "help at", "attacked at",  "we're at",
            "we're being pushed", "fighting at", "under attack",
            "falling back to", "moving to", "headed to"
        ]):
            return {"intent": "coord_panic"}

    # ⚠️ Emergency language fallback (w/o coords)
    if any(word in lowered for word in ["help", "incoming", "attack", "enemy", "pushed", "danger"]):
        return {"intent": "coord_panic"}

    # 🤖 LLM fallback (intent + coords/direction or dungeon/level if relevant)
    print("[Intent Detect] 🤖 Falling back to LLM for deeper understanding...")
    return await classify_transcription_intent(text)
