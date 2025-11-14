import xml.etree.ElementTree as ET
from ssr.config import settings
from ssr.core import AppContext
from ssr.io import exporter, importers
from pathlib import Path
context = AppContext()
context.project.channels.clear()
context.project.broadcasts.clear()
context.project.voices.clear()
importers.import_radio_data(context, str(settings.radio_data_path))
Path('test_output').mkdir(exist_ok=True)
exporter.export_radio_data(context, Path('test_output'))
root = ET.parse(Path('test_output') / 'RadioData.xml')
line_nodes = {node.get('ID'): node for node in root.findall('.//LineEntry')}
color_verified = False
voice_line_found = False
for broadcast in context.project.broadcasts.values():
    for line in broadcast.lines:
        if not line.voice_id:
            continue
        voice_line_found = True
        node = line_nodes.get(line.guid)
        if not node:
            print('no node for', line.guid)
            continue
        voice = context.project.voices.get(line.voice_id)
        if not voice:
            print('no voice for', line.voice_id)
            continue
        color = voice.color.lstrip('#')
        if len(color) != 6:
            print('bad color', voice.color)
            continue
        rgb = [str(int(color[i:i+2], 16)) for i in range(0, 6, 2)]
        node_r = node.get('r')
        node_g = node.get('g')
        node_b = node.get('b')
        print('checking', line.guid, 'node', (node_r, node_g, node_b), 'expected', tuple(rgb))
        if (node_r, node_g, node_b) != tuple(rgb):
            print('mismatch for', line.guid)
            continue
        color_verified = True
        print('color verified for', line.guid)
        break
    if color_verified:
        break
print('voice_line_found', voice_line_found, 'color_verified', color_verified)
