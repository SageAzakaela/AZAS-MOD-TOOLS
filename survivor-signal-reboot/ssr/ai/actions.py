from __future__ import annotations

import json
from typing import Any, Callable, Dict, Iterable, List, Tuple
from collections import defaultdict
from uuid import uuid4

from ..core import AppContext, project_ops
from .. import search as search_utils
from ..core.models import Voice, Broadcast, Channel, ChannelScheduleEntry, RecordedMediaLine
from ..ui.tabs import planning_tab


DEFAULT_LINE_DURATION = 180.0  # three minutes in seconds


def _parse_duration(value: Any, fallback: float | None = None) -> float | None:
    if value is None:
        return fallback
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return fallback
        if ":" in text:
            parts = [part.strip() for part in text.split(":") if part.strip()]
            try:
                numbers = [float(part) for part in parts]
            except ValueError:
                return fallback
            if len(numbers) == 1:
                return numbers[0]
            if len(numbers) == 2:
                return numbers[0] * 60 + numbers[1]
            if len(numbers) == 3:
                return numbers[0] * 3600 + numbers[1] * 60 + numbers[2]
            return fallback
        try:
            return float(text)
        except ValueError:
            return fallback
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


SUMMARY_ACTION_TYPES = {"summarize_station", "summarize_channel", "summarize_characters"}

DEFAULT_LINE_DURATION = 180.0


def _parse_duration(value: Any, fallback: float | None = None) -> float | None:
    if value is None:
        return fallback
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return fallback
        if ":" in text:
            parts = [part.strip() for part in text.split(":") if part.strip()]
            try:
                numbers = [float(part) for part in parts]
            except ValueError:
                return fallback
            if len(numbers) == 1:
                return numbers[0]
            if len(numbers) == 2:
                return numbers[0] * 60 + numbers[1]
            if len(numbers) == 3:
                return numbers[0] * 3600 + numbers[1] * 60 + numbers[2]
            return fallback
        try:
            return float(text)
        except ValueError:
            return fallback
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _format_bullets(lines: List[str]) -> str:
    return "\n".join(f"- {line}" for line in lines if line)


def _channel_schedule_summary(channel: Channel) -> str:
    if not channel.schedule:
        return "No scheduled broadcasts."
    entries = sorted(channel.schedule, key=lambda entry: (entry.day, entry.start))
    return "; ".join(f"Day {entry.day} {entry.start:.0f}-{entry.end:.0f}" for entry in entries)


def _line_examples(broadcast: Broadcast, limit: int = 3) -> List[str]:
    examples: List[str] = []
    for line in broadcast.lines:
        if line.text:
            examples.append(line.text)
            if len(examples) >= limit:
                break
    return examples


def _resolve_channel_id(context: AppContext, data: Dict[str, Any]) -> str | None:
    channel_id = data.get("channel_id")
    if channel_id and channel_id in context.project.channels:
        return channel_id
    channel_name = data.get("channel_name") or data.get("channel")
    if channel_name:
        for cid, channel in context.project.channels.items():
            if channel.name.lower() == str(channel_name).lower():
                return cid
    return context.active_channel_id


def _resolve_broadcast_id(context: AppContext, data: Dict[str, Any]) -> str | None:
    broadcast_id = data.get("broadcast_id")
    if broadcast_id and broadcast_id in context.project.broadcasts:
        return broadcast_id
    title_hint = (data.get("broadcast_title") or data.get("broadcast_name") or data.get("broadcast"))
    if title_hint:
        normalized = str(title_hint).strip().lower()
        for bid, broadcast in context.project.broadcasts.items():
            title = (broadcast.title or "").strip().lower()
            if title == normalized or normalized in title:
                return bid
    return context.active_broadcast_id


def _split_line_texts(text: str | None) -> list[str]:
    if not text:
        return []
    segments = [segment.strip() for segment in text.splitlines()]
    nonempty = [segment for segment in segments if segment]
    if nonempty:
        return nonempty
    trimmed = text.strip()
    return [trimmed] if trimmed else []


def parse_actions(response: str) -> List[Dict[str, Any]]:
    start = response.find("{")
    if start == -1:
        return []
    try:
        payload = json.loads(response[start:])
    except json.JSONDecodeError:
        return []
    if isinstance(payload, dict):
        return payload.get("actions", [])
    return []


def apply_actions(
    context: AppContext, actions: Iterable[Dict[str, Any]]
) -> tuple[list[str], list[str]]:
    summaries: List[str] = []
    reports: List[str] = []
    for action in actions:
        kind = action.get("type")
        handler = ACTION_HANDLERS.get(kind)
        payload = action.get("args", {})
        if not handler:
            summaries.append(f"Unknown action type: {kind}")
            continue
        try:
            summary, report = handler(context, payload)
        except Exception as exc:
            summaries.append(f"Action {kind} failed: {exc}")
            continue
        if summary:
            summaries.append(summary)
        if report:
            reports.append(report)
    if summaries:
        context.notify_data_changed()
    return summaries, reports


ActionHandler = Callable[[AppContext, Dict[str, Any]], Tuple[str, str]]


def add_voice(context: AppContext, data: Dict[str, Any]) -> Tuple[str, str]:
    vid = data.get("id") or uuid4().hex
    name = data.get("name", f"Voice {len(context.project.voices)+1}")
    color = data.get("color", "#ffffff")
    context.project.voices[vid] = Voice(id=vid, name=name, color=color)
    return f"Added voice {name}.", ""


def add_channel(context: AppContext, data: Dict[str, Any]) -> Tuple[str, str]:
    cid = data.get("id") or f"channel-{len(context.project.channels)+1}"
    name = data.get("name", f"Channel {cid}")
    freq = float(data.get("frequency", 100.0))
    category = data.get("category", "radio")
    channel = Channel(id=cid, name=name, frequency=freq, category=category)
    context.project.channels[cid] = channel
    if not context.active_channel_id:
        context.active_channel_id = cid
    return f"Added channel {name} ({freq}).", ""


def add_broadcast(context: AppContext, data: Dict[str, Any]) -> Tuple[str, str]:
    title = data.get("title", "New Broadcast")
    channel_id = _resolve_channel_id(context, data)
    if not channel_id:
        return "add_broadcast failed: channel required.", ""
    day = int(data.get("day", 0))
    start = float(data.get("start", 0.0))
    end = float(data.get("end", 60.0))
    try:
        broadcast, entry = project_ops.create_broadcast(
            context,
            title,
            data.get("description", ""),
            channel_id=channel_id,
            day=day,
            start=start,
            end=end,
            notify=False,
        )
    except ValueError as exc:
        return f"create_broadcast failed: {exc}", ""
    summary = f"Created broadcast {broadcast.id}."
    report = ""
    if entry and channel_id:
        channel = context.project.channels.get(channel_id)
        report = (
            f"Scheduled on {channel.name if channel else channel_id} "
            f"Day {entry.day} {entry.start:.0f}-{entry.end:.0f}"
        )
    return summary, report


def add_line(context: AppContext, data: Dict[str, Any]) -> Tuple[str, str]:
    broadcast_id = _resolve_broadcast_id(context, data)
    broadcast = context.project.broadcasts.get(broadcast_id)
    if not broadcast:
        return "Broadcast not found.", ""
    raw_text = data.get("text", "Generated line")
    line_texts = _split_line_texts(raw_text)
    if not line_texts:
        return "add_line failed: broadcast line text required.", ""
    voice_id = data.get("voice_id")
    moodle = data.get("moodle")
    effects = data.get("effects")
    sound_file = data.get("sound_file")
    character_id = data.get("character_id")
    duration = _parse_duration(data.get("duration"), DEFAULT_LINE_DURATION)
    try:
        for line_text in line_texts:
            project_ops.add_line_to_broadcast(
                context,
                broadcast_id,
                line_text,
                voice_id=voice_id,
                character_id=character_id,
                moodle=moodle,
                effects=effects,
                sound_file=sound_file,
                duration=duration,
                notify=False,
            )
    except ValueError as exc:
        return f"add_line failed: {exc}", ""
    line_count = len(line_texts)
    summary = (
        f"Added {line_count} line{'s' if line_count != 1 else ''} to {broadcast.title}."
    )
    return summary, ""


def _voice_usage(context: AppContext) -> Dict[str, Dict[str, Any]]:
    usage: Dict[str, Dict[str, Any]] = {}
    for broadcast in context.project.broadcasts.values():
        for line in broadcast.lines:
            voice_id = line.voice_id or "unknown"
            entry = usage.setdefault(
                voice_id,
                {"lines": 0, "broadcasts": set(), "sample": line.text or "", "first_line": line.text or ""},
            )
            entry["lines"] += 1
            entry["broadcasts"].add(broadcast.id)
            if not entry["sample"] and line.text:
                entry["sample"] = line.text
    return usage


def summarize_station(context: AppContext, data: Dict[str, Any]) -> Tuple[str, str]:
    channels = list(context.project.channels.values())
    broadcasts = list(context.project.broadcasts.values())
    total_slots = sum(len(channel.schedule) for channel in channels)
    scheduled_ids = {entry.broadcast_id for channel in channels for entry in channel.schedule}
    unscheduled = [b for b in broadcasts if b.id not in scheduled_ids]
    voice_usage = _voice_usage(context)
    top_voices = sorted(
        (
            (voice_id, stats)
            for voice_id, stats in voice_usage.items()
            if voice_id in context.project.voices
        ),
        key=lambda pair: pair[1]["lines"],
        reverse=True,
    )[:3]
    top_broadcasts = sorted(broadcasts, key=lambda b: len(b.lines), reverse=True)[:3]

    summary_lines: List[str] = [
        f"{len(channels)} channels, {len(broadcasts)} broadcasts ({total_slots} scheduled slots).",
        f"{len(unscheduled)} unscheduled broadcast{'s' if len(unscheduled) != 1 else ''}.",
        (
            "Top voices: "
            + ", ".join(
                context.project.voices.get(voice_id, Voice(id=voice_id, name=voice_id)).name
                + f" ({stats['lines']} lines)"
                for voice_id, stats in top_voices
            )
            if top_voices
            else "No voice lines recorded yet."
        ),
        (
            "Standout broadcasts: "
            + ", ".join(
                f"{broadcast.title or broadcast.id} ({len(broadcast.lines)} lines)"
                for broadcast in top_broadcasts
            )
        ),
    ]
    gaps = ", ".join(broadcast.title or broadcast.id for broadcast in unscheduled[:3])
    if gaps:
        summary_lines.append(f"Immediate gap(s): {gaps}.")

    report_lines: List[str] = [
        f"Scheduled slots per channel:",
    ]
    for channel in sorted(channels, key=lambda c: c.name):
        report_lines.append(f"{channel.name}: {len(channel.schedule)} slot(s) - {_channel_schedule_summary(channel)}")
    if unscheduled:
        report_lines.append("Unscheduled broadcasts: " + ", ".join(b.title or b.id for b in unscheduled))

    summary = _format_bullets(summary_lines)
    report = "\n".join(report_lines)
    planning_tab.set_planning_note_content("Notes", summary)
    return summary, report


def summarize_channel(context: AppContext, data: Dict[str, Any]) -> Tuple[str, str]:
    channel_id = _resolve_channel_id(context, data)
    channel = context.project.channels.get(channel_id) if channel_id else None
    if not channel:
        return "summarize_channel failed: channel not found.", ""
    broadcasts = [
        context.project.broadcasts.get(entry.broadcast_id)
        for entry in channel.schedule
        if context.project.broadcasts.get(entry.broadcast_id)
    ]
    total_lines = sum(len(broadcast.lines) for broadcast in broadcasts if broadcast)
    summary_lines = [
        f"Channel {channel.name} ({channel.frequency:.1f} MHz, {channel.category}).",
        f"{len(broadcasts)} scheduled broadcast{'s' if len(broadcasts) != 1 else ''}.",
        f"{total_lines} lines across that schedule.",
    ]
    if broadcasts:
        first_broadcast = broadcasts[0]
        summary_lines.append(f"Example broadcast: {first_broadcast.title or first_broadcast.id}.")
    report_lines = [
        f"{channel.name} schedule: {_channel_schedule_summary(channel)}",
        "Broadcast details:",
    ]
    for broadcast in broadcasts:
        example_lines = _line_examples(broadcast, limit=1)
        sample = example_lines[0] if example_lines else "(no lines)"
        report_lines.append(
            f"{broadcast.title or broadcast.id}: {len(broadcast.lines)} lines; sample: {sample}."
        )
    summary = _format_bullets(summary_lines)
    return summary, "\n".join(report_lines)


def summarize_characters(context: AppContext, data: Dict[str, Any]) -> Tuple[str, str]:
    usage = _voice_usage(context)
    if not usage:
        return "No character lines available to summarize.", ""
    summary_lines: List[str] = []
    report_lines: List[str] = ["Character heat map:"]
    for voice_id, stats in sorted(usage.items(), key=lambda item: item[1]["lines"], reverse=True):
        voice = context.project.voices.get(voice_id)
        name = voice.name if voice else voice_id
        broadcasts = stats["broadcasts"]
        example = stats["sample"] or "(no sample)"
        summary_lines.append(f"{name}: {stats['lines']} lines across {len(broadcasts)} broadcast(s).")
        report_lines.append(f"{name}: sample line \"{example}\"; broadcasts: {', '.join(sorted(broadcasts))}.")

    summary = _format_bullets(summary_lines)
    return summary, "\n".join(report_lines)


def schedule_broadcast_action(context: AppContext, data: Dict[str, Any]) -> Tuple[str, str]:
    channel_id = data.get("channel_id")
    broadcast_id = data.get("broadcast_id")
    if not channel_id or not broadcast_id:
        return "schedule_broadcast failed: channel_id and broadcast_id required.", ""
    try:
        entry = project_ops.schedule_broadcast(
            context,
            channel_id,
            broadcast_id,
            day=int(data.get("day", 0)),
            start=float(data.get("start", 0.0)),
            end=float(data.get("end", 60.0)),
            notify=False,
        )
    except ValueError as exc:
        return f"schedule_broadcast failed: {exc}", ""
    return (
        f"Scheduled broadcast {broadcast_id} on channel {channel_id}.",
        f"Scheduled on channel {channel_id} Day {entry.day} {entry.start:.0f}-{entry.end:.0f}",
    )


def reschedule_broadcast_action(context: AppContext, data: Dict[str, Any]) -> Tuple[str, str]:
    channel_id = data.get("channel_id")
    broadcast_id = data.get("broadcast_id")
    if not channel_id or not broadcast_id:
        return "reschedule_broadcast failed: channel_id and broadcast_id required.", ""
    try:
        entry = project_ops.reschedule_broadcast(
            context,
            channel_id,
            broadcast_id,
            day=int(data.get("day", 0)),
            start=float(data.get("start", 0.0)),
            end=float(data.get("end", 60.0)),
            notify=False,
        )
    except ValueError as exc:
        return f"reschedule_broadcast failed: {exc}", ""
    return (
        f"Rescheduled broadcast {broadcast_id}.",
        f"Now Day {entry.day} {entry.start:.0f}-{entry.end:.0f} on channel {channel_id}",
    )


def query_broadcasts(context: AppContext, data: Dict[str, Any]) -> tuple[str, str]:
    query = (data.get("query") or "").strip().lower()
    channel_filter = data.get("channel_id")
    max_results = int(data.get("limit", 5))
    schedule_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for channel in context.project.channels.values():
        for entry in channel.schedule:
            schedule_map[entry.broadcast_id].append(
                {
                    "channel_id": channel.id,
                    "channel_name": channel.name,
                    "day": entry.day,
                    "start": entry.start,
                    "end": entry.end,
                }
            )
    matches = []
    for broadcast in context.project.broadcasts.values():
        if channel_filter:
            entries = schedule_map.get(broadcast.id, [])
            if not any(entry["channel_id"] == channel_filter for entry in entries):
                continue
        text_blob = " ".join(
            filter(
                None,
                [broadcast.title, broadcast.description]
                + [line.text for line in broadcast.lines if line.text],
            )
        ).lower()
        if query and query not in text_blob:
            continue
        lines = schedule_map.get(broadcast.id, [])
        schedule_desc = (
            "; ".join(
                f"{entry['channel_name']} Day {entry['day']} {entry['start']:.0f}-{entry['end']:.0f}"
                for entry in lines
            )
            if lines
            else "unscheduled"
        )
        first_line = (
            next((line.text for line in broadcast.lines if line.text), "(no lines yet)")
            if broadcast.lines
            else "(no lines yet)"
        )
        matches.append(
            f"{broadcast.title or broadcast.id} (id={broadcast.id}): {first_line[:120]} ({schedule_desc})"
        )
        if len(matches) >= max_results:
            break
    report_parts = [f"Queried broadcasts for '{query or 'any'}'"]
    if channel_filter:
        report_parts.append(f"in channel {channel_filter}")
    report = " ".join(report_parts)
    if not matches:
        return (
            "No broadcasts matched that query.",
            report + " (no results)",
        )
    return f"Found broadcasts:\n" + "\n".join(matches), report


def query_channels(context: AppContext, data: Dict[str, Any]) -> tuple[str, str]:
    channel_lines = []
    for channel in context.project.channels.values():
        channel_lines.append(
            f"{channel.name} (id={channel.id}) freq={channel.frequency:.1f} category={channel.category}"
        )
    report = f"Queried channels, found {len(channel_lines)}."
    if not channel_lines:
        return "No channels available.", report
    return "Channels:\n" + "\n".join(channel_lines), report


def search_project_action(context: AppContext, data: Dict[str, Any]) -> tuple[str, str]:
    term = (data.get("term") or "").strip()
    if not term:
        return "search_project failed: term required.", ""
    try:
        limit = max(1, min(12, int(data.get("limit", 5))))
    except (TypeError, ValueError):
        limit = 5
    results = search_utils.search_project(context, term, limit=limit)
    if not results:
        return f"No results for '{term}'.", ""
    summary = f"Found {len(results)} result{'s' if len(results) != 1 else ''} for '{term}'."
    report_lines = []
    for item in results[:limit]:
        report_lines.append(f"{item.source} - {item.title}: {item.snippet}")
    return summary, "\n".join(report_lines)


def list_planning_panels(context: AppContext, data: Dict[str, Any]) -> tuple[str, str]:
    panels = planning_tab.available_planning_panels()
    if not panels:
        return "No planning panels registered yet.", ""
    return "Planning panels:\n" + "\n".join(panels), f"{len(panels)} panels available."


def update_broadcast(context: AppContext, data: Dict[str, Any]) -> Tuple[str, str]:
    broadcast_id = _resolve_broadcast_id(context, data)
    if not broadcast_id:
        return "update_broadcast failed: broadcast_id required.", ""
    broadcast = context.project.broadcasts.get(broadcast_id)
    if not broadcast:
        return f"Broadcast {broadcast_id} not found.", ""
    if title := data.get("title"):
        broadcast.title = title
    if description := data.get("description"):
        broadcast.description = description
    if day := data.get("day"):
        broadcast.day = int(day)
    for line_update in data.get("lines", []):
        guid = line_update.get("guid")
        if not guid:
            continue
        line = next((l for l in broadcast.lines if l.guid == guid), None)
        if not line:
            continue
        if text := line_update.get("text"):
            line.text = text
        if voice_id := line_update.get("voice_id"):
            line.voice_id = voice_id
        if effects := line_update.get("effects"):
            line.effects = list(effects)
    return f"Updated broadcast {broadcast.title or broadcast.id}.", ""


def update_channel(context: AppContext, data: Dict[str, Any]) -> Tuple[str, str]:
    channel_id = data.get("channel_id")
    if not channel_id:
        return "update_channel failed: channel_id required.", ""
    channel = context.project.channels.get(channel_id)
    if not channel:
        return f"Channel {channel_id} not found.", ""
    if name := data.get("name"):
        channel.name = name
    if freq := data.get("frequency"):
        channel.frequency = float(freq)
    if category := data.get("category"):
        channel.category = category
    return f"Updated channel {channel.name}.", ""


def update_line(context: AppContext, data: Dict[str, Any]) -> Tuple[str, str]:
    line_guid = data.get("line_guid")
    if not line_guid:
        return "update_line failed: line_guid required.", ""
    target_line = None
    for broadcast in context.project.broadcasts.values():
        for line in broadcast.lines:
            if line.guid == line_guid:
                target_line = line
                break
        if target_line:
            break
    if not target_line:
        return f"Line {line_guid} not found.", ""
    if text := data.get("text"):
        target_line.text = text
    if voice_id := data.get("voice_id"):
        target_line.voice_id = voice_id
    if effects := data.get("effects"):
        target_line.effects = list(effects)
    if "duration" in data:
        target_line.duration = _parse_duration(data.get("duration"), target_line.duration)
    return f"Updated line {line_guid}.", ""


def set_active_channel(context: AppContext, data: Dict[str, Any]) -> Tuple[str, str]:
    channel_id = _resolve_channel_id(context, data)
    if not channel_id or channel_id not in context.project.channels:
        return "set_active_channel failed: invalid channel specification.", ""
    context.active_channel_id = channel_id
    return f"Active channel set to {channel_id}.", ""


def stagger_broadcasts(context: AppContext, data: Dict[str, Any]) -> Tuple[str, str]:
    channel_id = _resolve_channel_id(context, data)
    if not channel_id:
        return "stagger_broadcasts failed: channel required.", ""
    broadcast_ids = data.get("broadcast_ids") or []
    if not broadcast_ids:
        return "stagger_broadcasts failed: broadcast_ids required.", ""
    day = int(data.get("day", 0))
    start = float(data.get("start", 0.0))
    gap = float(data.get("gap", 3600.0))
    duration = float(data.get("duration", 3600.0))
    for idx, bid in enumerate(broadcast_ids):
        if bid not in context.project.broadcasts:
            return f"stagger_broadcasts failed: broadcast {bid} not found.", ""
        entry_start = start + idx * gap
        entry_end = entry_start + duration
        try:
            project_ops.reschedule_broadcast(
                context,
                channel_id,
                bid,
                day=day,
                start=entry_start,
                end=entry_end,
                notify=False,
            )
        except ValueError as exc:
            return f"stagger_broadcasts failed: {exc}", ""
    return (
        f"Staggered {len(broadcast_ids)} broadcasts on channel {channel_id}.",
        f"Slots start at {start:.0f}s with {gap:.0f}s gaps.",
    )


def write_planning_note(context: AppContext, data: Dict[str, Any]) -> Tuple[str, str]:
    panel = data.get("panel")
    content = data.get("content", "")
    if not panel:
        return "write_planning_note failed: panel required.", ""
    if not planning_tab.set_planning_note_content(panel, content):
        return f"Panel '{panel}' not found.", ""
    return f"Wrote note in {panel}.", ""


def append_planning_note(context: AppContext, data: Dict[str, Any]) -> Tuple[str, str]:
    panel = data.get("panel")
    content = data.get("content", "")
    if not panel:
        return "append_planning_note failed: panel required.", ""
    if not planning_tab.append_planning_note_content(panel, content):
        return f"Panel '{panel}' not found.", ""
    return f"Appended note to {panel}.", ""


ACTION_HANDLERS: Dict[str, ActionHandler] = {
    "add_voice": add_voice,
    "add_channel": add_channel,
    "add_broadcast": add_broadcast,
    "schedule_broadcast": schedule_broadcast_action,
    "reschedule_broadcast": reschedule_broadcast_action,
    "add_line": add_line,
    "query_broadcasts": query_broadcasts,
    "query_channels": query_channels,
    "list_planning_panels": list_planning_panels,
    "search_project": search_project_action,
    "summary": lambda context, data: (data.get("text", "Assistant summary completed."), ""),
    "update_broadcast": update_broadcast,
    "update_channel": update_channel,
    "update_line": update_line,
    "set_active_channel": set_active_channel,
    "stagger_broadcasts": stagger_broadcasts,
    "write_planning_note": write_planning_note,
    "append_planning_note": append_planning_note,
    "summarize_station": summarize_station,
    "summarize_channel": summarize_channel,
    "summarize_characters": summarize_characters,
}
