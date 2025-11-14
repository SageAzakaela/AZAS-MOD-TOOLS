from ssr.core import AppContext
from ssr.io import importers
from ssr.config import settings
context = AppContext()
context.project.channels.clear()
context.project.broadcasts.clear()
context.project.voices.clear()
importers.import_radio_data(context, str(settings.radio_data_path))
for vid, voice in context.project.voices.items():
    print(vid, voice.color, len(voice.color))
