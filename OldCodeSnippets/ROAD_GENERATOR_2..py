import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk, ImageDraw
import random
import math

# ===================== CONSTANTS =====================
THUMB_SIZE = 256 *2

# PZ-ish colors
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


# ===================== ROAD GEN CORE =====================

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def pick_edge_start(w, h):
    """start somewhere on the border"""
    side = random.choice(["top", "bottom", "left", "right"])
    if side == "top":
        return random.randint(0, w - 1), 1, 90    # down
    if side == "bottom":
        return random.randint(0, w - 1), h - 2, -90  # up
    if side == "left":
        return 1, random.randint(0, h - 1), 0     # right
    return w - 2, random.randint(0, h - 1), 180   # left


def step_from(x, y, angle_deg, length):
    rad = math.radians(angle_deg)
    nx = x + math.cos(rad) * length
    ny = y + math.sin(rad) * length
    return nx, ny


def draw_road(draw, pts, color, width):
    draw.line(pts, fill=color, width=width, joint="curve")


def in_bounds(x, y, w, h, margin=0):
    return margin <= x < (w - margin) and margin <= y < (h - margin)


def apply_potholes(road_img, all_lines, density):
    """Sprinkle potholes on roads."""
    if density <= 0:
        return road_img

    d = ImageDraw.Draw(road_img)
    for points, road_type in all_lines:
        style = ROAD_STYLES[road_type]
        base_col = style["color"]
        # pick closest pothole shade
        if abs(base_col[0] - COLOR_POTHOLE_DARK[0]) < abs(base_col[0] - COLOR_POTHOLE_LIGHT[0]):
            pothole_col = COLOR_POTHOLE_DARK
        else:
            pothole_col = COLOR_POTHOLE_LIGHT

        w = max(1, style["width"] - 2)
        for (x, y) in points:
            if random.random() < density:
                r = max(1, w // 2)
                bbox = [x - r, y - r, x + r, y + r]
                d.ellipse(bbox, fill=pothole_col + (255,))
    return road_img


def generate_roads(w, h, params):
    """
    returns: (roads RGBA image, list_of_lines)
    list_of_lines = [(points, road_type), ...]
    params must contain:
      branch_prob, max_branch_depth,
      {type}_min_len, {type}_max_len,
      ortho, min_turn, max_turn,
      num_highways, num_majors, num_mains, num_sides,
      pothole_density
    """
    road_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(road_img)
    all_lines = []

    # hierarchy for branching
    next_down = {
        "highway": "major",
        "major": "main",
        "main": "side",
        "side": "side",
    }

    def make_road(start_x, start_y, start_angle, road_type, depth=0):
        """recursive road drawer with depth limit"""
        if depth > params["max_branch_depth"]:
            return

        style = ROAD_STYLES[road_type]
        min_len = params[f"{road_type}_min_len"]
        max_len = params[f"{road_type}_max_len"]

        # sanity: make sure min_len <= max_len
        if min_len > max_len:
            min_len, max_len = max_len, min_len

        angle = start_angle
        x, y = start_x, start_y
        points = [(x, y)]

        for _ in range(800):  # hard cap
            seg_len = random.randint(min_len, max_len)
            nx, ny = step_from(x, y, angle, seg_len)

            if not in_bounds(nx, ny, w, h, margin=3):
                break

            # maybe turn
            if not params["ortho"]:
                # smooth random turn
                jitter = random.uniform(params["min_turn"], params["max_turn"])
                if random.random() < 0.5:
                    jitter = -jitter
                angle = (angle + jitter) % 360
            else:
                # 90° grid-ish
                if random.random() < 0.25:
                    pass  # keep direction
                else:
                    angle = (angle + random.choice([-90, 90])) % 360

            points.append((nx, ny))

            # true branching, but guarded by depth and probability
            if depth < params["max_branch_depth"] and random.random() < params["branch_prob"]:
                branch_ang = (angle + random.choice([-90, 90])) % 360
                child_type = next_down[road_type]
                make_road(nx, ny, branch_ang, child_type, depth + 1)

            x, y = nx, ny

        if len(points) > 1:
            draw_road(d, points, style["color"] + (255,), style["width"])
            all_lines.append((points, road_type))

    # top-level spawners
    for _ in range(params["num_highways"]):
        sx, sy, ang = pick_edge_start(w, h)
        make_road(sx, sy, ang, "highway", depth=0)

    for _ in range(params["num_majors"]):
        sx, sy, ang = pick_edge_start(w, h)
        make_road(sx, sy, ang, "major", depth=0)

    for _ in range(params["num_mains"]):
        sx, sy, ang = pick_edge_start(w, h)
        make_road(sx, sy, ang, "main", depth=0)

    for _ in range(params["num_sides"]):
        sx, sy, ang = pick_edge_start(w, h)
        make_road(sx, sy, ang, "side", depth=0)

    # potholes pass
    road_img = apply_potholes(road_img, all_lines, params["pothole_density"])
    return road_img, all_lines


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


# ===================== GUI APP =====================

class RoadApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Road Overlay Tool (fixed recursion)")

        self.terrain_img = None
        self.vegetation_img = None
        self.roads_img = None
        self.veg_mask_img = None

        # GUI vars
        self.num_highways = tk.IntVar(value=2)
        self.num_majors = tk.IntVar(value=4)
        self.num_mains = tk.IntVar(value=8)
        self.num_sides = tk.IntVar(value=12)

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

        self.ortho_only = tk.BooleanVar(value=False)
        self.min_turn = tk.DoubleVar(value=10.0)
        self.max_turn = tk.DoubleVar(value=35.0)

        self.pothole_density = tk.DoubleVar(value=0.02)

        self.build_ui()

    def build_ui(self):
        top = ttk.Frame(self)
        top.pack(side="top", fill="x", padx=5, pady=5)

        # load/export
        ttk.Button(top, text="Load terrain...", command=self.load_terrain).grid(row=0, column=0, padx=3, pady=3)
        ttk.Button(top, text="Load vegetation...", command=self.load_vegetation).grid(row=0, column=1, padx=3, pady=3)
        ttk.Button(top, text="Generate roads", command=self.generate_roads_and_preview).grid(row=0, column=2, padx=3, pady=3)
        ttk.Button(top, text="Export...", command=self.export_all).grid(row=0, column=3, padx=3, pady=3)

        # counts
        row = 1
        ttk.Label(top, text="# Highways").grid(row=row, column=0, sticky="e")
        ttk.Spinbox(top, from_=0, to=50, textvariable=self.num_highways, width=5).grid(row=row, column=1, sticky="w")
        ttk.Label(top, text="# Majors").grid(row=row, column=2, sticky="e")
        ttk.Spinbox(top, from_=0, to=50, textvariable=self.num_majors, width=5).grid(row=row, column=3, sticky="w")
        row += 1
        ttk.Label(top, text="# Mains").grid(row=row, column=0, sticky="e")
        ttk.Spinbox(top, from_=0, to=50, textvariable=self.num_mains, width=5).grid(row=row, column=1, sticky="w")
        ttk.Label(top, text="# Side/Gravel").grid(row=row, column=2, sticky="e")
        ttk.Spinbox(top, from_=0, to=50, textvariable=self.num_sides, width=5).grid(row=row, column=3, sticky="w")
        row += 1

        # branch controls
        ttk.Label(top, text="Branch prob").grid(row=row, column=0, sticky="e")
        ttk.Scale(top, from_=0.0, to=0.5, variable=self.branch_prob,
                  orient="horizontal").grid(row=row, column=1, columnspan=2, sticky="we", padx=3)
        ttk.Label(top, text="Max branch depth").grid(row=row, column=3, sticky="e")
        ttk.Spinbox(top, from_=0, to=6, textvariable=self.max_branch_depth, width=4).grid(row=row, column=4, sticky="w")
        row += 1

        # length rows
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

        # angles
        ttk.Checkbutton(top, text="Orthogonal (90°) only",
                        variable=self.ortho_only,
                        command=self.generate_roads_and_preview).grid(row=row, column=0, columnspan=2, sticky="w")
        ttk.Label(top, text="Min turn").grid(row=row, column=2, sticky="e")
        ttk.Scale(top, from_=0, to=45, variable=self.min_turn, orient="horizontal").grid(row=row, column=3, sticky="we")
        row += 1
        ttk.Label(top, text="Max turn").grid(row=row, column=2, sticky="e")
        ttk.Scale(top, from_=5, to=90, variable=self.max_turn, orient="horizontal").grid(row=row, column=3, sticky="we")
        row += 1

        # potholes
        ttk.Label(top, text="Pothole density").grid(row=row, column=0, sticky="e")
        ttk.Scale(top, from_=0.0, to=0.1, variable=self.pothole_density,
                  orient="horizontal").grid(row=row, column=1, columnspan=3, sticky="we", padx=3)
        row += 1

        # previews
        prev_frame = ttk.Frame(self)
        prev_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)
        self.preview_label = ttk.Label(prev_frame, text="(load terrain to preview)")
        self.preview_label.pack(side="left", padx=5)
        self.preview_veg_label = ttk.Label(prev_frame, text="(veg mask)")
        self.preview_veg_label.pack(side="left", padx=5)

    # ------------- params helper -------------
    def _collect_params(self):
        return {
            "num_highways": self.num_highways.get(),
            "num_majors": self.num_majors.get(),
            "num_mains": self.num_mains.get(),
            "num_sides": self.num_sides.get(),
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
            "ortho": self.ortho_only.get(),
            "min_turn": self.min_turn.get(),
            "max_turn": self.max_turn.get(),
            "pothole_density": self.pothole_density.get(),
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

    # ------------- generate + preview -------------
    def generate_roads_and_preview(self):
        if self.terrain_img is None:
            return
        w, h = self.terrain_img.size
        params = self._collect_params()
        self.roads_img, _ = generate_roads(w, h, params)
        self.veg_mask_img = dilate_roads(self.roads_img, extra=3, color=(0, 0, 0))

        # terrain composite
        comp = self.terrain_img.copy().convert("RGBA")
        comp.alpha_composite(self.roads_img)
        thumb = comp.resize((THUMB_SIZE, THUMB_SIZE), Image.NEAREST)
        tkimg = ImageTk.PhotoImage(thumb)
        self.preview_label.config(image=tkimg)
        self.preview_label.image = tkimg

        # veg mask (for editor)
        vegthumb = self.veg_mask_img.resize((THUMB_SIZE, THUMB_SIZE), Image.NEAREST)
        tkveg = ImageTk.PhotoImage(vegthumb)
        self.preview_veg_label.config(image=tkveg)
        self.preview_veg_label.image = tkveg

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

        # vegetation masked
        if self.vegetation_img is not None:
            veg = self.vegetation_img.copy()
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
