from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from .core import AppContext


@dataclass
class SearchResult:
    source: str
    title: str
    snippet: str
    detail: str
    reference_id: Optional[str] = None


_TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _clean_text(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def _tokens(value: str | None) -> List[str]:
    if not value:
        return []
    return [token.lower() for token in _TOKEN_PATTERN.findall(value)]


def _normalize_term(term: str) -> List[str]:
    return [token for token in _tokens(term) if token]


def _matches(tokens: Iterable[str], value: str | None) -> bool:
    text = (value or "").lower()
    cleaned = _clean_text(value)
    return all(
        bool(token) and (token in text or token in cleaned)
        for token in tokens
    )


def _snippet(value: str | None, length: int = 180) -> str:
    if not value:
        return ""
    text = " ".join(value.replace("\n", " ").split())
    if len(text) <= length:
        return text
    truncated = text[: max(length - 3, 0)]
    return f"{truncated}..."


def _schedule_map(context: AppContext) -> Dict[str, List[str]]:
    schedule: Dict[str, List[str]] = defaultdict(list)
    for channel in context.project.channels.values():
        for entry in channel.schedule:
            schedule[entry.broadcast_id].append(
                f"{channel.name} day {entry.day} {entry.start:.0f}-{entry.end:.0f}"
            )
    return schedule


def _combine_fields(*values: str | None) -> str:
    return " ".join(value or "" for value in values if value)


def _metadata_text(metadata: Dict[str, str]) -> str:
    return " ".join(f"{key} {value}" for key, value in metadata.items())


def search_project(context: AppContext, term: str, limit: int = 30) -> List[SearchResult]:
    tokens = _normalize_term(term)
    if not tokens:
        return []

    schedule_map = _schedule_map(context)
    results: List[SearchResult] = []

    def maybe_append(result: SearchResult) -> None:
        results.append(result)

    for voice in context.project.voices.values():
        metadata_text = _metadata_text(voice.metadata)
        if _matches(
            tokens,
            _combine_fields(
                voice.id,
                voice.name,
                voice.notes,
                voice.channel_hint,
                metadata_text,
            ),
        ):
            detail = (
                f"Voice {voice.name} ({voice.id})\nNotes: {voice.notes or 'None'}\n"
                f"Channel hint: {voice.channel_hint or 'none'}"
            )
            maybe_append(
                SearchResult(
                    source="Voice",
                    title=voice.name,
                    snippet=_snippet(voice.notes or voice.name),
                    detail=detail,
                    reference_id=voice.id,
                )
            )

    for channel in context.project.channels.values():
        if _matches(
            tokens,
            _combine_fields(channel.name, channel.category, channel.default_advert_group),
        ):
            detail = (
                f"{channel.name} ({channel.id})\n"
                f"Category: {channel.category or 'radio'}\n"
                f"Frequency: {channel.frequency:.1f} MHz"
            )
            if channel.schedule:
                detail += "\nScheduled: " + "; ".join(
                    f"day {entry.day} {entry.start:.0f}-{entry.end:.0f}" for entry in channel.schedule
                )
            maybe_append(
                SearchResult(
                    source="Channel",
                    title=f"{channel.name} ({channel.frequency:.1f})",
                    snippet=_snippet(channel.category),
                    detail=detail,
                    reference_id=channel.id,
                )
            )

    for broadcast in context.project.broadcasts.values():
        combined_text = _combine_fields(
            broadcast.title,
            broadcast.description,
            " ".join(line.text for line in broadcast.lines if line.text),
            _metadata_text(broadcast.metadata),
        )
        if _matches(tokens, combined_text):
            schedule_desc = schedule_map.get(broadcast.id, [])
            schedule_text = "; ".join(schedule_desc) if schedule_desc else "unscheduled"
            first_line = next((line.text for line in broadcast.lines if line.text), "(no lines yet)")
            detail_lines = [
                f"Broadcast {broadcast.title or broadcast.id} ({broadcast.id})",
                f"Description: {broadcast.description or 'none'}",
                f"Schedule: {schedule_text}",
                f"First line: {first_line}",
            ]
            maybe_append(
                SearchResult(
                    source="Broadcast",
                    title=broadcast.title or broadcast.id,
                    snippet=_snippet(first_line),
                    detail="\n".join(detail_lines),
                    reference_id=broadcast.id,
                )
            )

    for entry in context.project.recorded_media.values():
        combined = _combine_fields(entry.title, entry.author, entry.category)
        if _matches(tokens, combined):
            line_texts = " ".join(line.text for line in entry.lines if line.text)
            detail = (
                f"{entry.title} by {entry.author}\nCategory: {entry.category}\n"
                f"Lines: {len(entry.lines)}"
            )
            maybe_append(
                SearchResult(
                    source="Recorded Media",
                    title=entry.title,
                    snippet=_snippet(line_texts, length=120),
                    detail=detail,
                    reference_id=entry.id,
                )
            )

    priority = {"Broadcast": 0, "Channel": 1, "Voice": 2, "Recorded Media": 3}

    results.sort(key=lambda res: (priority.get(res.source, 99), res.title.lower()))
    return results[:limit]
