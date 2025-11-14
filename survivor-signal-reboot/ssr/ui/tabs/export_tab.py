import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from ...core import AppContext
from ...io import exporter, modpack
from ...io.serializer import serialize_context


def make_tab(parent, context: AppContext):
    frame = ttk.Frame(parent)
    frame.configure(style="TFrame")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(1, weight=1)

    ttk.Label(frame, text="Export snapshot to disk or inspect JSON.").grid(row=0, column=0, sticky="w", padx=12, pady=8)

    text_frame = ttk.Frame(frame)
    text_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=8)
    text_frame.columnconfigure(0, weight=1)
    text_frame.rowconfigure(0, weight=1)

    preview = tk.Text(text_frame, wrap="none")
    preview.grid(row=0, column=0, sticky="nsew")
    vsb = ttk.Scrollbar(text_frame, orient="vertical", command=preview.yview)
    preview.configure(yscrollcommand=vsb.set)
    vsb.grid(row=0, column=1, sticky="ns")

    status_var = tk.StringVar(value="Ready to export.")
    mod_output_var = tk.StringVar(value=str(Path.cwd()))
    mod_id_var = tk.StringVar(value="survivor_signal_reboot")
    mod_name_var = tk.StringVar(value="Survivor Signal Reboot")
    mod_description_var = tk.StringVar(value="Generated mod")
    mod_version_var = tk.StringVar(value="1.0")
    mod_thumbnail_var = tk.StringVar(value="")

    def refresh():
        snapshot = serialize_context(context)
        preview.delete("1.0", tk.END)
        preview.insert(tk.END, json.dumps(snapshot, indent=2))

    def save():
        snapshot = serialize_context(context)
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(snapshot, handle, indent=2)
            preview.insert(tk.END, f"\nSaved snapshot to {path}")
            status_var.set(f"Saved snapshot to {path}")

    def export():
        directory = filedialog.askdirectory(title="Select export folder")
        if not directory:
            return
        out_path = Path(directory)
        exporter.export_radio_data(context, out_path)
        exporter.export_recorded_media(context, out_path)
        status_var.set(f"Exported files to {directory}")
        preview.insert(tk.END, f"\nExported radio and recorded media to {directory}")

    def export_mod():
        output_dir = Path(mod_output_var.get() or ".")
        metadata = modpack.ModMetadata(
            mod_id=mod_id_var.get() or "survivor_signal_reboot",
            name=mod_name_var.get() or "Survivor Signal Reboot",
            version=mod_version_var.get() or "1.0",
            description=mod_description_var.get(),
            thumbnail=Path(mod_thumbnail_var.get()) if mod_thumbnail_var.get() else None,
        )
        mod_folder = modpack.build_mod_package(context, output_dir, metadata)
        status_var.set(f"Exported mod to {mod_folder}")
        preview.insert(tk.END, f"\nExported mod to {mod_folder}")


    button_frame = ttk.Frame(frame)
    button_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=8)
    ttk.Button(button_frame, text="Refresh snapshot", command=refresh).pack(side="left", padx=4)
    ttk.Button(button_frame, text="Save snapshot", command=save, style="Accent.TButton").pack(side="right", padx=4)

    export_frame = ttk.Frame(frame)
    export_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))
    export_frame.columnconfigure(0, weight=1)
    ttk.Button(export_frame, text="Export to Project Zomboid", command=export, style="Accent.TButton").grid(
        row=0, column=0, sticky="ew"
    )
    ttk.Button(export_frame, text="Export mod package", command=export_mod, style="Accent.TButton").grid(
        row=0, column=1, sticky="ew", padx=4
    )
    ttk.Label(export_frame, textvariable=status_var).grid(row=1, column=0, columnspan=2, sticky="w", pady=4)

    mod_frame = ttk.LabelFrame(frame, text="Mod package settings")
    mod_frame.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 12))
    mod_frame.columnconfigure(1, weight=1)
    ttk.Label(mod_frame, text="Output folder").grid(row=0, column=0, sticky="w", padx=8, pady=4)
    ttk.Entry(mod_frame, textvariable=mod_output_var).grid(row=0, column=1, sticky="ew", padx=8, pady=4)
    ttk.Button(mod_frame, text="Choose...", command=lambda: _pick_folder(mod_output_var)).grid(row=0, column=2, sticky="ew", padx=4, pady=4)
    ttk.Label(mod_frame, text="Mod ID").grid(row=1, column=0, sticky="w", padx=8, pady=4)
    ttk.Entry(mod_frame, textvariable=mod_id_var).grid(row=1, column=1, sticky="ew", padx=8, pady=4)
    ttk.Label(mod_frame, text="Display name").grid(row=2, column=0, sticky="w", padx=8, pady=4)
    ttk.Entry(mod_frame, textvariable=mod_name_var).grid(row=2, column=1, sticky="ew", padx=8, pady=4)
    ttk.Label(mod_frame, text="Description").grid(row=3, column=0, sticky="w", padx=8, pady=4)
    ttk.Entry(mod_frame, textvariable=mod_description_var).grid(row=3, column=1, sticky="ew", padx=8, pady=4)
    ttk.Label(mod_frame, text="Version").grid(row=4, column=0, sticky="w", padx=8, pady=4)
    ttk.Entry(mod_frame, textvariable=mod_version_var).grid(row=4, column=1, sticky="ew", padx=8, pady=4)
    ttk.Label(mod_frame, text="Thumbnail").grid(row=5, column=0, sticky="w", padx=8, pady=4)
    ttk.Entry(mod_frame, textvariable=mod_thumbnail_var).grid(row=5, column=1, sticky="ew", padx=8, pady=4)
    ttk.Button(mod_frame, text="Choose...", command=lambda: _pick_file(mod_thumbnail_var)).grid(
        row=5, column=2, sticky="ew", padx=4, pady=4
    )

    refresh()

    return frame


def _pick_folder(var: tk.StringVar):
    path = filedialog.askdirectory(title="Select export folder")
    if path:
        var.set(path)


def _pick_file(var: tk.StringVar):
    path = filedialog.askopenfilename(title="Select thumbnail", filetypes=[("Images", "*.png;*.jpg;*.jpeg"), ("All files", "*.*")])
    if path:
        var.set(path)
