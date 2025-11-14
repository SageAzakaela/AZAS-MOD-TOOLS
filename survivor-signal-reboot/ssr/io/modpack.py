import shutil
from dataclasses import dataclass
from pathlib import Path

from .exporter import export_radio_data, export_recorded_media


@dataclass
class ModMetadata:
    mod_id: str
    name: str
    version: str = "1.0"
    description: str = ""
    thumbnail: Path | None = None


def build_mod_package(context, output_dir: Path, metadata: ModMetadata) -> Path:
    mod_root = output_dir / metadata.mod_id
    mod_root.mkdir(parents=True, exist_ok=True)

    radio_dir = mod_root / "media" / "radio"
    recorded_dir = mod_root / "media" / "lua" / "shared" / "RecordedMedia"
    translation_dir = mod_root / "media" / "lua" / "shared" / "Translate" / "EN"

    export_radio_data(context, radio_dir)
    export_recorded_media(context, recorded_dir, translation_dir)

    modinfo_path = mod_root / "mod.info"
    with modinfo_path.open("w", encoding="utf-8") as fh:
        fh.write(f"name={metadata.mod_id}\n")
        fh.write(f"displayName={metadata.name}\n")
        fh.write(f"version={metadata.version}\n")
        fh.write(f"description={metadata.description}\n")

    if metadata.thumbnail and metadata.thumbnail.exists():
        thumb_dest = mod_root / metadata.thumbnail.name
        shutil.copy(metadata.thumbnail, thumb_dest)

    return mod_root
