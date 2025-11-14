import colorsys
from typing import Iterable, Optional, Sequence


def format_time(minutes: float) -> str:
    total = int(minutes)
    hours = total // 60
    mins = total % 60
    return f"{hours:02}:{mins:02}"


def fallback_title(broadcast, channel_name: Optional[str] = None) -> str:
    title = (broadcast.title or "").strip()
    if title:
        return title
    start = format_time(broadcast.start_offset)
    end_minutes = broadcast.end_offset if broadcast.end_offset is not None else broadcast.start_offset
    end = format_time(end_minutes)
    channel_label = channel_name or "Channel"
    return f"{channel_label} – Day {broadcast.day} {start}-{end}"


def lines_as_text(lines: Iterable, project) -> str:
    rows = []
    for idx, line in enumerate(lines, start=1):
        voice = project.voices.get(line.voice_id)
        name = voice.name if voice else "Unknown"
        rows.append(f"{idx:02d}. {name}: {line.text}")
    return "\n".join(rows)


def rainbow_color(position: int, total: int) -> str:
    if total <= 1:
        hue = 0.0
    else:
        hue = (position / (total - 1)) * 0.75
    r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 0.95)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def channel_color_map(channel_ids: Sequence[str]) -> dict[str, str]:
    total = len(channel_ids)
    if total == 0:
        return {}
    total_arg = max(total, 1)
    return {channel_id: rainbow_color(idx, total_arg) for idx, channel_id in enumerate(channel_ids)}
