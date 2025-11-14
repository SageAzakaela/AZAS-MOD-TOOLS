import re
import xml.etree.ElementTree as ET
from typing import Dict, Optional

from ..core import (
    AppContext,
    AdvertBroadcast,
    AdvertScript,
    Broadcast,
    Channel,
    ChannelScheduleEntry,
    Line,
    RecordedMediaEntry,
    RecordedMediaLine,
    Voice,
)


def _read_metadata(element: ET.Element) -> Dict[str, str]:
    metadata: Dict[str, str] = {}
    meta_parent = element.find("Metadata")
    if meta_parent is None:
        return metadata
    for prop in meta_parent.findall("Property"):
        key = prop.get("key") or prop.get("name")
        if not key:
            continue
        value = prop.get("value")
        if value is None:
            value = prop.text or ""
        metadata[key] = value
    return metadata


def _hex_color_from_element(elem: ET.Element) -> str:
    if elem is None:
        return "#FFFFFF"
    r = int(elem.get("r", "0"))
    g = int(elem.get("g", "0"))
    b = int(elem.get("b", "0"))
    return f"#{r:02x}{g:02x}{b:02x}"


def _parse_lua_value(value: str):
    value = value.strip().rstrip(",")
    if value in ("nil", ""):
        return None
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _parse_translation(path: Optional[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not path:
        return mapping
    with open(path, encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("//"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip()
            mapping[key] = value
    return mapping


def import_radio_data(context: AppContext, path: str) -> None:
    tree = ET.parse(path)
    root = tree.getroot()

    voices = root.find("Voices")
    voice_color_map: Dict[str, str] = {}
    if voices is not None:
        for idx, entry in enumerate(voices.findall("VoiceEntry"), start=1):
            vid = entry.get("ID")
            color_elem = entry.find("FinalColor")
            color = _hex_color_from_element(color_elem)
            context.project.voices[vid] = Voice(
                id=vid,
                name=f"Unknown Speaker {idx}",
                color=color,
                metadata=_read_metadata(entry),
            )
            if color:
                voice_color_map[color.lower()] = vid

    adverts_node = root.find("Adverts")
    if adverts_node is not None:
        context.project.advertisements.clear()
        for script in adverts_node.findall("ScriptEntry"):
            script_id = script.get("ID")
            advert = AdvertScript(
                id=script_id,
                name=script.get("name", script_id),
                startdelay=float(script.get("startdelay", "0")),
                timestampmode=script.get("timestampmode", "Static"),
                loopmin=int(script.get("loopmin", "1")),
                loopmax=int(script.get("loopmax", "1")),
            )
            for broadcast_elem in script.findall("BroadcastEntry"):
                broadcast = AdvertBroadcast(
                    id=broadcast_elem.get("ID"),
                    timestamp=float(broadcast_elem.get("timestamp", "0")),
                    endstamp=float(broadcast_elem.get("endstamp", "0")),
                    day=int(broadcast_elem.get("day", "0")),
                    advert_cat=broadcast_elem.get("advertCat", "none"),
                    is_segment=broadcast_elem.get("isSegment", "false").lower() == "true",
                )
                for line_elem in broadcast_elem.findall("LineEntry"):
                    r = int(line_elem.get("r", "255"))
                    g = int(line_elem.get("g", "255"))
                    b = int(line_elem.get("b", "255"))
                    color_key = f"#{r:02x}{g:02x}{b:02x}".lower()
                    voice_id = line_elem.get("voice") or voice_color_map.get(color_key)
                    broadcast.lines.append(
                        Line(
                            text=line_elem.text or "",
                            effects=[line_elem.get("codes")] if line_elem.get("codes") else [],
                            guid=line_elem.get("ID"),
                            voice_id=voice_id,
                        )
                    )
                advert.broadcasts.append(broadcast)
            context.project.advertisements[script_id] = advert

    channels = root.find("Channels")
    if channels is None:
        return

    for channel_elem in channels.findall("ChannelEntry"):
        channel_id = channel_elem.get("ID")
        channel = Channel(
            id=channel_id,
            name=channel_elem.get("name", "Unnamed Channel"),
            frequency=float(channel_elem.get("freq", "0")) / 100.0,
            category=channel_elem.get("cat", "radio").lower(),
            default_advert_group=channel_elem.get("advertGroup", "") or "",
            start_script=channel_elem.get("startscript", "main") or "main",
        )
        context.project.channels[channel.id] = channel
        for broadcast_elem in channel_elem.findall(".//BroadcastEntry"):
            broadcast_id = broadcast_elem.get("ID")
            broadcast = Broadcast(
                id=broadcast_id,
                title=broadcast_elem.get("name", broadcast_id),
                description=broadcast_elem.get("description", ""),
                day=int(broadcast_elem.get("day", "0")),
                metadata=_read_metadata(broadcast_elem),
            )
            timestamp = float(broadcast_elem.get("timestamp", "0"))
            endstamp = float(broadcast_elem.get("endstamp", "0"))
            broadcast.start_offset = timestamp
            broadcast.end_offset = endstamp
            for line_elem in broadcast_elem.findall("LineEntry"):
                r = int(line_elem.get("r", "255"))
                g = int(line_elem.get("g", "255"))
                b = int(line_elem.get("b", "255"))
                color_key = f"#{r:02x}{g:02x}{b:02x}".lower()
                voice_id = line_elem.get("voice") or voice_color_map.get(color_key)
                broadcast.lines.append(
                    Line(
                        text=line_elem.text or "",
                        effects=[line_elem.get("codes")] if line_elem.get("codes") else [],
                        guid=line_elem.get("ID"),
                        voice_id=voice_id,
                        metadata=_read_metadata(line_elem),
                    )
                )
            context.project.broadcasts[broadcast.id] = broadcast
            channel.schedule.append(
                ChannelScheduleEntry(
                    broadcast_id=broadcast.id,
                    day=int(broadcast_elem.get("day", "0")),
                    start=timestamp,
                    end=endstamp,
                )
            )

    if channels.findall(".//BroadcastEntry"):
        first_broadcast = next(iter(context.project.broadcasts.values()), None)
        if first_broadcast:
            context.active_broadcast_id = first_broadcast.id


def import_recorded_media(
    context: AppContext, recorded_path: str, translation_path: Optional[str] = None
) -> None:
    translation = _parse_translation(translation_path)
    context.project.recorded_media.clear()
    current: Optional[Dict] = None
    in_lines = False
    line_buffer = []
    entries: Dict[str, Dict] = {}
    entry_id = None
    kv_re = re.compile(r"(\w+)\s*=\s*(.+)")

    with open(recorded_path, encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("--"):
                continue
            if line.startswith("RecMedia["):
                entry_id = re.search(r'RecMedia\["([^"]+)"\]', line).group(1)
                current = {"lines": []}
                continue
            if current is None:
                continue
            if line.startswith("lines"):
                in_lines = True
                continue
            if in_lines:
                if line.startswith("}"):
                    in_lines = False
                    continue
                if line.startswith("{"):
                    content = line.strip("{} ").strip()
                    parts = [part.strip() for part in content.split(",") if part.strip()]
                    record = {}
                    for part in parts:
                        if "=" not in part:
                            continue
                        key, value = part.split("=", 1)
                        record[key.strip()] = _parse_lua_value(value)
                    current["lines"].append(record)
                continue
            if line.startswith("};"):
                if entry_id and current is not None:
                    entries[entry_id] = current
                current = None
                entry_id = None
                continue
            kv_match = kv_re.match(line)
            if kv_match:
                key, value = kv_match.groups()
                current[key] = _parse_lua_value(value)

    for eid, info in entries.items():
        entry = RecordedMediaEntry(
            id=eid,
            title=translation.get(info.get("title", ""), info.get("title", eid)),
            author=translation.get(info.get("author", ""), info.get("author", "")),
            category=info.get("category", "CDs"),
            spawn=int(info.get("spawning", 0) or 0),
            extra=translation.get(info.get("extra", ""), info.get("extra")),
        )
        for line_info in info.get("lines", []):
            text_key = line_info.get("text")
            entry.lines.append(
                RecordedMediaLine(
                    text=translation.get(text_key, text_key),
                    r=float(line_info.get("r", 0.0) or 0.0),
                    g=float(line_info.get("g", 0.0) or 0.0),
                    b=float(line_info.get("b", 0.0) or 0.0),
                    codes=line_info.get("codes"),
                )
            )
        context.project.recorded_media[entry.id] = entry
