import tkinter as tk
from tkinter import ttk, simpledialog

from typing import Callable

from ...config import settings
from ...core import AppContext, Line, project_ops
from ...core.models import Character
from ..styles import ACCENT_CYAN, LIGHT_TEXT, SECONDARY_TEXT, SLATE_BG
from .utils import channel_color_map, fallback_title, format_time, lines_as_text

START_TIMES = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]
DURATIONS = [f"{m // 60:02d}:{m % 60:02d}" for m in range(30, 24 * 60, 30)]


def _hhmm_to_seconds(value: str) -> float:
    try:
        hours, minutes = map(int, value.split(":"))
        return hours * 3600 + minutes * 60
    except ValueError:
        return 0.0


def _seconds_to_hhmm(value: float) -> str:
    hours = int(value) // 3600
    minutes = (int(value) % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"


def _is_radio_channel(channel) -> bool:
    category = (channel.category or "").lower()
    return any(keyword in category for keyword in ("radio", "amateur", "military"))


def make_tab(parent, context: AppContext):
    frame = ttk.Frame(parent)
    frame.configure(style="TFrame")
    frame.columnconfigure(0, weight=0)
    frame.columnconfigure(1, weight=1)
    frame.columnconfigure(2, weight=2)
    frame.rowconfigure(0, weight=1)
    frame.rowconfigure(1, weight=0)
    frame.rowconfigure(2, weight=1)

    channel_frame = ttk.LabelFrame(frame, text="Channels")
    channel_frame.grid(row=0, column=0, sticky="ns", padx=12, pady=12)
    channel_frame.columnconfigure(0, weight=1)
    channel_frame.rowconfigure(0, weight=1)
    channels_list = tk.Listbox(
        channel_frame,
        width=32,
        exportselection=False,
        activestyle="none",
        background=SLATE_BG,
        font=("Spectral", 20),
        foreground=LIGHT_TEXT,
        selectbackground=ACCENT_CYAN,
        selectforeground="#04060a",
        highlightthickness=0,
    )
    channels_list.grid(row=0, column=0, sticky="nsew")
    channel_scroll = ttk.Scrollbar(channel_frame, orient="vertical", command=channels_list.yview)
    channels_list.configure(yscrollcommand=channel_scroll.set)
    channel_scroll.grid(row=0, column=1, sticky="ns")

    broadcast_frame = ttk.LabelFrame(frame, text="Broadcasts")
    broadcast_frame.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
    broadcast_frame.columnconfigure(0, weight=1)
    broadcast_frame.rowconfigure(0, weight=0)
    broadcast_frame.rowconfigure(1, weight=1)
    broadcast_frame.rowconfigure(2, weight=0)
    broadcast_search_var = tk.StringVar()
    search_frame = ttk.Frame(broadcast_frame)
    search_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 2))
    search_frame.columnconfigure(1, weight=1)
    ttk.Label(search_frame, text="Search").grid(row=0, column=0, sticky="w")
    ttk.Entry(search_frame, textvariable=broadcast_search_var).grid(
        row=0, column=1, sticky="ew", padx=(4, 0)
    )
    ttk.Button(search_frame, text="Clear", command=lambda: broadcast_search_var.set("")).grid(
        row=0, column=2, sticky="w", padx=(4, 0)
    )
    columns = ("day", "start", "end", "first_line", "lines")
    broadcast_tree = ttk.Treeview(
        broadcast_frame, columns=columns, show="headings", selectmode="browse", height=20
    )
    widths = {"day": 70, "start": 70, "end": 70, "first_line": 320, "lines": 80}
    for col, heading in zip(columns, ("Day", "Start", "End", "First line", "Lines")):
        anchor = "center" if col in ("day", "start", "end", "lines") else "w"
        broadcast_tree.heading(col, text=heading, anchor=anchor)
        broadcast_tree.column(
            col,
            anchor=anchor,
            stretch=(col == "first_line"),
            width=widths.get(col, 120),
        )
    broadcast_tree.tag_configure("day-bold", font=("Segoe UI", 10))
    broadcast_tree.grid(row=1, column=0, sticky="nsew")
    broadcast_scroll = ttk.Scrollbar(broadcast_frame, orient="vertical", command=broadcast_tree.yview)
    broadcast_tree.configure(yscrollcommand=broadcast_scroll.set)
    broadcast_scroll.grid(row=1, column=1, sticky="ns")

    creation_frame = ttk.LabelFrame(frame, text="Create broadcast")
    creation_frame.grid(row=2, column=1, sticky="ew", padx=12, pady=(0, 12))
    creation_frame.columnconfigure(1, weight=1)
    new_title_var = tk.StringVar()
    new_desc_var = tk.StringVar()
    new_day_var = tk.IntVar(value=0)
    start_label_var = tk.StringVar(value="00:00")
    new_duration_var = tk.StringVar(value=DURATIONS[0])
    channel_combo = ttk.Combobox(creation_frame, state="readonly")
    creation_status_var = tk.StringVar(value="")

    def refresh_channel_combo():
        if not channel_ids:
            channel_combo["values"] = []
            return
        channel_combo["values"] = [
            f"{context.project.channels[cid].name} ({context.project.channels[cid].frequency:.1f})"
            for cid in channel_ids
        ]
        if channel_combo["values"]:
            current = channel_combo.current()
            if current == -1:
                channel_combo.current(0)

    ttk.Label(creation_frame, text="Title").grid(row=0, column=0, sticky="w", padx=4, pady=2)
    ttk.Entry(creation_frame, textvariable=new_title_var).grid(row=0, column=1, sticky="ew", padx=4, pady=2)
    ttk.Label(creation_frame, text="Description").grid(row=1, column=0, sticky="w", padx=4, pady=2)
    ttk.Entry(creation_frame, textvariable=new_desc_var).grid(row=1, column=1, sticky="ew", padx=4, pady=2)
    ttk.Label(creation_frame, text="Channel").grid(row=2, column=0, sticky="w", padx=4, pady=2)
    channel_combo.grid(row=2, column=1, sticky="ew", padx=4, pady=2)
    ttk.Label(creation_frame, text="Day").grid(row=3, column=0, sticky="w", padx=4, pady=2)
    day_spinbox = ttk.Spinbox(
        creation_frame,
        from_=0,
        to=99,
        increment=1,
        textvariable=new_day_var,
        width=6,
    )
    day_spinbox.grid(row=3, column=1, sticky="w", padx=4, pady=2)
    ttk.Label(creation_frame, text="Start (HH:MM)").grid(row=4, column=0, sticky="w", padx=4, pady=2)
    ttk.Label(creation_frame, text="Start (auto)").grid(row=4, column=0, sticky="w", padx=4, pady=2)
    ttk.Label(creation_frame, textvariable=start_label_var).grid(row=4, column=1, sticky="w", padx=4, pady=2)
    ttk.Label(creation_frame, text="Duration").grid(row=5, column=0, sticky="w", padx=4, pady=2)
    duration_combo = ttk.Combobox(
        creation_frame,
        values=DURATIONS,
        textvariable=new_duration_var,
        state="readonly",
    )
    duration_combo.grid(row=5, column=1, sticky="w", padx=4, pady=2)

    creation_line_text_var = tk.StringVar()
    creation_voice_var = tk.StringVar()
    creation_character_var = tk.StringVar()
    creation_moodle_var = tk.StringVar()
    creation_effects_var = tk.StringVar()
    creation_sound_var = tk.StringVar()
    creation_character_display_map: dict[str, str] = {}

    creation_notebook = ttk.Notebook(creation_frame, style="Neon.TNotebook")
    creation_notebook.grid(row=6, column=0, columnspan=2, sticky="nsew", pady=(8, 4))
    creation_notebook.columnconfigure(0, weight=1)
    creation_notebook.rowconfigure(0, weight=1)

    creation_line_tab = ttk.Frame(creation_notebook)
    creation_line_tab.columnconfigure(1, weight=1)
    creation_notebook.add(creation_line_tab, text="Line")

    ttk.Label(creation_line_tab, text="Line text").grid(row=0, column=0, sticky="w", padx=4, pady=2)
    ttk.Entry(creation_line_tab, textvariable=creation_line_text_var).grid(
        row=0, column=1, sticky="ew", padx=4, pady=2
    )
    ttk.Label(creation_line_tab, text="Voice").grid(row=1, column=0, sticky="w", padx=4, pady=2)
    creation_voice_combo = ttk.Combobox(creation_line_tab, textvariable=creation_voice_var, state="readonly")
    creation_voice_combo.grid(row=1, column=1, sticky="ew", padx=4, pady=2)
    ttk.Label(creation_line_tab, text="Character").grid(row=2, column=0, sticky="w", padx=4, pady=2)
    creation_character_combo = ttk.Combobox(creation_line_tab, textvariable=creation_character_var, state="readonly")
    creation_character_combo.grid(row=2, column=1, sticky="ew", padx=4, pady=2)
    ttk.Label(creation_line_tab, text="Moodle").grid(row=3, column=0, sticky="w", padx=4, pady=2)
    ttk.Entry(creation_line_tab, textvariable=creation_moodle_var).grid(
        row=3, column=1, sticky="ew", padx=4, pady=2
    )
    ttk.Label(creation_line_tab, text="Effects").grid(row=4, column=0, sticky="w", padx=4, pady=2)
    ttk.Entry(creation_line_tab, textvariable=creation_effects_var).grid(
        row=4, column=1, sticky="ew", padx=4, pady=2
    )
    ttk.Label(creation_line_tab, text="Sound file").grid(row=5, column=0, sticky="w", padx=4, pady=2)
    ttk.Entry(creation_line_tab, textvariable=creation_sound_var).grid(
        row=5, column=1, sticky="ew", padx=4, pady=2
    )

    creation_transcript_tab = ttk.Frame(creation_notebook)
    creation_transcript_tab.columnconfigure(0, weight=1)
    creation_transcript_tab.rowconfigure(0, weight=1)
    creation_notebook.add(creation_transcript_tab, text="Transcript")
    creation_transcript_text = tk.Text(
        creation_transcript_tab,
        height=5,
        wrap="word",
        background=SLATE_BG,
        foreground=LIGHT_TEXT,
        insertbackground=ACCENT_CYAN,
        relief="sunken",
    )
    creation_transcript_text.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
    creation_transcript_scroll = ttk.Scrollbar(
        creation_transcript_tab, orient="vertical", command=creation_transcript_text.yview
    )
    creation_transcript_scroll.grid(row=0, column=1, sticky="ns", padx=(0, 4), pady=4)
    creation_transcript_text.configure(yscrollcommand=creation_transcript_scroll.set)
    ttk.Label(
        creation_transcript_tab,
        text="Use Speaker: line format or plain text for each line.",
        foreground=SECONDARY_TEXT,
    ).grid(row=1, column=0, sticky="w", padx=4, pady=(0, 4))

    ttk.Button(
        creation_frame,
        text="Create broadcast",
        style="Accent.TButton",
        command=lambda: _handle_create_broadcast(),
    ).grid(row=7, column=0, columnspan=2, pady=4)
    ttk.Label(creation_frame, textvariable=creation_status_var, foreground="#f4d6a2").grid(
        row=8, column=0, columnspan=2, sticky="w", padx=4, pady=(2, 0)
    )
    channel_combo.bind("<<ComboboxSelected>>", lambda _: _update_channel_defaults())

    detail_frame = ttk.LabelFrame(frame, text="Broadcast details")
    detail_frame.grid(row=0, column=2, rowspan=3, sticky="nsew", padx=12, pady=12)
    detail_frame.columnconfigure(0, weight=1)
    detail_frame.rowconfigure(0, weight=0)
    detail_frame.rowconfigure(1, weight=1)

    detail_panel = ttk.Frame(detail_frame)
    detail_panel.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
    detail_panel.columnconfigure(1, weight=1)
    title_var = tk.StringVar()
    desc_text = tk.Text(
        detail_panel,
        height=4,
        wrap="word",
        background="#050916",
        foreground=LIGHT_TEXT,
        insertbackground=ACCENT_CYAN,
        relief="sunken",
    )
    desc_scroll = ttk.Scrollbar(detail_panel, orient="vertical", command=desc_text.yview)
    desc_text.configure(yscrollcommand=desc_scroll.set)
    line_info_var = tk.StringVar(value="Select a line to inspect metadata.")
    meta_var = tk.StringVar()
    fallback_var = tk.StringVar()
    info_var = tk.StringVar(value="Select a broadcast to inspect its lines.")

    ttk.Label(detail_panel, text="Title").grid(row=0, column=0, sticky="w", pady=2)
    ttk.Entry(detail_panel, textvariable=title_var).grid(row=0, column=1, sticky="ew", pady=2)
    ttk.Label(detail_panel, text="Description").grid(row=1, column=0, sticky="nw", pady=2)
    desc_text.grid(row=1, column=1, sticky="ew", pady=2)
    desc_scroll.grid(row=1, column=2, sticky="ns", pady=2)
    fallback_label = ttk.Label(detail_panel, textvariable=fallback_var, foreground="#7fc1ff")
    fallback_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=2)
    meta_label = ttk.Label(detail_panel, textvariable=meta_var, foreground="#8f94a6")
    meta_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=2)
    ttk.Label(detail_panel, text="Line info").grid(row=4, column=0, sticky="w", pady=2)
    line_info_label = ttk.Label(detail_panel, textvariable=line_info_var, foreground="#c0c6e8")
    line_info_label.grid(row=4, column=1, sticky="w", pady=2)
    info_label = ttk.Label(detail_panel, textvariable=info_var, foreground="#8f94a6")
    info_label.grid(row=5, column=0, columnspan=2, sticky="w", pady=2)
    details_controls = ttk.Frame(detail_panel)
    details_controls.grid(row=6, column=0, columnspan=2, pady=8)

    reorder_frame = ttk.Frame(detail_panel)
    reorder_frame.grid(row=6, column=2, sticky="e", pady=8, padx=4)

    schedule_frame = ttk.LabelFrame(detail_panel, text="Reschedule broadcast")
    schedule_frame.grid(row=7, column=0, columnspan=2, sticky="ew", pady=4)
    schedule_frame.columnconfigure(1, weight=1)
    schedule_day_var = tk.IntVar(value=0)
    schedule_start_label_var = tk.StringVar(value="00:00")
    schedule_duration_var = tk.StringVar(value=DURATIONS[0])
    ttk.Label(schedule_frame, text="Day").grid(row=0, column=0, sticky="w", padx=4, pady=2)
    ttk.Spinbox(
        schedule_frame,
        from_=0,
        to=99,
        increment=1,
        textvariable=schedule_day_var,
        width=6,
    ).grid(row=0, column=1, sticky="w", padx=4, pady=2)
    ttk.Label(schedule_frame, text="Start").grid(row=1, column=0, sticky="w", padx=4, pady=2)
    ttk.Label(schedule_frame, textvariable=schedule_start_label_var).grid(
        row=1, column=1, sticky="w", padx=4, pady=2
    )
    ttk.Label(schedule_frame, text="Duration").grid(row=2, column=0, sticky="w", padx=4, pady=2)
    ttk.Combobox(
        schedule_frame,
        values=DURATIONS,
        textvariable=schedule_duration_var,
        state="readonly",
        width=6,
    ).grid(row=2, column=1, sticky="w", padx=4, pady=2)
    ttk.Button(schedule_frame, text="Apply", command=lambda: _handle_reschedule()).grid(
        row=3, column=0, columnspan=2, pady=4
    )

    detail_notebook = ttk.Notebook(detail_frame, style="Neon.TNotebook")
    detail_notebook.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
    lines_tab = ttk.Frame(detail_notebook)
    transcript_tab = ttk.Frame(detail_notebook)
    detail_notebook.add(lines_tab, text="Lines")
    detail_notebook.add(transcript_tab, text="Transcript")

    # Lines tab widgets
    lines_tab.columnconfigure(0, weight=1)
    lines_tab.rowconfigure(0, weight=1)
    lines_list = tk.Listbox(
        lines_tab,
        height=10,
        background=SLATE_BG,
        foreground=LIGHT_TEXT,
        selectbackground=ACCENT_CYAN,
        selectforeground="#04060a",
        highlightthickness=0,
        selectmode="extended",
    )
    lines_list.grid(row=0, column=0, sticky="nsew")
    lines_scroll = ttk.Scrollbar(lines_tab, orient="vertical", command=lines_list.yview)
    lines_list.configure(yscrollcommand=lines_scroll.set)
    lines_scroll.grid(row=0, column=1, sticky="ns")

    def _apply_to_selected_lines(operation: Callable[[Line], None]):
        active = context.active_broadcast
        if not active:
            return
        changed = False
        for idx in lines_list.curselection():
            if idx >= len(active.lines):
                continue
            operation(active.lines[idx])
            changed = True
        if changed:
            update_selection()

    def _assign_voice_to_selection(voice_id: str):
        nonlocal preferred_voice_id
        _apply_to_selected_lines(lambda line: setattr(line, "voice_id", voice_id))
        preferred_voice_id = voice_id

    def _clear_voice_from_selection():
        _apply_to_selected_lines(lambda line: setattr(line, "voice_id", None))

    def _character_display(character: Character) -> str:
        name = character.name or "Character"
        return f"{name} ({character.id})"

    def _character_color(character: Character) -> str:
        for vid in character.voice_ids:
            voice = context.project.voices.get(vid)
            if voice and voice.color:
                return voice.color
        return "#000000"

    def _assign_character_to_selection(character_id: str):
        nonlocal preferred_character_id
        _apply_to_selected_lines(lambda line: setattr(line, "character_id", character_id))
        preferred_character_id = character_id

    def _clear_character_from_selection():
        _apply_to_selected_lines(lambda line: setattr(line, "character_id", None))

    def _add_effect_to_selection():
        effect = simpledialog.askstring("Add effect", "Enter effect tag (comma separated) or single:")
        if not effect:
            return
        tokens = [token.strip() for token in effect.split(",") if token.strip()]
        _apply_to_selected_lines(lambda line: setattr(line, "effects", list(dict.fromkeys(line.effects + tokens))))

    def _remove_effects_from_selection():
        _apply_to_selected_lines(lambda line: setattr(line, "effects", []))

    def _build_line_context_menu(event):
        context_menu = tk.Menu(lines_list, tearoff=0)
        voice_menu = tk.Menu(context_menu, tearoff=0)
        voices = list(context.project.voices.values())
        if voices:
            for voice in voices:
                color = voice.color or "#000000"
                voice_menu.add_command(
                    label=voice.name,
                    command=lambda vid=voice.id: _assign_voice_to_selection(vid),
                    background=color,
                    foreground=_contrast_color(color),
                )
            context_menu.add_cascade(label="Set voice", menu=voice_menu)
            context_menu.add_command(label="Clear voice", command=_clear_voice_from_selection)
            context_menu.add_separator()
        character_menu = tk.Menu(context_menu, tearoff=0)
        characters = sorted(context.project.characters.values(), key=lambda char: (char.name or char.id).lower())
        if characters:
            for character in characters:
                color = _character_color(character)
                display = _character_display(character)
                character_menu.add_command(
                    label=display,
                    command=lambda cid=character.id: _assign_character_to_selection(cid),
                    background=color,
                    foreground=_contrast_color(color),
                )
            context_menu.add_cascade(label="Set character", menu=character_menu)
            context_menu.add_command(label="Clear character", command=_clear_character_from_selection)
            context_menu.add_separator()
        context_menu.add_command(label="Add effect", command=_add_effect_to_selection)
        context_menu.add_command(label="Remove effects", command=_remove_effects_from_selection)

        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    lines_list.bind("<Button-3>", _build_line_context_menu)

    line_editor = ttk.LabelFrame(lines_tab, text="Line editor")
    line_editor.grid(row=1, column=0, columnspan=2, sticky="ew", pady=4)
    line_editor.columnconfigure(1, weight=1)
    line_text_var = tk.StringVar()
    line_voice_var = tk.StringVar()
    line_character_var = tk.StringVar()
    line_moodle_var = tk.StringVar()
    line_effects_var = tk.StringVar()
    line_sound_var = tk.StringVar()
    preferred_voice_id: str | None = None
    preferred_character_id: str | None = None
    line_character_display_map: dict[str, str] = {}

    def _contrast_color(hex_color: str) -> str:
        hex_color = (hex_color or "#000000").lstrip("#")
        if len(hex_color) != 6:
            return "#000000"
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        return "#000000" if brightness > 186 else "#ffffff"

    ttk.Label(line_editor, text="Text").grid(row=0, column=0, sticky="w", padx=4, pady=2)
    ttk.Entry(line_editor, textvariable=line_text_var).grid(row=0, column=1, sticky="ew", padx=4, pady=2)
    ttk.Label(line_editor, text="Voice").grid(row=1, column=0, sticky="w", padx=4, pady=2)
    voice_combo = ttk.Combobox(line_editor, textvariable=line_voice_var, state="readonly")
    voice_combo.grid(row=1, column=1, sticky="ew", padx=4, pady=2)
    ttk.Label(line_editor, text="Character").grid(row=2, column=0, sticky="w", padx=4, pady=2)
    character_combo = ttk.Combobox(line_editor, textvariable=line_character_var, state="readonly")
    character_combo.grid(row=2, column=1, sticky="ew", padx=4, pady=2)
    ttk.Label(line_editor, text="Moodle").grid(row=3, column=0, sticky="w", padx=4, pady=2)
    ttk.Entry(line_editor, textvariable=line_moodle_var).grid(row=3, column=1, sticky="ew", padx=4, pady=2)
    ttk.Label(line_editor, text="Effects").grid(row=4, column=0, sticky="w", padx=4, pady=2)
    ttk.Entry(line_editor, textvariable=line_effects_var).grid(row=4, column=1, sticky="ew", padx=4, pady=2)
    ttk.Label(line_editor, text="Sound file").grid(row=5, column=0, sticky="w", padx=4, pady=2)
    ttk.Entry(line_editor, textvariable=line_sound_var).grid(row=5, column=1, sticky="ew", padx=4, pady=2)

    line_button_frame = ttk.Frame(line_editor)
    line_button_frame.grid(row=6, column=0, columnspan=2, pady=6)
    ttk.Button(
        line_button_frame,
        text="Update line",
        command=lambda: update_line(
            context,
            lines_list,
            line_text_var,
            line_voice_var,
            line_character_var,
            line_moodle_var,
            line_effects_var,
            line_sound_var,
        ),
    ).pack(side="left", padx=4)
    ttk.Button(line_button_frame, text="Copy GUID", command=lambda: copy_line_guid(lines_list, parent, context)).pack(
        side="left", padx=4
    )
    ttk.Button(line_button_frame, text="Delete line", command=lambda: delete_line(context, lines_list)).pack(side="left", padx=4)
    ttk.Button(line_button_frame, text="Add line", command=lambda: _handle_add_line(), style="Accent.TButton").pack(side="left", padx=4)

    def update_voice_combobox():
        names = [voice.name for voice in context.project.voices.values()]
        voice_combo["values"] = names
        if line_voice_var.get() not in names:
            line_voice_var.set("")

    def update_character_combobox():
        line_character_display_map.clear()
        sorted_characters = sorted(
            context.project.characters.values(), key=lambda char: (char.name or char.id).lower()
        )
        names = []
        for character in sorted_characters:
            display = _character_display(character)
            names.append(display)
            line_character_display_map[display] = character.id
        character_combo["values"] = names
        if line_character_var.get() not in line_character_display_map:
            line_character_var.set("")

    def _update_creation_voice_combo():
        names = [voice.name for voice in context.project.voices.values()]
        creation_voice_combo["values"] = names
        if creation_voice_var.get() not in names:
            creation_voice_var.set("")

    def _update_creation_character_combo():
        creation_character_display_map.clear()
        sorted_characters = sorted(
            context.project.characters.values(), key=lambda char: (char.name or char.id).lower()
        )
        names = []
        for character in sorted_characters:
            display = _character_display(character)
            names.append(display)
            creation_character_display_map[display] = character.id
        creation_character_combo["values"] = names
        if creation_character_var.get() not in creation_character_display_map:
            creation_character_var.set("")

    def _find_voice_id_by_name(name: str) -> str | None:
        if not name:
            return None
        match = next((v for v in context.project.voices.values() if v.name == name), None)
        return match.id if match else None

    def _resolve_speaker_hint(hint: str) -> tuple[str | None, str | None]:
        lowered = (hint or "").strip().lower()
        if not lowered:
            return None, None
        for character in context.project.characters.values():
            if character.name and character.name.lower() == lowered:
                voice_id = character.voice_ids[0] if character.voice_ids else None
                return voice_id, character.id
        for voice in context.project.voices.values():
            if voice.name and voice.name.lower() == lowered:
                return voice.id, None
        return None, None

    def _line_spec_from_fields(text: str, voice_id: str | None, character_id: str | None) -> dict:
        return {
            "text": text,
            "voice_id": voice_id,
            "character_id": character_id,
            "moodle": creation_moodle_var.get() or None,
            "effects": [effect.strip() for effect in creation_effects_var.get().split(",") if effect.strip()],
            "sound_file": creation_sound_var.get() or None,
        }

    def _collect_creation_line_specs() -> list[dict]:
        specs: list[dict] = []
        current_tab = creation_notebook.index("current")
        if current_tab == 0:
            text = creation_line_text_var.get().strip()
            if not text:
                return specs
            voice_id = _find_voice_id_by_name(creation_voice_var.get())
            character_display = creation_character_var.get()
            character_id = creation_character_display_map.get(character_display)
            specs.append(_line_spec_from_fields(text, voice_id, character_id))
            return specs
        for raw_line in creation_transcript_text.get("1.0", "end").splitlines():
            trimmed = raw_line.strip()
            if not trimmed:
                continue
            if ":" in trimmed:
                speaker, remainder = trimmed.split(":", 1)
                voice_hint, character_hint = _resolve_speaker_hint(speaker)
                line_text = remainder.strip()
            else:
                voice_hint, character_hint = (None, None)
                line_text = trimmed
            if not line_text:
                continue
            voice_id = voice_hint or _find_voice_id_by_name(creation_voice_var.get())
            character_id = character_hint or creation_character_display_map.get(creation_character_var.get())
            specs.append(_line_spec_from_fields(line_text, voice_id, character_id))
        return specs
    update_voice_combobox()

    ttk.Button(details_controls, text="Copy GUID", command=lambda: copy_guid(parent, context)).pack(side="left", padx=2)
    ttk.Button(details_controls, text="Apply broadcast", command=lambda: apply_broadcast(context, title_var, desc_text, refresh_broadcasts), style="Accent.TButton").pack(
        side="left", padx=4
    )
    ttk.Button(details_controls, text="Delete broadcast", command=lambda: _handle_delete_broadcast()).pack(side="right", padx=4)
    ttk.Button(details_controls, text="Add broadcast", command=lambda: _handle_create_broadcast()).pack(
        side="right", padx=4
    )
    ttk.Button(reorder_frame, text="Move up", command=lambda: _handle_reorder(-1)).grid(row=0, column=0, padx=2)
    ttk.Button(reorder_frame, text="Move down", command=lambda: _handle_reorder(1)).grid(row=0, column=1, padx=2)
    ttk.Button(details_controls, text="Delete broadcast", command=lambda: _handle_delete_broadcast()).pack(
        side="right", padx=4
    )

    transcript_panel = ttk.Frame(transcript_tab)
    transcript_panel.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
    transcript_panel.columnconfigure(0, weight=0)
    transcript_panel.columnconfigure(1, weight=1)
    transcript_panel.rowconfigure(0, weight=1)
    speaker_list = tk.Listbox(
        transcript_panel,
        width=26,
        background=SLATE_BG,
        foreground=LIGHT_TEXT,
        selectbackground=ACCENT_CYAN,
        selectforeground="#04060a",
        highlightthickness=0,
    )
    speaker_list.grid(row=0, column=0, sticky="ns")
    transcript_text = tk.Text(
        transcript_panel,
        wrap="word",
        background="#050916",
        foreground=LIGHT_TEXT,
        insertbackground=ACCENT_CYAN,
        relief="flat",
        height=12,
    )
    transcript_text.grid(row=0, column=1, sticky="nsew", padx=4, pady=2)
    transcript_tab.columnconfigure(0, weight=1)
    transcript_tab.rowconfigure(0, weight=1)
    button_frame = ttk.Frame(transcript_tab)
    button_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=4, pady=4)
    ttk.Button(
        button_frame,
        text="Refresh transcript",
        command=lambda: refresh_transcript(context, transcript_text, speaker_list),
    ).pack(side="left", padx=4)
    ttk.Button(
        button_frame,
        text="Apply transcript",
        command=lambda: apply_transcript(context, transcript_text, update_selection),
    ).pack(side="right", padx=4)
    reminder = ttk.Label(transcript_tab, text="Preview uses default voice until you set a voice on the Lines tab.", foreground="#8f94a6")
    reminder.grid(row=2, column=0, sticky="w", padx=4, pady=(0, 4))

    channel_ids: list[str] = []
    broadcast_items: list[tuple] = []

    def refresh_channels():
        channel_ids.clear()
        channels_list.delete(0, tk.END)
        ordered_ids = list(context.project.channels.keys())
        color_map = channel_color_map(ordered_ids)
        for channel_id in ordered_ids:
            channel = context.project.channels[channel_id]
            if not _is_radio_channel(channel):
                continue
            channel_ids.append(channel_id)
            channels_list.insert(tk.END, f"{channel.name} ({channel.frequency:.1f})")
            idx = channels_list.size() - 1
            channels_list.itemconfig(idx, fg=color_map.get(channel_id, LIGHT_TEXT))
        if not channel_ids:
            creation_status_var.set("Create a radio channel first.")
            return
        creation_status_var.set("")
        if context.active_channel_id not in channel_ids:
            context.active_channel_id = channel_ids[0]
        channels_list.selection_set(0)
        refresh_broadcasts()
        refresh_channel_combo()
        _update_channel_defaults()

    def _broadcast_matches_search(broadcast, snippet: str, entry, term: str) -> bool:
        if not term:
            return True
        haystack = " ".join(
            filter(
                None,
                [
                    broadcast.title or "",
                    snippet,
                    str(entry.day + 1),
                ],
            )
        )
        return term in haystack.lower()

    def refresh_broadcasts():
        nonlocal broadcast_items
        broadcast_items = []
        broadcast_tree.delete(*broadcast_tree.get_children())
        channel = context.project.channels.get(context.active_channel_id)
        if not channel:
            update_selection()
            return
        entries = sorted(channel.schedule, key=lambda entry: (entry.day, entry.start))
        voice_tag_map = {}
        search_term = (broadcast_search_var.get() or "").strip().lower()
        for entry in entries:
            broadcast = context.project.broadcasts.get(entry.broadcast_id)
            if not broadcast:
                continue
            first_line = broadcast.lines[0] if broadcast.lines else None
            snippet = (
                first_line.text.splitlines()[0].strip()
                if first_line and first_line.text
                else "(no lines yet)"
            )
            snippet = snippet[:60]
            if not _broadcast_matches_search(broadcast, snippet, entry, search_term):
                continue
            broadcast_items.append((entry, broadcast))
            start_label = format_time(entry.start)
            end_label = format_time(entry.end)
            values = (
                f"Day {entry.day + 1}",
                start_label,
                end_label,
                snippet,
                str(len(broadcast.lines)),
            )
            tags = ["day-bold"]
            broadcast_tree.insert("", "end", iid=broadcast.id, values=values, tags=tags)
            if first_line and first_line.voice_id:
                voice = context.project.voices.get(first_line.voice_id)
                if voice and voice.color:
                    color = voice.color
                    tag_name = f"voice-{first_line.voice_id}"
                    if tag_name not in voice_tag_map:
                        broadcast_tree.tag_configure(tag_name, foreground=color)
                        voice_tag_map[tag_name] = True
                    tags.append(tag_name)
                    broadcast_tree.item(broadcast.id, tags=tuple(tags))
        update_selection()

    def update_selection():
        active = context.active_broadcast
        lines_list.delete(0, tk.END)
        if not active:
            title_var.set("")
            desc_text.delete("1.0", "end")
            meta_var.set("")
            fallback_var.set("")
            info_var.set("No broadcast selected.")
            line_info_var.set("Select a line to inspect metadata.")
            refresh_transcript(context, transcript_text, speaker_list)
            return
        if not active.title and active.lines:
            active.title = active.lines[0].text
        channel = context.project.channels.get(context.active_channel_id)
        channel_name = channel.name if channel else "Channel"
        fallback_str = fallback_title(active, channel_name)
        fallback_var.set(f"Auto title: {fallback_str}" if not active.title else "")
        title_var.set(active.title)
        desc_text.delete("1.0", "end")
        desc_text.insert("1.0", active.description)
        lines_count = len(active.lines)
        voices_used = {line.voice_id for line in active.lines if line.voice_id}
        start = int(active.start_offset)
        end = int(active.end_offset if active.end_offset is not None else active.start_offset)
        meta_parts = [
            f"{lines_count} lines",
            f"Day {active.day + 1}",
            f"{start}-{end}s",
            f"{len(voices_used)} voices",
            f"Effects {', '.join(active.effects) or 'none'}",
            f"Adverts {len(active.adverts)}",
        ]
        meta_var.set(" · ".join(meta_parts))
        info_var.set(f"Broadcast GUID {active.id}")
        line_info_var.set("Select a line to inspect metadata.")
        schedule_day_var.set(active.day)
        schedule_start_label_var.set(_seconds_to_hhmm(active.start_offset))
        schedule_duration_var.set(DURATIONS[min(len(DURATIONS)-1, max(0, int((active.end_offset or active.start_offset - active.start_offset)/1800)))])
        for idx, line in enumerate(active.lines):
            voice = context.project.voices.get(line.voice_id)
            character = context.project.characters.get(line.character_id)
            speaker_name = character.name if character else (voice.name if voice else "Unknown")
            display = f"{idx + 1:02d}. {speaker_name}: {line.text}"
            lines_list.insert(tk.END, display)
            if voice and voice.color:
                lines_list.itemconfig(idx, fg=voice.color)
        update_character_combobox()
        refresh_transcript(context, transcript_text, speaker_list)

    def on_channel_select(_=None):
        selection = channels_list.curselection()
        if not selection:
            return
        idx = selection[0]
        if idx >= len(channel_ids):
            return
        context.active_channel_id = channel_ids[idx]
        refresh_broadcasts()

    def on_broadcast_select(_=None):
        selection = broadcast_tree.selection()
        if not selection:
            return
        bid = selection[0]
        context.select_broadcast(bid)
        update_selection()

    def _handle_add_line():
        active = context.active_broadcast
        if not active:
            return
            project_ops.add_line_to_broadcast(
                context,
                active.id,
                line_text_var.get(),
                voice_id=preferred_voice_id,
                character_id=preferred_character_id,
                moodle=line_moodle_var.get() or None,
            effects=[effect.strip() for effect in line_effects_var.get().split(",") if effect.strip()],
            sound_file=line_sound_var.get() or None,
            notify=True,
        )
        update_selection()
        _restore_line_selection(len(active.lines) - 1)
        line_text_var.set("")
        line_moodle_var.set("")
        line_effects_var.set("")
        line_sound_var.set("")

    def update_line(
        context,
        lines_list,
        line_text_var,
        line_voice_var,
        line_character_var,
        line_moodle_var,
        line_effects_var,
        line_sound_var,
    ):
        active = context.active_broadcast
        if not active:
            return
        selection = lines_list.curselection()
        if not selection:
            return
        idx = selection[0]
        if idx >= len(active.lines):
            return
        nonlocal preferred_voice_id
        nonlocal preferred_character_id
        line = active.lines[idx]
        line.text = line_text_var.get()
        voice_name = line_voice_var.get()
        voice = next((v for v in context.project.voices.values() if v.name == voice_name), None)
        line.voice_id = voice.id if voice else None
        preferred_voice_id = voice.id if voice else preferred_voice_id
        character_display = line_character_var.get()
        character_id = line_character_display_map.get(character_display)
        line.character_id = character_id
        preferred_character_id = character_id if character_id else preferred_character_id
        line.moodle = line_moodle_var.get()
        effects = [effect.strip() for effect in line_effects_var.get().split(",") if effect.strip()]
        line.effects = effects
        line.sound_file = line_sound_var.get() or None
        update_selection()
        _restore_line_selection(idx)

    def delete_line(context, lines_list):
        active = context.active_broadcast
        if not active:
            return
        selection = lines_list.curselection()
        if not selection:
            return
        idx = selection[0]
        if idx < len(active.lines):
            active.lines.pop(idx)
            update_selection()
            _restore_line_selection(min(idx, max(0, lines_list.size() - 1)))

    def _handle_reschedule():
        active = context.active_broadcast
        channel_id = context.active_channel_id
        if not active or not channel_id:
            return
        try:
            start_seconds = float(active.start_offset or 0.0)
            duration = _hhmm_to_seconds(schedule_duration_var.get())
            entry = project_ops.reschedule_broadcast(
                context,
                channel_id,
                active.id,
                day=int(schedule_day_var.get() or 0),
                start=start_seconds,
                end=start_seconds + duration,
                notify=False,
            )
        except ValueError:
            return
        refresh_broadcasts()
        context.select_broadcast(active.id)
        update_selection()
        _update_channel_defaults()

    def _handle_reorder(direction: int):
        active = context.active_broadcast
        channel = context.project.channels.get(context.active_channel_id)
        if not active or not channel:
            return
        schedule = channel.schedule
        idx = next((i for i, entry in enumerate(schedule) if entry.broadcast_id == active.id), None)
        if idx is None:
            return
        target = idx + direction
        if not (0 <= target < len(schedule)):
            return
        entry = schedule[idx]
        target_entry = schedule[target]
        entry_day, entry_start, entry_end = entry.day, entry.start, entry.end
        target_day, target_start, target_end = target_entry.day, target_entry.start, target_entry.end
        entry.day, entry.start, entry.end = target_day, target_start, target_end
        target_entry.day, target_entry.start, target_entry.end = entry_day, entry_start, entry_end
        schedule[idx], schedule[target] = schedule[target], schedule[idx]

        def _apply_schedule_timing(schedule_entry):
            broadcast = context.project.broadcasts.get(schedule_entry.broadcast_id)
            if not broadcast:
                return
            broadcast.day = schedule_entry.day
            broadcast.start_offset = schedule_entry.start
            broadcast.end_offset = schedule_entry.end

        _apply_schedule_timing(entry)
        _apply_schedule_timing(target_entry)
        refresh_broadcasts()
        broadcast_tree.selection_set(active.id)
        context.select_broadcast(active.id)
        update_selection()

    def _handle_delete_broadcast():
        active = context.active_broadcast
        channel_id = context.active_channel_id
        if not active or not channel_id:
            return
        channel = context.project.channels.get(channel_id)
        if channel:
            channel.schedule = [
                entry for entry in channel.schedule if entry.broadcast_id != active.id
            ]
        if active.id in context.project.broadcasts:
            del context.project.broadcasts[active.id]
        creation_status_var.set(f"Broadcast {active.id} deleted.")
        remaining = next(iter(context.project.broadcasts), None)
        if remaining:
            context.select_broadcast(remaining)
        else:
            context.active_broadcast_id = None
        refresh_broadcasts()
        update_selection()

    def _handle_delete_broadcast():
        active = context.active_broadcast
        if not active:
            return
        for channel in context.project.channels.values():
            channel.schedule = [entry for entry in channel.schedule if entry.broadcast_id != active.id]
        context.project.broadcasts.pop(active.id, None)
        context.active_broadcast_id = None
        refresh_broadcasts()
        update_selection()

    def _reset_creation_fields():
        new_title_var.set("")
        new_desc_var.set("")
        new_day_var.set(0)
        start_label_var.set(START_TIMES[0])
        new_duration_var.set(DURATIONS[0])
        creation_line_text_var.set("")
        creation_voice_var.set("")
        creation_character_var.set("")
        creation_moodle_var.set("")
        creation_effects_var.set("")
        creation_sound_var.set("")
        creation_transcript_text.delete("1.0", "end")

    def _compute_next_timing(channel_id: str, skip_broadcast: str | None = None) -> tuple[int, float]:
        channel = context.project.channels.get(channel_id)
        if not channel:
            return 0, 0.0
        max_offset = 0
        for entry in channel.schedule:
            if entry.broadcast_id == skip_broadcast:
                continue
            offset = entry.day * 24 * 3600 + entry.end
            if offset > max_offset:
                max_offset = offset
        return divmod(max_offset, 24 * 3600)

    def _update_channel_defaults():
        idx = channel_combo.current()
        if idx < 0 or idx >= len(channel_ids):
            return
        cid = channel_ids[idx]
        day, start_seconds = _compute_next_timing(cid)
        new_day_var.set(int(day))
        start_label_var.set(_seconds_to_hhmm(start_seconds))

    def _handle_create_broadcast():
        if not channel_ids:
            return
        idx = channel_combo.current()
        if idx < 0 or idx >= len(channel_ids):
            idx = 0
            channel_combo.current(idx)
        channel_id = channel_ids[idx]
        title = new_title_var.get().strip() or "New Broadcast"
        description = new_desc_var.get().strip()
        start_seconds = _hhmm_to_seconds(start_label_var.get())
        duration_seconds = _hhmm_to_seconds(new_duration_var.get())
        end_seconds = start_seconds + duration_seconds
        try:
            broadcast, _ = project_ops.create_broadcast(
                context,
                title,
                description,
                channel_id=channel_id,
                day=int(new_day_var.get() or 0),
                start=start_seconds,
                end=end_seconds,
                notify=False,
            )
        except ValueError:
            creation_status_var.set("Failed to create broadcast.")
            return
        specs = _collect_creation_line_specs()
        for spec in specs:
            project_ops.add_line_to_broadcast(
                context,
                broadcast.id,
                spec["text"],
                voice_id=spec["voice_id"],
                character_id=spec["character_id"],
                moodle=spec["moodle"],
                effects=spec["effects"],
                sound_file=spec["sound_file"],
                notify=False,
            )
        refresh_broadcasts()
        context.select_broadcast(broadcast.id)
        update_selection()
        _reset_creation_fields()
        _update_channel_defaults()
        creation_status_var.set(f"Broadcast {broadcast.id} created.")

    def copy_line_guid(lines_list, parent, context):
        active = context.active_broadcast
        if not active:
            return
        selection = lines_list.curselection()
        if not selection:
            return
        idx = selection[0]
        if idx >= len(active.lines):
            return
        guid = active.lines[idx].guid
        root = parent.winfo_toplevel()
        root.clipboard_clear()
        root.clipboard_append(guid)

    def refresh_transcript(context, transcript_text, speaker_list):
        active = context.active_broadcast
        transcript_text.configure(state="normal")
        transcript_text.delete("1.0", tk.END)
        speaker_list.delete(0, tk.END)
        if not active:
            transcript_text.insert("1.0", "No broadcast selected.")
            return
        for line in active.lines:
            voice = context.project.voices.get(line.voice_id)
            character = context.project.characters.get(line.character_id)
            speaker = character.name if character else (voice.name if voice else "Unknown")
            speaker_list.insert(tk.END, speaker)
            transcript_text.insert("end", f"{line.text}\n")

    def apply_transcript(context, transcript_text, update_callback):
        active = context.active_broadcast
        if not active:
            return
        content = transcript_text.get("1.0", "end").splitlines()
        new_lines = []
        voice = (
            context.project.voices.get(preferred_voice_id) if preferred_voice_id else None
        )
        for raw in content:
            line_text = raw.strip()
            if not line_text:
                continue
            trimmed = line_text[:180]
            new_lines.append(
                Line(
                    text=trimmed,
                    voice_id=voice.id if voice else None,
                )
            )
        active.lines = new_lines
        update_callback()

    def apply_broadcast(context, title_var, desc_widget, refresh_func):
        active = context.active_broadcast
        if not active:
            return
        active.title = title_var.get().strip() or active.title
        desc_value = desc_widget.get("1.0", "end").strip()
        active.description = desc_value
        refresh_func()

    def add_broadcast(context, title_var, desc_widget, refresh_func):
        desc_value = desc_widget.get("1.0", "end").strip()
        context.add_broadcast(title_var.get() or "New Broadcast", desc_value)
        refresh_func()

    def copy_guid(parent, context):
        active = context.active_broadcast
        if not active:
            return
        root = parent.winfo_toplevel()
        root.clipboard_clear()
        root.clipboard_append(active.id)

    channels_list.bind("<<ListboxSelect>>", on_channel_select)
    def _on_broadcast_context(event):
        item = broadcast_tree.identify_row(event.y)
        if not item:
            return
        broadcast_tree.selection_set(item)
        menu = tk.Menu(broadcast_tree, tearoff=0)
        menu.add_command(label="Move up", command=lambda: _handle_reorder(-1))
        menu.add_command(label="Move down", command=lambda: _handle_reorder(1))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    broadcast_tree.bind("<<TreeviewSelect>>", on_broadcast_select)
    broadcast_tree.bind("<Button-3>", _on_broadcast_context)
    lines_list.bind(
        "<<ListboxSelect>>",
        lambda event: load_line_selection(
            context,
            lines_list,
            line_text_var,
            line_voice_var,
            line_character_var,
            line_moodle_var,
            line_effects_var,
            line_sound_var,
        ),
    )

    refresh_channels()
    context.register_refresh_callback(refresh_channels)
    context.register_refresh_callback(update_voice_combobox)
    context.register_refresh_callback(update_character_combobox)
    context.register_refresh_callback(_update_creation_voice_combo)
    context.register_refresh_callback(_update_creation_character_combo)
    broadcast_search_var.trace_add("write", lambda *_: refresh_broadcasts())

    def load_line_selection(
        context,
        lines_list,
        text_var,
        voice_var,
        character_var,
        moodle_var,
        effects_var,
        sound_var,
    ):
        active = context.active_broadcast
        if not active:
            return
        selection = lines_list.curselection()
        if not selection:
            return
        idx = selection[0]
        if idx >= len(active.lines):
            return
        line = active.lines[idx]
        text_var.set(line.text)
        voice = context.project.voices.get(line.voice_id)
        voice_var.set(voice.name if voice else "")
        character = context.project.characters.get(line.character_id)
        character_var.set(_character_display(character) if character else "")
        moodle_var.set(line.moodle or "")
        effects_var.set(", ".join(line.effects))
        sound_var.set(line.sound_file or "")
        line_info_var.set(f"Line GUID {line.guid}")

    def _restore_line_selection(index: int):
        lines_list.selection_clear(0, tk.END)
        if 0 <= index < lines_list.size():
            lines_list.selection_set(index)
        load_line_selection(
            context,
            lines_list,
            line_text_var,
            line_voice_var,
            line_character_var,
            line_moodle_var,
            line_effects_var,
            line_sound_var,
        )

    tips_label = ttk.Label(
        frame,
        text="Tips: select multiple lines, right-click to add voices/effects, drag broadcasts using context menu",
        foreground="#8f94a6",
    )
    tips_label.grid(row=2, column=0, columnspan=3, sticky="e", padx=12, pady=4)

    return frame
