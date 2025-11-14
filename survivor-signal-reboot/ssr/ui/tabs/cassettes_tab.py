import tkinter as tk
from tkinter import ttk

from ...core import AppContext


def make_tab(parent, context: AppContext):
    frame = ttk.Frame(parent)
    frame.configure(style="TFrame")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)
    label = ttk.Label(
        frame,
        text="""Create cassette tapes with rewind constraints.\nVoices: {len(context.project.voices)} · Channels: {len(context.project.channels)} · Broadcasts: {len(context.project.broadcasts)}"""
    )
    label.grid(sticky='nw', padx=12, pady=12)
    return frame
