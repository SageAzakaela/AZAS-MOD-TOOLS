# zomboid_map_gen/utils/seeds.py
"""
Seed helpers: derive deterministic per-layer seeds from a master seed.

Python's built-in hash() is intentionally salted per process and not stable
across runs. Use a stable hash so saved configs reproduce the same maps.
"""

from hashlib import blake2s


def derive_seed(master: int, name: str) -> int:
    """
    Create a stable 32-bit integer seed from a master seed + name.
    """
    data = f"{int(master)}|{name}".encode("utf-8")
    h = blake2s(data, digest_size=4).digest()
    return int.from_bytes(h, "big", signed=False)
