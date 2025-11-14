import tkinter as tk
from tkinter import ttk

from .palette_utils import parse_palette_value, rgb_to_hex, rgb_to_string
from ..utils import colors as base_colors

def _label(p, t): return tk.Label(p, text=t, bg="#121212", fg="white")

class TerrainTab(tk.Frame):
    PRESETS = {
        "default":   dict(scale=60, octaves=6, persistence=0.50, lacunarity=2.0, water_threshold=0.25, dark_threshold=0.45, medium_threshold=0.70),
        "rural":     dict(scale=70, octaves=5, persistence=0.55, lacunarity=2.0, water_threshold=0.22, dark_threshold=0.44, medium_threshold=0.68),
        "suburban":  dict(scale=55, octaves=6, persistence=0.48, lacunarity=2.2, water_threshold=0.28, dark_threshold=0.46, medium_threshold=0.72),
        "overgrown": dict(scale=65, octaves=7, persistence=0.58, lacunarity=2.1, water_threshold=0.24, dark_threshold=0.43, medium_threshold=0.66),
    }

    def __init__(self, parent, conf, on_change, on_click):
        super().__init__(parent, bg="#121212")
        self.conf, self.on_change, self.on_click = conf, on_change, on_click
        ter = self.conf.setdefault("terrain", {})
        ter.setdefault("postprocess", {"edge_ragging": True, "speckle": True, "erosion": True})
        ter.setdefault("transform", {"rotation": 0, "offset_x": 0, "offset_y": 0})
        ter.setdefault("palette", {})

        # Preset
        row = tk.Frame(self, bg="#121212"); row.pack(fill=tk.X, padx=8, pady=(8,4))
        _label(row, "Preset").pack(side=tk.LEFT)
        self.var_preset = tk.StringVar(value=ter.get("preset","default"))
        cmb = ttk.Combobox(row, values=list(self.PRESETS.keys()), state="readonly", textvariable=self.var_preset)
        cmb.pack(side=tk.LEFT, padx=(6,8))
        cmb.bind("<<ComboboxSelected>>", self._apply_preset)

        # Sliders
        self.var_scale = tk.IntVar(value=ter.get("scale",60));      self._slider("Noise Scale",      10,300,1,  self.var_scale)
        self.var_oct   = tk.IntVar(value=ter.get("octaves",6));     self._slider("Octaves",           1, 12,1,   self.var_oct)
        self.var_pers  = tk.DoubleVar(value=ter.get("persistence",0.5)); self._slider("Persistence", 0.0,1.0,0.01,self.var_pers)
        self.var_lac   = tk.DoubleVar(value=ter.get("lacunarity",2.0));  self._slider("Lacunarity",  1.0,6.0,0.1, self.var_lac)
        self.var_wth   = tk.DoubleVar(value=ter.get("water_threshold",0.25)); self._slider("Water Threshold",0.0,1.0,0.01,self.var_wth)
        self.var_dth   = tk.DoubleVar(value=ter.get("dark_threshold",0.45));  self._slider("Dark Threshold", 0.0,1.0,0.01,self.var_dth)
        self.var_mth   = tk.DoubleVar(value=ter.get("medium_threshold",0.70));self._slider("Medium Threshold",0.0,1.0,0.01,self.var_mth)

        # Post-processing
        _label(self,"Post-Processing").pack(anchor="w", padx=8, pady=(10,0))
        pp = ter["postprocess"]
        self.var_edge = tk.BooleanVar(value=pp.get("edge_ragging",True))
        self.var_speck= tk.BooleanVar(value=pp.get("speckle",True))
        self.var_eros = tk.BooleanVar(value=pp.get("erosion",True))
        for text, var in [("Edge Ragging",self.var_edge),("Speckle",self.var_speck),("Erosion",self.var_eros)]:
            cb = tk.Checkbutton(self, text=text, variable=var, bg="#121212", fg="white",
                                selectcolor="#121212", command=self._write_back)
            cb.pack(anchor="w", padx=14)

        # Per-effect strengths
        self.var_edge_strength = tk.DoubleVar(value=pp.get("edge_strength", 0.6))
        self._slider("Edge Strength", 0.0, 1.0, 0.01, self.var_edge_strength)
        self.var_speckle_density = tk.DoubleVar(value=pp.get("speckle_density", 0.01))
        self._slider("Speckle Density", 0.0, 0.05, 0.001, self.var_speckle_density)
        self.var_erosion_strength = tk.DoubleVar(value=pp.get("erosion_strength", 0.6))
        self._slider("Erosion Strength", 0.0, 1.0, 0.01, self.var_erosion_strength)

        # Transforms
        _label(self,"Transforms").pack(anchor="w", padx=8, pady=(10,0))
        tr = ter["transform"]
        self.var_rot  = tk.IntVar(value=tr.get("rotation",0));  self._slider("Rotation°", 0,359,1,self.var_rot)
        self.var_offx = tk.IntVar(value=tr.get("offset_x",0));  self._slider("Offset X", -2048,2048,1,self.var_offx)
        self.var_offy = tk.IntVar(value=tr.get("offset_y",0));  self._slider("Offset Y", -2048,2048,1,self.var_offy)

        palette_container = tk.LabelFrame(self, text="Palette overrides", bg="#121212", fg="white")
        palette_container.pack(fill=tk.BOTH, padx=8, pady=(10,4), expand=True)
        palette_canvas = tk.Canvas(palette_container, bg="#121212", highlightthickness=0, height=220)
        palette_scroll = ttk.Scrollbar(palette_container, orient="vertical", command=palette_canvas.yview)
        palette_canvas.configure(yscrollcommand=palette_scroll.set)
        palette_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0,4), pady=4)
        palette_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=4)
        palette_inner = tk.Frame(palette_canvas, bg="#121212")
        self._palette_canvas_window = palette_canvas.create_window((0, 0), window=palette_inner, anchor="nw")
        palette_inner.bind("<Configure>", lambda ev: palette_canvas.configure(scrollregion=palette_canvas.bbox("all")))
        palette_canvas.bind("<Configure>", lambda ev: palette_canvas.itemconfigure(self._palette_canvas_window, width=ev.width))
        palette_canvas.bind("<MouseWheel>", lambda ev: palette_canvas.yview_scroll(int(-ev.delta / 120), "units"))
        self.palette_controls = {}
        for name in base_colors.DEFAULT_VANILLA:
            row = tk.Frame(palette_inner, bg="#121212")
            row.pack(fill=tk.X, padx=4, pady=2)
            tk.Label(row, text=name.replace("_"," ").title(), width=20, anchor="w", bg="#121212", fg="white").pack(side=tk.LEFT)
            var = tk.StringVar()
            entry = tk.Entry(row, width=12, textvariable=var, bg="#1b1b1b", fg="white", insertbackground="white")
            entry.pack(side=tk.LEFT, padx=6)
            preview = tk.Label(row, text=" ", width=3, bg="#000", relief="ridge", bd=1)
            preview.pack(side=tk.LEFT, padx=6)
            self.palette_controls[name] = {"var": var, "preview": preview}
            var.trace_add("write", lambda *_ , n=name: self._update_palette_preview(n))
            entry.bind("<Return>", lambda _e, n=name: self._apply_palette_entry(n))
            entry.bind("<FocusOut>", lambda _e, n=name: self._apply_palette_entry(n))
        self._load_palette_entries(ter)

        # Randomize / Permute controls
        rowb = tk.Frame(self, bg="#121212"); rowb.pack(fill=tk.X, padx=8, pady=(10,6))
        br = tk.Button(rowb, text="Randomize", command=self._randomize)
        br.pack(side=tk.LEFT)
        bp = tk.Button(rowb, text="Permute", command=self._permute)
        bp.pack(side=tk.LEFT, padx=6)

    def _slider(self, label, minv, maxv, step, var):
        row = tk.Frame(self, bg="#121212"); row.pack(fill=tk.X, padx=8, pady=(6,0))
        _label(row, label).pack(anchor="w")
        inner = tk.Frame(row, bg="#121212"); inner.pack(fill=tk.X)
        s = tk.Scale(inner, from_=minv, to=maxv, resolution=step, showvalue=False,
                     orient=tk.HORIZONTAL, variable=var,
                     command=lambda _v: self._write_back(),
                     bg="#121212", fg="white", troughcolor="#555", highlightthickness=0)
        s.pack(side=tk.LEFT, fill=tk.X, expand=True)
        e = tk.Entry(inner, width=8)
        def sync(*_): e.delete(0,tk.END); e.insert(0,str(var.get()))
        var.trace_add("write", lambda *_: sync()); sync()
        e.bind("<Return>", lambda _e: self._apply_entry(e,var,minv,maxv))
        e.bind("<FocusOut>", lambda _e: self._apply_entry(e,var,minv,maxv))
        e.pack(side=tk.LEFT, padx=6)
        s.bind("<ButtonRelease-1>", lambda _e: self.on_click())

    def _apply_entry(self, e, var, mn, mx):
        try:
            v = float(e.get()); v = max(mn, min(mx, v))
            if isinstance(var.get(), int): v = int(round(v))
            var.set(v); self._write_back()
        except Exception: pass

    def _load_palette_entries(self, ter):
        palette = ter.get("palette", {}) if isinstance(ter, dict) else {}
        for name, ctrl in self.palette_controls.items():
            specified = palette.get(name)
            if specified and len(specified) >= 3:
                rgb = tuple(int(specified[i]) for i in range(3))
            else:
                rgb = base_colors.DEFAULT_VANILLA[name][:3]
            ctrl["var"].set(rgb_to_string(rgb))
            self._update_palette_preview(name)

    def _update_palette_preview(self, name):
        ctrl = self.palette_controls.get(name)
        if not ctrl:
            return
        rgb = parse_palette_value(ctrl["var"].get())
        if not rgb:
            rgb = base_colors.DEFAULT_VANILLA[name][:3]
        ctrl["preview"].configure(bg=rgb_to_hex(rgb))

    def _apply_palette_entry(self, name):
        self._write_back()
        self.on_click()

    def _apply_preset(self, _e=None):
        key = self.var_preset.get()
        self.conf.setdefault("terrain", {})["preset"] = key
        self.conf["terrain"].update(self.PRESETS[key])
        self.apply_conf(self.conf)
        self.on_change()

    def _write_back(self):
        ter = self.conf.setdefault("terrain", {})
        ter.update({
            "scale": int(self.var_scale.get()),
            "octaves": int(self.var_oct.get()),
            "persistence": float(self.var_pers.get()),
            "lacunarity": float(self.var_lac.get()),
            "water_threshold": float(self.var_wth.get()),
            "dark_threshold": float(self.var_dth.get()),
            "medium_threshold": float(self.var_mth.get()),
        })
        ter.setdefault("postprocess", {}).update({
            "edge_ragging": bool(self.var_edge.get()),
            "speckle": bool(self.var_speck.get()),
            "erosion": bool(self.var_eros.get()),
            "edge_strength": float(self.var_edge_strength.get()),
            "speckle_density": float(self.var_speckle_density.get()),
            "erosion_strength": float(self.var_erosion_strength.get()),
        })
        ter.setdefault("transform", {}).update({
            "rotation": int(self.var_rot.get()),
            "offset_x": int(self.var_offx.get()),
            "offset_y": int(self.var_offy.get()),
        })
        palette = {}
        for name, ctrl in self.palette_controls.items():
            rgb = self._parse_palette_value(ctrl["var"].get())
            if rgb:
                palette[name] = list(rgb)
        ter["palette"] = palette
        self.on_change()

    def apply_conf(self, conf):
        self.conf = conf
        ter = conf.setdefault("terrain", {})
        self.var_preset.set(ter.get("preset","default"))
        self.var_scale.set(ter.get("scale",60))
        self.var_oct.set(ter.get("octaves",6))
        self.var_pers.set(ter.get("persistence",0.5))
        self.var_lac.set(ter.get("lacunarity",2.0))
        self.var_wth.set(ter.get("water_threshold",0.25))
        self.var_dth.set(ter.get("dark_threshold",0.45))
        self.var_mth.set(ter.get("medium_threshold",0.70))
        pp = ter.setdefault("postprocess", {})
        self.var_edge.set(pp.get("edge_ragging",True))
        self.var_speck.set(pp.get("speckle",True))
        self.var_eros.set(pp.get("erosion",True))
        self.var_edge_strength.set(pp.get("edge_strength",0.6))
        self.var_speckle_density.set(pp.get("speckle_density",0.01))
        self.var_erosion_strength.set(pp.get("erosion_strength",0.6))
        tr = ter.setdefault("transform", {})
        self.var_rot.set(tr.get("rotation",0))
        self.var_offx.set(tr.get("offset_x",0))
        self.var_offy.set(tr.get("offset_y",0))
        self._load_palette_entries(ter)

    def _randomize(self):
        import random
        # Randomize only terrain seed via offset; keep global master unchanged
        ter = self.conf.setdefault("terrain", {})
        ter["seed_offset"] = random.randint(0, 2**31-1)
        self.on_change(); self.on_click()

    def _permute(self):
        import random
        self.var_rot.set((int(self.var_rot.get()) + random.randint(-30, 30)) % 360)
        self.var_offx.set(int(self.var_offx.get()) + random.randint(-50, 50))
        self.var_offy.set(int(self.var_offy.get()) + random.randint(-50, 50))
        self._write_back()
        self.on_click()
