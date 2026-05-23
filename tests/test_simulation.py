from __future__ import annotations

import json
import time
import warnings

import numpy as np
import pytest

from app.simulation.engine import SimulationEngine
from app.simulation.event_system import EventSystem
from app.simulation.interventions import apply_intervention, set_government_parameter
from app.simulation.procedural import create_world
from app.simulation.world_state import WorldState


def rounded_metrics(engine: SimulationEngine) -> dict[str, float]:
    keys = [
        "gdp",
        "unemployment",
        "inflation",
        "productivity",
        "happiness",
        "stress",
        "polarization",
        "crime",
        "energy_margin",
        "housing_pressure",
        "congestion",
    ]
    return {key: round(float(engine.state.metrics[key]), 6) for key in keys}


def test_tick_consistency_is_deterministic() -> None:
    first = SimulationEngine(create_world(seed=77, population=1200, district_count=10))
    second = SimulationEngine(create_world(seed=77, population=1200, district_count=10))

    first.step(35)
    second.step(35)

    assert rounded_metrics(first) == rounded_metrics(second)
    assert [event.to_dict() for event in first.state.events] == [event.to_dict() for event in second.state.events]


def test_save_load_replay_continues_identically() -> None:
    baseline = SimulationEngine(create_world(seed=91, population=900, district_count=9))
    baseline.step(12)
    payload = json.loads(json.dumps(baseline.state.to_dict()))
    restored = SimulationEngine(WorldState.from_dict(payload))

    baseline.step(18)
    restored.step(18)

    restored_metrics = rounded_metrics(restored)
    baseline_metrics = rounded_metrics(baseline)
    assert restored_metrics.pop("gdp") == pytest.approx(baseline_metrics.pop("gdp"), rel=1e-8)
    assert restored_metrics == baseline_metrics
    assert restored.state.newspaper == baseline.state.newspaper


def test_interventions_are_serialized_and_continue_after_load() -> None:
    baseline = SimulationEngine(create_world(seed=101, population=900, district_count=9))
    apply_intervention(baseline.state, "climate_disaster", 0.75)
    payload = json.loads(json.dumps(baseline.state.to_dict()))
    restored = SimulationEngine(WorldState.from_dict(payload))

    assert restored.state.interventions[0].name == "Climate Disaster"
    assert restored.state.events[-1].category == "climate"

    restored.step(3)

    assert restored.state.metrics["active_interventions"] == 1.0
    assert restored.state.interventions[0].expires_tick > restored.state.tick


def test_revolution_and_war_are_severe_gdp_shocks() -> None:
    baseline = SimulationEngine(create_world(seed=222, population=1400, district_count=10))
    revolution = SimulationEngine(create_world(seed=222, population=1400, district_count=10))
    war = SimulationEngine(create_world(seed=222, population=1400, district_count=10))

    apply_intervention(revolution.state, "revolution", 0.9)
    apply_intervention(war.state, "war", 0.9)
    baseline.step(3)
    revolution.step(3)
    war.step(3)

    assert revolution.state.metrics["gdp"] < baseline.state.metrics["gdp"] * 0.86
    assert war.state.metrics["gdp"] < baseline.state.metrics["gdp"] * 0.8
    assert war.state.metrics["unemployment"] > baseline.state.metrics["unemployment"]


def test_collapsed_job_market_keeps_tick_loop_alive() -> None:
    engine = SimulationEngine(create_world(seed=333, population=1000, district_count=9))
    for district in engine.state.districts:
        district.business_activity = 0.0
    engine.state.citizens.employed[:] = False

    engine.step(4)

    assert engine.state.tick == 4
    assert engine.state.citizens.work_district.min() >= 0
    assert engine.state.citizens.work_district.max() < len(engine.state.districts)


def test_extreme_intervention_stack_does_not_crash_simulation() -> None:
    engine = SimulationEngine(create_world(seed=444, population=1200, district_count=10))
    for kind in ("war", "revolution", "war", "corruption_surge", "transit_strike"):
        apply_intervention(engine.state, kind, 1.0)
    set_government_parameter(engine.state, "crime", 1.0)

    engine.step(30)

    assert engine.state.tick == 30
    assert np.isfinite(engine.state.metrics["gdp"])
    assert np.isfinite(engine.state.metrics["crime"])


def test_nonfinite_loaded_economic_values_are_sanitized_without_runtime_warnings() -> None:
    engine = SimulationEngine(create_world(seed=555, population=1000, district_count=9))
    engine.state.companies[0].wage = float("inf")
    engine.state.companies[0].capital = float("inf")
    engine.state.companies[0].employees = 10**80
    engine.state.companies[1].wage = float("nan")
    engine.state.citizens.wealth[:8] = np.inf

    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        engine.step(4)

    assert np.isfinite(engine.state.metrics["gdp"])
    assert engine.state.companies[0].wage <= 1_000_000
    assert engine.state.companies[0].employees <= 500_000
    assert np.isfinite(engine.state.citizens.wealth).all()


def test_economy_and_citizen_behavior_update() -> None:
    engine = SimulationEngine(create_world(seed=1337, population=1500, district_count=11))
    initial_stress = float(engine.state.citizens.stress.mean())
    initial_gdp = engine.state.metrics["gdp"]

    engine.step(10)

    assert engine.state.metrics["gdp"] > 0
    assert engine.state.metrics["gdp"] != pytest.approx(initial_gdp)
    assert engine.state.metrics["unemployment"] >= 0
    assert float(engine.state.citizens.stress.mean()) != pytest.approx(initial_stress)
    assert len(engine.state.history) == 10


def test_event_generation_from_systemic_pressure() -> None:
    engine = SimulationEngine(create_world(seed=22, population=800, district_count=8))
    district = engine.state.districts[0]
    district.congestion = 0.91
    district.housing_demand = int(district.housing_supply * 1.34)
    district.energy_demand = district.energy_capacity * 1.4
    engine.state.metrics["protest_intensity"] = 0.64

    events = EventSystem(cooldown_ticks=0).evaluate(engine.state)
    categories = {event.category for event in events}

    assert {"transport", "housing", "energy", "politics"}.issubset(categories)


def test_performance_target_for_5000_citizens() -> None:
    engine = SimulationEngine(create_world(seed=5, population=5000, district_count=14))
    started = time.perf_counter()
    engine.step(20)
    elapsed = time.perf_counter() - started

    assert elapsed < 8.0
    assert engine.state.citizens.size == 5000
    assert len(engine.state.history) == 20


def test_long_run_keeps_recovery_loops_alive() -> None:
    engine = SimulationEngine(create_world(seed=2049, population=5000, district_count=14))

    engine.step(300)
    metrics = engine.state.metrics

    assert metrics["productivity"] > 0.2
    assert metrics["stress"] < 0.75
    assert metrics["congestion"] < 0.9
    assert metrics["approval"] > 0.25
    assert metrics["gdp"] > 0
