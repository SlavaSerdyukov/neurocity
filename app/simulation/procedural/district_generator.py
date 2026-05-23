from __future__ import annotations

import math

import numpy as np

from app.simulation.world_state import District, Road, TransitLine, clamp


DISTRICT_ARCHETYPES = [
    ("Arcology Core", 0.88, 0.95, 0.28, 0.18, 0.67, 0.20, 0.92, 0.85, 0.93),
    ("Old Grid", 0.48, 0.72, 0.55, 0.42, 0.49, -0.15, 0.52, 0.58, 0.45),
    ("Port Stack", 0.39, 0.64, 0.78, 0.51, 0.41, -0.25, 0.47, 0.42, 0.42),
    ("Solar Commune", 0.56, 0.45, 0.18, 0.22, 0.66, -0.48, 0.72, 0.61, 0.78),
    ("Luxury Enclave", 0.96, 0.38, 0.16, 0.08, 0.74, 0.42, 0.89, 0.72, 0.88),
    ("Maker Belt", 0.58, 0.68, 0.62, 0.34, 0.53, -0.05, 0.62, 0.64, 0.69),
    ("Peripheral Slab", 0.28, 0.83, 0.68, 0.64, 0.34, -0.34, 0.32, 0.29, 0.22),
    ("Research Campus", 0.78, 0.51, 0.22, 0.14, 0.71, 0.08, 0.82, 0.69, 0.96),
    ("Data Haven", 0.84, 0.47, 0.33, 0.27, 0.62, 0.36, 0.79, 0.53, 0.98),
    ("Floodplain", 0.34, 0.57, 0.71, 0.47, 0.38, -0.39, 0.39, 0.35, 0.31),
]

NAME_PREFIXES = [
    "Helix",
    "Saint Lumen",
    "Orchid",
    "Vanta",
    "Kestrel",
    "Mirrorglass",
    "Lowline",
    "Brightwater",
    "Aster",
    "Neon",
    "Ferro",
    "Nimbus",
    "Tessera",
    "Cobalt",
    "Marrow",
]

NAME_SUFFIXES = [
    "Ward",
    "Arc",
    "Stacks",
    "Exchange",
    "Mile",
    "Yards",
    "Loop",
    "Heights",
    "Canal",
    "Terrace",
    "Commons",
    "Spine",
]


def _district_polygon(x: float, y: float, radius: float, rng: np.random.Generator) -> list[list[float]]:
    points: list[list[float]] = []
    sides = int(rng.integers(5, 8))
    rotation = float(rng.uniform(0, math.pi))
    for index in range(sides):
        angle = rotation + 2 * math.pi * index / sides
        jitter = float(rng.uniform(0.72, 1.18))
        points.append([x + math.cos(angle) * radius * jitter, y + math.sin(angle) * radius * jitter])
    return points


def generate_districts(seed: int, district_count: int) -> list[District]:
    rng = np.random.default_rng(seed + 101)
    district_count = max(8, district_count)
    districts: list[District] = []
    columns = math.ceil(math.sqrt(district_count))
    rows = math.ceil(district_count / columns)
    spacing_x = 100 / (columns + 1)
    spacing_y = 100 / (rows + 1)

    for index in range(district_count):
        col = index % columns
        row = index // columns
        archetype = DISTRICT_ARCHETYPES[index % len(DISTRICT_ARCHETYPES)]
        base_name = f"{NAME_PREFIXES[index % len(NAME_PREFIXES)]} {NAME_SUFFIXES[(index * 3) % len(NAME_SUFFIXES)]}"
        x = spacing_x * (col + 1) + float(rng.normal(0, 3.4))
        y = spacing_y * (row + 1) + float(rng.normal(0, 3.0))
        wealth, density, pollution, crime, happiness, leaning, infra, transit, tech = archetype[1:]
        density = clamp(density + float(rng.normal(0, 0.06)))
        wealth = clamp(wealth + float(rng.normal(0, 0.05)))
        housing_supply = int(210 + density * 320 + wealth * 90 + rng.integers(-35, 55))
        housing_supply = max(180, housing_supply)
        housing_demand = int(housing_supply * rng.uniform(0.89, 1.23 + density * 0.15))
        districts.append(
            District(
                id=index,
                name=base_name,
                archetype=archetype[0],
                x=clamp(x, 5, 95),
                y=clamp(y, 5, 95),
                polygon=_district_polygon(clamp(x, 5, 95), clamp(y, 5, 95), 6.4 + density * 3.8, rng),
                wealth=wealth,
                density=density,
                pollution=clamp(pollution + rng.normal(0, 0.05)),
                crime=clamp(crime + rng.normal(0, 0.05)),
                happiness=clamp(happiness + rng.normal(0, 0.04)),
                political_leaning=clamp(leaning + rng.normal(0, 0.12), -1, 1),
                infrastructure_quality=clamp(infra + rng.normal(0, 0.05)),
                transit_access=clamp(transit + rng.normal(0, 0.07)),
                housing_supply=housing_supply,
                housing_demand=housing_demand,
                average_rent=round(650 + wealth * 2100 + density * 750 + rng.normal(0, 120), 2),
                energy_capacity=round(110 + infra * 120 + tech * 85 + rng.normal(0, 8), 2),
                energy_demand=round(120 + density * 170 + wealth * 80 + rng.normal(0, 10), 2),
                commute_index=clamp(0.35 + (1 - transit) * 0.36 + density * 0.15 + rng.normal(0, 0.04)),
                congestion=clamp(0.24 + density * 0.42 + (1 - transit) * 0.18 + rng.normal(0, 0.05)),
                unemployment=clamp(0.05 + (1 - wealth) * 0.17 + crime * 0.05 + rng.normal(0, 0.015)),
                business_activity=clamp(0.32 + wealth * 0.38 + tech * 0.22 + rng.normal(0, 0.05)),
                tech_level=tech,
            )
        )
    return districts


def generate_roads(districts: list[District], seed: int) -> list[Road]:
    rng = np.random.default_rng(seed + 202)
    roads: list[Road] = []
    for district in districts:
        distances = sorted(
            (
                (other.id, math.dist((district.x, district.y), (other.x, other.y)))
                for other in districts
                if other.id != district.id
            ),
            key=lambda item: item[1],
        )
        for target_id, distance in distances[:3]:
            source, target = sorted((district.id, target_id))
            if any(road.source == source and road.target == target for road in roads):
                continue
            source_district = districts[source]
            target_district = districts[target]
            average_infra = (source_district.infrastructure_quality + target_district.infrastructure_quality) / 2
            capacity = max(50, 260 - distance * 2.5 + average_infra * 120)
            roads.append(
                Road(
                    source=source,
                    target=target,
                    capacity=round(capacity, 2),
                    congestion=clamp((source_district.congestion + target_district.congestion) / 2 + rng.normal(0, 0.04)),
                )
            )
    return roads


def generate_transit_lines(districts: list[District], seed: int) -> list[TransitLine]:
    rng = np.random.default_rng(seed + 303)
    by_x = sorted(districts, key=lambda district: district.x)
    by_y = sorted(districts, key=lambda district: district.y)
    wealthy = sorted(districts, key=lambda district: district.wealth, reverse=True)
    lines = [
        TransitLine(0, "Aurora Spine", [district.id for district in by_x], 920.0, 0.73),
        TransitLine(1, "Canal Loop", [district.id for district in by_y], 760.0, 0.68),
        TransitLine(2, "Executive Shuttle", [district.id for district in wealthy[: max(4, len(districts) // 3)]], 420.0, 0.84),
    ]
    for line in lines:
        line.reliability = clamp(line.reliability + float(rng.normal(0, 0.04)))
    return lines
