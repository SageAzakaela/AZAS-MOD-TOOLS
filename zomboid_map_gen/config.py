# zomboid_map_gen/config.py
import json
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
DEFAULT_RULES = ASSETS_DIR / "text" / "Rules.txt"

def default_config() -> dict:
    return {
        "seed": 12345,
        "output_dir": "output",
        "canvas": {
            "cells_x": 1,
            "cells_y": 1,
            "cell_size": 300,
        },
        "preview": {
            "enabled": True,
            "cell_x": 0,
            "cell_y": 0,
            "thumbs": {
                "terrain": True,
                "vegetation": True,
                "combo": True,
                "roads": True,
                "lots": True,
                "details": True,
            },
        },
        "terrain": {
            "enabled": True,
            "scale": 60,
            "octaves": 6,
            "persistence": 0.5,
            "lacunarity": 2.0,
            "water_threshold": 0.25,
            "dark_threshold": 0.45,
            "medium_threshold": 0.70,
            "preset": "default",
            "postprocess": {
                "edge_ragging": True,
                "speckle": True,
                "erosion": True,
                "strength": 0.6,
            },
            "palette": {},
        },
        "vegetation": {
            "enabled": True,
            "preset": "overgrown",
            "scale": 50,
            "octaves": 5,
            "persistence": 0.55,
            "lacunarity": 2.0,
            "respect_terrain": True,
            "mode": "mixed",
            "mixed_wetness": 0.5,
            "use_layers": True,
            # bias helps thicker trees on dark/med grass
            "terrain_bias": {"dark_grass": 0.18, "med_grass": 0.08, "light_grass": -0.1, "sand": -0.22},
            # default layered vegetation for more colours; comment this block to fall back to banded mode
            "layers": [
                {"name": "grass_base", "color": [0,128,0,255], "scale": 70, "octaves": 4, "threshold": 0.45},
                {"name": "light_long_grass", "color": [0,255,0,255], "scale": 60, "octaves": 4, "threshold": 0.58, "terrain_in": ["light_grass","med_grass"]},
                {"name": "trees_grass", "color": [127,0,0,255], "scale": 55, "octaves": 5, "threshold": 0.62, "terrain_in": ["med_grass","dark_grass"]},
                {"name": "dense_trees_grass", "color": [200,0,0,255], "scale": 55, "octaves": 5, "threshold": 0.72, "terrain_in": ["dark_grass"]},
                {"name": "dense_forest", "color": [255,0,0,255], "scale": 50, "octaves": 5, "threshold": 0.80, "terrain_in": ["dark_grass"]},
                {"name": "bushes", "color": [255,0,255,255], "scale": 48, "octaves": 4, "threshold": 0.86, "terrain_in": ["light_grass","med_grass"]},
                {"name": "dead_corn_1", "color": [255,128,0,255], "scale": 64, "octaves": 3, "threshold": 0.78, "terrain_in": ["light_grass","dirt"]},
                {"name": "dead_corn_2", "color": [220,100,0,255], "scale": 64, "octaves": 3, "threshold": 0.82, "terrain_in": ["light_grass","dirt"]},
            ],
        },
        "rules_palette": {
            "terrain": {},
            "vegetation": {},
        },
        "roads": {
            "enabled": True,
            "planner": "random",          # user prefers random by default
            "mode": "ortho45",
            "type_angle_modes": {"highway": "ortho45", "major": "ortho45", "main": "ortho45", "side": "free"},
            # hierarchical counts tuned for nicer variety on 1x1..3x3
            "hierarchical": True,
            "highways_count": 2,
            "majors_per_highway": 2,
            "mains_per_major": 3,
            "sides_per_main": 3,
            # lengths & segment budgets (random planner)
            "grid_steps": {"highway": 9, "major": 6, "main": 6, "side": 3},
            "highway_min_len": 140, "highway_max_len": 260,
            "major_min_len": 100,  "major_max_len": 190,
            "main_min_len":  75,   "main_max_len": 150,
            "side_min_len":  45,   "side_max_len": 95,
            "highway_segments_max": 14,
            "major_segments_max":   11,
            "main_segments_max":    10,
            "side_segments_max":     6,
            # cost & separation
            "max_segment_cost": 3.0,
            "ignore_water": False,
            "ignore_trees": False,
            "min_parallel_sep": {"highway": 24, "major": 18, "main": 14, "side": 10},
            # potholes
            "pothole_density": 0.02,
            # pathfinder still available
            "planner_grid": 4,
            "towns": 1,
            "town_block": 48,
            "farm_spurs": 12,
        },
        "lots": {
            "mode": "prototype",
            "placed": [],
            "prototype": {
                "enabled": True,
                "asset_root": "zomboid_map_gen/assets/prototype_lots",
                "collision_padding": 8,
                "attempts_per_lot": 100,
                "categories": {
                    "residential": {
                        "folder": "residential",
                        "count": 8,
                        "road_distance": {"min": 10, "max": 26},
                        "terrain_pref": ["light_grass", "med_grass"],
                        "vegetation_pref": ["light_long_grass", "grass_some_trees"],
                    },
                    "commercial": {
                        "folder": "commercial",
                        "count": 5,
                        "road_distance": {"min": 8, "max": 18},
                        "terrain_pref": ["light_asphalt", "medium_asphalt", "sand", "dirt", "light_grass"],
                        "vegetation_pref": ["bushes_grass", "light_long_grass"],
                    },
                    "industrial": {
                        "folder": "industrial",
                        "count": 4,
                        "road_distance": {"min": 16, "max": 40},
                        "terrain_pref": ["dark_grass", "water", "med_grass"],
                        "vegetation_pref": ["dense_forest", "dense_trees_grass", "trees_grass"],
                    },
                },
                "size_presets": {
                    "residential": [
                        {"name": "small_house", "width": 18, "height": 20, "stories": 1},
                        {"name": "mid_house", "width": 24, "height": 26, "stories": 2},
                    ],
                    "commercial": [
                        {"name": "shop_front", "width": 30, "height": 20, "stories": 1},
                        {"name": "corner_store", "width": 26, "height": 26, "stories": 2},
                    ],
                    "industrial": [
                        {"name": "warehouse", "width": 34, "height": 34, "stories": 1},
                        {"name": "factory_strip", "width": 42, "height": 24, "stories": 1},
                    ],
                },
            },
        },
        "export": {
            "terrain_png": "terrain.png",
            "vegetation_png": "vegetation.png",
            "roads_png": "roads.png",
            "combined_png": "combined.png",
            "lots_png": "lots.png",
            "details_png": "details.png",
            "tile_prefix": "map",
            # preview saved downscaled to reduce GUI memory
            "preview_png": "preview.png",
            "preview_max_dim": 768,
            "preview_include_details": True,
        },
        "worlded": {
            "project_prefix": "INFINITY_Z",
            "output_root": "worlded_projects",
            "rules_file": str(DEFAULT_RULES),
            "worlded_exe": "",
            "default_project_name": "prototype",
            "assign_maps": True,
            "update_existing": True,
            "replace_existing": True,
            "open_folder": False,
            "auto_launch": False,
        },
        "audio": {
            "enabled": True,
            "music_mode": "always",
            "music_volume_db": -12.0,
        },
        "details": {
            "enabled": True,
            "density_multiplier": 1.0,
            "apply_to_vegetation": True,
            "preset": "pretty",
            "quick": {
                "flowers": {"enabled": True,  "density": 0.03},
                "leaves":  {"enabled": True,  "density": 0.04},
                "forest_floor": {"enabled": True, "density": 0.02},
                "trash":   {"enabled": True,  "density": 0.02},
                "cracks":  {"enabled": True,  "density": 0.01},
                "blood":   {"enabled": False, "density": 0.02},
            },
            "layers": [
                {
                    "name": "flowers_light_grass",
                    "enabled": True,
                    "rule_color": [240, 200, 160],
                    "density": 0.04,
                    "scale": 55,
                    "terrain_in": ["light_grass"],
                },
                {
                    "name": "bushes_med_grass",
                    "enabled": True,
                    "rule_color": [255, 0, 255],  # reuse veg magenta for demo rules
                    "density": 0.02,
                    "scale": 60,
                    "terrain_in": ["med_grass"],
                },
                {
                    "name": "fallen_leaves_near_trees",
                    "enabled": True,
                    "rule_color": [205, 95, 35],
                    "density": 0.06,
                    "scale": 70,
                    "veg_in": ["trees_grass", "dense_trees_grass", "dense_forest", "fir_trees_grass"],
                    "near_radius": 3,
                },
                {
                    "name": "trash_on_asphalt",
                    "enabled": True,
                    "rule_color": [160, 130, 95],   # one of the Street Trash colors
                    "density": 0.03,
                    "scale": 42,
                    "road_mode": "asphalt_only",
                },
            ],
        },
    }

def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(conf: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(conf, f, indent=2)
