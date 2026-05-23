from __future__ import annotations

import numpy as np

from app.simulation.world_state import WorldState, clamp, clamp_array


COALITIONS = [
    "Pragmatic Continuity Bloc",
    "Civic Autonomy Front",
    "Solar Labor Assembly",
    "Security Modernist League",
    "Distributed Commons Party",
]


def update_politics(state: WorldState) -> None:
    metrics = state.metrics
    approval_target = (
        0.32
        + metrics.get("happiness", 0.5) * 0.34
        + metrics.get("productivity", 0.5) * 0.12
        - metrics.get("unemployment", 0.1) * 0.45
        - metrics.get("crime", 0.2) * 0.18
        - metrics.get("housing_pressure", 0.2) * 0.16
        - metrics.get("blackout_risk", 0.0) * 0.22
        - state.government.corruption * 0.18
    )
    state.government.approval = clamp(state.government.approval * 0.9 + approval_target * 0.1)
    protest_intensity = clamp(
        (1 - state.government.approval) * 0.42
        + metrics.get("polarization", 0.0) * 0.24
        + metrics.get("stress", 0.0) * 0.18
        + metrics.get("housing_pressure", 0.0) * 0.22
        - state.government.surveillance * 0.08
    )
    metrics["approval"] = state.government.approval
    metrics["protest_intensity"] = protest_intensity

    if protest_intensity > 0.52:
        state.government.infrastructure_budget = clamp(state.government.infrastructure_budget + 0.009)
        state.government.policing_intensity = clamp(
            state.government.policing_intensity + (0.002 if metrics.get("crime", 0) > 0.45 else -0.002)
        )
        state.government.surveillance = clamp(state.government.surveillance - 0.002)
        state.government.corruption = clamp(state.government.corruption - 0.004)
        state.citizens.productivity = clamp_array(state.citizens.productivity - protest_intensity * 0.004)
        state.citizens.stress = clamp_array(state.citizens.stress - state.government.infrastructure_budget * 0.004)
    elif state.government.approval > 0.62:
        state.government.policing_intensity = clamp(state.government.policing_intensity - 0.003)
        state.government.infrastructure_budget = clamp(state.government.infrastructure_budget + 0.002)

    if metrics.get("blackout_risk", 0) > 0.18:
        state.government.infrastructure_budget = clamp(state.government.infrastructure_budget + 0.008)
        state.government.tax_rate = clamp(state.government.tax_rate + 0.001, 0.08, 0.42)
    if metrics.get("crime", 0) > 0.42:
        state.government.policing_intensity = clamp(state.government.policing_intensity + 0.006)
        state.government.surveillance = clamp(state.government.surveillance + 0.004)
    if metrics.get("housing_pressure", 0) > 0.35:
        state.government.tax_rate = clamp(state.government.tax_rate - 0.0008, 0.08, 0.42)
    if metrics.get("congestion", 0) > 0.62:
        worst = sorted(state.districts, key=lambda district: district.congestion, reverse=True)[: max(2, len(state.districts) // 4)]
        for district in worst:
            district.transit_access = clamp(district.transit_access + state.government.infrastructure_budget * 0.004)
            district.infrastructure_quality = clamp(district.infrastructure_quality + state.government.infrastructure_budget * 0.003)
        for road in state.roads:
            if any(road.source == district.id or road.target == district.id for district in worst):
                road.capacity = round(road.capacity * (1 + state.government.infrastructure_budget * 0.0015), 2)
    if metrics.get("unemployment", 0) > 0.16:
        state.government.tax_rate = clamp(state.government.tax_rate - 0.0012, 0.08, 0.42)
        for company in state.companies:
            if company.failure_risk < 0.55:
                company.open_roles += 1

    if state.day > 0 and state.day % state.government.election_cycle_day == 0:
        ideology_mean = float(np.mean(state.citizens.ideology))
        index = int(np.clip(round((ideology_mean + 1) / 2 * (len(COALITIONS) - 1)), 0, len(COALITIONS) - 1))
        if state.government.approval < 0.56:
            state.government.ruling_coalition = COALITIONS[index]
            state.government.corruption = clamp(state.government.corruption * 0.82)
