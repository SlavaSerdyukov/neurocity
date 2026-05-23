from __future__ import annotations

from collections.abc import Callable

from app.simulation.systems import (
    update_climate,
    update_crime,
    update_culture,
    update_economy,
    update_employment,
    update_energy,
    update_housing,
    update_politics,
    update_social_network,
    update_transportation,
)
from app.simulation.interventions import update_interventions
from app.simulation.world_state import WorldState


SystemFn = Callable[[WorldState], None]


SYSTEM_PIPELINE: tuple[SystemFn, ...] = (
    update_transportation,
    update_employment,
    update_housing,
    update_energy,
    update_climate,
    update_crime,
    update_social_network,
    update_culture,
    update_economy,
    update_politics,
    update_interventions,
)


def run_systems(state: WorldState) -> None:
    for system in SYSTEM_PIPELINE:
        system(state)
