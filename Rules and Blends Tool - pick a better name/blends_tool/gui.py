"""Tkinter GUI tailored to editing blend entries and their exclusions."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path
from typing import List

from .manager import BlendRepository
from .models import BlendEntry


class BlendsEditorApp:
    """Thin wrapper around a Tkinter window that edits blends."""

    def __init__(self, root: tk.Tk, repository: BlendRepository) -> None:
        self.root = root
        self.repo = repository
        self.repo.load()
        self.current_index: int | None = None

        self.filter_var = tk.StringVar()
        self.layer_var = tk.StringVar()
        self.main_var = tk.StringVar()
        self.blend_var = tk.StringVar()
        self.dir_var = tk.StringVar()
        self.exclude_entry_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")

        self._build_ui()
        self._refresh_list()

    def _build_ui(self) -> None:
        self.root.title("Blends Editor")
        self.root.geometry("900x520")

        container = ttk.Frame(self.root, padding=8)
        container.pack(fill="both", expand=True)

        notebook = ttk.Notebook(container)
        notebook.pack(fill="both", expand=True)

        preview_tab = ttk.Frame(notebook)
        editor_tab = ttk.Frame(notebook)
        notebook.add(preview_tab, text="Preview")
        notebook.add(editor_tab, text="Blends")

        self.preview_enabled = tk.BooleanVar(value=True)
        self._build_preview_tab(preview_tab)

        paned = ttk.PanedWindow(editor_tab, orient="horizontal")
        paned.pack(fill="both", expand=True)

        self._build_list_panel(paned)
        self._build_detail_panel(paned)

        action_row = ttk.Frame(container)
        action_row.pack(fill="x", pady=(6, 0))
        ttk.Button(action_row, text="Reload", command=self._reload).pack(side="left")
        ttk.Button(action_row, text="Save", command=self._save).pack(side="left", padx=(4, 0))
        ttk.Label(action_row, textvariable=self.status_var).pack(side="right")

    def _build_list_panel(self, paned: ttk.PanedWindow) -> None:
        frame = ttk.Labelframe(paned, text="Blend entries", width=280)
        paned.add(frame, weight=1)

        ttk.Label(frame, text="Filter by main tile").pack(anchor="w")
        filter_entry = ttk.Entry(frame, textvariable=self.filter_var)
        filter_entry.pack(fill="x")
        filter_entry.bind("<KeyRelease>", lambda event: self._refresh_list())

        self.listbox = tk.Listbox(frame, height=25)
        self.listbox.pack(fill="both", expand=True, pady=(4, 0))
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        move_frame = ttk.Frame(frame)
        move_frame.pack(fill="x", pady=(4, 0))
        ttk.Button(move_frame, text="Move up", command=lambda: self._move_selection(-1)).pack(
            side="left"
        )
        ttk.Button(
            move_frame,
            text="Move down",
            command=lambda: self._move_selection(1),
        ).pack(side="left", padx=(4, 0))

        ttk.Label(frame, text=f"File: {self.repo.source}").pack(anchor="w", pady=(4, 0))

    def _build_preview_tab(self, parent: ttk.Frame) -> None:
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)

        toolbar = ttk.Frame(frame)
        toolbar.pack(fill="x")
        ttk.Checkbutton(
            toolbar,
            text="Enable preview",
            variable=self.preview_enabled,
            command=self._refresh_preview,
        ).pack(side="left")

        self.preview_canvas = tk.Canvas(
            frame, bg="black", highlightthickness=0, height=260
        )
        self.preview_canvas.pack(fill="both", expand=True, pady=(6, 0))
        self.preview_canvas.bind("<Configure>", lambda event: self._refresh_preview())

        self._refresh_preview()

    def _refresh_preview(self) -> None:
        if not hasattr(self, "preview_canvas"):
            return
        self.preview_canvas.delete("all")
        width = self.preview_canvas.winfo_width() or 400
        height = self.preview_canvas.winfo_height() or 240
        if not self.preview_enabled.get():
            self.preview_canvas.create_rectangle(
                0, 0, width, height, fill="black", outline=""
            )
            return
        center_x = width // 2
        center_y = height // 2
        outer = 160
        inner = 100
        self.preview_canvas.create_polygon(
            [
                center_x,
                center_y - outer // 2,
                center_x + outer // 2,
                center_y,
                center_x,
                center_y + outer // 2,
                center_x - outer // 2,
                center_y,
            ],
            fill="#2a3c6d",
            outline="#4f6cb2",
            width=2,
        )
        self.preview_canvas.create_polygon(
            [
                center_x,
                center_y - inner // 2,
                center_x + inner // 2,
                center_y,
                center_x,
                center_y + inner // 2,
                center_x - inner // 2,
                center_y,
            ],
            fill="#4f5f7d",
            outline="#7e8fab",
            width=2,
        )

    def _build_detail_panel(self, paned: ttk.PanedWindow) -> None:
        frame = ttk.Labelframe(paned, text="Blend detail")
        paned.add(frame, weight=2)

        grid_frame = ttk.Frame(frame)
        grid_frame.pack(fill="x")

        ttk.Label(grid_frame, text="Layer").grid(row=0, column=0, sticky="w")
        ttk.Entry(grid_frame, textvariable=self.layer_var).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        ttk.Label(grid_frame, text="Main tile").grid(row=1, column=0, sticky="w")
        ttk.Entry(grid_frame, textvariable=self.main_var).grid(row=1, column=1, sticky="ew", padx=(4, 0))

        ttk.Label(grid_frame, text="Blend tile").grid(row=2, column=0, sticky="w")
        ttk.Entry(grid_frame, textvariable=self.blend_var).grid(row=2, column=1, sticky="ew", padx=(4, 0))

        ttk.Label(grid_frame, text="Direction").grid(row=3, column=0, sticky="w")
        ttk.Entry(grid_frame, textvariable=self.dir_var).grid(row=3, column=1, sticky="ew", padx=(4, 0))

        grid_frame.columnconfigure(1, weight=1)

        exclude_frame = ttk.LabelFrame(frame, text="Exclusions")
        exclude_frame.pack(fill="both", expand=True, pady=(8, 0))

        self.exclude_listbox = tk.Listbox(exclude_frame, height=8, selectmode="extended")
        self.exclude_listbox.pack(fill="both", expand=True, side="left")
        scrollbar = ttk.Scrollbar(exclude_frame, orient="vertical", command=self.exclude_listbox.yview)
        self.exclude_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="left", fill="y")

        exclude_actions = ttk.Frame(frame)
        exclude_actions.pack(fill="x", pady=(4, 0))
        ttk.Entry(exclude_actions, textvariable=self.exclude_entry_var).pack(side="left", fill="x", expand=True)
        ttk.Button(exclude_actions, text="Add", command=self._add_exclusion).pack(side="left", padx=(4, 0))
        ttk.Button(exclude_actions, text="Remove selected", command=self._remove_exclusion).pack(
            side="left", padx=(4, 0)
        )

        extras_frame = ttk.LabelFrame(frame, text="Extras")
        extras_frame.pack(fill="both", expand=True, pady=(6, 0))
        self.extras_text = tk.Text(extras_frame, height=5, wrap="word")
        self.extras_text.pack(fill="both", expand=True)

        bottom_row = ttk.Frame(frame)
        bottom_row.pack(fill="x", pady=(6, 0))
        ttk.Button(
            bottom_row, text="Optimize by priority", command=self._optimize
        ).pack(side="left")
        ttk.Button(bottom_row, text="New blank entry", command=self._create_entry).pack(side="left", padx=(4, 0))
        ttk.Button(bottom_row, text="Delete entry", command=self._delete_entry).pack(side="left", padx=(4, 0))

    def _refresh_list(self) -> None:
        self.listbox.delete(0, tk.END)
        filter_term = self.filter_var.get().lower()
        for idx, entry in enumerate(self.repo.entries):
            if filter_term and filter_term not in entry.main_tile.lower():
                continue
            self.listbox.insert(tk.END, f"{idx+1:04d}: {entry.display_label}")
        self._reselect_current()

    def _on_select(self, event: tk.Event) -> None:
        selection = self.listbox.curselection()
        if not selection:
            return
        visible_indexes = self._listbox_visible_indexes()
        self.current_index = visible_indexes[selection[0]]
        self._load_entry(self.repo.entries[self.current_index])

    def _listbox_visible_indexes(self) -> List[int]:
        choices = []
        filter_term = self.filter_var.get().lower()
        for idx, entry in enumerate(self.repo.entries):
            if filter_term and filter_term not in entry.main_tile.lower():
                continue
            choices.append(idx)
        return choices

    def _load_entry(self, entry: BlendEntry) -> None:
        self.layer_var.set(entry.layer)
        self.main_var.set(entry.main_tile)
        self.blend_var.set(entry.blend_tile)
        self.dir_var.set(entry.direction)
        self.exclude_listbox.delete(0, tk.END)
        for value in entry.exclude:
            self.exclude_listbox.insert(tk.END, value)
        extras_lines = [f"{key} = {value}" for key, value in entry.extras.items()]
        self.extras_text.delete("1.0", tk.END)
        self.extras_text.insert("1.0", "\n".join(extras_lines))

    def _move_selection(self, delta: int) -> None:
        selection = self.listbox.curselection()
        if not selection:
            return
        visible = self._listbox_visible_indexes()
        idx = visible[selection[0]]
        target = idx + delta
        if not (0 <= target < len(self.repo.entries)):
            return
        entries = self.repo.entries
        entries[idx], entries[target] = entries[target], entries[idx]
        self.current_index = target
        self._refresh_list()
        self.listbox.selection_clear(0, tk.END)
        visible_after = self._listbox_visible_indexes()
        if target in visible_after:
            new_index = visible_after.index(target)
            self.listbox.selection_set(new_index)
            self.listbox.event_generate("<<ListboxSelect>>")

    def _reselect_current(self) -> None:
        if self.current_index is None:
            return
        visible = self._listbox_visible_indexes()
        if self.current_index in visible:
            pos = visible.index(self.current_index)
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(pos)
        else:
            self.listbox.selection_clear(0, tk.END)

    def _update_current_entry(self) -> None:
        if self.current_index is None:
            return
        entry = self.repo.entries[self.current_index]
        entry.layer = self.layer_var.get()
        entry.main_tile = self.main_var.get()
        entry.blend_tile = self.blend_var.get()
        entry.direction = self.dir_var.get()
        entry.exclude = list(self.exclude_listbox.get(0, tk.END))
        extras_lines = [
            line for line in self.extras_text.get("1.0", tk.END).splitlines() if "=" in line
        ]
        extras: dict[str, str] = {}
        for line in extras_lines:
            key, value = line.split("=", 1)
            extras[key.strip()] = value.strip()
        entry.extras = extras

    def _add_exclusion(self) -> None:
        value = self.exclude_entry_var.get().strip()
        if not value:
            return
        existing = list(self.exclude_listbox.get(0, tk.END))
        if value in existing:
            return
        self.exclude_listbox.insert(tk.END, value)
        self.exclude_entry_var.set("")
        self._update_current_entry()

    def _remove_exclusion(self) -> None:
        selection = list(self.exclude_listbox.curselection())
        for idx in reversed(selection):
            self.exclude_listbox.delete(idx)
        self._update_current_entry()

    def _optimize(self) -> None:
        self._update_current_entry()
        self.repo.optimize_exclusions_from_priority()
        self._refresh_list()
        if self.current_index is not None:
            self._load_entry(self.repo.entries[self.current_index])
        self.status_var.set("Optimized exclusions based on priority order")

    def _create_entry(self) -> None:
        new_entry = BlendEntry(layer="", main_tile="", blend_tile="", direction="", exclude=[], extras={})
        self.repo.entries.append(new_entry)
        self._refresh_list()
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(tk.END)
        self.listbox.event_generate("<<ListboxSelect>>")
        self.status_var.set("New entry created")

    def _delete_entry(self) -> None:
        if self.current_index is None:
            return
        deleted = self.repo.entries.pop(self.current_index)
        self.current_index = None
        self._refresh_list()
        self.status_var.set(f"Deleted {deleted.display_label}")

    def _reload(self) -> None:
        self.repo.load()
        self.current_index = None
        self._refresh_list()
        self.status_var.set("Reloaded blends")

    def _save(self) -> None:
        self._update_current_entry()
        self.repo.save()
        self.status_var.set("Blends saved")
