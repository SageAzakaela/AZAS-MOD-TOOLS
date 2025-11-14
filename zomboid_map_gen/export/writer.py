# zomboid_map_gen/export/writer.py
from pathlib import Path


def _name(exp: dict, key: str, default: str) -> str:
    v = exp.get(key)
    return v if isinstance(v, str) and v.strip() else default


def save_all(conf, terrain_img, veg_img, roads_img, lots_img, details_img=None):
    out_dir = Path(conf.get("output_dir", "output"))
    out_dir.mkdir(parents=True, exist_ok=True)

    exp = conf.get("export", {})

    # Filenames (allow config override, fall back to sensible defaults)
    name_terrain = _name(exp, "terrain_png", "terrain.png")
    name_veg = _name(exp, "vegetation_png", "vegetation.png")
    name_roads = _name(exp, "roads_png", "roads.png")
    name_lots = _name(exp, "lots_png", "lots.png")
    name_details = _name(exp, "details_png", "details.png")

    # Combined (terrain + roads) separate from preview (terrain + veg + roads)
    name_combined = _name(exp, "combined_png", "combined.png")
    name_preview = exp.get("preview_png") or "preview.png"
    # Optional: a smaller preview to keep GUI memory low
    preview_max_dim = int(exp.get("preview_max_dim", 768))

    if terrain_img:
        terrain_img.save(out_dir / name_terrain)
    if veg_img:
        veg_img.save(out_dir / name_veg)
    if roads_img:
        roads_img.save(out_dir / name_roads)
    if lots_img:
        lots_img.save(out_dir / name_lots)
    if details_img:
        details_img.save(out_dir / name_details)

    # Combined: terrain + roads
    if terrain_img:
        combo = terrain_img.copy()
        if roads_img:
            combo.alpha_composite(roads_img)
        combo.save(out_dir / name_combined)

    # Preview: terrain + veg + roads (+ optional details), downscaled to preview_max_dim
    if terrain_img:
        prev = terrain_img.copy()
        if veg_img:
            prev.alpha_composite(veg_img)
        if roads_img:
            prev.alpha_composite(roads_img)
        # Optionally include details in preview for quick iteration
        if details_img and exp.get("preview_include_details", True):
            prev.alpha_composite(details_img.convert("RGBA"))
        # downscale prior to saving to reduce GUI memory/IO
        w, h = prev.size
        if max(w, h) > preview_max_dim:
            scale = preview_max_dim / float(max(w, h))
            nw, nh = int(w * scale), int(h * scale)
            prev = prev.resize((max(1, nw), max(1, nh)))
        prev.save(out_dir / name_preview)
