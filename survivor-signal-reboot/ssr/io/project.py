import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from ..core import AppContext
from ..core.models import (
    AdvertScript,
    Broadcast,
    CDCompilation,
    Channel,
    ChannelScheduleEntry,
    Character,
    Group,
    Line,
    RecordedMediaEntry,
    RecordedMediaLine,
    VHSTape,
    Voice,
)
from ..io.serializer import serialize_context


def save_project(context: AppContext, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = serialize_context(context)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_project(context: AppContext, path: Path) -> None:
    if not path.exists():
        return
    raw: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))

    project = context.project
    project.voices.clear()
    project.broadcasts.clear()
    project.channels.clear()
    project.vhs_tapes.clear()
    project.cds.clear()
    project.recorded_media.clear()
    project.advertisements.clear()

    for voice_data in raw.get("voices", []):
        project.voices[voice_data["id"]] = Voice(**voice_data)

    for char_data in raw.get("characters", []):
        project.characters[char_data["id"]] = Character(
            id=char_data["id"],
            name=char_data.get("name", ""),
            notes=char_data.get("notes", ""),
            voice_ids=list(char_data.get("voice_ids", [])),
            metadata=char_data.get("metadata", {}),
        )

    for group_data in raw.get("groups", []):
        project.groups[group_data["id"]] = Group(
            id=group_data["id"],
            name=group_data.get("name", ""),
            description=group_data.get("description", ""),
            character_ids=list(group_data.get("character_ids", [])),
        )

    for broadcast_data in raw.get("broadcasts", []):
        broadcast = Broadcast(
            id=broadcast_data["id"],
            title=broadcast_data.get("title", ""),
            description=broadcast_data.get("description", ""),
            start_offset=broadcast_data.get("start_offset", 0.0),
            effects=broadcast_data.get("effects", []),
            adverts=broadcast_data.get("adverts", []),
        )
        broadcast.lines = []
        for line_data in broadcast_data.get("lines", []):
            line_kwargs = {
                "text": line_data.get("text", ""),
                "voice_id": line_data.get("voice"),
                "duration": line_data.get("duration"),
                "moodle": line_data.get("moodle"),
                "effects": list(line_data.get("effects") or []),
                "sound_file": line_data.get("sound_file"),
            }
            guid_value = line_data.get("guid")
            if guid_value:
                line_kwargs["guid"] = guid_value
            broadcast.lines.append(Line(**line_kwargs))
        project.broadcasts[broadcast.id] = broadcast

    for channel_data in raw.get("channels", []):
        channel = Channel(
            id=channel_data["id"],
            name=channel_data.get("name", ""),
            frequency=channel_data.get("frequency", 0.0),
            category=channel_data.get("category", "radio"),
            auto_adverts=channel_data.get("auto_adverts", False),
            default_advert_group=channel_data.get("default_advert_group", ""),
            start_script=channel_data.get("start_script", "main"),
        )
        for entry_data in channel_data.get("schedule", []):
            entry = ChannelScheduleEntry(
                broadcast_id=entry_data["broadcast_id"],
                day=entry_data.get("day", 0),
                start=entry_data.get("start", 0.0),
                end=entry_data.get("end", 0.0),
            )
            channel.schedule.append(entry)
        project.channels[channel.id] = channel

    for vhs_data in raw.get("vhs_tapes", []):
        tape = VHSTape(
            id=vhs_data["id"],
            name=vhs_data.get("name", ""),
            description=vhs_data.get("description", ""),
            spawn_weight=vhs_data.get("spawn_weight", 1.0),
        )
        tape.broadcast_ids = list(vhs_data.get("broadcast_ids", []))
        project.vhs_tapes[tape.id] = tape

    for cd_data in raw.get("cds", []):
        cd = CDCompilation(
            id=cd_data["id"],
            name=cd_data.get("name", ""),
            curator=cd_data.get("curator", ""),
            genre=cd_data.get("genre", "ambient"),
        )
        cd.track_ids = list(cd_data.get("track_ids", []))
        project.cds[cd.id] = cd

    for entry_data in raw.get("recorded_media", []):
        entry = RecordedMediaEntry(
            id=entry_data["id"],
            title=entry_data.get("title", ""),
            author=entry_data.get("author", ""),
            category=entry_data.get("category", "CDs"),
            spawn=entry_data.get("spawn", 0),
        )
        entry.lines = [
            RecordedMediaLine(
                text=line["text"],
                r=line.get("r", 1.0),
                g=line.get("g", 1.0),
                b=line.get("b", 1.0),
                codes=line.get("codes"),
            )
            for line in entry_data.get("lines", [])
        ]
        project.recorded_media[entry.id] = entry

    for ad_data in raw.get("advertisements", []):
        advert = AdvertScript(
            id=ad_data["id"],
            name=ad_data.get("name", ""),
            startdelay=ad_data.get("startdelay", 0.0),
            timestampmode=ad_data.get("timestampmode", "Static"),
            loopmin=ad_data.get("loopmin", 1),
            loopmax=ad_data.get("loopmax", 1),
        )
        project.advertisements[advert.id] = advert

    context.notify_data_changed()
