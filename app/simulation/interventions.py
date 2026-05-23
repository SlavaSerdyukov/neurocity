from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from app.simulation.world_state import ActiveIntervention, CityEvent, WorldState, clamp, clamp_array


@dataclass(frozen=True, slots=True)
class InterventionDefinition:
    kind: str
    name: str
    category: str
    duration: int
    description: str


INTERVENTION_CATALOG: dict[str, InterventionDefinition] = {
    "corruption_surge": InterventionDefinition(
        "corruption_surge",
        "Corruption Surge",
        "politics",
        70,
        "Private actors capture regulation, budgets, and enforcement priorities.",
    ),
    "dictator": InterventionDefinition(
        "dictator",
        "Emergency Directorate",
        "politics",
        120,
        "A security ruler suspends normal coalition politics and centralizes command.",
    ),
    "climate_disaster": InterventionDefinition(
        "climate_disaster",
        "Climate Disaster",
        "climate",
        55,
        "A heat dome and grid shock push pollution, health, and energy systems together.",
    ),
    "transit_strike": InterventionDefinition(
        "transit_strike",
        "Transit Strike",
        "transport",
        38,
        "Autonomous transit operators and maintenance swarms go offline.",
    ),
    "meme_panic": InterventionDefinition(
        "meme_panic",
        "Meme Panic",
        "culture",
        45,
        "A viral outrage loop mutates faster than institutional response.",
    ),
    "housing_boom": InterventionDefinition(
        "housing_boom",
        "Housing Boom",
        "housing",
        85,
        "Emergency construction robotics expand supply and cool rents.",
    ),
    "anti_corruption_drive": InterventionDefinition(
        "anti_corruption_drive",
        "Anti-Corruption Drive",
        "politics",
        65,
        "Audits, procurement transparency, and lobbying restrictions clean up the state.",
    ),
    "revolution": InterventionDefinition(
        "revolution",
        "Revolution",
        "politics",
        95,
        "Mass mobilization shuts down firms, fractures legitimacy, and redirects civic labor into street politics.",
    ),
    "war": InterventionDefinition(
        "war",
        "Regional War",
        "conflict",
        150,
        "A regional conflict disrupts logistics, destroys infrastructure, and drains capital from the civilian economy.",
    ),
}


CONTROL_PARAMETERS = {
    "corruption",
    "crime",
    "tax_rate",
    "infrastructure_budget",
    "policing_intensity",
    "surveillance",
}


def available_interventions() -> list[dict[str, Any]]:
    return [
        {
            "kind": definition.kind,
            "name": definition.name,
            "category": definition.category,
            "duration": definition.duration,
            "description": definition.description,
        }
        for definition in INTERVENTION_CATALOG.values()
    ]


def apply_intervention(
    state: WorldState,
    kind: str,
    severity: float = 0.55,
    target_district_id: int | None = None,
) -> CityEvent:
    if kind not in INTERVENTION_CATALOG:
        raise ValueError(f"unknown intervention kind: {kind}")
    definition = INTERVENTION_CATALOG[kind]
    severity = clamp(float(severity), 0.05, 1.0)
    target = _select_target_district(state, kind, target_district_id)
    duration = max(8, int(definition.duration * (0.72 + severity * 0.56)))
    intervention = ActiveIntervention(
        id=f"{definition.kind}:{state.tick}:{len(state.interventions)}",
        name=definition.name,
        category=definition.category,
        severity=severity,
        started_tick=state.tick,
        expires_tick=state.tick + duration,
        target_district_id=target.id if target else None,
    )
    state.interventions.append(intervention)
    state.interventions = state.interventions[-16:]
    event = _apply_immediate_effect(state, intervention, definition, target)
    state.events.append(event)
    state.events = state.events[-500:]
    return event


def set_government_parameter(state: WorldState, parameter: str, value: float) -> CityEvent:
    if parameter not in CONTROL_PARAMETERS:
        raise ValueError(f"unknown control parameter: {parameter}")
    old_value = _current_control_value(state, parameter)
    value = clamp(float(value), 0.0, 1.0)
    if parameter == "crime":
        _set_city_crime(state, value)
    else:
        setattr(state.government, parameter, value)
    if parameter == "corruption":
        state.metrics["approval"] = clamp(state.metrics.get("approval", state.government.approval) - max(0, value - old_value) * 0.16)
        state.government.approval = state.metrics["approval"]
    event = CityEvent(
        tick=state.tick,
        day=state.day,
        category="policy",
        severity=abs(value - old_value),
        title=f"{_label(parameter)} shifted to {value:.0%}",
        description=f"Government parameter changed from {old_value:.0%} to {value:.0%}.",
    )
    state.events.append(event)
    state.events = state.events[-500:]
    return event


def update_interventions(state: WorldState) -> None:
    if not state.interventions:
        state.metrics["active_interventions"] = 0.0
        return

    active: list[ActiveIntervention] = []
    for intervention in state.interventions:
        if intervention.expires_tick <= state.tick:
            _add_expiry_event(state, intervention)
            continue
        active.append(intervention)
        _apply_ongoing_effect(state, intervention)

    state.interventions = active[-16:]
    state.metrics["active_interventions"] = float(len(state.interventions))


def _select_target_district(state: WorldState, kind: str, target_district_id: int | None):
    if target_district_id is not None:
        for district in state.districts:
            if district.id == target_district_id:
                return district
    if kind == "climate_disaster":
        return max(state.districts, key=lambda district: district.pollution + district.density * 0.5)
    if kind == "transit_strike":
        return max(state.districts, key=lambda district: district.congestion + district.transit_access)
    if kind == "housing_boom":
        return max(state.districts, key=lambda district: district.housing_demand / max(1, district.housing_supply))
    if kind == "corruption_surge":
        return max(state.districts, key=lambda district: district.business_activity + district.wealth)
    if kind == "revolution":
        return max(state.districts, key=lambda district: district.unemployment + (1 - district.happiness) + district.crime * 0.5)
    if kind == "war":
        return max(state.districts, key=lambda district: district.business_activity + district.energy_demand / max(1, district.energy_capacity))
    return None


def _apply_immediate_effect(
    state: WorldState,
    intervention: ActiveIntervention,
    definition: InterventionDefinition,
    target,
) -> CityEvent:
    severity = intervention.severity
    kind = definition.kind
    title = definition.name
    description = definition.description
    if target:
        title = f"{definition.name} hits {target.name}"

    if kind == "corruption_surge":
        state.government.corruption = clamp(state.government.corruption + 0.22 * severity)
        state.government.approval = clamp(state.government.approval - 0.11 * severity)
        for company in state.companies:
            company.lobbying = clamp(company.lobbying + 0.08 * severity)
        if target:
            target.crime = clamp(target.crime + 0.16 * severity)
            target.infrastructure_quality = clamp(target.infrastructure_quality - 0.08 * severity)
    elif kind == "dictator":
        state.government.ruling_coalition = "Emergency Directorate"
        state.government.surveillance = clamp(state.government.surveillance + 0.34 * severity)
        state.government.policing_intensity = clamp(state.government.policing_intensity + 0.22 * severity)
        state.government.corruption = clamp(state.government.corruption + 0.08 * severity)
        state.government.approval = clamp(state.government.approval - 0.16 * severity)
        state.citizens.stress = clamp_array(state.citizens.stress + 0.09 * severity)
        state.citizens.ideology = np.clip(state.citizens.ideology + np.sign(state.citizens.ideology) * 0.05 * severity, -1, 1)
    elif kind == "climate_disaster":
        districts = [target] if target else state.districts
        for district in districts:
            district.energy_demand = round(district.energy_demand * (1 + 0.24 * severity), 2)
            district.pollution = clamp(district.pollution + 0.18 * severity)
            district.infrastructure_quality = clamp(district.infrastructure_quality - 0.12 * severity)
            district.happiness = clamp(district.happiness - 0.08 * severity)
    elif kind == "transit_strike":
        districts = [target] if target else state.districts
        district_ids = {district.id for district in districts}
        for district in districts:
            district.transit_access = clamp(district.transit_access - 0.22 * severity)
            district.congestion = clamp(district.congestion + 0.24 * severity)
            district.commute_index = clamp(district.commute_index + 0.18 * severity)
        for line in state.transit_lines:
            if district_ids.intersection(line.stops):
                line.reliability = clamp(line.reliability - 0.26 * severity)
        for road in state.roads:
            if road.source in district_ids or road.target in district_ids:
                road.congestion = clamp(road.congestion + 0.22 * severity)
    elif kind == "meme_panic":
        meme = max(state.memes, key=lambda item: item.novelty + item.outrage)
        meme.outrage = clamp(meme.outrage + 0.28 * severity)
        meme.adoption = clamp(meme.adoption + 0.14 * severity)
        meme.mutation = clamp(meme.mutation + 0.18 * severity)
        state.citizens.stress = clamp_array(state.citizens.stress + state.citizens.media_susceptibility * 0.07 * severity)
    elif kind == "housing_boom":
        districts = [target] if target else state.districts
        for district in districts:
            district.housing_supply += int(max(12, district.housing_demand * 0.08 * severity))
            district.average_rent = round(district.average_rent * (1 - 0.06 * severity), 2)
            district.infrastructure_quality = clamp(district.infrastructure_quality + 0.04 * severity)
    elif kind == "anti_corruption_drive":
        state.government.corruption = clamp(state.government.corruption - 0.24 * severity)
        state.government.approval = clamp(state.government.approval + 0.08 * severity)
        state.government.surveillance = clamp(state.government.surveillance - 0.08 * severity)
        for company in state.companies:
            company.lobbying = clamp(company.lobbying - 0.1 * severity)
    elif kind == "revolution":
        state.government.ruling_coalition = "Revolutionary Council"
        state.government.approval = clamp(state.government.approval - 0.22 * severity)
        state.government.tax_rate = clamp(state.government.tax_rate + 0.08 * severity, 0.08, 0.55)
        state.government.policing_intensity = clamp(state.government.policing_intensity + 0.12 * severity)
        state.metrics["protest_intensity"] = clamp(max(state.metrics.get("protest_intensity", 0), 0.74 * severity))
        state.citizens.stress = clamp_array(state.citizens.stress + 0.16 * severity)
        state.citizens.happiness = clamp_array(state.citizens.happiness - 0.12 * severity)
        _shock_companies(state, capital_loss=0.18 * severity, productivity_loss=0.16 * severity, layoff_rate=0.08 * severity)
        if target:
            target.business_activity = clamp(target.business_activity - 0.28 * severity)
            target.infrastructure_quality = clamp(target.infrastructure_quality - 0.1 * severity)
            target.crime = clamp(target.crime + 0.18 * severity)
    elif kind == "war":
        state.government.ruling_coalition = "War Cabinet"
        state.government.tax_rate = clamp(state.government.tax_rate + 0.11 * severity, 0.08, 0.62)
        state.government.infrastructure_budget = clamp(state.government.infrastructure_budget - 0.12 * severity)
        state.government.policing_intensity = clamp(state.government.policing_intensity + 0.2 * severity)
        state.government.surveillance = clamp(state.government.surveillance + 0.16 * severity)
        state.citizens.stress = clamp_array(state.citizens.stress + 0.18 * severity)
        state.citizens.productivity = clamp_array(state.citizens.productivity - 0.11 * severity)
        _shock_companies(state, capital_loss=0.28 * severity, productivity_loss=0.22 * severity, layoff_rate=0.12 * severity)
        for district in state.districts:
            district.infrastructure_quality = clamp(district.infrastructure_quality - 0.13 * severity)
            district.energy_capacity = round(district.energy_capacity * (1 - 0.08 * severity), 2)
            district.business_activity = clamp(district.business_activity - 0.16 * severity)
            district.congestion = clamp(district.congestion + 0.1 * severity)
        for road in state.roads:
            road.capacity = round(max(40, road.capacity * (1 - 0.16 * severity)), 2)
            road.congestion = clamp(road.congestion + 0.14 * severity)

    return CityEvent(
        tick=state.tick,
        day=state.day,
        category=definition.category,
        severity=severity,
        title=title,
        description=description,
        district_id=target.id if target else None,
    )


def _apply_ongoing_effect(state: WorldState, intervention: ActiveIntervention) -> None:
    severity = intervention.severity
    target = None
    if intervention.target_district_id is not None:
        target = next((district for district in state.districts if district.id == intervention.target_district_id), None)

    if intervention.id.startswith("corruption_surge"):
        state.government.corruption = clamp(state.government.corruption + 0.0014 * severity)
        state.government.approval = clamp(state.government.approval - 0.0009 * severity)
        for district in state.districts:
            district.crime = clamp(district.crime + district.unemployment * 0.0018 * severity)
        state.citizens.crime_propensity = clamp_array(state.citizens.crime_propensity + 0.0007 * severity)
    elif intervention.id.startswith("dictator"):
        state.government.surveillance = clamp(max(state.government.surveillance, 0.58 + 0.3 * severity))
        state.government.policing_intensity = clamp(max(state.government.policing_intensity, 0.52 + 0.22 * severity))
        state.government.corruption = clamp(state.government.corruption + 0.0005 * severity)
        state.metrics["protest_intensity"] = clamp(state.metrics.get("protest_intensity", 0) * (1 - 0.18 * severity))
        state.citizens.stress = clamp_array(state.citizens.stress + 0.0028 * severity)
        state.citizens.happiness = clamp_array(state.citizens.happiness - 0.0018 * severity)
    elif intervention.id.startswith("climate_disaster"):
        districts = [target] if target else state.districts
        for district in districts:
            district.energy_demand = round(district.energy_demand * (1 + 0.006 * severity), 2)
            district.pollution = clamp(district.pollution + 0.0032 * severity)
            district.infrastructure_quality = clamp(district.infrastructure_quality - 0.0025 * severity)
        affected_ids = {district.id for district in districts}
        affected = np.isin(state.citizens.home_district, list(affected_ids))
        state.citizens.health[affected] = clamp_array(state.citizens.health[affected] - 0.0045 * severity)
        state.citizens.stress[affected] = clamp_array(state.citizens.stress[affected] + 0.006 * severity)
    elif intervention.id.startswith("transit_strike"):
        districts = [target] if target else state.districts
        district_ids = {district.id for district in districts}
        for district in districts:
            district.congestion = clamp(district.congestion + 0.005 * severity)
            district.transit_access = clamp(district.transit_access - 0.003 * severity)
        for road in state.roads:
            if road.source in district_ids or road.target in district_ids:
                road.congestion = clamp(road.congestion + 0.0055 * severity)
    elif intervention.id.startswith("meme_panic"):
        for meme in state.memes:
            meme.outrage = clamp(meme.outrage + meme.adoption * 0.004 * severity)
            meme.mutation = clamp(meme.mutation + 0.002 * severity)
        state.metrics["polarization"] = clamp(state.metrics.get("polarization", 0) + 0.003 * severity)
    elif intervention.id.startswith("housing_boom"):
        districts = [target] if target else state.districts
        for district in districts:
            district.housing_supply += max(1, int(district.housing_demand * 0.002 * severity))
            district.average_rent = round(district.average_rent * (1 - 0.0018 * severity), 2)
    elif intervention.id.startswith("anti_corruption_drive"):
        state.government.corruption = clamp(state.government.corruption - 0.0022 * severity)
        state.government.approval = clamp(state.government.approval + 0.0009 * severity)
        for company in state.companies:
            company.lobbying = clamp(company.lobbying - 0.0018 * severity)
    elif intervention.id.startswith("revolution"):
        state.metrics["protest_intensity"] = clamp(max(state.metrics.get("protest_intensity", 0), 0.58 * severity))
        state.citizens.stress = clamp_array(state.citizens.stress + 0.004 * severity)
        state.citizens.productivity = clamp_array(state.citizens.productivity - 0.0035 * severity)
        _shock_companies(state, capital_loss=0.006 * severity, productivity_loss=0.0045 * severity, layoff_rate=0.006 * severity)
        for district in state.districts:
            district.business_activity = clamp(district.business_activity - 0.006 * severity)
            district.infrastructure_quality = clamp(district.infrastructure_quality - 0.0025 * severity)
            district.crime = clamp(district.crime + 0.0025 * severity)
    elif intervention.id.startswith("war"):
        state.citizens.stress = clamp_array(state.citizens.stress + 0.005 * severity)
        state.citizens.productivity = clamp_array(state.citizens.productivity - 0.0048 * severity)
        _shock_companies(state, capital_loss=0.008 * severity, productivity_loss=0.006 * severity, layoff_rate=0.007 * severity)
        for district in state.districts:
            district.infrastructure_quality = clamp(district.infrastructure_quality - 0.0036 * severity)
            district.energy_capacity = round(max(20, district.energy_capacity * (1 - 0.0022 * severity)), 2)
            district.business_activity = clamp(district.business_activity - 0.007 * severity)
            district.pollution = clamp(district.pollution + 0.0028 * severity)
        for road in state.roads:
            road.capacity = round(max(40, road.capacity * (1 - 0.0025 * severity)), 2)
            road.congestion = clamp(road.congestion + 0.0032 * severity)


def _add_expiry_event(state: WorldState, intervention: ActiveIntervention) -> None:
    if any(event.tick == state.tick and event.title == f"{intervention.name} pressure fades" for event in state.events[-12:]):
        return
    state.events.append(
        CityEvent(
            tick=state.tick,
            day=state.day,
            category=intervention.category,
            severity=max(0.08, intervention.severity * 0.35),
            title=f"{intervention.name} pressure fades",
            description="The direct intervention expires, leaving only systemic aftershocks in the city state.",
            district_id=intervention.target_district_id,
        )
    )
    state.events = state.events[-500:]


def _label(parameter: str) -> str:
    return parameter.replace("_", " ").title()


def _current_control_value(state: WorldState, parameter: str) -> float:
    if parameter == "crime":
        return float(state.metrics.get("crime", np.mean([district.crime for district in state.districts])))
    return float(getattr(state.government, parameter))


def _set_city_crime(state: WorldState, value: float) -> None:
    current = max(0.001, float(np.mean([district.crime for district in state.districts])))
    ratio = value / current
    for district in state.districts:
        district.crime = value
        district.happiness = clamp(district.happiness - max(0, value - current) * 0.08)
    state.citizens.crime_propensity = clamp_array(state.citizens.crime_propensity * (0.55 + ratio * 0.45))
    state.citizens.stress = clamp_array(state.citizens.stress + max(0, value - current) * 0.06)
    state.metrics["crime"] = float(np.mean([district.crime for district in state.districts]))


def _shock_companies(
    state: WorldState,
    capital_loss: float,
    productivity_loss: float,
    layoff_rate: float,
) -> None:
    rng = state.rng(91)
    company_layoff_pressure = 0.0
    for company in state.companies:
        disruption = float(np.clip(0.78 + rng.random() * 0.44, 0.78, 1.22))
        company.capital = round(max(0, company.capital * (1 - capital_loss * disruption)), 2)
        company.productivity = float(np.clip(company.productivity * (1 - productivity_loss * disruption), 0.03, 1.6))
        company.failure_risk = clamp(company.failure_risk + (capital_loss + productivity_loss) * 0.72)
        layoffs = int(company.employees * min(0.8, layoff_rate * disruption))
        if layoffs > 0:
            company.employees = max(1, company.employees - layoffs)
            company.open_roles = max(0, company.open_roles - layoffs)
            company_layoff_pressure += layoffs
        else:
            company.open_roles = max(0, int(company.open_roles * (1 - layoff_rate)))

    if company_layoff_pressure <= 0:
        return
    employed_indices = np.flatnonzero(state.citizens.employed)
    if employed_indices.size == 0:
        return
    citizen_layoff_count = int(min(employed_indices.size, max(1, company_layoff_pressure)))
    selected = rng.choice(employed_indices, citizen_layoff_count, replace=False)
    state.citizens.employed[selected] = False
    state.citizens.stress[selected] = clamp_array(state.citizens.stress[selected] + min(0.28, layoff_rate * 1.4))
    state.citizens.happiness[selected] = clamp_array(state.citizens.happiness[selected] - min(0.22, layoff_rate))
