from ssr.config import settings
from ssr.core import AppContext
from ssr.io import exporter, importers
from pathlib import Path
import xml.etree.ElementTree as ET
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
        if line.voice_id:
            print('repr guid', repr(line.guid))
            print('line guid in nodes', repr(line.guid) in line_nodes)
            if not line.guid in line_nodes:
                print('node missing? keys snippet', list(line_nodes.keys())[:5])
            raise SystemExit
