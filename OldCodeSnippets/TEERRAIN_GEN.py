import numpy as np
from PIL import Image, ImageTk
import noise
import tkinter as tk
from tkinter import ttk, filedialog
import random

# ====== CONFIG ======
CELL_SIZE = 300          # each cell is 300x300
THUMB_SIZE = 256         # preview size
DEFAULT_CELLS_WIDE = 3
DEFAULT_CELLS_HIGH = 3

# "natural" ranges
SCALE_MIN, SCALE_MAX, SCALE_DEFAULT = 30, 120, 60
OCT_MIN, OCT_MAX, OCT_DEFAULT = 2, 8, 6
PERSIST_MIN, PERSIST_MAX, PERSIST_DEFAULT = 0.3, 0.7, 0.5
LAC_MIN, LAC_MAX, LAC_DEFAULT = 1.5, 2.5, 2.0

# thresholds (normalized)
WATER_MIN, WATER_MAX, WATER_DEFAULT = 0.10, 0.35, 0.25
DARK_MIN, DARK_MAX, DARK_DEFAULT = 0.35, 0.55, 0.45
MED_MIN, MED_MAX, MED_DEFAULT = 0.55, 0.80, 0.70

THRESH_MARGIN = 0.02  # how far apart they must stay


class TerrainGeneratorApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Terrain & Vegetation Generator")

        # vars
        self.cells_wide_var = tk.IntVar(value=DEFAULT_CELLS_WIDE)
        self.cells_high_var = tk.IntVar(value=DEFAULT_CELLS_HIGH)

        self.scale_var = tk.DoubleVar(value=SCALE_DEFAULT)
        self.octaves_var = tk.IntVar(value=OCT_DEFAULT)
        self.persistence_var = tk.DoubleVar(value=PERSIST_DEFAULT)
        self.lacunarity_var = tk.DoubleVar(value=LAC_DEFAULT)

        self.water_threshold_var = tk.DoubleVar(value=WATER_DEFAULT)
        self.dark_grass_threshold_var = tk.DoubleVar(value=DARK_DEFAULT)
        self.medium_grass_threshold_var = tk.DoubleVar(value=MED_DEFAULT)

        # last + previous full images
        self.last_terrain_image = None
        self.last_vegetation_image = None
        self.prev_terrain_image = None
        self.prev_vegetation_image = None

        self.create_widgets()
        self.bind_traces()
        # initial preview
        self.update_preview()

    def create_widgets(self):
        # --- top row: cells ---
        ttk.Label(self, text="Cells Wide:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        cells_wide_spin = ttk.Spinbox(self, from_=1, to=20, textvariable=self.cells_wide_var, width=5,
                                      command=self.update_preview)
        cells_wide_spin.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(self, text="Cells High:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        cells_high_spin = ttk.Spinbox(self, from_=1, to=20, textvariable=self.cells_high_var, width=5,
                                      command=self.update_preview)
        cells_high_spin.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        # --- Noise controls ---
        # scale
        ttk.Label(self, text="Scale:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        ttk.Scale(self, from_=SCALE_MIN, to=SCALE_MAX, orient="horizontal",
                  variable=self.scale_var,
                  command=lambda v: self.update_preview()).grid(row=1, column=1, columnspan=3, sticky="we", padx=5)

        # octaves
        ttk.Label(self, text="Octaves:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        ttk.Scale(self, from_=OCT_MIN, to=OCT_MAX, orient="horizontal",
                  variable=self.octaves_var,
                  command=lambda v: self.update_preview()).grid(row=2, column=1, columnspan=3, sticky="we", padx=5)

        # persistence
        ttk.Label(self, text="Persistence:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        ttk.Scale(self, from_=PERSIST_MIN, to=PERSIST_MAX, orient="horizontal",
                  variable=self.persistence_var,
                  command=lambda v: self.update_preview()).grid(row=3, column=1, columnspan=3, sticky="we", padx=5)

        # lacunarity
        ttk.Label(self, text="Lacunarity:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
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
        ttk.Label(self, text="Seed:").grid(row=8, column=0, padx=5, pady=5, sticky="e")
        self.seed_entry = ttk.Entry(self)
        self.seed_entry.grid(row=8, column=1, columnspan=3, padx=5, pady=5, sticky="we")
        self.seed_entry.bind("<KeyRelease>", lambda e: self.update_preview())

        # buttons
        ttk.Button(self, text="Generate (Full)", command=self.generate_full).grid(row=9, column=0, padx=5, pady=5)
        ttk.Button(self, text="Export Images...", command=self.export_images).grid(row=9, column=1, padx=5, pady=5)
        ttk.Button(self, text="Randomize", command=self.randomize_all).grid(row=9, column=2, padx=5, pady=5)
        ttk.Button(self, text="Show Previous", command=self.show_previous).grid(row=9, column=3, padx=5, pady=5)

        # preview frame (side-by-side)
        preview_frame = ttk.Frame(self)
        preview_frame.grid(row=10, column=0, columnspan=4, sticky="we", padx=5, pady=5)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.columnconfigure(1, weight=1)

        self.preview_terrain_label = ttk.Label(preview_frame, text="terrain preview")
        self.preview_terrain_label.grid(row=0, column=0, padx=5, pady=5)

        self.preview_vegetation_label = ttk.Label(preview_frame, text="vegetation preview")
        self.preview_vegetation_label.grid(row=0, column=1, padx=5, pady=5)

        # make main columns stretch
        for c in range(4):
            self.columnconfigure(c, weight=1)

    def bind_traces(self):
        # nothing fancy right now, just hook if needed later
        pass

    # ====== RELATIONSHIP CONSTRAINTS ======
    def on_threshold_change(self, which, value):
        w = self.water_threshold_var.get()
        d = self.dark_grass_threshold_var.get()
        m = self.medium_grass_threshold_var.get()

        if which == "water":
            # water must be < dark - margin
            if value > d - THRESH_MARGIN:
                self.dark_grass_threshold_var.set(min(d + 0.0, value + THRESH_MARGIN))
            self.water_threshold_var.set(value)
        elif which == "dark":
            # dark must be > water + margin and < medium - margin
            if value < w + THRESH_MARGIN:
                value = w + THRESH_MARGIN
            if value > m - THRESH_MARGIN:
                value = m - THRESH_MARGIN
            self.dark_grass_threshold_var.set(value)
        elif which == "medium":
            # medium must be > dark + margin
            if value < d + THRESH_MARGIN:
                value = d + THRESH_MARGIN
            self.medium_grass_threshold_var.set(value)

        # after enforcing, update preview
        self.update_preview()

    # ====== PREVIEW (small, fast) ======
    def update_preview(self):
        # small preview uses fixed size
        width = THUMB_SIZE
        height = THUMB_SIZE

        params = self.get_params()
        terrain_img, vegetation_img = generate_terrain_and_vegetation(
            width, height,
            params["scale"], params["octaves"], params["persistence"], params["lacunarity"],
            params["water"], params["dark"], params["medium"],
            seed=params["seed"]
        )

        # show on labels
        self.set_preview(self.preview_terrain_label, terrain_img)
        self.set_preview(self.preview_vegetation_label, vegetation_img)

    def set_preview(self, label, pil_image):
        # ensure fits exactly
        img = pil_image.copy()
        img = img.resize((THUMB_SIZE, THUMB_SIZE))
        photo = ImageTk.PhotoImage(img)
        label.config(image=photo)
        label.image = photo

    # ====== FULL GENERATION ======
    def generate_full(self):
        params = self.get_params()
        # true size from cells
        width = params["cells_wide"] * CELL_SIZE
        height = params["cells_high"] * CELL_SIZE

        # move current into previous
        self.prev_terrain_image = self.last_terrain_image
        self.prev_vegetation_image = self.last_vegetation_image

        terrain_img, vegetation_img = generate_terrain_and_vegetation(
            width, height,
            params["scale"], params["octaves"], params["persistence"], params["lacunarity"],
            params["water"], params["dark"], params["medium"],
            seed=params["seed"]
        )

        self.last_terrain_image = terrain_img
        self.last_vegetation_image = vegetation_img

        # show in separate windows
        self.show_in_window(terrain_img, "Terrain (full)")
        self.show_in_window(vegetation_img, "Vegetation (full)")

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

    # ====== EXPORT ======
    def export_images(self):
        if self.last_terrain_image is None or self.last_vegetation_image is None:
            return

        terrain_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png")],
            title="Save terrain image as..."
        )
        if terrain_path:
            self.last_terrain_image.save(terrain_path)

        vegetation_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png")],
            title="Save vegetation image as..."
        )
        if vegetation_path:
            self.last_vegetation_image.save(vegetation_path)

    # ====== RANDOMIZE ======
    def randomize_all(self):
        # noise params
        self.scale_var.set(random.uniform(SCALE_MIN, SCALE_MAX))
        self.octaves_var.set(random.randint(OCT_MIN, OCT_MAX))
        self.persistence_var.set(random.uniform(PERSIST_MIN, PERSIST_MAX))
        self.lacunarity_var.set(random.uniform(LAC_MIN, LAC_MAX))

        # thresholds in correct order
        w = random.uniform(WATER_MIN, WATER_MAX)
        d = random.uniform(max(DARK_MIN, w + THRESH_MARGIN), DARK_MAX)
        m = random.uniform(max(MED_MIN, d + THRESH_MARGIN), MED_MAX)

        self.water_threshold_var.set(w)
        self.dark_grass_threshold_var.set(d)
        self.medium_grass_threshold_var.set(m)

        # seed
        rand_seed = random.randint(1, 9999)
        self.seed_entry.delete(0, tk.END)
        self.seed_entry.insert(0, str(rand_seed))

        # update preview
        self.update_preview()

    # ====== SHOW PREVIOUS ======
    def show_previous(self):
        if self.prev_terrain_image is not None:
            self.show_in_window(self.prev_terrain_image, "Previous Terrain")
        if self.prev_vegetation_image is not None:
            self.show_in_window(self.prev_vegetation_image, "Previous Vegetation")

    # ====== HELPER ======
    def get_params(self):
        # seed handling / normalize
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
        }


# ====== NOISE / MAP FUNCTIONS ======
def generate_perlin_noise(width, height, scale, octaves, persistence, lacunarity, seed):
    noise_map = np.zeros((width, height))
    if seed is None:
        seed = random.randint(1, 10000)
    base = int(seed) % 1024  # clamp so long seeds don't get weird

    for i in range(width):
        for j in range(height):
            noise_map[i][j] = noise.pnoise2(
                i / scale,
                j / scale,
                octaves=octaves,
                persistence=persistence,
                lacunarity=lacunarity,
                # if you want perfect tiling, you can uncomment:
                # repeatx=width,
                # repeaty=height,
                base=base
            )
    return noise_map


def generate_vegetation_map(width, height, scale, octaves, persistence, lacunarity,
                            water_threshold, dark_grass_threshold, medium_grass_threshold, seed=None):
    if seed is None:
        seed = random.randint(1, 10000)

    vegetation_noise = generate_perlin_noise(
        width, height, scale, octaves, persistence, lacunarity, seed=seed + 1
    )

    vmin = np.min(vegetation_noise)
    vmax = np.max(vegetation_noise)
    vrange = vmax - vmin
    normalized = (vegetation_noise - vmin) / vrange

    image = Image.new("RGB", (width, height))
    colors = [
        (0, 0, 0),
        (0, 128, 0),
        (0, 255, 0)
    ]

    for x in range(width):
        for y in range(height):
            v = normalized[x][y]
            if v < 0.3:
                color = colors[0]
            elif v < 0.6:
                color = colors[1]
            else:
                color = colors[2]
            image.putpixel((x, y), color)

    return image


def generate_terrain_map(width, height, scale, octaves, persistence, lacunarity,
                         water_threshold, dark_grass_threshold, medium_grass_threshold, seed=None):
    if seed is None:
        seed = random.randint(1, 10000)

    terrain_noise = generate_perlin_noise(
        width, height, scale, octaves, persistence, lacunarity, seed
    )

    tmin = np.min(terrain_noise)
    tmax = np.max(terrain_noise)
    trange = tmax - tmin
    normalized = (terrain_noise - tmin) / trange

    image = Image.new("RGB", (width, height))
    colors = [
        (0, 138, 255),   # water
        (90, 100, 35),   # dark grass
        (117, 117, 47),  # medium grass
        (145, 135, 60)   # light grass
    ]

    for x in range(width):
        for y in range(height):
            t = normalized[x][y]
            if t < water_threshold:
                color = colors[0]
            elif t < dark_grass_threshold:
                color = colors[1]
            elif t < medium_grass_threshold:
                color = colors[2]
            else:
                color = colors[3]
            image.putpixel((x, y), color)

    return image, normalized


def generate_terrain_and_vegetation(width, height, scale, octaves, persistence, lacunarity,
                                    water_threshold, dark_grass_threshold, medium_grass_threshold, seed=None):
    terrain_map, _ = generate_terrain_map(
        width, height, scale, octaves, persistence, lacunarity,
        water_threshold, dark_grass_threshold, medium_grass_threshold, seed
    )
    vegetation_map = generate_vegetation_map(
        width, height, scale, octaves, persistence, lacunarity,
        water_threshold, dark_grass_threshold, medium_grass_threshold, seed
    )
    return terrain_map, vegetation_map


if __name__ == "__main__":
    app = TerrainGeneratorApp()
    app.mainloop()
