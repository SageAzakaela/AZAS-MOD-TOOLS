# zomboid_map_gen/roads/dirt_paths.py
"""
Optional dirt path generation.
"""

from PIL import Image

def generate_paths(width, height, conf: dict):
    # placeholder: return empty transparent image
    return Image.new("RGBA", (width, height), (0, 0, 0, 0))
