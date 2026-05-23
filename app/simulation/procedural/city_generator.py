from __future__ import annotations

import numpy as np

from app.config import get_settings
from app.simulation.procedural.district_generator import (
    generate_districts,
    generate_roads,
    generate_transit_lines,
)
from app.simulation.procedural.population_generator import generate_population
from app.simulation.world_state import Company, GovernmentState, Meme, WorldState


SECTORS = [
    ("autonomous logistics", 0.57, 0.63),
    ("synthetic food", 0.44, 0.52),
    ("civic AI", 0.78, 0.82),
    ("biomed", 0.73, 0.74),
    ("construction robotics", 0.48, 0.57),
    ("data brokerage", 0.84, 0.88),
    ("public services", 0.39, 0.46),
    ("media swarms", 0.62, 0.79),
]


def generate_companies(seed: int, districts_count: int, count: int = 84) -> list[Company]:
    rng = np.random.default_rng(seed + 505)
    companies: list[Company] = []
    for company_id in range(count):
        sector, productivity_base, tech_bias = SECTORS[company_id % len(SECTORS)]
        district_id = int(rng.integers(0, districts_count))
        scale = float(rng.lognormal(3.35, 0.75))
        employees = int(max(4, scale * rng.uniform(0.6, 1.7)))
        companies.append(
            Company(
                id=company_id,
                name=f"{sector.title()} Node {company_id:02d}",
                sector=sector,
                district_id=district_id,
                employees=employees,
                open_roles=int(max(0, rng.normal(8, 6))),
                wage=round(42_000 + productivity_base * 58_000 + rng.normal(0, 6000), 2),
                capital=round(max(12_000, rng.lognormal(12.1 + tech_bias * 0.35, 0.65)), 2),
                productivity=float(np.clip(productivity_base + rng.normal(0, 0.07), 0.1, 1.4)),
                lobbying=float(np.clip(rng.beta(1.4 + tech_bias, 5.0), 0, 1)),
                failure_risk=float(np.clip(0.13 + rng.normal(0, 0.04), 0.01, 0.7)),
            )
        )
    return companies


def initial_memes() -> list[Meme]:
    return [
        Meme(0, "Rent Is A Compiler Error", -0.48, 0.62, 0.74, 0.18, 0.08),
        Meme(1, "Let The Trains Think", 0.12, 0.34, 0.68, 0.12, 0.05),
        Meme(2, "Humans Need A Patch", 0.44, 0.77, 0.81, 0.09, 0.11),
        Meme(3, "No Gods No Dashboards", -0.66, 0.71, 0.59, 0.07, 0.12),
        Meme(4, "Solar Dividends Now", -0.32, 0.48, 0.66, 0.15, 0.06),
    ]


def initial_metrics() -> dict[str, float]:
    return {
        "gdp": 0.0,
        "unemployment": 0.0,
        "inflation": 0.03,
        "productivity": 0.0,
        "happiness": 0.0,
        "stress": 0.0,
        "polarization": 0.0,
        "approval": 0.52,
        "crime": 0.0,
        "energy_margin": 0.0,
        "blackout_risk": 0.0,
        "housing_pressure": 0.0,
        "average_rent": 0.0,
        "commute_time": 0.0,
        "congestion": 0.0,
        "pollution": 0.0,
        "protest_intensity": 0.0,
        "tech_level": 0.0,
    }


def bootstrap_metrics(world: WorldState) -> None:
    citizens = world.citizens
    districts = world.districts
    gdp = sum(company.employees * company.wage * company.productivity / 52 for company in world.companies)
    energy_margins = [
        (district.energy_capacity - district.energy_demand) / max(1, district.energy_demand)
        for district in districts
    ]
    housing_pressure = [
        max(0.0, district.housing_demand / max(1, district.housing_supply) - 0.92)
        for district in districts
    ]
    commute_seed = np.array([district.commute_index for district in districts], dtype=np.float32)[citizens.home_district]
    world.metrics.update(
        {
            "gdp": float(gdp),
            "unemployment": float(np.mean(~citizens.employed)),
            "productivity": float(np.mean(citizens.productivity)),
            "happiness": float(np.mean(citizens.happiness)),
            "stress": float(np.mean(citizens.stress)),
            "polarization": float(np.std(citizens.ideology) * 1.8),
            "approval": world.government.approval,
            "crime": float(np.mean([district.crime for district in districts])),
            "energy_margin": float(np.mean(energy_margins)),
            "blackout_risk": float(np.mean([max(0.0, -margin) for margin in energy_margins])),
            "housing_pressure": float(np.mean(housing_pressure)),
            "average_rent": float(np.mean([district.average_rent for district in districts])),
            "commute_time": float(np.mean(18 + commute_seed * 68)),
            "congestion": float(np.mean([district.congestion for district in districts])),
            "pollution": float(np.mean([district.pollution for district in districts])),
            "protest_intensity": float(
                np.clip((1 - world.government.approval) * 0.34 + np.std(citizens.ideology) * 0.26, 0, 1)
            ),
            "tech_level": float(np.mean([district.tech_level for district in districts])),
        }
    )
    hottest_meme = max(world.memes, key=lambda meme: meme.adoption * meme.outrage)
    world.newspaper = [
        "METROGRID TIMES",
        f"Opening GDP reads {world.metrics['gdp'] / 1_000_000:.1f}M across {len(world.companies)} firms",
        f"Housing pressure starts at {world.metrics['housing_pressure']:.0%}; average rent {world.metrics['average_rent']:,.0f}",
        f"Commute model flags {world.metrics['commute_time']:.0f} minute average travel time",
        f"Trend desks track '{hottest_meme.text}' at {hottest_meme.adoption:.0%} adoption",
    ]


def create_world(
    seed: int | None = None,
    population: int | None = None,
    district_count: int | None = None,
) -> WorldState:
    settings = get_settings()
    seed = settings.default_seed if seed is None else seed
    population = settings.default_population if population is None else population
    district_count = settings.default_districts if district_count is None else district_count
    districts = generate_districts(seed, district_count)
    citizens = generate_population(seed, population, districts)
    world = WorldState(
        seed=seed,
        tick=0,
        day=0,
        districts=districts,
        roads=generate_roads(districts, seed),
        transit_lines=generate_transit_lines(districts, seed),
        citizens=citizens,
        companies=generate_companies(seed, len(districts)),
        government=GovernmentState(
            approval=0.51,
            tax_rate=0.18,
            infrastructure_budget=0.42,
            policing_intensity=0.46,
            surveillance=0.37,
            corruption=0.21,
            election_cycle_day=365,
            ruling_coalition="Pragmatic Continuity Bloc",
        ),
        memes=initial_memes(),
        events=[],
        metrics=initial_metrics(),
        history=[],
        newspaper=["Metrogrid Times: City boot sequence complete."],
    )
    bootstrap_metrics(world)
    return world
