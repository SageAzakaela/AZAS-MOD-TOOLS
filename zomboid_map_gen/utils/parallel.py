"""
Lightweight helpers for parallel execution.

- Uses ProcessPoolExecutor for CPU-bound loops (escapes the GIL)
- Provides range splitting utilities

No external dependencies. Safe to import from Windows/macOS/Linux.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
import os
from typing import Callable, Iterable, Any


def cpu_count(default: int = 4) -> int:
    try:
        c = os.cpu_count() or default
        # cap to something reasonable so small jobs don't overspawn
        return max(1, min(c, 12))
    except Exception:
        return default


def split_range(n: int, parts: int | None = None) -> list[tuple[int, int]]:
    """Split [0, n) into roughly-equal half-open ranges.

    Returns list of (start, end) with start < end. Empty if n <= 0.
    """
    if n <= 0:
        return []
    if parts is None or parts <= 0:
        parts = cpu_count()
    parts = max(1, min(parts, n))
    base = n // parts
    rem = n % parts
    out = []
    s = 0
    for i in range(parts):
        e = s + base + (1 if i < rem else 0)
        if s < e:
            out.append((s, e))
        s = e
    return out


def run_process_map(
    worker: Callable[..., Any],
    args_list: Iterable[tuple[Any, ...]],
    max_workers: int | None = None,
) -> list[Any]:
    """Run worker over args tuples using processes, preserving order.

    worker must be a top-level function (picklable) because Windows uses spawn.
    """
    args_list = list(args_list)
    if not args_list:
        return []
    if max_workers is None:
        max_workers = cpu_count()

    results = [None] * len(args_list)
    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        fut_to_idx = {ex.submit(worker, *args): i for i, args in enumerate(args_list)}
        for fut in as_completed(fut_to_idx):
            i = fut_to_idx[fut]
            results[i] = fut.result()
    return results

