"""Tkinter GUI for editing Rules.txt, Blends.txt, and tile previews."""
from __future__ import annotations

import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageTk

from .data_manager import RulesBlendsManager, TileEntry, TileLibrary
from .models import AliasRule, BlendRule


class RulesBlendsApp:
    """Main application window that coordinates data and the preview/uplift."""

    ISO_LABEL = "26.67deg isometric preview"
    TILE_WIDTH = 128
    TILE_HEIGHT = 256
    TILE_INDEX_PATTERN = re.compile(r"^(?P<base>.+?)_(?P<index>[0-9]+)$")

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Rules & Blends Editor")
        self.root.geometry("1400x760")
        self.base_dir = Path(__file__).resolve().parents[1]

        rules_path = self.base_dir / "vanilla" / "Rules.txt"
        blends_path = self.base_dir / "vanilla" / "Blends.txt"

        self.manager = RulesBlendsManager(
            rules_path=rules_path,
            blends_path=blends_path,
        )
        self.tile_library = TileLibrary(
            [self.base_dir / "vanilla" / "2x", self.base_dir / "custom_tiles"]
        )
        self.tile_library.scan()

        self.alias_by_iid: Dict[str, AliasRule] = {}
        self.blend_by_iid: Dict[str, BlendRule] = {}
        self.visible_tiles: List[TileEntry] = []
        self.preview_photo_main: Optional[ImageTk.PhotoImage] = None
        self.preview_photo_blend: Optional[ImageTk.PhotoImage] = None

        self.status_var = tk.StringVar(value="Ready")
        self.preview_status_var = tk.StringVar(value=self.ISO_LABEL)
        self.tile_count_var = tk.StringVar(value="0 tiles")
        self.tileset_index_var = tk.StringVar(value="Tileset preview")
        self.tileset_index_state: Dict[str, int] = {}
        self.tileset_layout_cache: Dict[str, Tuple[int, int, int]] = {}
        self.current_tileset_entry: Optional[TileEntry] = None

        self._setup_ui()
        self.reload_all()

    def _setup_ui(self) -> None:
        main_frame = ttk.Frame(self.root, padding=8)
        main_frame.pack(fill="both", expand=True)

        paned = ttk.PanedWindow(main_frame, orient="horizontal")
        paned.pack(fill="both", expand=True)

        self._build_tile_panel(paned)
        self._build_preview_panel(paned)
        self._build_editor_panel(paned)

        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill="x", pady=(8, 0))
        ttk.Button(action_frame, text="Reload All", command=self.reload_all).pack(
            side="left", padx=(0, 4)
        )
        ttk.Button(action_frame, text="Save Rules", command=self.save_rules).pack(
            side="left", padx=(0, 4)
        )
        ttk.Button(action_frame, text="Save Blends", command=self.save_blends).pack(
            side="left", padx=(0, 4)
        )
        ttk.Label(action_frame, textvariable=self.status_var).pack(side="left", padx=8)

    def _build_tile_panel(self, paned: ttk.PanedWindow) -> None:
        tile_frame = ttk.Labelframe(paned, text="Tile selector", width=260)
        paned.add(tile_frame, weight=1)

        ttk.Label(tile_frame, textvariable=self.tile_count_var).pack(anchor="w")

        list_frame = ttk.Frame(tile_frame)
        list_frame.pack(fill="both", expand=True, pady=(4, 4))

        self.tile_listbox = tk.Listbox(list_frame, height=20)
        scrollbar = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.tile_listbox.yview
        )
        self.tile_listbox.config(yscrollcommand=scrollbar.set)
        self.tile_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tile_listbox.bind("<<ListboxSelect>>", self._on_tile_selected)

        btn_frame = ttk.Frame(tile_frame)
        btn_frame.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_frame, text="Reload Tiles", command=self._reload_tiles).pack(
            side="left"
        )
        ttk.Button(btn_frame, text="Add tiles folder", command=self._add_tileset_dir).pack(
            side="left", padx=(4, 0)
        )

    def _build_preview_panel(self, paned: ttk.PanedWindow) -> None:
        preview_frame = ttk.Labelframe(paned, text="Isometric Preview", width=420)
        paned.add(preview_frame, weight=2)

        self.preview_canvas = tk.Canvas(
            preview_frame, width=420, height=320, bg="#131313", highlightthickness=0
        )
        self.preview_canvas.pack(fill="both", expand=True, padx=6, pady=6)

        nav_frame = ttk.Frame(preview_frame)
        nav_frame.pack(fill="x", pady=(0, 4))
        ttk.Button(
            nav_frame,
            text="<",
            width=3,
            command=lambda: self._advance_tileset_preview(-1),
        ).pack(side="left")
        ttk.Label(nav_frame, textvariable=self.tileset_index_var).pack(
            side="left", expand=True, anchor="center"
        )
        ttk.Button(
            nav_frame,
            text=">",
            width=3,
            command=lambda: self._advance_tileset_preview(1),
        ).pack(side="right")

        ttk.Label(preview_frame, textvariable=self.preview_status_var).pack(
            pady=(0, 4)
        )
        self.root.after(100, self._draw_preview)  # ensure canvas size

    def _build_editor_panel(self, paned: ttk.PanedWindow) -> None:
        editor_frame = ttk.Frame(paned)
        paned.add(editor_frame, weight=3)

        notebook = ttk.Notebook(editor_frame)
        notebook.pack(fill="both", expand=True)

        self._build_rules_tab(notebook)
        self._build_blends_tab(notebook)

    def _build_rules_tab(self, notebook: ttk.Notebook) -> None:
        rules_tab = ttk.Frame(notebook)
        notebook.add(rules_tab, text="Rules")

        self.rules_tree = ttk.Treeview(
            rules_tab, columns=("name",), show="headings", selectmode="browse"
        )
        self.rules_tree.heading("name", text="Alias Name")
        self.rules_tree.column("name", width=320)
        self.rules_tree.bind("<<TreeviewSelect>>", self._on_alias_selected)
        self.rules_tree.pack(fill="both", expand=True, padx=6, pady=(6, 2))

        form = ttk.Frame(rules_tab)
        form.pack(fill="x", padx=6, pady=(4, 6))
        ttk.Label(form, text="Alias Name").grid(row=0, column=0, sticky="w")
        self.rule_name_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.rule_name_var, width=40).grid(
            row=0, column=1, sticky="ew", padx=(4, 0)
        )
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Tiles (one per line)").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )
        self.rule_tiles_text = tk.Text(form, height=5, wrap="none")
        self.rule_tiles_text.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(2, 0))

        ttk.Button(
            form, text="Apply alias edits", command=self._apply_alias_changes
        ).grid(row=3, column=0, columnspan=2, pady=(6, 0))

    def _build_blends_tab(self, notebook: ttk.Notebook) -> None:
        blends_tab = ttk.Frame(notebook)
        notebook.add(blends_tab, text="Blends")

        self.blend_tree = ttk.Treeview(
            blends_tab,
            columns=("layer", "main", "blend", "dir"),
            show="headings",
            selectmode="browse",
        )
        self.blend_tree.heading("layer", text="Layer")
        self.blend_tree.heading("main", text="Main Tile")
        self.blend_tree.heading("blend", text="Blend Tile")
        self.blend_tree.heading("dir", text="Direction")
        self.blend_tree.column("layer", width=120)
        self.blend_tree.column("main", width=120)
        self.blend_tree.column("blend", width=120)
        self.blend_tree.column("dir", width=80)
        self.blend_tree.pack(fill="both", expand=True, padx=6, pady=(6, 2))
        self.blend_tree.bind("<<TreeviewSelect>>", self._on_blend_selected)

        form = ttk.Frame(blends_tab)
        form.pack(fill="x", padx=6, pady=(4, 6))
        ttk.Label(form, text="Layer").grid(row=0, column=0, sticky="w")
        self.blend_layer_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.blend_layer_var, width=24).grid(
            row=0, column=1, sticky="ew", padx=(4, 0)
        )
        ttk.Label(form, text="Direction").grid(row=0, column=2, sticky="w", padx=(16, 0))
        self.blend_dir_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.blend_dir_var, width=12).grid(
            row=0, column=3, sticky="ew", padx=(4, 0)
        )
        form.columnconfigure(3, weight=1)

        ttk.Label(form, text="Main Tile").grid(row=1, column=0, sticky="w")
        self.blend_main_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.blend_main_var, width=24).grid(
            row=1, column=1, sticky="ew", padx=(4, 0)
        )
        ttk.Label(form, text="Blend Tile").grid(row=1, column=2, sticky="w", padx=(16, 0))
        self.blend_tile_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.blend_tile_var, width=24).grid(
            row=1, column=3, sticky="ew", padx=(4, 0)
        )

        ttk.Label(form, text="Extras (key = value)").grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(8, 0)
        )
        self.blend_extras_text = tk.Text(form, height=5, wrap="none")
        self.blend_extras_text.grid(
            row=3, column=0, columnspan=4, sticky="ew", pady=(2, 0)
        )

        ttk.Button(
            form, text="Apply blend edits", command=self._apply_blend_changes
        ).grid(row=4, column=0, columnspan=4, pady=(6, 0))

    def reload_all(self) -> None:
        self.reload_rules()
        self.reload_blends()
        self._reload_tiles()

    def reload_rules(self) -> None:
        try:
            self.manager.load_rules()
            self._populate_rules_tree()
            self.status_var.set("Rules reloaded")
        except Exception as exc:  # pragma: no cover - UI failure
            messagebox.showerror("Rules reload failed", str(exc))
            self.status_var.set("Rules reload failed")

    def reload_blends(self) -> None:
        try:
            self.manager.load_blends()
            self._populate_blends_tree()
            self.status_var.set("Blends reloaded")
        except Exception as exc:  # pragma: no cover - UI failure
            messagebox.showerror("Blends reload failed", str(exc))
            self.status_var.set("Blends reload failed")

    def _reload_tiles(self) -> None:
        self.tileset_layout_cache.clear()
        self.tile_library.scan()
        self.visible_tiles = list(self.tile_library.list_tiles())
        self.tile_listbox.delete(0, tk.END)
        for entry in self.visible_tiles:
            self.tile_listbox.insert(tk.END, entry.display_label())
        self.tile_count_var.set(f"{len(self.visible_tiles)} tiles")
        self.status_var.set("Tiles reloaded")

    def _add_tileset_dir(self) -> None:
        folder = filedialog.askdirectory(initialdir=str(self.base_dir))
        if folder:
            self.tile_library.add_search_path(Path(folder))
            self._reload_tiles()
            self.status_var.set(f"Added tiles folder {Path(folder).name}")

    def _populate_rules_tree(self) -> None:
        self.rules_tree.delete(*self.rules_tree.get_children())
        self.alias_by_iid.clear()
        for idx, alias in enumerate(self.manager.aliases):
            iid = f"alias_{idx}"
            self.alias_by_iid[iid] = alias
            self.rules_tree.insert("", "end", iid, values=(alias.name,))

    def _populate_blends_tree(self) -> None:
        self.blend_tree.delete(*self.blend_tree.get_children())
        self.blend_by_iid.clear()
        for idx, blend in enumerate(self.manager.blends):
            iid = f"blend_{idx}"
            self.blend_by_iid[iid] = blend
            self.blend_tree.insert(
                "",
                "end",
                iid,
                values=(
                    blend.layer,
                    blend.main_tile,
                    blend.blend_tile,
                    blend.direction,
                ),
            )

    def _on_tile_selected(self, event: tk.Event) -> None:
        selection = self.tile_listbox.curselection()
        if not selection:
            return
        entry = self.visible_tiles[selection[0]]
        self.current_tileset_entry = entry
        key = str(entry.path)
        index = self.tileset_index_state.get(key, 0)
        self.tileset_index_state[key] = index
        self._draw_preview(
            main_entry=entry,
            main_index=index,
            tileset_entry=entry,
            tileset_index=index,
        )
        self.status_var.set(f"Tile selected: {entry.display_label()}")

    def _on_alias_selected(self, event: tk.Event) -> None:
        selection = self.rules_tree.selection()
        if not selection:
            return
        alias = self.alias_by_iid[selection[0]]
        self.rule_name_var.set(alias.name)
        self.rule_tiles_text.delete("1.0", tk.END)
        self.rule_tiles_text.insert("1.0", "\n".join(alias.tiles))
        primary_tile = alias.tiles[0] if alias.tiles else None
        self._draw_preview_from_names(main_name=primary_tile)
        self.status_var.set(f"Alias selected: {alias.name}")

    def _on_blend_selected(self, event: tk.Event) -> None:
        selection = self.blend_tree.selection()
        if not selection:
            return
        blend = self.blend_by_iid[selection[0]]
        self.blend_layer_var.set(blend.layer)
        self.blend_dir_var.set(blend.direction)
        self.blend_main_var.set(blend.main_tile)
        self.blend_tile_var.set(blend.blend_tile)
        extras_lines = [f"{k} = {v}" for k, v in blend.extras.items()]
        self.blend_extras_text.delete("1.0", tk.END)
        self.blend_extras_text.insert("1.0", "\n".join(extras_lines))
        self._draw_preview_from_names(
            main_name=blend.main_tile, blend_name=blend.blend_tile
        )
        self.status_var.set(
            f"Blend selected: {blend.layer} ({blend.direction})"
        )

    def _apply_alias_changes(self) -> None:
        selection = self.rules_tree.selection()
        if not selection:
            messagebox.showinfo("No selection", "Please choose an alias first.")
            return
        alias = self.alias_by_iid[selection[0]]
        new_name = self.rule_name_var.get().strip()
        tiles = [
            line.strip()
            for line in self.rule_tiles_text.get("1.0", tk.END).splitlines()
            if line.strip()
        ]
        if new_name:
            alias.name = new_name
        alias.tiles = tiles
        self.rules_tree.item(selection[0], values=(alias.name,))
        self.status_var.set(f"Alias saved: {alias.name}")
        self._draw_preview_from_names(main_name=tiles[0] if tiles else None)

    def _apply_blend_changes(self) -> None:
        selection = self.blend_tree.selection()
        if not selection:
            messagebox.showinfo("No selection", "Please choose a blend first.")
            return
        blend = self.blend_by_iid[selection[0]]
        blend.layer = self.blend_layer_var.get().strip()
        blend.direction = self.blend_dir_var.get().strip()
        blend.main_tile = self.blend_main_var.get().strip()
        blend.blend_tile = self.blend_tile_var.get().strip()
        extras = {}
        for line in self.blend_extras_text.get("1.0", tk.END).splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            extras[key.strip()] = value.strip()
        blend.extras = extras
        self.blend_tree.item(
            selection[0],
            values=(
                blend.layer,
                blend.main_tile,
                blend.blend_tile,
                blend.direction,
            ),
        )
        self.status_var.set(f"Blend saved: {blend.layer}")
        self._draw_preview_from_names(
            main_name=blend.main_tile, blend_name=blend.blend_tile
        )

    def _advance_tileset_preview(self, delta: int) -> None:
        entry = self.current_tileset_entry
        if not entry:
            return
        cols, rows, total = self._tileset_layout_for_entry(entry)
        if total == 0:
            return
        key = str(entry.path)
        current_index = self.tileset_index_state.get(key, 0)
        next_index = max(0, min(total - 1, current_index + delta))
        self.tileset_index_state[key] = next_index
        self._draw_preview(
            main_entry=entry,
            main_index=next_index,
            tileset_entry=entry,
            tileset_index=next_index,
        )
        self.status_var.set(
            f"Tileset {entry.display_label()} tile {next_index + 1}/{total}"
        )

    def save_rules(self) -> None:
        try:
            self.manager.save_rules()
            self.status_var.set("Rules saved")
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))
            self.status_var.set("Failed to save rules")

    def save_blends(self) -> None:
        try:
            self.manager.save_blends()
            self.status_var.set("Blends saved")
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))
            self.status_var.set("Failed to save blends")

    def _draw_preview_from_names(
        self, main_name: Optional[str] = None, blend_name: Optional[str] = None
    ) -> None:
        main_entry, main_index = self._resolve_tile_reference(main_name)
        blend_entry, blend_index = self._resolve_tile_reference(blend_name)
        self._draw_preview(
            main_entry=main_entry,
            blend_entry=blend_entry,
            main_index=main_index,
            blend_index=blend_index,
        )

    def _resolve_tile_reference(
        self, tile_name: Optional[str]
    ) -> tuple[Optional[TileEntry], Optional[int]]:
        if not tile_name:
            return None, None
        entry_name = tile_name
        index: Optional[int] = None
        match = self.TILE_INDEX_PATTERN.match(tile_name)
        if match:
            entry_name = match.group("base")
            try:
                index = int(match.group("index"))
            except ValueError:
                index = None
        entry = self.tile_library.find_best_match(entry_name)
        if entry is None or index is None:
            return entry, index
        cols, rows, total = self._tileset_layout_for_entry(entry)
        if total == 0:
            return entry, None
        adjusted = index
        if adjusted >= total and adjusted > 0:
            adjusted -= 1
        adjusted = max(0, min(adjusted, total - 1))
        return entry, adjusted

    def _load_tile_image(
        self, entry: TileEntry, tile_index: Optional[int] = None
    ) -> Optional[ImageTk.PhotoImage]:
        try:
            with Image.open(entry.path) as image:
                image = image.convert("RGBA")
                if tile_index is not None:
                    image = self._crop_tileset_tile(entry, image, tile_index)
                resample = (
                    Image.Resampling.LANCZOS
                    if hasattr(Image, "Resampling")
                    else Image.ANTIALIAS
                )
                image.thumbnail((200, 320), resample)
                return ImageTk.PhotoImage(image)
        except Exception:
            return None

    def _crop_tileset_tile(
        self, entry: TileEntry, image: Image.Image, tile_index: int
    ) -> Image.Image:
        cols, rows, total = self._tileset_layout_for_entry(entry, image.size)
        if total == 0:
            return image
        index = max(0, min(tile_index, total - 1))
        col = index % cols
        row = index // cols
        left = col * self.TILE_WIDTH
        top = row * self.TILE_HEIGHT
        right = min(left + self.TILE_WIDTH, image.width)
        bottom = min(top + self.TILE_HEIGHT, image.height)
        return image.crop((left, top, right, bottom))

    def _tileset_layout_for_entry(
        self, entry: TileEntry, provided_size: Optional[Tuple[int, int]] = None
    ) -> Tuple[int, int, int]:
        key = str(entry.path)
        if provided_size is None and key in self.tileset_layout_cache:
            return self.tileset_layout_cache[key]
        if provided_size:
            width, height = provided_size
        else:
            try:
                with Image.open(entry.path) as image:
                    width, height = image.size
            except Exception:
                return 0, 0, 0
        cols = width // self.TILE_WIDTH if width else 0
        rows = height // self.TILE_HEIGHT if height else 0
        total = cols * rows
        self.tileset_layout_cache[key] = (cols, rows, total)
        return cols, rows, total

    def _draw_preview(
        self,
        *,
        main_entry: Optional[TileEntry] = None,
        blend_entry: Optional[TileEntry] = None,
        main_index: Optional[int] = None,
        blend_index: Optional[int] = None,
        tileset_entry: Optional[TileEntry] = None,
        tileset_index: Optional[int] = None,
    ) -> None:
        self.preview_canvas.delete("all")
        width = int(self.preview_canvas["width"])
        height = int(self.preview_canvas["height"])
        center_x = width // 2
        center_y = int(height * 0.65)

        self.preview_canvas.create_text(
            10, 10, anchor="nw", fill="#e0e0e0", text=self.ISO_LABEL
        )

        def diamond_points(offset_y: int = 0) -> List[int]:
            w = 160
            h = 70
            return [
                center_x,
                center_y - h // 2 + offset_y,
                center_x + w // 2,
                center_y + offset_y,
                center_x,
                center_y + h // 2 + offset_y,
                center_x - w // 2,
                center_y + offset_y,
            ]

        self.preview_canvas.create_polygon(
            diamond_points(),
            fill="#2a3c6d",
            outline="#4f6cb2",
            width=2,
            stipple="gray12",
        )

        if blend_entry:
            self.preview_canvas.create_polygon(
                diamond_points(offset_y=-6),
                fill="#5b8c3b",
                outline="#87b56a",
                width=2,
                stipple="gray25",
            )

        self.preview_photo_main = (
            self._load_tile_image(main_entry, main_index) if main_entry else None
        )
        if self.preview_photo_main:
            self.preview_canvas.create_image(
                center_x,
                center_y + 40,
                image=self.preview_photo_main,
                anchor="s",
            )

        self.preview_photo_blend = (
            self._load_tile_image(blend_entry, blend_index) if blend_entry else None
        )
        if self.preview_photo_blend:
            self.preview_canvas.create_image(
                center_x + 16,
                center_y + 20,
                image=self.preview_photo_blend,
                anchor="s",
            )

        if tileset_entry is not None and tileset_index is not None:
            cols, rows, total = self._tileset_layout_for_entry(tileset_entry)
            total_label = total or "?"
            if total:
                display_idx = min(max(1, tileset_index + 1), total)
            else:
                display_idx = tileset_index + 1
            self.tileset_index_var.set(
                f"{tileset_entry.display_label()} {display_idx}/{total_label}"
            )
            self.preview_status_var.set(
                f"Tileset preview · {tileset_entry.display_label()} ({display_idx}/{total_label})"
            )
        else:
            self.tileset_index_var.set("Tileset preview")
            captions: List[str] = []
            if main_entry:
                captions.append(f"Main: {main_entry.display_label()}")
            if blend_entry:
                captions.append(f"Blend: {blend_entry.display_label()}")
            self.preview_status_var.set(" | ".join(captions) or self.ISO_LABEL)


def run_app() -> None:
    """Helper to instantiate and run the GUI."""
    root = tk.Tk()
    RulesBlendsApp(root)
    root.mainloop()
