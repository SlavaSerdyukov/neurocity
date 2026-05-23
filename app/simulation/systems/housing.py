from __future__ import annotations

import numpy as np

from app.simulation.world_state import WorldState, clamp, clamp_array


def update_housing(state: WorldState) -> None:
    citizens = state.citizens
    rng = state.rng(24)
    district_count = len(state.districts)
    resident_counts = np.bincount(citizens.home_district, minlength=district_count)
    district_wealth = np.array([district.wealth for district in state.districts], dtype=np.float32)
    rents = np.zeros(district_count, dtype=np.float32)
    pressure = np.zeros(district_count, dtype=np.float32)

    for district in state.districts:
        district.housing_demand = int(resident_counts[district.id] * (1 + district.business_activity * 0.08))
        demand_ratio = district.housing_demand / max(1, district.housing_supply)
        pressure[district.id] = float(np.clip(demand_ratio - 0.92, 0, 1.4))
        scarcity = demand_ratio - 1
        if scarcity > 0.06:
            construction = int(1 + scarcity * 3 + state.government.infrastructure_budget * 4 + district.tech_level * 2)
            district.housing_supply += max(1, min(12, construction))
        target_rent = 520 + district.wealth * 2200 + district.density * 670 + max(0, scarcity) * 1600
        district.average_rent = round(district.average_rent * 0.84 + target_rent * 0.16, 2)
        district.happiness = clamp(district.happiness - max(0, scarcity) * 0.018 + district.infrastructure_quality * 0.006)
        district.wealth = clamp(district.wealth + (district.business_activity - 0.5) * 0.003 - max(0, scarcity) * 0.002)
        rents[district.id] = district.average_rent

    rent_burden = rents[citizens.home_district] / np.maximum(1, citizens.wealth / 36)
    rent_stress = np.clip((rent_burden - 0.32) / 1.1, 0, 1)
    citizens.stress = clamp_array(citizens.stress + rent_stress * 0.035)
    citizens.happiness = clamp_array(citizens.happiness - rent_stress * 0.028)

    move_probability = np.clip(rent_stress * 0.018 + citizens.risk_tolerance * 0.006, 0, 0.05)
    movers = rng.random(citizens.size) < move_probability
    if movers.any():
        affordability = (1.1 - pressure) * (0.35 + district_wealth) + np.array(
            [district.transit_access for district in state.districts], dtype=np.float32
        ) * 0.12
        affordability = np.maximum(0.01, affordability)
        affordability = affordability / affordability.sum()
        citizens.home_district[movers] = rng.choice(district_count, int(movers.sum()), p=affordability)
        citizens.memory_stress[movers] = clamp_array(citizens.memory_stress[movers] + 0.08)

    state.metrics["housing_pressure"] = float(np.mean(pressure))
    state.metrics["average_rent"] = float(np.mean(rents))
