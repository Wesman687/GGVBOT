

import json
import re



def validate_coords(coords: str) -> bool:
    try:
        x, y = map(int, coords.split())
        return 0 <= x <= 7000 and 0 <= y <= 7000
    except:
        return False

def extract_coords(text: str) -> str | None:
    # Normalize common separators to spaces: dash, comma, "to", etc.
    cleaned = re.sub(r"\b(to|at|into|through)\b", " ", text.lower())
    cleaned = re.sub(r"[-,]+", " ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned.strip())

    # Extract two 3- or 4-digit numbers
    match = re.search(r"\b(\d{3,4})\s+(\d{3,4})\b", cleaned)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    return None
def normalize_transcript(text: str) -> str:
    import re

    # Lowercase junk patterns
    junk_phrases = [
        "we'll see you in the next video",
        "okay um let's see here",
        "hello was that going on",
        "okay um",
        "okay so",
        "we're trying to go to",
    ]
    for junk in junk_phrases:
        if junk in text.lower():
            print(f"🗑️ Detected Whisper filler/junk: {junk}")
            return ""

    # Remove commas from numbers
    text = re.sub(r'(\d),(\d{3})', r'\1\2', text)
    text = re.sub(r'[,;]', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)

    # Fix common misheard terms
    corrections = {
        r"\bpanning\b": "panic",
        r"\bpoma\b": "pulma",
        r"\bpulmy\b": "pulma",
        r"\bhoma\b": "pulma",
        r"\bauxuary\b": "ossuary",
        r"\bossawary\b": "ossuary",
        r"\beferno\b": "inferno",
        r"\baferna\b": "inferno",
    }
    for wrong, correct in corrections.items():
        text = re.sub(wrong, correct, text, flags=re.I)

    return text.strip()



def extract_direction(text: str) -> str | None:
    """Extract direction like north, south, east, west from text if present."""
    match = re.search(r"\b(north(?:east)?|south(?:west)?|east|west|northeast|northwest|southeast|southwest)\b", text.lower())
    return match.group(1) if match else None


DIRECTION_KEYWORDS = {
    "north", "south", "east", "west",
    "northeast", "northwest", "southeast", "southwest",
    "up", "down", "left", "right"
}

MOVEMENT_PHRASES = {
    "heading", "moving", "now at", "going to", "changed to", "update", "new location"
}

def parse_keywords_and_direction(text: str):
    text = text.lower()

    # Fallback: check if movement language exists
    has_movement = any(phrase in text for phrase in MOVEMENT_PHRASES)
    direction = next((d for d in DIRECTION_KEYWORDS if d in text), None)

    # Quick coordinate match
    coords_match = re.search(r"\b(\d{3,4})[\s,]+(\d{3,4})\b", text)
    coords = None
    if coords_match:
        coords = f"{coords_match.group(1)} {coords_match.group(2)}"

    # If there's evidence of update intent, return that
    if has_movement or direction:
        return {
            "intent": "update_coords" if coords or direction else "none",
            "coords": coords,
            "direction": direction
        }

    return {
        "intent": "none",
        "coords": None,
        "direction": None
    }
    
def extract_json_fallback(raw: str) -> dict:
    # Attempt clean parse first
    try:
        return json.loads(raw)
    except Exception:
        pass

    # Fallback: extract closest `{}` section
    try:
        match = re.search(r'{.*}', raw, re.DOTALL)
        if match:
            candidate = match.group(0)
            candidate = re.sub(r'([^\s,{"])(\s*")', r'\1,\2', candidate)  # Fix missing commas
            return json.loads(candidate)
    except Exception as e:
        print(f"⚠️ LLM fallback JSON parse failed: {e}")
    
    return {"intent": "unknown"}