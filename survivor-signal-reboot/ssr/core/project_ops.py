from __future__ import annotations

from typing import Optional, Tuple

from .models import AppContext, Broadcast, ChannelScheduleEntry, Line


def create_broadcast(
    context: AppContext,
    title: str,
    description: str = "",
    channel_id: Optional[str] = None,
    day: int = 0,
    start: float = 0.0,
    end: float = 30.0,
    notify: bool = False,
) -> Tuple[Broadcast, Optional[ChannelScheduleEntry]]:
    broadcast = context.project.create_broadcast(title, description)
    schedule = None
    if channel_id:
        schedule = schedule_broadcast(context, channel_id, broadcast.id, day, start, end, notify=notify)
    if notify:
        context.notify_data_changed()
    return broadcast, schedule


def schedule_broadcast(
    context: AppContext,
    channel_id: str,
    broadcast_id: str,
    day: int = 0,
    start: float = 0.0,
    end: float = 30.0,
    notify: bool = False,
) -> ChannelScheduleEntry:
    channel = context.project.channels.get(channel_id)
    if not channel:
        raise ValueError(f"Channel {channel_id} not found.")
    entry = ChannelScheduleEntry(
        broadcast_id=broadcast_id,
        day=day,
        start=start,
        end=end,
    )
    channel.schedule.append(entry)
    if notify:
        context.notify_data_changed()
    return entry


def reschedule_broadcast(
    context: AppContext,
    channel_id: str,
    broadcast_id: str,
    day: int,
    start: float,
    end: float,
    notify: bool = False,
) -> ChannelScheduleEntry:
    channel = context.project.channels.get(channel_id)
    if not channel:
        raise ValueError(f"Channel {channel_id} not found.")
    entry = next(
        (entry for entry in channel.schedule if entry.broadcast_id == broadcast_id), None
    )
    if not entry:
        raise ValueError(f"Broadcast {broadcast_id} not scheduled on channel {channel_id}.")
    entry.day = day
    entry.start = start
    entry.end = end
    if notify:
        context.notify_data_changed()
    return entry


def add_line_to_broadcast(
    context: AppContext,
    broadcast_id: str,
    text: str,
    voice_id: Optional[str] = None,
    character_id: Optional[str] = None,
    duration: Optional[float] = None,
    moodle: Optional[str] = None,
    effects: Optional[list[str]] = None,
    sound_file: Optional[str] = None,
    notify: bool = False,
) -> Line:
    broadcast = context.project.broadcasts.get(broadcast_id)
    if not broadcast:
        raise ValueError(f"Broadcast {broadcast_id} not found.")
    line = Line(
        text=text,
        voice_id=voice_id,
        character_id=character_id,
        duration=duration,
        moodle=moodle,
        effects=list(effects) if effects else [],
        sound_file=sound_file,
    )
    broadcast.lines.append(line)
    if notify:
        context.notify_data_changed()
    return line
