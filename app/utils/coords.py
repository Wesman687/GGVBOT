

def validate_coords(coords: str) -> bool:
    try:
        x, y = map(int, coords.split())
        return 0 <= x <= 7000 and 0 <= y <= 7000
    except:
        return False