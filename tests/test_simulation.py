from __future__ import annotations

import json
import time

import pytest

from app.simulation.engine import SimulationEngine
from app.simulation.event_system import EventSystem
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
