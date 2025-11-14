"""Launch point for the blends-only editor."""
from __future__ import annotations

from pathlib import Path
import tkinter as tk

from .gui import BlendsEditorApp
from .manager import BlendRepository


def main() -> None:
    repo = BlendRepository(Path(__file__).resolve().parents[1] / "vanilla" / "Blends.txt")
    root = tk.Tk()
    BlendsEditorApp(root, repo)
    root.mainloop()


if __name__ == "__main__":
    main()
