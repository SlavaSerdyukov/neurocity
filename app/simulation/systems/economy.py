from __future__ import annotations

import pandas as pd
import numpy as np

from app.simulation.world_state import MAX_COMPANY_CAPITAL, WorldState, clamp, finite_float


def update_economy(state: WorldState) -> None:
    citizens = state.citizens
    rng = state.rng(36)
    district_count = len(state.districts)
    district_productivity = np.zeros(district_count, dtype=np.float64)
    employed_counts = np.bincount(citizens.work_district[citizens.employed], minlength=district_count).astype(np.float64)
    productivity_sums = np.bincount(
        citizens.work_district[citizens.employed],
        weights=citizens.productivity[citizens.employed],
        minlength=district_count,
    )
    district_productivity = np.divide(productivity_sums, np.maximum(1, employed_counts))

    district_energy_margin = np.array(
        [(district.energy_capacity - district.energy_demand) / max(1, district.energy_demand) for district in state.districts],
        dtype=np.float32,
    )
    district_congestion = np.array([district.congestion for district in state.districts], dtype=np.float32)

    gdp = 0.0
    for company in state.companies:
        company.sanitize(district_count)
        district = state.districts[company.district_id]
        labor_signal = finite_float(district_productivity[company.district_id], default=0.45, low=0.0, high=1.6)
        energy_penalty = max(0, -district_energy_margin[company.district_id]) * 0.16
        commute_penalty = district_congestion[company.district_id] * 0.055
        tax_drag = finite_float(state.government.tax_rate, default=0.18, low=0.0, high=0.75) * 0.07
        adaptation_bonus = district.tech_level * 0.014 + district.infrastructure_quality * 0.006
        growth = (labor_signal - 0.48) * 0.024 + adaptation_bonus - energy_penalty - commute_penalty - tax_drag
        growth = finite_float(growth, default=-0.02, low=-0.45, high=0.18)
        public_contract_multiplier = 1.0 if company.sector in {"public services", "construction robotics", "autonomous logistics", "civic AI"} else 0.32
        public_contracts = state.government.infrastructure_budget * district.infrastructure_quality * 1450 * public_contract_multiplier
        company.productivity = float(np.clip(company.productivity * 0.92 + (0.42 + labor_signal) * 0.08, 0.05, 1.6))
        next_capital = company.capital * (1 + growth) + public_contracts
        company.capital = round(finite_float(next_capital, default=0.0, low=0.0, high=MAX_COMPANY_CAPITAL), 2)
        company.failure_risk = clamp(
            company.failure_risk * 0.86
            + max(0, -growth) * 0.34
            + district.unemployment * 0.035
            + district_congestion[company.district_id] * 0.012
            - labor_signal * 0.018
            - state.government.infrastructure_budget * 0.01
        )
        inflation = finite_float(state.metrics.get("inflation", 0.03), default=0.03, low=-0.02, high=0.18)
        next_wage = company.wage * (1 + (labor_signal - 0.54) * 0.006 + inflation * 0.018)
        company.wage = round(finite_float(next_wage, default=60_000.0, low=18_000.0, high=1_000_000.0), 2)
        if company.capital < 18_000 and company.failure_risk < 0.58 and district.business_activity > 0.32:
            company.capital = round(company.capital + 16_000 + district.tech_level * 24_000 + rng.uniform(0, 9_000), 2)
            company.employees += int(1 + rng.integers(1, 5))
            company.open_roles += int(rng.integers(1, 4))
        elif company.capital < 18_000 or company.failure_risk > 0.74:
            layoffs = max(1, int(company.employees * min(0.12, company.failure_risk * 0.08)))
            company.employees = max(1, company.employees - layoffs)
            company.open_roles = max(0, company.open_roles - layoffs)
            company.failure_risk = clamp(company.failure_risk - 0.12)
        elif growth > 0.004 and rng.random() < 0.32:
            hires = int(1 + rng.integers(1, 7))
            company.employees += hires
            company.open_roles += int(rng.integers(0, 4))
        company.sanitize(district_count)
        gdp += finite_float(company.employees * company.wage * company.productivity / 52, default=0.0, low=0.0, high=25_000_000_000.0)

    frame = pd.DataFrame([company.to_dict() for company in state.companies])
    sector_growth = frame.groupby("sector")["capital"].sum().pct_change().fillna(0).mean() if not frame.empty else 0
    sector_growth = finite_float(sector_growth, default=0.0, low=-1.0, high=1.0)
    unemployment = state.metrics.get("unemployment", 0.0)
    rent_pressure = state.metrics.get("housing_pressure", 0.0)
    inflation_target = 0.018 + rent_pressure * 0.035 + max(0, gdp / 42_000_000 - 1) * 0.008 + unemployment * 0.015
    state.metrics["inflation"] = float(np.clip(state.metrics["inflation"] * 0.82 + inflation_target * 0.18 + sector_growth * 0.001, -0.02, 0.18))

    company_counts = np.bincount([company.district_id for company in state.companies], minlength=district_count)
    for district in state.districts:
        local_companies = company_counts[district.id]
        activity = (
            0.2
            + district_productivity[district.id] * 0.42
            + min(0.32, local_companies / 120)
            - district.congestion * 0.045
            + district.infrastructure_quality * 0.035
        )
        district.business_activity = clamp(district.business_activity * 0.72 + activity * 0.28)
        district.tech_level = clamp(district.tech_level + district.business_activity * 0.0018 - district.pollution * 0.0006)

    state.metrics["gdp"] = float(gdp)
    state.metrics["productivity"] = float(np.mean(citizens.productivity))
    state.metrics["tech_level"] = float(np.mean([district.tech_level for district in state.districts]))
