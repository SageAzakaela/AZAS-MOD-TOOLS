# assistant_tab.py
from __future__ import annotations

import json
import re
import colorsys
import itertools

from pathlib import Path
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import ttk

from ...ai import assistant as ai_agent
from ...ai import actions as ai_actions
from ...config import settings
from ...io import project as project_io
from ..styles import ACCENT_CYAN, LIGHT_TEXT, SECONDARY_TEXT
from ...core import AppContext
from ...ui.tabs import planning_tab
from ...utils.typewriter_sound import TypewriterSoundPlayer, TYPEWRITER_SOUND_PATH

# ---------------- UI constants ----------------

class _ToolTip:
    def __init__(self, widget: tk.Widget, text: str) -> None:
        self._widget = widget
        self._text = text
        self._tipwindow: tk.Toplevel | None = None
        self._widget.bind("<Enter>", self._show)
        self._widget.bind("<Leave>", self._hide)

    def _show(self, event: tk.Event | None = None) -> None:
        if self._tipwindow or not self._text:
            return
        x = (event.x_root + 10) if event else self._widget.winfo_rootx()
        y = (event.y_root + 20) if event else self._widget.winfo_rooty() + 20
        self._tipwindow = tw = tk.Toplevel(self._widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=self._text,
            justify="left",
            background="#1f2430",
            foreground="#f0f4ff",
            relief="solid",
            borderwidth=1,
            wraplength=280,
            font=("Segoe UI", 16),
        )
        label.pack(padx=6, pady=4)

    def _hide(self, event: tk.Event | None = None) -> None:
        if self._tipwindow:
            self._tipwindow.destroy()
            self._tipwindow = None


ACTION_CATALOG = [
    {
        "title": "Discovery & planning",
        "description": "Gather context, search across assets, and keep planning notes up to date before issuing edits.",
        "actions": [
            {
                "tag": "[QueryBroadcasts]",
                "label": "Pull broadcast samples",
                "tooltip": "Inserts the query tag so Aza returns broadcast titles, days, lines, and metadata for the currently focused channel.",
            },
            {
                "tag": "[QueryChannels]",
                "label": "List channels",
                "tooltip": "Lists every channel, including frequency, category, and scheduling status, without changing any data.",
            },
            {
                "tag": "[SearchProject]",
                "label": "Search project data",
                "tooltip": "Lets Aza search across broadcasts, voices, and recorded media using your keywords, surfacing relevant lines or IDs.",
            },
            {
                "tag": "[ListPlanningPanels]",
                "label": "Show planning panels",
                "tooltip": "Asks Aza to describe the planning panels you already have so you can reference them in follow-up notes.",
            },
            {
                "tag": "[WritePlanningNote]",
                "label": "Write planning note",
                "tooltip": "Adds the write tag so Aza can create fresh content inside a named planning panel (use panel name + content).",
            },
            {
                "tag": "[AppendPlanningNote]",
                "label": "Append planning note",
                "tooltip": "Appends content to an existing planning panel, preserving what’s already there while adding new context.",
            },
        ],
    },
    {
        "title": "Broadcast engineering",
        "description": "Schedule, reschedule, and edit broadcasts or lines while keeping the right channel in focus.",
        "actions": [
            {
                "tag": "[AddBroadcast]",
                "label": "Schedule broadcast",
                "tooltip": "Inserts the tag that prompts Aza to create a new broadcast entry with a title, day, and timing.",
            },
            {
                "tag": "[AddLine]",
                "label": "Append a line",
                "tooltip": "Lets Aza append a line (text, voice, effects) to an existing broadcast, keeping the flow coherent.",
            },
            {
                "tag": "[UpdateBroadcast]",
                "label": "Update broadcast",
                "tooltip": "Request edits to an existing broadcast’s title, description, or metadata without touching other assets.",
            },
            {
                "tag": "[UpdateLine]",
                "label": "Update line",
                "tooltip": "Speaks directly to an existing line so Aza can change text, voice clues, or effects on the fly.",
            },
            {
                "tag": "[StaggerBroadcasts]",
                "label": "Stagger broadcasts",
                "tooltip": "Tell Aza to space a list of broadcasts evenly across a channel, ideal for auto-scheduling clusters.",
            },
            {
                "tag": "[SetActiveChannel]",
                "label": "Focus channel",
                "tooltip": "Switches the active channel so follow-up actions target the correct schedule and lines.",
            },
        ],
    },
    {
        "title": "Voices & station summaries",
        "description": "Manage voices, channels, and station-wide summaries that steer the assistant’s understanding.",
        "actions": [
            {
                "tag": "[AddVoice]",
                "label": "Create voice entity",
                "tooltip": "Inserts a voice creation tag so Aza can name a new speaker, assign a color, and suggest metadata.",
            },
            {
                "tag": "[AddChannel]",
                "label": "Create broadcast channel",
                "tooltip": "Asks Aza to add a channel (name, frequency, category) before routing new broadcasts there.",
            },
            {
                "tag": "[UpdateChannel]",
                "label": "Update channel",
                "tooltip": "Request edits to channel metadata such as frequency, category, or advert groups without touching broadcasts.",
            },
            {
                "tag": "[SummarizeStation]",
                "label": "Station summary",
                "tooltip": "Generates a full station summary covering assets, strengths, gaps, and suggested next steps.",
            },
            {
                "tag": "[SummarizeChannel]",
                "label": "Channel summary",
                "tooltip": "Focuses the summary on a single channel so you can understand its tone, schedule, and coverage.",
            },
            {
                "tag": "[SummarizeCharacters]",
                "label": "Character summary",
                "tooltip": "Asks Aza about character usage, which voices dominate, and where you might diversify.",
            },
        ],
    },
]

ASSISTANT_NAME = "Azakaela, the Goddess of Secrets"
ASSISTANT_COLOR = "#ffc0ff"
USER_COLOR = "#7ad7ff"
TEXT_FONT = ("Segoe UI", 16)
CODE_FONT = ("Consolas", 12)
MAX_PROJECT_SNIPPET = 1500 
MAX_RADIO_SNIPPET = 1000 
MAX_SUMMARY_LINES = 20 

# ---------------- model / style ----------------

ACTION_MODEL = "gpt-4o-mini"
PROSE_MODEL = "gpt-4o"
ACTION_MAX_TOKENS = 800 
PROSE_MAX_TOKENS = 1200
ACTION_TEMPERATURE = 0.1 
PROSE_TEMPERATURE = 0.6

ACTION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                    "enum": [
                        "query_broadcasts",
                        "add_voice",
                        "add_channel",
                        "add_broadcast",
                        "add_line",
                        "update_broadcast",
                        "update_channel",
                        "update_line",
                        "set_active_channel",
                        "query_channels",
                        "search_project",
                        "list_planning_panels",
                        "stagger_broadcasts",
                        "write_planning_note",
                        "append_planning_note",
                        "summarize_station",
                        "summarize_channel",
                        "summarize_characters",
                        ],
                    },
                    "args": {"type": "object"},
                },
                "required": ["type", "args"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["actions"],
    "additionalProperties": False,
}

SYSTEM_PERSONA = (
    "You are Aza, a seasoned radio editor. Your prime directive is MEANINGFUL SUMMARIES.\n"
    "When asked to summarize, always produce:\n"
    "1) Headlines: 4–7 bullets capturing current assets.\n"
    "2) Highlights: strongest scenes/voices and why they land.\n"
    "3) Gaps: missing days, empty hours, thin arcs, or underused voices.\n"
    "4) Next steps: concrete, tool-addressable actions (e.g., add_broadcast, add_line).\n"
    "Keep tone warm, precise, and brief."
)

ACTION_INSTRUCTIONS = (
    "You must output ONLY a single JSON object following this JSON Schema:\n"
    + json.dumps(ACTION_SCHEMA, indent=2)
    + "\nDo not include any prose or code fences. Example output:\n"
    '{"actions":[{"type":"write_planning_note","args":{"panel":"Notes","content":"It worked"}}]}'
)

PROSE_INSTRUCTIONS = (
    "After actions run, respond with the rubric above for any summary request. "
    "Otherwise keep 'Summary / Observations / Next steps'. Prefer bullets. Avoid filler."
)

BANNED_PHRASES = (
    "One moment please",
    "Here’s what I’ve gathered",
    "Here's what I've gathered",
    "cosmic waves of the data",
)

# -------------- local bracket-tag fallback --------------

TAG_TO_ACTION = {
    "WritePlanningNote": "write_planning_note",
    "AppendPlanningNote": "append_planning_note",
    "AddVoice": "add_voice",
    "AddChannel": "add_channel",
    "AddBroadcast": "add_broadcast",
    "AddLine": "add_line",
    "UpdateBroadcast": "update_broadcast",
    "UpdateChannel": "update_channel",
    "UpdateLine": "update_line",
    "QueryBroadcasts": "query_broadcasts",
    "QueryChannels": "query_channels",
    "ListPlanningPanels": "list_planning_panels",
    "StaggerBroadcasts": "stagger_broadcasts",
    "SetActiveChannel": "set_active_channel",
    "SummarizeStation": "summarize_station",
    "SummarizeChannel": "summarize_channel",
    "SummarizeCharacters": "summarize_characters",
}

def _extract_quoted(text: str) -> str | None:
    m = re.search(r'["“](.+?)["”]', text, flags=re.DOTALL)
    return m.group(1).strip() if m else None

def _infer_panel(prompt: str) -> str:
    p = prompt.lower()
    if "world" in p: return "World Building Planner"
    if "timeline" in p: return "Timeline Planner"
    if "character" in p: return "Character Planner"
    if "event" in p: return "Event Planner"
    if "recorded" in p: return "Recorded Media Planner"
    return "Notes"

def parse_bracket_tags_to_actions(prompt: str) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []
    for tag in re.findall(r"\[(\w+)\]", prompt):
        kind = TAG_TO_ACTION.get(tag)
        if not kind:
            continue
        args: Dict[str, Any] = {}
        tail = prompt.split(f"[{tag}]", 1)[-1].strip()

        if kind in ("write_planning_note", "append_planning_note"):
            content = _extract_quoted(tail) or tail
            args = {"panel": _infer_panel(prompt), "content": content.strip()}
        elif kind == "query_broadcasts":
            args = {"query": _extract_quoted(tail) or tail, "limit": 5}
        elif kind == "set_active_channel":
            ch = _extract_quoted(tail) or tail
            args = {"channel_id": ch.strip()}
        else:
            # allow inline JSON-ish args for other actions
            m = re.search(r"\{(.+)\}", tail, flags=re.DOTALL)
            if m:
                try:
                    args = json.loads("{" + m.group(1) + "}")
                except Exception:
                    args = {}

        if args is not None:
            actions.append({"type": kind, "args": args})
    return actions

# ---------------- assistant helpers ----------------

def _safe_call_assistant(messages: List[Dict[str, Any]], *, model: str, max_tokens: int, temperature: float) -> str:
    """Works with wrappers that may or may not accept model/temperature."""
    try:
        return ai_agent.call_assistant(
            settings.ai_api_key,
            messages,
            max_tokens=max_tokens,      # type: ignore[arg-type]
            temperature=temperature,     # type: ignore[call-arg]
            model=model,                 # type: ignore[call-arg]
        )
    except TypeError:
        return ai_agent.call_assistant(settings.ai_api_key, messages, max_tokens=max_tokens)  # type: ignore[misc]

def _truncate_text(value: str, length: int) -> str:
    return value if len(value) <= length else value[:length] + "\n[... truncated ...]"

def _broadcast_story_summary(project_data: Dict[str, Any], limit: int = MAX_SUMMARY_LINES) -> str:
    items = []
    for b in project_data.get("broadcasts", []):
        title = b.get("title") or b.get("id") or "<unnamed>"
        first = next((ln.get("text", "").strip() for ln in b.get("lines", []) if ln.get("text")), "(no text yet)")
        items.append(f"{title}: {first[:120]}")
        if len(items) >= limit:
            break
    return "\n".join(items) if items else "No broadcasts available."

def _radio_data_excerpt() -> str:
    path = settings.radio_data_path
    if not path.exists():
        return "RadioData.xml not loaded yet."
    text = path.read_text(encoding="utf-8", errors="ignore")
    snippet = _truncate_text(text, MAX_RADIO_SNIPPET)
    return f"Loaded RadioData ({path.name}):\n{snippet}"

def _build_compact_context(project_data: Dict[str, Any], context: AppContext) -> str:
    voices = len(project_data.get("voices", []))
    channels = len(project_data.get("channels", []))
    broadcasts = len(project_data.get("broadcasts", []))

    ch = context.project.channels.get(getattr(context, "active_channel_id", None)) if hasattr(context, "project") else None
    bc = context.project.broadcasts.get(getattr(context, "active_broadcast_id", None)) if hasattr(context, "project") else None

    active_line = f"Active channel: {ch.name} ({getattr(ch, 'frequency', 0.0):.1f})" if ch else "Active channel: None"
    active_broadcast_line = f"Active broadcast: {(bc.title or bc.id)}" if bc else "Active broadcast: None"

    recent = _broadcast_story_summary(project_data, limit=5)
    panels = planning_tab.available_planning_panels()
    panel_line = (
        "Planning panels: " + ", ".join(panels)
        if panels
        else "Planning panels: none registered"
    )
    return "\n".join(
        [
            f"Project summary: voices={voices}, channels={channels}, broadcasts={broadcasts}",
            active_line,
            active_broadcast_line,
            "Recent broadcasts (top 5):",
            recent,
            panel_line,
        ]
    )

def _sanitize_response(text: str) -> str:
    out = text
    for phrase in BANNED_PHRASES:
        out = out.replace(phrase, "")
    lines = [ln.strip() for ln in out.splitlines()]
    return "\n".join([ln for ln in lines if ln])

# ---------- hue animation (assistant prose only) ----------

_anim_id_counter = itertools.count(1)

def _animate_tag_hue(widget: tk.Text, tag: str,
                     duration_ms: int = 6000, interval_ms: int = 40,
                     sat: float = 0.85, val: float = 1.0, start_h: float = 0.0) -> None:
    """
    Animate the foreground color of a specific tag through a hue cycle
    for `duration_ms`. Used only on assistant prose messages.
    """
    steps = max(1, duration_ms // interval_ms)
    state = {"i": 0}

    def tick():
        i = state["i"]
        h = (start_h + i / steps) % 1.0
        r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(h, sat, val)]
        widget.tag_config(tag, foreground=f"#{r:02x}{g:02x}{b:02x}")
        state["i"] = i + 1
        if state["i"] <= steps:
            widget.after(interval_ms, tick)

    tick()

# ---------------- UI tab ----------------

def make_tab(parent, context: AppContext):
    frame = ttk.Frame(parent)
    frame.configure(style="TFrame")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=3)
    frame.rowconfigure(1, weight=0)
    frame.rowconfigure(2, weight=0)

    history_frame = ttk.LabelFrame(frame, text="Assistant conversation")
    history_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=8)
    history_frame.columnconfigure(0, weight=1)
    history_frame.rowconfigure(0, weight=1)
    history_frame.rowconfigure(1, weight=0)

    conversation = tk.Text(
        history_frame,
        wrap="word",
        height=18,
        background="#050916",
        foreground=LIGHT_TEXT,
        insertbackground=ACCENT_CYAN,
        relief="flat",
        font=CODE_FONT,
    )
    conversation.grid(row=0, column=0, sticky="nsew")
    conv_scroll = ttk.Scrollbar(history_frame, command=conversation.yview)
    conv_scroll.grid(row=0, column=1, sticky="ns")
    conversation.configure(yscrollcommand=conv_scroll.set)
    conversation.tag_configure("assistant", foreground=ASSISTANT_COLOR)
    conversation.tag_configure("user", foreground=USER_COLOR)
    conversation.tag_configure("default", foreground=LIGHT_TEXT)
    conversation.tag_configure("query", foreground=ACCENT_CYAN)
    conversation.configure(state="normal")
    conversation.insert("1.0", f"{ASSISTANT_NAME} ready. Provide your prompt.")
    conversation.configure(state="disabled")

    def append_line(author, text, tag="default"):
        conversation.configure(state="normal")
        start_index = conversation.index("end-1c")
        conversation.insert("end", f"\n{author}: {text}", tag)
        end_index = conversation.index("end-1c")

        # Animate only assistant prose (not 'query' tool reports)
        if tag == "assistant":
            anim_tag = f"assistant_anim_{next(_anim_id_counter)}"
            conversation.tag_add(anim_tag, start_index, end_index)
            _animate_tag_hue(conversation, anim_tag)

        conversation.see("end")
        conversation.configure(state="disabled")

    control_frame = ttk.Frame(history_frame)
    control_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
    control_frame.columnconfigure(0, weight=1)
    control_frame.columnconfigure(1, weight=0)

    prompt_box = tk.Text(
        control_frame,
        height=6,
        wrap="word",
        font=TEXT_FONT,
        background="#050916",
        foreground=LIGHT_TEXT,
        insertbackground=ACCENT_CYAN,
        relief="flat",
    )
    prompt_box.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 4))
    prompt_box.focus_set()
    summary_var = tk.StringVar(value="Ready to assist.")
    summary_label = ttk.Label(frame, textvariable=summary_var, foreground=SECONDARY_TEXT)
    summary_label.grid(row=1, column=0, sticky="w", padx=12)
    planning_turns_var = tk.IntVar(value=1)

    def send_prompt(event=None):
        prompt = prompt_box.get("1.0", "end").strip()
        if not prompt:
            return
        append_line("You", prompt, "user")
        prompt_box.delete("1.0", "end")
        response, action_reports = run_assistant(context, prompt, planning_turns_var.get())
        append_line(ASSISTANT_NAME, response, "assistant")
        for report in action_reports:
            append_line(ASSISTANT_NAME, report, "query")
        summary_var.set(f"{ASSISTANT_NAME} responded to: {prompt[:50]}...")

    def _handle_enter(event):
        send_prompt()
        return "break"

    def _handle_shift_enter(event):
        prompt_box.insert("insert", "\n")
        return "break"

    prompt_box.bind("<Return>", _handle_enter)
    prompt_box.bind("<Shift-Return>", _handle_shift_enter)

    send_button = ttk.Button(control_frame, text="Send", command=send_prompt, style="Accent.TButton")
    send_button.grid(row=1, column=0, sticky="e")
    prompt_box.bind("<Control-Return>", _handle_enter)
    send_button.bind("<Return>", lambda event: send_prompt())
    turns_frame = ttk.Frame(control_frame)
    turns_frame.grid(row=1, column=1, sticky="w", padx=(6, 0))
    ttk.Label(turns_frame, text="Planning turns:").grid(row=0, column=0, sticky="w")
    ttk.Spinbox(
        turns_frame,
        from_=1,
        to=3,
        textvariable=planning_turns_var,
        width=3,
        justify="center",
        wrap=True,
    ).grid(row=0, column=1, sticky="w", padx=(4, 0))

    def insert_action_tag(tag: str):
        prompt_box.insert("end", f"{tag} ")
        prompt_box.focus_set()

    action_frame = ttk.Frame(control_frame)
    action_frame.grid(row=2, column=0, sticky="ew", pady=(4, 0))
    for col_idx, category in enumerate(ACTION_CATALOG):
        column_frame = ttk.LabelFrame(action_frame, text=category["title"])
        column_frame.grid(row=0, column=col_idx, sticky="nsew", padx=4, pady=2)
        action_frame.columnconfigure(col_idx, weight=1)
        description = category.get("description")
        row_offset = 0
        if description:
            ttk.Label(
                column_frame,
                text=description,
                foreground=SECONDARY_TEXT,
                wraplength=220,
            ).grid(row=0, column=0, sticky="w", padx=4, pady=(2, 4))
            row_offset = 1
        for row_idx, action in enumerate(category["actions"]):
            btn = ttk.Button(
                column_frame,
                text=action["label"],
                command=lambda t=action["tag"]: insert_action_tag(t),
                style="Accent.TButton",
            )
            btn.grid(row=row_offset + row_idx, column=0, sticky="ew", padx=2, pady=2)
            _ToolTip(btn, action["tooltip"])

    settings_frame = ttk.LabelFrame(frame, text="Session context")
    settings_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 12))
    settings_frame.columnconfigure(0, weight=1)

    notes_var = tk.StringVar(value="No recent changes.")
    ttk.Label(settings_frame, textvariable=notes_var).grid(row=0, column=0, sticky="w", padx=8, pady=4)
    ttk.LabelFrame(settings_frame, text="Context aware data").grid_forget()

    return frame

# ---------------- engine ----------------

def run_assistant(context: AppContext, prompt: str, planning_turns: int = 1) -> tuple[str, list[str]]:
    if not settings.ai_api_key:
        return "AI key missing; set it in Config tab.", []

    project_path = Path("assistant_project.srx")

    def _build_action_payload():
        project_io.save_project(context, project_path)
        project_data = json.loads(project_path.read_text(encoding="utf-8"))
        compact_context = _build_compact_context(project_data, context)
        project_snapshot = _truncate_text(json.dumps(project_data, indent=2), MAX_PROJECT_SNIPPET)
        radio_excerpt = _truncate_text(_radio_data_excerpt(), MAX_RADIO_SNIPPET)
        return project_data, compact_context, project_snapshot, radio_excerpt

    turns = max(1, min(3, planning_turns))
    summary_action_done = False
    actions_executed = False
    summaries: list[str] = []
    reports: list[str] = []
    action_notes: list[str] = []
    prompt_lower = prompt.lower()
    summary_keywords = ("summary", "summarize", "recap", "report", "review", "status")
    want_summary = any(keyword in prompt_lower for keyword in summary_keywords)

    last_project_data = None
    compact_context = ""
    project_snapshot = ""
    radio_excerpt = ""

    for _ in range(turns):
        project_data, compact_context, project_snapshot, radio_excerpt = _build_action_payload()
        last_project_data = project_data
        action_messages = [
            {
                "role": "system",
                "content": f"{SYSTEM_PERSONA}\n{ACTION_INSTRUCTIONS}",
            },
            {
                "role": "user",
                "content": (
                    f"{compact_context}\n"
                    f"Project snapshot (truncated):\n{project_snapshot}\n\n"
                    f"{radio_excerpt}\n\n"
                    f"User prompt: {prompt}"
                ),
            },
        ]

        try:
            action_reply = ai_agent.call_assistant(
                settings.ai_api_key,
                action_messages,
                max_tokens=ACTION_MAX_TOKENS,
                temperature=ACTION_TEMPERATURE,
                model=ACTION_MODEL,
            )
        except ai_agent.AssistantError as exc:
            return f"Assistant error: {exc}", action_notes

        actions = ai_actions.parse_actions(action_reply)
        if not actions:
            break

        actions_executed = True
        summary_action_done |= any(
            action.get("type") in ai_actions.SUMMARY_ACTION_TYPES for action in actions
        )
        new_summaries, new_reports = ai_actions.apply_actions(context, actions)
        summaries.extend(new_summaries)
        reports.extend(new_reports)
        action_notes.extend(new_summaries)
        action_notes.extend(new_reports)

    should_auto_summary = (not actions_executed or want_summary) and not summary_action_done
    if should_auto_summary:
        extra_summaries, extra_reports = ai_actions.apply_actions(
            context, [{"type": "summarize_station", "args": {}}]
        )
        if extra_summaries or extra_reports:
            summaries.extend(extra_summaries)
            reports.extend(extra_reports)
            action_notes.extend(extra_summaries)
            action_notes.extend(extra_reports)

    project_io.save_project(context, project_path)
    project_data = json.loads(project_path.read_text(encoding="utf-8"))
    compact_context = _build_compact_context(project_data, context)
    project_snapshot = _truncate_text(json.dumps(project_data, indent=2), MAX_PROJECT_SNIPPET)
    radio_excerpt = _truncate_text(_radio_data_excerpt(), MAX_RADIO_SNIPPET)

    def _format_entries(entries: list[str], default: str) -> str:
        if not entries:
            return default
        formatted: list[str] = []
        for entry in entries:
            stripped = entry.strip()
            if stripped.startswith("-"):
                formatted.append(stripped)
            else:
                formatted.append(f"- {stripped}")
        return "\n".join(formatted)

    action_summary_text = _format_entries(summaries, "- No tool actions were executed.")
    action_report_text = _format_entries(reports, "- No reports generated.")

    final_messages = [
        {
            "role": "system",
            "content": f"{SYSTEM_PERSONA}\n{PROSE_INSTRUCTIONS}",
        },
        {
            "role": "user",
            "content": (
                f"{compact_context}\n"
                f"Action summary:\n{action_summary_text}\n\n"
                f"Action reports:\n{action_report_text}\n\n"
                f"User prompt: {prompt}"
            ),
        },
    ]

    try:
        final_reply = ai_agent.call_assistant(
            settings.ai_api_key,
            final_messages,
            max_tokens=PROSE_MAX_TOKENS,
            temperature=PROSE_TEMPERATURE,
            model=PROSE_MODEL,
        )
    except ai_agent.AssistantError as exc:
        return f"Assistant error: {exc}", action_notes

    final_reply = _sanitize_response(final_reply)
    return final_reply, action_notes
