import tkinter as tk
from tkinter import ttk

BG = "#121212"
FG = "white"


def _label(p, t):
    return tk.Label(p, text=t, bg=BG, fg=FG)


class DetailsTab(tk.Frame):
    """Simple controls for details bitmap layers.

    Exposes enable toggle and per-layer density sliders, plus road/terrain filters
    as lightweight text entries (comma-separated).
    """
    def __init__(self, parent, conf, on_change, on_click):
        super().__init__(parent, bg=BG)
        self.conf = conf
        self.on_change = on_change
        self.on_click = on_click

        det = self.conf.setdefault("details", {})

        row0 = tk.Frame(self, bg=BG); row0.pack(fill=tk.X, padx=8, pady=(8, 4))
        self.var_enabled = tk.BooleanVar(value=det.get("enabled", True))
        cb = tk.Checkbutton(row0, text="Enable Details Bitmap (Rules.txt colors)",
                             variable=self.var_enabled, bg=BG, fg=FG,
                             selectcolor=BG, command=self._write_back)
        cb.pack(anchor="w")

        # Overlay toggle
        row0b = tk.Frame(self, bg=BG); row0b.pack(fill=tk.X, padx=8, pady=(0, 6))
        self.var_apply_veg = tk.BooleanVar(value=det.get("apply_to_vegetation", True))
        cb2 = tk.Checkbutton(row0b, text="Overlay details onto vegetation preview",
                              variable=self.var_apply_veg, bg=BG, fg=FG,
                              selectcolor=BG, command=self._write_back)
        cb2.pack(anchor="w")

        # Global multiplier
        gm = tk.Frame(self, bg=BG); gm.pack(fill=tk.X, padx=8, pady=(8, 0))
        _label(gm, "Global density multiplier").pack(side=tk.LEFT)
        self.var_mult = tk.DoubleVar(value=float(det.get("density_multiplier", 1.0)))
        s = tk.Scale(gm, from_=0.0, to=2.0, resolution=0.05, showvalue=True, orient=tk.HORIZONTAL,
                     variable=self.var_mult, command=lambda _v: self._write_back(), bg=BG, fg=FG,
                     troughcolor="#555", highlightthickness=0, length=160)
        s.pack(side=tk.LEFT, padx=6)
        _label(self, "Quick Items").pack(anchor="w", padx=8, pady=(8, 0))

        # Scrollable container for the big quick-items list
        scroll_wrap = tk.Frame(self, bg=BG)
        scroll_wrap.pack(fill=tk.BOTH, expand=True, padx=6, pady=(4,8))
        self._scroll_canvas = tk.Canvas(scroll_wrap, bg=BG, highlightthickness=0)
        vscroll = tk.Scrollbar(scroll_wrap, orient=tk.VERTICAL, command=self._scroll_canvas.yview)
        self._scroll_canvas.configure(yscrollcommand=vscroll.set)
        self._scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vscroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._scroll_inner = tk.Frame(self._scroll_canvas, bg=BG)
        # Keep a handle to the inner window so we can resize it with the canvas
        self._inner_window_id = self._scroll_canvas.create_window((0, 0), window=self._scroll_inner, anchor="nw")

        def _on_inner_config(_evt=None):
            # Update scrollregion to encompass the inner frame
            self._scroll_canvas.configure(scrollregion=self._scroll_canvas.bbox("all"))
        self._scroll_inner.bind("<Configure>", _on_inner_config)

        # Make inner frame match canvas width so content uses full width
        def _on_canvas_config(evt):
            try:
                self._scroll_canvas.itemconfigure(self._inner_window_id, width=evt.width)
            except Exception:
                pass
        self._scroll_canvas.bind("<Configure>", _on_canvas_config)

        # Mouse wheel support (Windows/Mac/Linux)
        def _on_wheel(event):
            delta = 0
            if hasattr(event, 'delta') and event.delta:
                delta = -1 * int(event.delta/120)
            elif event.num == 5:
                delta = 1
            elif event.num == 4:
                delta = -1
            if delta:
                self._scroll_canvas.yview_scroll(delta, 'units')
                return 'break'
        self._scroll_canvas.bind_all('<MouseWheel>', _on_wheel)
        self._scroll_canvas.bind_all('<Button-4>', _on_wheel)
        self._scroll_canvas.bind_all('<Button-5>', _on_wheel)

        # Build simplified quick items UI (checkbox + sliders) inside scroll area
        self.quick_widgets = []
        self._build_quick_ui()

    def _rebuild_layers(self):
        # Advanced layers removed from the UI for simplicity
        for row in getattr(self, 'layer_rows', []):
            try: row.destroy()
            except Exception: pass
        self.layer_rows = []

    # mutators
    def _set_layer_density(self, idx, val):
        det = self.conf.setdefault("details", {})
        layers = det.setdefault("layers", [])
        if 0 <= idx < len(layers):
            layers[idx]["density"] = max(0.0, min(0.5, float(val)))
        self.on_change(); self.on_click()

    def _set_layer_key(self, idx, key, value):
        det = self.conf.setdefault("details", {})
        layers = det.setdefault("layers", [])
        if 0 <= idx < len(layers):
            layers[idx][key] = value
        self.on_change(); self.on_click()

    def _set_layer_list(self, idx, key, csv):
        items = [s.strip() for s in csv.split(',') if s.strip()]
        self._set_layer_key(idx, key, items)

    # Quick Items -----------------------------------------------------------
    def _build_quick_ui(self):
        for w in getattr(self, 'quick_widgets', []):
            try: w.destroy()
            except Exception: pass
        self.quick_widgets = []

        cont = tk.Frame(self._scroll_inner, bg=BG); cont.pack(fill=tk.X, padx=8, pady=(8,2))
        _label(cont, "Toggle items and tune density, cluster radius, jitter, and proximity where applicable.").pack(anchor="w")
        self.quick_widgets.append(cont)

        # Single-column container for quick items (avoids clipping)
        items = tk.Frame(self._scroll_inner, bg=BG)
        items.pack(fill=tk.BOTH, expand=True, padx=6, pady=(2,8))
        items.grid_columnconfigure(0, weight=1)
        self.quick_widgets.append(items)

        grid_r = 0

        def section(title: str):
            nonlocal grid_r
            tk.Label(items, text=title, bg=BG, fg=FG).grid(row=grid_r, column=0, sticky="w", padx=2, pady=(8,2))
            grid_r += 1

        def place_row(row: tk.Frame):
            nonlocal grid_r
            row.grid(row=grid_r, column=0, sticky="ew", padx=4, pady=3)
            grid_r += 1

        def make_quick(name, title, near_key=None, near_label=None, near_min=0, near_max=6):
            row = tk.Frame(items, bg=BG)
            self.quick_widgets.append(row)
            q = self.conf.setdefault("details", {}).setdefault("quick", {})

            # Checkbox / title
            en = tk.BooleanVar(value=q.get(name, {}).get("enabled", False))
            cb = tk.Checkbutton(row, text=title, variable=en, bg=BG, fg=FG, selectcolor=BG,
                                command=lambda n=name, v=en: self._quick_set(n, "enabled", bool(v.get())))
            cb.grid(row=0, column=0, padx=(0,10), sticky="w")

            # Density
            dens = tk.DoubleVar(value=q.get(name, {}).get("density", 0.03))
            _label(row, "Density").grid(row=0, column=1, sticky="e")
            sd = tk.Scale(row, from_=0.0, to=0.2, resolution=0.005, showvalue=True, orient=tk.HORIZONTAL,
                          variable=dens, command=lambda _v, n=name, v=dens: self._quick_set(n, "density", float(v.get())),
                          bg=BG, fg=FG, troughcolor="#555", highlightthickness=0, length=110)
            sd.grid(row=0, column=2, padx=(6,10), sticky="w")

            # Cluster radius
            rad = tk.IntVar(value=q.get(name, {}).get("cluster_radius", 2))
            _label(row, "Cluster").grid(row=0, column=3, sticky="e")
            sr = tk.Scale(row, from_=1, to=6, resolution=1, showvalue=True, orient=tk.HORIZONTAL,
                          variable=rad, command=lambda _v, n=name, v=rad: self._quick_set(n, "cluster_radius", int(v.get())),
                          bg=BG, fg=FG, troughcolor="#555", highlightthickness=0, length=90)
            sr.grid(row=0, column=4, padx=(6,10), sticky="w")

            # Jitter
            jit = tk.IntVar(value=q.get(name, {}).get("jitter", 1))
            _label(row, "Jitter").grid(row=0, column=5, sticky="e")
            sj = tk.Scale(row, from_=0, to=6, resolution=1, showvalue=True, orient=tk.HORIZONTAL,
                          variable=jit, command=lambda _v, n=name, v=jit: self._quick_set(n, "jitter", int(v.get())),
                          bg=BG, fg=FG, troughcolor="#555", highlightthickness=0, length=90)
            sj.grid(row=0, column=6, padx=(6,10), sticky="w")

            # optional proximity slider
            col = 7
            if near_key:
                nv = tk.IntVar(value=q.get(name, {}).get(near_key, 0))
                _label(row, near_label or "Near").grid(row=0, column=col, sticky="e")
                sn = tk.Scale(row, from_=near_min, to=near_max, resolution=1, showvalue=True, orient=tk.HORIZONTAL,
                              variable=nv, command=lambda _v, n=name, v=nv, k=near_key: self._quick_set(n, k, int(v.get())),
                              bg=BG, fg=FG, troughcolor="#555", highlightthickness=0, length=90)
                sn.grid(row=0, column=col+1, padx=(6,10), sticky="w")
                col += 2

            # Optional explicit count (0 = auto)
            pts = tk.IntVar(value=q.get(name, {}).get("points", 0))
            _label(row, "Count (0=auto)").grid(row=0, column=col, sticky="e")
            sp = tk.Scale(row, from_=0, to=5000, resolution=50, showvalue=True, orient=tk.HORIZONTAL,
                          variable=pts, command=lambda _v, n=name, v=pts: self._quick_set(n, "points", int(v.get())),
                          bg=BG, fg=FG, troughcolor="#555", highlightthickness=0, length=110)
            sp.grid(row=0, column=col+1, padx=(6,10), sticky="w")
            place_row(row)

        # Sections in two columns
        section("Flowers")
        make_quick("flowers", "All flowers (varied)")
        make_quick("flowers_orange", "Flowers - Orange")
        make_quick("flowers_yellow", "Flowers - Yellow")
        make_quick("flowers_pink_low", "Flowers - Pink Low")
        make_quick("flowers_tall_pale", "Flowers - Tall Pale")
        make_quick("flowers_purple", "Flowers - Purple")
        make_quick("flowers_white", "Flowers - White")
        make_quick("flowers_tiny_warm", "Flowers - Tiny Warm")
        make_quick("flowers_tiny_cool", "Flowers - Tiny Cool")

        section("Leaves")
        make_quick("leaves", "Fallen leaves near trees", near_key="near_radius", near_label="Near trees")

        section("Forest Floor")
        make_quick("forest_sprouts", "Sprouts", near_key="near_radius", near_label="Near trees")
        make_quick("forest_branches", "Fallen branches", near_key="near_radius", near_label="Near trees")
        make_quick("forest_roots_shoots", "Roots & shoots", near_key="near_radius", near_label="Near trees")
        make_quick("forest_rocks_duff", "Rocks & duff", near_key="near_radius", near_label="Near trees")
        make_quick("forest_low_ferns", "Low ferns", near_key="near_radius", near_label="Near trees")
        make_quick("forest_twigs", "Twigs", near_key="near_radius", near_label="Near trees")
        make_quick("forest_light_scatter", "Light scatter", near_key="near_radius", near_label="Near trees")
        make_quick("forest_deep_layer", "Deep layer", near_key="near_radius", near_label="Near trees")

        section("Trash / Urban")
        make_quick("trash_papers", "Street trash - Papers", near_key="near_road_radius", near_label="Near road")
        make_quick("trash_bulk", "Street trash - Bulk", near_key="near_road_radius", near_label="Near road")
        make_quick("trash_small_scatter", "Street trash - Small scatter", near_key="near_road_radius", near_label="Near road")
        make_quick("trash_ground", "Ground trash", near_key="near_road_radius", near_label="Near road")
        make_quick("trash_glass", "Broken glass", near_key="near_road_radius", near_label="Near road")
        make_quick("trash_grimy_mix", "Grimy street mix", near_key="near_road_radius", near_label="Near road")

        section("Street Cracks")
        make_quick("cracks_small", "Street cracks - Small")
        make_quick("cracks_medium", "Street cracks - Medium")
        make_quick("cracks_heavy", "Street cracks - Heavy")

        section("Blood")
        make_quick("blood", "Blood near streets", near_key="near_road_radius", near_label="Near road")

        section("Vegetation markers (magenta)")
        make_quick("bushes_dark", "Bushes/grass (dark grass)")
        make_quick("bushes_medium", "Bushes/grass (medium grass)")
        make_quick("bushes_light", "Bushes/grass (light grass)")
        return

        # Sections
        _label(self, "Flowers").pack(anchor="w", padx=8, pady=(10, 0))
        make_quick("flowers", "All flowers (varied)")
        make_quick("flowers_orange", "Flowers – Orange")
        make_quick("flowers_yellow", "Flowers – Yellow")
        make_quick("flowers_pink_low", "Flowers – Pink Low")
        make_quick("flowers_tall_pale", "Flowers – Tall Pale")
        make_quick("flowers_purple", "Flowers – Purple")
        make_quick("flowers_white", "Flowers – White")
        make_quick("flowers_tiny_warm", "Flowers – Tiny Warm")
        make_quick("flowers_tiny_cool", "Flowers – Tiny Cool")

        _label(self, "Leaves").pack(anchor="w", padx=8, pady=(10, 0))
        make_quick("leaves", "Fallen leaves near trees", near_key="near_radius", near_label="Near trees")

        _label(self, "Forest Floor").pack(anchor="w", padx=8, pady=(10, 0))
        make_quick("forest_sprouts", "Sprouts", near_key="near_radius", near_label="Near trees")
        make_quick("forest_branches", "Fallen branches", near_key="near_radius", near_label="Near trees")
        make_quick("forest_roots_shoots", "Roots & shoots", near_key="near_radius", near_label="Near trees")
        make_quick("forest_rocks_duff", "Rocks & duff", near_key="near_radius", near_label="Near trees")
        make_quick("forest_low_ferns", "Low ferns", near_key="near_radius", near_label="Near trees")
        make_quick("forest_twigs", "Twigs", near_key="near_radius", near_label="Near trees")
        make_quick("forest_light_scatter", "Light scatter", near_key="near_radius", near_label="Near trees")
        make_quick("forest_deep_layer", "Deep layer", near_key="near_radius", near_label="Near trees")

        _label(self, "Trash / Urban").pack(anchor="w", padx=8, pady=(10, 0))
        make_quick("trash_papers", "Street trash – Papers", near_key="near_road_radius", near_label="Near road")
        make_quick("trash_bulk", "Street trash – Bulk", near_key="near_road_radius", near_label="Near road")
        make_quick("trash_small_scatter", "Street trash – Small scatter", near_key="near_road_radius", near_label="Near road")
        make_quick("trash_ground", "Ground trash", near_key="near_road_radius", near_label="Near road")
        make_quick("trash_glass", "Broken glass", near_key="near_road_radius", near_label="Near road")
        make_quick("trash_grimy_mix", "Grimy street mix", near_key="near_road_radius", near_label="Near road")

        _label(self, "Street Cracks").pack(anchor="w", padx=8, pady=(10, 0))
        make_quick("cracks_small", "Street cracks – Small")
        make_quick("cracks_medium", "Street cracks – Medium")
        make_quick("cracks_heavy", "Street cracks – Heavy")

        _label(self, "Blood").pack(anchor="w", padx=8, pady=(10, 0))
        make_quick("blood", "Blood near streets", near_key="near_road_radius", near_label="Near road")

        _label(self, "Vegetation markers (magenta)").pack(anchor="w", padx=8, pady=(10, 0))
        make_quick("bushes_dark", "Bushes/grass (dark grass)")
        make_quick("bushes_medium", "Bushes/grass (medium grass)")
        make_quick("bushes_light", "Bushes/grass (light grass)")

    def _quick_set(self, key, subkey, val):
        q = self.conf.setdefault("details", {}).setdefault("quick", {})
        d = q.setdefault(key, {})
        d[subkey] = val
        self.on_change(); self.on_click()

    def _write_back(self):
        dd = self.conf.setdefault("details", {})
        dd["enabled"] = bool(self.var_enabled.get())
        dd["density_multiplier"] = float(self.var_mult.get())
        dd["apply_to_vegetation"] = bool(self.var_apply_veg.get())
        self.on_change()

    def apply_conf(self, conf):
        self.conf = conf
        det = conf.setdefault("details", {})
        self.var_enabled.set(det.get("enabled", True))
        self.var_apply_veg.set(det.get("apply_to_vegetation", True))
        self._rebuild_layers()
        self._build_quick_ui()

    # (Presets removed for simplicity)
