import base64
import struct
import zlib
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk

from PIL import Image, ImageTk


COLOR_MAP = {
    "ns": (255, 255, 255),
    "we": (0, 0, 0),
    "door": (255, 255, 0),
    "window": (0, 255, 255),
    "corner": (255, 0, 0),
}
PREVIEW_MAX = 520
BACKGROUND = (24, 24, 24)


@dataclass(slots=True)
class _TilesetRange:
    first: int
    last: int
    name: str


@dataclass(slots=True)
class _LayerPreview:
    name: str
    width: int
    height: int
    codes: list[list[str | None]]
    stats: Counter[str]
    total: int


def _collect_tilesets(root: ET.Element) -> list[_TilesetRange]:
    defaults = {
        "tilewidth": int(root.attrib.get("tilewidth") or 0),
        "tileheight": int(root.attrib.get("tileheight") or 0),
    }
    results: list[_TilesetRange] = []
    for tileset in root.findall("tileset"):
        firstgid = int(tileset.attrib.get("firstgid") or 0)
        tilewidth = int(tileset.attrib.get("tilewidth") or defaults["tilewidth"])
        tileheight = int(tileset.attrib.get("tileheight") or defaults["tileheight"])
        tilecount = int(tileset.attrib.get("tilecount") or 0)
        if tilecount <= 0:
            img = tileset.find("image")
            if img is not None and tilewidth and tileheight:
                imgw = int(img.attrib.get("width") or 0)
                imgh = int(img.attrib.get("height") or 0)
                cols = imgw // tilewidth if tilewidth else 0
                rows = imgh // tileheight if tileheight else 0
                tilecount = cols * rows
        if tilecount <= 0:
            continue
        name = tileset.attrib.get("name") or ""
        results.append(_TilesetRange(first=firstgid, last=firstgid + tilecount - 1, name=name))
    return results


def _gid_in_ranges(gid: int, ranges: list[_TilesetRange]) -> bool:
    for rng in ranges:
        if rng.first <= gid <= rng.last:
            return True
    return False


def _is_door_tileset(name: str) -> bool:
    return "door" in name.lower()


def _is_window_tileset(name: str) -> bool:
    return "window" in name.lower()


def _decode_layer_data(layer: ET.Element, width: int, height: int) -> list[int]:
    data = layer.find("data")
    if data is None:
        raise ValueError("Layer has no <data> element")
    raw_text = (data.text or "").strip()
    if not raw_text:
        return [0] * (width * height)
    clean = "".join(raw_text.split())
    if data.attrib.get("encoding") != "base64":
        raise ValueError("Only base64-encoded layers are supported")
    blob = base64.b64decode(clean)
    if data.attrib.get("compression") == "zlib":
        blob = zlib.decompress(blob)
    expected = width * height * 4
    if len(blob) < expected:
        raise ValueError("Layer data is shorter than expected")
    gids = struct.unpack(f"<{width * height}I", blob[:expected])
    return list(gids)


def _classify_layer(
    gids: list[int],
    width: int,
    height: int,
    door_ranges: list[_TilesetRange],
    window_ranges: list[_TilesetRange],
) -> _LayerPreview:
    stats = Counter()
    codes: list[list[str | None]] = []
    for y in range(height):
        row: list[str | None] = []
        for x in range(width):
            idx = y * width + x
            gid = gids[idx]
            if gid == 0:
                row.append(None)
                continue
            if _gid_in_ranges(gid, door_ranges):
                code = "door"
            elif _gid_in_ranges(gid, window_ranges):
                code = "window"
            else:
                vert = (y > 0 and gids[idx - width]) or (y < height - 1 and gids[idx + width])
                horiz = (x > 0 and gids[idx - 1]) or (x < width - 1 and gids[idx + 1])
                if vert and horiz:
                    code = "corner"
                elif vert:
                    code = "ns"
                elif horiz:
                    code = "we"
                else:
                    code = "ns"
            stats[code] += 1
            row.append(code)
        codes.append(row)
    total = sum(stats.values())
    return _LayerPreview(name="", width=width, height=height, codes=codes, stats=stats, total=total)


def _render_preview(layer: _LayerPreview) -> Image.Image:
    img = Image.new("RGB", (layer.width, layer.height), BACKGROUND)
    pixels = img.load()
    for y, row in enumerate(layer.codes):
        for x, code in enumerate(row):
            if not code:
                continue
            color = COLOR_MAP.get(code, (255, 0, 255))
            pixels[x, y] = color
    scale = max(1.0, min(4.0, PREVIEW_MAX / max(layer.width, layer.height)))
    if scale != 1.0:
        new_size = (max(1, int(layer.width * scale)), max(1, int(layer.height * scale)))
        img = img.resize(new_size, Image.NEAREST)
    return img


def _parse_wall_layers(path: Path) -> list[_LayerPreview]:
    tree = ET.parse(path)
    root = tree.getroot()
    tilesets = _collect_tilesets(root)
    door_ranges = [ts for ts in tilesets if _is_door_tileset(ts.name)]
    window_ranges = [ts for ts in tilesets if _is_window_tileset(ts.name)]
    results: list[_LayerPreview] = []
    for layer in root.findall("layer"):
        name = layer.attrib.get("name", "")
        if "wall" not in name.lower():
            continue
        width = int(layer.attrib.get("width") or 0)
        height = int(layer.attrib.get("height") or 0)
        if width <= 0 or height <= 0:
            continue
        gids = _decode_layer_data(layer, width, height)
        preview = _classify_layer(gids, width, height, door_ranges, window_ranges)
        if preview.total == 0:
            continue
        preview.name = name
        results.append(preview)
    return results


class TmxReadWindow:
    def __init__(self, parent: tk.Tk, tmx_path: Path):
        self._parent = parent
        self.top = tk.Toplevel(parent)
        self.top.title(f"TMX Reader - {tmx_path.name}")
        self.top.configure(bg="#111")
        self.top.transient(parent)
        self.top.grab_set()
        self._preview_img: ImageTk.PhotoImage | None = None
        try:
            self._layers = _parse_wall_layers(tmx_path)
        except Exception:
            self.top.destroy()
            raise
        self._build_ui(tmx_path)

    def _build_ui(self, tmx_path: Path):
        self.top.geometry("900x560")
        frame = tk.Frame(self.top, bg="#111")
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        left = tk.Frame(frame, bg="#111")
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
        tk.Label(left, text="Wall Layers", fg="white", bg="#111", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self._layer_list = tk.Listbox(left, bg="#1a1a1a", fg="white", selectbackground="#333", exportselection=False, height=15, width=28)
        self._layer_list.pack(fill=tk.Y, expand=True, pady=(6, 0))
        self._layer_list.bind("<<ListboxSelect>>", self._on_layer_selected)
        if self._layers:
            for layer in self._layers:
                self._layer_list.insert(tk.END, layer.name)
            self._layer_list.selection_set(0)
        else:
            self._layer_list.insert(tk.END, "No wall layers found")
            self._layer_list.configure(state="disabled")

        preview_frame = tk.Frame(frame, bg="#111")
        preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(preview_frame, text=str(tmx_path), fg="#ccc", bg="#111", anchor="w").pack(fill=tk.X)
        self._preview_label = tk.Label(preview_frame, bg="#0c0c0c")
        self._preview_label.pack(fill=tk.BOTH, expand=True, pady=(6, 4))
        self._info_label = tk.Label(preview_frame, bg="#111", fg="#dde", justify="left", anchor="nw")
        self._info_label.pack(fill=tk.X, pady=(0, 4))
        legend = "Legend: White=North/South, Black=West/East, Yellow=Door, Cyan=Window, Red=Corner"
        tk.Label(preview_frame, text=legend, fg="#bbb", bg="#111", wraplength=500, justify="left").pack(fill=tk.X)
        close = tk.Button(self.top, text="Close", command=self.top.destroy, bg="#222", fg="white", padx=12, pady=6)
        close.pack(side=tk.BOTTOM, pady=(0, 10))
        self.top.protocol("WM_DELETE_WINDOW", self.top.destroy)
        if self._layers:
            self._show_layer(0)
        else:
            self._info_label.configure(text="No walls could be detected in this TMX.")

    def _on_layer_selected(self, event):
        sel = self._layer_list.curselection()
        if not sel or not self._layers:
            return
        self._show_layer(sel[0])

    def _show_layer(self, index: int):
        layer = self._layers[index]
        img = _render_preview(layer)
        self._preview_img = ImageTk.PhotoImage(img)
        self._preview_label.configure(image=self._preview_img, text="")
        stats = layer.stats
        info = (
            f"Layer: {layer.name}\n"
            f"Dimensions: {layer.width} × {layer.height}\n"
            f"Tiles: {layer.total}\n"
            f"North/South (white): {stats.get('ns', 0)}\n"
            f"West/East (black): {stats.get('we', 0)}\n"
            f"Doors (yellow): {stats.get('door', 0)}\n"
            f"Windows (cyan): {stats.get('window', 0)}\n"
            f"Corners (red): {stats.get('corner', 0)}"
        )
        self._info_label.configure(text=info)
