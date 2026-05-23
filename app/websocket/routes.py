from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.simulation.engine import SimulationEngine


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
                await engine.step_async(int(message.get("steps", 1)))
            elif action == "reset":
                await engine.reset(seed=message.get("seed"), population=message.get("population"))
    except WebSocketDisconnect:
        engine.unsubscribe(sender)

