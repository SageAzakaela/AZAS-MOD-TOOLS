import tkinter as tk
from tkinter import ttk

from ..styles import LIGHT_TEXT, PANEL_BG
from ...core import AppContext


NOTE_EDITORS: dict[str, tk.Text] = {}
_EDITOR_EDITABLE: dict[str, bool] = {}
_EDITOR_TITLES: dict[str, str] = {}


def _normalize_title(title: str) -> str:
    return title.strip().lower()

def available_planning_panels() -> list[str]:
    """Return the registered panel titles."""
    return list(_EDITOR_TITLES.values())


def _register_panel(title: str, editor: tk.Text, editable: bool) -> None:
    normalized = _normalize_title(title)
    NOTE_EDITORS[normalized] = editor
    _EDITOR_EDITABLE[normalized] = editable
    _EDITOR_TITLES[normalized] = title


def set_planning_note_content(title: str, content: str) -> bool:
    normalized = _normalize_title(title)
    editor = NOTE_EDITORS.get(normalized)
    if not editor:
        return False
    editable = _EDITOR_EDITABLE.get(normalized, True)
    editor.configure(state="normal")
    editor.delete("1.0", "end")
    editor.insert("1.0", content)
    if not editable:
        editor.configure(state="disabled")
    return True


def append_planning_note_content(title: str, content: str) -> bool:
    normalized = _normalize_title(title)
    editor = NOTE_EDITORS.get(normalized)
    if not editor:
        return False
    editable = _EDITOR_EDITABLE.get(normalized, True)
    editor.configure(state="normal")
    editor.insert("end", content)
    if not editable:
        editor.configure(state="disabled")
    return True


def _make_panel(frame, label, text="", editable=False):
    panel = ttk.Frame(frame)
    panel.columnconfigure(0, weight=1)
    scroll = ttk.Scrollbar(panel)
    editor = tk.Text(
        panel,
        wrap="word",
        background=PANEL_BG,
        foreground=LIGHT_TEXT,
        insertbackground="#ffffff",
        relief="flat",
        font=("Segoe UI", 16),
    )
    editor.grid(row=0, column=0, sticky="nsew")
    scroll.grid(row=0, column=1, sticky="ns")
    editor.configure(yscrollcommand=scroll.set)
    scroll.configure(command=editor.yview)
    if text:
        editor.insert("1.0", text)
    if not editable:
        editor.configure(state="disabled")
    _register_panel(label, editor, editable)
    return panel


def make_tab(parent, context: AppContext):
    frame = ttk.Frame(parent)
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)

    notebook = ttk.Notebook(frame, style="Neon.TNotebook")
    notebook.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

    getting_started_text = """Survivor Signal Reboot Planning Primer

OVERVIEW
This Planning tab is where you sketch the story beats, pacing, and assets you want to produce before you dive into the technical editors. Treat each panel as a living design doc:
- Getting Started: keep procedural reminders, team notes, or links to lore documents about the world you are building.
- Notes: jot down temporary observations, brainstorming fragments, or TODOs that you can later move into the other tabs.
- Timeline Planner: rough out days, hours, and the flow of broadcasts so you can compare them against the channel grids later.
- World Building Planner: describe locations, factions, strange events, and the tone you want across the radio/TV lineup.
- Character Planner: catalogue voices and NPCs, include inspiration (mood, sample lines, or accents), and track who is speaking when.
- Event Planner: note triggers, props, or new channel launches tied to in-game events; keep track of how each broadcast resolves.
- Recorded Media Planner: decide which VHS tapes, CDs, or audio drops should exist, and which broadcasts feed them.

WORKFLOW
1. Config -> load the base `RadioData.xml` + `RecordedMedia.lua` to populate every tab with vanilla channels, voices, and media so you can remix them.
2. Planning -> expand these panels with your ideas, targets, and pacing notes. Use this text as an outline you can refer to while writing lines and scheduling content in the other tabs.
3. Voices/Channels -> create or edit entities, then drop into Radio/Television/Recorded Media to author broadcasts/scenes. Cross-reference the Planning panels for tone, day offsets, and who should speak.
4. Export -> once the data is complete, generate the XML + Lua exports and drop them into a mod. Playtest in-game, revisit Planning notes, and repeat.

TIPS
- Use the Timeline and Event planners to spot empty days or tightly packed hours before you start writing lines.
- Keep character motivations in the Character planner so you can quickly check who should sound angry, calm, or mysterious.
- Reuse the Notes panel for collaboration snippets or reminders, then copy anything important into the more structured planners.
- Trim long-form lore into digestible bullet points so you can scan the panel quickly in the heat of writing.
- Export often and compare your Planning notes to what appears in-game via the AI Assistant or debug tools."""

    note_template = (
        "Leave notes for yourself or ask Aza to help. Think of this panel as a scratch pad for "
        "story beats, tone cues, or TODOs. The assistant can append content when you drop in a "
        "[WritePlanningNote] tag, so jot anything useful here until more formal planning tools show up."
    )
    starters = (
        ("Getting Started", getting_started_text),
        ("Notes", note_template),
        ("Timeline Planner", "Use this space for timeline notes, pacing reminders, and anchor dates."),
        (
            "World Building Planner",
            "Capture locations, factions, and strange events. Treat this panel as your lore notebook until tighter controls land.",
        ),
        (
            "Character Planner",
            "Record voice identities, moods, motivations, and interactions. The assistant can add persona notes if you ask for it here.",
        ),
        (
            "Event Planner",
            "Sketch triggers, props, and broadcast consequences. Add short-form event notes for now; richer event tools are coming.",
        ),
        (
            "Recorded Media Planner",
            "Note which tapes, CDs, or drops you want. Ask Aza to append story notes by tagging [WritePlanningNote] in the AI tab.",
        ),
    )

    for idx, (title, content) in enumerate(starters):
        panel = _make_panel(frame, title, text=content, editable=(title != "Getting Started"))
        notebook.add(panel, text=title)

    return frame
