from __future__ import annotations

import numpy as np

from app.simulation.world_state import WorldState, clamp, clamp_array


def update_crime(state: WorldState) -> None:
    citizens = state.citizens
    district_count = len(state.districts)
    poverty_signal = 1 - np.array([district.wealth for district in state.districts], dtype=np.float32)
    unemployment = np.array([district.unemployment for district in state.districts], dtype=np.float32)
    policing = state.government.policing_intensity

    wealth_by_home = citizens.wealth
    low_wealth = np.clip((18_000 - wealth_by_home) / 18_000, 0, 1)
    district_pressure = poverty_signal[citizens.home_district] * 0.28 + unemployment[citizens.home_district] * 0.42
    citizens.crime_propensity = clamp_array(
        citizens.crime_propensity * 0.91
        + low_wealth * 0.05
        + citizens.stress * 0.035
        + district_pressure * 0.045
        - citizens.education * 0.018
        - policing * 0.025
    )

    crime_sums = np.bincount(
        citizens.home_district,
        weights=citizens.crime_propensity,
        minlength=district_count,
    )
    counts = np.bincount(citizens.home_district, minlength=district_count)
    crime_by_district = np.divide(crime_sums, np.maximum(1, counts))
    inequality = np.zeros(district_count, dtype=np.float32)
    for district_id in range(district_count):
        mask = citizens.home_district == district_id
        if mask.any():
            local_wealth = citizens.wealth[mask]
            inequality[district_id] = float((np.percentile(local_wealth, 90) - np.percentile(local_wealth, 10)) / max(1, np.mean(local_wealth)))

    for district in state.districts:
        pressure = crime_by_district[district.id] + inequality[district.id] * 0.04 + district.unemployment * 0.24
        district.crime = clamp(district.crime * 0.68 + pressure * 0.32 - policing * 0.07 + state.government.corruption * 0.05)
        district.happiness = clamp(district.happiness - district.crime * 0.008)

    citizens.stress = clamp_array(citizens.stress + np.array([state.districts[index].crime for index in citizens.home_district]) * 0.01)
    state.metrics["crime"] = float(np.mean([district.crime for district in state.districts]))

