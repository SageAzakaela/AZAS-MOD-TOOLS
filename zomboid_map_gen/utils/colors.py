# zomboid_map_gen/utils/colors.py

"""
Vanilla-ish color definitions for Project Zomboid map images,
matching the user's base map & veg map color notes.
"""

# ---- Base Map Colours ----
# Dark Grass | 90 100 35
# Medium Grass | 117 117 47
# Light Grass | 145 135 60
# Sand | 210 200 160
# Light Asphalt | 165 160 140
# Dark Asphalt (main roads) | 100 100 100
# Medium Asphalt | 120 120 120
# Gravel Dirt | 140 70 15
# Dirt | 120 70 20
# Dirt Grass | 80 55 20
# Dark Pothole | 110 100 100
# Light Pothole | 130 120 120
# Water | 0 138 255

DEFAULT_VANILLA = {
    "water": (0, 138, 255, 255),

    "dark_grass": (90, 100, 35, 255),
    "med_grass": (117, 117, 47, 255),
    "light_grass": (145, 135, 60, 255),
    "dirt_grass": (80, 55, 20, 255),

    "sand": (210, 200, 160, 255),

    "light_asphalt": (165, 160, 140, 255),
    "dark_asphalt": (100, 100, 100, 255),
    "medium_asphalt": (120, 120, 120, 255),

    "gravel_dirt": (140, 70, 15, 255),
    "dirt": (120, 70, 20, 255),

    "dark_pothole": (110, 100, 100, 255),
    "light_pothole": (130, 120, 120, 255),
}

VANILLA = dict(DEFAULT_VANILLA)

# ---- Veg Map Colours ----
# Dense Forest | 255 0 0
# Dense Trees + grass | 200 0 0
# Trees + grass | 127 0 0
# Fir Trees + grass | 64 0 0
# Mainly grass, some trees | 0 128 0
# Light long grass | 0 255 0
# Bushes grass + few trees | 255 0 255
# Dead corn 1 | 255 128 0
# Dead corn 2 | 220 100 0
# None (black) | 0 0 0

VEG = {
    "dense_forest": (255, 0, 0, 255),
    "dense_trees_grass": (200, 0, 0, 255),
    "trees_grass": (127, 0, 0, 255),
    "fir_trees_grass": (64, 0, 0, 255),
    "grass_some_trees": (0, 128, 0, 255),
    "light_long_grass": (0, 255, 0, 255),
    "bushes_grass": (255, 0, 255, 255),
    "dead_corn_1": (255, 128, 0, 255),
    "dead_corn_2": (220, 100, 0, 255),
    "none": (0, 0, 0, 255),
}


import re


def reset_vanilla_palette():
    VANILLA.clear()
    VANILLA.update(DEFAULT_VANILLA)


def _normalize_rgb(value):
    if value is None:
        return None
    if isinstance(value, str):
        parts = re.split(r"[,\s]+", value.strip())
    else:
        try:
            parts = list(value)
        except Exception:
            return None
    if len(parts) < 3:
        return None
    try:
        r = int(parts[0])
        g = int(parts[1])
        b = int(parts[2])
    except Exception:
        return None
    return (
        max(0, min(255, r)),
        max(0, min(255, g)),
        max(0, min(255, b)),
    )


def apply_palette_overrides(overrides: dict | None):
    reset_vanilla_palette()
    if not overrides:
        return
    for name, value in overrides.items():
        if name not in DEFAULT_VANILLA:
            continue
        rgb = _normalize_rgb(value)
        if rgb:
            VANILLA[name] = (*rgb, 255)
