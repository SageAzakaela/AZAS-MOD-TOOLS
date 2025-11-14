import copy
import tkinter as tk
from tkinter import ttk

def _label(p, t): return tk.Label(p, text=t, bg="#121212", fg="white")

def _layer(name, color, threshold, scale, octaves, terrain_in=None):
    layer = {
        "name": name,
        "color": list(color),
        "threshold": threshold,
        "scale": scale,
        "octaves": octaves,
    }
    if terrain_in:
        layer["terrain_in"] = terrain_in
    return layer

LAYER_PRESETS = {
    "overgrown": [
        _layer("grass_base", (0, 128, 0), 0.45, 70, 4, ["light_grass", "med_grass", "dark_grass"]),
        _layer("light_long_grass", (0, 255, 0), 0.58, 60, 4, ["light_grass", "med_grass"]),
        _layer("trees_grass", (127, 0, 0), 0.62, 55, 5, ["med_grass", "dark_grass"]),
        _layer("dense_trees_grass", (200, 0, 0), 0.72, 55, 5, ["dark_grass"]),
        _layer("dense_forest", (255, 0, 0), 0.80, 50, 5, ["dark_grass"]),
        _layer("bushes", (255, 0, 255), 0.86, 48, 4, ["light_grass", "med_grass"]),
    ],
    "rural": [
        _layer("wild_grass", (60, 160, 40), 0.38, 75, 4, ["light_grass", "med_grass"]),
        _layer("meadow_flowers", (240, 200, 160), 0.60, 55, 4, ["light_grass", "med_grass"]),
        _layer("scattered_trees", (90, 30, 0), 0.70, 60, 4, ["med_grass", "dark_grass"]),
    ],
    "suburban": [
        _layer("lush_lawn", (45, 150, 60), 0.35, 65, 3, ["light_grass"]),
        _layer("fringe_trees", (120, 40, 10), 0.65, 50, 4, ["light_grass", "med_grass"]),
        _layer("shrubs", (255, 0, 255), 0.55, 45, 4, ["light_grass", "med_grass"]),
        _layer("dead_corn", (255, 128, 0), 0.78, 62, 3, ["light_grass", "dirt"]),
    ],
    "meadow": [
        _layer("meadow_grass", (50, 180, 80), 0.40, 68, 4, ["light_grass", "med_grass"]),
        _layer("wildflowers", (255, 190, 200), 0.58, 58, 5, ["light_grass", "med_grass"]),
        _layer("spring_shade", (180, 90, 200), 0.72, 52, 5, ["med_grass"]),
    ],
    "marsh": [
        _layer("reed_field", (40, 130, 70), 0.32, 45, 5, ["water", "sand", "dirt"]),
        _layer("moss", (80, 140, 70), 0.52, 60, 4, ["water", "dirt"]),
        _layer("algae", (30, 90, 30), 0.68, 48, 3, ["water"]),
    ],
    "taiga": [
        _layer("taiga_floor", (20, 60, 30), 0.38, 55, 5, ["dark_grass", "med_grass"]),
        _layer("fir_trees", (64, 0, 0), 0.58, 52, 6, ["dark_grass"]),
        _layer("leaf_litter", (20, 50, 35), 0.72, 48, 4, ["dark_grass"]),
    ],
    "rocky_plateau": [
        _layer("sparse_grass", (90, 120, 80), 0.50, 80, 3, ["dirt", "sand", "gravel_dirt"]),
        _layer("stone", (145, 135, 60), 0.75, 40, 3, ["dirt", "light_grass"]),
        _layer("dusty_shrub", (180, 130, 100), 0.88, 35, 2, ["dirt"]),
    ],
    "neon_dune": [
        _layer("glow_sand", (255, 180, 0), 0.40, 35, 2, ["sand"]),
        _layer("electric_grass", (100, 255, 200), 0.60, 40, 3, ["sand"]),
        _layer("strange_flora", (255, 50, 200), 0.80, 30, 3, ["sand"]),
    ],
    "mystic_swamp": [
        _layer("brackish_moss", (45, 85, 60), 0.35, 50, 3, ["water", "dark_grass"]),
        _layer("psychedelic_mists", (140, 40, 185), 0.60, 42, 4, ["water"]),
        _layer("dead_florals", (170, 70, 70), 0.77, 38, 3, ["water", "dirt"]),
    ],
}

def _layers_for(name):
    return copy.deepcopy(LAYER_PRESETS.get(name, []))

class VegetationTab(tk.Frame):
    PRESETS = {
        "overgrown": dict(scale=50, octaves=5, persistence=0.55, lacunarity=2.0,
                          respect_terrain=True, mode="mixed", mixed_wetness=0.6,
                          use_layers=True, layers=_layers_for("overgrown")),
        "rural":     dict(scale=60, octaves=4, persistence=0.52, lacunarity=2.0,
                          respect_terrain=True, mode="mixed", mixed_wetness=0.5,
                          use_layers=True, layers=_layers_for("rural")),
        "suburban":  dict(scale=45, octaves=6, persistence=0.50, lacunarity=2.2,
                          respect_terrain=True, mode="mixed", mixed_wetness=0.45,
                          use_layers=True, layers=_layers_for("suburban")),
        "meadow":    dict(scale=55, octaves=4, persistence=0.48, lacunarity=2.1,
                          respect_terrain=True, mode="mixed", mixed_wetness=0.6,
                          use_layers=True, layers=_layers_for("meadow")),
        "marsh":     dict(scale=35, octaves=6, persistence=0.62, lacunarity=2.4,
                          respect_terrain=True, mode="mixed", mixed_wetness=0.7,
                          use_layers=True, layers=_layers_for("marsh")),
        "rocky_plateau": dict(scale=85, octaves=3, persistence=0.44, lacunarity=1.9,
                             respect_terrain=False, mode="mixed", mixed_wetness=0.35,
                             use_layers=True, layers=_layers_for("rocky_plateau")),
        "taiga":     dict(scale=40, octaves=7, persistence=0.58, lacunarity=2.3,
                          respect_terrain=True, mode="mixed", mixed_wetness=0.55,
                          use_layers=True, layers=_layers_for("taiga")),
        "neon_dune": dict(scale=25, octaves=2, persistence=0.35, lacunarity=1.6,
                          respect_terrain=False, mode="layered", mixed_wetness=0.35,
                          use_layers=True, layers=_layers_for("neon_dune")),
        "mystic_swamp": dict(scale=45, octaves=5, persistence=0.65, lacunarity=2.5,
                            respect_terrain=False, mode="mixed", mixed_wetness=0.8,
                            use_layers=True, layers=_layers_for("mystic_swamp")),
    }

    def __init__(self, parent, conf, on_change, on_click):
        super().__init__(parent, bg="#121212")
        self.conf = conf
        self.on_change = on_change
        self.on_click = on_click
        veg = self.conf.setdefault("vegetation", {})

        row = tk.Frame(self, bg="#121212"); row.pack(fill=tk.X, padx=8, pady=(8, 4))
        _label(row, "Preset").pack(side=tk.LEFT)
        self.var_preset = tk.StringVar(value=veg.get("preset", "overgrown"))
        cmb = ttk.Combobox(row, values=list(self.PRESETS.keys()), state="readonly", textvariable=self.var_preset)
        cmb.pack(side=tk.LEFT, padx=(6, 8))
        cmb.bind("<<ComboboxSelected>>", self._apply_preset)

        self.var_scale = tk.IntVar(value=veg.get("scale", 50))
        self._slider("Noise Scale", 10, 300, 1, self.var_scale)

        self.var_oct = tk.IntVar(value=veg.get("octaves", 5))
        self._slider("Octaves", 1, 12, 1, self.var_oct)

        self.var_pers = tk.DoubleVar(value=veg.get("persistence", 0.55))
        self._slider("Persistence", 0.0, 1.0, 0.01, self.var_pers)

        self.var_lac = tk.DoubleVar(value=veg.get("lacunarity", 2.0))
        self._slider("Lacunarity", 1.0, 6.0, 0.1, self.var_lac)

        self.var_respect = tk.BooleanVar(value=veg.get("respect_terrain", True))
        cb = tk.Checkbutton(self, text="Respect terrain (no trees on water/asphalt)",
                            variable=self.var_respect, bg="#121212", fg="white",
                            selectcolor="#121212", command=self._write_back)
        cb.pack(anchor="w", padx=8, pady=(8, 2))

        # Mode + wetness
        rowm = tk.Frame(self, bg="#121212"); rowm.pack(fill=tk.X, padx=8, pady=(2,2))
        _label(rowm, "Mode").pack(side=tk.LEFT)
        self.var_mode = tk.StringVar(value=veg.get("mode", "mixed" if veg.get("layers") else "banded"))
        cmbm = ttk.Combobox(rowm, values=["banded","layered","mixed"], state="readonly", textvariable=self.var_mode)
        cmbm.pack(side=tk.LEFT, padx=(6,12))
        cmbm.bind("<<ComboboxSelected>>", lambda _e: self._write_back())
        self.var_wet = tk.DoubleVar(value=veg.get("mixed_wetness", 0.5))
        _label(rowm, "Layer Mix").pack(side=tk.LEFT)
        s_wet = tk.Scale(rowm, from_=0.0, to=1.0, resolution=0.01, showvalue=True, orient=tk.HORIZONTAL,
                         variable=self.var_wet, command=lambda _v: self._write_back(), bg="#121212", fg="white",
                         troughcolor="#555", highlightthickness=0, length=140)
        s_wet.pack(side=tk.LEFT)

        # Transforms for vegetation noise
        _label(self, "Transforms").pack(anchor="w", padx=8, pady=(10, 0))
        tr = veg.setdefault("transform", {"rotation": 0, "offset_x": 0, "offset_y": 0})
        self.var_rot  = tk.IntVar(value=tr.get("rotation",0));  self._slider("Rotation", 0,359,1,self.var_rot)
        self.var_offx = tk.IntVar(value=tr.get("offset_x",0));  self._slider("Offset X", -2048,2048,1,self.var_offx)
        self.var_offy = tk.IntVar(value=tr.get("offset_y",0));  self._slider("Offset Y", -2048,2048,1,self.var_offy)

        # Layered vegetation toggle and editor
        box_layers = tk.LabelFrame(self, text="Layered Vegetation (advanced)", bg="#121212", fg="white")
        box_layers.pack(fill=tk.X, padx=8, pady=(10,6))
        self.var_use_layers = tk.BooleanVar(value=veg.get("use_layers", True if veg.get("layers") else False))
        cbL = tk.Checkbutton(box_layers, text="Use layer mode (overrides banded)", variable=self.var_use_layers,
                             bg="#121212", fg="white", selectcolor="#121212", command=self._toggle_layers)
        cbL.pack(anchor="w", padx=6, pady=(2,4))

        self.frame_layers = tk.Frame(box_layers, bg="#121212")
        self.frame_layers.pack(fill=tk.X)
        self._build_layers_ui()

        # Randomize / Permute controls
        rowb = tk.Frame(self, bg="#121212"); rowb.pack(fill=tk.X, padx=8, pady=(10,6))
        br = tk.Button(rowb, text="Randomize", command=self._randomize)
        br.pack(side=tk.LEFT)
        bp = tk.Button(rowb, text="Permute", command=self._permute)
        bp.pack(side=tk.LEFT, padx=6)

    def _slider(self, label, minv, maxv, step, var):
        row = tk.Frame(self, bg="#121212"); row.pack(fill=tk.X, padx=8, pady=(6, 0))
        _label(row, label).pack(anchor="w")
        inner = tk.Frame(row, bg="#121212"); inner.pack(fill=tk.X)
        s = tk.Scale(inner, from_=minv, to=maxv, resolution=step, showvalue=False,
                     orient=tk.HORIZONTAL, variable=var,
                     command=lambda _v: self._write_back(),
                     bg="#121212", fg="white", troughcolor="#555", highlightthickness=0)
        s.pack(side=tk.LEFT, fill=tk.X, expand=True)
        e = tk.Entry(inner, width=8)
        def sync(*_): e.delete(0, tk.END); e.insert(0, str(var.get()))
        var.trace_add("write", lambda *_: sync()); sync()
        e.bind("<Return>", lambda _e: self._apply_entry(e, var, minv, maxv))
        e.bind("<FocusOut>", lambda _e: self._apply_entry(e, var, minv, maxv))
        e.pack(side=tk.LEFT, padx=6)
        s.bind("<ButtonRelease-1>", lambda _e: self.on_click())

    def _apply_entry(self, e, var, mn, mx):
        try:
            v = float(e.get()); v = max(mn, min(mx, v))
            if isinstance(var.get(), int): v = int(round(v))
            var.set(v); self._write_back()
        except Exception: pass

    def _apply_preset(self, _e=None):
        self.conf.setdefault("vegetation", {})["preset"] = self.var_preset.get()
        P = copy.deepcopy(self.PRESETS[self.var_preset.get()])
        self.conf["vegetation"].update(P)
        self.apply_conf(self.conf)
        self.on_change()

    def _write_back(self):
        veg = self.conf.setdefault("vegetation", {})
        veg.update({
            "scale": int(self.var_scale.get()),
            "octaves": int(self.var_oct.get()),
            "persistence": float(self.var_pers.get()),
            "lacunarity": float(self.var_lac.get()),
            "respect_terrain": bool(self.var_respect.get()),
            "mode": self.var_mode.get(),
            "mixed_wetness": float(self.var_wet.get()),
            "use_layers": bool(self.var_use_layers.get()),
        })
        veg.setdefault("transform", {}).update({
            "rotation": int(self.var_rot.get()),
            "offset_x": int(self.var_offx.get()),
            "offset_y": int(self.var_offy.get()),
        })
        self.on_change()

    def apply_conf(self, conf):
        self.conf = conf
        veg = conf.setdefault("vegetation", {})
        self.var_preset.set(veg.get("preset", "overgrown"))
        self.var_scale.set(veg.get("scale", 50))
        self.var_oct.set(veg.get("octaves", 5))
        self.var_pers.set(veg.get("persistence", 0.55))
        self.var_lac.set(veg.get("lacunarity", 2.0))
        self.var_respect.set(veg.get("respect_terrain", True))
        self.var_mode.set(veg.get("mode", "mixed" if veg.get("layers") else "banded"))
        self.var_wet.set(veg.get("mixed_wetness", 0.5))
        tr = veg.setdefault("transform", {})
        self.var_rot.set(tr.get("rotation",0))
        self.var_offx.set(tr.get("offset_x",0))
        self.var_offy.set(tr.get("offset_y",0))
        self.var_use_layers.set(veg.get("use_layers", True if veg.get("layers") else False))
        self._build_layers_ui()

    def _randomize(self):
        import random
        # Randomize only vegetation via seed_offset; avoids changing terrain/roads
        veg = self.conf.setdefault("vegetation", {})
        veg["seed_offset"] = random.randint(0, 2**31-1)
        self.on_change(); self.on_click()

    def _permute(self):
        import random
        # Small random perturbation of vegetation transforms
        self.var_rot.set((int(self.var_rot.get()) + random.randint(-30, 30)) % 360)
        self.var_offx.set(int(self.var_offx.get()) + random.randint(-50, 50))
        self.var_offy.set(int(self.var_offy.get()) + random.randint(-50, 50))
        self._write_back()
        self.on_click()

    # ----- Layer UI helpers -----
    def _toggle_layers(self):
        self._write_back()
        self._build_layers_ui()

    def _build_layers_ui(self):
        for w in self.frame_layers.winfo_children():
            w.destroy()
        if not self.var_use_layers.get():
            tk.Label(self.frame_layers, text="Layer mode disabled.", bg="#121212", fg="white").pack(anchor="w", padx=6)
            return
        veg = self.conf.setdefault("vegetation", {})
        layers = veg.setdefault("layers", [])

        header = tk.Frame(self.frame_layers, bg="#121212"); header.pack(fill=tk.X, padx=6)
        tk.Label(header, text="Name", bg="#121212", fg="white", width=14).pack(side=tk.LEFT)
        tk.Label(header, text="Color r,g,b", bg="#121212", fg="white", width=14).pack(side=tk.LEFT)
        tk.Label(header, text="Thresh", bg="#121212", fg="white", width=6).pack(side=tk.LEFT)
        tk.Label(header, text="Scale", bg="#121212", fg="white", width=6).pack(side=tk.LEFT)
        tk.Label(header, text="Oct", bg="#121212", fg="white", width=4).pack(side=tk.LEFT)
        tk.Label(header, text="Seed", bg="#121212", fg="white", width=8).pack(side=tk.LEFT)
        tk.Label(header, text="TerrainIn (csv)", bg="#121212", fg="white").pack(side=tk.LEFT, padx=(8,0))

        for idx, L in enumerate(layers):
            row = tk.Frame(self.frame_layers, bg="#121212"); row.pack(fill=tk.X, padx=6, pady=2)
            # Name
            vname = tk.StringVar(value=L.get("name", f"layer{idx}")); e1 = tk.Entry(row, width=14, textvariable=vname)
            e1.pack(side=tk.LEFT)
            e1.bind("<FocusOut>", lambda _e, i=idx, v=vname: self._set_layer(i, "name", v.get()))
            # Color
            col = L.get("color", [0,255,0,255])
            vcol = tk.StringVar(value=','.join(map(str, col[:3])))
            e2 = tk.Entry(row, width=14, textvariable=vcol); e2.pack(side=tk.LEFT)
            e2.bind("<FocusOut>", lambda _e, i=idx, v=vcol: self._set_layer_color(i, v.get()))
            # Thresh
            vth = tk.DoubleVar(value=float(L.get("threshold", 0.5)))
            e3 = tk.Entry(row, width=6, textvariable=vth); e3.pack(side=tk.LEFT)
            e3.bind("<FocusOut>", lambda _e, i=idx, v=vth: self._set_layer(i, "threshold", float(v.get())))
            # Scale
            vsc = tk.IntVar(value=int(L.get("scale", 60)))
            e4 = tk.Entry(row, width=6, textvariable=vsc); e4.pack(side=tk.LEFT)
            e4.bind("<FocusOut>", lambda _e, i=idx, v=vsc: self._set_layer(i, "scale", int(v.get())))
            # Octaves
            voc = tk.IntVar(value=int(L.get("octaves", 5)))
            e5 = tk.Entry(row, width=4, textvariable=voc); e5.pack(side=tk.LEFT)
            e5.bind("<FocusOut>", lambda _e, i=idx, v=voc: self._set_layer(i, "octaves", int(v.get())))
            # Seed
            vsd = tk.IntVar(value=int(L.get("seed", 0)))
            e6 = tk.Entry(row, width=8, textvariable=vsd); e6.pack(side=tk.LEFT)
            e6.bind("<FocusOut>", lambda _e, i=idx, v=vsd: self._set_layer(i, "seed", int(v.get())))
            # Terrain In
            vti = tk.StringVar(value=','.join(L.get("terrain_in", [])))
            e7 = tk.Entry(row, width=28, textvariable=vti); e7.pack(side=tk.LEFT, padx=(8,0))
            e7.bind("<FocusOut>", lambda _e, i=idx, v=vti: self._set_layer_list(i, "terrain_in", v.get()))
            # Remove
            tk.Button(row, text="Remove", command=lambda i=idx: self._remove_layer(i)).pack(side=tk.RIGHT, padx=(6,0))

        tk.Button(self.frame_layers, text="Add Layer", command=self._add_layer).pack(anchor="w", padx=6, pady=(6,2))

    def _set_layer(self, idx, key, val):
        veg = self.conf.setdefault("vegetation", {})
        layers = veg.setdefault("layers", [])
        if 0 <= idx < len(layers):
            layers[idx][key] = val
        self.on_change()

    def _set_layer_color(self, idx, csv):
        try:
            parts = [int(p.strip()) for p in csv.split(',') if p.strip()]
            if len(parts) >= 3:
                col = [parts[0], parts[1], parts[2], 255]
                self._set_layer(idx, "color", col)
        except Exception:
            pass

    def _set_layer_list(self, idx, key, csv):
        items = [s.strip() for s in csv.split(',') if s.strip()]
        self._set_layer(idx, key, items)

    def _add_layer(self):
        veg = self.conf.setdefault("vegetation", {})
        layers = veg.setdefault("layers", [])
        layers.append({"name": f"layer{len(layers)}", "color": [0,255,0,255], "scale": 60, "octaves": 5, "threshold": 0.6})
        self._build_layers_ui()
        self.on_change(); self.on_click()

    def _remove_layer(self, idx):
        veg = self.conf.setdefault("vegetation", {})
        layers = veg.setdefault("layers", [])
        if 0 <= idx < len(layers):
            layers.pop(idx)
        self._build_layers_ui()
        self.on_change(); self.on_click()
