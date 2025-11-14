from __future__ import annotations

import subprocess
from pathlib import Path

from .bridge import WorldEdProject


def launch_worlded(project: WorldEdProject, world_conf: dict) -> subprocess.Popen:
    exe = Path(world_conf.get("worlded_exe", "")).expanduser()
    if not exe.exists():
        raise FileNotFoundError(f"WorldEd executable not found: {exe}")
    args = [str(exe), str(project.pzw_path)]
    return subprocess.Popen(args, cwd=exe.parent)
