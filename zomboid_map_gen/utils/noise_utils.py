# zomboid_map_gen/utils/noise_utils.py
import random

try:
    import noise  # optional: pip install noise
except ImportError:
    noise = None


def perlin2(
    x: float,
    y: float,
    scale: float = 60.0,
    octaves: int = 4,
    persistence: float = 0.5,
    lacunarity: float = 2.0,
    seed: int = 0,
) -> float:
    """
    Returns a value in roughly [-1, 1].
    If the 'noise' library is available, we use real Perlin.
    Otherwise we use a deterministic PRNG-based fallback so generation still runs.
    """
    if noise is None:
        # Deterministic smooth value-noise fallback with fBm octaves.
        def hash2(ix, iy, s):
            k = (ix * 374761393 + iy * 668265263 + (s & 0xFFFFFFFF) * 2654435761) & 0xFFFFFFFF
            k ^= (k >> 13); k = (k * 1274126177) & 0xFFFFFFFF
            return ((k >> 8) & 0xFFFFFF) / 0xFFFFFF  # 0..1

        def fade(t):
            return t * t * (3 - 2 * t)

        def value_noise(sx, sy, s):
            ix = int(sx); iy = int(sy)
            fx = sx - ix; fy = sy - iy
            v00 = hash2(ix, iy, s)
            v10 = hash2(ix + 1, iy, s)
            v01 = hash2(ix, iy + 1, s)
            v11 = hash2(ix + 1, iy + 1, s)
            u = fade(fx); v = fade(fy)
            a = v00 * (1 - u) + v10 * u
            b = v01 * (1 - u) + v11 * u
            return (a * (1 - v) + b * v) * 2.0 - 1.0

        # fBm accumulation respecting octaves/persistence/lacunarity
        amp = 1.0
        freq = 1.0 / max(1e-6, float(scale))
        total = 0.0
        norm = 0.0
        base_seed = (seed & 0xFFFFFFFF)
        for i in range(max(1, int(octaves))):
            sx = x * freq
            sy = y * freq
            total += value_noise(sx, sy, base_seed + i * 1013) * amp
            norm += amp
            amp *= float(persistence)
            freq *= float(lacunarity)
        return total / max(1e-6, norm)

    return noise.pnoise2(
        x / scale,
        y / scale,
        octaves=octaves,
        persistence=persistence,
        lacunarity=lacunarity,
        base=seed % 1024,
    )


def domain_warp_coords(x: float, y: float, amount: float = 0.0, warp_scale: float = 100.0, seed: int = 0) -> tuple[float, float]:
    """
    Compute domain-warped coordinates by offsetting (x,y) with two low-frequency
    noise fields. If amount <= 0, returns the input unchanged.
    """
    if amount <= 0.0:
        return x, y
    dx = perlin2(x, y, scale=warp_scale, octaves=2, persistence=0.5, lacunarity=2.0, seed=(seed * 31 + 1))
    dy = perlin2(x + 133.7, y - 79.4, scale=warp_scale, octaves=2, persistence=0.5, lacunarity=2.0, seed=(seed * 31 + 2))
    # perlin2 ≈ [-1,1] -> scale by amount in pixels
    return x + dx * amount, y + dy * amount
