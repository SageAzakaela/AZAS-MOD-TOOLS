"""
Angle / layout helpers for roads + grid utilities.
"""

import math


def snap_angle(angle: float, mode: str) -> float:
    """
    Snap an angle to a grid depending on mode.
    - "ortho": 0, 90, 180, 270
    - "ortho45": every 45 degrees
    - "free": no snapping
    """
    mode = (mode or "free").lower()
    if mode == "ortho":
        return round(angle / 90.0) * 90 % 360
    if mode == "ortho45":
        return round(angle / 45.0) * 45 % 360
    return angle % 360


def snap_point_to_grid(x: float, y: float, step: int | float) -> tuple[float, float]:
    """
    Snap a point to a grid. Used to keep road control points divisible by
    3/6/9px to line up with 300px cells and 3-tile vehicle width.
    """
    if not step or step <= 1:
        return x, y
    return round(x / step) * step, round(y / step) * step


def line_angle_degrees(x1: float, y1: float, x2: float, y2: float) -> float:
    """
    Angle from (x1, y1) to (x2, y2) in degrees, 0..360
    """
    return math.degrees(math.atan2(y2 - y1, x2 - x1)) % 360
