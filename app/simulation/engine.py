from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from app.simulation.ai.narrative_generator import deterministic_newspaper
from app.simulation.event_system import EventSystem
from app.simulation.interventions import apply_intervention, set_government_parameter
from app.simulation.procedural import create_world
from app.simulation.scheduler import run_systems
from app.simulation.tick_manager import SimulationSpeed, speed_delay
from app.simulation.world_state import WorldState


Subscriber = Callable[[dict], Awaitable[None]]


class SimulationEngine:
    def __init__(self, state: WorldState | None = None) -> None:
        self.state = state or create_world()
        self.event_system = EventSystem()
        self.speed = SimulationSpeed.PAUSED
        self._task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self._subscribers: set[Subscriber] = set()

    @property
    def running(self) -> bool:
        return self.speed != SimulationSpeed.PAUSED

    def subscribe(self, subscriber: Subscriber) -> None:
        self._subscribers.add(subscriber)

    def unsubscribe(self, subscriber: Subscriber) -> None:
        self._subscribers.discard(subscriber)

    async def start(self, speed: int | None = None) -> None:
        self.set_speed(speed or SimulationSpeed.NORMAL)
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run_loop())

    def pause(self) -> None:
        self.speed = SimulationSpeed.PAUSED

    def set_speed(self, speed: int) -> None:
        allowed = {0, 1, 5, 20, 100}
        if int(speed) not in allowed:
            raise ValueError("speed must be one of 0, 1, 5, 20, 100")
        self.speed = SimulationSpeed(int(speed))

    async def reset(self, seed: int | None = None, population: int | None = None) -> dict:
        async with self._lock:
            self.state = create_world(seed=seed, population=population)
            self.speed = SimulationSpeed.PAUSED
            snapshot = self.snapshot()
        await self._broadcast(snapshot)
        return snapshot

    def load_state(self, state: WorldState) -> dict:
        self.state = state
        self.speed = SimulationSpeed.PAUSED
        return self.snapshot()

    async def apply_intervention_async(
        self,
        kind: str,
        severity: float = 0.55,
        target_district_id: int | None = None,
    ) -> dict:
        async with self._lock:
            apply_intervention(self.state, kind, severity, target_district_id)
            snapshot = self.snapshot()
        await self._broadcast(snapshot)
        return snapshot

    async def set_government_parameter_async(self, parameter: str, value: float) -> dict:
        async with self._lock:
            set_government_parameter(self.state, parameter, value)
            snapshot = self.snapshot()
        await self._broadcast(snapshot)
        return snapshot

    def step(self, steps: int = 1) -> dict:
        for _ in range(max(1, steps)):
            self.state.tick += 1
            self.state.day = self.state.tick
            run_systems(self.state)
            new_events = self.event_system.evaluate(self.state)
            self.state.newspaper = deterministic_newspaper(self.state, new_events)
            self._record_history()
        return self.snapshot()

    def snapshot(self) -> dict:
        payload = self.state.public_snapshot()
        payload["running"] = self.running
        payload["speed"] = int(self.speed)
        return payload

    async def step_async(self, steps: int = 1) -> dict:
        async with self._lock:
            snapshot = self.step(steps)
        await self._broadcast(snapshot)
        return snapshot

    async def _run_loop(self) -> None:
        while True:
            if self.speed == SimulationSpeed.PAUSED:
                await asyncio.sleep(0.25)
                if not self._subscribers:
                    continue
            else:
                await self.step_async()
                await asyncio.sleep(speed_delay(int(self.speed)))

    async def _broadcast(self, snapshot: dict) -> None:
        if not self._subscribers:
            return
        dead: list[Subscriber] = []
        for subscriber in list(self._subscribers):
            try:
                await subscriber(snapshot)
            except Exception:
                dead.append(subscriber)
        for subscriber in dead:
            self.unsubscribe(subscriber)

    def _record_history(self) -> None:
        metrics = self.state.metrics
        self.state.history.append(
            {
                "tick": float(self.state.tick),
                "gdp": float(metrics.get("gdp", 0)),
                "unemployment": float(metrics.get("unemployment", 0)),
                "inflation": float(metrics.get("inflation", 0)),
                "happiness": float(metrics.get("happiness", 0)),
                "stress": float(metrics.get("stress", 0)),
                "polarization": float(metrics.get("polarization", 0)),
                "crime": float(metrics.get("crime", 0)),
                "energy_margin": float(metrics.get("energy_margin", 0)),
                "housing_pressure": float(metrics.get("housing_pressure", 0)),
                "congestion": float(metrics.get("congestion", 0)),
                "approval": float(metrics.get("approval", 0)),
            }
        )
        self.state.history = self.state.history[-2000:]
