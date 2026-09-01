from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.simulation.engine import SimulationEngine
from app.simulation.limits import (
    MAX_MANUAL_TICK_STEPS,
    MAX_PUBLIC_POPULATION,
    MIN_PUBLIC_POPULATION,
    clamp_int,
)


router = APIRouter()


@router.websocket("/ws/simulation")
async def simulation_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    engine: SimulationEngine = websocket.app.state.engine

    async def sender(snapshot: dict) -> None:
        await websocket.send_json(snapshot)

    engine.subscribe(sender)
    await sender(engine.snapshot())
    try:
        while True:
            message = await websocket.receive_json()
            action = message.get("action")
            if action == "start":
                await engine.start(int(message.get("speed", 1)))
            elif action == "pause":
                engine.pause()
                await sender(engine.snapshot())
            elif action == "speed":
                engine.set_speed(int(message.get("speed", 1)))
            elif action == "tick":
                steps = clamp_int(
                    message.get("steps", 1),
                    default=1,
                    minimum=1,
                    maximum=MAX_MANUAL_TICK_STEPS,
                )
                await engine.step_async(steps)
            elif action == "reset":
                raw_population = message.get("population")
                population = None
                if raw_population is not None:
                    population = clamp_int(
                        raw_population,
                        default=MIN_PUBLIC_POPULATION,
                        minimum=MIN_PUBLIC_POPULATION,
                        maximum=MAX_PUBLIC_POPULATION,
                    )
                await engine.reset(seed=message.get("seed"), population=population)
            elif action == "intervention":
                await engine.apply_intervention_async(
                    str(message.get("kind", "")),
                    min(max(float(message.get("severity", 0.55)), 0.05), 1.0),
                    message.get("target_district_id"),
                )
            elif action == "policy":
                await engine.set_government_parameter_async(
                    str(message.get("parameter", "")),
                    min(max(float(message.get("value", 0.0)), 0.0), 1.0),
                )
    except WebSocketDisconnect:
        pass
    finally:
        engine.unsubscribe(sender)
