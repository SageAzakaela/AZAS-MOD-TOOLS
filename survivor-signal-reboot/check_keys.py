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
print('has key 5766', '576674c7-6cbf-4ec5-a3e9-7d8269fc44b8' in line_nodes)
print('keys example', list(line_nodes.keys())[:5])
