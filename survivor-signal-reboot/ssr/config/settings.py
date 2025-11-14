import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path


VANILLA_ASSETS_DIR = Path(__file__).resolve().parents[2] / "VanillaFiles"


@dataclass
class Settings:
    pz_base_path: Path = Path(os.environ.get("PZ_HOME", r":\SteamLibrary\steamapps\common\ProjectZomboid"))
    auto_load_vanilla: bool = False
    transcript_line_limit: int = 180
    ai_api_key: str = ""
    typewriter_sound_enabled: bool = False
    last_recorded_path: str = ""
    last_translation_path: str = ""
    show_ai_tab: bool = False
    pz_configured: bool = False

    @property
    def radio_data_path(self) -> Path:
        vanilla = VANILLA_ASSETS_DIR / "RadioData.xml"
        if vanilla.exists():
            return vanilla
        return self.pz_base_path / "media" / "radio" / "RadioData.xml"

    @property
    def recorded_media_path(self) -> Path:
        vanilla = VANILLA_ASSETS_DIR / "recorded_media.lua"
        if vanilla.exists():
            return vanilla
        return self.pz_base_path / "media" / "lua" / "shared" / "RecordedMedia" / "recorded_media.lua"

    @property
    def translation_path(self) -> Path:
        vanilla = VANILLA_ASSETS_DIR / "Recorded_Media_EN.txt"
        if vanilla.exists():
            return vanilla
        return self.pz_base_path / "media" / "lua" / "shared" / "Translate" / "EN" / "Recorded_Media_EN.txt"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["pz_base_path"] = str(self.pz_base_path)
        return data


SETTINGS_FILE = Path(__file__).parent / "user_settings.json"


def save_settings() -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with SETTINGS_FILE.open("w", encoding="utf-8") as handle:
        json.dump(settings.to_dict(), handle, indent=2)


def _load_settings():
    if not SETTINGS_FILE.exists():
        return
    data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    for field_info in fields(Settings):
        key = field_info.name
        if key not in data:
            continue
        value = data[key]
        if key == "pz_base_path":
            setattr(settings, key, Path(value))
        else:
            setattr(settings, key, value)


settings = Settings()
_load_settings()
