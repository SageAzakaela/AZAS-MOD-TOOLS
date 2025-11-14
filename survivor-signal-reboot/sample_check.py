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
print('keys sample', list(line_nodes.keys())[:5])
first_voice_line = None
for broadcast in context.project.broadcasts.values():
    for line in broadcast.lines:
        if line.voice_id:
            first_voice_line = line
            break
    if first_voice_line:
        break
print('first voice guid', first_voice_line.guid)
print('line in nodes', first_voice_line.guid in line_nodes)
print('line_nodes has attr for this key', line_nodes.get(first_voice_line.guid) is not None)
