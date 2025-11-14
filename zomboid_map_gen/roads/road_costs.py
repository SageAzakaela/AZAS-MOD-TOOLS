# zomboid_map_gen/roads/road_costs.py
"""
Sample terrain/vegetation and return a "cost" for putting a road there.
Higher cost = worse place to put a road.
"""

from ..utils import colors as base_colors

# build a table using the user's actual base map colours
# (color, tolerance, cost)
TERRAIN_COST_TABLE = [
    (base_colors.VANILLA["water"][:3],        12, 9999),  # water: basically no
    (base_colors.VANILLA["dark_grass"][:3],   12, 2.5),
    (base_colors.VANILLA["med_grass"][:3],    12, 2.0),
    (base_colors.VANILLA["light_grass"][:3],  12, 1.7),
    (base_colors.VANILLA["dirt"][:3],         15, 1.2),
    (base_colors.VANILLA["gravel_dirt"][:3],  15, 1.3),
    (base_colors.VANILLA["sand"][:3],         15, 1.5),
    (base_colors.VANILLA["light_asphalt"][:3], 10, 1.0),
    (base_colors.VANILLA["medium_asphalt"][:3], 10, 1.0),
    (base_colors.VANILLA["dark_asphalt"][:3], 10, 1.0),
]

# vegetation colors we consider "thick" and should cost extra
DENSE_VEG = [
    base_colors.VEG["dense_forest"][:3],
    base_colors.VEG["dense_trees_grass"][:3],
    base_colors.VEG["bushes_grass"][:3],
    base_colors.VEG["trees_grass"][:3],
]


def _color_distance(c1, c2):
    return abs(c1[0] - c2[0]) + abs(c1[1] - c2[1]) + abs(c1[2] - c2[2])


def terrain_cost_at(x, y, terrain_img, ignore_water=False):
    if terrain_img is None:
        return 1.5
    w, h = terrain_img.size
    if x < 0 or y < 0 or x >= w or y >= h:
        return 9999
    rgb = terrain_img.getpixel((x, y))[:3]
    for base_col, tol, cost in TERRAIN_COST_TABLE:
        if _color_distance(rgb, base_col) <= tol:
            if ignore_water and cost >= 9999:
                return 2.0
            return cost
    return 2.0


def veg_cost_at(x, y, veg_img, ignore_trees=False):
    if veg_img is None:
        return 0.0
    w, h = veg_img.size
    if x < 0 or y < 0 or x >= w or y >= h:
        return 0.0
    rgb = veg_img.getpixel((x, y))[:3]
    for dense in DENSE_VEG:
        if _color_distance(rgb, dense) < 60:
            if ignore_trees:
                return 0.0
            return 1.2
    return 0.0


def segment_avg_cost(x1, y1, x2, y2, terrain_img, veg_img,
                     ignore_water=False, ignore_trees=False, samples=6):
    total = 0.0
    for i in range(samples):
        t = i / max(1, samples - 1)
        sx = int(x1 + (x2 - x1) * t)
        sy = int(y1 + (y2 - y1) * t)
        c = terrain_cost_at(sx, sy, terrain_img, ignore_water=ignore_water)
        c += veg_cost_at(sx, sy, veg_img, ignore_trees=ignore_trees)
        total += c
    return total / samples
