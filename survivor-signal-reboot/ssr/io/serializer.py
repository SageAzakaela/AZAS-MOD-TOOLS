from dataclasses import asdict
from typing import Dict, Any

from ..core import AppContext
from ..core.models import (
    CDCompilation,
    ChannelScheduleEntry,
    Character,
    Group,
    RecordedMediaEntry,
    RecordedMediaLine,
    VHSTape,
    Voice,
)


def serialize_voice(voice: "Voice") -> Dict[str, Any]:
    return {
        "id": voice.id,
        "name": voice.name,
        "color": voice.color,
        "notes": voice.notes,
        "groups": list(voice.groups),
        "channel_hint": voice.channel_hint,
        "metadata": dict(voice.metadata),
    }


def serialize_character(character: "Character") -> Dict[str, Any]:
    return {
        "id": character.id,
        "name": character.name,
        "notes": character.notes,
        "voice_ids": list(character.voice_ids),
        "metadata": dict(character.metadata),
    }


def serialize_group(group: "Group") -> Dict[str, Any]:
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "character_ids": list(group.character_ids),
    }


def serialize_line(line: "Line") -> Dict[str, Any]:
    return {
        "text": line.text,
        "voice": line.voice_id,
        "duration": line.duration,
        "moodle": line.moodle,
        "effects": list(line.effects),
        "guid": line.guid,
    }


def serialize_broadcast(broadcast: "Broadcast") -> Dict[str, Any]:
    return {
        "id": broadcast.id,
        "title": broadcast.title,
        "description": broadcast.description,
        "lines": [serialize_line(line) for line in broadcast.lines],
        "start_offset": broadcast.start_offset,
        "effects": list(broadcast.effects),
        "adverts": list(broadcast.adverts),
    }


def serialize_channel(channel: "Channel") -> Dict[str, Any]:
    return {
        "id": channel.id,
        "name": channel.name,
        "frequency": channel.frequency,
        "category": channel.category,
        "schedule": [serialize_schedule_entry(entry) for entry in channel.schedule],
        "auto_adverts": channel.auto_adverts,
        "default_advert_group": channel.default_advert_group,
        "start_script": channel.start_script,
    }


def serialize_vhs(tape: VHSTape) -> Dict[str, Any]:
    return {
        "id": tape.id,
        "name": tape.name,
        "description": tape.description,
        "broadcast_ids": list(tape.broadcast_ids),
        "spawn_weight": tape.spawn_weight,
        "guid": tape.guid,
    }


def serialize_cd(cd: CDCompilation) -> Dict[str, Any]:
    return {
        "id": cd.id,
        "name": cd.name,
        "curator": cd.curator,
        "genre": cd.genre,
        "track_ids": list(cd.track_ids),
        "guid": cd.guid,
    }


def serialize_recorded_line(line: RecordedMediaLine) -> Dict[str, Any]:
    return {
        "text": line.text,
        "r": line.r,
        "g": line.g,
        "b": line.b,
        "codes": line.codes,
    }


def serialize_recorded_media(entry: RecordedMediaEntry) -> Dict[str, Any]:
    return {
        "id": entry.id,
        "title": entry.title,
        "author": entry.author,
        "category": entry.category,
        "spawn": entry.spawn,
        "lines": [serialize_recorded_line(line) for line in entry.lines],
    }


def serialize_schedule_entry(entry: ChannelScheduleEntry) -> Dict[str, Any]:
    return {
        "broadcast_id": entry.broadcast_id,
        "day": entry.day,
        "start": entry.start,
        "end": entry.end,
    }


def serialize_context(context: AppContext) -> Dict[str, Any]:
    project = context.project
    return {
        "voices": [serialize_voice(v) for v in project.voices.values()],
        "characters": [serialize_character(c) for c in project.characters.values()],
        "groups": [serialize_group(g) for g in project.groups.values()],
        "broadcasts": [serialize_broadcast(b) for b in project.broadcasts.values()],
        "channels": [serialize_channel(c) for c in project.channels.values()],
        "vhs_tapes": [serialize_vhs(t) for t in project.vhs_tapes.values()],
        "cds": [serialize_cd(c) for c in project.cds.values()],
        "recorded_media": [serialize_recorded_media(r) for r in project.recorded_media.values()],
        "active_channel": context.active_channel_id,
        "active_broadcast": context.active_broadcast_id,
    }
