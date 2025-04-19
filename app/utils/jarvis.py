import difflib
import re


JARVIS_ALIASES = [
    "jarvis", "garvis", "jarvus", "jarviz", "darvis", "garves", "jervis", "jarbis", "jarviss", "charvis"
]


def heard_jarvis(text: str) -> bool:
    """Fuzzy detect if Jarvis was probably mentioned."""
    words = re.findall(r"[a-zA-Z]+", text.lower())
    for word in words:
        matches = difflib.get_close_matches(word, JARVIS_ALIASES, n=1, cutoff=0.7)
        if matches:
            return True
    return False

