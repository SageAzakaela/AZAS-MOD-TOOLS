import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ..config import save_settings, settings
from ..core import AppContext
from . import styles
from ..utils.typewriter_sound import TypewriterSoundPlayer
from .tabs import (
    assistant_tab,
    adverts_tab,
    channels_tab,
    config_tab,
    planning_tab,
    radio_tab,
    recorded_tab,
    search_tab,
    tv_tab,
    voices_tab,
    export_tab,
)

ICON_FOLDER = Path(__file__).resolve().parents[2] / "assets" / "images"
ICON_SIZE = 26
ROOT_ICON = "Radio_Model_pink.png"

TAB_ORDER = [
    (config_tab, "Config", "200px-Wrench_Model.png"),
    (planning_tab, "Planning", "Map.png"),
    (voices_tab, "Voices", "Microphone.png"),
    (channels_tab, "Channels", "Channels.png"),
    (radio_tab, "Radio", "Radio_Model_pink.png"),
    (tv_tab, "Television", "TvBlack.png"),
    (adverts_tab, "Advertisement", "ComicBook.png"),
    (recorded_tab, "Recorded Media", "VHS.png"),
    (export_tab, "Export", "BirthdaySpiffo.png"),
    (search_tab, "Search", "201px-404SpiffoMascotMap.png"),
    (assistant_tab, "Assistant", "221px-SpiffoDO.png"),
]


def _prompt_for_project_zomboid(root: tk.Tk) -> None:
    if settings.pz_configured and settings.pz_base_path.exists():
        return
    messagebox.showinfo(
        "Project Zomboid path",
        "Please point Aza's Media Manager to your Project Zomboid install so the vanilla files can load.",
        parent=root,
    )
    selected = filedialog.askdirectory(title="Select Project Zomboid install", parent=root)
    if selected:
        settings.pz_base_path = Path(selected)
        settings.pz_configured = True
        save_settings()
    else:
        messagebox.showwarning(
            "Path missing",
            "No path selected. Vanilla assets will remain unavailable until you choose the install folder.",
            parent=root,
        )


def _load_icon(filename: str, size: int = ICON_SIZE) -> tk.PhotoImage | None:
    path = ICON_FOLDER / filename
    if not path.exists():
        return None
    try:
        image = tk.PhotoImage(file=str(path))
    except tk.TclError:
        return None
    width = max(image.width(), 1)
    height = max(image.height(), 1)
    factor = max(1, width // size, height // size)
    if factor > 1:
        image = image.subsample(factor, factor)
    return image


def build_menu(root, context: AppContext):
    menu = tk.Menu(root)

    file_menu = tk.Menu(menu, tearoff=False)
    file_menu.add_command(label="New Project")
    file_menu.add_command(label="Open Project")
    file_menu.add_command(label="Load Vanilla Radio", command=lambda: config_tab.load_radio_data(context))
    file_menu.add_command(label="Load Recorded Media", command=lambda: config_tab.load_recorded_media(context))
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=root.destroy)
    menu.add_cascade(label="File", menu=file_menu)

    prefs_menu = tk.Menu(menu, tearoff=False)
    prefs_menu.add_command(label="Preferences")
    menu.add_cascade(label="Preferences", menu=prefs_menu)

    export_menu = tk.Menu(menu, tearoff=False)
    export_menu.add_command(label="Export Broadcasts")
    export_menu.add_command(label="Build Mod")
    menu.add_cascade(label="Export", menu=export_menu)

    help_menu = tk.Menu(menu, tearoff=False)
    help_menu.add_command(label="About")
    help_menu.add_command(label="Donate!")
    menu.add_cascade(label="Help", menu=help_menu)

    root.config(menu=menu)


def main():
    root = tk.Tk()
    root.title("Aza's Media Manager")
    root.state("zoomed")
    styles.apply_dark_style(root)

    _prompt_for_project_zomboid(root)

    typewriter_player = TypewriterSoundPlayer()
    root.bind_all("<Key>", lambda event: typewriter_player.trigger())

    root_icon = _load_icon(ROOT_ICON, size=32)
    if root_icon:
        root.iconphoto(True, root_icon)

    context = AppContext()
    build_menu(root, context)

    notebook = ttk.Notebook(root, style="Neon.TNotebook")
    notebook.pack(fill="both", expand=True)

    icon_cache: list[tk.PhotoImage] = []
    assistant_tab_state = {"frame": None, "title": "", "icon": None, "added": False}

    def _set_assistant_tab_visible(show: bool) -> None:
        frame = assistant_tab_state["frame"]
        if frame is None:
            return
        if show and not assistant_tab_state["added"]:
            kwargs = {"text": assistant_tab_state["title"]}
            icon = assistant_tab_state["icon"]
            if icon:
                kwargs["image"] = icon
                kwargs["compound"] = "left"
            notebook.add(frame, **kwargs)
            assistant_tab_state["added"] = True
        elif not show and assistant_tab_state["added"]:
            notebook.forget(frame)
            assistant_tab_state["added"] = False

    config_tab.register_ai_tab_toggle_callback(_set_assistant_tab_visible)

    for module, title, icon_name in TAB_ORDER:
        tab_frame = module.make_tab(notebook, context)
        icon = _load_icon(icon_name)
        if icon:
            icon_cache.append(icon)
        if module is assistant_tab:
            assistant_tab_state["frame"] = tab_frame
            assistant_tab_state["title"] = title
            assistant_tab_state["icon"] = icon
            continue
        if icon:
            notebook.add(tab_frame, text=title, image=icon, compound="left")
        else:
            notebook.add(tab_frame, text=title)

    _set_assistant_tab_visible(settings.show_ai_tab)

    root.mainloop()
