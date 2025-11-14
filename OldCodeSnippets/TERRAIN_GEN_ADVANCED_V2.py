import numpy as np
from PIL import Image, ImageTk
import noise
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser
import random

# ====== CONFIG / CONSTANTS ======
CELL_SIZE = 300
THUMB_SIZE = 256
DEFAULT_CELLS_WIDE = 3
DEFAULT_CELLS_HIGH = 3

# "natural" ranges for TERRAIN
SCALE_MIN, SCALE_MAX, SCALE_DEFAULT = 30, 120, 60
OCT_MIN, OCT_MAX, OCT_DEFAULT = 2, 8, 6
PERSIST_MIN, PERSIST_MAX, PERSIST_DEFAULT = 0.3, 0.7, 0.5
LAC_MIN, LAC_MAX, LAC_DEFAULT = 1.5, 2.5, 2.0

# we'll use slightly wider ranges for vegetation (you can tune)
VEG_SCALE_MIN, VEG_SCALE_MAX, VEG_SCALE_DEFAULT = 20, 140, 50
VEG_OCT_MIN, VEG_OCT_MAX, VEG_OCT_DEFAULT = 2, 8, 5
VEG_PERSIST_MIN, VEG_PERSIST_MAX, VEG_PERSIST_DEFAULT = 0.3, 0.7, 0.55
VEG_LAC_MIN, VEG_LAC_MAX, VEG_LAC_DEFAULT = 1.5, 2.5, 2.0

# thresholds (normalized)
WATER_MIN, WATER_MAX, WATER_DEFAULT = 0.10, 0.35, 0.25
DARK_MIN, DARK_MAX, DARK_DEFAULT = 0.35, 0.55, 0.45
MED_MIN, MED_MAX, MED_DEFAULT = 0.55, 0.80, 0.70
THRESH_MARGIN = 0.02  # minimum gap between water < dark < medium

# default colors (you tuned these — I’ll leave them as hex, but parser will accept RGB too)
DEFAULT_LAYER_CONFIG = {
    "terrain": {
        "seed": 1,
        "layers": [
            {"name": "Water",       "key": "water",       "color": "#008AFF"},
            {"name": "Dark Grass",  "key": "dark_grass",  "color": "#5A6423"},
            {"name": "Medium Grass","key": "medium_grass","color": "#75752F"},
            {"name": "Light Grass", "key": "light_grass", "color": "#91873c"},
            {"name": "Dirt Grass",  "key": "dirt_grass",  "color": "#784614"},
            {"name": "Dirt",        "key": "dirt",        "color": "#784614"},
            {"name": "Sand",        "key": "sand",        "color": "#d2c880"},
        ]
    },
    "vegetation": {
        "seed": 5,
        "layers": [
            {"name": "Grass + Few Trees",     "key": "few_trees",      "color": "#008000"},
            {"name": "Dense Trees",           "key": "dense_trees",    "color": "#c80000"},
            {"name": "Trees",                 "key": "trees",          "color": "#ff0000"},
            {"name": "Dense Bushes & Grass",  "key": "dense_bushes",   "color": "#ff00ff"},
            {"name": "Bushes + Grass",        "key": "bushes_grass",   "color": "#6400c8"},
            {"name": "Long Grass",            "key": "long_grass",     "color": "#00ff00"},
            {"name": "Short Grass",           "key": "short_grass",    "color": "#00fa00"},
            {"name": "Grass + Few Trees",     "key": "fir_trees",      "color": "#008000"},
        ]
    },
    "water": {
        "seed": 7,
        "layers": []
    }
}


class TerrainGeneratorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Terrain & Vegetation Generator")

        import copy
        self.layer_config = copy.deepcopy(DEFAULT_LAYER_CONFIG)

        # main vars
        self.cells_wide_var = tk.IntVar(value=DEFAULT_CELLS_WIDE)
        self.cells_high_var = tk.IntVar(value=DEFAULT_CELLS_HIGH)

        # TERRAIN noise vars
        self.scale_var = tk.DoubleVar(value=SCALE_DEFAULT)
        self.octaves_var = tk.IntVar(value=OCT_DEFAULT)
        self.persistence_var = tk.DoubleVar(value=PERSIST_DEFAULT)
        self.lacunarity_var = tk.DoubleVar(value=LAC_DEFAULT)

        # VEGETATION noise vars
        self.veg_scale_var = tk.DoubleVar(value=VEG_SCALE_DEFAULT)
        self.veg_octaves_var = tk.IntVar(value=VEG_OCT_DEFAULT)
        self.veg_persistence_var = tk.DoubleVar(value=VEG_PERSIST_DEFAULT)
        self.veg_lacunarity_var = tk.DoubleVar(value=VEG_LAC_DEFAULT)

        # terrain thresholds
        self.water_threshold_var = tk.DoubleVar(value=WATER_DEFAULT)
        self.dark_grass_threshold_var = tk.DoubleVar(value=DARK_DEFAULT)
        self.medium_grass_threshold_var = tk.DoubleVar(value=MED_DEFAULT)

        self.seed_entry = None

        # last + previous full images
        self.last_terrain_image = None
        self.last_vegetation_image = None
        self.prev_terrain_image = None
        self.prev_vegetation_image = None

        self.create_widgets()
        self.update_preview()

    def create_widgets(self):
        # --- cells ---
        ttk.Label(self, text="Cells Wide:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        ttk.Spinbox(self, from_=1, to=20, textvariable=self.cells_wide_var, width=5,
                    command=self.update_preview).grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(self, text="Cells High:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        ttk.Spinbox(self, from_=1, to=20, textvariable=self.cells_high_var, width=5,
                    command=self.update_preview).grid(row=0, column=3, padx=5, pady=5, sticky="w")

        # --- TERRAIN noise sliders ---
        ttk.Label(self, text="Terrain Scale:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        ttk.Scale(self, from_=SCALE_MIN, to=SCALE_MAX, orient="horizontal",
                  variable=self.scale_var,
                  command=lambda v: self.update_preview()).grid(row=1, column=1, columnspan=3, sticky="we", padx=5)

        ttk.Label(self, text="Terrain Octaves:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        ttk.Scale(self, from_=OCT_MIN, to=OCT_MAX, orient="horizontal",
                  variable=self.octaves_var,
                  command=lambda v: self.update_preview()).grid(row=2, column=1, columnspan=3, sticky="we", padx=5)

        ttk.Label(self, text="Terrain Persistence:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        ttk.Scale(self, from_=PERSIST_MIN, to=PERSIST_MAX, orient="horizontal",
                  variable=self.persistence_var,
                  command=lambda v: self.update_preview()).grid(row=3, column=1, columnspan=3, sticky="we", padx=5)

        ttk.Label(self, text="Terrain Lacunarity:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
        ttk.Scale(self, from_=LAC_MIN, to=LAC_MAX, orient="horizontal",
                  variable=self.lacunarity_var,
                  command=lambda v: self.update_preview()).grid(row=4, column=1, columnspan=3, sticky="we", padx=5)

        # --- thresholds ---
        ttk.Label(self, text="Water Threshold:").grid(row=5, column=0, padx=5, pady=5, sticky="e")
        ttk.Scale(self, from_=WATER_MIN, to=WATER_MAX, orient="horizontal",
                  variable=self.water_threshold_var,
                  command=lambda v: self.on_threshold_change("water", float(v))).grid(row=5, column=1, columnspan=3, sticky="we", padx=5)

        ttk.Label(self, text="Dark Grass Threshold:").grid(row=6, column=0, padx=5, pady=5, sticky="e")
        ttk.Scale(self, from_=DARK_MIN, to=DARK_MAX, orient="horizontal",
                  variable=self.dark_grass_threshold_var,
                  command=lambda v: self.on_threshold_change("dark", float(v))).grid(row=6, column=1, columnspan=3, sticky="we", padx=5)

        ttk.Label(self, text="Medium Grass Threshold:").grid(row=7, column=0, padx=5, pady=5, sticky="e")
        ttk.Scale(self, from_=MED_MIN, to=MED_MAX, orient="horizontal",
                  variable=self.medium_grass_threshold_var,
                  command=lambda v: self.on_threshold_change("medium", float(v))).grid(row=7, column=1, columnspan=3, sticky="we", padx=5)

        # seed
        ttk.Label(self, text="Base Seed:").grid(row=8, column=0, padx=5, pady=5, sticky="e")
        self.seed_entry = ttk.Entry(self)
        self.seed_entry.grid(row=8, column=1, columnspan=3, padx=5, pady=5, sticky="we")
        self.seed_entry.bind("<KeyRelease>", lambda e: self.update_preview())

        # --- VEGETATION noise sliders ---
        ttk.Label(self, text="Veg Scale:").grid(row=9, column=0, padx=5, pady=5, sticky="e")
        ttk.Scale(self, from_=VEG_SCALE_MIN, to=VEG_SCALE_MAX, orient="horizontal",
                  variable=self.veg_scale_var,
                  command=lambda v: self.update_preview()).grid(row=9, column=1, columnspan=3, sticky="we", padx=5)

        ttk.Label(self, text="Veg Octaves:").grid(row=10, column=0, padx=5, pady=5, sticky="e")
        ttk.Scale(self, from_=VEG_OCT_MIN, to=VEG_OCT_MAX, orient="horizontal",
                  variable=self.veg_octaves_var,
                  command=lambda v: self.update_preview()).grid(row=10, column=1, columnspan=3, sticky="we", padx=5)

        ttk.Label(self, text="Veg Persistence:").grid(row=11, column=0, padx=5, pady=5, sticky="e")
        ttk.Scale(self, from_=VEG_PERSIST_MIN, to=VEG_PERSIST_MAX, orient="horizontal",
                  variable=self.veg_persistence_var,
                  command=lambda v: self.update_preview()).grid(row=11, column=1, columnspan=3, sticky="we", padx=5)

        ttk.Label(self, text="Veg Lacunarity:").grid(row=12, column=0, padx=5, pady=5, sticky="e")
        ttk.Scale(self, from_=VEG_LAC_MIN, to=VEG_LAC_MAX, orient="horizontal",
                  variable=self.veg_lacunarity_var,
                  command=lambda v: self.update_preview()).grid(row=12, column=1, columnspan=3, sticky="we", padx=5)

        # buttons
        ttk.Button(self, text="Generate (Full)", command=self.generate_full).grid(row=13, column=0, padx=5, pady=5)
        ttk.Button(self, text="Export Images...", command=self.export_images).grid(row=13, column=1, padx=5, pady=5)
        ttk.Button(self, text="Randomize", command=self.randomize_all).grid(row=13, column=2, padx=5, pady=5)
        ttk.Button(self, text="Show Previous", command=self.show_previous).grid(row=13, column=3, padx=5, pady=5)
        ttk.Button(self, text="Layers / Colors…", command=self.open_layer_editor).grid(row=13, column=4, padx=5, pady=5)

        # preview frame
        preview_frame = ttk.Frame(self)
        preview_frame.grid(row=14, column=0, columnspan=5, sticky="we", padx=5, pady=5)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.columnconfigure(1, weight=1)

        self.preview_terrain_label = ttk.Label(preview_frame, text="terrain preview")
        self.preview_terrain_label.grid(row=0, column=0, padx=5, pady=5)
        self.preview_vegetation_label = ttk.Label(preview_frame, text="vegetation preview")
        self.preview_vegetation_label.grid(row=0, column=1, padx=5, pady=5)

        for c in range(5):
            self.columnconfigure(c, weight=1)

    # ====== Threshold relationships ======
    def on_threshold_change(self, which, value):
        w = self.water_threshold_var.get()
        d = self.dark_grass_threshold_var.get()
        m = self.medium_grass_threshold_var.get()

        if which == "water":
            if value > d - THRESH_MARGIN:
                d = value + THRESH_MARGIN
                self.dark_grass_threshold_var.set(d)
            self.water_threshold_var.set(value)
        elif which == "dark":
            if value < w + THRESH_MARGIN:
                value = w + THRESH_MARGIN
            if value > m - THRESH_MARGIN:
                value = m - THRESH_MARGIN
            self.dark_grass_threshold_var.set(value)
        elif which == "medium":
            if value < d + THRESH_MARGIN:
                value = d + THRESH_MARGIN
            self.medium_grass_threshold_var.set(value)

        self.update_preview()

    # ====== Preview ======
    def update_preview(self):
        params = self.get_params()
        terrain_img, veg_img = generate_terrain_and_vegetation(
            THUMB_SIZE, THUMB_SIZE,
            # terrain params
            params["scale"], params["octaves"], params["persistence"], params["lacunarity"],
            params["water"], params["dark"], params["medium"],
            # base seed
            seed=params["seed"],
            layer_config=self.layer_config,
            # vegetation params
            veg_scale=params["veg_scale"],
            veg_octaves=params["veg_octaves"],
            veg_persistence=params["veg_persistence"],
            veg_lacunarity=params["veg_lacunarity"],
        )
        self.set_preview(self.preview_terrain_label, terrain_img)
        self.set_preview(self.preview_vegetation_label, veg_img)

    def set_preview(self, label, img):
        img2 = img.resize((THUMB_SIZE, THUMB_SIZE))
        photo = ImageTk.PhotoImage(img2)
        label.config(image=photo)
        label.image = photo

    # ====== Full generation ======
    def generate_full(self):
        params = self.get_params()
        width = params["cells_wide"] * CELL_SIZE
        height = params["cells_high"] * CELL_SIZE

        # store previous
        self.prev_terrain_image = self.last_terrain_image
        self.prev_vegetation_image = self.last_vegetation_image

        terrain_img, veg_img = generate_terrain_and_vegetation(
            width, height,
            params["scale"], params["octaves"], params["persistence"], params["lacunarity"],
            params["water"], params["dark"], params["medium"],
            seed=params["seed"],
            layer_config=self.layer_config,
            veg_scale=params["veg_scale"],
            veg_octaves=params["veg_octaves"],
            veg_persistence=params["veg_persistence"],
            veg_lacunarity=params["veg_lacunarity"],
        )

        self.last_terrain_image = terrain_img
        self.last_vegetation_image = veg_img

        self.show_in_window(terrain_img, "Terrain (full)")
        self.show_in_window(veg_img, "Vegetation (full)")

    def show_in_window(self, pil_image, title="Image"):
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("500x500")

        hbar = tk.Scrollbar(win, orient="horizontal")
        hbar.pack(side="bottom", fill="x")
        vbar = tk.Scrollbar(win, orient="vertical")
        vbar.pack(side="right", fill="y")

        canvas = tk.Canvas(win, xscrollcommand=hbar.set, yscrollcommand=vbar.set, bg="black")
        canvas.pack(side="left", fill="both", expand=True)

        hbar.config(command=canvas.xview)
        vbar.config(command=canvas.yview)

        photo = ImageTk.PhotoImage(pil_image)
        win.image = photo
        canvas.create_image(0, 0, anchor="nw", image=photo)
        canvas.config(scrollregion=(0, 0, pil_image.width, pil_image.height))

    # ====== Export ======
    def export_images(self):
        if self.last_terrain_image is None or self.last_vegetation_image is None:
            return
        path1 = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")],
                                             title="Save terrain image as...")
        if path1:
            self.last_terrain_image.save(path1)
        path2 = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")],
                                             title="Save vegetation image as...")
        if path2:
            self.last_vegetation_image.save(path2)

    # ====== Randomize ======
    def randomize_all(self):
        # terrain
        self.scale_var.set(random.uniform(SCALE_MIN, SCALE_MAX))
        self.octaves_var.set(random.randint(OCT_MIN, OCT_MAX))
        self.persistence_var.set(random.uniform(PERSIST_MIN, PERSIST_MAX))
        self.lacunarity_var.set(random.uniform(LAC_MIN, LAC_MAX))
        # vegetation
        self.veg_scale_var.set(random.uniform(VEG_SCALE_MIN, VEG_SCALE_MAX))
        self.veg_octaves_var.set(random.randint(VEG_OCT_MIN, VEG_OCT_MAX))
        self.veg_persistence_var.set(random.uniform(VEG_PERSIST_MIN, VEG_PERSIST_MAX))
        self.veg_lacunarity_var.set(random.uniform(VEG_LAC_MIN, VEG_LAC_MAX))

        # thresholds
        w = random.uniform(WATER_MIN, WATER_MAX)
        d = random.uniform(max(DARK_MIN, w + THRESH_MARGIN), DARK_MAX)
        m = random.uniform(max(MED_MIN, d + THRESH_MARGIN), MED_MAX)
        self.water_threshold_var.set(w)
        self.dark_grass_threshold_var.set(d)
        self.medium_grass_threshold_var.set(m)

        # base seed
        rand_seed = random.randint(1, 9999)
        self.seed_entry.delete(0, tk.END)
        self.seed_entry.insert(0, str(rand_seed))

        self.update_preview()

    # ====== Show previous ======
    def show_previous(self):
        if self.prev_terrain_image is not None:
            self.show_in_window(self.prev_terrain_image, "Previous Terrain")
        if self.prev_vegetation_image is not None:
            self.show_in_window(self.prev_vegetation_image, "Previous Vegetation")

    # ====== Layer editor ======
    def open_layer_editor(self):
        win = tk.Toplevel(self)
        win.title("Layer & Color Editor")

        row = 0
        for group_name, group in self.layer_config.items():
            ttk.Label(win, text=group_name.upper(), font=("Arial", 10, "bold")).grid(row=row, column=0, sticky="w", pady=(5,2))
            # seed for group
            seed_var = tk.StringVar(value=str(group.get("seed", 0)))
            def make_save_seed(gname, svar):
                return lambda e=None: self._save_group_seed(gname, svar.get())
            seed_entry = ttk.Entry(win, textvariable=seed_var, width=8)
            seed_entry.grid(row=row, column=1, padx=5)
            seed_entry.bind("<FocusOut>", make_save_seed(group_name, seed_var))
            row += 1
            for layer in group.get("layers", []):
                ttk.Label(win, text="  " + layer["name"]).grid(row=row, column=0, sticky="w", padx=10)
                btn = ttk.Button(win, text=str(layer["color"]), width=16,
                                 command=lambda l=layer, w=win: self.change_layer_color(l, w))
                btn.grid(row=row, column=1, padx=5, pady=2)
                row += 1

    def _save_group_seed(self, group_name, val):
        try:
            self.layer_config[group_name]["seed"] = int(val)
        except ValueError:
            self.layer_config[group_name]["seed"] = 0
        self.update_preview()

    def change_layer_color(self, layer, win):
        # colorchooser returns hex, we store it, but our parser accepts both
        color = colorchooser.askcolor(color=layer["color"], parent=win)[1]
        if color:
            layer["color"] = color
            self.update_preview()

    # ====== helper ======
    def get_params(self):
        seed_text = self.seed_entry.get().strip()
        if seed_text == "":
            seed_val = None
        else:
            try:
                seed_val = int(seed_text)
            except ValueError:
                seed_val = abs(hash(seed_text)) % 10000

        return {
            "cells_wide": max(1, self.cells_wide_var.get()),
            "cells_high": max(1, self.cells_high_var.get()),
            "scale": self.scale_var.get(),
            "octaves": int(self.octaves_var.get()),
            "persistence": self.persistence_var.get(),
            "lacunarity": self.lacunarity_var.get(),
            "water": self.water_threshold_var.get(),
            "dark": self.dark_grass_threshold_var.get(),
            "medium": self.medium_grass_threshold_var.get(),
            "seed": seed_val,
            # vegetation params
            "veg_scale": self.veg_scale_var.get(),
            "veg_octaves": int(self.veg_octaves_var.get()),
            "veg_persistence": self.veg_persistence_var.get(),
            "veg_lacunarity": self.veg_lacunarity_var.get(),
        }


# ====== NOISE / MAP FUNCS ======

def generate_perlin_noise(width, height, scale, octaves, persistence, lacunarity, seed):
    noise_map = np.zeros((width, height))
    if seed is None:
        seed = random.randint(1, 10000)
    base = int(seed) % 1024
    for i in range(width):
        for j in range(height):
            noise_map[i][j] = noise.pnoise2(
                i / scale,
                j / scale,
                octaves=octaves,
                persistence=persistence,
                lacunarity=lacunarity,
                base=base
            )
    return noise_map


def generate_terrain_map(width, height, scale, octaves, persistence, lacunarity,
                         water_threshold, dark_threshold, medium_threshold,
                         seed=None, layer_config=None):
    if layer_config is None:
        layer_config = DEFAULT_LAYER_CONFIG

    terrain_group_seed = layer_config.get("terrain", {}).get("seed", 0)
    real_seed = (seed or 0) + terrain_group_seed

    terrain_noise = generate_perlin_noise(width, height, scale, octaves, persistence, lacunarity, real_seed)
    tmin = np.min(terrain_noise)
    tmax = np.max(terrain_noise)
    trange = tmax - tmin
    normalized = (terrain_noise - tmin) / trange

    img = Image.new("RGB", (width, height))

    t_layers = layer_config["terrain"]["layers"]
    clr_water = _get_color(t_layers, "water")
    clr_dark = _get_color(t_layers, "dark_grass")
    clr_med = _get_color(t_layers, "medium_grass")
    clr_light = _get_color(t_layers, "light_grass")
    clr_dirt_grass = _get_color(t_layers, "dirt_grass")
    clr_dirt = _get_color(t_layers, "dirt")
    clr_sand = _get_color(t_layers, "sand")

    extra1 = min(1.0, medium_threshold + 0.10)
    extra2 = min(1.0, medium_threshold + 0.18)
    extra3 = min(1.0, medium_threshold + 0.26)

    for x in range(width):
        for y in range(height):
            v = normalized[x][y]
            if v < water_threshold:
                color = clr_water
            elif v < dark_threshold:
                color = clr_dark
            elif v < medium_threshold:
                color = clr_med
            elif v < extra1:
                color = clr_light
            elif v < extra2:
                color = clr_dirt_grass
            elif v < extra3:
                color = clr_dirt
            else:
                color = clr_sand
            img.putpixel((x, y), color)

    return img, normalized


def generate_vegetation_map(width, height,
                            veg_scale, veg_octaves, veg_persistence, veg_lacunarity,
                            seed=None, layer_config=None):
    if layer_config is None:
        layer_config = DEFAULT_LAYER_CONFIG

    veg_group_seed = layer_config.get("vegetation", {}).get("seed", 0)
    real_seed = (seed or 0) + veg_group_seed

    veg_noise = generate_perlin_noise(width, height,
                                      veg_scale, veg_octaves, veg_persistence, veg_lacunarity,
                                      real_seed)
    vmin = np.min(veg_noise)
    vmax = np.max(veg_noise)
    vrange = vmax - vmin
    normalized = (veg_noise - vmin) / vrange

    img = Image.new("RGB", (width, height))

    v_layers = layer_config["vegetation"]["layers"]
    for x in range(width):
        for y in range(height):
            v = normalized[x][y]
            idx = int(v * len(v_layers))
            if idx >= len(v_layers):
                idx = len(v_layers) - 1
            layer = v_layers[idx]
            img.putpixel((x, y), _parse_color(layer["color"]))

    return img


def generate_terrain_and_vegetation(width, height, scale, octaves, persistence, lacunarity,
                                    water_threshold, dark_threshold, medium_threshold,
                                    seed=None, layer_config=None,
                                    veg_scale=None, veg_octaves=None, veg_persistence=None, veg_lacunarity=None):
    terrain_img, _ = generate_terrain_map(
        width, height,
        scale, octaves, persistence, lacunarity,
        water_threshold, dark_threshold, medium_threshold,
        seed=seed, layer_config=layer_config
    )
    vegetation_img = generate_vegetation_map(
        width, height,
        veg_scale, veg_octaves, veg_persistence, veg_lacunarity,
        seed=seed, layer_config=layer_config
    )
    return terrain_img, vegetation_img


# ====== small helpers ======
def _parse_color(c):
    """
    Accepts '#RRGGBB', '(r,g,b)', 'r,g,b', or (r,g,b)
    Returns (r,g,b)
    """
    if isinstance(c, tuple) and len(c) == 3:
        return c
    if isinstance(c, str):
        c = c.strip()
        if c.startswith("#"):
            c = c.lstrip("#")
            return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
        # maybe "r,g,b" or "(r,g,b)"
        c = c.replace("(", "").replace(")", "")
        parts = [p.strip() for p in c.split(",")]
        if len(parts) == 3:
            try:
                return (int(parts[0]), int(parts[1]), int(parts[2]))
            except ValueError:
                pass
    return (255, 255, 255)


def _get_color(layer_list, key):
    for layer in layer_list:
        if layer["key"] == key:
            return _parse_color(layer["color"])
    return (255, 255, 255)


if __name__ == "__main__":
    app = TerrainGeneratorApp()
    app.mainloop()
