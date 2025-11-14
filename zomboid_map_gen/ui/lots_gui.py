import random
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

LOT_TYPES = [
    ("North Residential", "#008b8b"),
    ("East Residential", "#006400"),
    ("South Residential", "#8b0000"),
    ("West Residential", "#8b008b"),
    ("North Industrial", "#00ced1"),
    ("East Industrial", "#3cb371"),
    ("South Industrial", "#cd5c5c"),
    ("West Industrial", "#c71585"),
    ("North Commercial", "#e0ffff"),
    ("East Commercial", "#90ee90"),
    ("South Commercial", "#ffb6c1"),
    ("West Commercial", "#ff77ff"),
]
LOT_SHAPES = {"Square": (1, 1), "Long Rect": (2, 1), "Tall Rect": (1, 2)}


def _label(parent, text):
    return tk.Label(parent, text=text, bg="#121212", fg="white")


class LotsTab(tk.Frame):
    def __init__(self, parent, conf, on_change, on_click, get_paths):
        super().__init__(parent, bg="#121212")
        self.conf = conf
        self.on_change = on_change
        self.on_click = on_click
        self.get_paths = get_paths
        self.var_lot_type = tk.StringVar(value=LOT_TYPES[0][0])
        self.var_lot_shape = tk.StringVar(value="Square")
        self.var_lot_x = tk.IntVar(value=0)
        self.var_lot_y = tk.IntVar(value=0)
        self.var_lot_size = tk.IntVar(value=100)
        self.var_lot_width = tk.IntVar(value=100)
        self.var_lot_height = tk.IntVar(value=100)
        self.var_mask_veg = tk.BooleanVar(value=False)
        self.var_pave = tk.BooleanVar(value=False)
        self.var_auto_count = tk.IntVar(value=16)

        self._preview_img = None
        self._lot_list = []

        self._build_ui()
        self._update_list_entries()
        self.refresh_preview()

    def _build_ui(self):
        top = tk.Frame(self, bg="#121212")
        top.pack(fill=tk.X, padx=8, pady=6)
        _label(top, "Type").pack(side=tk.LEFT)
        type_combo = ttk.Combobox(top, values=[t[0] for t in LOT_TYPES], textvariable=self.var_lot_type,
                                  state="readonly", width=20)
        type_combo.pack(side=tk.LEFT, padx=(6, 8))
        _label(top, "Shape").pack(side=tk.LEFT)
        shape_combo = ttk.Combobox(top, values=list(LOT_SHAPES.keys()), textvariable=self.var_lot_shape,
                                   state="readonly", width=10)
        shape_combo.pack(side=tk.LEFT, padx=(6, 0))
        shape_combo.bind("<<ComboboxSelected>>", self._lot_shape_changed)

        coords = tk.Frame(self, bg="#121212")
        coords.pack(fill=tk.X, padx=8, pady=(4, 0))
        _label(coords, "X").pack(side=tk.LEFT)
        tk.Entry(coords, textvariable=self.var_lot_x, width=5, bg="#1e1e1e", fg="white").pack(side=tk.LEFT, padx=4)
        _label(coords, "Y").pack(side=tk.LEFT)
        tk.Entry(coords, textvariable=self.var_lot_y, width=5, bg="#1e1e1e", fg="white").pack(side=tk.LEFT, padx=4)
        _label(coords, "Base").pack(side=tk.LEFT)
        tk.Entry(coords, textvariable=self.var_lot_size, width=6, bg="#1e1e1e", fg="white").pack(side=tk.LEFT, padx=4)

        dims = tk.Frame(self, bg="#121212")
        dims.pack(fill=tk.X, padx=8, pady=(4, 0))
        _label(dims, "Width").pack(side=tk.LEFT)
        tk.Entry(dims, textvariable=self.var_lot_width, width=6, bg="#1e1e1e", fg="white").pack(side=tk.LEFT, padx=4)
        _label(dims, "Height").pack(side=tk.LEFT, padx=(12, 0))
        tk.Entry(dims, textvariable=self.var_lot_height, width=6, bg="#1e1e1e", fg="white").pack(side=tk.LEFT, padx=4)

        buttons = tk.Frame(self, bg="#121212")
        buttons.pack(fill=tk.X, padx=8, pady=(6, 0))
        tk.Button(buttons, text="Add Lot", command=self._add_lot).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(buttons, text="Remove Selected", command=self._remove_lot).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(buttons, text="Edit Selected", command=self._edit_selected).pack(side=tk.LEFT)

        mask_frame = tk.Frame(self, bg="#121212")
        mask_frame.pack(fill=tk.X, padx=8, pady=(6, 0))
        tk.Checkbutton(mask_frame, text="Mask lots in vegetation", bg="#121212", fg="white",
                       selectcolor="#121212", variable=self.var_mask_veg, command=self._toggle_mask).pack(side=tk.LEFT)
        tk.Checkbutton(mask_frame, text="Pave lots", bg="#121212", fg="white",
                       selectcolor="#121212", variable=self.var_pave, command=self._toggle_pave).pack(side=tk.LEFT, padx=(16, 0))

        auto_frame = tk.Frame(self, bg="#121212")
        auto_frame.pack(fill=tk.X, padx=8, pady=(6, 0))
        _label(auto_frame, "Auto generate near roads").pack(side=tk.LEFT)
        tk.Scale(auto_frame, from_=1, to=200, orient=tk.HORIZONTAL, variable=self.var_auto_count, length=160,
                 bg="#121212", fg="white", troughcolor="#333").pack(side=tk.LEFT, padx=(6, 0))
        tk.Button(auto_frame, text="Auto Generate", command=self._auto_generate).pack(side=tk.LEFT, padx=6)

        list_frame = tk.Frame(self, bg="#121212")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(6, 0))
        self._listbox = tk.Listbox(list_frame, bg="#1a1a1a", fg="white", selectbackground="#333", height=10)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self._listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._listbox.config(yscrollcommand=scrollbar.set)

        preview_frame = tk.Frame(self, bg="#121212")
        preview_frame.pack(fill=tk.X, padx=8, pady=(6, 0))
        self._preview_canvas = tk.Canvas(preview_frame, width=260, height=260, bg="#141414", highlightthickness=1, highlightbackground="#333")
        self._preview_canvas.pack()
        self._preview_canvas.bind("<Button-1>", self._place_from_canvas)

        legend = tk.Frame(self, bg="#121212")
        legend.pack(fill=tk.X, padx=8, pady=(6, 0))
        for name, color in LOT_TYPES:
            key = tk.Frame(legend, bg="#121212")
            key.pack(side=tk.LEFT, padx=4)
            tk.Label(key, width=2, bg=color).pack(side=tk.LEFT)
            tk.Label(key, text=name.split()[0], bg="#121212", fg="white").pack(side=tk.LEFT, padx=(4, 0))

    def _lot_shape_changed(self, *_):
        shape = self.var_lot_shape.get()
        ratio = LOT_SHAPES.get(shape, (1, 1))
        base = max(1, int(self.var_lot_size.get()))
        self.var_lot_width.set(max(1, base * ratio[0]))
        self.var_lot_height.set(max(1, base * ratio[1]))

    def _update_list_entries(self):
        self._listbox.delete(0, tk.END)
        for lot in self.conf.setdefault("lots", {}).setdefault("placed", []):
            self._listbox.insert(tk.END, f"{lot['type']} @ ({lot['x']},{lot['y']}) {lot['width']}x{lot['height']}")

    def _edit_selected(self):
        sel = self._listbox.curselection()
        if not sel:
            return
        lot = self.conf.setdefault("lots", {}).setdefault("placed", [])[sel[0]]
        self.var_lot_type.set(lot["type"])
        self.var_lot_x.set(lot["x"])
        self.var_lot_y.set(lot["y"])
        self.var_lot_width.set(lot["width"])
        self.var_lot_height.set(lot["height"])
        self.var_lot_size.set(max(lot["width"], lot["height"]))
        self.var_lot_shape.set("Square")
        self._lot_shape_changed()
        self.on_change()

    def _add_lot(self):
        placed = self.conf.setdefault("lots", {}).setdefault("placed", [])
        placed.append({
            "type": self.var_lot_type.get(),
            "x": int(self.var_lot_x.get()),
            "y": int(self.var_lot_y.get()),
            "width": int(self.var_lot_width.get()),
            "height": int(self.var_lot_height.get()),
        })
        self.on_change()
        self._update_list_entries()
        self._draw_preview()

    def _remove_lot(self):
        sel = self._listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        placed = self.conf.setdefault("lots", {}).setdefault("placed", [])
        if 0 <= idx < len(placed):
            placed.pop(idx)
            self.on_change()
            self._update_list_entries()
            self._draw_preview()

    def _toggle_mask(self):
        self.conf.setdefault("lots", {})["mask_vegetation"] = bool(self.var_mask_veg.get())
        self.on_change()

    def _toggle_pave(self):
        self.conf.setdefault("lots", {})["pave"] = bool(self.var_pave.get())
        self.on_change()

    def _auto_generate(self):
        roads_path = self.get_paths()[2]
        if not roads_path or not roads_path.exists():
            return
        img = Image.open(roads_path).convert("RGBA")
        coords = [(x, y) for x in range(img.width) for y in range(img.height) if img.getpixel((x, y))[3] > 0]
        if not coords:
            return
        count = max(1, int(self.var_auto_count.get()))
        placed = self.conf.setdefault("lots", {}).setdefault("placed", [])
        for _ in range(count):
            x, y = random.choice(coords)
            placed.append({
                "type": self.var_lot_type.get(),
                "x": x,
                "y": y,
                "width": int(self.var_lot_width.get()),
                "height": int(self.var_lot_height.get()),
            })
        self.on_change()
        self._update_list_entries()
        self._draw_preview()

    def refresh_preview(self):
        paths = self.get_paths()
        if not paths:
            return
        preview_path = paths[3]
        if not preview_path or not preview_path.exists():
            return
        img = Image.open(preview_path)
        img.thumbnail((260, 260), Image.LANCZOS)
        self._preview_img = ImageTk.PhotoImage(img)
        self._preview_canvas.delete("all")
        self._preview_canvas.create_image(0, 0, anchor="nw", image=self._preview_img)
        self._draw_preview()

    def _draw_preview(self):
        self._preview_canvas.delete("lot")
        if not self._preview_img:
            return
        canvas_w = self._preview_canvas.winfo_width() or self._preview_img.width()
        canvas_h = self._preview_canvas.winfo_height() or self._preview_img.height()
        scale_x = canvas_w / self._preview_img.width()
        scale_y = canvas_h / self._preview_img.height()
        for lot in self.conf.setdefault("lots", {}).setdefault("placed", []):
            x1 = lot["x"] * scale_x
            y1 = lot["y"] * scale_y
            x2 = (lot["x"] + lot["width"]) * scale_x
            y2 = (lot["y"] + lot["height"]) * scale_y
            color = next((c for name, c in LOT_TYPES if name == lot["type"]), "#ffffff")
            self._preview_canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=2, tag="lot")

    def _place_from_canvas(self, event):
        if not self._preview_img:
            return
        canvas_w = self._preview_canvas.winfo_width()
        canvas_h = self._preview_canvas.winfo_height()
        img_w = self._preview_img.width()
        img_h = self._preview_img.height()
        if not img_w or not img_h or not canvas_w or not canvas_h:
            return
        x = int(event.x * img_w / canvas_w)
        y = int(event.y * img_h / canvas_h)
        self.var_lot_x.set(x)
        self.var_lot_y.set(y)

    def apply_conf(self, conf):
        self.conf = conf
        self._update_list_entries()
        self.refresh_preview()
