# zomboid_map_gen/terrain/presets.py
"""
Prebuilt terrain presets.
These mainly tweak thresholds and scale.
"""

def get_preset(name: str):
    name = (name or "").lower()

    if name == "islands":
        return {
            "water_threshold": 0.35,
            "dark_threshold": 0.52,
            "medium_threshold": 0.72,
            "scale": 85,
        }
    if name == "lakes":
        return {
            "water_threshold": 0.30,
            "dark_threshold": 0.50,
            "medium_threshold": 0.72,
            "scale": 55,
        }
    if name == "dry":
        return {
            "water_threshold": 0.15,
            "dark_threshold": 0.42,
            "medium_threshold": 0.68,
            "scale": 60,
        }

    # default
    return {
        "water_threshold": 0.25,
        "dark_threshold": 0.45,
        "medium_threshold": 0.70,
        "scale": 60,
    }
