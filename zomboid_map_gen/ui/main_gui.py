import io
import json
import os
import shutil
import sys
import tempfile

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from PIL import Image, ImageTk, ImageEnhance
import threading

from .. import core, config as cfg
from ..worlded import launch_worlded, prepare_project, project_dir_for
from .sound import SoundPlayer
from .terrain_gui import TerrainTab
from .vegetation_gui import VegetationTab
from .rules_palette_gui import RulesPaletteTab
from .roads_gui import RoadsTab
from .export_gui import ExportTab
from .details_gui import DetailsTab
from .tmx_tools import TmxReadWindow


THUMB_SIZE = (300, 300)   # larger thumbnails, keep aspect via .thumbnail
THUMB_BG = "#1b1b1b"
FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "font"
DEFAULT_PRESETS = [
    ("Normal", "normal.json"),
    ("Apocalyptic World", "apocalyptic_world.json"),
    ("Islands", "islands.json"),
    ("Coast", "coast.json"),
    ("Desert", "desert.json"),
    ("Forest", "forest.json"),
    ("10 Years Later", "ten_years_later.json"),
    ("100 Years Later", "hundred_years_later.json"),
    ("Blood and Trash Everywhere", "blood_and_trash.json"),
    ("Overgrown World", "overgrown_world.json"),
    ("Flower Fields", "flower_fields.json"),
]


THUMB_KEYS = [
    ("terrain", "Terrain"),
    ("vegetation", "Vegetation"),
    ("combo", "Terrain + Roads"),
    ("roads", "Road Network"),
    ("lots", "Lots"),
    ("details", "Details"),
]


class PreviewTab(tk.Frame):
    def __init__(self, parent, conf, on_change):
        super().__init__(parent, bg="#121212")
        self.conf = conf
        self.on_change = on_change
        preview = self.conf.setdefault("preview", {})
        preview.setdefault("enabled", True)

        tk.Label(self, text="Live previews", bg="#121212", fg="white", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=8, pady=(8, 2))
        self.var_enabled = tk.BooleanVar(value=preview.get("enabled", True))
        cb = tk.Checkbutton(self, text="Enable preview generation", variable=self.var_enabled,
                            bg="#121212", fg="white", selectcolor="#121212", activebackground="#1b1b1b",
                            command=self._write_back)
        cb.pack(anchor="w", padx=12, pady=(0, 4))
        tk.Label(self, text="Disabling the preview skips generating thumbnails and leaves the history panels black.",
                 bg="#121212", fg="#ccc", wraplength=260, justify="left").pack(anchor="w", padx=12, pady=(0, 4))
        thumbs_frame = tk.LabelFrame(self, text="Thumb visibility", bg="#121212", fg="white")
        thumbs_frame.pack(fill=tk.X, padx=8, pady=(8, 4))
        thumbs = preview.setdefault("thumbs", {})
        self.thumb_vars = {}
        for key, label in THUMB_KEYS:
            var = tk.BooleanVar(value=thumbs.get(key, True))
            cb = tk.Checkbutton(thumbs_frame, text=label, variable=var,
                                bg="#121212", fg="white", selectcolor="#121212",
                                command=self._write_back)
            cb.pack(anchor="w", padx=12, pady=2)
            self.thumb_vars[key] = var

    def _write_back(self):
        preview = self.conf.setdefault("preview", {})
        preview["enabled"] = bool(self.var_enabled.get())
        thumbs = preview.setdefault("thumbs", {})
        for key, var in self.thumb_vars.items():
            thumbs[key] = bool(var.get())
        self.on_change()

    def apply_conf(self, conf):
        self.conf = conf
        preview = conf.setdefault("preview", {})
        preview.setdefault("enabled", True)
        self.var_enabled.set(preview.get("enabled", True))
        thumbs = preview.setdefault("thumbs", {})
        for key, var in self.thumb_vars.items():
            var.set(thumbs.get(key, True))


class InfinitXYZApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self._prepare_fonts()
        self.title("Infinit_x_y_z")
        self.configure(bg="#121212")
        self.geometry("1280x760")
        self.minsize(1100, 640)

        # project root (…/zomboid_map_gen/..)
        self.project_root = Path(__file__).resolve().parents[2]
        self.default_config_dir = self.project_root / "assets" / "default_configs"

        # config in memory
        self.conf = cfg.default_config()

        self.sound = SoundPlayer(self.project_root, self.conf)

        # debounce / busy
        self._regen_after_id = None
        self._regen_delay_ms = 250
        self._busy = False
        self._gen_thread = None
        self._latest_pzw: Path | None = None
        self._roads_grid_thread: threading.Thread | None = None

        # thumbnail image refs (prevent GC)
        self._thumb_imgs = {key: None for key, _ in THUMB_KEYS}
        self._thumb_last_paths = {key: None for key, _ in THUMB_KEYS}
        self._thumb_disabled_imgs = {}

        self._build_ui()
        self._schedule_regen()
        self.bind_all("<Control-r>", self._on_ctrl_r)

    def _prepare_fonts(self):
        def tuple_from_file(name, size):
            path = FONT_DIR / name
            if path.exists():
                return ("@" + str(path), size)
            fallback = "Segoe UI" if sys.platform.startswith("win") else "Helvetica"
            return (fallback, size)

        self.fonts = {
            "regular": tuple_from_file("Spectral-Regular.ttf", 11),
            "semi_bold": tuple_from_file("Spectral-SemiBold.ttf", 12),
            "light": tuple_from_file("Spectral-Light.ttf", 11),
        }
        self.option_add("*Font", self.fonts["regular"])
        self.option_add("*Button.Font", self.fonts["semi_bold"])
        self.option_add("*Checkbutton.Font", self.fonts["regular"])
        self.option_add("*Label.Font", self.fonts["regular"])

    # ---------- UI ----------
    def _build_ui(self):
        self._build_menu()

        # Top bar
        top = tk.Frame(self, bg="#121212")
        top.pack(side=tk.TOP, fill=tk.X)
        self.var_live = tk.BooleanVar(value=True)
        live = tk.Checkbutton(top, text="Live Update", variable=self.var_live, bg="#121212", fg="white",
                              selectcolor="#121212", command=self._click)
        live.pack(side=tk.LEFT, padx=10, pady=6)

        worlded_btn = tk.Button(top, text="INFINIT-Z", command=self._worlded_clicked,
                                 bg="#f5d442", fg="#1b1b1b", padx=18, pady=6,
                                 font=self.fonts.get("semi_bold"), activebackground="#ffe47a", activeforeground="#151515")
        worlded_btn.pack(side=tk.RIGHT, padx=10, pady=6)
        self._worlded_btn = worlded_btn
        open_pzw = tk.Button(top, text="Open .pzw", command=self._open_worlded_file, state="disabled",
                             bg="#222", fg="white", padx=12, pady=6)
        open_pzw.pack(side=tk.RIGHT, padx=10, pady=6)
        self._open_pzw_btn = open_pzw

        gen = tk.Button(top, text="Generate", command=self._generate_clicked,
                        bg="#ffffff", fg="#121212", padx=16, pady=6,
                        font=self.fonts.get("semi_bold"), activebackground="#f5f5f5", activeforeground="#101010")
        gen.pack(side=tk.RIGHT, padx=10, pady=6)

        # Preview cell controls (X,Y)
        prev = tk.Frame(top, bg="#121212")
        prev.pack(side=tk.LEFT, padx=10)
        tk.Label(prev, text="Preview cell:", bg="#121212", fg="white").pack(side=tk.LEFT)
        cx, cy = self.conf.get("preview", {}).get("cell_x", 0), self.conf.get("preview", {}).get("cell_y", 0)
        self.var_prev_x = tk.IntVar(value=int(cx))
        self.var_prev_y = tk.IntVar(value=int(cy))
        sx = tk.Spinbox(prev, from_=0, to=999, width=3, textvariable=self.var_prev_x, command=self._preview_changed)
        sy = tk.Spinbox(prev, from_=0, to=999, width=3, textvariable=self.var_prev_y, command=self._preview_changed)
        sx.pack(side=tk.LEFT, padx=(6,2))
        tk.Label(prev, text=",", bg="#121212", fg="white").pack(side=tk.LEFT)
        sy.pack(side=tk.LEFT, padx=(2,0))

        # Body split: left tabs, right thumbnails
        body = tk.Frame(self, bg="#121212")
        body.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(body, bg="#121212")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.nb = ttk.Notebook(left)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=6, pady=(6, 0))
        self._style_notebook()
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self.preview_tab = PreviewTab(self.nb, self.conf, on_change=self.on_params_changed)
        self.nb.add(self.preview_tab, text="Preview")

        # Tabs (each is passed callbacks to update config and schedule regen)
        self.terrain_tab = TerrainTab(self.nb, self.conf, on_change=self.on_params_changed, on_click=self._click)
        self.nb.add(self.terrain_tab, text="Terrain")

        self.vegetation_tab = VegetationTab(self.nb, self.conf, on_change=self.on_params_changed, on_click=self._click)
        self.nb.add(self.vegetation_tab, text="Vegetation")

        self.rules_palette_tab = RulesPaletteTab(self.nb, self.conf, on_change=self.on_params_changed, on_click=self._click)
        self.nb.add(self.rules_palette_tab, text="Palette")

        roads_holder = tk.Frame(self.nb, bg="#121212")
        roads_canvas = tk.Canvas(roads_holder, bg="#121212", highlightthickness=0)
        roads_scroll = ttk.Scrollbar(roads_holder, orient="vertical", command=roads_canvas.yview)
        roads_canvas.configure(yscrollcommand=roads_scroll.set)
        roads_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        roads_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.roads_tab = RoadsTab(roads_holder, self.conf, on_change=self.on_params_changed, on_click=self._click)
        tab_window = roads_canvas.create_window((0, 0), window=self.roads_tab, anchor="nw")

        def _update_scroll(_event=None):
            roads_canvas.configure(scrollregion=roads_canvas.bbox("all"))

        self.roads_tab.bind("<Configure>", _update_scroll)
        roads_canvas.bind("<Configure>", lambda ev: roads_canvas.itemconfigure(tab_window, width=ev.width))
        roads_canvas.bind("<MouseWheel>", lambda ev: roads_canvas.yview_scroll(int(-ev.delta / 120), "units"))

        self.nb.add(roads_holder, text="Roads")

        self.details_tab = DetailsTab(self.nb, self.conf, on_change=self.on_params_changed, on_click=self._click)
        self.nb.add(self.details_tab, text="Details")


        self.export_tab = ExportTab(self.nb, self.conf, on_change=self.on_params_changed, on_click=self._click)
        self.nb.add(self.export_tab, text="Export")

        # Right: thumbnails only (no big preview)
        right = tk.Frame(body, bg="#121212")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._thumb_grid = tk.Frame(right, bg="#121212")
        self._thumb_grid.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=6, pady=6)

        self._thumb_labels = {}
        # arrange in two columns
        self._thumb_labels["terrain"] = self._make_thumb_box(self._thumb_grid, "Terrain", 0, 0)
        self._thumb_labels["vegetation"] = self._make_thumb_box(self._thumb_grid, "Vegetation", 0, 1)
        self._thumb_labels["combo"] = self._make_thumb_box(self._thumb_grid, "Terrain + Roads", 1, 0)
        self._thumb_labels["roads"] = self._make_thumb_box(self._thumb_grid, "Road Network", 1, 1)
        self._thumb_labels["lots"] = self._make_thumb_box(self._thumb_grid, "Lots", 2, 0)
        self._thumb_labels["details"] = self._make_thumb_box(self._thumb_grid, "Details", 2, 1)

        # Status
        self.status_var = tk.StringVar(value="Ready.")
        status = tk.Label(self, textvariable=self.status_var, bg="#121212", fg="white", anchor="w")
        status.pack(side=tk.BOTTOM, fill=tk.X)

    def _build_menu(self):
        mb = tk.Menu(self)
        filem = tk.Menu(mb, tearoff=0)
        filem.add_command(label="Open Config.", command=self._menu_load)
        filem.add_command(label="Save Config As.", command=self._menu_save)
        filem.add_separator()
        filem.add_command(label="Exit", command=self.destroy)
        defaultm = tk.Menu(filem, tearoff=0)
        entries = self._default_config_entries()
        if entries:
            for label, path in entries:
                defaultm.add_command(label=label, command=lambda p=path, lbl=label: self._load_default_config(p, lbl))
        else:
            defaultm.add_command(label="(no presets found)", state="disabled")
        filem.add_cascade(label="Default Configs", menu=defaultm)
        mb.add_cascade(label="File", menu=filem)

        toolm = tk.Menu(mb, tearoff=0)
        toolm.add_command(label="TMX Read.", command=self._menu_tmx_read)
        toolm.add_command(label="TMX Edit.", state="disabled")
        toolm.add_command(label="TMX Build.", state="disabled")
        mb.add_cascade(label="Tool", menu=toolm)

        exportm = tk.Menu(mb, tearoff=0)
        exportm.add_command(label="Open Output Folder", command=self._open_output_folder)
        mb.add_cascade(label="Export", menu=exportm)

        helpm = tk.Menu(mb, tearoff=0)
        helpm.add_command(label="About", command=lambda: messagebox.showinfo("About", "Infinit_x_y_z"))
        mb.add_cascade(label="Help", menu=helpm)

        self.config(menu=mb)

    def _default_config_entries(self):
        entries = []
        for label, filename in DEFAULT_PRESETS:
            path = self.default_config_dir / filename
            if path.exists():
                entries.append((label, path))
        return entries

    def _style_notebook(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook", background="#121212", borderwidth=0)
        style.configure("TNotebook.Tab", background="#ff7fb3", foreground="#121212",
                        font=self.fonts.get("semi_bold"), padding=(10, 6), borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", "#4ff0ff"), ("!selected", "#ff7fb3")],
                  foreground=[("selected", "#050505"), ("!selected", "#050505")])

    def _make_thumb_box(self, parent, title, row, col):
        wrap = tk.Frame(parent, bg="#121212")
        wrap.grid(row=row, column=col, padx=8, pady=8, sticky="n")

        tk.Label(wrap, text=title, bg="#121212", fg="white").pack(anchor="w")
        lbl = tk.Label(wrap, bg=THUMB_BG, width=THUMB_SIZE[0], height=THUMB_SIZE[1])
        lbl.pack()
        lbl.bind("<Double-Button-1>", lambda e, key=title: self._open_single_image(key))
        return lbl

    def _on_tab_changed(self, *_):
        self.sound.tab_switched()

    # ---------- Events / sounds ----------
    def _click(self):
        self.sound.click()

    def _menu_save(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        cfg.save_config(self.conf, path)
        self.status_var.set(f"Config saved: {path}")
        self.sound.bubble()

    def _menu_load(self):
        path = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            conf = cfg.load_config(path)
        except Exception as exc:
            messagebox.showerror("Load Config", f"Could not read {path}: {exc}")
            return
        self._apply_conf(conf, f"Config loaded: {path}")
        self.sound.bubble()

    def _menu_tmx_read(self):
        path = filedialog.askopenfilename(title="Open TMX File", filetypes=[("TMX", "*.tmx"), ("All files", "*.*")])
        if not path:
            return
        try:
            window = TmxReadWindow(self, Path(path))
            self.wait_window(window.top)
        except Exception as exc:
            messagebox.showerror("TMX Reader", f"Failed to read TMX:\n{exc}")

    def _apply_conf(self, conf, status_text=None):
        self.conf = conf
        self.preview_tab.apply_conf(self.conf)
        self.terrain_tab.apply_conf(self.conf)
        self.vegetation_tab.apply_conf(self.conf)
        self.rules_palette_tab.apply_conf(self.conf)
        self.roads_tab.apply_conf(self.conf)
        self.details_tab.apply_conf(self.conf)
        self.export_tab.apply_conf(self.conf)
        self.sound.sync_settings()
        if status_text:
            self.status_var.set(status_text)
        self._schedule_regen()

    def _load_default_config(self, path: Path, label: str):
        try:
            override = cfg.load_config(str(path))
        except Exception as exc:
            messagebox.showerror("Default Configs", f"Could not load {label}: {exc}")
            return
        conf = self._merge_dict(cfg.default_config(), override)
        self._apply_conf(conf, f"Default config applied: {label}")
        self.sound.bubble()

    def _merge_dict(self, base: dict, override: dict):
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key] = self._merge_dict(base[key], value)
            else:
                base[key] = value
        return base

    def _open_output_folder(self):
        out_dir = Path(self.conf.get("output_dir", "output")).resolve()
        try:
            if sys.platform.startswith("win"): os.startfile(str(out_dir))
            elif sys.platform == "darwin": os.system(f'open "{out_dir}"')
            else: os.system(f'xdg-open "{out_dir}"')
        except Exception: pass
        self._click()

    def _open_single_image(self, key_title):
        # map from display title to actual file path
        t_path, v_path, r_path, c_path, l_path, d_path = self._paths()
        mapping = {
            "Terrain": t_path,
            "Vegetation": v_path,
            "Terrain + Roads": c_path,  # combined
            "Road Network": r_path,
            "Lots": l_path,
            "Details": d_path,
        }
        p = mapping.get(key_title)
        if not p or not p.exists(): return
        self._open_image_viewer(p)
        self.sound.bubble()

    # ---------- Change / regen ----------
    def on_params_changed(self, *_):
        # tabs already wrote values into self.conf
        self.sound.sync_settings()
        if self.var_live.get():
            self._schedule_regen()

    def _schedule_regen(self):
        if self._regen_after_id:
            self.after_cancel(self._regen_after_id)
        self._regen_after_id = self.after(self._regen_delay_ms, self._do_regen)

    def _do_regen(self):

        self._regen_after_id = None

        self._start_generation(full=False)



    def _generate_clicked(self):
        self._start_generation(full=True)

    def _worlded_clicked(self):
        if self._busy:
            return
        self._set_worlded_result(None)
        world_conf = self.conf.get("worlded", {}) or {}
        project_name = world_conf.get("default_project_name") or self.conf.get("export", {}).get("tile_prefix", "map")
        project_dir = project_dir_for(self.conf, project_name)
        project_dir.parent.mkdir(parents=True, exist_ok=True)
        images_root = project_dir / "images"
        shutil.rmtree(images_root, ignore_errors=True)


        def after_generate(conf_snapshot):
            world_conf_snapshot = conf_snapshot.get("worlded", {}) or {}
            project = prepare_project(
                conf_snapshot,
                project_name=project_name,
                tiles_root_override=images_root,
                reuse_tiles=True,
            )
            auto_launch = bool(world_conf_snapshot.get("auto_launch")) and world_conf_snapshot.get("worlded_exe")
            launch_note = ""
            if auto_launch:
                try:
                    launch_worlded(project, world_conf_snapshot)
                    launch_note = " (WorldEd launched)"
                except Exception as exc:
                    launch_note = f" (auto-launch failed: {exc})"
            message = f"WorldEd project ready: {project.project_dir}{launch_note}"
            return {"message": message, "project_dir": str(project.project_dir), "pzw": str(project.pzw_path)}

        self._start_generation(full=True, after_generate=after_generate, tiles_root_override=images_root)

    def _open_worlded_file(self):
        if not self._latest_pzw:
            return
        if self._latest_pzw.exists():
            try:
                os.startfile(str(self._latest_pzw))
            except Exception as exc:
                messagebox.showerror("WorldEd", f"Could not open .pzw: {exc}")
        else:
            messagebox.showwarning("WorldEd", f"WorldEd file missing: {self._latest_pzw}")

    def _open_worlded_folder(self, folder_path: str | None):
        if not folder_path:
            return
        folder = Path(folder_path)
        if not folder.exists():
            messagebox.showwarning("WorldEd", f"Folder not found: {folder}")
            return
        try:
            os.startfile(str(folder))
        except Exception as exc:
            messagebox.showerror("WorldEd", f"Could not open folder: {exc}")

    def _set_worlded_result(self, pzw_path: str | None):
        if pzw_path:
            self._latest_pzw = Path(pzw_path)
            self._open_pzw_btn.config(state="normal")
        else:
            self._latest_pzw = None
            self._open_pzw_btn.config(state="disabled")

    def _start_generation(self, full: bool, after_generate=None, *, tiles_root_override: Path | None = None):

        if self._busy:

            return

        px = max(0, int(self.var_prev_x.get()))

        py = max(0, int(self.var_prev_y.get()))

        preview_on = self._preview_enabled()

        if full:
            self.sound.generate_started()

        self._busy = True

        if not full:
            status_text = "Generating preview..." if preview_on else "Preview disabled."
        else:
            status_text = "Generating tiles + WorldEd export..." if after_generate else "Generating tiles..."

        self.status_var.set(status_text)

        self.update_idletasks()

        conf_copy = json.loads(json.dumps(self.conf))

        progress_popup = None

        report_callback = None

        if full:

            canvas = self.conf.get("canvas", {})

            cells_x = max(1, int(canvas.get("cells_x", 1)))

            cells_y = max(1, int(canvas.get("cells_y", 1)))

            total_tiles = cells_x * cells_y

            progress_popup = _TileProgressPopup(self, total_tiles)

            def report(done, total):

                self.after(0, lambda: progress_popup.update(done, total))

            report_callback = report

        tile_prefix = self.conf.get("export", {}).get("tile_prefix", "tiles")

        after_result = {}

        def worker():

            try:

                if full:
                    core.generate_tiles(conf_copy, tile_prefix, progress=report_callback,
                                        tile_root_override=tiles_root_override)
                    if after_generate:
                        result_payload = after_generate(conf_copy)
                        if isinstance(result_payload, dict):
                            after_result.update(result_payload)
                        elif result_payload is not None:
                            after_result["message"] = str(result_payload)
                else:

                    if preview_on:
                        core.generate_preview_from_config(conf_copy, px, py)

                def on_complete():

                    if progress_popup:

                        progress_popup.close()

                    self._update_thumbs()

                    if not full and preview_on:

                        self._animate_preview_fade()

                    self.sound.bubble()

                    self.sound.preview_ready()

                    if full:
                        self.sound.generate_completed()

                    worlded_path = after_result.get("pzw")
                    self._set_worlded_result(worlded_path)
                    if full and after_result.get("message"):
                        self.status_var.set(after_result["message"])
                    else:
                        final_status = "Live update complete." if not full else "Generation complete."
                        self.status_var.set(final_status)
                    if full and after_result.get("project_dir") and self.conf.get("worlded", {}).get("open_folder"):
                        self._open_worlded_folder(after_result.get("project_dir"))

                self.after(0, on_complete)

            except Exception as e:
                err_msg = str(e)

                def on_error():

                    if progress_popup:

                        progress_popup.close()

                    self.status_var.set("Generation failed.")

                    self.sound.oops()

                    messagebox.showerror("Error", err_msg)

                self.after(0, on_error)

            finally:

                self.after(0, lambda: setattr(self, "_busy", False))

        t = threading.Thread(target=worker, daemon=True)

        self._gen_thread = t

        t.start()

    def _preview_enabled(self) -> bool:
        return bool(self.conf.get("preview", {}).get("enabled", True))

    def _preview_thumb_enabled(self, key: str) -> bool:
        thumbs = self.conf.get("preview", {}).get("thumbs", {})
        return bool(thumbs.get(key, True))

    def _on_ctrl_r(self, event):
        self._show_roads_grid_popup()
        return "break"

    def _show_roads_grid_popup(self):
        if getattr(self, "_roads_grid_thread", None) and self._roads_grid_thread.is_alive():
            return
        popup = _RoadNetworkPopup(self, cells=5)

        def worker():
            try:
                data = self._generate_roads_grid_bytes(5)
            except Exception as exc:
                self.after(0, lambda: popup.set_error(str(exc)))
            else:
                self.after(0, lambda: popup.set_image(data))

        thread = threading.Thread(target=worker, daemon=True)
        self._roads_grid_thread = thread
        thread.start()

    def _generate_roads_grid_bytes(self, cells: int) -> bytes:
        cells = max(1, cells)
        conf_copy = json.loads(json.dumps(self.conf))
        canvas = conf_copy.setdefault("canvas", {})
        canvas["cells_x"] = cells
        canvas["cells_y"] = cells
        canvas.setdefault("cell_size", 300)
        with tempfile.TemporaryDirectory(prefix="zmg_roads_") as tmpdir:
            conf_copy["output_dir"] = tmpdir
            core.generate_from_config(conf_copy)
            exp = conf_copy.get("export", {})
            roads_name = exp.get("roads_png", "roads.png")
            roads_path = Path(tmpdir) / roads_name
            if not roads_path.exists():
                raise FileNotFoundError(f"Road output missing at {roads_path}")
            return roads_path.read_bytes()

    # ---------- Thumbnails ----------
    def _paths(self):
        out_dir = Path(self.conf.get("output_dir","output"))
        exp = self.conf.get("export", {})
        # respect config but fall back smartly
        t = out_dir / exp.get("terrain_png", "terrain.png")
        v = out_dir / exp.get("vegetation_png", "vegetation.png")
        r = out_dir / exp.get("roads_png", "roads.png")

        # combined might be preview.png or combined.png depending on writer/UI
        c = out_dir / exp.get("combined_png", "preview.png")
        if not c.exists():
            alt = self._pick_latest(out_dir, [exp.get("combined_png",""), "preview.png", "combined.png"])
            c = alt if alt else c
        l = out_dir / exp.get("lots_png", "lots.png")
        d = out_dir / exp.get("details_png", "details.png")
        return t, v, r, c, l, d


    def _set_thumb(self, key, path: Path):
        lbl = self._thumb_labels.get(key)
        if not lbl:
            return
        if not self._preview_enabled() or not self._preview_thumb_enabled(key):
            self._apply_thumb_dim(key, path)
            return
        lbl.configure(bg=THUMB_BG)
        if not path or not path.exists():
            lbl.configure(image="")
            self._thumb_imgs[key] = None
            self._thumb_last_paths[key] = path
            return
        img = self._open_image_fresh(path)
        img.thumbnail(THUMB_SIZE, Image.LANCZOS)
        imgtk = ImageTk.PhotoImage(img)
        lbl.configure(image=imgtk)
        self._thumb_imgs[key] = imgtk
        self._thumb_last_paths[key] = path

    def _update_thumbs(self):
        t_path, v_path, r_path, c_path, l_path, d_path = self._paths()

        self._set_thumb("terrain", t_path)
        self._set_thumb("vegetation", v_path)

        if c_path and c_path.exists():
            self._set_thumb("combo", c_path)
        else:
            # build combo from terrain+roads if writer didn’t emit combined
            if t_path.exists():
                img = self._open_image_fresh(t_path).convert("RGBA")
                if r_path.exists():
                    roads = self._open_image_fresh(r_path).convert("RGBA")
                    img.alpha_composite(roads)
                img.thumbnail(THUMB_SIZE, Image.LANCZOS)
                imgtk = ImageTk.PhotoImage(img)
                self._thumb_labels["combo"].configure(image=imgtk)
                self._thumb_imgs["combo"] = imgtk
            else:
                self._thumb_labels["combo"].configure(image="")
                self._thumb_imgs["combo"] = None

        self._set_thumb("roads", r_path)
        self._set_thumb("lots", l_path)
        self._set_thumb("details", d_path)

    def _apply_thumb_dim(self, key: str, path: Path | None):
        lbl = self._thumb_labels.get(key)
        if not lbl:
            return
        target = path or self._thumb_last_paths.get(key)
        if target and target.exists():
            dimmed = self._dim_thumb_photo(target)
            if dimmed:
                lbl.configure(image=dimmed)
                self._thumb_disabled_imgs[key] = dimmed
                return
        lbl.configure(image="")
        self._thumb_disabled_imgs.pop(key, None)

    def _dim_thumb_photo(self, path: Path) -> ImageTk.PhotoImage | None:
        try:
            img = self._open_image_fresh(path)
        except Exception:
            return None
        img.thumbnail(THUMB_SIZE, Image.LANCZOS)
        img = ImageEnhance.Brightness(img).enhance(0.35)
        img = ImageEnhance.Color(img).enhance(0.25)
        return ImageTk.PhotoImage(img)

    def _open_image_fresh(self, path: Path) -> Image.Image:
        # avoid stale handles/caching
        with Image.open(path) as im:
            im.load()
            return im.copy()

    def _animate_preview_fade(self):
        # Fade the combined preview image if available
        _, _, _, c_path, _, _ = self._paths()
        if not c_path or not c_path.exists():
            return
        try:
            base = self._open_image_fresh(c_path)
            base.thumbnail(THUMB_SIZE, Image.LANCZOS)
            steps = [0.5, 0.3, 0.15, 0.35, 0.6, 0.85, 1.0]
            imgs = []
            for f in steps:
                enh = ImageEnhance.Brightness(base)
                imgs.append(ImageTk.PhotoImage(enh.enhance(max(0.0, f))))

            lbl = self._thumb_labels.get("combo")
            if not lbl:
                return

            def _step(i=0):
                if i >= len(imgs):
                    return
                lbl.configure(image=imgs[i])
                # keep ref so it's not GC'ed
                self._thumb_imgs["combo"] = imgs[i]
                self.after(40, lambda: _step(i+1))
            _step(0)
        except Exception:
            pass

    def _preview_changed(self):
        # When spinboxes change, schedule a preview regen
        if self.var_live.get():
            self._schedule_regen()


class _TileProgressPopup:
    def __init__(self, parent, total: int):
        self._total = max(1, total)
        self._top = tk.Toplevel(parent)
        self._top.configure(bg="black")
        self._top.overrideredirect(True)
        self._top.attributes("-topmost", True)
        parent.update_idletasks()
        w, h = 220, 180
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self._top.geometry(f"{w}x{h}+{max(0,x)}+{max(0,y)}")
        self._symbol = tk.Label(self._top, text="∞", font=("Segoe UI", 68, "bold"), fg="#444", bg="black")
        self._symbol.pack(side=tk.TOP, pady=(20, 0))
        self._label = tk.Label(self._top, text=f"0% (0/{self._total})", font=("Segoe UI", 12), fg="white", bg="black")
        self._label.pack(side=tk.TOP, pady=(12, 0))
        self._steps = 24
        self._step = 0
        self._running = True
        self._closed = False
        self._animate_color()

    def update(self, done: int, total: int):
        if self._closed:
            return
        percent = min(100, int(done / total * 100)) if total else 100
        self._label.config(text=f"{percent}% ({done}/{total})")
        if percent >= 100:
            self.close()

    def _animate_color(self):
        if not self._running:
            return
        val = 100 + int((self._step / max(1, self._steps - 1)) * 155)
        color = f"#{val:02x}{val:02x}{val:02x}"
        self._symbol.config(fg=color)
        self._step = (self._step + 1) % self._steps
        self._top.after(120, self._animate_color)

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._running = False
        try:
            self._top.destroy()
        except Exception:
            pass

    def _open_image_viewer(self, path: Path):
        try:
            top = tk.Toplevel(self)
            top.title(str(path.name))
            top.configure(bg="#121212")
            xscroll = tk.Scrollbar(top, orient=tk.HORIZONTAL)
            yscroll = tk.Scrollbar(top, orient=tk.VERTICAL)
            canv = tk.Canvas(top, bg="#1b1b1b", xscrollcommand=xscroll.set, yscrollcommand=yscroll.set, highlightthickness=0)
            xscroll.config(command=canv.xview)
            yscroll.config(command=canv.yview)
            xscroll.pack(side=tk.BOTTOM, fill=tk.X)
            yscroll.pack(side=tk.RIGHT, fill=tk.Y)
            canv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            img = self._open_image_fresh(path)
            imgtk = ImageTk.PhotoImage(img)
            canv.create_image(0, 0, anchor="nw", image=imgtk)
            canv.image = imgtk
            canv.config(scrollregion=(0, 0, img.width, img.height))
            top.geometry(f"{min(1200, img.width+32)}x{min(800, img.height+32)}")
        except Exception:
            try:
                if sys.platform.startswith("win"): os.startfile(str(path))
                elif sys.platform == "darwin": os.system(f'open "{path}"')
                else: os.system(f'xdg-open "{path}"')
            except Exception:
                pass

    def _pick_latest(self, out_dir: Path, candidates: list[str]) -> Path | None:
        latest = None; lm = -1
        for name in candidates:
            p = out_dir / name
            if p.exists():
                m = p.stat().st_mtime
                if m > lm: latest, lm = p, m
        return latest


class _RoadNetworkPopup:
    def __init__(self, parent, cells: int):
        self._top = tk.Toplevel(parent)
        self._top.title(f"{cells}×{cells} Road Network")
        self._top.configure(bg="#121212")
        self._top.transient(parent)
        self._top.resizable(True, True)
        self._cells = cells
        self._label = tk.Label(self._top, text=f"Generating {cells}×{cells} road network...", bg="#121212", fg="white")
        self._label.pack(padx=12, pady=(12, 4))
        self._img_label = tk.Label(self._top, text="Please wait...", bg="#121212", fg="white")
        self._img_label.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        self._status = tk.Label(self._top, text="Starting...", bg="#121212", fg="white")
        self._status.pack(padx=12, pady=(0, 12))
        close = tk.Button(self._top, text="Close", command=self._top.destroy, bg="#2a2a2a", fg="white")
        close.pack(pady=(0, 12))
        self._img_ref = None

    def set_image(self, data: bytes):
        if not self._top.winfo_exists():
            return
        try:
            img = Image.open(io.BytesIO(data))
            img.thumbnail((1100, 1100), Image.LANCZOS)
            imgtk = ImageTk.PhotoImage(img)
            self._img_label.configure(image=imgtk, text="")
            self._img_ref = imgtk
            self._status.configure(text="Road network generated.")
        except Exception as exc:
            self.set_error(str(exc))

    def set_error(self, message: str):
        if not self._top.winfo_exists():
            return
        self._img_label.configure(text="Failed to show road network", image="")
        self._status.configure(text=message or "Unknown error.")



def main():
    app = InfinitXYZApp()
    app.mainloop()


if __name__ == "__main__":
    main()

