from __future__ import annotations


MIN_PUBLIC_POPULATION = 100
MAX_PUBLIC_POPULATION = 10_000
MAX_MANUAL_TICK_STEPS = 250


def clamp_int(value: object, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        parsed = default
    return min(max(parsed, minimum), maximum)
