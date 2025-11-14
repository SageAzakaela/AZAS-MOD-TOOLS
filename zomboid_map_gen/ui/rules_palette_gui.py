import tkinter as tk
from tkinter import ttk

from ..utils import rules_palette as rules_palette_utils
from .palette_utils import parse_palette_value, rgb_to_hex, rgb_to_string


BG = "#121212"
FG = "white"
SECTION_HEIGHT = 220


class RulesPaletteTab(tk.Frame):
    """Palette overrides based on the Rules.txt terrain + vegetation rules."""

    def __init__(self, parent, conf, on_change, on_click):
        super().__init__(parent, bg=BG)
        self.conf = conf
        self.on_change = on_change
        self.on_click = on_click
        self.palette_controls = {"terrain": {}, "vegetation": {}}
        self._section_defaults: dict[str, dict[str, tuple[int, int, int]]] = {
            "terrain": {},
            "vegetation": {},
        }
        self._sections: dict[str, dict] = {}
        self._rules: dict[str, dict[str, tuple[int, int, int]]] = {"terrain": {}, "vegetation": {}}

        self._notice = tk.Label(
            self,
            text="Overrides below follow the Rules.txt colors for the final Terrain+Roads and Vegetation outputs. "
                 "Leave a field blank to revert to the rule default.",
            bg=BG,
            fg="#d5d5d5",
            wraplength=460,
            justify="left",
        )
        self._notice.pack(anchor="w", padx=8, pady=(8, 0))
        self._error_label = tk.Label(self, text="", bg=BG, fg="#ff7777", wraplength=460, justify="left")
        self._error_label.pack(anchor="w", padx=8, pady=(0, 4))

        for key, title in (("terrain", "Terrain + Roads (Rules)"), ("vegetation", "Vegetation (Rules)")):
            self._sections[key] = self._build_scroll_section(title)

        self.apply_conf(conf)

    def _build_scroll_section(self, title: str) -> dict:
        container = tk.LabelFrame(self, text=title, bg=BG, fg=FG)
        container.pack(fill=tk.BOTH, padx=8, pady=(4, 4), expand=True)
        canvas = tk.Canvas(container, bg=BG, highlightthickness=0, height=SECTION_HEIGHT)
        scroll = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 4), pady=4)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=4)
        inner = tk.Frame(canvas, bg=BG)
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda ev, c=canvas: c.configure(scrollregion=c.bbox("all")))
        canvas.bind("<Configure>", lambda ev, c=canvas, w=window: c.itemconfigure(w, width=ev.width))
        canvas.bind("<MouseWheel>", lambda ev, c=canvas: c.yview_scroll(int(-ev.delta / 120), "units"))
        return {"canvas": canvas, "inner": inner, "rows": [], "scroll_window": window}

    def apply_conf(self, conf):
        self.conf = conf
        rules_path = rules_palette_utils.get_rules_file(self.conf)
        if rules_path:
            entries, error = rules_palette_utils.load_rules_colors(rules_path)
        else:
            entries, error = {"terrain": {}, "vegetation": {}}, "Rules file not found."
        self._rules = entries
        self._error_label.config(text=error or "")
        for key in ("terrain", "vegetation"):
            self._populate_section(key)

    def _populate_section(self, key: str):
        section = self._sections[key]
        for row in section["rows"]:
            row.destroy()
        section["rows"].clear()
        self.palette_controls[key].clear()
        self._section_defaults[key].clear()

        overrides = self.conf.setdefault("rules_palette", {}).setdefault(key, {})
        section_rules = self._rules.get(key, {})
        if not section_rules:
            return
        for label, default_color in section_rules.items():
            row = tk.Frame(section["inner"], bg=BG)
            row.pack(fill=tk.X, padx=4, pady=2)
            lbl = tk.Label(row, text=label, width=26, anchor="w", bg=BG, fg=FG, wraplength=240, justify="left")
            lbl.pack(side=tk.LEFT)
            var = tk.StringVar()
            entry = tk.Entry(row, width=14, textvariable=var, bg="#1b1b1b", fg="white", insertbackground="white")
            entry.pack(side=tk.LEFT, padx=6)
            preview = tk.Label(row, text=" ", width=3, bg="#000", relief="ridge", bd=1)
            preview.pack(side=tk.LEFT, padx=6)
            self.palette_controls[key][label] = {"var": var, "preview": preview}
            self._section_defaults[key][label] = tuple(default_color)

            specified = overrides.get(label)
            rgb = tuple(specified) if specified and len(specified) >= 3 else default_color
            var.set(rgb_to_string(rgb))
            var.trace_add("write", lambda *_ , s=key, lbl=label: self._update_preview(s, lbl))
            entry.bind("<Return>", lambda _e, s=key, lbl=label: self._apply_entry(s, lbl))
            entry.bind("<FocusOut>", lambda _e, s=key, lbl=label: self._apply_entry(s, lbl))
            self._update_preview(key, label)
            section["rows"].append(row)

    def _update_preview(self, section_key: str, label: str):
        ctrl = self.palette_controls.get(section_key, {}).get(label)
        if not ctrl:
            return
        rgb = parse_palette_value(ctrl["var"].get())
        if not rgb:
            rgb = self._section_defaults[section_key].get(label, (0, 0, 0))
        ctrl["preview"].configure(bg=rgb_to_hex(rgb))

    def _apply_entry(self, section_key: str, label: str):
        ctrl = self.palette_controls.get(section_key, {}).get(label)
        if not ctrl:
            return
        rgb = parse_palette_value(ctrl["var"].get())
        palette = self.conf.setdefault("rules_palette", {}).setdefault(section_key, {})
        if rgb:
            palette[label] = list(rgb)
        else:
            palette.pop(label, None)
        self.on_change()
        self.on_click()
