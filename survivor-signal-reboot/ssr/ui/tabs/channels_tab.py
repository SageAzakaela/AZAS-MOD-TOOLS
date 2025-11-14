import tkinter as tk
from tkinter import ttk

from ...core import AppContext, Channel
from ..styles import ACCENT_CYAN, LIGHT_TEXT, PANEL_BG, SECONDARY_TEXT, SLATE_BG
from .utils import channel_color_map

DAY_WIDTH_MIN = 90
DAYS_VISIBLE = 7
HOURS_IN_DAY = 24


def make_tab(parent, context: AppContext):
    frame = ttk.Frame(parent)
    frame.configure(style="TFrame")
    frame.columnconfigure(0, weight=1)
    frame.columnconfigure(1, weight=2)
    frame.rowconfigure(0, weight=1)
    frame.rowconfigure(1, weight=2)

    channel_store: list[str] = []
    channel_colors: dict[str, str] = {}
    channel_positions: dict[str, int] = {}
    timeline_base_day = 0

    def get_channel_color(channel_id: str) -> str:
        return channel_colors.get(channel_id, "#ffffff")

    def channel_display(channel: Channel) -> str:
        return f"{channel.name} ({channel.frequency:.1f})"

    def update_timeline_label():
        start = timeline_base_day
        end = start + DAYS_VISIBLE - 1
        timeline_info_var.set(f"Viewing days {start}-{end}")

    def draw_timeline():
        timeline_canvas.delete("all")
        width = timeline_canvas.winfo_width()
        height = timeline_canvas.winfo_height()
        if width < 60 or height < 60:
            return

        margin_left = 60
        margin_top = 26
        margin_bottom = 26
        usable_width = max(1, width - margin_left - 10)
        usable_height = max(1, height - margin_top - margin_bottom)
        max_days = DAYS_VISIBLE
        day_width = usable_width / max_days
        row_height = usable_height / HOURS_IN_DAY
        total_minutes = HOURS_IN_DAY * 60

        base_x = margin_left
        base_y = margin_top

        timeline_canvas.create_rectangle(
            base_x, base_y, base_x + day_width * max_days, base_y + usable_height, outline="#2b2f3a"
        )

        for idx in range(max_days + 1):
            x = base_x + idx * day_width
            timeline_canvas.create_line(x, base_y, x, base_y + usable_height, fill="#2b2f3a")
            if idx < max_days:
                day_label = timeline_base_day + idx
                timeline_canvas.create_text(
                    x + day_width * 0.5,
                    base_y - 12,
                    text=f"Day {day_label}",
                    fill=SECONDARY_TEXT,
                    anchor="s",
                    font=("Spectral", 18),
                )

        for hour in range(0, HOURS_IN_DAY + 1, 2):
            y = base_y + hour * row_height
            timeline_canvas.create_line(base_x, y, base_x + day_width * max_days, y, fill="#2b2f3a")
            timeline_canvas.create_text(
                margin_left - 12,
                y,
                text=f"{hour:02d}:00",
                fill=SECONDARY_TEXT,
                anchor="e",
                font=("Spectral", 18),
            )

        channel_count = max(1, len(channel_store))
        column_width = day_width / channel_count
        for idx, channel_id in enumerate(channel_store):
            color = get_channel_color(channel_id)
            position = channel_positions.get(channel_id, 0)
            column_offset = position * column_width
            channel = context.project.channels.get(channel_id)
            if not channel:
                continue
            for entry in channel.schedule:
                day_index = entry.day - timeline_base_day
                if not (0 <= day_index < max_days):
                    continue
                minute_of_day = entry.start % total_minutes
                start_y = base_y + (minute_of_day / total_minutes) * usable_height
                end_minutes = entry.end if entry.end > entry.start else entry.start + 1
                end_minutes = max(end_minutes, minute_of_day + 10)
                end_y = base_y + (end_minutes / total_minutes) * usable_height
                x = base_x + day_index * day_width + column_offset + (column_width * 0.1)
                rect_width = column_width * 0.8
                timeline_canvas.create_rectangle(
                    x,
                    start_y,
                    x + rect_width,
                    end_y,
                    fill=color,
                    outline="#050916",
                    width=1.5,
                )

    def shift_week(direction: int):
        nonlocal timeline_base_day
        timeline_base_day = max(0, timeline_base_day + direction * DAYS_VISIBLE)
        update_timeline_label()
        draw_timeline()

    def refresh_timeline():
        update_timeline_label()
        draw_timeline()

    def refresh_start_scripts():
        start_script_combo["values"] = [
            broadcast.id for broadcast in context.project.broadcasts.values()
        ]

    def select_channel_by_id(channel_id: str | None):
        if not channel_store:
            return
        if channel_id and channel_id in channel_store:
            idx = channel_store.index(channel_id)
        else:
            idx = 0
        channels_list.selection_clear(0, tk.END)
        channels_list.selection_set(idx)
        channels_list.see(idx)
        on_select()

    def refresh_channels():
        channel_store.clear()
        channels_list.delete(0, tk.END)
        ordered_ids = list(context.project.channels.keys())
        channel_colors.clear()
        channel_colors.update(channel_color_map(ordered_ids))
        channel_positions.clear()
        for idx, channel_id in enumerate(ordered_ids):
            channel_positions[channel_id] = idx

        for idx, channel_id in enumerate(ordered_ids):
            channel = context.project.channels[channel_id]
            channel_store.append(channel_id)
            channels_list.insert(tk.END, channel_display(channel))
            channels_list.itemconfig(idx, fg=channel_colors[channel_id])
        refresh_start_scripts()
        select_channel_by_id(context.active_channel_id)
        refresh_timeline()

    def on_select(_=None):
        sel = channels_list.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(channel_store):
            return
        channel_id = channel_store[idx]
        context.active_channel_id = channel_id
        channel = context.project.channels.get(channel_id)
        if not channel:
            return
        name_var.set(channel.name)
        freq_var.set(str(channel.frequency))
        category_var.set(channel.category)
        auto_var.set(channel.auto_adverts)
        advert_var.set(channel.default_advert_group)
        start_script_var.set(channel.start_script)

    def apply_changes():
        sel = channels_list.curselection()
        if not sel:
            return
        channel_id = channel_store[sel[0]]
        channel = context.project.channels.get(channel_id)
        if not channel:
            return
        channel.name = name_var.get() or channel.name
        try:
            channel.frequency = float(freq_var.get())
        except ValueError:
            pass
        channel.category = category_var.get() or channel.category
        channel.auto_adverts = auto_var.get()
        channel.default_advert_group = advert_var.get()
        channel.start_script = start_script_var.get() or channel.start_script
        refresh_channels()
        context.notify_data_changed()

    def add_channel():
        new_id = f"channel-{len(context.project.channels) + 1}"
        channel = Channel(
            id=new_id,
            name=name_var.get() or f"Channel {len(context.project.channels) + 1}",
            frequency=float(freq_var.get()) if freq_var.get() else 90.1,
            category=category_var.get() or "radio",
            auto_adverts=auto_var.get(),
            default_advert_group=advert_var.get(),
            start_script=start_script_var.get() or "main",
        )
        context.project.channels[new_id] = channel
        context.active_channel_id = new_id
        refresh_channels()
        context.notify_data_changed()

    channel_frame = ttk.LabelFrame(frame, text="Channel roster")
    channel_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
    channel_frame.columnconfigure(0, weight=1)
    channel_frame.rowconfigure(0, weight=1)

    channels_list = tk.Listbox(
        channel_frame,
        background=SLATE_BG,
        foreground=LIGHT_TEXT,
        selectbackground=ACCENT_CYAN,
        selectforeground="#04060a",
        font=("Spectral", 16),
        activestyle="none",
        exportselection=False,
        highlightthickness=0,
    )
    channels_list.grid(row=0, column=0, sticky="nsew")
    channels_scroll = ttk.Scrollbar(channel_frame, orient="vertical", command=channels_list.yview)
    channels_list.configure(yscrollcommand=channels_scroll.set)
    channels_scroll.grid(row=0, column=1, sticky="ns")
    channels_list.bind("<<ListboxSelect>>", on_select)

    timeline_frame = ttk.LabelFrame(frame, text="Channel timeline")
    timeline_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=12, pady=(0, 12))
    timeline_frame.columnconfigure(0, weight=1)
    timeline_frame.rowconfigure(0, weight=1)

    timeline_canvas = tk.Canvas(
        timeline_frame,
        background=PANEL_BG,
        highlightthickness=0,
        height=260,
    )
    timeline_canvas.grid(row=0, column=0, sticky="nsew")
    timeline_canvas.bind("<Configure>", lambda event: draw_timeline())

    timeline_info_frame = ttk.Frame(timeline_frame)
    timeline_info_frame.grid(row=1, column=0, sticky="ew", padx=4, pady=4)
    timeline_info_frame.columnconfigure(1, weight=1)

    timeline_info_var = tk.StringVar(value="Viewing days 0-6")
    ttk.Label(timeline_info_frame, textvariable=timeline_info_var, foreground=SECONDARY_TEXT).grid(
        row=0, column=0, columnspan=2, sticky="w"
    )

    nav_frame = ttk.Frame(timeline_frame)
    nav_frame.grid(row=2, column=0, sticky="ew", pady=(0, 4), padx=4)
    ttk.Button(nav_frame, text="< Previous weeks", command=lambda: shift_week(-1)).pack(
        side="left"
    )
    ttk.Button(nav_frame, text="Next weeks >", command=lambda: shift_week(1)).pack(
        side="right"
    )

    detail_frame = ttk.LabelFrame(frame, text="Channel details")
    detail_frame.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
    detail_frame.columnconfigure(1, weight=1)

    name_var = tk.StringVar()
    freq_var = tk.StringVar()
    category_var = tk.StringVar(value="radio")
    auto_var = tk.BooleanVar()
    advert_var = tk.StringVar()
    start_script_var = tk.StringVar()

    ttk.Label(detail_frame, text="Name").grid(row=0, column=0, sticky="w", padx=8, pady=(6, 2))
    ttk.Entry(detail_frame, textvariable=name_var).grid(row=0, column=1, sticky="ew", padx=8, pady=(6, 2))
    ttk.Label(detail_frame, text="Frequency").grid(row=1, column=0, sticky="w", padx=8, pady=2)
    ttk.Entry(detail_frame, textvariable=freq_var).grid(row=1, column=1, sticky="ew", padx=8, pady=2)
    ttk.Label(detail_frame, text="Category").grid(row=2, column=0, sticky="w", padx=8, pady=2)
    ttk.Entry(detail_frame, textvariable=category_var).grid(row=2, column=1, sticky="ew", padx=8, pady=2)
    ttk.Checkbutton(detail_frame, text="Auto assign adverts", variable=auto_var).grid(
        row=3, column=0, columnspan=2, sticky="w", padx=8, pady=4
    )

    ttk.Label(detail_frame, text="Default advert group").grid(
        row=4, column=0, sticky="w", padx=8, pady=2
    )
    ttk.Entry(detail_frame, textvariable=advert_var).grid(
        row=4, column=1, sticky="ew", padx=8, pady=2
    )
    ttk.Label(detail_frame, text="Start script").grid(row=5, column=0, sticky="w", padx=8, pady=2)
    start_script_combo = ttk.Combobox(detail_frame, textvariable=start_script_var)
    start_script_combo.grid(row=5, column=1, sticky="ew", padx=8, pady=2)
    start_script_combo.configure(state="normal")

    button_frame = ttk.Frame(detail_frame)
    button_frame.grid(row=6, column=0, columnspan=2, pady=12)
    ttk.Button(button_frame, text="Apply changes", command=apply_changes, style="Accent.TButton").pack(
        side="left", padx=6
    )
    ttk.Button(button_frame, text="New channel", command=add_channel).pack(side="right", padx=6)

    refresh_channels()
    context.register_refresh_callback(refresh_channels)
    context.register_refresh_callback(refresh_timeline)

    return frame
