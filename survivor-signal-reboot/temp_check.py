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
line_nodes = {}
root = ET.parse(Path('test_output') / 'RadioData.xml')
for node in root.findall('.//LineEntry'):
    line_nodes[node.get('ID')] = node
print('total_lines', sum(len(b.lines) for b in context.project.broadcasts.values()))
print('line_nodes', len(line_nodes))
color_verified = False
voice_line_found = False
for broadcast in context.project.broadcasts.values():
    for line in broadcast.lines:
        if not line.voice_id:
            continue
        voice_line_found = True
        node = line_nodes.get(line.guid)
        if not node:
            print('missing node for', line.guid)
            continue
        voice = context.project.voices.get(line.voice_id)
        if not voice:
            print('missing voice for', line.voice_id)
            continue
        color = voice.color.lstrip('#')
        if len(color) != 6:
            print('bad color length', voice.color)
            continue
        rgb = [str(int(color[i:i+2], 16)) for i in range(0, 6, 2)]
        r,g,b = node.get('r'), node.get('g'), node.get('b')
        print('check line', line.guid, 'node', (r,g,b), 'expected', tuple(rgb))
        if (r,g,b) != tuple(rgb):
            print('mismatch', line.guid)
        else:
            color_verified = True
            print('color verified for', line.guid)
            break
    if color_verified:
        break
if voice_line_found:
    print('voice line found')
print('color_verified', color_verified)
