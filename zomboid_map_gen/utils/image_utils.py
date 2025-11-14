# zomboid_map_gen/utils/image_utils.py
"""
Image creation/compositing helpers.
Wraps Pillow so other modules don't have to import it directly.
"""

try:
    from PIL import Image
except ImportError:
    Image = None


def create_rgba(width: int, height: int, color=(0, 0, 0, 0)):
    if Image is None:
        return None
    return Image.new("RGBA", (width, height), color)


def composite_under(base, overlay):
    """
    Put base at the bottom and overlay on top (respecting alpha).
    """
    if base is None:
        return overlay
    if overlay is None:
        return base
    base = base.copy()
    base.paste(overlay, (0, 0), overlay)
    return base
