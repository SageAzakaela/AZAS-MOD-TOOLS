import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk, ImageDraw
import random
import math

# try to import winsound for SFX (works on Windows)
try:
    import winsound
except ImportError:
    winsound = None

# ===================== CONSTANTS =====================
THUMB_SIZE = 256 * 2  # preview size

# road surface colors
COLOR_HIGHWAY = (100, 100, 100)      # dark asphalt
COLOR_MAJOR   = (120, 120, 120)      # medium asphalt
COLOR_MAIN    = (165, 160, 140)      # light asphalt
COLOR_SIDE    = (120,  70,  20)      # dirt-ish

COLOR_POTHOLE_DARK  = (110, 100, 100)
COLOR_POTHOLE_LIGHT = (130, 120, 120)

ROAD_STYLES = {
    "highway": {"color": COLOR_HIGHWAY, "width": 7},
    "major":   {"color": COLOR_MAJOR,   "width": 6},
    "main":    {"color": COLOR_MAIN,    "width": 6},
    "side":    {"color": COLOR_SIDE,    "width": 3},
}

# terrain-ish colors from the terrain generator
TERRAIN_COST_TABLE = [
    ((0, 138, 255), 12, 9999),    # water -> very expensive
    ((90, 100, 35),  12, 2.5),    # dark grass
    ((117, 117, 47), 12, 2.0),    # medium grass
    ((145, 135, 60), 12, 1.7),    # light grass
    ((120, 70, 20),  15, 1.2),    # dirt-ish
    ((210, 200, 120), 15, 1.3),   # sand-ish
]

# vegetation colors that count as “thick trees”
DENSE_VEG_COLORS = [
    (255, 0, 0),      # trees
    (200, 0, 0),      # dense trees
    (255, 0, 255),    # dense bushes
    (100, 0, 200),    # bushes + grass
]


# ===================== SMALL HELPERS =====================
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def pick_edge_start(w, h):
    """start somewhere on the border, and aim inward-ish"""
    side = random.choice(["top", "bottom", "left", "right"])
    if side == "top":
        return random.randint(0, w - 1), 1, 90
    if side == "bottom":
        return random.randint(0, w - 1), h - 2, -90
    if side == "left":
        return 1, random.randint(0, h - 1), 0
    return w - 2, random.randint(0, h - 1), 180


def step_from(x, y, angle_deg, length):
    rad = math.radians(angle_deg)
    nx = x + math.cos(rad) * length
    ny = y + math.sin(rad) * length
    return nx, ny


def draw_road(draw, pts, color, width):
    draw.line(pts, fill=color, width=width, joint="curve")


def in_bounds(x, y, w, h, margin=0):
    return margin <= x < (w - margin) and margin <= y < (h - margin)


def color_distance(c1, c2):
    return abs(c1[0]-c2[0]) + abs(c1[1]-c2[1]) + abs(c1[2]-c2[2])


def terrain_cost_at(px, py, terrain_img, ignore_water=False):
    """look up cost from terrain pixel"""
    if terrain_img is None:
        return 1.5  # neutral
    w, h = terrain_img.size
    if not (0 <= px < w and 0 <= py < h):
        return 9999
    rgb = terrain_img.getpixel((px, py))
    if len(rgb) == 4:
        rgb = rgb[:3]

    best_cost = 2.0
    for base_col, tol, cost in TERRAIN_COST_TABLE:
        if color_distance(rgb, base_col) <= tol:
            if ignore_water and cost >= 9999:
                return 1.5  # pretend water is fine
            return cost
    return best_cost


def veg_cost_at(px, py, vegetation_img, ignore_thick_trees=False):
    if vegetation_img is None:
        return 0.0
    w, h = vegetation_img.size
    if not (0 <= px < w and 0 <= py < h):
        return 0.0
    rgb = vegetation_img.getpixel((px, py))
    if len(rgb) == 4:
        rgb = rgb[:3]
    for base in DENSE_VEG_COLORS:
        if color_distance(rgb, base) < 60:
            if ignore_thick_trees:
                return 0.0
            return 1.2
    return 0.0


def segment_avg_cost(x1, y1, x2, y2, terrain_img, vegetation_img,
                     ignore_water=False, ignore_trees=False, samples=6):
    total = 0.0
    for i in range(samples):
        t = i / max(1, (samples - 1))
        sx = int(x1 + (x2 - x1) * t)
        sy = int(y1 + (y2 - y1) * t)
        c = terrain_cost_at(sx, sy, terrain_img, ignore_water=ignore_water)
        c += veg_cost_at(sx, sy, vegetation_img, ignore_thick_trees=ignore_trees)
        total += c
    return total / samples


def snap_angle(angle, mode):
    """mode: 'free', 'ortho', 'ortho45'"""
    if mode == "free":
        return angle % 360
    elif mode == "ortho":
        return round(angle / 90.0) * 90 % 360
    elif mode == "ortho45":
        return round(angle / 45.0) * 45 % 360
    return angle % 360


def apply_potholes_noise_jagged(road_img, density=0.02, seed=None):
    """
    Better potholes:
    - only on asphalt (not dirt)
    - jagged-ish small polygons
    - dark-on-dark, light-on-light
    - finer pattern
    """
    if density <= 0:
        return road_img
    if seed is not None:
        rnd = random.Random(seed)
    else:
        rnd = random

    w, h = road_img.size
    pix = road_img.load()
    d = ImageDraw.Draw(road_img)

    def is_dirt(c):
        return color_distance(c, COLOR_SIDE) < 20

    for y in range(h):
        for x in range(w):
            r, g, b, a = pix[x, y]
            if a == 0:
                continue
            if is_dirt((r, g, b)):
                continue  # no potholes on dirt

            n = (math.sin(x * 0.18) + math.cos(y * 0.21)) * 0.25 + 0.5
            chance = density * n
            if rnd.random() < chance:
                base_luma = (r + g + b) // 3
                if base_luma < 120:
                    pc = COLOR_POTHOLE_LIGHT
                else:
                    pc = COLOR_POTHOLE_DARK
                pts = []
                rad = rnd.randint(1, 3)
                sides = rnd.randint(4, 7)
                for i in range(sides):
                    ang = (2 * math.pi * i) / sides
                    rr = rad + rnd.uniform(-0.8, 0.6)
                    px = x + math.cos(ang) * rr
                    py = y + math.sin(ang) * rr
                    pts.append((px, py))
                d.polygon(pts, fill=pc + (255,))
    return road_img


def dilate_roads(road_img, extra=3, color=(0, 0, 0)):
    """make a thick black mask for vegetation"""
    w, h = road_img.size
    mask = Image.new("RGB", (w, h), (0, 0, 0))
    road_pix = road_img.load()
    mask_draw = ImageDraw.Draw(mask)
    for x in range(w):
        for y in range(h):
            if road_pix[x, y][3] > 0:
                mask_draw.rectangle(
                    [x - extra, y - extra, x + extra, y + extra],
                    fill=color
                )
    return mask


def pick_town_spot(w, h, terrain_img):
    best = None
    best_cost = 9999
    for _ in range(40):
        x = random.randint(int(w * 0.1), int(w * 0.9))
        y = random.randint(int(h * 0.1), int(h * 0.9))
        c = terrain_cost_at(x, y, terrain_img)
        if c < best_cost and c < 9999:
            best = (x, y)
            best_cost = c
    if best is None:
        return w // 2, h // 2
    return best


def add_parking_lots(road_img, all_lines, params):
    d = ImageDraw.Draw(road_img)
    w, h = road_img.size

    for points, road_type in all_lines:
        if len(points) < 2:
            continue
        if random.random() > params["lot_spawn_chance"]:
            continue

        idx = random.randint(0, len(points) - 2)
        (x1, y1) = points[idx]
        (x2, y2) = points[idx + 1]

        dx = x2 - x1
        dy = y2 - y1
        seg_len = math.hypot(dx, dy)
        if seg_len == 0:
            continue

        nx = -dy / seg_len
        ny = dx / seg_len

        wmin = params["lot_min_w"]
        wmax = params["lot_max_w"]
        hmin = params["lot_min_h"]
        hmax = params["lot_max_h"]
        lot_w = random.randint(wmin, wmax)
        lot_h = random.randint(hmin, hmax)

        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2

        ox = mx + nx * (ROAD_STYLES[road_type]["width"] + 2)
        oy = my + ny * (ROAD_STYLES[road_type]["width"] + 2)

        x0 = int(ox)
        y0 = int(oy)
        x1r = int(ox + lot_w)
        y1r = int(oy + lot_h)

        if x0 < 0 or y0 < 0 or x1r >= w or y1r >= h:
            continue

        d.rectangle([x0, y0, x1r, y1r], fill=COLOR_MAIN + (255,))

    return road_img


# ===================== ROAD GEN CORE =====================
def generate_roads(w, h, params, terrain_img=None, vegetation_img=None):
    road_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(road_img)
    all_lines = []

    angle_mode = params["angle_mode"]  # 'free', 'ortho', 'ortho45'

    next_down = {
        "highway": "major",
        "major": "main",
        "main": "side",
        "side": "side",
    }

    def make_road(start_x, start_y, start_angle, road_type, depth=0):
        if depth > params["max_branch_depth"]:
            return

        style = ROAD_STYLES[road_type]
        min_len = params[f"{road_type}_min_len"]
        max_len = params[f"{road_type}_max_len"]
        if min_len > max_len:
            min_len, max_len = max_len, min_len

        angle = snap_angle(start_angle, angle_mode)
        x, y = start_x, start_y
        points = [(x, y)]

        for _ in range(600):
            seg_len = random.randint(min_len, max_len)
            nx, ny = step_from(x, y, angle, seg_len)

            if not in_bounds(nx, ny, w, h, margin=3):
                break

            avg_c = segment_avg_cost(
                x, y, nx, ny,
                terrain_img,
                vegetation_img,
                ignore_water=params["ignore_water"],
                ignore_trees=params["ignore_trees"],
                samples=5,
            )
            if avg_c > params["max_segment_cost"]:
                break

            if angle_mode == "free":
                jitter = random.uniform(params["min_turn"], params["max_turn"])
                if random.random() < 0.5:
                    jitter = -jitter
                angle = (angle + jitter) % 360
            else:
                if random.random() < 0.3:
                    pass
                else:
                    if angle_mode == "ortho":
                        angle = snap_angle(angle + random.choice([-90, 90]), angle_mode)
                    else:  # ortho45
                        angle = snap_angle(angle + random.choice([-90, -45, 45, 90]), angle_mode)

            angle = snap_angle(angle, angle_mode)
            points.append((nx, ny))

            if depth < params["max_branch_depth"] and random.random() < params["branch_prob"]:
                if angle_mode == "free":
                    branch_ang = (angle + random.choice([-90, 90])) % 360
                else:
                    branch_ang = snap_angle(angle + random.choice([-90, 90]), angle_mode)
                child_type = next_down[road_type]
                make_road(nx, ny, branch_ang, child_type, depth + 1)

            x, y = nx, ny

        if len(points) > 1:
            draw_road(d, points, style["color"] + (255,), style["width"])
            all_lines.append((points, road_type))

    # highways from edges
    for _ in range(params["num_highways"]):
        sx, sy, ang = pick_edge_start(w, h)
        make_road(sx, sy, ang, "highway", depth=0)

    # towns
    for _ in range(params["num_towns"]):
        tx, ty = pick_town_spot(w, h, terrain_img)
        block = 30
        local_roads = [
            ((tx - block, ty), (tx + block, ty)),
            ((tx, ty - block), (tx, ty + block)),
        ]
        for (x1, y1), (x2, y2) in local_roads:
            draw_road(d, [(x1, y1), (x2, y2)], COLOR_MAIN + (255,), 5)
            all_lines.append(([(x1, y1), (x2, y2)], "main"))
        for _ in range(random.randint(2, 4)):
            ang = random.randint(0, 359)
            make_road(tx, ty, ang, "major", depth=1)

    # more roads from edges
    for _ in range(params["num_majors"]):
        sx, sy, ang = pick_edge_start(w, h)
        make_road(sx, sy, ang, "major", depth=0)
    for _ in range(params["num_mains"]):
        sx, sy, ang = pick_edge_start(w, h)
        make_road(sx, sy, ang, "main", depth=0)
    for _ in range(params["num_sides"]):
        sx, sy, ang = pick_edge_start(w, h)
        make_road(sx, sy, ang, "side", depth=0)

    # parking lots / foundations
    road_img = add_parking_lots(road_img, all_lines, params)

    # pothole pass
    road_img = apply_potholes_noise_jagged(road_img, params["pothole_density"])

    return road_img, all_lines


def make_checkerboard(w, h, cell=8):
    img = Image.new("RGB", (w, h), (200, 200, 200))
    d = ImageDraw.Draw(img)
    c1 = (200, 200, 200)
    c2 = (160, 160, 160)
    for y in range(0, h, cell):
        for x in range(0, w, cell):
            if (x // cell + y // cell) % 2 == 0:
                d.rectangle([x, y, x+cell, y+cell], fill=c1)
            else:
                d.rectangle([x, y, x+cell, y+cell], fill=c2)
    return img


# ===================== GUI APP =====================
class RoadApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Road Overlay Tool (with transparent export + sfx)")

        self.terrain_img = None
        self.vegetation_img = None
        self.roads_img = None
        self.veg_mask_img = None
        self.sfx_path = None  # user-loaded sound

        # GUI vars
        self.num_highways = tk.IntVar(value=2)
        self.num_majors = tk.IntVar(value=3)
        self.num_mains = tk.IntVar(value=6)
        self.num_sides = tk.IntVar(value=10)
        self.num_towns = tk.IntVar(value=3)

        self.branch_prob = tk.DoubleVar(value=0.15)
        self.max_branch_depth = tk.IntVar(value=3)

        self.highway_min_len = tk.IntVar(value=120)
        self.highway_max_len = tk.IntVar(value=240)
        self.major_min_len = tk.IntVar(value=90)
        self.major_max_len = tk.IntVar(value=180)
        self.main_min_len  = tk.IntVar(value=70)
        self.main_max_len  = tk.IntVar(value=140)
        self.side_min_len  = tk.IntVar(value=40)
        self.side_max_len  = tk.IntVar(value=90)

        self.angle_mode = tk.StringVar(value="free")  # free / ortho / ortho45
        self.min_turn = tk.StringVar(value="10.0")
        self.max_turn = tk.StringVar(value="35.0")

        self.pothole_density = tk.DoubleVar(value=0.02)
        self.max_segment_cost = tk.DoubleVar(value=3.0)

        # parking lots
        self.lot_spawn_chance = tk.DoubleVar(value=0.25)
        self.lot_min_w = tk.IntVar(value=16)
        self.lot_max_w = tk.IntVar(value=40)
        self.lot_min_h = tk.IntVar(value=16)
        self.lot_max_h = tk.IntVar(value=40)

        # ignore flags
        self.ignore_water = tk.BooleanVar(value=False)
        self.ignore_trees = tk.BooleanVar(value=False)

        self.build_ui()

    def build_ui(self):
        top = ttk.Frame(self)
        top.pack(side="top", fill="x", padx=5, pady=5)

        # load/export
        ttk.Button(top, text="Load terrain...", command=self.load_terrain).grid(row=0, column=0, padx=3, pady=3)
        ttk.Button(top, text="Load vegetation...", command=self.load_vegetation).grid(row=0, column=1, padx=3, pady=3)
        ttk.Button(top, text="Generate roads", command=self.on_generate_pressed).grid(row=0, column=2, padx=3, pady=3)
        ttk.Button(top, text="Export...", command=self.export_all).grid(row=0, column=3, padx=3, pady=3)
        ttk.Button(top, text="Load sound...", command=self.load_sound).grid(row=0, column=4, padx=3, pady=3)

        row = 1
        ttk.Label(top, text="# Highways").grid(row=row, column=0, sticky="e")
        ttk.Spinbox(top, from_=0, to=50, textvariable=self.num_highways, width=5,
                    command=self.generate_roads_and_preview).grid(row=row, column=1, sticky="w")
        ttk.Label(top, text="# Towns").grid(row=row, column=2, sticky="e")
        ttk.Spinbox(top, from_=0, to=20, textvariable=self.num_towns, width=5,
                    command=self.generate_roads_and_preview).grid(row=row, column=3, sticky="w")
        row += 1

        ttk.Label(top, text="# Majors").grid(row=row, column=0, sticky="e")
        ttk.Spinbox(top, from_=0, to=50, textvariable=self.num_majors, width=5,
                    command=self.generate_roads_and_preview).grid(row=row, column=1, sticky="w")
        ttk.Label(top, text="# Mains").grid(row=row, column=2, sticky="e")
        ttk.Spinbox(top, from_=0, to=50, textvariable=self.num_mains, width=5,
                    command=self.generate_roads_and_preview).grid(row=row, column=3, sticky="w")
        row += 1

        ttk.Label(top, text="# Side/Gravel").grid(row=row, column=0, sticky="e")
        ttk.Spinbox(top, from_=0, to=50, textvariable=self.num_sides, width=5,
                    command=self.generate_roads_and_preview).grid(row=row, column=1, sticky="w")
        row += 1

        # angle mode
        ttk.Label(top, text="Angle mode").grid(row=row, column=0, sticky="e")
        ttk.Combobox(top, textvariable=self.angle_mode,
                     values=["free", "ortho", "ortho45"], width=8).grid(row=row, column=1, sticky="w")
        ttk.Label(top, text="Min turn").grid(row=row, column=2, sticky="e")
        tk.Entry(top, textvariable=self.min_turn, width=6).grid(row=row, column=3, sticky="w")
        row += 1
        ttk.Label(top, text="Max turn").grid(row=row, column=2, sticky="e")
        tk.Entry(top, textvariable=self.max_turn, width=6).grid(row=row, column=3, sticky="w")
        row += 1

        # branch
        ttk.Label(top, text="Branch prob").grid(row=row, column=0, sticky="e")
        ttk.Scale(top, from_=0.0, to=0.5, variable=self.branch_prob,
                  orient="horizontal", command=lambda e: self.generate_roads_and_preview()
                  ).grid(row=row, column=1, columnspan=2, sticky="we", padx=3)
        ttk.Label(top, text="Max branch depth").grid(row=row, column=3, sticky="e")
        ttk.Spinbox(top, from_=0, to=6, textvariable=self.max_branch_depth, width=4,
                    command=self.generate_roads_and_preview).grid(row=row, column=4, sticky="w")
        row += 1

        # road lengths
        def add_len_row(label, vmin, vmax, r):
            ttk.Label(top, text=label+" len").grid(row=r, column=0, sticky="e")
            f = ttk.Frame(top)
            f.grid(row=r, column=1, columnspan=4, sticky="we", pady=1)
            ttk.Label(f, text="min").pack(side="left")
            ttk.Entry(f, textvariable=vmin, width=5).pack(side="left")
            ttk.Label(f, text="max").pack(side="left")
            ttk.Entry(f, textvariable=vmax, width=5).pack(side="left")

        add_len_row("Highway", self.highway_min_len, self.highway_max_len, row); row += 1
        add_len_row("Major",   self.major_min_len,   self.major_max_len,   row); row += 1
        add_len_row("Main",    self.main_min_len,    self.main_max_len,    row); row += 1
        add_len_row("Side",    self.side_min_len,    self.side_max_len,    row); row += 1

        # cost cap
        ttk.Label(top, text="Max segment cost").grid(row=row, column=0, sticky="e")
        ttk.Scale(top, from_=1.0, to=6.0, variable=self.max_segment_cost,
                  orient="horizontal", command=lambda e: self.generate_roads_and_preview()
                  ).grid(row=row, column=1, columnspan=3, sticky="we", padx=3)
        row += 1

        # potholes
        ttk.Label(top, text="Pothole density").grid(row=row, column=0, sticky="e")
        ttk.Scale(top, from_=0.0, to=0.1, variable=self.pothole_density,
                  orient="horizontal", command=lambda e: self.generate_roads_and_preview()
                  ).grid(row=row, column=1, columnspan=3, sticky="we", padx=3)
        row += 1

        # parking lots
        ttk.Label(top, text="Lot spawn chance").grid(row=row, column=0, sticky="e")
        ttk.Scale(top, from_=0.0, to=1.0, variable=self.lot_spawn_chance,
                  orient="horizontal", command=lambda e: self.generate_roads_and_preview()
                  ).grid(row=row, column=1, columnspan=3, sticky="we", padx=3)
        row += 1

        ttk.Label(top, text="Lot min W/H").grid(row=row, column=0, sticky="e")
        tk.Entry(top, textvariable=self.lot_min_w, width=5).grid(row=row, column=1, sticky="w")
        tk.Entry(top, textvariable=self.lot_min_h, width=5).grid(row=row, column=2, sticky="w")
        row += 1
        ttk.Label(top, text="Lot max W/H").grid(row=row, column=0, sticky="e")
        tk.Entry(top, textvariable=self.lot_max_w, width=5).grid(row=row, column=1, sticky="w")
        tk.Entry(top, textvariable=self.lot_max_h, width=5).grid(row=row, column=2, sticky="w")
        row += 1

        # ignore flags
        ttk.Checkbutton(top, text="Ignore water", variable=self.ignore_water,
                        command=self.generate_roads_and_preview).grid(row=row, column=0, sticky="w")
        ttk.Checkbutton(top, text="Ignore thick trees", variable=self.ignore_trees,
                        command=self.generate_roads_and_preview).grid(row=row, column=1, sticky="w")
        row += 1

        # previews
        prev_frame = ttk.Frame(self)
        prev_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)

        self.preview_label = ttk.Label(prev_frame, text="(terrain+roads)")
        self.preview_label.pack(side="left", padx=5)

        self.preview_veg_label = ttk.Label(prev_frame, text="(veg+black roads)")
        self.preview_veg_label.pack(side="left", padx=5)

        self.preview_roads_label = ttk.Label(prev_frame, text="(roads only)")
        self.preview_roads_label.pack(side="left", padx=5)

    # ------------- sound -------------
    def load_sound(self):
        path = "A_cute_little_guitar-1762560304328.wav"
        if path:
            self.sfx_path = path

    def play_sound(self):
        if self.sfx_path and winsound is not None:
            # winsound is happiest with wav
            try:
                winsound.PlaySound(self.sfx_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except RuntimeError:
                pass

    # ------------- params helper -------------
    def _collect_params(self):
        try:
            min_turn_val = float(self.min_turn.get())
        except ValueError:
            min_turn_val = 10.0
        try:
            max_turn_val = float(self.max_turn.get())
        except ValueError:
            max_turn_val = 35.0

        return {
            "num_highways": self.num_highways.get(),
            "num_majors": self.num_majors.get(),
            "num_mains": self.num_mains.get(),
            "num_sides": self.num_sides.get(),
            "num_towns": self.num_towns.get(),
            "branch_prob": self.branch_prob.get(),
            "max_branch_depth": self.max_branch_depth.get(),
            "highway_min_len": self.highway_min_len.get(),
            "highway_max_len": self.highway_max_len.get(),
            "major_min_len": self.major_min_len.get(),
            "major_max_len": self.major_max_len.get(),
            "main_min_len": self.main_min_len.get(),
            "main_max_len": self.main_max_len.get(),
            "side_min_len": self.side_min_len.get(),
            "side_max_len": self.side_max_len.get(),
            "angle_mode": self.angle_mode.get(),
            "min_turn": min_turn_val,
            "max_turn": max_turn_val,
            "pothole_density": self.pothole_density.get(),
            "max_segment_cost": self.max_segment_cost.get(),
            "lot_spawn_chance": self.lot_spawn_chance.get(),
            "lot_min_w": self.lot_min_w.get(),
            "lot_max_w": self.lot_max_w.get(),
            "lot_min_h": self.lot_min_h.get(),
            "lot_max_h": self.lot_max_h.get(),
            "ignore_water": self.ignore_water.get(),
            "ignore_trees": self.ignore_trees.get(),
        }

    # ------------- load -------------
    def load_terrain(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.bmp")])
        if not path:
            return
        self.terrain_img = Image.open(path).convert("RGB")
        self.generate_roads_and_preview()

    def load_vegetation(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.bmp")])
        if not path:
            return
        self.vegetation_img = Image.open(path).convert("RGB")
        self.generate_roads_and_preview()

    def on_generate_pressed(self):
        self.play_sound()
        self.generate_roads_and_preview()

    # ------------- generate + preview -------------
    def generate_roads_and_preview(self):
        if self.terrain_img is None:
            return
        w, h = self.terrain_img.size
        params = self._collect_params()
        self.roads_img, _ = generate_roads(
            w, h, params,
            terrain_img=self.terrain_img,
            vegetation_img=self.vegetation_img
        )
        self.veg_mask_img = dilate_roads(self.roads_img, extra=3, color=(0, 0, 0))

        # terrain composite
        comp = self.terrain_img.copy().convert("RGBA")
        comp.alpha_composite(self.roads_img)
        thumb = comp.resize((THUMB_SIZE, THUMB_SIZE), Image.NEAREST)
        tkimg = ImageTk.PhotoImage(thumb)
        self.preview_label.config(image=tkimg)
        self.preview_label.image = tkimg

        # veg overlay preview
        if self.vegetation_img is not None:
            veg_prev = self.vegetation_img.copy().convert("RGB")
        else:
            veg_prev = self.terrain_img.copy().convert("RGB")

        mpix = self.veg_mask_img.load()
        vpix = veg_prev.load()
        for x in range(w):
            for y in range(h):
                if mpix[x, y] != (0, 0, 0):
                    vpix[x, y] = (0, 0, 0)
        vegthumb = veg_prev.resize((THUMB_SIZE, THUMB_SIZE), Image.NEAREST)
        tkveg = ImageTk.PhotoImage(vegthumb)
        self.preview_veg_label.config(image=tkveg)
        self.preview_veg_label.image = tkveg

        # roads-only preview with checkerboard
        cb = make_checkerboard(w, h, cell=8).convert("RGBA")
        roads_only_prev = cb.copy()
        roads_only_prev.alpha_composite(self.roads_img)
        roads_thumb = roads_only_prev.resize((THUMB_SIZE, THUMB_SIZE), Image.NEAREST)
        tkroads = ImageTk.PhotoImage(roads_thumb)
        self.preview_roads_label.config(image=tkroads)
        self.preview_roads_label.image = tkroads

    # ------------- export -------------
    def export_all(self):
        if self.terrain_img is None or self.roads_img is None:
            return

        # terrain+roads
        comp = self.terrain_img.copy().convert("RGBA")
        comp.alpha_composite(self.roads_img)
        out1 = filedialog.asksaveasfilename(defaultextension=".png",
                                            title="Save terrain+roads as...",
                                            filetypes=[("PNG", "*.png")])
        if out1:
            comp.save(out1)

        # roads-only transparent
        out_roads = filedialog.asksaveasfilename(defaultextension=".png",
                                                 title="Save roads (transparent) as...",
                                                 filetypes=[("PNG", "*.png")])
        if out_roads:
            self.roads_img.save(out_roads)

        # vegetation masked
        if self.vegetation_img is not None:
            veg = self.vegetation_img.copy().convert("RGB")
            m = self.veg_mask_img
            vpix = veg.load()
            mpix = m.load()
            w, h = veg.size
            for x in range(w):
                for y in range(h):
                    if mpix[x, y] != (0, 0, 0):
                        vpix[x, y] = (0, 0, 0)
            out2 = filedialog.asksaveasfilename(defaultextension=".png",
                                                title="Save vegetation (roads black) as...",
                                                filetypes=[("PNG", "*.png")])
            if out2:
                veg.save(out2)
        else:
            out3 = filedialog.asksaveasfilename(defaultextension=".png",
                                                title="Save road mask as...",
                                                filetypes=[("PNG", "*.png")])
            if out3:
                self.veg_mask_img.save(out3)


if __name__ == "__main__":
    app = RoadApp()
    app.mainloop()
