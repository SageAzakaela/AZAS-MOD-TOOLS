from tkinter import ttk

LIGHT_TEXT = "#f6f8fd"
SLATE_BG = "#121726"
PANEL_BG = "#1d2233"
ACCENT_MAGENTA = "#dc4fe5"
ACCENT_CYAN = "#64ddea"
ACCENT_BLUE = "#5ad1ff"
SECONDARY_TEXT = "#b8c3e5"
FONT = ("Spectral", 15)
MONO_FONT = ("VT323", 15)


def apply_dark_style(root):
    style = ttk.Style(root)
    root.configure(bg=SLATE_BG)
    style.theme_use("clam")
    style.configure("TFrame", background=SLATE_BG)
    style.configure("TLabel", background=SLATE_BG, foreground=LIGHT_TEXT, font=FONT)
    style.configure("TLabelFrame", background=SLATE_BG, foreground=LIGHT_TEXT)
    style.configure("TEntry", fieldbackground="#0c1130", foreground=LIGHT_TEXT, font=FONT)
    style.configure("TText", background="#050916", foreground=LIGHT_TEXT, font=MONO_FONT)
    style.configure("TNotebook", background=SLATE_BG)
    style.configure("Neon.TNotebook", background=SLATE_BG, borderwidth=0)
    style.configure(
        "Neon.TNotebook.Tab",
        background=PANEL_BG,
        foreground=LIGHT_TEXT,
        padding=(12, 6),
        font=("Spectral", 18),
    )
    style.map(
        "Neon.TNotebook.Tab",
        background=[("selected", ACCENT_CYAN)],
        foreground=[("selected", "#04060a")],
    )
    style.configure("Accent.TButton", background=ACCENT_MAGENTA, foreground="#04060a", font=FONT)
    style.map("Accent.TButton", background=[("active", ACCENT_BLUE)])
    style.configure("TNotebook.Tab", background=PANEL_BG, foreground=LIGHT_TEXT, padding=4)
    style.configure("Treeview", background="#091024", fieldbackground="#091024", foreground=LIGHT_TEXT, font=FONT)
