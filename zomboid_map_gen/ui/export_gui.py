import tkinter as tk
from tkinter import filedialog

def _label(p, t): return tk.Label(p, text=t, bg="#121212", fg="white")

class ExportTab(tk.Frame):
    def __init__(self, parent, conf, on_change, on_click):
        super().__init__(parent, bg="#121212")
        self.conf = conf
        self.on_change = on_change
        self.on_click = on_click

        # Canvas size controls
        _label(self, "Canvas (cells)").pack(anchor="w", padx=8, pady=(8, 0))
        canvas = conf.setdefault("canvas", {"cells_x": 1, "cells_y": 1, "cell_size": 300})
        rowc1 = tk.Frame(self, bg="#121212"); rowc1.pack(fill=tk.X, padx=8, pady=(2,0))
        _label(rowc1, "Cells X").pack(side=tk.LEFT)
        self.var_cells_x = tk.IntVar(value=canvas.get("cells_x", 1))
        spx = tk.Spinbox(rowc1, from_=1, to=64, width=6, textvariable=self.var_cells_x, command=self._write_canvas)
        spx.pack(side=tk.LEFT, padx=(6,12))
        spx.bind("<Return>", lambda _e: self._write_canvas())
        spx.bind("<FocusOut>", lambda _e: self._write_canvas())
        _label(rowc1, "Cells Y").pack(side=tk.LEFT)
        self.var_cells_y = tk.IntVar(value=canvas.get("cells_y", 1))
        spy = tk.Spinbox(rowc1, from_=1, to=64, width=6, textvariable=self.var_cells_y, command=self._write_canvas)
        spy.pack(side=tk.LEFT, padx=(6,12))
        spy.bind("<Return>", lambda _e: self._write_canvas())
        spy.bind("<FocusOut>", lambda _e: self._write_canvas())

        rowc2 = tk.Frame(self, bg="#121212"); rowc2.pack(fill=tk.X, padx=8, pady=(2,6))
        _label(rowc2, "Cell Size (px)").pack(side=tk.LEFT)
        self.var_cell_size = tk.IntVar(value=canvas.get("cell_size", 300))
        sps = tk.Spinbox(rowc2, from_=50, to=2000, width=8, textvariable=self.var_cell_size, command=self._write_canvas)
        sps.pack(side=tk.LEFT, padx=(6,0))
        sps.bind("<Return>", lambda _e: self._write_canvas())
        sps.bind("<FocusOut>", lambda _e: self._write_canvas())

        self.var_outdir = tk.StringVar(value=conf.get("output_dir", "output"))
        _label(self, "Output folder").pack(anchor="w", padx=8, pady=(8, 0))
        ent = tk.Entry(self, textvariable=self.var_outdir, bg="#1e1e1e", fg="white", insertbackground="white")
        ent.pack(fill=tk.X, padx=8, pady=(0, 6))
        ent.bind("<KeyRelease>", lambda _e: self._write_back())

        br = tk.Button(self, text="Browse…", command=self._browse)
        br.pack(anchor="w", padx=8, pady=(0, 10))

        _label(self, "Filenames").pack(anchor="w", padx=8, pady=(4, 0))
        exp = conf.setdefault("export", {
            "terrain_png": "terrain.png",
            "vegetation_png": "vegetation.png",
            "roads_png": "roads.png",
            "combined_png": "preview.png",
            "lots_png": "lots.png",
            "tile_prefix": "map",
        })

        self.entries = {}
        for key in ["terrain_png","vegetation_png","roads_png","combined_png","lots_png","details_png"]:
            row = tk.Frame(self, bg="#121212"); row.pack(fill=tk.X, padx=8, pady=(2,0))
            _label(row, key).pack(side=tk.LEFT)
            var = tk.StringVar(value=exp.get(key, ""))
            ent = tk.Entry(row, width=24, textvariable=var, bg="#1e1e1e", fg="white", insertbackground="white")
            ent.pack(side=tk.LEFT, padx=(6,0))
            ent.bind("<KeyRelease>", lambda _e, k=key, v=var: self._write_file(k, v))
            self.entries[key] = var
        rowp = tk.Frame(self, bg="#121212"); rowp.pack(fill=tk.X, padx=8, pady=(6,0))
        _label(rowp, "Tile prefix").pack(side=tk.LEFT)
        self.var_tile_prefix = tk.StringVar(value=exp.get("tile_prefix", ""))
        entp = tk.Entry(rowp, width=18, textvariable=self.var_tile_prefix, bg="#1e1e1e", fg="white", insertbackground="white")
        entp.pack(side=tk.LEFT, padx=(6,0))
        entp.bind("<KeyRelease>", lambda _e: self._write_tile_prefix())

        # ----- WorldEd options -----
        _label(self, "WorldEd Bridge").pack(anchor="w", padx=8, pady=(14, 4))
        self.worlded = conf.setdefault("worlded", {})

        self.var_worlded_output = tk.StringVar(value=self.worlded.get("output_root", "worlded_projects"))
        self.var_worlded_rules = tk.StringVar(value=self.worlded.get("rules_file", "Rules.txt"))
        self.var_worlded_exe = tk.StringVar(value=self.worlded.get("worlded_exe", ""))
        self.var_worlded_prefix = tk.StringVar(value=self.worlded.get("project_prefix", "INFINITY_Z"))
        self.var_worlded_default = tk.StringVar(value=self.worlded.get("default_project_name", "prototype"))

        self.var_worlded_assign = tk.BooleanVar(value=bool(self.worlded.get("assign_maps", True)))
        self.var_worlded_update = tk.BooleanVar(value=bool(self.worlded.get("update_existing",
                                                                              self.worlded.get("replace_existing", True))))
        self.var_worlded_launch = tk.BooleanVar(value=bool(self.worlded.get("auto_launch", False)))
        self.var_worlded_open_folder = tk.BooleanVar(value=bool(self.worlded.get("open_folder", False)))

        self._worlded_entry("Project prefix", self.var_worlded_prefix, lambda: self._write_worlded("project_prefix", self.var_worlded_prefix.get()))
        self._worlded_entry("Default project name", self.var_worlded_default, lambda: self._write_worlded("default_project_name", self.var_worlded_default.get()))
        self._worlded_path("WorldEd output root", self.var_worlded_output, self._browse_worlded_output)
        self._worlded_path("Rules.txt", self.var_worlded_rules, self._browse_worlded_rules, filetypes=[("Rules", "*.txt"), ("All", "*.*")])
        self._worlded_path("PZWorldEd.exe", self.var_worlded_exe, self._browse_worlded_exe, filetypes=[("Executable", "*.exe"), ("All", "*.*")])

        toggles = tk.Frame(self, bg="#121212"); toggles.pack(anchor="w", padx=8, pady=(8, 0))
        tk.Checkbutton(toggles, text="Assign maps to world", variable=self.var_worlded_assign,
                       command=lambda: self._write_worlded("assign_maps", self.var_worlded_assign.get()),
                       bg="#121212", fg="white", selectcolor="#121212").pack(anchor="w")
        tk.Checkbutton(toggles, text="Update existing TMX", variable=self.var_worlded_update,
                       command=lambda: self._write_worlded("update_existing", self.var_worlded_update.get()),
                       bg="#121212", fg="white", selectcolor="#121212").pack(anchor="w", pady=(2,0))
        tk.Checkbutton(toggles, text="Auto-launch WorldEd after export", variable=self.var_worlded_launch,
                       command=lambda: self._write_worlded("auto_launch", self.var_worlded_launch.get()),
                       bg="#121212", fg="white", selectcolor="#121212").pack(anchor="w", pady=(2,0))
        tk.Checkbutton(toggles, text="Open folder after export", variable=self.var_worlded_open_folder,
                       command=lambda: self._write_worlded("open_folder", self.var_worlded_open_folder.get()),
                       bg="#121212", fg="white", selectcolor="#121212").pack(anchor="w", pady=(2,0))

        # ----- Audio -----
        _label(self, "Audio").pack(anchor="w", padx=8, pady=(14, 4))
        audio = conf.setdefault("audio", {})
        self.var_audio_enabled = tk.BooleanVar(value=bool(audio.get("enabled", True)))
        self.var_music_mode = tk.StringVar(value=audio.get("music_mode", "always"))
        self.var_music_volume = tk.DoubleVar(value=float(audio.get("music_volume_db", -12.0)))

        sound_frame = tk.Frame(self, bg="#121212"); sound_frame.pack(fill=tk.X, padx=8, pady=(2, 0))
        tk.Checkbutton(sound_frame, text="Enable sound effects", variable=self.var_audio_enabled,
                       command=lambda: self._write_audio("enabled", self.var_audio_enabled.get()),
                       bg="#121212", fg="white", selectcolor="#121212").pack(anchor="w")

        mode_frame = tk.Frame(self, bg="#121212"); mode_frame.pack(fill=tk.X, padx=8, pady=(2, 0))
        _label(mode_frame, "Music mode").pack(side=tk.LEFT)
        mode_menu = tk.OptionMenu(mode_frame, self.var_music_mode, "always", "waiting", "off",
                                  command=lambda v: self._write_audio("music_mode", v))
        mode_menu.configure(bg="#1e1e1e", fg="white", highlightthickness=0)
        mode_menu.pack(side=tk.LEFT, padx=(6, 0))

        vol_frame = tk.Frame(self, bg="#121212"); vol_frame.pack(fill=tk.X, padx=8, pady=(6, 0))
        self._volume_label = _label(vol_frame, f"Music volume ({self.var_music_volume.get():.1f} dB)")
        self._volume_label.pack(side=tk.LEFT)
        vol_scale = tk.Scale(vol_frame, from_=-30, to=-3, orient=tk.HORIZONTAL, resolution=0.5,
                             variable=self.var_music_volume, bg="#121212", fg="white", troughcolor="#2a2a2a",
                             highlightthickness=0, length=200, command=self._audio_volume_changed)
        vol_scale.pack(side=tk.LEFT, padx=(8, 0))

    def _browse(self):
        d = filedialog.askdirectory()
        if not d: return
        self.var_outdir.set(d)
        self._write_back()

    def _write_back(self):
        self.conf["output_dir"] = self.var_outdir.get()
        self.on_change()

    def _write_file(self, key, var):
        self.conf.setdefault("export", {})[key] = var.get()
        self.on_change()

    def _write_tile_prefix(self):
        self.conf.setdefault("export", {})["tile_prefix"] = self.var_tile_prefix.get()
        self.on_change()

    def _write_canvas(self):
        can = self.conf.setdefault("canvas", {})
        can["cells_x"] = int(self.var_cells_x.get())
        can["cells_y"] = int(self.var_cells_y.get())
        can["cell_size"] = int(self.var_cell_size.get())
        self.on_change()

    def _write_audio(self, key, value):
        self.conf.setdefault("audio", {})[key] = value
        self.on_change()

    def _audio_volume_changed(self, value):
        try:
            vol = float(value)
        except ValueError:
            vol = self.var_music_volume.get()
        self._write_audio("music_volume_db", vol)
        if hasattr(self, "_volume_label"):
            self._volume_label.config(text=f"Music volume ({vol:.1f} dB)")

    def _worlded_entry(self, label, var, callback):
        row = tk.Frame(self, bg="#121212"); row.pack(fill=tk.X, padx=8, pady=(2,0))
        _label(row, label).pack(side=tk.LEFT)
        ent = tk.Entry(row, textvariable=var, bg="#1e1e1e", fg="white", insertbackground="white")
        ent.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6,0))
        ent.bind("<KeyRelease>", lambda _e: callback())

    def _worlded_path(self, label, var, callback, filetypes=None):
        row = tk.Frame(self, bg="#121212"); row.pack(fill=tk.X, padx=8, pady=(2,0))
        _label(row, label).pack(side=tk.LEFT)
        ent = tk.Entry(row, textvariable=var, bg="#1e1e1e", fg="white", insertbackground="white")
        ent.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6,4))
        btn = tk.Button(row, text="Browse…", command=lambda: callback(filetypes=filetypes))
        btn.pack(side=tk.LEFT)

    def _browse_worlded_output(self, filetypes=None):
        d = filedialog.askdirectory()
        if not d:
            return
        self.var_worlded_output.set(d)
        self._write_worlded("output_root", d)

    def _browse_worlded_rules(self, filetypes=None):
        path = filedialog.askopenfilename(filetypes=filetypes or [])
        if not path:
            return
        self.var_worlded_rules.set(path)
        self._write_worlded("rules_file", path)

    def _browse_worlded_exe(self, filetypes=None):
        path = filedialog.askopenfilename(filetypes=filetypes or [])
        if not path:
            return
        self.var_worlded_exe.set(path)
        self._write_worlded("worlded_exe", path)

    def _write_worlded(self, key, value):
        w = self.conf.setdefault("worlded", {})
        w[key] = value
        if key == "update_existing":
            w["replace_existing"] = value
        elif key == "replace_existing" and "update_existing" not in w:
            w["update_existing"] = value
        self.on_change()

    def apply_conf(self, conf):
        self.conf = conf
        self.var_outdir.set(conf.get("output_dir","output"))
        exp = conf.setdefault("export", {})
        for key, var in self.entries.items():
            var.set(exp.get(key,var.get()))
        self.var_tile_prefix.set(exp.get("tile_prefix", self.var_tile_prefix.get()))
        can = conf.setdefault("canvas", {})
        self.var_cells_x.set(can.get("cells_x",1))
        self.var_cells_y.set(can.get("cells_y",1))
        self.var_cell_size.set(can.get("cell_size",300))
        w = conf.setdefault("worlded", {})
        self.var_worlded_output.set(w.get("output_root", self.var_worlded_output.get()))
        self.var_worlded_rules.set(w.get("rules_file", self.var_worlded_rules.get()))
        self.var_worlded_exe.set(w.get("worlded_exe", self.var_worlded_exe.get()))
        self.var_worlded_prefix.set(w.get("project_prefix", self.var_worlded_prefix.get()))
        self.var_worlded_default.set(w.get("default_project_name", self.var_worlded_default.get()))
        self.var_worlded_assign.set(bool(w.get("assign_maps", True)))
        self.var_worlded_update.set(bool(w.get("update_existing", w.get("replace_existing", True))))
        self.var_worlded_launch.set(bool(w.get("auto_launch", False)))
        self.var_worlded_open_folder.set(bool(w.get("open_folder", False)))
        audio = conf.setdefault("audio", {})
        self.var_audio_enabled.set(bool(audio.get("enabled", self.var_audio_enabled.get())))
        self.var_music_mode.set(audio.get("music_mode", self.var_music_mode.get()))
        self.var_music_volume.set(float(audio.get("music_volume_db", self.var_music_volume.get())))
        if hasattr(self, "_volume_label"):
            self._volume_label.config(text=f"Music volume ({self.var_music_volume.get():.1f} dB)")
