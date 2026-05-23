from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
from typing import Any

import numpy as np


MAX_COMPANY_EMPLOYEES = 500_000
MAX_COMPANY_OPEN_ROLES = 500_000
MAX_COMPANY_WAGE = 1_000_000.0
MAX_COMPANY_CAPITAL = 10_000_000_000.0
MAX_CITIZEN_WEALTH = 100_000_000.0


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return float(max(low, min(high, value)))


def clamp_array(values: np.ndarray, low: float = 0.0, high: float = 1.0) -> np.ndarray:
    return np.clip(values, low, high)


def finite_float(
    value: Any,
    default: float = 0.0,
    low: float | None = None,
    high: float | None = None,
) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        result = default
    if not math.isfinite(result):
        result = default
    if low is not None:
        result = max(low, result)
    if high is not None:
        result = min(high, result)
    return float(result)


def finite_int(
    value: Any,
    default: int = 0,
    low: int | None = None,
    high: int | None = None,
) -> int:
    result = int(finite_float(value, float(default), None, None))
    if low is not None:
        result = max(low, result)
    if high is not None:
        result = min(high, result)
    return result


@dataclass(slots=True)
class District:
    id: int
    name: str
    archetype: str
    x: float
    y: float
    polygon: list[list[float]]
    wealth: float
    density: float
    pollution: float
    crime: float
    happiness: float
    political_leaning: float
    infrastructure_quality: float
    transit_access: float
    housing_supply: int
    housing_demand: int
    average_rent: float
    energy_capacity: float
    energy_demand: float
    commute_index: float
    congestion: float
    unemployment: float
    business_activity: float
    tech_level: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "District":
        return cls(**payload)


@dataclass(slots=True)
class Road:
    source: int
    target: int
    capacity: float
    congestion: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TransitLine:
    id: int
    name: str
    stops: list[int]
    capacity: float
    reliability: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Company:
    id: int
    name: str
    sector: str
    district_id: int
    employees: int
    open_roles: int
    wage: float
    capital: float
    productivity: float
    lobbying: float
    failure_risk: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def sanitize(self, district_count: int | None = None) -> None:
        max_district = None if district_count is None else max(0, district_count - 1)
        self.id = finite_int(self.id, low=0)
        self.district_id = finite_int(self.district_id, low=0, high=max_district)
        self.employees = finite_int(self.employees, default=1, low=1, high=MAX_COMPANY_EMPLOYEES)
        self.open_roles = finite_int(self.open_roles, default=0, low=0, high=MAX_COMPANY_OPEN_ROLES)
        self.wage = finite_float(self.wage, default=60_000.0, low=18_000.0, high=MAX_COMPANY_WAGE)
        self.capital = finite_float(self.capital, default=0.0, low=0.0, high=MAX_COMPANY_CAPITAL)
        self.productivity = finite_float(self.productivity, default=0.5, low=0.03, high=1.6)
        self.lobbying = finite_float(self.lobbying, default=0.0, low=0.0, high=1.0)
        self.failure_risk = finite_float(self.failure_risk, default=0.2, low=0.0, high=1.0)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Company":
        company = cls(**payload)
        company.sanitize()
        return company


@dataclass(slots=True)
class Meme:
    id: int
    text: str
    ideology: float
    outrage: float
    novelty: float
    adoption: float
    mutation: float
    age: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Meme":
        return cls(**payload)


@dataclass(slots=True)
class GovernmentState:
    approval: float
    tax_rate: float
    infrastructure_budget: float
    policing_intensity: float
    surveillance: float
    corruption: float
    election_cycle_day: int
    ruling_coalition: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GovernmentState":
        return cls(**payload)


@dataclass(slots=True)
class CityEvent:
    tick: int
    day: int
    category: str
    severity: float
    title: str
    description: str
    district_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CityEvent":
        return cls(**payload)


@dataclass(slots=True)
class ActiveIntervention:
    id: str
    name: str
    category: str
    severity: float
    started_tick: int
    expires_tick: int
    target_district_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ActiveIntervention":
        return cls(**payload)


class PopulationState:
    """Vectorized citizen state for thousands of autonomous agents."""

    SERIALIZED_ARRAYS = (
        "ids",
        "age",
        "education",
        "class_index",
        "home_district",
        "work_district",
        "employed",
        "happiness",
        "stress",
        "energy",
        "wealth",
        "health",
        "ideology",
        "productivity",
        "media_susceptibility",
        "crime_propensity",
        "risk_tolerance",
        "entrepreneurship",
        "memory_stress",
        "meme_id",
    )

    def __init__(
        self,
        ids: np.ndarray,
        names: list[str],
        age: np.ndarray,
        education: np.ndarray,
        class_index: np.ndarray,
        home_district: np.ndarray,
        work_district: np.ndarray,
        employed: np.ndarray,
        happiness: np.ndarray,
        stress: np.ndarray,
        energy: np.ndarray,
        wealth: np.ndarray,
        health: np.ndarray,
        ideology: np.ndarray,
        productivity: np.ndarray,
        media_susceptibility: np.ndarray,
        crime_propensity: np.ndarray,
        risk_tolerance: np.ndarray,
        entrepreneurship: np.ndarray,
        memory_stress: np.ndarray,
        meme_id: np.ndarray,
    ) -> None:
        self.ids = ids.astype(np.int32)
        self.names = names
        self.age = age.astype(np.int16)
        self.education = education.astype(np.float32)
        self.class_index = class_index.astype(np.int8)
        self.home_district = home_district.astype(np.int16)
        self.work_district = work_district.astype(np.int16)
        self.employed = employed.astype(bool)
        self.happiness = happiness.astype(np.float32)
        self.stress = stress.astype(np.float32)
        self.energy = energy.astype(np.float32)
        self.wealth = wealth.astype(np.float32)
        self.health = health.astype(np.float32)
        self.ideology = ideology.astype(np.float32)
        self.productivity = productivity.astype(np.float32)
        self.media_susceptibility = media_susceptibility.astype(np.float32)
        self.crime_propensity = crime_propensity.astype(np.float32)
        self.risk_tolerance = risk_tolerance.astype(np.float32)
        self.entrepreneurship = entrepreneurship.astype(np.float32)
        self.memory_stress = memory_stress.astype(np.float32)
        self.meme_id = meme_id.astype(np.int16)

    @property
    def size(self) -> int:
        return int(self.ids.size)

    def to_dict(self) -> dict[str, Any]:
        payload = {key: getattr(self, key).tolist() for key in self.SERIALIZED_ARRAYS}
        payload["names"] = self.names
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PopulationState":
        kwargs = {key: np.array(payload[key]) for key in cls.SERIALIZED_ARRAYS}
        kwargs["names"] = list(payload["names"])
        return cls(**kwargs)

    def sample(self, limit: int = 100) -> list[dict[str, Any]]:
        count = min(limit, self.size)
        class_names = np.array(["Precarious", "Working", "Middle", "Affluent", "Elite"])
        return [
            {
                "id": int(self.ids[i]),
                "name": self.names[i],
                "age": int(self.age[i]),
                "education": round(float(self.education[i]), 3),
                "social_class": str(class_names[int(self.class_index[i])]),
                "home_district": int(self.home_district[i]),
                "work_district": int(self.work_district[i]),
                "employed": bool(self.employed[i]),
                "happiness": round(float(self.happiness[i]), 3),
                "stress": round(float(self.stress[i]), 3),
                "wealth": round(float(self.wealth[i]), 2),
                "health": round(float(self.health[i]), 3),
                "ideology": round(float(self.ideology[i]), 3),
                "productivity": round(float(self.productivity[i]), 3),
            }
            for i in range(count)
        ]


@dataclass
class WorldState:
    seed: int
    tick: int
    day: int
    districts: list[District]
    roads: list[Road]
    transit_lines: list[TransitLine]
    citizens: PopulationState
    companies: list[Company]
    government: GovernmentState
    memes: list[Meme]
    events: list[CityEvent]
    metrics: dict[str, float]
    history: list[dict[str, float]]
    newspaper: list[str]
    interventions: list[ActiveIntervention] = field(default_factory=list)

    def rng(self, salt: int = 0) -> np.random.Generator:
        return np.random.default_rng(self.seed + self.tick * 100_003 + salt * 9_973)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "tick": self.tick,
            "day": self.day,
            "districts": [district.to_dict() for district in self.districts],
            "roads": [road.to_dict() for road in self.roads],
            "transit_lines": [line.to_dict() for line in self.transit_lines],
            "citizens": self.citizens.to_dict(),
            "companies": [company.to_dict() for company in self.companies],
            "government": self.government.to_dict(),
            "memes": [meme.to_dict() for meme in self.memes],
            "events": [event.to_dict() for event in self.events],
            "metrics": self.metrics,
            "history": self.history,
            "newspaper": self.newspaper,
            "interventions": [intervention.to_dict() for intervention in self.interventions],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WorldState":
        state = cls(
            seed=int(payload["seed"]),
            tick=int(payload["tick"]),
            day=int(payload["day"]),
            districts=[District.from_dict(item) for item in payload["districts"]],
            roads=[Road(**item) for item in payload["roads"]],
            transit_lines=[TransitLine(**item) for item in payload["transit_lines"]],
            citizens=PopulationState.from_dict(payload["citizens"]),
            companies=[Company.from_dict(item) for item in payload["companies"]],
            government=GovernmentState.from_dict(payload["government"]),
            memes=[Meme.from_dict(item) for item in payload["memes"]],
            events=[CityEvent.from_dict(item) for item in payload["events"]],
            metrics={key: float(value) for key, value in payload["metrics"].items()},
            history=[{key: float(value) for key, value in row.items()} for row in payload["history"]],
            newspaper=list(payload.get("newspaper", [])),
            interventions=[
                ActiveIntervention.from_dict(item)
                for item in payload.get("interventions", [])
                if int(item.get("expires_tick", 0)) >= int(payload["tick"])
            ],
        )
        for company in state.companies:
            company.sanitize(len(state.districts))
        return state

    def public_snapshot(self, citizen_limit: int = 80) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "tick": self.tick,
            "day": self.day,
            "metrics": self.metrics,
            "districts": [district.to_dict() for district in self.districts],
            "roads": [road.to_dict() for road in self.roads],
            "transit_lines": [line.to_dict() for line in self.transit_lines],
            "citizens": self.citizens.sample(citizen_limit),
            "companies": [company.to_dict() for company in self.companies[:60]],
            "government": self.government.to_dict(),
            "memes": [meme.to_dict() for meme in sorted(self.memes, key=lambda item: item.adoption, reverse=True)],
            "events": [event.to_dict() for event in self.events[-80:]],
            "history": self.history[-240:],
            "newspaper": self.newspaper,
            "interventions": [intervention.to_dict() for intervention in self.interventions],
        }
