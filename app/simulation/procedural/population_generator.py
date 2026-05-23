from __future__ import annotations

import numpy as np

from app.simulation.world_state import District, PopulationState, clamp_array


FIRST_NAMES = [
    "Ari",
    "Mira",
    "Sol",
    "Niko",
    "Juno",
    "Ilya",
    "Tala",
    "Ren",
    "Vera",
    "Oren",
    "Sana",
    "Kai",
    "Lea",
    "Noam",
    "Yara",
    "Ezra",
]

LAST_NAMES = [
    "Novak",
    "Sato",
    "Ivers",
    "Vale",
    "Okafor",
    "Singh",
    "Rossi",
    "Kade",
    "Moroz",
    "Chen",
    "Hale",
    "Barrera",
    "Volkov",
    "Ndiaye",
    "Frost",
    "Lian",
]


def generate_population(seed: int, count: int, districts: list[District]) -> PopulationState:
    rng = np.random.default_rng(seed + 404)
    district_weights = np.array([district.density * district.housing_supply for district in districts], dtype=np.float64)
    district_weights = district_weights / district_weights.sum()
    home_district = rng.choice(len(districts), count, p=district_weights)

    ages = np.clip(rng.normal(38, 13, count), 18, 82).astype(np.int16)
    district_wealth = np.array([district.wealth for district in districts], dtype=np.float32)
    district_leaning = np.array([district.political_leaning for district in districts], dtype=np.float32)
    district_happiness = np.array([district.happiness for district in districts], dtype=np.float32)
    home_wealth = district_wealth[home_district]

    education = clamp_array(rng.beta(2.1 + home_wealth, 2.2, count) + rng.normal(0, 0.08, count))
    class_index = np.clip(np.floor(home_wealth * 4 + education * 1.2 + rng.normal(0, 0.8, count)), 0, 4).astype(np.int8)

    employment_probability = np.clip(0.72 + education * 0.19 + home_wealth * 0.05 - (ages > 65) * 0.45, 0.08, 0.96)
    employed = rng.random(count) < employment_probability
    work_weights = np.array([district.business_activity * (0.4 + district.tech_level) for district in districts], dtype=np.float64)
    work_weights = work_weights / work_weights.sum()
    work_district = rng.choice(len(districts), count, p=work_weights)
    work_district[~employed] = home_district[~employed]

    wealth = np.maximum(0, rng.lognormal(mean=7.1 + home_wealth * 1.0 + education * 0.5, sigma=0.55, size=count)).astype(np.float32)
    ideology = np.clip(district_leaning[home_district] + rng.normal(0, 0.32, count), -1, 1).astype(np.float32)
    happiness = clamp_array(district_happiness[home_district] + home_wealth * 0.12 + employed * 0.08 + rng.normal(0, 0.08, count))
    stress = clamp_array(0.36 + (1 - home_wealth) * 0.18 + (~employed) * 0.15 + rng.normal(0, 0.09, count))
    health = clamp_array(0.72 + home_wealth * 0.12 - stress * 0.1 + rng.normal(0, 0.07, count))
    energy = clamp_array(0.64 - stress * 0.18 + health * 0.16 + rng.normal(0, 0.06, count))
    productivity = clamp_array(0.42 + education * 0.28 + energy * 0.18 - stress * 0.18 + employed * 0.12)
    media_susceptibility = clamp_array(rng.beta(2.4, 2.6, count) + stress * 0.15)
    crime_propensity = clamp_array(rng.beta(1.6, 6.5, count) + stress * 0.16 + (1 - home_wealth) * 0.12 - education * 0.1)
    risk_tolerance = clamp_array(rng.beta(2.0, 2.7, count) + education * 0.05)
    entrepreneurship = clamp_array(rng.beta(1.7, 5.2, count) + education * 0.18 + class_index / 24)
    memory_stress = stress.copy().astype(np.float32)
    meme_id = np.full(count, -1, dtype=np.int16)

    names = [
        f"{FIRST_NAMES[i % len(FIRST_NAMES)]} {LAST_NAMES[(i * 7) % len(LAST_NAMES)]}-{1000 + int(i)}"
        for i in range(count)
    ]

    return PopulationState(
        ids=np.arange(count, dtype=np.int32),
        names=names,
        age=ages,
        education=education,
        class_index=class_index,
        home_district=home_district,
        work_district=work_district,
        employed=employed,
        happiness=happiness,
        stress=stress,
        energy=energy,
        wealth=wealth,
        health=health,
        ideology=ideology,
        productivity=productivity,
        media_susceptibility=media_susceptibility,
        crime_propensity=crime_propensity,
        risk_tolerance=risk_tolerance,
        entrepreneurship=entrepreneurship,
        memory_stress=memory_stress,
        meme_id=meme_id,
    )

