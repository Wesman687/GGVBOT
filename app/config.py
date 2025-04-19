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

COMMON_MISHEARINGS = {
    "oceawary": "ossuary",
    "ossuray": "ossuary",
    "infero": "inferno",
    "cav": "cavernam",
    "mount p": "mount petram",
    "mount": "mount petram",  # careful if you use "mount" generically
    "ssc": "shadowspire cathedral",
    "maus": "the mausoleum",
    "dm": "darkmire",
}

# Flatten alias list for reverse lookup
FLATTENED_DUNGEONS = {alias: canon for canon, aliases in DUNGEON_ALIASES.items() for alias in aliases}