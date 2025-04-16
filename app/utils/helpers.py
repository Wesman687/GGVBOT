

import re



def extract_coords(text: str):
    match = re.search(r'\b(\d{3,4})\s+(\d{3,4})\b', text)
    return match.group(0) if match else None

def normalize_transcript(text: str) -> str:
    import re
    # Basic normalizations
    text = re.sub(r'(\d),(\d{3})', r'\1\2', text)
    text = re.sub(r'[,;]', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    
    # Common misheard fixes
    text = re.sub(r"\bpanning\b", "panic", text, flags=re.I)
    
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