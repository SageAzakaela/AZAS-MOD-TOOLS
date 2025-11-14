# zomboid_map_gen/vegetation/presets.py
"""
Vegetation presets to quickly change density / patchiness.
"""

def get_preset(name: str):
    name = (name or "").lower()

    if name == "overgrown":
        return {
            "scale": 45,
            "octaves": 5,
            "persistence": 0.6,
            "lacunarity": 2.1,
        }
    if name == "rural":
        return {
            "scale": 65,
            "octaves": 4,
            "persistence": 0.5,
            "lacunarity": 2.0,
        }
    if name == "suburban":
        return {
            "scale": 85,
            "octaves": 3,
            "persistence": 0.45,
            "lacunarity": 2.0,
        }

    # default
    return {
        "scale": 50,
        "octaves": 5,
        "persistence": 0.55,
        "lacunarity": 2.0,
    }
