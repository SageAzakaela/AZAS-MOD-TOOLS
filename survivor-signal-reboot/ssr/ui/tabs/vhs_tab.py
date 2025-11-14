import tkinter as tk
from tkinter import ttk

from ...core import AppContext


def make_tab(parent, context: AppContext):
    frame = ttk.Frame(parent)
    frame.configure(style="TFrame")
    frame.columnconfigure(0, weight=1)
    frame.columnconfigure(1, weight=2)
    frame.rowconfigure(0, weight=1)

    list_frame = ttk.LabelFrame(frame, text="VHS Tapes")
    list_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
    list_frame.columnconfigure(0, weight=1)
    tape_list = tk.Listbox(list_frame, height=10)
    tape_list.grid(row=0, column=0, sticky="nsew")
    list_frame.rowconfigure(0, weight=1)
    tape_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=tape_list.yview)
    tape_list.configure(yscrollcommand=tape_scroll.set)
    tape_scroll.grid(row=0, column=1, sticky="ns")

    detail = ttk.LabelFrame(frame, text="Tape metadata")
    detail.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
    detail.columnconfigure(1, weight=1)

    name_var = tk.StringVar()
    desc_var = tk.StringVar()
    spawn_var = tk.DoubleVar(value=1.0)

    ttk.Label(detail, text="Name").grid(row=0, column=0, sticky="w", padx=8, pady=4)
    ttk.Entry(detail, textvariable=name_var).grid(row=0, column=1, sticky="ew", padx=8, pady=4)
    ttk.Label(detail, text="Description").grid(row=1, column=0, sticky="w", padx=8, pady=4)
    ttk.Entry(detail, textvariable=desc_var).grid(row=1, column=1, sticky="ew", padx=8, pady=4)
    ttk.Label(detail, text="Spawn weight").grid(row=2, column=0, sticky="w", padx=8, pady=4)
    ttk.Entry(detail, textvariable=spawn_var).grid(row=2, column=1, sticky="ew", padx=8, pady=4)

    assignments = tk.Listbox(detail, height=6)
    assignments.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=8, pady=8)
    detail.rowconfigure(3, weight=1)

    def refresh():
        tape_list.delete(0, tk.END)
        for tape in context.project.vhs_tapes.values():
            tape_list.insert(tk.END, f"{tape.name} [{tape.id}]")
        update_detail()

    def update_detail():
        tape = context.active_vhs
        assignments.delete(0, tk.END)
        if not tape:
            name_var.set("")
            desc_var.set("")
            spawn_var.set(1.0)
            return
        name_var.set(tape.name)
        desc_var.set(tape.description)
        spawn_var.set(tape.spawn_weight)
        for bid in tape.broadcast_ids:
            broadcast = context.project.broadcasts.get(bid)
            if broadcast:
                assignments.insert(tk.END, f"{broadcast.title} ({bid})")

    def on_select(_=None):
        sel = tape_list.curselection()
        if not sel:
            return
        tape_id = list(context.project.vhs_tapes)[sel[0]]
        context.select_vhs(tape_id)
        update_detail()

    def apply():
        tape = context.active_vhs
        if not tape:
            return
        tape.name = name_var.get() or tape.name
        tape.description = desc_var.get()
        tape.spawn_weight = float(spawn_var.get())
        refresh()

    def add_tape():
        tape = context.add_vhs(name_var.get() or "New Tape", desc_var.get(), spawn_var.get())
        refresh()
        tape_list.selection_clear(0, tk.END)
        idx = list(context.project.vhs_tapes).index(tape.id)
        tape_list.selection_set(idx)
        tape_list.activate(idx)
        update_detail()

    tape_list.bind("<<ListboxSelect>>", on_select)

    btn_frame = ttk.Frame(detail)
    btn_frame.grid(row=4, column=0, columnspan=2, pady=8)
    ttk.Button(btn_frame, text="Apply", command=apply, style="Accent.TButton").pack(side="left", padx=4)
    ttk.Button(btn_frame, text="Add Tape", command=add_tape).pack(side="right", padx=4)

    refresh()

    return frame
