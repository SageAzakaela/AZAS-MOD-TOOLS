import tkinter as tk
from tkinter import ttk

from ...core import AppContext
from ... import search as search_utils
from ..styles import ACCENT_CYAN, LIGHT_TEXT, PANEL_BG, SECONDARY_TEXT

SOURCE_FILTERS = ["All", "Broadcast", "Channel", "Voice", "Recorded Media"]


def make_tab(parent, context: AppContext):
    frame = ttk.Frame(parent)
    frame.configure(style="TFrame")
    frame.columnconfigure(0, weight=3)
    frame.columnconfigure(1, weight=2)
    frame.rowconfigure(0, weight=0)
    frame.rowconfigure(1, weight=1)

    search_var = tk.StringVar()
    source_filter_var = tk.StringVar(value="All")
    status_var = tk.StringVar(value="Enter a search term to begin.")

    header = ttk.Frame(frame)
    header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(12, 4))
    header.columnconfigure(1, weight=1)
    ttk.Label(header, text="Keyword search:").grid(row=0, column=0, sticky="w")
    search_entry = ttk.Entry(header, textvariable=search_var)
    search_entry.grid(row=0, column=1, sticky="ew", padx=(4, 4))
    source_combo = ttk.Combobox(
        header, values=SOURCE_FILTERS, textvariable=source_filter_var, state="readonly", width=18
    )
    source_combo.grid(row=0, column=2, sticky="w", padx=(0, 4))
    ttk.Button(
        header,
        text="Search",
        style="Accent.TButton",
        command=lambda: perform_search(),
    ).grid(row=0, column=3, sticky="e")

    results_frame = ttk.LabelFrame(frame, text="Search results")
    results_frame.grid(row=1, column=0, sticky="nsew", padx=(12, 6), pady=(0, 12))
    results_frame.columnconfigure(0, weight=1)
    results_frame.rowconfigure(0, weight=1)
    results_frame.rowconfigure(1, weight=0)

    columns = ("source", "title", "snippet")
    results_tree = ttk.Treeview(
        results_frame,
        columns=columns,
        show="headings",
        selectmode="browse",
        height=16,
    )
    for name, heading in zip(columns, ("Source", "Title", "Snippet")):
        results_tree.heading(name, text=heading)
        results_tree.column(name, anchor="w", stretch=(name != "source"), width=140 if name != "snippet" else 220)
    results_tree.grid(row=0, column=0, sticky="nsew")
    tree_scroll = ttk.Scrollbar(results_frame, orient="vertical", command=results_tree.yview)
    results_tree.configure(yscrollcommand=tree_scroll.set)
    tree_scroll.grid(row=0, column=1, sticky="ns")

    status_label = ttk.Label(results_frame, textvariable=status_var, foreground=SECONDARY_TEXT)
    status_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=8, pady=(4, 0))

    preview_frame = ttk.LabelFrame(frame, text="Result preview")
    preview_frame.grid(row=1, column=1, sticky="nsew", padx=(6, 12), pady=(0, 12))
    preview_frame.columnconfigure(0, weight=1)
    preview_frame.rowconfigure(0, weight=1)
    preview_frame.rowconfigure(1, weight=0)

    detail_area = tk.Text(
        preview_frame,
        wrap="word",
        height=16,
        background=PANEL_BG,
        foreground=LIGHT_TEXT,
        insertbackground=ACCENT_CYAN,
        relief="flat",
    )
    detail_area.grid(row=0, column=0, sticky="nsew", padx=4, pady=(4, 0))
    detail_area.configure(state="disabled")

    meta_var = tk.StringVar(value="No item selected.")
    meta_label = ttk.Label(preview_frame, textvariable=meta_var, foreground=SECONDARY_TEXT)
    meta_label.grid(row=1, column=0, sticky="w", padx=8, pady=(4, 6))

    results: list[search_utils.SearchResult] = []
    after_id: str | None = None

    def _clear_preview():
        detail_area.configure(state="normal")
        detail_area.delete("1.0", "end")
        detail_area.configure(state="disabled")
        meta_var.set("No item selected.")

    def _populate_tree(items: list[search_utils.SearchResult]) -> None:
        for idx, item in enumerate(items):
            results_tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(item.source, item.title, item.snippet),
            )

    def perform_search():
        nonlocal after_id
        if after_id:
            frame.after_cancel(after_id)
            after_id = None
        term = search_var.get().strip()
        results_tree.delete(*results_tree.get_children())
        results.clear()
        _clear_preview()
        if not term:
            status_var.set("Enter a search term to begin.")
            return
        status_var.set("Searching...")
        raw = search_utils.search_project(context, term, limit=200)
        filtered = [
            result
            for result in raw
            if source_filter_var.get() == "All" or result.source == source_filter_var.get()
        ]
        results.extend(filtered)
        _populate_tree(results)
        count = len(results)
        status_var.set(f'{count} result{"s" if count != 1 else ""} for "{term}".')
        after_id = None

    def schedule_search(event=None):
        nonlocal after_id
        if after_id:
            frame.after_cancel(after_id)
        after_id = frame.after(200, perform_search)

    def on_select(event=None):
        selection = results_tree.selection()
        if not selection:
            return
        idx = int(selection[0])
        item = results[idx]
        detail_area.configure(state="normal")
        detail_area.delete("1.0", "end")
        detail_area.insert("1.0", item.detail)
        detail_area.configure(state="disabled")
        meta_var.set(f"{item.source} - {item.reference_id or 'n/a'}")

    results_tree.bind("<<TreeviewSelect>>", on_select)
    search_entry.bind("<Return>", lambda event: perform_search())
    search_entry.bind("<KeyRelease>", schedule_search)
    source_filter_var.trace_add("write", lambda *_: schedule_search())

    def refresh_callback():
        if search_var.get().strip():
            perform_search()

    context.register_refresh_callback(refresh_callback)
    search_entry.focus_set()
    perform_search()

    return frame
