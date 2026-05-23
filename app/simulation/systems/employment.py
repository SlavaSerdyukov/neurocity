from __future__ import annotations

import numpy as np
from scipy.special import expit

from app.simulation.world_state import WorldState, clamp, clamp_array


def update_employment(state: WorldState) -> None:
    citizens = state.citizens
    rng = state.rng(12)
    district_count = len(state.districts)

    business_activity = np.array([district.business_activity for district in state.districts], dtype=np.float32)
    district_unemployment = np.array([district.unemployment for district in state.districts], dtype=np.float32)
    work_activity = business_activity[citizens.work_district]
    home_unemployment = district_unemployment[citizens.home_district]

    civic_jobs = np.clip(state.government.infrastructure_budget * 0.18 + home_unemployment * 0.35, 0, 0.16)
    hire_probability = expit(-1.45 + citizens.education * 1.25 + work_activity * 1.35 - home_unemployment * 1.35 + civic_jobs)
    fire_probability = expit(-4.45 + home_unemployment * 1.85 + citizens.stress * 0.78 - citizens.productivity * 1.45)

    unemployed = ~citizens.employed
    new_hires = unemployed & (rng.random(citizens.size) < hire_probability * (0.105 + civic_jobs))
    layoffs = citizens.employed & (rng.random(citizens.size) < fire_probability * 0.022)
    citizens.employed[new_hires] = True
    citizens.employed[layoffs] = False

    attractive_jobs = business_activity / max(float(business_activity.sum()), 1)
    seeking = (~citizens.employed) & (rng.random(citizens.size) < 0.08 + citizens.risk_tolerance * 0.05)
    if seeking.any():
        citizens.work_district[seeking] = rng.choice(district_count, int(seeking.sum()), p=attractive_jobs)

    wage_by_district = np.zeros(district_count, dtype=np.float32)
    counts_by_district = np.zeros(district_count, dtype=np.float32)
    for company in state.companies:
        wage_by_district[company.district_id] += company.wage * max(company.employees, 1)
        counts_by_district[company.district_id] += max(company.employees, 1)
    wage_by_district = np.divide(wage_by_district, np.maximum(1, counts_by_district))
    monthly_income = np.where(citizens.employed, wage_by_district[citizens.work_district] / 12, 900)
    rent = np.array([state.districts[index].average_rent for index in citizens.home_district], dtype=np.float32)
    taxes = monthly_income * state.government.tax_rate
    disposable = np.maximum(-650, monthly_income - rent - taxes)
    citizens.wealth = np.maximum(0, citizens.wealth + disposable * 0.018).astype(np.float32)
    citizens.happiness = clamp_array(citizens.happiness + np.where(citizens.employed, 0.011, -0.017))
    citizens.stress = clamp_array(citizens.stress + np.where(citizens.employed, -0.01, 0.019))

    unemployed_counts = np.bincount(citizens.home_district[~citizens.employed], minlength=district_count)
    resident_counts = np.bincount(citizens.home_district, minlength=district_count)
    for district in state.districts:
        rate = float(unemployed_counts[district.id] / max(1, resident_counts[district.id]))
        district.unemployment = clamp(district.unemployment * 0.55 + rate * 0.45)

    state.metrics["unemployment"] = float(np.mean(~citizens.employed))
