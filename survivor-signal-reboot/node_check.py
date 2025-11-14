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
for broadcast in context.project.broadcasts.values():
    for line in broadcast.lines:
        if not line.voice_id:
            continue
        node_present = line.guid in line_nodes
        print('line', line.guid, 'node_present', node_present)
        if not node_present:
            print('line missing in nodes? keys sample', list(line_nodes.keys())[:5])
            raise SystemExit
        break
    break
