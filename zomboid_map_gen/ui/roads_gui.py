import tkinter as tk
from tkinter import ttk

BG = "#121212"
FG = "white"


def _label(p, t): 
    return tk.Label(p, text=t, bg=BG, fg=FG)


class RoadsTab(tk.Frame):
    def __init__(self, parent, conf, on_change, on_click):
        super().__init__(parent, bg=BG)
        self.conf = conf
        self.on_change = on_change
        self.on_click = on_click
        roads = self.conf.setdefault("roads", {})

        # ====== PLANNER / GLOBAL MODE ======
        row_planner = tk.Frame(self, bg=BG); row_planner.pack(fill=tk.X, padx=8, pady=(8,0))
        _label(row_planner, "Planner").pack(side=tk.LEFT)
        self.var_planner = tk.StringVar(value=roads.get("planner", "path"))
        cmbp = ttk.Combobox(row_planner, values=["path", "random"], state="readonly", textvariable=self.var_planner)
        cmbp.pack(side=tk.LEFT, padx=(6,12))
        cmbp.bind("<<ComboboxSelected>>", lambda _e: self._write_back())

        # global angle mode
        _label(self, "Global Angle Mode").pack(anchor="w", padx=8, pady=(8, 0))
        self.var_mode = tk.StringVar(value=roads.get("mode", "ortho45"))
        cmb = ttk.Combobox(self, values=["ortho", "ortho45", "free"],
                           state="readonly", textvariable=self.var_mode)
        cmb.pack(anchor="w", padx=8, pady=(0, 8))
        cmb.bind("<<ComboboxSelected>>", lambda _e: self._write_back())

        # ====== HIERARCHICAL TOGGLE ======
        self.var_hier = tk.BooleanVar(value=roads.get("hierarchical", True))
        cb_h = tk.Checkbutton(self, text="Use hierarchical generation",
                              variable=self.var_hier,
                              bg=BG, fg=FG, selectcolor=BG,
                              command=self._toggle_hier)
        cb_h.pack(anchor="w", padx=8, pady=(0, 6))

        # ====== HIERARCHICAL FRAME ======
        self.frame_hier = tk.Frame(self, bg=BG)
        self.frame_hier.pack(fill=tk.X, padx=4, pady=(0, 6))

        self.var_highways_count = tk.IntVar(value=roads.get("highways_count", 1))
        self._slider_int(self.frame_hier, "Highways", 0, 99, self.var_highways_count)

        self.var_maj_per_hwy = tk.IntVar(value=roads.get("majors_per_highway", 2))
        self._slider_int(self.frame_hier, "Majors per highway", 0, 12, self.var_maj_per_hwy)

        self.var_mains_per_major = tk.IntVar(value=roads.get("mains_per_major", 3))
        self._slider_int(self.frame_hier, "Mains per major", 0, 12, self.var_mains_per_major)

        self.var_sides_per_main = tk.IntVar(value=roads.get("sides_per_main", 2))
        self._slider_int(self.frame_hier, "Sides per main", 0, 12, self.var_sides_per_main)

        # ====== LEGACY FRAME (old num_* sliders) ======
        self.frame_legacy = tk.Frame(self, bg=BG)
        # keep your original sliders here
        self.var_num_highways = tk.IntVar(value=roads.get("num_highways", 2))
        self._slider_int(self.frame_legacy, "Highways (legacy)", 0, 99, self.var_num_highways)
        self.var_num_majors = tk.IntVar(value=roads.get("num_majors", 3))
        self._slider_int(self.frame_legacy, "Major Roads (legacy)", 0, 99, self.var_num_majors)
        self.var_num_mains = tk.IntVar(value=roads.get("num_mains", 6))
        self._slider_int(self.frame_legacy, "Main Roads (legacy)", 0, 99, self.var_num_mains)
        self.var_num_sides = tk.IntVar(value=roads.get("num_sides", 12))
        self._slider_int(self.frame_legacy, "Side Roads (legacy)", 0, 99, self.var_num_sides)

        # show/hide correct frame initially
        self._toggle_hier(initial=True)

        # ====== PER-TYPE ANGLE MODES ======
        box_angles = tk.LabelFrame(self, text="Per-road-type angle modes", bg=BG, fg=FG)
        box_angles.pack(fill=tk.X, padx=8, pady=(6, 6))

        def _make_type_mode(name, key):
            v = tk.StringVar(value=roads.get("type_angle_modes", {}).get(key, ""))
            # allow "" = inherit/global
            cmb = ttk.Combobox(box_angles,
                               values=["", "ortho", "ortho45", "free"],
                               state="readonly", textvariable=v)
            lbl = tk.Label(box_angles, text=name, bg=BG, fg=FG)
            lbl.pack(anchor="w", padx=4)
            cmb.pack(anchor="w", padx=12, pady=(0, 4))
            cmb.bind("<<ComboboxSelected>>", lambda _e: self._write_back())
            return v

        self.var_mode_highway = _make_type_mode("Highway", "highway")
        self.var_mode_major = _make_type_mode("Major", "major")
        self.var_mode_main = _make_type_mode("Main", "main")
        self.var_mode_side = _make_type_mode("Side", "side")

        # ====== GRID STEPS ======
        box_grid = tk.LabelFrame(self, text="Grid steps (px)", bg=BG, fg=FG)
        box_grid.pack(fill=tk.X, padx=8, pady=(6, 6))

        grid_defaults = roads.get("grid_steps", {})
        self.var_grid_highway = tk.IntVar(value=grid_defaults.get("highway", 9))
        self.var_grid_major = tk.IntVar(value=grid_defaults.get("major", 6))
        self.var_grid_main = tk.IntVar(value=grid_defaults.get("main", 6))
        self.var_grid_side = tk.IntVar(value=grid_defaults.get("side", 3))

        self._entry_small(box_grid, "Highway", self.var_grid_highway)
        self._entry_small(box_grid, "Major", self.var_grid_major)
        self._entry_small(box_grid, "Main", self.var_grid_main)
        self._entry_small(box_grid, "Side", self.var_grid_side)

        # Road Lengths
        box_len = tk.LabelFrame(self, text="Road segment lengths (px)", bg=BG, fg=FG)
        box_len.pack(fill=tk.X, padx=8, pady=(6, 6))

        self.var_hwy_min = tk.IntVar(value=roads.get("highway_min_len", 120))
        self.var_hwy_max = tk.IntVar(value=roads.get("highway_max_len", 240))
        self._entry_pair(box_len, "Highway", self.var_hwy_min, self.var_hwy_max)

        self.var_maj_min = tk.IntVar(value=roads.get("major_min_len", 90))
        self.var_maj_max = tk.IntVar(value=roads.get("major_max_len", 180))
        self._entry_pair(box_len, "Major", self.var_maj_min, self.var_maj_max)

        self.var_main_min = tk.IntVar(value=roads.get("main_min_len", 70))
        self.var_main_max = tk.IntVar(value=roads.get("main_max_len", 140))
        self._entry_pair(box_len, "Main", self.var_main_min, self.var_main_max)

        self.var_side_min = tk.IntVar(value=roads.get("side_min_len", 40))
        self.var_side_max = tk.IntVar(value=roads.get("side_max_len", 90))
        self._entry_pair(box_len, "Side", self.var_side_min, self.var_side_max)

        # ====== PATHFINDER OPTIONS ======
        box_pf = tk.LabelFrame(self, text="Pathfinder (when planner=path)", bg=BG, fg=FG)
        box_pf.pack(fill=tk.X, padx=8, pady=(6, 6))
        self.var_pf_grid = tk.IntVar(value=roads.get("planner_grid", 4))
        self._entry_small(box_pf, "Planner grid (px)", self.var_pf_grid)
        self.var_towns = tk.IntVar(value=roads.get("towns", 1))
        self._entry_small(box_pf, "Towns", self.var_towns)
        self.var_town_block = tk.IntVar(value=roads.get("town_block", 48))
        self._entry_small(box_pf, "Town block (px)", self.var_town_block)
        self.var_farm_spurs = tk.IntVar(value=roads.get("farm_spurs", 12))
        self._entry_small(box_pf, "Farm spurs", self.var_farm_spurs)

        # ====== POTHOLES / COSTS / IGNORES ======
        self.var_pothole = tk.DoubleVar(value=roads.get("pothole_density", 0.02))
        self._slider_float("Pothole Density", 0.0, 0.5, 0.001, self.var_pothole)

        self.var_maxcost = tk.DoubleVar(value=roads.get("max_segment_cost", 3.0))
        self._slider_float("Max Segment Cost", 0.5, 10.0, 0.1, self.var_maxcost)

        self.var_ignore_water = tk.BooleanVar(value=roads.get("ignore_water", False))
        self.var_ignore_trees = tk.BooleanVar(value=roads.get("ignore_trees", False))
        for text, var in [("Ignore water", self.var_ignore_water),
                          ("Ignore trees", self.var_ignore_trees)]:
            cb = tk.Checkbutton(self, text=text, variable=var, bg=BG, fg=FG,
                                selectcolor=BG, command=self._write_back)
            cb.pack(anchor="w", padx=8)

        # ====== RANDOMIZE / PERMUTE ======
        rowb = tk.Frame(self, bg=BG); rowb.pack(fill=tk.X, padx=8, pady=(10, 6))
        import random as _random

        def _rand():
            r = self.conf.setdefault("roads", {})
            r["seed_offset"] = _random.randint(0, 2**31 - 1)
            self.on_change(); self.on_click()

        def _perm():
            r = self.conf.setdefault("roads", {})
            r["seed_offset"] = _random.randint(0, 2**31 - 1)
            self.on_change(); self.on_click()

        tk.Button(rowb, text="Randomize", command=_rand).pack(side=tk.LEFT)
        tk.Button(rowb, text="Permute", command=_perm).pack(side=tk.LEFT, padx=6)

        # final write
        self._write_back()

    # ==== helper: show/hide frames ====
    def _toggle_hier(self, initial=False):
        if self.var_hier.get():
            self.frame_legacy.pack_forget()
            self.frame_hier.pack(fill=tk.X, padx=4, pady=(0, 6))
        else:
            self.frame_hier.pack_forget()
            self.frame_legacy.pack(fill=tk.X, padx=4, pady=(0, 6))
        if not initial:
            self._write_back()

    # ==== write config back ====
    def _write_back(self):
        r = self.conf.setdefault("roads", {})

        # base
        r["planner"] = self.var_planner.get()
        r["mode"] = self.var_mode.get()
        r["hierarchical"] = bool(self.var_hier.get())
        r["pothole_density"] = float(self.var_pothole.get())
        r["max_segment_cost"] = float(self.var_maxcost.get())
        r["ignore_water"] = bool(self.var_ignore_water.get())
        r["ignore_trees"] = bool(self.var_ignore_trees.get())

        # hierarchical vs legacy
        if self.var_hier.get():
            r["highways_count"] = int(self.var_highways_count.get())
            r["majors_per_highway"] = int(self.var_maj_per_hwy.get())
            r["mains_per_major"] = int(self.var_mains_per_major.get())
            r["sides_per_main"] = int(self.var_sides_per_main.get())
        else:
            r["num_highways"] = int(self.var_num_highways.get())
            r["num_majors"] = int(self.var_num_majors.get())
            r["num_mains"] = int(self.var_num_mains.get())
            r["num_sides"] = int(self.var_num_sides.get())

        # per-type angle modes (skip empty)
        type_modes = {}
        for key, var in [
            ("highway", self.var_mode_highway),
            ("major", self.var_mode_major),
            ("main", self.var_mode_main),
            ("side", self.var_mode_side),
        ]:
            val = var.get().strip()
            if val:
                type_modes[key] = val
        if type_modes:
            r["type_angle_modes"] = type_modes
        else:
            r.pop("type_angle_modes", None)

        # grid steps
        r["grid_steps"] = {
            "highway": int(self.var_grid_highway.get()),
            "major": int(self.var_grid_major.get()),
            "main": int(self.var_grid_main.get()),
            "side": int(self.var_grid_side.get()),
        }

        # segment lengths (if present)
        try:
            r["highway_min_len"] = int(self.var_hwy_min.get())
            r["highway_max_len"] = int(self.var_hwy_max.get())
            r["major_min_len"] = int(self.var_maj_min.get())
            r["major_max_len"] = int(self.var_maj_max.get())
            r["main_min_len"] = int(self.var_main_min.get())
            r["main_max_len"] = int(self.var_main_max.get())
            r["side_min_len"] = int(self.var_side_min.get())
            r["side_max_len"] = int(self.var_side_max.get())
        except Exception:
            pass

        # pathfinder
        r["planner_grid"] = int(self.var_pf_grid.get())
        r["towns"] = int(self.var_towns.get())
        r["town_block"] = int(self.var_town_block.get())
        r["farm_spurs"] = int(self.var_farm_spurs.get())

        self.on_change()

    # ==== external apply (if config changed elsewhere) ====
    def apply_conf(self, conf):
        self.conf = conf
        r = conf.setdefault("roads", {})
        self.var_planner.set(r.get("planner", "path"))
        self.var_mode.set(r.get("mode", "ortho45"))
        self.var_hier.set(r.get("hierarchical", True))

        self.var_highways_count.set(r.get("highways_count", 1))
        self.var_maj_per_hwy.set(r.get("majors_per_highway", 2))
        self.var_mains_per_major.set(r.get("mains_per_major", 3))
        self.var_sides_per_main.set(r.get("sides_per_main", 2))

        self.var_num_highways.set(r.get("num_highways", 2))
        self.var_num_majors.set(r.get("num_majors", 3))
        self.var_num_mains.set(r.get("num_mains", 6))
        self.var_num_sides.set(r.get("num_sides", 12))

        # per-type
        tm = r.get("type_angle_modes", {})
        self.var_mode_highway.set(tm.get("highway", ""))
        self.var_mode_major.set(tm.get("major", ""))
        self.var_mode_main.set(tm.get("main", ""))
        self.var_mode_side.set(tm.get("side", ""))

        # grid
        gs = r.get("grid_steps", {})
        self.var_grid_highway.set(gs.get("highway", 9))
        self.var_grid_major.set(gs.get("major", 6))
        self.var_grid_main.set(gs.get("main", 6))
        self.var_grid_side.set(gs.get("side", 3))

        self.var_pothole.set(r.get("pothole_density", 0.02))
        self.var_maxcost.set(r.get("max_segment_cost", 3.0))
        self.var_ignore_water.set(r.get("ignore_water", False))
        self.var_ignore_trees.set(r.get("ignore_trees", False))

        # pathfinder
        self.var_pf_grid.set(r.get("planner_grid", 4))
        self.var_towns.set(r.get("towns", 1))
        self.var_town_block.set(r.get("town_block", 48))
        self.var_farm_spurs.set(r.get("farm_spurs", 12))

        # length
        r["highway_min_len"] = int(self.var_hwy_min.get())
        r["highway_max_len"] = int(self.var_hwy_max.get())
        r["major_min_len"] = int(self.var_maj_min.get())
        r["major_max_len"] = int(self.var_maj_max.get())
        r["main_min_len"] = int(self.var_main_min.get())
        r["main_max_len"] = int(self.var_main_max.get())
        r["side_min_len"] = int(self.var_side_min.get())
        r["side_max_len"] = int(self.var_side_max.get())

        self._toggle_hier(initial=True)
        self._write_back()

    # ---- Helpers ----
    def _slider_int(self, parent, label, mn, mx, var: tk.IntVar):
        row = tk.Frame(parent, bg=BG); row.pack(fill=tk.X, padx=8, pady=(6, 0))
        _label(row, label).pack(anchor="w")
        inner = tk.Frame(row, bg=BG); inner.pack(fill=tk.X)
        s = tk.Scale(inner, from_=mn, to=mx, resolution=1, showvalue=False,
                     orient=tk.HORIZONTAL, variable=var,
                     command=lambda _v: self._write_back(),
                     bg=BG, fg=FG, troughcolor="#555", highlightthickness=0)
        s.pack(side=tk.LEFT, fill=tk.X, expand=True)
        e = tk.Entry(inner, width=8)
        def sync(*_): 
            e.delete(0, tk.END); 
            e.insert(0, str(var.get()))
        var.trace_add("write", lambda *_: sync()); sync()
        e.bind("<Return>", lambda _e: self._apply_entry(e, var, mn, mx))
        e.bind("<FocusOut>", lambda _e: self._apply_entry(e, var, mn, mx))
        e.pack(side=tk.LEFT, padx=6)
        s.bind("<ButtonRelease-1>", lambda _e: self.on_click())

    def _slider_float(self, label, mn, mx, step, var: tk.DoubleVar):
        row = tk.Frame(self, bg=BG); row.pack(fill=tk.X, padx=8, pady=(6, 0))
        _label(row, label).pack(anchor="w")
        inner = tk.Frame(row, bg=BG); inner.pack(fill=tk.X)
        s = tk.Scale(inner, from_=mn, to=mx, resolution=step, showvalue=False,
                     orient=tk.HORIZONTAL, variable=var,
                     command=lambda _v: self._write_back(),
                     bg=BG, fg=FG, troughcolor="#555", highlightthickness=0)
        s.pack(side=tk.LEFT, fill=tk.X, expand=True)
        e = tk.Entry(inner, width=8)
        def sync(*_):
            e.delete(0, tk.END)
            e.insert(0, str(var.get()))
        var.trace_add("write", lambda *_: sync()); sync()
        e.bind("<Return>", lambda _e: self._apply_entry(e, var, mn, mx))
        e.bind("<FocusOut>", lambda _e: self._apply_entry(e, var, mn, mx))
        e.pack(side=tk.LEFT, padx=6)
        s.bind("<ButtonRelease-1>", lambda _e: self.on_click())

    def _entry_small(self, parent, label, var):
        row = tk.Frame(parent, bg=BG); row.pack(fill=tk.X, padx=6, pady=(2, 2))
        tk.Label(row, text=label, bg=BG, fg=FG).pack(side=tk.LEFT)
        e = tk.Entry(row, width=6)
        e.pack(side=tk.LEFT, padx=6)
        e.insert(0, str(var.get()))
        def apply_entry(*_):
            try:
                v = int(e.get())
                var.set(v)
                self._write_back()
            except ValueError:
                pass
        e.bind("<Return>", apply_entry)
        e.bind("<FocusOut>", apply_entry)

    def _entry_pair(self, parent, label, var_min: tk.IntVar, var_max: tk.IntVar):
        row = tk.Frame(parent, bg=BG); row.pack(fill=tk.X, padx=6, pady=(2, 2))
        tk.Label(row, text=f"{label} min/max", bg=BG, fg=FG).pack(side=tk.LEFT)
        e_min = tk.Entry(row, width=6); e_min.pack(side=tk.LEFT, padx=(6, 4))
        e_max = tk.Entry(row, width=6); e_max.pack(side=tk.LEFT, padx=(4, 6))
        e_min.insert(0, str(var_min.get()))
        e_max.insert(0, str(var_max.get()))
        def apply_both(*_):
            try:
                vmin = int(e_min.get()); vmax = int(e_max.get())
                if vmax < vmin:
                    vmax = vmin
                var_min.set(vmin); var_max.set(vmax)
                self._write_back()
            except ValueError:
                pass
        for w in (e_min, e_max):
            w.bind("<Return>", apply_both)
            w.bind("<FocusOut>", apply_both)

    def _apply_entry(self, e, var, mn, mx):
        try:
            v = float(e.get())
            v = max(mn, min(mx, v))
            if isinstance(var.get(), int):
                v = int(round(v))
            var.set(v)
            self._write_back()
        except Exception:
            pass
