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
        font=("Spectral", 20),
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

    getting_started_text = """[SURVIVOR SIGNAL PLANNING PRIMER]

[OVERVIEW / WHAT TO TRACK]
Think of this notebook as your theatrical stage directions before you hit the editors. Each tab is a living note tied to a major craft lane:
- [Getting Started] stores your playbook: team radios, references, ritual checklists, or lore links you want visible every session.
- [Notes] is a scratch pad for flashes of inspiration, TODO flags, or collaborator shout-outs—keep it messy, then move the important bits to the structured planners.
- [Timeline Planner] is your longitudinal grid; sketch days → hours, mark pacing notes, and spot gaps before you start scripting lines.
- [World Building Planner] narrates the setting. Record locations, factions, vibes, and any recurring magical or radio phenomena (use a fresh paragraph per idea).
- [Character Planner] catalogs voices, accents, moods, and sample lines so you can match them to broadcasts when you jump into Radio/TV.
- [Event Planner] tracks triggers, props, channel premieres, and callouts for later; think of it as the “plot beats” companion to the Timeline.
- [Recorded Media Planner] maps VHS, CDs, and drops. Note what tapes exist, who features on them, and which broadcasts should unlock them.

[WORKFLOW / HOW IT FLOWS]
1. **Config First.** Load `RadioData.xml` + `RecordedMedia.lua` to plant the vanilla channels, voices, and tapes into each tab.
2. **Plan Next.** Fill these panels with your initial beats, pacing, and tone notes. Treat the text as your story bible while writing lines and scheduling.
3. **Build Elsewhere.** Jump into Voices/Channels, Radio, TV, or Recorded Media to author actual assets. Refer back to Planning for voice choices, day offsets, and style cues.
4. **Export / Iterate.** When you feel stable, export the XML/Lua, test in-game, and revisit your planning notes—add notes after playtests so the history stays here.

[QUICK TIPS]
- Use colors/labels when you paste into the Timeline planner so you can spot empty days or overloaded hours at a glance.
- Keep Character motivations beside the voice references so you instantly remember how a speaker should deliver lines.
- Drop AI assistant marks like `[WritePlanningNote]` to have it append context into a panel (especially helpful in the Notes or Character sections).
- Keep the Recorded Media panel lean—list the tapes you want, then list which broadcasts feed them, with a short “why this tape deserves attention.”
- Export regularly and compare the physical broadcast list to these panels so nothing drifts from plan to execution."""

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
