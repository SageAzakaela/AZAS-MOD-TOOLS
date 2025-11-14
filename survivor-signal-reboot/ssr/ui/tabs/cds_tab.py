import tkinter as tk
from tkinter import ttk

from ...core import AppContext


def make_tab(parent, context: AppContext):
    frame = ttk.Frame(parent)
    frame.configure(style="TFrame")
    frame.columnconfigure(0, weight=1)
    frame.columnconfigure(1, weight=2)
    frame.rowconfigure(0, weight=1)

    list_frame = ttk.LabelFrame(frame, text="CD Compilations")
    list_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
    list_frame.columnconfigure(0, weight=1)
    cd_list = tk.Listbox(list_frame, height=10)
    cd_list.grid(row=0, column=0, sticky="nsew")
    list_frame.rowconfigure(0, weight=1)
    cd_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=cd_list.yview)
    cd_list.configure(yscrollcommand=cd_scroll.set)
    cd_scroll.grid(row=0, column=1, sticky="ns")

    detail = ttk.LabelFrame(frame, text="Compilation metadata")
    detail.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
    detail.columnconfigure(1, weight=1)
    detail.rowconfigure(3, weight=1)

    name_var = tk.StringVar()
    curator_var = tk.StringVar()
    genre_var = tk.StringVar()

    ttk.Label(detail, text="Name").grid(row=0, column=0, sticky="w", padx=8, pady=4)
    ttk.Entry(detail, textvariable=name_var).grid(row=0, column=1, sticky="ew", padx=8, pady=4)
    ttk.Label(detail, text="Curator").grid(row=1, column=0, sticky="w", padx=8, pady=4)
    ttk.Entry(detail, textvariable=curator_var).grid(row=1, column=1, sticky="ew", padx=8, pady=4)
    ttk.Label(detail, text="Genre").grid(row=2, column=0, sticky="w", padx=8, pady=4)
    ttk.Entry(detail, textvariable=genre_var).grid(row=2, column=1, sticky="ew", padx=8, pady=4)

    playlist = tk.Listbox(detail, height=6)
    playlist.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=8, pady=8)

    def refresh():
        cd_list.delete(0, tk.END)
        for cd in context.project.cds.values():
            cd_list.insert(tk.END, f"{cd.name} ({cd.genre})")
        update_detail()

    def update_detail():
        cd = context.active_cd
        playlist.delete(0, tk.END)
        if not cd:
            name_var.set("")
            curator_var.set("")
            genre_var.set("")
            return
        name_var.set(cd.name)
        curator_var.set(cd.curator)
        genre_var.set(cd.genre)
        for bid in cd.track_ids:
            tr = context.project.broadcasts.get(bid)
            if tr:
                playlist.insert(tk.END, f"{tr.title} [{tr.id}]")

    def on_select(_=None):
        sel = cd_list.curselection()
        if not sel:
            return
        cd_id = list(context.project.cds)[sel[0]]
        context.select_cd(cd_id)
        update_detail()

    def apply():
        cd = context.active_cd
        if not cd:
            return
        cd.name = name_var.get() or cd.name
        cd.curator = curator_var.get()
        cd.genre = genre_var.get()
        refresh()

    def add_cd():
        cd = context.add_cd(name_var.get() or "New Compilation", curator_var.get(), genre_var.get())
        refresh()
        idx = list(context.project.cds).index(cd.id)
        cd_list.selection_clear(0, tk.END)
        cd_list.selection_set(idx)
        cd_list.activate(idx)
        update_detail()

    cd_list.bind("<<ListboxSelect>>", on_select)

    btn_frame = ttk.Frame(detail)
    btn_frame.grid(row=4, column=0, columnspan=2, pady=8)
    ttk.Button(btn_frame, text="Apply", command=apply, style="Accent.TButton").pack(side="left", padx=4)
    ttk.Button(btn_frame, text="Create CD", command=add_cd).pack(side="right", padx=4)

    refresh()

    return frame
