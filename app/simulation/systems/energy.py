from __future__ import annotations

import numpy as np

from app.simulation.world_state import WorldState, clamp, clamp_array


def update_energy(state: WorldState) -> None:
    citizens = state.citizens
    resident_counts = np.bincount(citizens.home_district, minlength=len(state.districts))
    margins: list[float] = []
    blackout_pressure: list[float] = []
    for district in state.districts:
        demand_target = (
            92
            + resident_counts[district.id] * (0.045 + district.wealth * 0.018)
            + district.business_activity * 120
            + district.tech_level * 65
        )
        renewable_gain = (district.tech_level * 0.4 + state.government.infrastructure_budget * 0.22) * 0.32
        emergency_grid_work = max(0.0, state.metrics.get("blackout_risk", 0.0) - 0.08) * state.government.infrastructure_budget
        district.energy_capacity = round(district.energy_capacity * (1 + renewable_gain * 0.004 + emergency_grid_work * 0.006), 2)
        district.energy_demand = round(district.energy_demand * 0.78 + demand_target * 0.22, 2)
        margin = (district.energy_capacity - district.energy_demand) / max(1, district.energy_demand)
        margins.append(margin)
        pressure = float(np.clip(-margin, 0, 1))
        blackout_pressure.append(pressure)
        district.infrastructure_quality = clamp(district.infrastructure_quality - pressure * 0.012 + state.government.infrastructure_budget * 0.003)
        district.pollution = clamp(district.pollution + pressure * 0.015 - district.tech_level * 0.003)

    home_blackout = np.array([blackout_pressure[index] for index in citizens.home_district], dtype=np.float32)
    citizens.energy = clamp_array(citizens.energy - home_blackout * 0.038 + 0.012)
    citizens.stress = clamp_array(citizens.stress + home_blackout * 0.026 - np.maximum(0, 0.12 - home_blackout) * 0.012)
    citizens.productivity = clamp_array(citizens.productivity - home_blackout * 0.036)

    state.metrics["energy_margin"] = float(np.mean(margins))
    state.metrics["blackout_risk"] = float(np.mean(blackout_pressure))
