import tkinter as tk
from tkinter import ttk
from uuid import uuid4

from ...core import AppContext
from ...core.models import RecordedMediaEntry, RecordedMediaLine
from ..styles import LIGHT_TEXT, PANEL_BG, ACCENT_CYAN


def _make_category_panel(frame, context: AppContext, title, category_filter):
    panel = ttk.Frame(frame)
    panel.columnconfigure(0, weight=1)
    panel.columnconfigure(1, weight=2)
    panel.rowconfigure(0, weight=1)

    list_frame = ttk.LabelFrame(panel, text=f"{title} entries")
    list_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
    list_frame.columnconfigure(0, weight=1)
    list_frame.rowconfigure(0, weight=1)
    entry_list = tk.Listbox(list_frame, height=14, background="#0a1022", foreground=LIGHT_TEXT)
    entry_list.grid(row=0, column=0, sticky="nsew")
    scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=entry_list.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    entry_list.configure(yscrollcommand=scrollbar.set)

    detail_frame = ttk.LabelFrame(panel, text=f"{title} details")
    detail_frame.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
    detail_frame.columnconfigure(0, weight=1)
    detail_frame.rowconfigure(3, weight=1)

    title_var = tk.StringVar()
    author_var = tk.StringVar()
    category_var = tk.StringVar()
    extra_var = tk.StringVar()
    spawn_var = tk.DoubleVar(value=0)

    ttk.Label(detail_frame, text="Title").grid(row=0, column=0, sticky="w", padx=8, pady=(6, 2))
    ttk.Entry(detail_frame, textvariable=title_var).grid(row=0, column=1, sticky="ew", padx=8, pady=(6, 2))
    ttk.Label(detail_frame, text="Author").grid(row=1, column=0, sticky="w", padx=8, pady=2)
    ttk.Entry(detail_frame, textvariable=author_var).grid(row=1, column=1, sticky="ew", padx=8, pady=2)
    ttk.Label(detail_frame, text="Category").grid(row=2, column=0, sticky="w", padx=8, pady=2)
    category_combo = ttk.Combobox(detail_frame, textvariable=category_var, state="readonly")
    category_combo["values"] = ("CDs", "Home-VHS", "Retail-VHS")
    category_combo.grid(row=2, column=1, sticky="ew", padx=8, pady=2)
    ttk.Label(detail_frame, text="Extra").grid(row=3, column=0, sticky="w", padx=8, pady=2)
    ttk.Entry(detail_frame, textvariable=extra_var).grid(row=3, column=1, sticky="ew", padx=8, pady=2)
    ttk.Label(detail_frame, text="Spawn").grid(row=4, column=0, sticky="w", padx=8, pady=2)
    ttk.Entry(detail_frame, textvariable=spawn_var).grid(row=4, column=1, sticky="ew", padx=8, pady=2)

    info = ttk.Label(detail_frame, text="Select an entry to inspect or edit it.")
    info.grid(row=5, column=0, columnspan=2, sticky="w", padx=8, pady=4)

    lines_list = tk.Listbox(detail_frame, height=8, background="#050816", foreground=LIGHT_TEXT)
    lines_list.grid(row=6, column=0, columnspan=2, sticky="nsew", padx=8, pady=4)
    detail_frame.rowconfigure(6, weight=1)

    line_text_var = tk.StringVar()
    line_codes_var = tk.StringVar()
    line_r_var = tk.DoubleVar(value=1.0)
    line_g_var = tk.DoubleVar(value=1.0)
    line_b_var = tk.DoubleVar(value=1.0)

    line_editor = ttk.Frame(detail_frame)
    line_editor.grid(row=7, column=0, columnspan=2, sticky="ew", padx=8, pady=4)
    line_editor.columnconfigure(1, weight=1)
    ttk.Label(line_editor, text="Line text").grid(row=0, column=0, sticky="w")
    ttk.Entry(line_editor, textvariable=line_text_var).grid(row=0, column=1, sticky="ew", padx=4)
    ttk.Label(line_editor, text="Codes").grid(row=1, column=0, sticky="w")
    ttk.Entry(line_editor, textvariable=line_codes_var).grid(row=1, column=1, sticky="ew", padx=4)

    color_frame = ttk.Frame(line_editor)
    color_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))
    ttk.Label(color_frame, text="Color r").grid(row=0, column=0, sticky="w")
    ttk.Entry(color_frame, textvariable=line_r_var, width=6).grid(row=0, column=1, padx=2)
    ttk.Label(color_frame, text="g").grid(row=0, column=2, sticky="w")
    ttk.Entry(color_frame, textvariable=line_g_var, width=6).grid(row=0, column=3, padx=2)
    ttk.Label(color_frame, text="b").grid(row=0, column=4, sticky="w")
    ttk.Entry(color_frame, textvariable=line_b_var, width=6).grid(row=0, column=5, padx=2)

    transcript_text = tk.Text(
        detail_frame,
        height=6,
        wrap="word",
        background=PANEL_BG,
        foreground=LIGHT_TEXT,
        insertbackground="#ffffff",
    )
    transcript_text.grid(row=8, column=0, columnspan=2, sticky="nsew", padx=8, pady=4)
    detail_frame.rowconfigure(8, weight=0)

    button_frame = ttk.Frame(detail_frame)
    button_frame.grid(row=9, column=0, columnspan=2, sticky="ew", padx=8, pady=4)
    ttk.Button(button_frame, text="Apply metadata", command=lambda: apply_metadata()).pack(
        side="left", padx=4
    )
    ttk.Button(button_frame, text="Update transcript", command=lambda: apply_transcript()).pack(
        side="left", padx=4
    )
    ttk.Button(button_frame, text="Duplicate entry", command=lambda: duplicate_entry()).pack(
        side="left", padx=4
    )
    ttk.Button(button_frame, text="Delete entry", command=lambda: delete_entry()).pack(
        side="right", padx=4
    )

    current_entry_id = None
    current_line_index = None

    def get_entries():
        return [
            entry for entry in context.project.recorded_media.values()
            if entry.category == category_filter
        ]

    def refresh():
        entry_list.delete(0, tk.END)
        entries = get_entries()
        for entry in entries:
            entry_list.insert(tk.END, f"{entry.title} ({entry.author})")
        info.configure(text=f"{len(entries)} entries loaded.")

    def update_detail(_lines_list, _info, listbox=None):
        nonlocal current_entry_id
        _lines_list.delete(0, tk.END)
        entries = get_entries()
        if not entries:
            _info.configure(text="Load recorded media to populate this category.")
            current_entry_id = None
            return
        sel = listbox.curselection() if listbox else ()
        if not sel:
            _info.configure(text=f"{len(entries)} entries available.")
            current_entry_id = None
            return
        entry = entries[sel[0]]
        current_entry_id = entry.id
        title_var.set(entry.title)
        author_var.set(entry.author)
        category_var.set(entry.category)
        extra_var.set(entry.extra or "")
        spawn_var.set(entry.spawn)
        transcript_text.delete("1.0", "end")
        transcript_text.insert("1.0", "\n".join(line.text for line in entry.lines))
        _info.configure(text=f"{entry.title} · {len(entry.lines)} lines")
        for idx, line in enumerate(entry.lines):
            code = f" [{line.codes}]" if line.codes else ""
            _lines_list.insert(tk.END, f"{idx+1:02d}. {line.text}{code}")

    def apply_metadata():
        if not current_entry_id:
            return
        entry = context.project.recorded_media.get(current_entry_id)
        if not entry:
            return
        entry.title = title_var.get()
        entry.author = author_var.get()
        entry.category = category_var.get()
        entry.extra = extra_var.get()
        entry.spawn = int(float(spawn_var.get()))
        refresh()
        context.notify_data_changed()

    def apply_transcript():
        if not current_entry_id:
            return
        entry = context.project.recorded_media.get(current_entry_id)
        if not entry:
            return
        lines = [line.strip() for line in transcript_text.get("1.0", "end").splitlines() if line.strip()]
        entry.lines = [
            RecordedMediaLine(text=line, r=1.0, g=1.0, b=1.0)
            for line in lines
        ]
        update_detail(lines_list, info, entry_list)
        context.notify_data_changed()

    def apply_line():
        nonlocal current_line_index
        if current_entry_id is None or current_line_index is None:
            return
        entry = context.project.recorded_media.get(current_entry_id)
        if not entry or current_line_index >= len(entry.lines):
            return
        line = entry.lines[current_line_index]
        line.text = line_text_var.get()
        line.codes = line_codes_var.get() or None
        try:
            line.r = float(line_r_var.get())
            line.g = float(line_g_var.get())
            line.b = float(line_b_var.get())
        except ValueError:
            pass
        update_detail(lines_list, info, entry_list)
        context.notify_data_changed()

    def delete_entry():
        entries = get_entries()
        if not entries or current_entry_id is None:
            return
        context.project.recorded_media.pop(current_entry_id, None)
        current_entry_id = None
        refresh()
        context.notify_data_changed()

    def duplicate_entry():
        if current_entry_id is None:
            return
        entry = context.project.recorded_media.get(current_entry_id)
        if not entry:
            return
        new_id = uuid4().hex
        dup = RecordedMediaEntry(
            id=new_id,
            title=f"{entry.title} (copy)",
            author=entry.author,
            category=entry.category,
            spawn=entry.spawn,
            extra=entry.extra,
            lines=[
                RecordedMediaLine(text=line.text, r=line.r, g=line.g, b=line.b, codes=line.codes)
                for line in entry.lines
            ],
        )
        context.project.recorded_media[new_id] = dup
        refresh()
        context.notify_data_changed()

    def on_line_select(_=None):
        nonlocal current_line_index
        sel = lines_list.curselection()
        if not sel or current_entry_id is None:
            current_line_index = None
            return
        entry = context.project.recorded_media.get(current_entry_id)
        if not entry:
            current_line_index = None
            return
        idx = sel[0]
        if idx >= len(entry.lines):
            current_line_index = None
            return
        line = entry.lines[idx]
        current_line_index = idx
        line_text_var.set(line.text)
        line_codes_var.set(line.codes or "")
        line_r_var.set(line.r)
        line_g_var.set(line.g)
        line_b_var.set(line.b)

    entry_list.bind("<<ListboxSelect>>", lambda event: update_detail(lines_list, info, entry_list))
    lines_list.bind("<<ListboxSelect>>", on_line_select)

    ttk.Button(button_frame, text="Update line", command=apply_line).pack(side="left", padx=4)

    return panel, refresh


def make_tab(parent, context: AppContext):
    frame = ttk.Frame(parent)
    frame.configure(style="TFrame")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)
    frame.rowconfigure(1, weight=0)

    notebook = ttk.Notebook(frame, style="Neon.TNotebook")
    notebook.grid(row=0, column=0, sticky="nsew", padx=12, pady=8)

    home_panel, home_refresh = _make_category_panel(frame, context, "Home VHS", "Home-VHS")
    retail_panel, retail_refresh = _make_category_panel(
        frame, context, "Retail VHS", "Retail-VHS"
    )
    cd_panel, cd_refresh = _make_category_panel(frame, context, "CDs", "CDs")

    notebook.add(home_panel, text="Home VHS")
    notebook.add(retail_panel, text="Retail VHS")
    notebook.add(cd_panel, text="CDs")

    create_frame = ttk.LabelFrame(frame, text="Create new recorded media")
    create_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
    create_frame.columnconfigure(1, weight=1)

    new_title = tk.StringVar()
    new_author = tk.StringVar()
    new_category = tk.StringVar(value="CDs")
    new_spawn = tk.DoubleVar(value=0)

    ttk.Label(create_frame, text="Title").grid(row=0, column=0, sticky="w", padx=8, pady=4)
    ttk.Entry(create_frame, textvariable=new_title).grid(row=0, column=1, sticky="ew", padx=8, pady=4)
    ttk.Label(create_frame, text="Author").grid(row=1, column=0, sticky="w", padx=8, pady=4)
    ttk.Entry(create_frame, textvariable=new_author).grid(
        row=1, column=1, sticky="ew", padx=8, pady=4
    )
    ttk.Label(create_frame, text="Category").grid(row=2, column=0, sticky="w", padx=8, pady=4)
    category_combo = ttk.Combobox(
        create_frame, textvariable=new_category, state="readonly", values=("CDs", "Home-VHS", "Retail-VHS")
    )
    category_combo.grid(row=2, column=1, sticky="w", padx=8, pady=4)
    ttk.Label(create_frame, text="Spawn weight").grid(row=3, column=0, sticky="w", padx=8, pady=4)
    ttk.Entry(create_frame, textvariable=new_spawn).grid(row=3, column=1, sticky="ew", padx=8, pady=4)

    transcript_label = ttk.Label(create_frame, text="Transcript lines (one per row)")
    transcript_label.grid(row=4, column=0, columnspan=2, sticky="w", padx=8, pady=(4, 0))
    transcript_text = tk.Text(
        create_frame,
        height=6,
        wrap="word",
        background=PANEL_BG,
        foreground=LIGHT_TEXT,
        insertbackground="#ffffff",
    )
    transcript_text.grid(row=5, column=0, columnspan=2, sticky="ew", padx=8, pady=4)

    def create_entry():
        lines = [
            line.strip()
            for line in transcript_text.get("1.0", "end").splitlines()
            if line.strip()
        ]
        if not new_title.get() or not lines:
            return
        entry = RecordedMediaEntry(
            id=uuid4().hex,
            title=new_title.get(),
            author=new_author.get(),
            category=new_category.get(),
            spawn=int(float(new_spawn.get())),
            extra="",
            lines=[RecordedMediaLine(text=line, r=1.0, g=1.0, b=1.0) for line in lines],
        )
        context.project.recorded_media[entry.id] = entry
        context.notify_data_changed()

    ttk.Button(
        create_frame,
        text="Create recorded media",
        command=create_entry,
        style="Accent.TButton",
    ).grid(row=6, column=0, columnspan=2, pady=8)

    def refresh_all():
        home_refresh()
        retail_refresh()
        cd_refresh()

    context.register_refresh_callback(refresh_all)
    refresh_all()

    return frame
