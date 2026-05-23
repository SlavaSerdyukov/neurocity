from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


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
