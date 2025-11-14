import tkinter as tk
from tkinter import ttk, messagebox

from ...core import AppContext
from ..styles import ACCENT_CYAN, LIGHT_TEXT, PANEL_BG, SECONDARY_TEXT, FONT


WIZARD_STEPS = [
    ("Characters", "Define the character roster and bios."),
    ("Voices", "Assign voices and colors to active talent."),
    ("Groups", "Segment characters into broadcast-ready groups."),
    ("Broadcasts", "Build broadcasts with schedules and lines."),
    ("Channels", "Map broadcasts to channels & timelines."),
    ("Review", "Validate the entire station before launch."),
]


def _handle_wizard(name: str) -> None:
    messagebox.showinfo("Wizard", f"Launching the {name} wizard (coming soon).")


def make_tab(parent, context: AppContext):
    frame = ttk.Frame(parent)
    frame.configure(style="TFrame")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=0)
    frame.rowconfigure(1, weight=1)

    header = ttk.Label(
        frame,
        text="Signal Wizards",
        foreground=LIGHT_TEXT,
        font=("Spectral", 24, "bold"),
    )
    header.grid(row=0, column=0, sticky="ew", pady=(16, 8))

    steps_frame = ttk.Frame(frame)
    steps_frame.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 16))
    steps_frame.columnconfigure(0, weight=1)
    steps_frame.columnconfigure(1, weight=1)
    steps_frame.columnconfigure(2, weight=1)
    steps_frame.rowconfigure(tuple(range(len(WIZARD_STEPS))), weight=0)

    for idx, (title, detail) in enumerate(WIZARD_STEPS):
        btn = ttk.Button(
            steps_frame,
            text=title,
            command=lambda name=title: _handle_wizard(name),
            style="Accent.TButton",
        )
        btn.grid(row=idx // 3 * 2, column=idx % 3, sticky="ew", padx=8, pady=(idx >= 3 and 16 or 0, 4))
        label = ttk.Label(
            steps_frame,
            text=detail,
            foreground=SECONDARY_TEXT,
            background=PANEL_BG,
            wraplength=220,
            justify="center",
        )
        label.grid(row=(idx // 3) * 2 + 1, column=idx % 3, sticky="ew", padx=8, pady=(0, 12))

    return frame
