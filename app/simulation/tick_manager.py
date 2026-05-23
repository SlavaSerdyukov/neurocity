from __future__ import annotations

from enum import IntEnum


class SimulationSpeed(IntEnum):
    PAUSED = 0
    NORMAL = 1
    FAST = 5
    VERY_FAST = 20
    HYPER = 100


def speed_delay(speed: int) -> float:
    if speed <= 0:
        return 1.0
    return max(0.01, 1.0 / min(speed, 100))

