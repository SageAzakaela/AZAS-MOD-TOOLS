import tkinter as tk
from tkinter import ttk, simpledialog

from typing import Callable

from ...config import settings
from ...core import AppContext, Line, project_ops
from ..styles import ACCENT_CYAN, LIGHT_TEXT, SLATE_BG
from .utils import channel_color_map, fallback_title, format_time


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


def _is_tv_channel(channel) -> bool:
    category = (channel.category or "").lower()
    return "tv" in category or "television" in category


def make_tab(parent, context: AppContext):
    frame = ttk.Frame(parent)
    frame.configure(style="TFrame")
    frame.columnconfigure(0, weight=0)
    frame.columnconfigure(1, weight=1)
    frame.columnconfigure(2, weight=2)
    frame.rowconfigure(0, weight=1)

    channel_frame = ttk.LabelFrame(frame, text="TV Channels")
    channel_frame.grid(row=0, column=0, sticky="ns", padx=12, pady=12)
    channel_frame.columnconfigure(0, weight=1)
    channel_frame.rowconfigure(0, weight=1)
    channels_list = tk.Listbox(
        channel_frame,
        width=32,
        exportselection=False,
        activestyle="none",
        background=SLATE_BG,
        font=("Segoe UI Bold", 16),
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
    broadcast_frame.rowconfigure(0, weight=1)
    columns = ("day", "start", "end", "first_line", "lines")
    broadcast_tree = ttk.Treeview(
        broadcast_frame, columns=columns, show="headings", selectmode="browse", height=20
    )
    widths = {"day": 70, "start": 70, "end": 70, "first_line": 320, "lines": 80}
    for col, heading in zip(columns, ("Day", "Start", "End", "First line", "Scenes")):
        broadcast_tree.heading(col, text=heading)
        broadcast_tree.column(col, anchor="w", stretch=(col == "first_line"), width=widths.get(col, 120))
    broadcast_tree.grid(row=0, column=0, sticky="nsew")
    broadcast_scroll = ttk.Scrollbar(broadcast_frame, orient="vertical", command=broadcast_tree.yview)
    broadcast_tree.configure(yscrollcommand=broadcast_scroll.set)
    broadcast_scroll.grid(row=0, column=1, sticky="ns")

    creation_frame = ttk.LabelFrame(frame, text="Create broadcast")
    creation_frame.grid(row=1, column=1, sticky="ew", padx=12, pady=(0, 12))
    creation_frame.columnconfigure(1, weight=1)
    new_title_var = tk.StringVar()
    new_desc_var = tk.StringVar()
    new_day_var = tk.IntVar(value=0)
    start_label_var = tk.StringVar(value="00:00")
    new_duration_var = tk.StringVar(value=DURATIONS[0])
    channel_combo = ttk.Combobox(creation_frame, state="readonly")
    creation_status_var = tk.StringVar(value="")

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
    ttk.Button(
        creation_frame,
        text="Create broadcast",
        style="Accent.TButton",
        command=lambda: _handle_create_broadcast(),
    ).grid(row=6, column=0, columnspan=2, pady=4)
    ttk.Label(creation_frame, textvariable=creation_status_var, foreground="#f4d6a2").grid(
        row=7, column=0, columnspan=2, sticky="w", padx=4, pady=(2, 0)
    )
    channel_combo.bind("<<ComboboxSelected>>", lambda _: _update_channel_defaults())

    detail_frame = ttk.LabelFrame(frame, text="Broadcast details")
    detail_frame.grid(row=0, column=2, sticky="nsew", padx=12, pady=12)
    detail_frame.columnconfigure(0, weight=1)
    detail_frame.rowconfigure(0, weight=0)
    detail_frame.rowconfigure(1, weight=1)

    detail_panel = ttk.Frame(detail_frame)
    detail_panel.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
    detail_panel.columnconfigure(1, weight=1)
    title_var = tk.StringVar()
    description_var = tk.StringVar()
    line_info_var = tk.StringVar(value="Select a scene to inspect metadata.")
    meta_var = tk.StringVar()
    fallback_var = tk.StringVar()
    info_var = tk.StringVar(value="Select a broadcast to preview TV overlays.")

    ttk.Label(detail_panel, text="Title").grid(row=0, column=0, sticky="w", pady=2)
    ttk.Entry(detail_panel, textvariable=title_var).grid(row=0, column=1, sticky="ew", pady=2)
    ttk.Label(detail_panel, text="Description").grid(row=1, column=0, sticky="w", pady=2)
    ttk.Entry(detail_panel, textvariable=description_var).grid(row=1, column=1, sticky="ew", pady=2)
    fallback_label = ttk.Label(detail_panel, textvariable=fallback_var, foreground="#7fc1ff")
    fallback_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=2)
    meta_label = ttk.Label(detail_panel, textvariable=meta_var, foreground="#8f94a6")
    meta_label.grid(row=4, column=0, columnspan=2, sticky="w", pady=2)
    ttk.Label(detail_panel, text="Scene info").grid(row=5, column=0, sticky="w", pady=2)
    line_info_label = ttk.Label(detail_panel, textvariable=line_info_var, foreground="#c0c6e8")
    line_info_label.grid(row=5, column=1, sticky="w", pady=2)
    info_label = ttk.Label(detail_panel, textvariable=info_var, foreground="#8f94a6")
    info_label.grid(row=6, column=0, columnspan=2, sticky="w", pady=2)
    copy_guid_button = ttk.Button(detail_panel, text="Copy GUID", command=lambda: copy_guid(parent, context))
    copy_guid_button.grid(row=4, column=2, rowspan=2, sticky="e", padx=4)
    details_controls = ttk.Frame(detail_panel)
    details_controls.grid(row=7, column=0, columnspan=2, pady=8)
    ttk.Button(details_controls, text="Copy GUID", command=lambda: copy_guid(parent, context)).pack(side="left", padx=2)
    ttk.Button(details_controls, text="Apply broadcast", command=lambda: apply_broadcast(context, title_var, description_var, refresh_broadcasts), style="Accent.TButton").pack(
        side="left", padx=4
    )
    ttk.Button(details_controls, text="Delete broadcast", command=lambda: _handle_delete_broadcast()).pack(side="right", padx=4)
    ttk.Button(details_controls, text="Add broadcast", command=lambda: add_broadcast(context, title_var, description_var, refresh_broadcasts)).pack(
        side="right", padx=4
    )
    reorder_frame = ttk.Frame(detail_panel)
    reorder_frame.grid(row=7, column=2, sticky="e", pady=8, padx=4)
    ttk.Button(reorder_frame, text="Move up", command=lambda: _handle_reorder(-1)).grid(row=0, column=0, padx=2)
    ttk.Button(reorder_frame, text="Move down", command=lambda: _handle_reorder(1)).grid(row=0, column=1, padx=2)
    schedule_frame = ttk.LabelFrame(detail_panel, text="Reschedule broadcast")
    schedule_frame.grid(row=8, column=0, columnspan=2, sticky="ew", pady=4)
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
    detail_notebook.add(lines_tab, text="Scenes")
    detail_notebook.add(transcript_tab, text="Transcript")

    # Scenes tab widgets
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
    )
    lines_list.grid(row=0, column=0, sticky="nsew")
    lines_scroll = ttk.Scrollbar(lines_tab, orient="vertical", command=lines_list.yview)
    lines_list.configure(yscrollcommand=lines_scroll.set)
    lines_scroll.grid(row=0, column=1, sticky="ns")

    preferred_voice_id: str | None = None

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
        context_menu.add_command(label="Add effect", command=_add_effect_to_selection)
        context_menu.add_command(label="Remove effects", command=_remove_effects_from_selection)

        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    lines_list.bind("<Button-3>", _build_line_context_menu)

    line_editor = ttk.LabelFrame(lines_tab, text="Scene editor")
    line_editor.grid(row=1, column=0, columnspan=2, sticky="ew", pady=4)
    line_editor.columnconfigure(1, weight=1)
    line_text_var = tk.StringVar()
    line_voice_var = tk.StringVar()
    line_moodle_var = tk.StringVar()
    line_effects_var = tk.StringVar()
    line_sound_var = tk.StringVar()

    ttk.Label(line_editor, text="Text").grid(row=0, column=0, sticky="w", padx=4, pady=2)
    ttk.Entry(line_editor, textvariable=line_text_var).grid(row=0, column=1, sticky="ew", padx=4, pady=2)
    ttk.Label(line_editor, text="Voice").grid(row=1, column=0, sticky="w", padx=4, pady=2)
    voice_combo = ttk.Combobox(line_editor, textvariable=line_voice_var, state="readonly")
    voice_combo.grid(row=1, column=1, sticky="ew", padx=4, pady=2)
    ttk.Label(line_editor, text="Moodle").grid(row=2, column=0, sticky="w", padx=4, pady=2)
    ttk.Entry(line_editor, textvariable=line_moodle_var).grid(row=2, column=1, sticky="ew", padx=4, pady=2)
    ttk.Label(line_editor, text="Effects").grid(row=3, column=0, sticky="w", padx=4, pady=2)
    ttk.Entry(line_editor, textvariable=line_effects_var).grid(row=3, column=1, sticky="ew", padx=4, pady=2)
    ttk.Label(line_editor, text="Sound file").grid(row=4, column=0, sticky="w", padx=4, pady=2)
    ttk.Entry(line_editor, textvariable=line_sound_var).grid(row=4, column=1, sticky="ew", padx=4, pady=2)

    line_button_frame = ttk.Frame(line_editor)
    line_button_frame.grid(row=5, column=0, columnspan=2, pady=6)
    ttk.Button(
        line_button_frame,
        text="Update scene",
        command=lambda: update_line(
            context,
            lines_list,
            line_text_var,
            line_voice_var,
            line_moodle_var,
            line_effects_var,
            line_sound_var,
        ),
    ).pack(side="left", padx=4)
    ttk.Button(line_button_frame, text="Copy GUID", command=lambda: copy_line_guid(lines_list, parent, context)).pack(
        side="left", padx=4
    )
    ttk.Button(line_button_frame, text="Delete scene", command=lambda: delete_line(context, lines_list)).pack(side="left", padx=4)
    ttk.Button(line_button_frame, text="Add scene", command=lambda: _handle_add_line(), style="Accent.TButton").pack(side="left", padx=4)
    lines_list.bind("<<ListboxSelect>>", lambda event: load_line_selection(
        context,
        lines_list,
        line_text_var,
        line_voice_var,
        line_moodle_var,
        line_effects_var,
        line_sound_var,
    ))

    def _contrast_color(hex_color: str) -> str:
        hex_color = (hex_color or "#000000").lstrip("#")
        if len(hex_color) != 6:
            return "#000000"
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        return "#000000" if brightness > 186 else "#ffffff"

    ttk.Button(details_controls, text="Apply broadcast", command=lambda: apply_broadcast(context, title_var, description_var, refresh_broadcasts), style="Accent.TButton").pack(
        side="left", padx=4
    )
    ttk.Button(details_controls, text="Add broadcast", command=lambda: add_broadcast(context, title_var, description_var, refresh_broadcasts)).pack(
        side="right", padx=4
    )

    transcript_panel = ttk.Frame(transcript_tab)
    transcript_panel.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
    transcript_panel.columnconfigure(0, weight=0)
    transcript_panel.columnconfigure(1, weight=1)
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
        height=10,
    )
    transcript_text.grid(row=0, column=1, sticky="nsew", padx=4, pady=2)
    transcript_tab.columnconfigure(0, weight=1)
    transcript_tab.rowconfigure(0, weight=1)
    button_frame = ttk.Frame(transcript_tab)
    button_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=4, pady=4)
    ttk.Button(button_frame, text="Refresh transcript", command=lambda: refresh_transcript(context, transcript_text, speaker_list)).pack(side="left", padx=4)
    ttk.Button(button_frame, text="Apply transcript", command=lambda: apply_transcript(context, transcript_text, speaker_list, update_selection)).pack(side="right", padx=4)

    channel_ids: list[str] = []
    broadcast_items: list[tuple] = []

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

    def refresh_channels():
        channel_ids.clear()
        channels_list.delete(0, tk.END)
        ordered_ids = list(context.project.channels.keys())
        color_map = channel_color_map(ordered_ids)
        for channel_id in ordered_ids:
            channel = context.project.channels[channel_id]
            if not _is_tv_channel(channel):
                continue
            channel_ids.append(channel_id)
            channels_list.insert(tk.END, f"{channel.name} ({channel.frequency:.1f})")
            idx = channels_list.size() - 1
            channels_list.itemconfig(idx, fg=color_map.get(channel_id, LIGHT_TEXT))
        if not channel_ids:
            creation_status_var.set("Create a TV channel first.")
            refresh_channel_combo()
            return
        creation_status_var.set("")
        refresh_channel_combo()
        if context.active_channel_id not in channel_ids:
            context.active_channel_id = channel_ids[0]
        channels_list.selection_set(0)
        refresh_broadcasts()
        _update_channel_defaults()

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
        for entry in entries:
            broadcast = context.project.broadcasts.get(entry.broadcast_id)
            if not broadcast:
                continue
            broadcast_items.append((entry, broadcast))
            first_line = broadcast.lines[0] if broadcast.lines else None
            snippet = (
                first_line.text.splitlines()[0].strip()
                if first_line and first_line.text
                else "(no lines yet)"
            )
            snippet = snippet[:60]
            start_label = format_time(entry.start)
            end_label = format_time(entry.end)
            values = (
                f"Day {entry.day + 1}",
                start_label,
                end_label,
                snippet,
                str(len(broadcast.lines)),
            )
            broadcast_tree.insert("", "end", iid=broadcast.id, values=values)
            if first_line and first_line.voice_id:
                voice = context.project.voices.get(first_line.voice_id)
                if voice and voice.color:
                    color = voice.color
                    tag_name = f"voice-{first_line.voice_id}"
                    if tag_name not in voice_tag_map:
                        broadcast_tree.tag_configure(tag_name, foreground=color)
                        voice_tag_map[tag_name] = True
                    broadcast_tree.item(broadcast.id, tags=(tag_name,))
        if broadcast_items:
            context.select_broadcast(broadcast_items[0][1].id)
        update_selection()

    def update_selection():
        active = context.active_broadcast
        lines_list.delete(0, tk.END)
        if not active:
            title_var.set("")
            description_var.set("")
            meta_var.set("")
            fallback_var.set("")
            info_var.set("No broadcast selected.")
            line_info_var.set("Select a scene to inspect metadata.")
            # update_transcript()
            return
        if not active.title and active.lines:
            active.title = active.lines[0].text
        channel = context.project.channels.get(context.active_channel_id)
        channel_name = channel.name if channel else "Channel"
        fallback_str = fallback_title(active, channel_name)
        fallback_var.set(f"Auto title: {fallback_str}" if not active.title else "")
        title_var.set(active.title)
        description_var.set(active.description)
        lines_count = len(active.lines)
        voices_used = {line.voice_id for line in active.lines if line.voice_id}
        start = int(active.start_offset)
        end = int(active.end_offset if active.end_offset is not None else active.start_offset)
        meta_parts = [
            f"{lines_count} scenes",
            f"Day {active.day + 1}",
            f"{start}-{end}s",
            f"{len(voices_used)} voices",
            f"Effects {', '.join(active.effects) or 'none'}",
            f"Adverts {len(active.adverts)}",
        ]
        meta_var.set(" · ".join(meta_parts))
        info_var.set(f"Broadcast GUID {active.id}")
        line_info_var.set("Select a scene to inspect metadata.")
        schedule_day_var.set(active.day)
        schedule_start_label_var.set(_seconds_to_hhmm(active.start_offset))
        schedule_duration_var.set(DURATIONS[min(len(DURATIONS)-1, max(0, int((active.end_offset or active.start_offset - active.start_offset)/1800)))])
        for idx, line in enumerate(active.lines):
            voice = context.project.voices.get(line.voice_id)
            name = voice.name if voice else "Unknown"
            display = f"{idx + 1:02d}. {name}: {line.text}"
            lines_list.insert(tk.END, display)
            if voice and voice.color:
                lines_list.itemconfig(idx, fg=voice.color)
        update_voice_combobox()
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

    def update_voice_combobox():
        names = [voice.name for voice in context.project.voices.values()]
        voice_combo["values"] = names

    update_voice_combobox()

    def _handle_add_line():
        active = context.active_broadcast
        if not active:
            return
        project_ops.add_line_to_broadcast(
            context,
            active.id,
            line_text_var.get(),
            voice_id=preferred_voice_id,
            moodle=line_moodle_var.get() or None,
            effects=[effect.strip() for effect in line_effects_var.get().split(",") if effect.strip()],
            sound_file=line_sound_var.get() or None,
            notify=True,
        )
        update_selection()
        # _restore_line_selection(len(active.lines) - 1)
        line_text_var.set("")
        line_moodle_var.set("")
        line_effects_var.set("")
        line_sound_var.set("")

    def update_line(
        context,
        lines_list,
        line_text_var,
        line_voice_var,
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
        line = active.lines[idx]
        nonlocal preferred_voice_id
        line.text = line_text_var.get()
        voice_name = line_voice_var.get()
        voice = next((v for v in context.project.voices.values() if v.name == voice_name), None)
        line.voice_id = voice.id if voice else None
        preferred_voice_id = voice.id if voice else preferred_voice_id
        line.moodle = line_moodle_var.get()
        effects = [effect.strip() for effect in line_effects_var.get().split(",") if effect.strip()]
        line.effects = effects
        line.sound_file = line_sound_var.get() or None
        update_selection()

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

    def _reset_creation_fields():
        new_title_var.set("")
        new_desc_var.set("")
        new_day_var.set(0)
        start_label_var.set(START_TIMES[0])
        new_duration_var.set(DURATIONS[0])

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
            creation_status_var.set("Create a TV channel first.")
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
            transcript_text.configure(state="disabled")
            return
        for line in active.lines:
            voice = context.project.voices.get(line.voice_id)
            speaker = voice.name if voice else "Unknown"
            speaker_list.insert(tk.END, speaker)
            transcript_text.insert("end", f"{line.text}\n")

    def apply_transcript(context, transcript_text, speaker_list, update_callback):
        active = context.active_broadcast
        if not active:
            return
        content = transcript_text.get("1.0", "end").strip().splitlines()
        if not content:
            return
        new_lines = []
        for raw in content:
            line_text = raw.strip()
            if not line_text:
                continue
            trimmed = line_text[: settings.transcript_line_limit]
            new_lines.append(Line(text=trimmed))
        active.lines = new_lines
        update_callback()

    def apply_broadcast(context, title_var, description_var, refresh_func):
        active = context.active_broadcast
        if not active:
            return
        active.title = title_var.get().strip() or active.title
        active.description = description_var.get()
        refresh_func()

    def add_broadcast(context, title_var, description_var, refresh_func):
        context.add_broadcast(title_var.get() or "New Broadcast", description_var.get())
        refresh_func()

    def copy_guid(parent, context):
        active = context.active_broadcast
        if not active:
            return
        root = parent.winfo_toplevel()
        root.clipboard_clear()
        root.clipboard_append(active.id)

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

    def load_line_selection(
        context,
        lines_list,
        text_var,
        voice_var,
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
        moodle_var.set(line.moodle or "")
        effects_var.set(", ".join(line.effects))
        sound_var.set(line.sound_file or "")
        line_info_var.set(f"Scene GUID {line.guid}")

    channels_list.bind("<<ListboxSelect>>", on_channel_select)
    broadcast_tree.bind("<<TreeviewSelect>>", on_broadcast_select)
    broadcast_tree.bind("<Button-3>", _on_broadcast_context)
    refresh_channels()
    context.register_refresh_callback(refresh_channels)
    context.register_refresh_callback(update_voice_combobox)

    return frame
