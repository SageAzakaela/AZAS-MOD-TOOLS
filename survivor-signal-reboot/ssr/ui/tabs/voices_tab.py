import tkinter as tk
from tkinter import colorchooser, messagebox, simpledialog, ttk

from ...core import AppContext
from ...core.models import Broadcast, Character, Group, Line, Voice
from ..styles import ACCENT_CYAN, LIGHT_TEXT, PANEL_BG, SECONDARY_TEXT, SLATE_BG


VOICE_PALETTE = [
    "#ff66c4",
    "#ff4c4c",
    "#ff813e",
    "#ffd24c",
    "#fff167",
    "#f4ff8a",
    "#c8ff7a",
    "#66ffec",
    "#1ac7ff",
    "#4f99ff",
    "#7c79ff",
    "#a75dff",
    "#d085ff",
    "#ff9ae3",
    "#ffb3a3",
    "#f0d67d",
    "#c2ffd4",
    "#00b140",
    "#5ef4ff",
    "#7a5cff",
    "#d1d1ff",
    "#ffffff",
    "#8a8a8a",
    "#1b1b3c",
]


def _contrast_color(value: str) -> str:
    clean = value.lstrip("#")
    if len(clean) != 6:
        return "#000000"
    r = int(clean[0:2], 16)
    g = int(clean[2:4], 16)
    b = int(clean[4:6], 16)
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    return "#000000" if brightness > 180 else "#ffffff"


def _generate_id(prefix: str, existing: set[str]) -> str:
    idx = 1
    while True:
        candidate = f"{prefix}_{idx}"
        if candidate not in existing:
            return candidate
        idx += 1


def make_tab(parent, context: AppContext):
    project = context.project
    frame = ttk.Frame(parent)
    frame.configure(style="TFrame")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=3)
    frame.rowconfigure(1, weight=2)

    columns_frame = ttk.Frame(frame)
    columns_frame.grid(row=0, column=0, sticky="nsew")
    columns_frame.columnconfigure(0, weight=1)
    columns_frame.columnconfigure(1, weight=2)
    columns_frame.columnconfigure(2, weight=1)
    columns_frame.rowconfigure(0, weight=1)

    group_frame = ttk.LabelFrame(columns_frame, text="Groups")
    group_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
    group_frame.columnconfigure(0, weight=1)
    for row_idx in range(8):
        group_frame.rowconfigure(row_idx, weight=1 if row_idx == 3 else 0)
    group_ids: list[str] = []
    current_group_id: str | None = None
    group_search_var = tk.StringVar()

    group_main_button_frame = ttk.Frame(group_frame)
    group_main_button_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 2))
    for idx in range(3):
        group_main_button_frame.columnconfigure(idx, weight=1)
    ttk.Button(group_main_button_frame, text="Add group", command=lambda: _add_group()).grid(
        row=0, column=0, sticky="ew", padx=2
    )
    ttk.Button(group_main_button_frame, text="Edit group", command=lambda: _save_group()).grid(
        row=0, column=1, sticky="ew", padx=2
    )
    ttk.Button(group_main_button_frame, text="Delete group", command=lambda: _delete_group()).grid(
        row=0, column=2, sticky="ew", padx=2
    )

    group_assign_button_frame = ttk.Frame(group_frame)
    group_assign_button_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 4))
    for idx in range(2):
        group_assign_button_frame.columnconfigure(idx, weight=1)
    ttk.Button(
        group_assign_button_frame, text="Add character", command=lambda: _add_character_to_group()
    ).grid(row=0, column=0, sticky="ew", padx=2)
    ttk.Button(
        group_assign_button_frame, text="Remove character", command=lambda: _remove_character_from_group()
    ).grid(row=0, column=1, sticky="ew", padx=2)

    group_search_frame = ttk.Frame(group_frame)
    group_search_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 4))
    group_search_frame.columnconfigure(1, weight=1)
    ttk.Label(group_search_frame, text="Search").grid(row=0, column=0, sticky="w")
    ttk.Entry(group_search_frame, textvariable=group_search_var).grid(
        row=0, column=1, sticky="ew", padx=(4, 0)
    )

    group_list_frame = ttk.Frame(group_frame)
    group_list_frame.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 4))
    group_list_frame.columnconfigure(0, weight=1)
    group_list_frame.rowconfigure(0, weight=1)
    group_list = tk.Listbox(
        group_list_frame,
        background=SLATE_BG,
        foreground=LIGHT_TEXT,
        selectbackground=ACCENT_CYAN,
        selectforeground="#04060a",
        exportselection=False,
        activestyle="none",
        highlightthickness=0,
    )
    group_list.grid(row=0, column=0, sticky="nsew")
    group_scroll = ttk.Scrollbar(group_list_frame, orient="vertical", command=group_list.yview)
    group_scroll.grid(row=0, column=1, sticky="ns")
    group_list.configure(yscrollcommand=group_scroll.set)

    group_details = ttk.Frame(group_frame)
    group_details.grid(row=4, column=0, sticky="ew", padx=8, pady=(0, 4))
    group_details.columnconfigure(1, weight=1)
    group_name_var = tk.StringVar()
    ttk.Label(group_details, text="Name").grid(row=0, column=0, sticky="w")
    ttk.Entry(group_details, textvariable=group_name_var).grid(row=0, column=1, sticky="ew", padx=(4, 0))

    description_label = ttk.Label(group_frame, text="Description")
    description_label.grid(row=5, column=0, sticky="w", padx=8)
    group_desc_text = tk.Text(
        group_frame,
        height=3,
        wrap="word",
        background=PANEL_BG,
        foreground=LIGHT_TEXT,
        insertbackground=ACCENT_CYAN,
        relief="flat",
        borderwidth=0,
    )
    group_desc_text.grid(row=6, column=0, sticky="ew", padx=8, pady=(0, 4))

    group_char_frame = ttk.Frame(group_frame)
    group_char_frame.grid(row=7, column=0, sticky="ew", padx=8, pady=(2, 6))
    group_char_frame.columnconfigure(0, weight=1)
    ttk.Label(group_char_frame, text="Characters in group").grid(row=0, column=0, sticky="w")
    group_char_list = tk.Listbox(
        group_char_frame,
        height=4,
        background=SLATE_BG,
        foreground=LIGHT_TEXT,
        selectmode="none",
        relief="flat",
        borderwidth=0,
    )
    group_char_list.grid(row=1, column=0, sticky="nsew", pady=(2, 0))

    character_frame = ttk.LabelFrame(columns_frame, text="Characters")
    character_frame.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
    character_frame.columnconfigure(0, weight=1)
    for row_idx in range(11):
        character_frame.rowconfigure(row_idx, weight=1 if row_idx == 2 else 0)
    character_ids: list[str] = []
    current_character_id: str | None = None
    character_search_var = tk.StringVar()

    char_button_frame = ttk.Frame(character_frame)
    char_button_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 2))
    for idx in range(5):
        char_button_frame.columnconfigure(idx, weight=1)
    ttk.Button(char_button_frame, text="Add character", command=lambda: _create_character()).grid(
        row=0, column=0, sticky="ew", padx=2
    )
    ttk.Button(char_button_frame, text="Delete character", command=lambda: _delete_character()).grid(
        row=0, column=1, sticky="ew", padx=2
    )
    ttk.Button(char_button_frame, text="Assign voice", command=lambda: _save_character()).grid(
        row=0, column=2, sticky="ew", padx=2
    )
    ttk.Button(char_button_frame, text="Assign group", command=lambda: _add_character_to_group()).grid(
        row=0, column=3, sticky="ew", padx=2
    )
    ttk.Button(char_button_frame, text="Details", command=lambda: _open_character_details_popup()).grid(
        row=0, column=4, sticky="ew", padx=2
    )

    character_search_frame = ttk.Frame(character_frame)
    character_search_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 4))
    character_search_frame.columnconfigure(1, weight=1)
    ttk.Label(character_search_frame, text="Search").grid(row=0, column=0, sticky="w")
    ttk.Entry(character_search_frame, textvariable=character_search_var).grid(
        row=0, column=1, sticky="ew", padx=(4, 0)
    )

    character_list_frame = ttk.Frame(character_frame)
    character_list_frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 4))
    character_list_frame.columnconfigure(0, weight=1)
    character_list_frame.rowconfigure(0, weight=1)
    character_list = tk.Listbox(
        character_list_frame,
        background=SLATE_BG,
        foreground=LIGHT_TEXT,
        selectbackground=ACCENT_CYAN,
        selectforeground="#04060a",
        exportselection=False,
        activestyle="none",
        highlightthickness=0,
    )
    character_list.grid(row=0, column=0, sticky="nsew")
    character_scroll = ttk.Scrollbar(character_list_frame, orient="vertical", command=character_list.yview)
    character_scroll.grid(row=0, column=1, sticky="ns")
    character_list.configure(yscrollcommand=character_scroll.set)

    char_name_var = tk.StringVar()
    ttk.Label(character_frame, text="Name").grid(row=3, column=0, sticky="w", padx=8)
    ttk.Entry(character_frame, textvariable=char_name_var).grid(
        row=4, column=0, sticky="ew", padx=8, pady=(0, 4)
    )

    ttk.Label(character_frame, text="Notes").grid(row=5, column=0, sticky="w", padx=8)
    character_notes = tk.Text(
        character_frame,
        height=3,
        wrap="word",
        background=PANEL_BG,
        foreground=LIGHT_TEXT,
        insertbackground=ACCENT_CYAN,
        relief="flat",
        borderwidth=0,
    )
    character_notes.grid(row=6, column=0, sticky="ew", padx=8, pady=(0, 4))

    voice_selector_label = ttk.Label(character_frame, text="Assign voices (up to 4)")
    voice_selector_label.grid(row=7, column=0, sticky="w", padx=8)
    voice_selector = tk.Listbox(
        character_frame,
        height=5,
        selectmode="extended",
        background=SLATE_BG,
        foreground=LIGHT_TEXT,
        exportselection=False,
        activestyle="none",
        highlightthickness=0,
    )
    voice_selector.grid(row=8, column=0, sticky="ew", padx=8, pady=(0, 4))

    character_group_label = ttk.Label(character_frame, text="Groups: none", foreground=SECONDARY_TEXT)
    character_group_label.grid(row=9, column=0, sticky="w", padx=8, pady=(0, 4))

    char_save_frame = ttk.Frame(character_frame)
    char_save_frame.grid(row=10, column=0, sticky="ew", padx=8, pady=(4, 8))
    char_save_frame.columnconfigure(0, weight=1)
    ttk.Button(char_save_frame, text="Save character", command=lambda: _save_character()).grid(
        row=0, column=0, sticky="ew"
    )

    voice_frame = ttk.LabelFrame(columns_frame, text="Voice Search Panel")
    voice_frame.grid(row=0, column=2, sticky="nsew", padx=12, pady=12)
    voice_frame.columnconfigure(0, weight=1)
    for row_idx in range(9):
        voice_frame.rowconfigure(row_idx, weight=1 if row_idx == 2 else 0)
    voice_search_var = tk.StringVar()

    voice_control_frame = ttk.Frame(voice_frame)
    voice_control_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 2))
    for idx in range(3):
        voice_control_frame.columnconfigure(idx, weight=1)
    ttk.Button(voice_control_frame, text="Add voice", command=lambda: _create_voice()).grid(
        row=0, column=0, sticky="ew", padx=2
    )
    ttk.Button(voice_control_frame, text="Save voice", command=lambda: _save_voice()).grid(
        row=0, column=1, sticky="ew", padx=2
    )
    ttk.Button(
        voice_control_frame, text="Reset search", command=lambda: _reset_voice_search()
    ).grid(row=0, column=2, sticky="ew", padx=2)

    voice_search_frame = ttk.Frame(voice_frame)
    voice_search_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 4))
    voice_search_frame.columnconfigure(1, weight=1)
    ttk.Label(voice_search_frame, text="Voice search").grid(row=0, column=0, sticky="w")
    ttk.Entry(voice_search_frame, textvariable=voice_search_var).grid(
        row=0, column=1, sticky="ew", padx=(4, 0)
    )

    voice_list_frame = ttk.Frame(voice_frame)
    voice_list_frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 4))
    voice_list_frame.columnconfigure(0, weight=1)
    voice_list_frame.rowconfigure(0, weight=1)
    voice_tree = ttk.Treeview(
        voice_list_frame,
        columns=("color", "name"),
        show="headings",
        selectmode="browse",
        height=12,
    )
    voice_tree.heading("color", text="Color")
    voice_tree.heading("name", text="Voice")
    voice_tree.column("color", width=80, anchor="center")
    voice_tree.column("name", anchor="w")
    voice_tree.grid(row=0, column=0, sticky="nsew")
    voice_tree_scroll = ttk.Scrollbar(voice_list_frame, orient="vertical", command=voice_tree.yview)
    voice_tree_scroll.grid(row=0, column=1, sticky="ns")
    voice_tree.configure(yscrollcommand=voice_tree_scroll.set)

    voice_palette_zone = ttk.Frame(voice_frame)
    voice_palette_zone.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 4))
    voice_palette_zone.columnconfigure(0, weight=1)
    palette_label = ttk.Label(voice_palette_zone, text="Voice palette", foreground=SECONDARY_TEXT)
    palette_label.grid(row=0, column=0, sticky="w")
    palette_frame = ttk.Frame(voice_palette_zone)
    palette_frame.grid(row=2, column=0, sticky="ew")
    palette_frame.columnconfigure(0, weight=1)
    palette_colors = VOICE_PALETTE.copy()

    color_var = tk.StringVar(value="#ffffff")
    color_button = tk.Button(
        voice_palette_zone,
        text="Current color",
        width=12,
        background=color_var.get(),
        foreground="#04060a",
        relief="ridge",
        borderwidth=0,
        highlightthickness=0,
    )
    color_button.grid(row=1, column=0, sticky="w", pady=(4, 6))
    color_var.trace_add("write", lambda *_: color_button.configure(background=color_var.get()))

    voice_name_var = tk.StringVar()
    ttk.Label(voice_frame, text="Name").grid(row=4, column=0, sticky="w", padx=8)
    ttk.Entry(voice_frame, textvariable=voice_name_var).grid(
        row=5, column=0, sticky="ew", padx=8, pady=(0, 4)
    )

    ttk.Label(voice_frame, text="Notes").grid(row=6, column=0, sticky="w", padx=8)
    voice_notes = tk.Text(
        voice_frame,
        height=3,
        wrap="word",
        background=PANEL_BG,
        foreground=LIGHT_TEXT,
        insertbackground=ACCENT_CYAN,
        relief="flat",
        borderwidth=0,
    )
    voice_notes.grid(row=7, column=0, sticky="ew", padx=8, pady=(0, 4))

    voice_usage_label = ttk.Label(voice_frame, text="Used by characters: none", foreground=SECONDARY_TEXT)
    voice_usage_label.grid(row=8, column=0, sticky="w", padx=8, pady=(0, 4))

    broadcast_frame = ttk.LabelFrame(frame, text="Broadcasts")
    broadcast_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
    broadcast_frame.columnconfigure(0, weight=1)
    broadcast_frame.rowconfigure(1, weight=1)
    broadcast_frame.rowconfigure(2, weight=0)
    broadcast_frame.rowconfigure(3, weight=2)
    broadcast_filter_label = ttk.Label(broadcast_frame, text="Filter: All broadcasts", foreground=SECONDARY_TEXT)
    broadcast_filter_label.grid(row=0, column=0, sticky="w", padx=8, pady=(4, 0))

    broadcast_tree_frame = ttk.Frame(broadcast_frame)
    broadcast_tree_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(2, 4))
    broadcast_tree_frame.columnconfigure(0, weight=1)
    broadcast_tree_frame.rowconfigure(0, weight=1)
    broadcast_tree = ttk.Treeview(
        broadcast_tree_frame,
        columns=("channel", "broadcast", "first_line", "day", "lines"),
        show="headings",
        selectmode="browse",
        height=10,
    )
    broadcast_tree.heading("channel", text="Channel")
    broadcast_tree.heading("broadcast", text="Broadcast")
    broadcast_tree.heading("first_line", text="First line")
    broadcast_tree.heading("day", text="Day")
    broadcast_tree.heading("lines", text="Lines")
    broadcast_tree.column("channel", width=80, anchor="w")
    broadcast_tree.column("broadcast", width=200, anchor="w")
    broadcast_tree.column("first_line", width=240, anchor="w")
    broadcast_tree.column("day", width=40, anchor="center")
    broadcast_tree.column("lines", width=60, anchor="center")
    broadcast_tree.grid(row=0, column=0, sticky="nsew")
    broadcast_tree_scroll = ttk.Scrollbar(broadcast_tree_frame, orient="vertical", command=broadcast_tree.yview)
    broadcast_tree_scroll.grid(row=0, column=1, sticky="ns")
    broadcast_tree.configure(yscrollcommand=broadcast_tree_scroll.set)

    ttk.Label(broadcast_frame, text="Broadcast content").grid(row=2, column=0, sticky="w", padx=8)
    content_frame = ttk.Frame(broadcast_frame)
    content_frame.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 8))
    content_frame.columnconfigure(0, weight=1)
    content_frame.rowconfigure(0, weight=1)
    content_notebook = ttk.Notebook(content_frame)
    content_notebook.grid(row=0, column=0, sticky="nsew")

    lines_tab = ttk.Frame(content_notebook)
    lines_tab.columnconfigure(0, weight=1)
    lines_tab.rowconfigure(0, weight=1)
    lines_list = tk.Listbox(
        lines_tab,
        background=SLATE_BG,
        foreground=LIGHT_TEXT,
        selectbackground=ACCENT_CYAN,
        selectforeground="#04060a",
        activestyle="none",
        highlightthickness=0,
    )
    lines_list.grid(row=0, column=0, sticky="nsew")
    lines_scroll = ttk.Scrollbar(lines_tab, orient="vertical", command=lines_list.yview)
    lines_scroll.grid(row=0, column=1, sticky="ns")
    lines_list.configure(yscrollcommand=lines_scroll.set)
    content_notebook.add(lines_tab, text="Lines")

    transcript_tab = ttk.Frame(content_notebook)
    transcript_tab.columnconfigure(0, weight=1)
    transcript_tab.rowconfigure(0, weight=1)
    transcript_tab.rowconfigure(1, weight=0)
    transcript_text = tk.Text(
        transcript_tab,
        background=SLATE_BG,
        foreground=LIGHT_TEXT,
        insertbackground=ACCENT_CYAN,
        wrap="word",
        borderwidth=0,
        relief="flat",
    )
    transcript_text.grid(row=0, column=0, sticky="nsew")
    transcript_scroll = ttk.Scrollbar(transcript_tab, orient="vertical", command=transcript_text.yview)
    transcript_scroll.grid(row=0, column=1, sticky="ns")
    transcript_text.configure(yscrollcommand=transcript_scroll.set)
    transcript_actions = ttk.Frame(transcript_tab)
    transcript_actions.grid(row=1, column=0, sticky="ew", pady=(6, 0))
    transcript_actions.columnconfigure(0, weight=1)
    ttk.Button(transcript_actions, text="Save transcript", command=lambda: _save_transcript_lines()).grid(
        row=0, column=0, sticky="w"
    )
    content_notebook.add(transcript_tab, text="Transcript")
    voice_ids: list[str] = []
    current_voice_id: str | None = None
    broadcast_ids: list[str] = []
    current_broadcast_id: str | None = None
    broadcast_filter_scope: str = "all"
    broadcast_filter_id: str | None = None

    def _render_palette():
        for child in palette_frame.winfo_children():
            child.destroy()
        for idx, color in enumerate(palette_colors):
            btn = tk.Button(
                palette_frame,
                background=color,
                width=2,
                relief="flat",
                borderwidth=0,
                highlightthickness=0,
                command=lambda c=color: _assign_color(c),
            )
            btn.grid(row=0, column=idx, padx=2, pady=2, sticky="ew")
        palette_frame.update_idletasks()

    def _assign_color(color: str):
        if not color:
            return
        color_var.set(color)
        color_button.configure(background=color)
        if not current_voice_id:
            return
        voice = project.voices.get(current_voice_id)
        if not voice:
            return
        voice.color = color
        refresh_voices()

    def _choose_custom_color():
        result = colorchooser.askcolor(initialcolor=color_var.get(), title="Pick a voice color")
        color_hex = result[1] if result else None
        if not color_hex:
            return
        if color_hex not in palette_colors:
            palette_colors.append(color_hex)
        _assign_color(color_hex)
        _render_palette()

    def _reset_voice_search():
        voice_search_var.set("")

    def _refresh_groups():
        nonlocal group_ids, current_group_id
        group_list.delete(0, "end")
        search_term = (group_search_var.get() or "").strip().lower()
        sorted_groups = sorted(
            project.groups.values(), key=lambda group: (group.name or group.id).lower()
        )
        if search_term:
            sorted_groups = [
                group
                for group in sorted_groups
                if search_term in (group.name or group.id).lower()
            ]
        group_ids = [group.id for group in sorted_groups]
        for group in sorted_groups:
            group_list.insert("end", group.name or group.id)
        if current_group_id not in group_ids:
            current_group_id = None
            _clear_group_details()
        else:
            _set_group_selection(current_group_id)

    def _set_group_selection(group_id: str):
        nonlocal current_group_id
        if not group_id:
            return
        current_group_id = group_id
        idx = group_ids.index(group_id)
        group_list.selection_clear(0, "end")
        group_list.selection_set(idx)
        _populate_group_details()

    def _populate_group_details():
        group = project.groups.get(current_group_id)
        if not group:
            _clear_group_details()
            return
        group_name_var.set(group.name)
        group_desc_text.configure(state="normal")
        group_desc_text.delete("1.0", "end")
        group_desc_text.insert("1.0", group.description)
        group_desc_text.configure(state="normal")
        group_char_list.delete(0, "end")
        for cid in group.character_ids:
            character = project.characters.get(cid)
            if character:
                group_char_list.insert("end", character.name or character.id)

    def _clear_group_details():
        group_name_var.set("")
        group_desc_text.configure(state="normal")
        group_desc_text.delete("1.0", "end")
        group_desc_text.configure(state="normal")
        group_char_list.delete(0, "end")

    def _set_broadcast_filter(scope: str = "all", identifier: str | None = None):
        nonlocal broadcast_filter_scope, broadcast_filter_id, current_broadcast_id
        broadcast_filter_scope = scope
        broadcast_filter_id = identifier
        current_broadcast_id = None
        _refresh_broadcast_list()

    def _on_group_selected(event=None):
        nonlocal current_group_id
        selection = group_list.curselection()
        if not selection:
            current_group_id = None
            _clear_group_details()
            _set_broadcast_filter()
            return
        current_group_id = group_ids[selection[0]]
        _populate_group_details()
        _set_broadcast_filter("group", current_group_id)

    def _add_group():
        name = simpledialog.askstring("New group", "Group name:")
        if not name:
            return
        group_id = _generate_id("group", set(project.groups.keys()))
        project.groups[group_id] = Group(id=group_id, name=name)
        refresh_all()
        _set_group_selection(group_id)

    def _save_group():
        if not current_group_id:
            return
        group = project.groups.get(current_group_id)
        if not group:
            return
        group.name = group_name_var.get().strip() or group.name
        group.description = group_desc_text.get("1.0", "end").strip()
        refresh_all()
        _set_group_selection(group.id)

    def _delete_group():
        nonlocal current_group_id
        if not current_group_id:
            return
        project.groups.pop(current_group_id, None)
        current_group_id = None
        refresh_all()
        _set_broadcast_filter()

    def _add_character_to_group():
        if not current_group_id or not current_character_id:
            return
        group = project.groups.get(current_group_id)
        if not group:
            return
        if current_character_id not in group.character_ids:
            group.character_ids.append(current_character_id)
        refresh_all()
        _populate_group_details()

    def _remove_character_from_group():
        if not current_group_id or not current_character_id:
            return
        group = project.groups.get(current_group_id)
        if not group:
            return
        if current_character_id in group.character_ids:
            group.character_ids.remove(current_character_id)
        refresh_all()
        _populate_group_details()

    def _refresh_characters():
        nonlocal character_ids
        character_list.delete(0, "end")
        search_term = (character_search_var.get() or "").strip().lower()
        sorted_characters = sorted(
            project.characters.values(), key=lambda char: (char.name or char.id).lower()
        )
        if search_term:
            sorted_characters = [
                char
                for char in sorted_characters
                if search_term in (char.name or char.id).lower()
            ]
        character_ids = [char.id for char in sorted_characters]
        for character in sorted_characters:
            character_list.insert("end", character.name or character.id)
        _sync_character_selection()

    def _sync_character_selection():
        nonlocal current_character_id
        if current_character_id and current_character_id in character_ids:
            idx = character_ids.index(current_character_id)
            character_list.selection_clear(0, "end")
            character_list.selection_set(idx)
            _populate_character_details()
        else:
            current_character_id = None
            _clear_character_details()

    def _populate_character_details():
        character = project.characters.get(current_character_id)
        if not character:
            _clear_character_details()
            return
        char_name_var.set(character.name)
        character_notes.configure(state="normal")
        character_notes.delete("1.0", "end")
        character_notes.insert("1.0", character.notes)
        character_notes.configure(state="normal")
        _sync_character_voice_selection(character)
        groups_using = [grp.name for grp in project.groups.values() if current_character_id in grp.character_ids]
        character_group_label.configure(text=f"Groups: {', '.join(groups_using) or 'none'}")

    def _clear_character_details():
        char_name_var.set("")
        character_notes.configure(state="normal")
        character_notes.delete("1.0", "end")
        character_notes.configure(state="normal")
        voice_selector.selection_clear(0, "end")
        character_group_label.configure(text="Groups: none")

    def _on_character_selected(event=None):
        nonlocal current_character_id
        selection = character_list.curselection()
        if not selection:
            current_character_id = None
            _clear_character_details()
            _set_broadcast_filter()
            return
        current_character_id = character_ids[selection[0]]
        _populate_character_details()
        _set_broadcast_filter("character", current_character_id)

    def _sync_character_voice_selection(character: Character):
        voice_selector.selection_clear(0, "end")
        for idx, vid in enumerate(voice_ids):
            if vid in character.voice_ids:
                voice_selector.selection_set(idx)

    def _collect_character_voice_ids() -> list[str]:
        selected = voice_selector.curselection()
        return [voice_ids[idx] for idx in selected]

    def _create_character():
        name = char_name_var.get().strip() or "New Character"
        char_id = _generate_id("character", set(project.characters.keys()))
        new_character = Character(id=char_id, name=name)
        project.characters[char_id] = new_character
        refresh_all()
        nonlocal current_character_id
        current_character_id = char_id
        _sync_character_selection()

    def _apply_character_changes(
        character_id: str | None, name: str, notes: str, selected_ids: list[str]
    ) -> bool:
        if not character_id:
            return False
        character = project.characters.get(character_id)
        if not character:
            return False
        if len(selected_ids) > 4:
            messagebox.showerror("Voice limit", "A character can only reference up to 4 voices.")
            return False
        character.name = name or character.name
        character.notes = notes
        character.voice_ids = selected_ids
        return True

    def _save_character():
        notes = character_notes.get("1.0", "end").strip()
        selected_ids = _collect_character_voice_ids()
        if not _apply_character_changes(current_character_id, char_name_var.get().strip(), notes, selected_ids):
            return
        refresh_all()
        _sync_character_selection()

    def _delete_character():
        nonlocal current_character_id
        if not current_character_id:
            return
        project.characters.pop(current_character_id, None)
        for group in project.groups.values():
            if current_character_id in group.character_ids:
                group.character_ids.remove(current_character_id)
        current_character_id = None
        refresh_all()
        _set_broadcast_filter()

    def _open_character_details_popup():
        if not current_character_id:
            return
        character = project.characters.get(current_character_id)
        if not character:
            return
        popup = tk.Toplevel(frame)
        popup.title(f"Character details - {character.name or character.id}")
        popup.transient(frame)
        popup.grab_set()
        popup.columnconfigure(0, weight=1)

        detail_name_var = tk.StringVar(value=character.name)
        ttk.Label(popup, text="Name").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        ttk.Entry(popup, textvariable=detail_name_var).grid(
            row=1, column=0, sticky="ew", padx=8, pady=(0, 8)
        )

        ttk.Label(popup, text="Notes").grid(row=2, column=0, sticky="w", padx=8)
        detail_notes = tk.Text(
            popup,
            height=6,
            wrap="word",
            background=PANEL_BG,
            foreground=LIGHT_TEXT,
            insertbackground=ACCENT_CYAN,
            relief="flat",
            borderwidth=0,
        )
        detail_notes.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 8))
        detail_notes.insert("1.0", character.notes)

        popup.columnconfigure(0, weight=1)
        popup.rowconfigure(3, weight=1)
        ttk.Label(popup, text="Assign voices (up to 4)").grid(row=4, column=0, sticky="w", padx=8)
        popup_voice_frame = ttk.Frame(popup)
        popup_voice_frame.grid(row=5, column=0, sticky="ew", padx=8, pady=(0, 8))
        popup_voice_frame.columnconfigure(0, weight=1)
        popup_voice_view = tk.Listbox(
            popup_voice_frame,
            height=6,
            selectmode="extended",
            background=SLATE_BG,
            foreground=LIGHT_TEXT,
            activestyle="none",
            exportselection=False,
            highlightthickness=0,
        )
        popup_voice_view.grid(row=0, column=0, sticky="nsew")
        popup_voice_scroll = ttk.Scrollbar(popup_voice_frame, orient="vertical", command=popup_voice_view.yview)
        popup_voice_scroll.grid(row=0, column=1, sticky="ns")
        popup_voice_view.configure(yscrollcommand=popup_voice_scroll.set)

        sorted_voices = sorted(project.voices.values(), key=lambda voice: (voice.name or voice.id).lower())
        popup_voice_ids = [voice.id for voice in sorted_voices]
        for idx, voice in enumerate(sorted_voices):
            popup_voice_view.insert("end", voice.name or voice.id)
            if voice.id in character.voice_ids:
                popup_voice_view.selection_set(idx)

        groups_using = [
            group.name for group in project.groups.values() if current_character_id in group.character_ids
        ]
        ttk.Label(
            popup,
            text=f"Groups: {', '.join(groups_using) or 'none'}",
            foreground=SECONDARY_TEXT,
        ).grid(row=6, column=0, sticky="w", padx=8, pady=(0, 8))

        button_row = ttk.Frame(popup)
        button_row.grid(row=7, column=0, sticky="ew", padx=8, pady=(0, 8))
        button_row.columnconfigure(0, weight=1)
        button_row.columnconfigure(1, weight=1)

        def _save_details():
            voice_selection = popup_voice_view.curselection()
            selected_ids = [popup_voice_ids[idx] for idx in voice_selection]
            if not _apply_character_changes(
                current_character_id, detail_name_var.get().strip(), detail_notes.get("1.0", "end").strip(), selected_ids
            ):
                return
            refresh_all()
            _sync_character_selection()
            popup.destroy()

        ttk.Button(button_row, text="Save", command=_save_details).grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )
        ttk.Button(button_row, text="Cancel", command=popup.destroy).grid(
            row=0, column=1, sticky="ew", padx=(4, 0)
        )

    def _refresh_voices():
        nonlocal voice_ids, current_voice_id
        voice_tree.delete(*voice_tree.get_children())
        voice_selector.delete(0, "end")
        sorted_voices = sorted(project.voices.values(), key=lambda v: (v.name or v.id).lower())
        filter_term = (voice_search_var.get() or "").strip().lower()
        voice_ids = [voice.id for voice in sorted_voices]
        for voice in sorted_voices:
            voice_selector.insert("end", f"{voice.name or voice.id} ({voice.color})")
            label = (voice.name or voice.id).lower()
            if filter_term and filter_term not in label:
                continue
            voice_tree.insert(
                "",
                "end",
                iid=voice.id,
                values=(voice.color, voice.name or voice.id),
                tags=(voice.id,),
            )
            voice_tree.tag_configure(voice.id, background=voice.color, foreground=_contrast_color(voice.color))
        _sync_voice_selection()
        if current_character_id:
            _sync_character_voice_selection(project.characters.get(current_character_id))

    def _sync_voice_selection():
        if current_voice_id and current_voice_id in voice_ids:
            if voice_tree.exists(current_voice_id):
                voice_tree.selection_set(current_voice_id)
            else:
                voice_tree.selection_remove(voice_tree.selection())
            _populate_voice_details()
        else:
            voice_tree.selection_remove(voice_tree.selection())
            _clear_voice_details()

    def _clear_voice_details():
        voice_name_var.set("")
        voice_notes.configure(state="normal")
        voice_notes.delete("1.0", "end")
        voice_notes.configure(state="normal")
        voice_usage_label.configure(text="Used by characters: none")
        color_var.set("#ffffff")
        color_button.configure(background=color_var.get())

    def _populate_voice_details():
        voice = project.voices.get(current_voice_id)
        if not voice:
            _clear_voice_details()
            return
        voice_name_var.set(voice.name)
        voice_notes.configure(state="normal")
        voice_notes.delete("1.0", "end")
        voice_notes.insert("1.0", voice.notes)
        voice_notes.configure(state="normal")
        color_var.set(voice.color)
        color_button.configure(background=voice.color)
        characters_using = [char.name for char in project.characters.values() if voice.id in char.voice_ids]
        voice_usage_label.configure(text=f"Used by characters: {', '.join(characters_using) or 'none'}")

    def _on_voice_selected(event=None):
        nonlocal current_voice_id
        selection = voice_tree.selection()
        if not selection:
            current_voice_id = None
            _clear_voice_details()
            _set_broadcast_filter()
            return
        current_voice_id = selection[0]
        _populate_voice_details()
        _set_broadcast_filter("voice", current_voice_id)

    def _create_voice():
        name = voice_name_var.get().strip() or "New Voice"
        voice_id = _generate_id("voice", set(project.voices.keys()))
        color = color_var.get()
        project.voices[voice_id] = Voice(id=voice_id, name=name, color=color)
        refresh_all()
        nonlocal current_voice_id
        current_voice_id = voice_id
        _sync_voice_selection()

    def _save_voice():
        if not current_voice_id:
            return
        voice = project.voices.get(current_voice_id)
        if not voice:
            return
        voice.name = voice_name_var.get().strip() or voice.name
        voice.notes = voice_notes.get("1.0", "end").strip()
        voice.color = color_var.get()
        refresh_all()
        _sync_voice_selection()

    def _resolve_broadcast_filter() -> tuple[set[str] | None, str]:
        scope = broadcast_filter_scope
        identifier = broadcast_filter_id
        voice_ids: set[str] | None = None
        label = "Filter: All broadcasts"
        if scope == "voice" and identifier:
            voice = project.voices.get(identifier)
            name = voice.name if voice and voice.name else identifier
            label = f"Filter: Voice - {name}"
            voice_ids = {identifier}
        elif scope == "character" and identifier:
            character = project.characters.get(identifier)
            name = character.name if character and character.name else identifier
            label = f"Filter: Character - {name}"
            voice_ids = set(character.voice_ids) if character else set()
        elif scope == "group" and identifier:
            group = project.groups.get(identifier)
            name = group.name if group and group.name else identifier
            label = f"Filter: Group - {name}"
            collected: set[str] = set()
            if group:
                for cid in group.character_ids:
                    character = project.characters.get(cid)
                    if character:
                        collected.update(character.voice_ids)
            voice_ids = collected
        if voice_ids is not None and not voice_ids:
            label += " (no voices assigned)"
        return voice_ids, label

    def _speaker_from_line(line: Line) -> tuple[str, str | None]:
        voice = project.voices.get(line.voice_id) if line.voice_id else None
        if voice and voice.name:
            return voice.name, voice.color
        return (line.voice_id or "Unknown", None)

    def _channel_name_for_broadcast(broadcast_id: str) -> str:
        for channel in project.channels.values():
            if any(entry.broadcast_id == broadcast_id for entry in channel.schedule):
                return channel.name
        return "-"

    def _refresh_line_interface(broadcast: Broadcast | None):
        lines_list.delete(0, "end")
        transcript_text.configure(state="normal")
        transcript_text.delete("1.0", "end")
        if not broadcast:
            transcript_text.insert("1.0", "No broadcast selected.")
            return
        for idx, line in enumerate(broadcast.lines):
            speaker_name, speaker_color = _speaker_from_line(line)
            display = f"{idx + 1:02d}. {speaker_name}: {line.text or ''}"
            lines_list.insert("end", display)
            if speaker_color:
                lines_list.itemconfig(idx, foreground=speaker_color)
        transcript_text.insert(
            "1.0",
            "\n".join(line.text or "" for line in broadcast.lines),
        )

    def _parse_transcript_entry(line_text: str) -> tuple[str, str | None]:
        content = line_text.strip()
        if not content:
            return "", None
        if ":" in content:
            hint, remainder = content.split(":", 1)
            voice_hint = _resolve_speaker_hint(hint.strip())
            return remainder.strip(), voice_hint
        return content, None

    def _resolve_speaker_hint(hint: str) -> str | None:
        lowered = hint.lower()
        for voice in project.voices.values():
            if voice.name and voice.name.lower() == lowered:
                return voice.id
        for character in project.characters.values():
            if character.name and character.name.lower() == lowered:
                if character.voice_ids:
                    return character.voice_ids[0]
        return None

    def _save_transcript_lines():
        if not current_broadcast_id:
            return
        broadcast = project.broadcasts.get(current_broadcast_id)
        if not broadcast:
            return
        parsed_lines: list[tuple[str, str | None]] = []
        for raw_line in transcript_text.get("1.0", "end").splitlines():
            text, voice_hint = _parse_transcript_entry(raw_line)
            if not text:
                continue
            parsed_lines.append((text, voice_hint))
        default_voice = current_voice_id or (voice_ids[0] if voice_ids else None)
        if not parsed_lines:
            broadcast.lines.clear()
            refresh_all()
            return
        for idx, (text, voice_hint) in enumerate(parsed_lines):
            if idx < len(broadcast.lines):
                line = broadcast.lines[idx]
            else:
                line = Line(text="", voice_id=default_voice)
                broadcast.lines.append(line)
            if voice_hint:
                line.voice_id = voice_hint
            line.text = text
        if len(broadcast.lines) > len(parsed_lines):
            del broadcast.lines[len(parsed_lines) :]
        refresh_all()

    def _refresh_broadcast_list():
        nonlocal broadcast_ids, current_broadcast_id
        match_voice_ids, label = _resolve_broadcast_filter()
        broadcast_filter_label.configure(text=label)
        candidates: list[Broadcast] = []
        if match_voice_ids is None:
            candidates = list(project.broadcasts.values())
        elif match_voice_ids:
            candidates = [
                broadcast
                for broadcast in project.broadcasts.values()
                if any(line.voice_id in match_voice_ids for line in broadcast.lines)
            ]
        ordered = sorted(candidates, key=lambda broadcast: (broadcast.title or broadcast.id).lower())
        broadcast_tree.delete(*broadcast_tree.get_children())
        broadcast_ids = [broadcast.id for broadcast in ordered]
        for broadcast in ordered:
            first_line = broadcast.lines[0] if broadcast.lines else None
            first_line_text = ""
            row_color = None
            if first_line:
                first_line_name, row_color = _speaker_from_line(first_line)
                first_line_text = f"{first_line_name}: {first_line.text or ''}"
            channel_name = _channel_name_for_broadcast(broadcast.id)
            values = (
                channel_name,
                broadcast.title or "Untitled",
                first_line_text,
                broadcast.day + 1,
                len(broadcast.lines),
            )
            if row_color:
                tag_name = f"voice-color-{broadcast.id}"
                broadcast_tree.insert("", "end", iid=broadcast.id, values=values, tags=(tag_name,))
                broadcast_tree.tag_configure(tag_name, foreground=row_color)
            else:
                broadcast_tree.insert("", "end", iid=broadcast.id, values=values)
        if not broadcast_ids:
            current_broadcast_id = None
            _refresh_line_interface(None)
            return
        if current_broadcast_id not in broadcast_ids:
            current_broadcast_id = broadcast_ids[0]
        if broadcast_tree.exists(current_broadcast_id):
            broadcast_tree.selection_set(current_broadcast_id)
            broadcast_tree.see(current_broadcast_id)
        _refresh_line_interface(project.broadcasts.get(current_broadcast_id))

    def _on_broadcast_selected(event=None):
        nonlocal current_broadcast_id
        match_voice_ids, _ = _resolve_broadcast_filter()
        selection = broadcast_tree.selection()
        if not selection:
            current_broadcast_id = None
            _refresh_line_interface(None)
            return
        current_broadcast_id = selection[0]
        _refresh_line_interface(project.broadcasts.get(current_broadcast_id))

    def refresh_all():
        _refresh_groups()
        _refresh_characters()
        _refresh_voices()
        _refresh_broadcast_list()

    context.register_refresh_callback(refresh_all)

    _render_palette()
    group_search_var.trace_add("write", lambda *_: _refresh_groups())
    character_search_var.trace_add("write", lambda *_: _refresh_characters())
    voice_search_var.trace_add("write", lambda *_: _refresh_voices())
    ttk.Button(
        voice_palette_zone,
        text="Add custom color",
        command=_choose_custom_color,
        style="Accent.TButton",
    ).grid(row=3, column=0, sticky="w", pady=(6, 0))
    group_list.bind("<<ListboxSelect>>", _on_group_selected)
    character_list.bind("<<ListboxSelect>>", _on_character_selected)
    voice_tree.bind("<<TreeviewSelect>>", _on_voice_selected)
    broadcast_tree.bind("<<TreeviewSelect>>", _on_broadcast_selected)
    refresh_all()
    return frame
