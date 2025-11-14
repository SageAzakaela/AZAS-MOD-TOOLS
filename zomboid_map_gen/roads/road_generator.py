"""
Road overlay generator.

Two planners are available:
1) random: legacy hierarchical random-walk with branching
2) path:   deterministic pathfinding on a coarse grid with town grids

Default is "path" which tends to be reliable and obstacle-aware.
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

# make widths multiples of 3 to play nice with 300px cells / 3-tile cars
ROAD_STYLES = {
    "highway": {"color": COLOR_HIGHWAY, "width": 9},
    "major":   {"color": COLOR_MAJOR,   "width": 6},
    "main":    {"color": COLOR_MAIN,    "width": 6},
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

    planner = (road_conf.get("planner", "path") or "path").lower()

    # --- hierarchy counts (used by both planners) ---
    hierarchical = road_conf.get("hierarchical", True)
    highways_count = int(road_conf.get("highways_count", 1))
    majors_per_highway = int(road_conf.get("majors_per_highway", 2))
    mains_per_major = int(road_conf.get("mains_per_major", 3))
    sides_per_main = int(road_conf.get("sides_per_main", 2))

    # legacy fallback
    legacy_totals = {
        "num_highways": road_conf.get("num_highways", highways_count),
        "num_majors": road_conf.get("num_majors", majors_per_highway * highways_count),
        "num_mains": road_conf.get("num_mains", mains_per_major * majors_per_highway * highways_count),
        "num_sides": road_conf.get("num_sides", sides_per_main * mains_per_major * majors_per_highway * highways_count),
    }

    # --- angle modes ---
    default_mode = (road_conf.get("mode", "ortho45") or "ortho45").lower()
    type_modes = road_conf.get("type_angle_modes", {
        "highway": default_mode,
        "major": default_mode,
        "main": default_mode,
        "side": default_mode,
    })

    # --- grid steps ---
    grid_steps = road_conf.get("grid_steps", {
        "highway": 9,
        "major": 6,
        "main": 6,
        "side": 3,
    })

    # --- lengths & segment budgets (now you can expose these in GUI) ---
    length_ranges = {
        "highway": (
            road_conf.get("highway_min_len", 120),
            road_conf.get("highway_max_len", 240),
        ),
        "major": (
            road_conf.get("major_min_len", 90),
            road_conf.get("major_max_len", 180),
        ),
        "main": (
            road_conf.get("main_min_len", 70),
            road_conf.get("main_max_len", 140),
        ),
        "side": (
            road_conf.get("side_min_len", 40),
            road_conf.get("side_max_len", 90),
        ),
    }
    segments_max = {
        "highway": int(road_conf.get("highway_segments_max", 12)),
        "major":   int(road_conf.get("major_segments_max", 10)),
        "main":    int(road_conf.get("main_segments_max", 9)),
        # make side roads less rambly by default
        "side":    int(road_conf.get("side_segments_max", 5)),
    }

    # --- free-mode turn jitter (random planner only) ---
    turn_min = float(road_conf.get("free_turn_min_deg", 10.0))
    turn_max = float(road_conf.get("free_turn_max_deg", 35.0))

    # --- cost ---
    max_segment_cost = float(road_conf.get("max_segment_cost", 3.0))

    # --- separation ---
    min_parallel_sep = road_conf.get("min_parallel_sep", {
        "highway": 24,
        "major": 18,
        "main": 14,
        "side": 10,
    })

    # --- lots ---
    lot_spawn_chance = float(road_conf.get("lot_spawn_chance", 0.25))
    lot_min_w = int(road_conf.get("lot_min_w", 16))
    lot_max_w = int(road_conf.get("lot_max_w", 40))
    lot_min_h = int(road_conf.get("lot_min_h", 16))
    lot_max_h = int(road_conf.get("lot_max_h", 40))

    ignore_water = bool(road_conf.get("ignore_water", False))
    ignore_trees = bool(road_conf.get("ignore_trees", False))

    # RNG
    master_seed = conf.get("seed", 0)
    seed_offset = int(road_conf.get("seed_offset", 4242))
    random.seed(master_seed + seed_offset)

    # --- accumulators ---
    polylines = {"highway": [], "major": [], "main": [], "side": []}
    same_type_segments = {"highway": [], "major": [], "main": [], "side": []}

    roads_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    lots_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    # helpers ---------------------------------------------------------------
    # Common helpers used by both planners
    def _record_segment(road_type: str, x1, y1, x2, y2):
        ang = patterns.line_angle_degrees(x1, y1, x2, y2)
        same_type_segments[road_type].append((x1, y1, x2, y2, ang))

    def _too_close_parallel(road_type: str, x1, y1, x2, y2) -> bool:
        sep = float(min_parallel_sep.get(road_type, 0) or 0)
        if sep <= 0:
            return False
        ang_new = patterns.line_angle_degrees(x1, y1, x2, y2)
        for (ax1, ay1, ax2, ay2, aang) in same_type_segments[road_type]:
            diff = abs((ang_new - aang + 180) % 360 - 180)
            if diff <= 30:
                mx, my = (x1 + x2) * 0.5, (y1 + y2) * 0.5
                mxa, mya = (ax1 + ax2) * 0.5, (ay1 + ay2) * 0.5
                if (mx - mxa) ** 2 + (my - mya) ** 2 < sep * sep:
                    return True
        return False

    def _choose_branch_angles(parent_angle: float, child_mode: str):
        child_mode = (child_mode or default_mode).lower()
        if child_mode == "free":
            return [(parent_angle + 90) % 360, (parent_angle - 90) % 360]
        if child_mode == "ortho":
            return [
                patterns.snap_angle(parent_angle + 90, "ortho"),
                patterns.snap_angle(parent_angle - 90, "ortho"),
            ]
        return [
            patterns.snap_angle(parent_angle + 45, "ortho45"),
            patterns.snap_angle(parent_angle - 45, "ortho45"),
            patterns.snap_angle(parent_angle + 90, "ortho45"),
            patterns.snap_angle(parent_angle - 90, "ortho45"),
        ]

    # ------------------- Random-walk planner ------------------------------
    def _make_road(start_x, start_y, start_angle, road_type: str):
        mode = (type_modes.get(road_type) or default_mode).lower()
        gstep = grid_steps.get(road_type, 0)
        min_len, max_len = length_ranges[road_type]
        max_segs = segments_max[road_type]

        angle = patterns.snap_angle(start_angle, mode)
        x, y = patterns.snap_point_to_grid(start_x, start_y, gstep)
        points = [(x, y)]
        segs_made = 0

        for _ in range(800):
            if segs_made >= max_segs:
                break

            seg_len = random.randint(int(min_len), int(max_len))
            nx, ny = _step_from(x, y, angle, seg_len)
            nx, ny = patterns.snap_point_to_grid(nx, ny, gstep)

            if not _in_bounds(nx, ny, width, height, margin=3):
                break

            avg_cost = road_costs.segment_avg_cost(
                x, y, nx, ny,
                terrain_img, vegetation_img,
                ignore_water=ignore_water,
                ignore_trees=ignore_trees,
            )
            if avg_cost > max_segment_cost:
                break

            if _too_close_parallel(road_type, x, y, nx, ny):
                # try a turn then retry
                if mode == "free":
                    jitter = random.uniform(turn_min, turn_max)
                    if random.random() < 0.5:
                        jitter = -jitter
                    angle = patterns.snap_angle(angle + jitter, mode)
                else:
                    angle = patterns.snap_angle(angle + random.choice([-90, 90, -45, 45]), mode)
                continue

            # commit
            points.append((nx, ny))
            _record_segment(road_type, x, y, nx, ny)
            segs_made += 1

            # maybe lot
            if road_type in ("major", "main") and random.random() < lot_spawn_chance:
                lw = random.randint(lot_min_w, lot_max_w)
                lh = random.randint(lot_min_h, lot_max_h)
                lx, ly = int(nx + 5), int(ny + 5)
                if _in_bounds(lx, ly, width, height, margin=5):
                    road_post.add_parking_lot_rect(lots_img, lx, ly, lw, lh)

            x, y = nx, ny

            # turn for next segment
            if mode == "free":
                jitter = random.uniform(turn_min, turn_max)
                angle = patterns.snap_angle(angle + (jitter if random.random() < 0.5 else -jitter), mode)
            else:
                if mode == "ortho":
                    angle = patterns.snap_angle(angle + random.choice([0, 90, -90]), mode)
                else:  # ortho45
                    angle = patterns.snap_angle(angle + random.choice([0, 45, -45, 90, -90]), mode)

        return points if len(points) > 1 else None

    # ------------------- Pathfinding planner ------------------------------
    def _build_cost_grid(step: int):
        """Downscale terrain/veg into a small integer cost grid."""
        gw = max(1, width // step)
        gh = max(1, height // step)
        grid = [[2 for _ in range(gw)] for __ in range(gh)]
        for gy in range(gh):
            py = min(height - 1, gy * step + step // 2)
            for gx in range(gw):
                px = min(width - 1, gx * step + step // 2)
                c = road_costs.terrain_cost_at(px, py, terrain_img, ignore_water=ignore_water)
                c += road_costs.veg_cost_at(px, py, vegetation_img, ignore_trees=ignore_trees)
                # clamp reasonable range and bias to integers
                grid[gy][gx] = int(max(1.0, min(9999.0, c * 10.0)))
        return grid

    def _astar(grid, start, goal, diag=True):
        gw, gh = len(grid[0]), len(grid)
        sx, sy = start; gx, gy = goal
        if not (0 <= sx < gw and 0 <= sy < gh and 0 <= gx < gw and 0 <= gy < gh):
            return None
        from heapq import heappush, heappop
        def h(a, b):
            ax, ay = a; bx, by = b
            return abs(ax - bx) + abs(ay - by)
        neigh4 = [(1,0),(-1,0),(0,1),(0,-1)]
        neigh8 = neigh4 + [(1,1),(1,-1),(-1,1),(-1,-1)]
        neigh = neigh8 if diag else neigh4
        openh = []
        heappush(openh, (0, (sx, sy)))
        came = {}
        gscore = {(sx, sy): 0}
        while openh:
            _f, cur = heappop(openh)
            if cur == (gx, gy):
                # reconstruct
                path = [cur]
                while cur in came:
                    cur = came[cur]
                    path.append(cur)
                path.reverse()
                return path
            cx, cy = cur
            for dx, dy in neigh:
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < gw and 0 <= ny < gh):
                    continue
                ccost = grid[ny][nx]
                if ccost >= 9999:
                    continue
                step_cost = ccost * (1.4 if dx and dy else 1.0)
                ng = gscore[cur] + step_cost
                if ng < gscore.get((nx, ny), 1e18):
                    gscore[(nx, ny)] = ng
                    came[(nx, ny)] = cur
                    heappush(openh, (ng + h((nx, ny), (gx, gy))*8, (nx, ny)))
        return None

    def _simplify_colinear(pts):
        if len(pts) <= 2:
            return pts
        out = [pts[0]]
        def dir(a,b):
            ax, ay = a; bx, by = b
            dx = 0 if bx==ax else (1 if bx>ax else -1)
            dy = 0 if by==ay else (1 if by>ay else -1)
            return (dx,dy)
        cur_dir = dir(pts[0], pts[1])
        for i in range(1, len(pts)-1):
            nd = dir(pts[i], pts[i+1])
            if nd != cur_dir:
                out.append(pts[i])
                cur_dir = nd
        out.append(pts[-1])
        return out

    def _grid_path_to_pixels(grid_path, step):
        if not grid_path:
            return None
        pts = []
        for gx, gy in grid_path:
            x = gx * step + step//2
            y = gy * step + step//2
            pts.append((x, y))
        pts = _simplify_colinear(pts)
        return pts if len(pts) > 1 else None

    def _add_road_poly(rtype, poly):
        if not poly:
            return
        polylines[rtype].append(poly)
        for i in range(len(poly)-1):
            x1,y1 = poly[i]
            x2,y2 = poly[i+1]
            _record_segment(rtype, x1,y1,x2,y2)

    def _inflate_near_path(grid, path, step, amount=80, radius=2):
        if not path: return
        gw, gh = len(grid[0]), len(grid)
        cells = set()
        for gx, gy in path:
            for dy in range(-radius, radius+1):
                for dx in range(-radius, radius+1):
                    nx, ny = gx+dx, gy+dy
                    if 0 <= nx < gw and 0 <= ny < gh:
                        grid[ny][nx] = min(9999, grid[ny][nx] + amount)

    def _stamp_town_grid(rect, block, rtype="main"):
        x0, y0, x1, y1 = rect
        # clamp
        x0 = max(2, min(width-3, x0)); x1 = max(2, min(width-3, x1))
        y0 = max(2, min(height-3, y0)); y1 = max(2, min(height-3, y1))
        # verticals
        x = x0
        while x <= x1:
            _add_road_poly(rtype, [(x, y0), (x, y1)])
            x += block
        # horizontals
        y = y0
        while y <= y1:
            _add_road_poly(rtype, [(x0, y), (x1, y)])
            y += block

    # ------------------------------------------------------------------
    # Branching pass: try to place N children along ALL segments of parents
    # ------------------------------------------------------------------
    def _spawn_children_along(parent_polys, child_type: str, per_parent: int):
        """Return list of child polylines created."""
        created = []
        if per_parent <= 0:
            return created

        child_mode = type_modes.get(child_type, default_mode)

        for parent in parent_polys:
            remaining = per_parent
            if len(parent) < 2:
                continue

            # walk every segment in this parent
            for i in range(len(parent) - 1):
                if remaining <= 0:
                    break
                x0, y0 = parent[i]
                x1, y1 = parent[i + 1]
                parent_ang = patterns.line_angle_degrees(x0, y0, x1, y1)

                # midpoint of this segment
                mx = (x0 + x1) * 0.5
                my = (y0 + y1) * 0.5

                for a in _choose_branch_angles(parent_ang, child_mode):
                    poly = _make_road(mx, my, a, child_type)
                    if poly:
                        polylines[child_type].append(poly)
                        created.append(poly)
                        remaining -= 1
                        break  # success on this segment, move to next segment

        return created

    # ------------------------------------------------------------------
    # BUILD
    # ------------------------------------------------------------------
    if planner == "path":
        # coarse planning grid
        planner_grid = int(road_conf.get("planner_grid", 4))
        cost_grid = _build_cost_grid(max(1, planner_grid))
        diag = (default_mode != "ortho")

        # Highways: connect opposite edges. Ensure at least one L-R path.
        highways = []
        count_hw = max(1, int(highways_count))
        edge_pairs = []
        # pairs as ((sx,sy),(gx,gy)) in grid coords
        gw, gh = len(cost_grid[0]), len(cost_grid)
        midy = gh//2
        midx = gw//2
        edge_pairs.append(((0, midy), (gw-1, midy)))
        if count_hw >= 2:
            edge_pairs.append(((midx, 0), (midx, gh-1)))
        for i in range(2, count_hw):
            # additional random pairs across opposite sides
            if random.random() < 0.5:
                sy = random.randint(1, gh-2)
                edge_pairs.append(((0, sy), (gw-1, sy)))
            else:
                sx = random.randint(1, gw-2)
                edge_pairs.append(((sx, 0), (sx, gh-1)))

        for (s, g) in edge_pairs:
            path = _astar(cost_grid, s, g, diag=diag)
            if path:
                poly = _grid_path_to_pixels(path, planner_grid)
                if poly:
                    highways.append(poly)
                    _add_road_poly("highway", poly)
                    _inflate_near_path(cost_grid, path, planner_grid, amount=60, radius=2)

        # Town grids
        towns = int(road_conf.get("towns", 1))
        town_block = int(road_conf.get("town_block", 48))
        town_rects = []
        for _ in range(max(0, towns)):
            # pick a low-cost center away from edges
            best = None; bestc = 1e18
            for _i in range(40):
                gx = random.randint(gw//5, gw - gw//5)
                gy = random.randint(gh//5, gh - gh//5)
                c = cost_grid[gy][gx]
                if c < bestc:
                    bestc = c; best = (gx, gy)
            if not best:
                continue
            px = best[0] * planner_grid + planner_grid//2
            py = best[1] * planner_grid + planner_grid//2
            wrect = max(140, min(width//2, town_block*4))
            hrect = max(140, min(height//2, town_block*3))
            rect = (px - wrect//2, py - hrect//2, px + wrect//2, py + hrect//2)
            town_rects.append(rect)
            _stamp_town_grid(rect, town_block, rtype="main")

            # connect town center to nearest highway via major
            if highways:
                # pick nearest point along first highway poly as goal
                hx = highways[0][len(highways[0])//2][0] // planner_grid
                hy = highways[0][len(highways[0])//2][1] // planner_grid
                start = (best[0], best[1])
                goal = (hx, hy)
                path = _astar(cost_grid, start, goal, diag=diag)
                if path:
                    poly = _grid_path_to_pixels(path, planner_grid)
                    _add_road_poly("major", poly)
                    _inflate_near_path(cost_grid, path, planner_grid, amount=50, radius=1)

        # Farm spurs: pick random grass-ish cells
        farm_spurs = int(road_conf.get("farm_spurs", 12))
        for _ in range(max(0, farm_spurs)):
            gx = random.randint(1, gw-2)
            gy = random.randint(1, gh-2)
            # simple heuristic: skip if current cost is high (water)
            if cost_grid[gy][gx] >= 200:
                continue
            # connect to nearest major/highway poly center
            targets = []
            for plist in (polylines["major"], polylines["highway"], polylines["main"]):
                for poly in plist:
                    px, py = poly[len(poly)//2]
                    targets.append((px//planner_grid, py//planner_grid))
            if not targets:
                continue
            tx, ty = min(targets, key=lambda t: (t[0]-gx)**2 + (t[1]-gy)**2)
            path = _astar(cost_grid, (gx, gy), (tx, ty), diag=diag)
            if path:
                poly = _grid_path_to_pixels(path, planner_grid)
                _add_road_poly("side", poly)
                _inflate_near_path(cost_grid, path, planner_grid, amount=40, radius=1)

    elif hierarchical:
        # highways from edges
        highways = []
        for _ in range(highways_count):
            sx, sy, ang = _pick_edge_start(width, height)
            poly = _make_road(sx, sy, ang, "highway")
            if poly:
                polylines["highway"].append(poly)
                highways.append(poly)

        # majors from every highway (spread along whole road)
        majors = _spawn_children_along(highways, "major", majors_per_highway)

        # mains from every major
        mains = _spawn_children_along(majors, "main", mains_per_major)

        # sides from every main
        _ = _spawn_children_along(mains, "side", sides_per_main)

    else:
        # legacy mode: just spawn totals from edges
        def _spawn_total(n, rtype):
            for _ in range(int(n)):
                sx, sy, ang = _pick_edge_start(width, height)
                poly = _make_road(sx, sy, ang, rtype)
                if poly:
                    polylines[rtype].append(poly)
        _spawn_total(legacy_totals["num_highways"], "highway")
        _spawn_total(legacy_totals["num_majors"], "major")
        _spawn_total(legacy_totals["num_mains"], "main")
        _spawn_total(legacy_totals["num_sides"], "side")

    # ------------------------------------------------------------------
    # Draw in Z-order: side -> main -> major -> highway
    # ------------------------------------------------------------------
    draw = ImageDraw.Draw(roads_img)
    for rtype in ("side", "main", "major", "highway"):
        style = ROAD_STYLES[rtype].copy()
        style["width"] = int(road_conf.get(f"{rtype}_width_px", style["width"]))
        for pts in polylines[rtype]:
            draw.line(pts, fill=style["color"] + (255,), width=style["width"], joint="curve")

    # potholes only on asphalt
    pothole_density = float(road_conf.get("pothole_density", 0.02))
    if pothole_density > 0:
        road_post.apply_potholes_noise_jagged_clipped(
            roads_img,
            density=pothole_density,
            seed=(master_seed + seed_offset * 7) & 0xFFFFFFFF,
        )

    # sprinkle transitions
    road_post.sprinkle_dirt_transitions(roads_img)

    # optional dirt path pass
    _ = dirt_paths.generate_paths(width, height, road_conf)

    return roads_img, lots_img
