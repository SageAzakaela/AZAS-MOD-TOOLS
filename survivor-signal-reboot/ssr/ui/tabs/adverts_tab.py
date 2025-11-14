import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Callable
from uuid import uuid4

from ...core import AppContext, Line, project_ops
from ...core.models import AdvertBroadcast, AdvertScript
from ..styles import ACCENT_CYAN, LIGHT_TEXT, SLATE_BG, SECONDARY_TEXT
from .utils import lines_as_text


def format_meta(advert: AdvertScript) -> str:
    return (
        f"ID {advert.id} · loop {advert.loopmin}-{advert.loopmax} · "
        f"{advert.timestampmode} · {len(advert.broadcasts)} broadcast(s)"
    )


def _unique_advert_id() -> str:
    return f"advert-{uuid4().hex[:8]}"


def _unique_broadcast_id() -> str:
    return f"advert-bcast-{uuid4().hex[:8]}"


def _contrast_color(hex_color: str) -> str:
    hex_color = (hex_color or "#000000").lstrip("#")
    if len(hex_color) != 6:
        return "#000000"
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    return "#000000" if brightness > 186 else "#ffffff"


def make_tab(parent, context: AppContext):
    frame = ttk.Frame(parent)
    frame.configure(style="TFrame")
    frame.columnconfigure(0, weight=0)
    frame.columnconfigure(1, weight=1)
    frame.rowconfigure(0, weight=1)
    frame.rowconfigure(1, weight=0)

    left = ttk.LabelFrame(frame, text="Advert groups")
    left.grid(row=0, column=0, sticky="ns", padx=12, pady=12)
    left.columnconfigure(0, weight=1)
    left.rowconfigure(0, weight=1)
    advert_list = tk.Listbox(
        left,
        width=24,
        background=SLATE_BG,
        foreground=LIGHT_TEXT,
        selectbackground=ACCENT_CYAN,
        activestyle="none",
        highlightthickness=0,
        borderwidth=0,
    )
    advert_list.grid(row=0, column=0, sticky="nsew")
    advert_scroll = ttk.Scrollbar(left, orient="vertical", command=advert_list.yview)
    advert_list.configure(yscrollcommand=advert_scroll.set)
    advert_scroll.grid(row=0, column=1, sticky="ns")

    left_button_panel = ttk.Frame(left)
    left_button_panel.grid(row=1, column=0, columnspan=2, pady=(8, 0))
    ttk.Button(
        left_button_panel,
        text="Add group",
        command=lambda: add_advert(),
        style="Accent.TButton",
    ).pack(side="left", padx=4, expand=True)
    ttk.Button(left_button_panel, text="Duplicate", command=lambda: duplicate_advert()).pack(
        side="left", padx=4, expand=True
    )
    ttk.Button(left_button_panel, text="Delete", command=lambda: delete_advert()).pack(
        side="left", padx=4, expand=True
    )

    right = ttk.LabelFrame(frame, text="Advert content")
    right.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
    right.columnconfigure(0, weight=1)
    right.rowconfigure(3, weight=1)

    title_var = tk.StringVar()
    meta_var = tk.StringVar(value="Select an advert group to preview its broadcasts.")

    header = ttk.Frame(right)
    header.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 2))
    header.columnconfigure(1, weight=1)
    ttk.Label(header, text="Name").grid(row=0, column=0, sticky="w")
    ttk.Entry(header, textvariable=title_var, state="readonly").grid(
        row=0, column=1, sticky="ew", padx=(4, 0)
    )
    ttk.Label(right, textvariable=meta_var, foreground=SECONDARY_TEXT).grid(
        row=1, column=0, sticky="w", padx=8, pady=(0, 8)
    )

    broadcast_frame = ttk.LabelFrame(right, text="Broadcast entries")
    broadcast_frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=4)
    broadcast_frame.columnconfigure(0, weight=1)
    broadcast_frame.rowconfigure(0, weight=1)
    broadcast_tree = ttk.Treeview(
        broadcast_frame,
        columns=("first_line",),
        show="headings",
        selectmode="browse",
        height=8,
    )
    broadcast_tree.heading("first_line", text="First line")
    broadcast_tree.column("first_line", anchor="w")
    broadcast_tree.grid(row=0, column=0, sticky="nsew")
    bcast_scroll = ttk.Scrollbar(broadcast_frame, orient="vertical", command=broadcast_tree.yview)
    broadcast_tree.configure(yscrollcommand=bcast_scroll.set)
    bcast_scroll.grid(row=0, column=1, sticky="ns")

    bcast_button_frame = ttk.Frame(broadcast_frame)
    bcast_button_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 0))
    ttk.Button(
        bcast_button_frame, text="Add broadcast", command=lambda: add_broadcast()
    ).pack(side="left", padx=4)
    ttk.Button(
        bcast_button_frame, text="Delete broadcast", command=lambda: delete_broadcast()
    ).pack(side="left", padx=4)

    content_notebook = ttk.Notebook(right, style="Neon.TNotebook")
    content_notebook.grid(row=3, column=0, sticky="nsew", padx=8, pady=(4, 8))

    lines_tab = ttk.Frame(content_notebook)
    lines_tab.columnconfigure(0, weight=1)
    lines_tab.rowconfigure(0, weight=1)
    lines_list = tk.Listbox(
        lines_tab,
        background=SLATE_BG,
        foreground=LIGHT_TEXT,
        selectbackground=ACCENT_CYAN,
        activestyle="none",
        highlightthickness=0,
        selectmode="extended",
    )
    lines_list.grid(row=0, column=0, sticky="nsew")
    lines_scroll = ttk.Scrollbar(lines_tab, orient="vertical", command=lines_list.yview)
    lines_list.configure(yscrollcommand=lines_scroll.set)
    lines_scroll.grid(row=0, column=1, sticky="ns")

    preferred_voice_id: str | None = None

    def _apply_to_selected_lines(operation: Callable[[Line], None]):
        if not current_broadcast_id:
            return
        broadcast = broadcast_map.get(current_broadcast_id)
        if not broadcast:
            return
        changed = False
        selection = lines_list.curselection()
        for idx in selection:
            if idx >= len(broadcast.lines):
                continue
            operation(broadcast.lines[idx])
            changed = True
        if changed:
            refresh_lines(broadcast)

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

    line_editor = ttk.LabelFrame(lines_tab, text="Line editor")
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
    ttk.Button(line_button_frame, text="Update line", command=lambda: update_line(
        context,
        lines_list,
        line_text_var,
        line_voice_var,
        line_moodle_var,
        line_effects_var,
        line_sound_var,
    )).pack(side="left", padx=4)
    ttk.Button(line_button_frame, text="Copy GUID", command=lambda: copy_line_guid(lines_list, parent, context)).pack(side="left", padx=4)
    ttk.Button(line_button_frame, text="Delete line", command=lambda: delete_line(context, lines_list)).pack(side="left", padx=4)
    ttk.Button(line_button_frame, text="Add line", command=lambda: _handle_add_line(), style="Accent.TButton").pack(side="left", padx=4)
    content_notebook.add(lines_tab, text="Lines")

    transcript_tab = ttk.Frame(content_notebook)
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
        background=SLATE_BG,
        foreground=LIGHT_TEXT,
        insertbackground=ACCENT_CYAN,
        relief="flat",
        borderwidth=0,
        height=10,
    )
    transcript_text.grid(row=0, column=1, sticky="nsew", padx=4, pady=2)
    transcript_tab.columnconfigure(0, weight=1)
    transcript_tab.rowconfigure(0, weight=1)
    button_frame = ttk.Frame(transcript_tab)
    button_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=4, pady=4)
    ttk.Button(button_frame, text="Refresh transcript", command=lambda: refresh_transcript_panel(broadcast_map.get(current_broadcast_id))).pack(side="left", padx=4)
    ttk.Button(button_frame, text="Apply transcript", command=lambda: apply_transcript()).pack(side="right", padx=4)
    content_notebook.add(transcript_tab, text="Transcript")

    advert_ids: list[str] = []
    broadcast_map: dict[str, AdvertBroadcast] = {}
    voice_tag_map: dict[str, str] = {}
    current_advert_id: str | None = None
    current_broadcast_id: str | None = None

    def refresh_lines(broadcast: AdvertBroadcast):
        lines_list.delete(0, tk.END)
        for idx, line in enumerate(broadcast.lines):
            voice = context.project.voices.get(line.voice_id)
            speaker = voice.name if voice else "Unknown"
            display = f"{idx + 1:02d}. {speaker}: {line.text}"
            lines_list.insert("end", display)
            if voice and voice.color:
                lines_list.itemconfig(idx, fg=voice.color)

    def show_broadcast(broadcast: AdvertBroadcast, lines_widget: tk.Text = transcript_text):
        nonlocal current_broadcast_id
        current_broadcast_id = broadcast.id
        lines_widget.configure(state="normal")
        lines_widget.delete("1.0", "end")
        lines_widget.insert("1.0", lines_as_text(broadcast.lines, context.project))
        lines_widget.configure(state="disabled")
        refresh_lines(broadcast)
        update_voice_combobox()
        refresh_transcript_panel(broadcast)
        if broadcast_tree.exists(broadcast.id):
            snippet = broadcast.lines[0].text if broadcast.lines else "(no lines yet)"
            broadcast_tree.item(broadcast.id, values=(snippet,))

    def refresh_transcript_panel(broadcast: AdvertBroadcast | None):
        speaker_list.delete(0, tk.END)
        transcript_text.configure(state="normal")
        transcript_text.delete("1.0", "end")
        if not broadcast:
            transcript_text.insert("1.0", "No broadcast selected.")
            transcript_text.configure(state="disabled")
            return
        for line in broadcast.lines:
            voice = context.project.voices.get(line.voice_id)
            speaker = voice.name if voice else "Unknown"
            speaker_list.insert("end", speaker)
            transcript_text.insert("end", f"{line.text}\n")

    def show_advert(advert: AdvertScript):
        nonlocal current_advert_id
        current_advert_id = advert.id
        title_var.set(advert.name)
        meta_var.set(format_meta(advert))
        broadcast_tree.delete(*broadcast_tree.get_children())
        broadcast_map.clear()
        if advert.broadcasts:
            for broadcast in advert.broadcasts:
                broadcast_map[broadcast.id] = broadcast
                snippet = broadcast.lines[0].text if broadcast.lines else "(no lines yet)"
                tags: tuple[str, ...] = ()
                first_line = broadcast.lines[0] if broadcast.lines else None
                if first_line and first_line.voice_id:
                    voice = context.project.voices.get(first_line.voice_id)
                    if voice and voice.color:
                        tag_name = f"advert-voice-{voice.id}"
                        if tag_name not in voice_tag_map:
                            broadcast_tree.tag_configure(tag_name, foreground=voice.color)
                            voice_tag_map[tag_name] = voice.color
                        tags = (tag_name,)
                broadcast_tree.insert(
                    "",
                    "end",
                    iid=broadcast.id,
                    values=(snippet,),
                    tags=tags,
                )
            broadcast_tree.selection_set(advert.broadcasts[0].id)
            show_broadcast(advert.broadcasts[0])
        else:
            current_broadcast_id = None
            refresh_transcript_panel(None)
            lines_list.delete(0, tk.END)

    def update_voice_combobox():
        names = [voice.name for voice in context.project.voices.values()]
        voice_combo["values"] = names
        if line_voice_var.get() not in names:
            line_voice_var.set("")

    update_voice_combobox()


    def refresh_adverts():
        nonlocal current_advert_id
        advert_ids.clear()
        advert_list.delete(0, tk.END)
        for advert in context.project.advertisements.values():
            advert_ids.append(advert.id)
            advert_list.insert("end", advert.name)
        if not advert_ids:
            current_advert_id = None
            title_var.set("")
            meta_var.set("No adverts loaded.")
            transcript_text.configure(state="normal")
            transcript_text.delete("1.0", "end")
            transcript_text.configure(state="disabled")
            lines_list.delete(0, tk.END)
            return
        if current_advert_id not in advert_ids:
            current_advert_id = advert_ids[0]
        idx = advert_ids.index(current_advert_id)
        advert_list.selection_clear(0, "end")
        advert_list.selection_set(idx)
        advert = context.project.advertisements.get(current_advert_id)
        if advert:
            show_advert(advert)

    def _restore_line_selection(index: int):
        lines_list.selection_clear(0, "end")
        if 0 <= index < lines_list.size():
            lines_list.selection_set(index)
            load_line_selection(
                context,
                lines_list,
                line_text_var,
                line_voice_var,
                line_moodle_var,
                line_effects_var,
                line_sound_var,
            )

    def _handle_add_line():
        if not current_broadcast_id:
            return
        broadcast = broadcast_map.get(current_broadcast_id)
        if not broadcast:
            return
        project_ops.add_line_to_broadcast(
            context,
            broadcast.id,
            line_text_var.get(),
            voice_id=preferred_voice_id,
            moodle=line_moodle_var.get() or None,
            effects=[effect.strip() for effect in line_effects_var.get().split(",") if effect.strip()],
            sound_file=line_sound_var.get() or None,
            notify=True,
        )
        show_broadcast(broadcast)
        _restore_line_selection(len(broadcast.lines) - 1)
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
        if not current_broadcast_id:
            return
        broadcast = broadcast_map.get(current_broadcast_id)
        if not broadcast:
            return
        selection = lines_list.curselection()
        if not selection:
            return
        idx = selection[0]
        if idx >= len(broadcast.lines):
            return
        line = broadcast.lines[idx]
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
        show_broadcast(broadcast)
        _restore_line_selection(idx)

    def delete_line(context, lines_list):
        if not current_broadcast_id:
            return
        broadcast = broadcast_map.get(current_broadcast_id)
        if not broadcast:
            return
        selection = lines_list.curselection()
        if not selection:
            return
        idx = selection[0]
        if idx < len(broadcast.lines):
            broadcast.lines.pop(idx)
            show_broadcast(broadcast)
            _restore_line_selection(min(idx, max(0, len(broadcast.lines) - 1)))

    def copy_line_guid(lines_list, parent, context):
        if not current_broadcast_id:
            return
        broadcast = broadcast_map.get(current_broadcast_id)
        if not broadcast:
            return
        selection = lines_list.curselection()
        if not selection:
            return
        idx = selection[0]
        if idx >= len(broadcast.lines):
            return
        guid = broadcast.lines[idx].guid
        root = parent.winfo_toplevel()
        root.clipboard_clear()
        root.clipboard_append(guid)

    def load_line_selection(
        context,
        lines_list,
        text_var,
        voice_var,
        moodle_var,
        effects_var,
        sound_var,
    ):
        if not current_broadcast_id:
            return
        broadcast = broadcast_map.get(current_broadcast_id)
        if not broadcast:
            return
        selection = lines_list.curselection()
        if not selection:
            return
        idx = selection[0]
        if idx >= len(broadcast.lines):
            return
        line = broadcast.lines[idx]
        text_var.set(line.text)
        voice = context.project.voices.get(line.voice_id)
        voice_var.set(voice.name if voice else "")
        moodle_var.set(line.moodle or "")
        effects_var.set(", ".join(line.effects))
        sound_var.set(line.sound_file or "")

    lines_list.bind(
        "<<ListboxSelect>>",
        lambda event: load_line_selection(
            context,
            lines_list,
            line_text_var,
            line_voice_var,
            line_moodle_var,
            line_effects_var,
            line_sound_var,
        ),
    )

    def on_select(event=None):
        selection = advert_list.curselection()
        if not selection:
            return
        idx = selection[0]
        if idx >= len(advert_ids):
            return
        advert_id = advert_ids[idx]
        advert = context.project.advertisements.get(advert_id)
        if advert:
            show_advert(advert)

    def on_broadcast_select(event=None):
        selection = broadcast_tree.selection()
        if not selection:
            return
        bcast_id = selection[0]
        broadcast = broadcast_map.get(bcast_id)
        if broadcast:
            show_broadcast(broadcast)

    def add_advert():
        nonlocal current_advert_id
        new_id = _unique_advert_id()
        advert = AdvertScript(
            id=new_id,
            name=f"Advert {len(context.project.advertisements) + 1}",
            startdelay=0.0,
            timestampmode="Static",
            loopmin=1,
            loopmax=1,
        )
        broadcast = AdvertBroadcast(
            id=_unique_broadcast_id(),
            timestamp=0.0,
            endstamp=30.0,
            day=0,
            advert_cat="none",
            is_segment=True,
        )
        broadcast.lines.append(Line(text="New advert line", voice_id=None))
        advert.broadcasts.append(broadcast)
        context.project.advertisements[new_id] = advert
        current_advert_id = new_id
        refresh_adverts()

    def duplicate_advert():
        nonlocal current_advert_id
        if not current_advert_id:
            return
        original = context.project.advertisements.get(current_advert_id)
        if not original:
            return
        new_id = _unique_advert_id()
        clone = AdvertScript(
            id=new_id,
            name=f"{original.name} Copy",
            startdelay=original.startdelay,
            timestampmode=original.timestampmode,
            loopmin=original.loopmin,
            loopmax=original.loopmax,
            lines=[Line(text=line.text, voice_id=line.voice_id, effects=list(line.effects)) for line in original.lines],
        )
        for broadcast in original.broadcasts:
            dup = AdvertBroadcast(
                id=_unique_broadcast_id(),
                timestamp=broadcast.timestamp,
                endstamp=broadcast.endstamp,
                day=broadcast.day,
                advert_cat=broadcast.advert_cat,
                is_segment=broadcast.is_segment,
                lines=[Line(text=line.text, voice_id=line.voice_id, effects=list(line.effects)) for line in broadcast.lines],
            )
            clone.broadcasts.append(dup)
        context.project.advertisements[new_id] = clone
        current_advert_id = new_id
        refresh_adverts()

    def delete_advert():
        nonlocal current_advert_id
        if not current_advert_id:
            return
        if not messagebox.askyesno(
            "Delete advert",
            "Deleting this advert group removes all associated broadcasts. Continue?",
        ):
            return
        context.project.advertisements.pop(current_advert_id, None)
        current_advert_id = None
        refresh_adverts()

    def add_broadcast():
        if not current_advert_id:
            return
        advert = context.project.advertisements.get(current_advert_id)
        if not advert:
            return
        new_broadcast = AdvertBroadcast(
            id=_unique_broadcast_id(),
            timestamp=0.0,
            endstamp=30.0,
            day=0,
            advert_cat="none",
            is_segment=True,
        )
        new_broadcast.lines.append(Line(text="New advert line", voice_id=None))
        advert.broadcasts.append(new_broadcast)
        refresh_adverts()
        broadcast_tree.selection_set(new_broadcast.id)
        show_broadcast(new_broadcast)

    def delete_broadcast():
        if not current_advert_id or not current_broadcast_id:
            return
        advert = context.project.advertisements.get(current_advert_id)
        if not advert:
            return
        advert.broadcasts = [
            b for b in advert.broadcasts if b.id != current_broadcast_id
        ]
        current_broadcast_id = None
        refresh_adverts()

    def apply_transcript():
        if not current_advert_id or not current_broadcast_id:
            return
        advert = context.project.advertisements.get(current_advert_id)
        if not advert:
            return
        broadcast = next((b for b in advert.broadcasts if b.id == current_broadcast_id), None)
        if not broadcast:
            return
        content = [line.strip() for line in transcript_text.get("1.0", "end").splitlines() if line.strip()]
        broadcast.lines = [Line(text=line) for line in content]
        show_broadcast(broadcast)

    advert_list.bind("<<ListboxSelect>>", on_select)
    broadcast_tree.bind("<<TreeviewSelect>>", on_broadcast_select)
    refresh_adverts()
    context.register_refresh_callback(refresh_adverts)
    context.register_refresh_callback(update_voice_combobox)

    tips_label = ttk.Label(
        frame,
        text="Tips: select multiple lines, right-click for voice/effects, use the line buttons to add/delete quickly",
        foreground="#8f94a6",
    )
    tips_label.grid(row=1, column=0, columnspan=2, sticky="e", padx=12, pady=(0, 8))

    return frame
