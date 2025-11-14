import threading, time, sys
from pathlib import Path
from typing import Optional
from ..config import settings

try:
    import winsound
except ImportError:
    winsound = None


def _find_sound(name: str) -> Optional[Path]:
    """Search up the tree for assets/sound/<name>; also handle frozen apps."""
    bases = []
    try:
        bases.append(Path(__file__).resolve())
    except Exception:
        pass

    bases.append(Path.cwd())

    try:
        bases.append(Path(sys.argv[0]).resolve())
    except Exception:
        pass

    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            bases.append(Path(meipass))

    for base in bases:
        for root in [base, *base.parents[:6]]:
            p = root / "assets" / "sound" / name
            if p.exists():
                return p
    return None


# --- Back-compat & explicit paths -------------------------------------------

# Your filenames appear (intentionally) without the 'e' in "typewriter".
CLICK_SOUND_PATH: Optional[Path] = _find_sound("typwriternoise.wav")
STOP_SOUND_PATH:  Optional[Path] = _find_sound("typwriterSTOPnoise.wav")

# Backwards-compatible alias for older imports
TYPEWRITER_SOUND_PATH = CLICK_SOUND_PATH  # <— restores the symbol UI expects


class TypewriterSoundPlayer:
    """Plays typing 'clicks' and a Return/Stop sound."""

    _min_interval = 0.08  # rate-limit replays

    def __init__(
        self,
        click_path: Optional[Path] = CLICK_SOUND_PATH,
        stop_path:  Optional[Path] = STOP_SOUND_PATH,
    ):
        self.click_path = click_path
        self.stop_path  = stop_path
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._end_t = 0.0
        self._last_play = 0.0

    def trigger(self) -> None:
        """Play the normal key click (keeps alive for 0.3s after last key)."""
        if not self._ready(self.click_path):
            return
        now = time.monotonic()
        with self._lock:
            self._end_t = max(self._end_t, now + 0.3)
            if not (self._thread and self._thread.is_alive()):
                self._thread = threading.Thread(
                    target=self._loop, args=(self.click_path,), daemon=True
                )
                self._thread.start()

    def trigger_stop(self) -> None:
        """Play the Return/Stop sound once (no loop)."""
        if not self._ready(self.stop_path):
            return
        try:
            winsound.PlaySound(
                str(self.stop_path),
                winsound.SND_FILENAME | winsound.SND_ASYNC
            )
        except RuntimeError:
            pass

    def _ready(self, path: Optional[Path]) -> bool:
        return (
            getattr(settings, "typewriter_sound_enabled", False)
            and winsound is not None
            and path is not None
            and path.exists()
        )

    def _loop(self, path: Path) -> None:
        flags = winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NOSTOP
        try:
            while True:
                with self._lock:
                    now = time.monotonic()
                    enabled = getattr(settings, "typewriter_sound_enabled", False)
                    end_t = self._end_t
                if not enabled or now >= end_t:
                    break
                if now - self._last_play >= self._min_interval:
                    try:
                        winsound.PlaySound(str(path), flags)
                        self._last_play = now
                    except RuntimeError:
                        time.sleep(0.05)
                time.sleep(0.02)
        finally:
            try:
                winsound.PlaySound(None, 0)
            except RuntimeError:
                pass
