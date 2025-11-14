from ssr.core import AppContext
from ssr.io import exporter, importers
from ssr.config import settings
from pathlib import Path
context = AppContext()
context.project.channels.clear()
context.project.broadcasts.clear()
context.project.voices.clear()
importers.import_radio_data(context, str(settings.radio_data_path))
print('Voices loaded:', len(context.project.voices))
voice = next(iter(context.project.voices.values()))
print('First voice color', voice.color)
broadcast = next(iter(context.project.broadcasts.values()))
voice_line_count = sum(1 for line in broadcast.lines if line.voice_id)
print('Voice lines in first broadcast', voice_line_count)
Path('test_output').mkdir(exist_ok=True)
exporter.export_radio_data(context, Path('test_output'))
from xml.etree import ElementTree as ET
root = ET.parse(Path('test_output') / 'RadioData.xml').getroot()
line_nodes = {node.get('ID'): node for node in root.findall('.//LineEntry')}
for line in broadcast.lines:
    if not line.voice_id:
        continue
    node = line_nodes.get(line.guid)
    print('Line', line.guid, 'node', 'present' if node is not None else 'missing')
    if node is None:
        break
    voice = context.project.voices.get(line.voice_id)
    print('Voice color for', line.voice_id, voice.color if voice else 'missing voice')
    color = (voice.color.lstrip('#') if voice else '')
    if len(color) == 6:
        rgb = [str(int(color[i:i+2], 16)) for i in range(0, 6, 2)]
        r,g,b = node.get('r'), node.get('g'), node.get('b')
        print('Expected', rgb, 'got', (r,g,b))
    break
print('done script')
