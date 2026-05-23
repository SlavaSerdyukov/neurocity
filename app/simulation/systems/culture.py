from __future__ import annotations

import numpy as np

from app.simulation.world_state import WorldState, clamp, clamp_array


def update_culture(state: WorldState) -> None:
    citizens = state.citizens
    district_count = len(state.districts)
    meme_heat = sum(meme.adoption * meme.outrage for meme in state.memes)
    social_fatigue = min(0.28, meme_heat * 0.04 + state.metrics.get("polarization", 0) * 0.05)
    local_happiness = np.bincount(
        citizens.home_district,
        weights=citizens.happiness,
        minlength=district_count,
    ) / np.maximum(1, np.bincount(citizens.home_district, minlength=district_count))

    for district in state.districts:
        creative_boom = district.tech_level * 0.006 + district.transit_access * 0.003
        district.happiness = clamp(district.happiness * 0.86 + float(local_happiness[district.id]) * 0.14 + creative_boom - social_fatigue * 0.01)
        district.political_leaning = clamp(
            district.political_leaning * 0.995
            + float(np.mean(citizens.ideology[citizens.home_district == district.id])) * 0.005
            if np.any(citizens.home_district == district.id)
            else district.political_leaning,
            -1,
            1,
        )

    civic_trust = max(0.0, state.government.approval - 0.35)
    recovery = citizens.energy * 0.01 + citizens.health * 0.006 + civic_trust * 0.01
    citizens.happiness = clamp_array(citizens.happiness + 0.009 - social_fatigue * 0.015 + citizens.energy * 0.005 + civic_trust * 0.006)
    citizens.stress = clamp_array(citizens.stress * 0.988 - recovery)
    citizens.productivity = clamp_array(citizens.productivity + citizens.energy * 0.006 + citizens.health * 0.004 - citizens.stress * 0.003)
    citizens.memory_stress = clamp_array(citizens.memory_stress * 0.96 + citizens.stress * 0.04)
    state.metrics["happiness"] = float(np.mean(citizens.happiness))
    state.metrics["stress"] = float(np.mean(citizens.stress))
