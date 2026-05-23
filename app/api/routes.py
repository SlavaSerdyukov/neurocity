from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.database import SimulationSave, get_session, latest_save
from app.simulation.engine import SimulationEngine
from app.simulation.world_state import WorldState


router = APIRouter()


class SpeedRequest(BaseModel):
    speed: int = Field(..., description="0, 1, 5, 20, or 100")


class ResetRequest(BaseModel):
    seed: int | None = None
    population: int | None = None


class SaveRequest(BaseModel):
    name: str = "autosave"


class LoadRequest(BaseModel):
    id: int | None = None
    name: str | None = None


def get_engine(request: Request) -> SimulationEngine:
    return request.app.state.engine


@router.get("/city")
def city(engine: Annotated[SimulationEngine, Depends(get_engine)]) -> dict:
    return engine.snapshot()


@router.get("/districts")
def districts(engine: Annotated[SimulationEngine, Depends(get_engine)]) -> list[dict]:
    return [district.to_dict() for district in engine.state.districts]


@router.get("/citizens")
def citizens(engine: Annotated[SimulationEngine, Depends(get_engine)], limit: int = 120) -> list[dict]:
    return engine.state.citizens.sample(min(max(limit, 1), 500))


@router.get("/economy")
def economy(engine: Annotated[SimulationEngine, Depends(get_engine)]) -> dict:
    return {
        "metrics": {
            key: engine.state.metrics.get(key)
            for key in ("gdp", "unemployment", "inflation", "productivity", "average_rent", "housing_pressure")
        },
        "companies": [company.to_dict() for company in engine.state.companies],
    }


@router.get("/events")
def events(engine: Annotated[SimulationEngine, Depends(get_engine)], limit: int = 100) -> list[dict]:
    return [event.to_dict() for event in engine.state.events[-min(max(limit, 1), 300) :]]


@router.post("/simulation/start")
async def start(engine: Annotated[SimulationEngine, Depends(get_engine)], payload: SpeedRequest | None = None) -> dict:
    await engine.start(payload.speed if payload else 1)
    return engine.snapshot()


@router.post("/simulation/pause")
def pause(engine: Annotated[SimulationEngine, Depends(get_engine)]) -> dict:
    engine.pause()
    return engine.snapshot()


@router.post("/simulation/reset")
async def reset(engine: Annotated[SimulationEngine, Depends(get_engine)], payload: ResetRequest | None = None) -> dict:
    payload = payload or ResetRequest()
    return await engine.reset(seed=payload.seed, population=payload.population)


@router.post("/simulation/speed")
async def speed(engine: Annotated[SimulationEngine, Depends(get_engine)], payload: SpeedRequest) -> dict:
    engine.set_speed(payload.speed)
    if payload.speed > 0:
        await engine.start(payload.speed)
    return engine.snapshot()


@router.post("/simulation/tick")
async def tick(engine: Annotated[SimulationEngine, Depends(get_engine)], steps: int = 1) -> dict:
    return await engine.step_async(min(max(steps, 1), 250))


@router.post("/save")
def save(
    engine: Annotated[SimulationEngine, Depends(get_engine)],
    payload: SaveRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    record = SimulationSave(
        name=payload.name,
        tick=engine.state.tick,
        payload_json=json.dumps(engine.state.to_dict(), separators=(",", ":")),
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return {"id": record.id, "name": record.name, "tick": record.tick, "created_at": record.created_at.isoformat()}


@router.post("/load")
def load(
    engine: Annotated[SimulationEngine, Depends(get_engine)],
    payload: LoadRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    record: SimulationSave | None
    if payload.id is not None:
        record = session.exec(select(SimulationSave).where(SimulationSave.id == payload.id)).first()
    else:
        record = latest_save(session, payload.name)
    if record is None:
        if payload.id is None:
            snapshot = engine.snapshot()
            snapshot["load_status"] = {
                "loaded": False,
                "message": "No matching simulation save found; keeping the current city state.",
            }
            return snapshot
        raise HTTPException(status_code=404, detail="No matching simulation save found")
    state = WorldState.from_dict(json.loads(record.payload_json))
    snapshot = engine.load_state(state)
    snapshot["load_status"] = {
        "loaded": True,
        "id": record.id,
        "name": record.name,
        "tick": record.tick,
        "created_at": record.created_at.isoformat(),
    }
    return snapshot
