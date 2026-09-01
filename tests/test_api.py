from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.simulation.engine import SimulationEngine
from app.simulation.limits import MAX_PUBLIC_POPULATION, MIN_PUBLIC_POPULATION
from app.simulation.procedural import create_world


def test_dashboard_and_core_api_endpoints() -> None:
    with TestClient(app) as client:
        dashboard = client.get("/dashboard")
        assert dashboard.status_code == 200
        assert "NEUROCITY" in dashboard.text
        assert 'rel="icon"' in dashboard.text

        favicon = client.get("/favicon.ico")
        assert favicon.status_code == 200
        assert favicon.headers["content-type"].startswith("image/svg+xml")

        city = client.get("/city")
        assert city.status_code == 200
        payload = city.json()
        assert payload["tick"] == 0
        assert len(payload["districts"]) >= 8
        assert len(payload["citizens"]) > 0

        ticked = client.post("/simulation/tick?steps=3")
        assert ticked.status_code == 200
        assert ticked.json()["tick"] == 3

        assert client.get("/districts").status_code == 200
        assert client.get("/citizens?limit=10").status_code == 200
        assert client.get("/economy").status_code == 200
        assert client.get("/events").status_code == 200
        assert client.get("/interventions").status_code == 200


def test_public_reset_population_is_bounded_for_http_and_websocket() -> None:
    with TestClient(app) as client:
        too_small = client.post("/simulation/reset", json={"population": MIN_PUBLIC_POPULATION - 1})
        too_large = client.post("/simulation/reset", json={"population": MAX_PUBLIC_POPULATION + 1})
        assert too_small.status_code == 422
        assert too_large.status_code == 422

        with client.websocket_connect("/ws/simulation") as websocket:
            websocket.receive_json()
            websocket.send_json({"action": "reset", "population": 1})
            websocket.receive_json()
            assert app.state.engine.state.citizens.size == MIN_PUBLIC_POPULATION


def test_save_load_and_websocket_initial_snapshot() -> None:
    with TestClient(app) as client:
        client.post("/simulation/tick?steps=4")
        saved = client.post("/save", json={"name": "pytest-save"})
        assert saved.status_code == 200
        save_id = saved.json()["id"]

        client.post("/simulation/tick?steps=2")
        loaded = client.post("/load", json={"id": save_id})
        assert loaded.status_code == 200
        assert loaded.json()["tick"] == 4

        with client.websocket_connect("/ws/simulation") as websocket:
            snapshot = websocket.receive_json()
            assert snapshot["tick"] == 4
            websocket.send_json({"action": "tick", "steps": 1})
            updated = websocket.receive_json()
            assert updated["tick"] == 5
            websocket.send_json({"action": "intervention", "kind": "meme_panic", "severity": 0.6})
            intervened = websocket.receive_json()
            assert intervened["interventions"][-1]["name"] == "Meme Panic"


def test_load_empty_named_slot_is_noop_snapshot() -> None:
    with TestClient(app) as client:
        missing = client.post("/load", json={"name": "pytest-missing-save-slot"})
        assert missing.status_code == 200
        payload = missing.json()
        assert payload["load_status"]["loaded"] is False
        assert payload["tick"] == 0

        missing_id = client.post("/load", json={"id": -1})
        assert missing_id.status_code == 404


def test_intervention_and_policy_api_update_city_state() -> None:
    with TestClient(app) as client:
        catalog = client.get("/interventions")
        assert catalog.status_code == 200
        kinds = {item["kind"] for item in catalog.json()}
        assert {"dictator", "revolution", "war"}.issubset(kinds)

        intervention = client.post("/intervention", json={"kind": "dictator", "severity": 0.7})
        assert intervention.status_code == 200
        payload = intervention.json()
        assert payload["government"]["ruling_coalition"] == "Emergency Directorate"
        assert payload["interventions"][0]["name"] == "Emergency Directorate"
        assert payload["events"][-1]["category"] == "politics"

        policy = client.post("/policy", json={"parameter": "corruption", "value": 0.82})
        assert policy.status_code == 200
        assert policy.json()["government"]["corruption"] == 0.82

        crime = client.post("/policy", json={"parameter": "crime", "value": 0.74})
        assert crime.status_code == 200
        assert crime.json()["metrics"]["crime"] == pytest.approx(0.74)

        invalid = client.post("/intervention", json={"kind": "moonfall", "severity": 0.5})
        assert invalid.status_code == 400


def test_engine_records_system_error_and_pauses(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.simulation.engine as engine_module

    def failing_system(_state) -> None:
        raise RuntimeError("synthetic subsystem failure")

    monkeypatch.setattr(engine_module, "run_systems", failing_system)
    engine = SimulationEngine(create_world(seed=19, population=200))
    engine.set_speed(20)

    snapshot = asyncio.run(engine.step_async())

    assert snapshot["running"] is False
    assert snapshot["speed"] == 0
    assert snapshot["engine_error"] == "RuntimeError: synthetic subsystem failure"
    assert snapshot["events"][-1]["category"] == "system"
    assert "synthetic subsystem failure" in snapshot["events"][-1]["description"]
