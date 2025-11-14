import xml.etree.ElementTree as ET

import pytest

from ssr.config import settings
from ssr.core import AppContext
from ssr.io import exporter, importers


@pytest.mark.skipif(
    not settings.radio_data_path.exists(),
    reason="Project Zomboid radio data not available in this environment.",
)
def test_radio_data_import_export_roundtrip(tmp_path):
    context = AppContext()
    context.project.channels.clear()
    context.project.broadcasts.clear()
    context.project.voices.clear()

    importers.import_radio_data(context, str(settings.radio_data_path))
    assert context.project.channels
    assert context.project.broadcasts
    assert context.project.voices
    assert all(channel.frequency > 0 for channel in context.project.channels.values())
    assert all(channel.category for channel in context.project.channels.values())
    total_lines = sum(len(b.lines) for b in context.project.broadcasts.values())
    assert total_lines > 0
    exporter.export_radio_data(context, tmp_path)

    tree = ET.parse(tmp_path / "RadioData.xml")
    channel_entries = tree.findall(".//ChannelEntry")
    assert len(channel_entries) == len(context.project.channels)

    for channel in context.project.channels.values():
        channel_elem = next(
            (elem for elem in channel_entries if elem.get("ID") == channel.id), None
        )
        assert channel_elem is not None
        for entry in channel.schedule:
            matching = [
                be
                for be in channel_elem.findall("BroadcastEntry")
                if be.get("ID") == entry.broadcast_id
                and be.get("day") == str(entry.day)
                and be.get("timestamp") == str(int(entry.start))
                and be.get("endstamp") == str(int(entry.end))
            ]
            assert matching, f"Missing broadcast entry for {entry.broadcast_id} on channel {channel.id}"

    line_nodes = {node.get("ID"): node for node in tree.findall(".//LineEntry")}
    assert len(line_nodes) == total_lines
    color_verified = False
    voice_line_found = False
    for broadcast in context.project.broadcasts.values():
        for line in broadcast.lines:
            if not line.voice_id:
                continue
            voice_line_found = True
            node = line_nodes.get(line.guid)
            if node is None:
                continue
            voice = context.project.voices.get(line.voice_id)
            if not voice:
                continue
            color = voice.color.lstrip("#")
            if len(color) != 6:
                continue
            rgb = [str(int(color[i : i + 2], 16)) for i in range(0, 6, 2)]
            assert node.get("r") == rgb[0]
            assert node.get("g") == rgb[1]
            assert node.get("b") == rgb[2]
            color_verified = True
            break
        if color_verified:
            break
    if voice_line_found:
        assert color_verified, "Expected at least one voice-colored line in export"


@pytest.mark.skipif(
    not settings.recorded_media_path.exists(),
    reason="Project Zomboid recorded media not available in this environment.",
)
def test_recorded_media_import_export_roundtrip(tmp_path):
    context = AppContext()
    context.project.recorded_media.clear()
    translation_path = settings.translation_path if settings.translation_path.exists() else None
    importers.import_recorded_media(
        context,
        str(settings.recorded_media_path),
        str(translation_path) if translation_path else None,
    )
    assert context.project.recorded_media

    exporter.export_recorded_media(context, tmp_path)

    lua_contents = (tmp_path / "recorded_media.lua").read_text(encoding="utf-8")
    translations = (tmp_path / "Recorded_Media_EN.txt").read_text(encoding="utf-8")
    entry = next(iter(context.project.recorded_media.values()))
    assert f'RecMedia["{entry.id}"]' in lua_contents

    assert f"RM_{entry.id}_title" in translations
    assert f"RM_{entry.id}_author" in translations
    assert f"RM_{entry.id}_extra" in translations
    for line in entry.lines:
        assert f"RM_{line.guid} =" in translations
        assert line.text in translations

    assert lua_contents.count("RecMedia[") == len(context.project.recorded_media)
    assert lua_contents.count("lines = {") == len(context.project.recorded_media)
    assert translations.startswith("// Auto-generated")
    for recorded_entry in context.project.recorded_media.values():
        for line in recorded_entry.lines:
            assert f"r = {line.r:.2f}" in lua_contents
            assert f"g = {line.g:.2f}" in lua_contents
            assert f"b = {line.b:.2f}" in lua_contents
