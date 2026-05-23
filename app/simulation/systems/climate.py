from __future__ import annotations

import math

import numpy as np

from app.simulation.world_state import WorldState, clamp, clamp_array


def update_climate(state: WorldState) -> None:
    seasonal_heat = 0.5 + 0.5 * math.sin((state.day % 365) / 365 * math.tau)
    pollution = np.array([district.pollution for district in state.districts], dtype=np.float32)
    heat_stress_by_district = np.clip(seasonal_heat * 0.22 + pollution * 0.2 - 0.08, 0, 0.42)

    for district in state.districts:
        climate_pressure = seasonal_heat * district.pollution
        district.happiness = clamp(district.happiness - climate_pressure * 0.004)
        district.infrastructure_quality = clamp(district.infrastructure_quality - max(0, climate_pressure - 0.25) * 0.004)
        district.pollution = clamp(district.pollution + district.congestion * 0.003 - district.tech_level * 0.0025)

    citizen_heat = heat_stress_by_district[state.citizens.home_district]
    state.citizens.health = clamp_array(state.citizens.health - citizen_heat * 0.018)
    state.citizens.stress = clamp_array(state.citizens.stress + citizen_heat * 0.019)
    state.metrics["pollution"] = float(np.mean([district.pollution for district in state.districts]))

