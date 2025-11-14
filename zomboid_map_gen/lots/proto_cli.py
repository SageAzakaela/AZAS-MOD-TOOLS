"""
Quick-and-dirty CLI to exercise the prototype lot placement sandbox without
launching the full Tkinter UI.

Usage:
    python -m zomboid_map_gen.lots.proto_cli [--config path/to/conf.json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from .. import config as cfg
from ..core import LOT_COLOR_MAP
from ..terrain import terrain_generator
from ..vegetation import vegetation_generator
from ..roads import road_generator
from . import prototype as lots_prototype


def main():
    parser = argparse.ArgumentParser(description="Prototype lot placement sandbox")
    parser.add_argument("--config", type=str, help="Optional config JSON path.")
    parser.add_argument("--json", type=str, help="Override for the placements JSON output.")
    parser.add_argument("--preview", type=str, help="Override for the overlay preview PNG.")
    args = parser.parse_args()

    conf = cfg.load_config(args.config) if args.config else cfg.default_config()
    lots_conf = conf.get("lots", {})
    if lots_conf.get("mode") != "prototype":
        lots_conf["mode"] = "prototype"

    terrain_img = terrain_generator.generate(conf) if conf.get("terrain", {}).get("enabled", True) else None
    veg_img = vegetation_generator.generate(conf, terrain_img) if terrain_img and conf.get("vegetation", {}).get("enabled", True) else None
    roads_img, _ = road_generator.generate(conf, terrain_img, veg_img) if terrain_img else (None, None)
    placements = lots_prototype.generate_prototype_layout(lots_conf, terrain_img, roads_img, veg_img)

    out_dir = Path(conf.get("output_dir", "output"))
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = Path(args.json) if args.json else out_dir / "lots_prototype.json"
    preview_path = Path(args.preview) if args.preview else out_dir / "lots_prototype_preview.png"

    if placements:
        json_path.write_text(json.dumps(placements, indent=2), encoding="utf-8")
        print(f"[lots.proto] wrote {len(placements)} placements -> {json_path}")
        if terrain_img:
            overlay = _draw_overlay(terrain_img.size, placements, lots_conf)
            overlay.save(preview_path)
            print(f"[lots.proto] preview saved -> {preview_path}")
    else:
        print("[lots.proto] No placements generated. Check road/terrain inputs and TBX folders.")


def _draw_overlay(size: tuple[int, int], placements: list[dict], lots_conf: dict) -> Image.Image:
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pave = lots_conf.get("pave", False)
    for lot in placements:
        color = LOT_COLOR_MAP.get(lot.get("type", ""), (255, 255, 255))
        fill = (210, 210, 210) if pave else color
        x, y = lot.get("x", 0), lot.get("y", 0)
        w, h = lot.get("width", 0), lot.get("height", 0)
        draw.rectangle([x, y, x + w, y + h], fill=fill + (180,))
    return img


if __name__ == "__main__":
    main()
