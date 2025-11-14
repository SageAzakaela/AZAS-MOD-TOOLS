import xml.etree.ElementTree as ET

from ssr.core import AppContext
from ssr.core.models import (
    Broadcast,
    Channel,
    ChannelScheduleEntry,
    Line,
    RecordedMediaEntry,
    RecordedMediaLine,
    Voice,
)
from ssr.io import exporter


def test_export_radio_data_serializes_schedule(tmp_path):
    context = AppContext()
    context.project.channels.clear()
    context.project.broadcasts.clear()
    context.project.voices.clear()

    voice = Voice(id="voice-test", name="Narrator", color="#112233")
    context.project.voices[voice.id] = voice

    broadcast = Broadcast(id="broadcast-test", title="Test Broadcast")
    line = Line(text="Listen up survivors.", voice_id=voice.id)
    broadcast.lines.append(line)
    context.project.broadcasts[broadcast.id] = broadcast

    channel = Channel(id="channel-test", name="Harbor", frequency=101.1)
    schedule_entry = ChannelScheduleEntry(
        broadcast_id=broadcast.id,
        day=1,
        start=12.7,
        end=90.3,
    )
    channel.schedule.append(schedule_entry)
    context.project.channels[channel.id] = channel

    exporter.export_radio_data(context, tmp_path)

    tree = ET.parse(tmp_path / "RadioData.xml")
    channel_elem = next(node for node in tree.findall(".//ChannelEntry") if node.get("ID") == channel.id)
    broadcast_elem = channel_elem.find("BroadcastEntry")
    assert broadcast_elem is not None
    assert broadcast_elem.get("ID") == broadcast.id
    assert broadcast_elem.get("timestamp") == str(int(schedule_entry.start))
    assert broadcast_elem.get("endstamp") == str(int(schedule_entry.end))
    assert broadcast_elem.get("day") == str(schedule_entry.day)

    line_elem = broadcast_elem.find("LineEntry")
    assert line_elem.text == line.text
    assert line_elem.get("ID") == line.guid
    assert line_elem.get("r") == str(int("11", 16))
    assert line_elem.get("g") == str(int("22", 16))
    assert line_elem.get("b") == str(int("33", 16))


def test_export_recorded_media_structures_output(tmp_path):
    context = AppContext()
    context.project.recorded_media.clear()

    entry = RecordedMediaEntry(
        id="rm-test",
        title="Survivor Journal",
        author="Field Team",
        category="CDs",
        spawn=3,
        extra="Notes",
    )
    entry.lines.append(
        RecordedMediaLine(text="Entry one", r=0.1, g=0.2, b=0.3, codes="A1")
    )
    entry.lines.append(
        RecordedMediaLine(text="Entry two", r=0.4, g=0.5, b=0.6, codes=None)
    )
    context.project.recorded_media[entry.id] = entry

    exporter.export_recorded_media(context, tmp_path)

    lua_contents = (tmp_path / "recorded_media.lua").read_text(encoding="utf-8")
    assert f'RecMedia["{entry.id}"]' in lua_contents
    assert lua_contents.count("\t},") == 1
    for line in entry.lines:
        assert f'"RM_{line.guid}"' in lua_contents

    translations = (tmp_path / "Recorded_Media_EN.txt").read_text(encoding="utf-8")
    assert f"RM_{entry.id}_title = \"{entry.title}\"" in translations
    assert f"RM_{entry.id}_author = \"{entry.author}\"" in translations
    assert f"RM_{entry.id}_extra = \"{entry.extra}\"" in translations
    for line in entry.lines:
        assert f"RM_{line.guid} = \"{line.text}\"" in translations
