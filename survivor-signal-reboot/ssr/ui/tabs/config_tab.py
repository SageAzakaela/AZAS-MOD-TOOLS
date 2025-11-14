import pathlib
from pathlib import Path
from typing import Callable

import tempfile

import tkinter as tk
from tkinter import filedialog, ttk

from ...config.settings import save_settings, settings
from ...core import AppContext
from ...io import importers
from ...io import project as project_io
from ..styles import ACCENT_CYAN


def _format_path(path):
    return str(path)


BLANK_RADIO_XML = """<?xml version="1.0" encoding="utf-8"?>
<RadioData>
  <RootInfo>
    <SourceFile>SurvivorSignalReboot</SourceFile>
    <FileGUID>00000000-0000-0000-0000-000000000000</FileGUID>
    <Version>1</Version>
  </RootInfo>
  <Voices />
  <Channels />
</RadioData>
"""

BLANK_RECORDED_LUA = "-- Blank recorded media\nRecMedia = RecMedia or {}\n"
BLANK_TRANSLATION = "// Blank translation\n"

def _set_recorded_path(recorded_path_var: tk.StringVar, path: str | Path):
    recorded_path_var.set(_format_path(path))
    settings.last_recorded_path = _format_path(path)
    save_settings()


def _set_translation_path(translation_var: tk.StringVar, path: str | Path):
    translation_var.set(_format_path(path))
    settings.last_translation_path = _format_path(path)
    save_settings()


_ai_tab_toggle_callbacks: list[Callable[[bool], None]] = []


def register_ai_tab_toggle_callback(callback: Callable[[bool], None]) -> None:
    _ai_tab_toggle_callbacks.append(callback)


def _notify_ai_tab_toggle(show: bool) -> None:
    for callback in _ai_tab_toggle_callbacks:
        try:
            callback(show)
        except Exception:
            pass


def load_radio_data(
    context: AppContext, status_var: tk.StringVar | None = None, path: str | None = None
) -> None:
    target = path or settings.radio_data_path
    if isinstance(target, str):
        target_path = pathlib.Path(target)
    else:
        target_path = target
    if not target_path.exists():
        if status_var:
            status_var.set(f"Radio data missing: {_format_path(target_path)}")
        return False
    importers.import_radio_data(context, str(target_path))
    context.notify_data_changed()
    if status_var:
        status_var.set(f"Loaded radio data from {_format_path(target_path)}")
    return True


def load_recorded_media(
    context: AppContext,
    status_var: tk.StringVar | None = None,
    path: str | None = None,
    translation_path: str | None = None,
    recorded_path_var: tk.StringVar | None = None,
) -> None:
    target = path or settings.recorded_media_path
    if isinstance(target, str):
        target_path = pathlib.Path(target)
    else:
        target_path = target
    if not target_path.exists():
        if status_var:
            status_var.set(f"Recorded media missing: {_format_path(target_path)}")
        return False
    translation = translation_path
    if translation:
        translation_path_obj = pathlib.Path(translation)
        if not translation_path_obj.exists():
            if status_var:
                status_var.set("Translation file missing; select it before loading recorded media.")
            return False
        translation_arg = str(translation_path_obj)
    else:
        default_translation = settings.translation_path
        translation_arg = str(default_translation) if default_translation.exists() else None
        if not translation_arg and status_var:
            status_var.set("Translation file missing; continuing without translation.")
    importers.import_recorded_media(context, str(target_path), translation_arg)
    context.notify_data_changed()
    if recorded_path_var:
        recorded_path_var.set(_format_path(target_path))
    if status_var:
        status_var.set(f"Loaded recorded media from {_format_path(target_path)}")
    settings.last_recorded_path = _format_path(target_path)
    if translation_arg:
        settings.last_translation_path = _format_path(translation_arg)
    save_settings()
    return True


def make_tab(parent, context: AppContext):
    frame = ttk.Frame(parent)
    frame.configure(style="TFrame")
    frame.columnconfigure(0, weight=1)

    info = ttk.Label(
        frame,
        text="Load vanilla Project Zomboid data on demand.",
        foreground="#d1d1f0",
    )
    info.grid(row=0, column=0, sticky="w", padx=12, pady=(8, 4))

    recorded_path_value = settings.last_recorded_path or _format_path(settings.recorded_media_path)
    recorded_path_var = tk.StringVar(value=recorded_path_value)
    status_var = tk.StringVar(value="No vanilla data loaded.")
    translation_path_value = settings.last_translation_path or _format_path(settings.translation_path)
    translation_path_var = tk.StringVar(value=translation_path_value)

    ai_key_var = tk.StringVar(value=settings.ai_api_key)
    api_status_var = tk.StringVar(value="OpenAI key not saved.")
    typewriter_var = tk.BooleanVar(value=settings.typewriter_sound_enabled)
    ai_tab_var = tk.BooleanVar(value=getattr(settings, "show_ai_tab", True))

    general_frame = ttk.LabelFrame(frame, text="General settings")
    general_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
    general_frame.columnconfigure(0, weight=1)

    ttk.Label(general_frame, text="OpenAI API key:").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
    ttk.Entry(general_frame, textvariable=ai_key_var, show="*").grid(
        row=1,
        column=0,
        sticky="ew",
        padx=8,
        pady=(0, 8),
    )

    api_status_label = ttk.Label(general_frame, textvariable=api_status_var, foreground=ACCENT_CYAN)
    api_status_label.grid(row=2, column=0, sticky="w", padx=8, pady=(0, 6))

    ttk.Button(
        general_frame,
        text="Save OpenAI key",
        command=lambda: save_ai_key(),
        style="Accent.TButton",
    ).grid(row=3, column=0, sticky="w", padx=8, pady=(0, 8))

    ttk.Checkbutton(
        general_frame,
        text="Enable typewriter typing sounds",
        variable=typewriter_var,
        command=lambda: _update_typewriter_setting(typewriter_var, status_var),
    ).grid(row=4, column=0, sticky="w", padx=8, pady=(0, 4))

    ttk.Checkbutton(
        general_frame,
        text="Show Assistant tab",
        variable=ai_tab_var,
        command=lambda: _update_ai_tab_setting(ai_tab_var, status_var),
    ).grid(row=5, column=0, sticky="w", padx=8, pady=(0, 8))

    def save_ai_key():
        settings.ai_api_key = ai_key_var.get().strip()
        api_status_var.set("OpenAI API key saved.")
        if status_var:
            status_var.set("OpenAI key saved.")
        save_settings()

    def _update_typewriter_setting(var: tk.BooleanVar, status_var: tk.StringVar | None = None) -> None:
        settings.typewriter_sound_enabled = var.get()
        if status_var:
            msg = "Typewriter sound enabled." if var.get() else "Typewriter sound disabled."
            status_var.set(msg)
        save_settings()

    def _update_ai_tab_setting(var: tk.BooleanVar, status_var: tk.StringVar | None = None) -> None:
        settings.show_ai_tab = var.get()
        if status_var:
            msg = "Assistant tab visible." if var.get() else "Assistant tab hidden."
            status_var.set(msg)
        save_settings()
        _notify_ai_tab_toggle(var.get())

    status_label = ttk.Label(frame, textvariable=status_var, foreground="#8f94a6")
    status_label.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 4))
    recorded_label = ttk.Label(frame, textvariable=recorded_path_var, foreground="#64ddea")
    recorded_label.grid(row=3, column=0, sticky="e", padx=12, pady=(0, 4))
    translation_label = ttk.Label(frame, textvariable=translation_path_var, foreground=ACCENT_CYAN)
    translation_label.grid(row=4, column=0, sticky="w", padx=12, pady=(0, 12))
    ttk.Separator(frame, orient="horizontal").grid(row=5, column=0, sticky="ew", padx=12, pady=(0, 12))

    def _load_vanilla_bundle():
        radio_loaded = load_radio_data(context, status_var)
        recorded_source = settings.last_recorded_path or _format_path(settings.recorded_media_path)
        translation_source = (
            translation_path_var.get()
            or settings.last_translation_path
            or _format_path(settings.translation_path)
        )
        recorded_loaded = load_recorded_media(
            context,
            status_var,
            recorded_source,
            translation_path=translation_source,
            recorded_path_var=recorded_path_var,
        )
        if recorded_loaded:
            _set_recorded_path(recorded_path_var, recorded_source)
            if translation_source:
                _set_translation_path(translation_path_var, translation_source)
        if radio_loaded and recorded_loaded:
            status_var.set("Loaded vanilla RadioData + recorded media.")

    def _load_blank_bundle():
        with tempfile.TemporaryDirectory() as tmpdirname:
            temp_dir = Path(tmpdirname)
            radio_path = temp_dir / "RadioData.xml"
            recorded_path = temp_dir / "RecordedMedia.lua"
            translation_path = temp_dir / "RecordedMedia_EN.txt"
            radio_path.write_text(BLANK_RADIO_XML, encoding="utf-8")
            recorded_path.write_text(BLANK_RECORDED_LUA, encoding="utf-8")
            translation_path.write_text(BLANK_TRANSLATION, encoding="utf-8")
            load_radio_data(context, status_var, str(radio_path))
            success = load_recorded_media(
                context,
                status_var,
                str(recorded_path),
                translation_path=str(translation_path),
            )
            if success:
                status_var.set("Loaded blank RadioData + recorded media.")
            else:
                status_var.set("Failed to load blank recorded media.")

    def _load_manual_recorded():
        translation_value = translation_path_var.get() or None
        success = load_recorded_media(
            context,
            status_var,
            translation_path=translation_value,
            recorded_path_var=recorded_path_var,
        )
        if success:
            record_path = settings.last_recorded_path or _format_path(settings.recorded_media_path)
            _set_recorded_path(recorded_path_var, record_path)
            if translation_value:
                _set_translation_path(translation_path_var, translation_value)

    bundle_frame = ttk.Frame(frame)
    bundle_frame.grid(row=6, column=0, sticky="w", padx=12, pady=(0, 12))
    ttk.Button(
        bundle_frame,
        text="Load vanilla data bundle",
        command=_load_vanilla_bundle,
        style="Accent.TButton",
    ).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(
        bundle_frame,
        text="Load blank data bundle",
        command=_load_blank_bundle,
    ).grid(row=0, column=1)

    button_frame = ttk.Frame(frame)
    button_frame.grid(row=7, column=0, sticky="w", padx=12, pady=(0, 12))
    ttk.Button(
        button_frame,
        text="Load RadioData.xml",
        command=lambda: load_radio_data(context, status_var),
        style="Accent.TButton",
    ).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(
        button_frame,
        text="Load Recorded Media",
        command=_load_manual_recorded,
    ).grid(row=0, column=1)

    file_frame = ttk.Frame(frame)
    file_frame.grid(row=8, column=0, sticky="w", padx=12, pady=(0, 12))

    ttk.Button(
        file_frame,
        text="Select RadioData XML...",
        command=lambda: _pick_radio(context, status_var),
    ).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(
        file_frame,
        text="Select Recorded Media...",
        command=lambda: _pick_recorded(
            context, status_var, translation_path_var, recorded_path_var
        ),
    ).grid(row=0, column=1, padx=(0, 8))
    ttk.Button(
        file_frame,
        text="Select Translation file...",
        command=lambda: _pick_translation(translation_path_var, status_var),
    ).grid(row=0, column=2)

    project_frame = ttk.Frame(frame)
    project_frame.grid(row=9, column=0, sticky="w", padx=12, pady=(0, 12))
    ttk.Button(
        project_frame,
        text="Save Project (.srx)",
        command=lambda: _save_project(context, status_var),
        style="Accent.TButton",
    ).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(
        project_frame,
        text="Load Project (.srx)",
        command=lambda: _load_project(context, status_var),
    ).grid(row=0, column=1)

    if settings.auto_load_vanilla:
        warning = ttk.Label(
            frame,
            text="Auto-load is enabled; manual buttons will update existing data.",
            foreground="#ffb347",
        )
        warning.grid(row=10, column=0, sticky="w", padx=12)

    return frame



def _pick_radio(context: AppContext, status_var: tk.StringVar | None = None) -> None:
    path = filedialog.askopenfilename(
        title="Select RadioData XML",
        filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
    )
    if path:
        load_radio_data(context, status_var, path)


def _pick_recorded(
    context: AppContext,
    status_var: tk.StringVar | None = None,
    translation_var: tk.StringVar | None = None,
    recorded_path_var: tk.StringVar | None = None,
) -> None:
    path = filedialog.askopenfilename(
        title="Select Recorded Media LUA",
        filetypes=[("Lua files", "*.lua"), ("All files", "*.*")],
    )
    if path:
        translation_value = translation_var.get() if translation_var else None
        success = load_recorded_media(
            context,
            status_var,
            path,
            translation_path=translation_value,
            recorded_path_var=recorded_path_var,
        )
        if success:
            if recorded_path_var:
                _set_recorded_path(recorded_path_var, path)
            if translation_var and translation_value:
                _set_translation_path(translation_var, translation_value)


def _pick_translation(
    translation_var: tk.StringVar,
    status_var: tk.StringVar | None = None,
) -> None:
    path = filedialog.askopenfilename(
        title="Select Recorded Media translation",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
    )
    if path:
        _set_translation_path(translation_var, path)
        if status_var:
            status_var.set(f"Translation file set to {_format_path(path)}")
PROJECT_EXT = ".srx"

def _save_project(context: AppContext, status_var: tk.StringVar | None = None) -> None:
    path = filedialog.asksaveasfilename(
        title="Save Signal Reboot project",
        defaultextension=PROJECT_EXT,
        filetypes=[("Signal Reboot Project", f"*{PROJECT_EXT}"), ("All files", "*.*")],
    )
    if not path:
        return
    project_io.save_project(context, pathlib.Path(path))
    if status_var:
        status_var.set(f"Project saved to {path}")


def _load_project(context: AppContext, status_var: tk.StringVar | None = None) -> None:
    path = filedialog.askopenfilename(
        title="Load Signal Reboot project",
        filetypes=[("Signal Reboot Project", f"*{PROJECT_EXT}"), ("All files", "*.*")],
    )
    if not path:
        return
    project_io.load_project(context, pathlib.Path(path))
    if status_var:
        status_var.set(f"Project loaded from {path}")
