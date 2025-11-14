from __future__ import annotations

from pathlib import Path
from typing import Dict


SFX_FILES = {
    "click": "click.wav",
    "bubble": "bubblepop.wav",
    "tada": "tada.wav",
    "oops": "oopsie.wav",
    "braam_drone": "Ghosthack-CE_Braam Drone_Infinity_D.wav",
    "braam_short": "Ghosthack-CE_Braam_Absolute_C.wav",
    "reverse": "Ghosthack-CSFX3_Suckback_Alien.wav",
    "whoosh": "Ghosthack-CSFX3_Whoosh_Electricity.wav",
    "heal": "uwu_sfx Heal 2.wav",
}
MUSIC_EXTS = {".wav", ".mp3"}


class SoundPlayer:
    """Cross-platform sound & music helper used by the GUI."""

    def __init__(self, project_root: Path, conf: dict):
        self.conf = conf
        sound_root = self._find_sound_root(project_root)
        self.pad = sound_root / "sound"
        self.music = sound_root / "music"

        self.paths: Dict[str, Path] = {}
        # self.sounds: Dict[str, "pygame.mixer.Sound"] = {}
        self.music_tracks: list[Path] = []
        self._pygame = None
        self._winsound = None
        self._music_playing = False
        self._waiting_music = False
        self._drone_played = False
        self._music_index = 0

        self._init_audio()
        self._load_sfx()
        self._load_music()
        self.sync_settings()

    def _find_sound_root(self, project_root: Path) -> Path:
        candidates = [
            project_root / "assets",
            project_root / "zomboid_map_gen" / "assets",
        ]
        for c in candidates:
            if c.exists():
                return c
        return candidates[0]

    def _init_audio(self):
        try:
            import pygame

            pygame.mixer.init()
            self._pygame = pygame
        except Exception:
            self._pygame = None
        try:
            import winsound  # type: ignore

            self._winsound = winsound
        except Exception:
            self._winsound = None

    def _load_sfx(self):
        for key, fname in SFX_FILES.items():
            path = self.pad / fname
            self.paths[key] = path
            if self._pygame and path.exists():
                try:
                    self.sounds[key] = self._pygame.mixer.Sound(str(path))
                except Exception:
                    pass

    def _load_music(self):
        if not self.music.exists():
            return
        for entry in sorted(self.music.iterdir()):
            if entry.suffix.lower() in MUSIC_EXTS and entry.is_file():
                self.music_tracks.append(entry)

    def sync_settings(self):
        audio = self.conf.setdefault("audio", {})
        audio.setdefault("enabled", True)
        audio.setdefault("music_mode", "always")
        audio.setdefault("music_volume_db", -12.0)
        if self._pygame:
            self._set_music_volume()
        self._maybe_update_music()

    def _music_mode(self) -> str:
        return str(self.conf.get("audio", {}).get("music_mode", "always"))

    def _music_volume_db(self) -> float:
        return float(self.conf.get("audio", {}).get("music_volume_db", -12.0))

    def _db_to_linear(self, db: float) -> float:
        return min(1.0, max(0.0, 10.0 ** (db / 20.0)))

    def _sound_enabled(self) -> bool:
        return bool(self.conf.get("audio", {}).get("enabled", True))

    def _set_music_volume(self):
        if not self._pygame:
            return
        vol = self._db_to_linear(self._music_volume_db())
        try:
            self._pygame.mixer.music.set_volume(vol)
        except Exception:
            pass

    def _play_sfx(self, key: str):
        if not self._sound_enabled():
            return
        if self._pygame and key in self.sounds:
            try:
                self.sounds[key].play()
                return
            except Exception:
                pass
        if self._winsound:
            path = self.paths.get(key)
            if path and path.exists():
                try:
                    self._winsound.PlaySound(str(path), self._winsound.SND_FILENAME | self._winsound.SND_ASYNC)
                except Exception:
                    pass

    def play_click(self):
        self._play_sfx("click")

    def play_bubble(self):
        self._play_sfx("bubble")

    def play_tada(self):
        self._play_sfx("tada")

    def play_oops(self):
        self._play_sfx("oops")

    # Legacy helpers (main_gui uses these names)
    def click(self):
        self.play_click()

    def bubble(self):
        self.play_bubble()

    def tada(self):
        self.play_tada()

    def oops(self):
        self.play_oops()

    def preview_ready(self):
        if self._drone_played:
            return
        self._play_sfx("braam_drone")
        self._drone_played = True

    def generate_started(self):
        self._play_sfx("whoosh")
        self._play_sfx("reverse")
        self._play_sfx("bubble")
        self._waiting_music = True
        self._maybe_update_music()

    def generate_completed(self):
        self._waiting_music = False
        self._maybe_update_music()
        self._play_sfx("braam_short")

    def tab_switched(self):
        self._play_sfx("heal")

    def _should_play_music(self) -> bool:
        if not self._pygame or not self._sound_enabled():
            return False
        mode = self._music_mode()
        if mode == "always":
            return True
        if mode == "waiting":
            return self._waiting_music
        return False

    def _maybe_update_music(self):
        if not self._pygame or not self.music_tracks:
            return
        should = self._should_play_music()
        if should and not self._music_playing:
            self._start_music_loop()
        elif not should and self._music_playing:
            self._stop_music()

    def _start_music_loop(self):
        if not self.music_tracks:
            return
        track = self.music_tracks[self._music_index % len(self.music_tracks)]
        self._music_index += 1
        try:
            self._pygame.mixer.music.load(str(track))
            self._set_music_volume()
            self._pygame.mixer.music.play(-1)
            self._music_playing = True
        except Exception:
            self._music_playing = False

    def _stop_music(self):
        try:
            self._pygame.mixer.music.stop()
        except Exception:
            pass
        self._music_playing = False
