# zomboid_map_gen/roads/road_generator.py
"""
Road overlay generator.
Supports modes: ortho, ortho45, free.
Generates:
- transparent road overlay (roads_img)
- simple lots mask (lots_img)
"""

import random
import math
from PIL import Image, ImageDraw

from ..utils import colors as base_colors
from . import patterns
from . import road_costs
from . import road_post
from . import dirt_paths


# pick colors straight from user palette
COLOR_HIGHWAY = base_colors.VANILLA["dark_asphalt"][:3]
COLOR_MAJOR   = base_colors.VANILLA["medium_asphalt"][:3]
COLOR_MAIN    = base_colors.VANILLA["light_asphalt"][:3]
COLOR_SIDE    = base_colors.VANILLA["dirt"][:3]

ROAD_STYLES = {
    "highway": {"color": COLOR_HIGHWAY, "width": 7},
    "major":   {"color": COLOR_MAJOR,   "width": 6},
    "main":    {"color": COLOR_MAIN,    "width": 5},
    "side":    {"color": COLOR_SIDE,    "width": 3},
}


def _in_bounds(x, y, w, h, margin=0):
    return margin <= x < (w - margin) and margin <= y < (h - margin)


def _step_from(x, y, angle_deg, length):
    rad = math.radians(angle_deg)
    return x + math.cos(rad) * length, y + math.sin(rad) * length


def _pick_edge_start(w, h):
    side = random.choice(["top", "bottom", "left", "right"])
    if side == "top":
        return random.randint(0, w - 1), 1, 90
    if side == "bottom":
        return random.randint(0, w - 1), h - 2, -90
    if side == "left":
        return 1, random.randint(0, h - 1), 0
    return w - 2, random.randint(0, h - 1), 180


def generate(conf: dict, terrain_img=None, vegetation_img=None):
    if terrain_img is None:
        raise ValueError("road_generator.generate needs terrain_img for sizing")

    width, height = terrain_img.size

    road_conf = conf.get("roads", {})
    angle_mode = road_conf.get("mode", "ortho45")

    params = {
        "num_highways": road_conf.get("num_highways", 2),
        "num_majors": road_conf.get("num_majors", 3),
        "num_mains": road_conf.get("num_mains", 6),
        "num_sides": road_conf.get("num_sides", 12),

        "branch_prob": road_conf.get("branch_prob", 0.15),
        "max_branch_depth": road_conf.get("max_branch_depth", 3),

        "highway_min_len": road_conf.get("highway_min_len", 120),
        "highway_max_len": road_conf.get("highway_max_len", 240),
        "major_min_len": road_conf.get("major_min_len", 90),
        "major_max_len": road_conf.get("major_max_len", 180),
        "main_min_len":  road_conf.get("main_min_len", 70),
        "main_max_len":  road_conf.get("main_max_len", 140),
        "side_min_len":  road_conf.get("side_min_len", 40),
        "side_max_len":  road_conf.get("side_max_len", 90),

        "angle_mode": angle_mode,
        "min_turn": road_conf.get("min_turn", 10.0),
        "max_turn": road_conf.get("max_turn", 35.0),

        "max_segment_cost": road_conf.get("max_segment_cost", 3.0),
        "min_separation": road_conf.get("min_separation", 8),

        "pothole_density": road_conf.get("pothole_density", 0.02),

        "lot_spawn_chance": road_conf.get("lot_spawn_chance", 0.25),
        "lot_min_w": road_conf.get("lot_min_w", 16),
        "lot_max_w": road_conf.get("lot_max_w", 40),
        "lot_min_h": road_conf.get("lot_min_h", 16),
        "lot_max_h": road_conf.get("lot_max_h", 40),

        "ignore_water": road_conf.get("ignore_water", False),
        "ignore_trees": road_conf.get("ignore_trees", False),
    }

    # Deterministic RNG based on master seed + optional offset
    master_seed = conf.get("seed", 0)
    seed_offset = int(road_conf.get("seed_offset", 4242))
    random.seed(master_seed + seed_offset)

    # We'll accumulate polylines per road type for z-order control
    polylines = {
        "highway": [],
        "major": [],
        "main": [],
        "side": [],
    }

    roads_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    lots_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    next_down = {
        "highway": "major",
        "major": "main",
        "main": "side",
        "side": "side",
    }

    # NOTE: separation logic removed per request – roads can branch/touch freely

    def make_road(start_x, start_y, start_angle, road_type, depth=0):
        if depth > params["max_branch_depth"]:
            return

        style = ROAD_STYLES[road_type]
        min_len = params[f"{road_type}_min_len"]
        max_len = params[f"{road_type}_max_len"]

        angle = patterns.snap_angle(start_angle, angle_mode)
        x, y = start_x, start_y
        points = [(x, y)]

        for _ in range(600):
            seg_len = random.randint(min_len, max_len)
            nx, ny = _step_from(x, y, angle, seg_len)

            if not _in_bounds(nx, ny, width, height, margin=3):
                break

            avg_cost = road_costs.segment_avg_cost(
                conf,
                x, y, nx, ny,
                terrain_img, vegetation_img,
                ignore_water=params["ignore_water"],
                ignore_trees=params["ignore_trees"],
            )
            if avg_cost > params["max_segment_cost"]:
                break

            # separation: avoid going too close to existing roads
            # separation disabled – do not block segments based on proximity

            # commit the segment
            points.append((nx, ny))
            # (separation disabled – no occupancy marking)

            # maybe spawn a lot
            if random.random() < params["lot_spawn_chance"]:
                lw = random.randint(params["lot_min_w"], params["lot_max_w"])
                lh = random.randint(params["lot_min_h"], params["lot_max_h"])
                # simple: put lot to the right of segment start
                lx = int(nx + 5)
                ly = int(ny + 5)
                if _in_bounds(lx, ly, width, height, margin=5):
                    road_post.add_parking_lot_rect(lots_img, lx, ly, lw, lh)

            # maybe branch
            if depth < params["max_branch_depth"] and random.random() < params["branch_prob"]:
                if angle_mode == "free":
                    branch_ang = (angle + random.choice([-90, 90])) % 360
                else:
                    branch_ang = patterns.snap_angle(angle + random.choice([-90, 90]), angle_mode)
                child_type = next_down[road_type]
                make_road(nx, ny, branch_ang, child_type, depth + 1)

            # update position
            x, y = nx, ny

            # maybe turn a bit
            if angle_mode == "free":
                jitter = random.uniform(params["min_turn"], params["max_turn"])
                if random.random() < 0.5:
                    jitter = -jitter
                angle = patterns.snap_angle(angle + jitter, angle_mode)
            else:
                # ortho/ortho45: sometimes straight, sometimes right/left
                if random.random() < 0.3:
                    pass
                else:
                    if angle_mode == "ortho":
                        angle = patterns.snap_angle(angle + random.choice([-90, 90]), angle_mode)
                    else:
                        angle = patterns.snap_angle(angle + random.choice([-90, -45, 45, 90]), angle_mode)

        # draw it
        if len(points) > 1:
            polylines[road_type].append(points)

    # highways from edges
    for _ in range(params["num_highways"]):
        sx, sy, ang = _pick_edge_start(width, height)
        make_road(sx, sy, ang, "highway", depth=0)

    # extra majors/mains/sides
    for _ in range(params["num_majors"]):
        sx, sy, ang = _pick_edge_start(width, height)
        make_road(sx, sy, ang, "major", depth=0)
    for _ in range(params["num_mains"]):
        sx, sy, ang = _pick_edge_start(width, height)
        make_road(sx, sy, ang, "main", depth=0)
    for _ in range(params["num_sides"]):
        sx, sy, ang = _pick_edge_start(width, height)
        make_road(sx, sy, ang, "side", depth=0)

    # Draw in z-order: side (bottom) -> main -> major -> highway (top)
    draw = ImageDraw.Draw(roads_img)
    order = ["side", "main", "major", "highway"]
    for k in order:
        style = ROAD_STYLES[k]
        for pts in polylines[k]:
            draw.line(pts, fill=style["color"] + (255,), width=style["width"], joint="curve")

    # post-process: potholes (on asphalt only)
    pothole_density = params["pothole_density"]
    if pothole_density > 0:
        road_post.apply_potholes_noise_jagged(roads_img, density=pothole_density)

    # sprinkle dirt at asphalt/dirt transitions
    road_post.sprinkle_dirt_transitions(roads_img)

    # optional: dirt paths overlay (right now empty)
    _ = dirt_paths.generate_paths(width, height, road_conf)

    return roads_img, lots_img

