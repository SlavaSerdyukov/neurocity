from __future__ import annotations

from app.simulation.world_state import CityEvent, WorldState


class EventSystem:
    """Converts systemic pressure into observable city events."""

    def __init__(self, cooldown_ticks: int = 10) -> None:
        self.cooldown_ticks = cooldown_ticks

    def _recent(self, state: WorldState, category: str) -> bool:
        return any(event.category == category and state.tick - event.tick < self.cooldown_ticks for event in state.events[-60:])

    def evaluate(self, state: WorldState) -> list[CityEvent]:
        metrics = state.metrics
        events: list[CityEvent] = []
        most_congested = max(state.districts, key=lambda district: district.congestion)
        hottest_meme = max(state.memes, key=lambda meme: meme.adoption * (0.5 + meme.outrage))
        highest_crime = max(state.districts, key=lambda district: district.crime)
        tightest_housing = max(
            state.districts,
            key=lambda district: district.housing_demand / max(1, district.housing_supply),
        )
        weakest_grid = min(
            state.districts,
            key=lambda district: (district.energy_capacity - district.energy_demand) / max(1, district.energy_demand),
        )

        if most_congested.congestion > 0.72 and not self._recent(state, "transport"):
            events.append(
                CityEvent(
                    state.tick,
                    state.day,
                    "transport",
                    most_congested.congestion,
                    f"Transit collapse slows {most_congested.name}",
                    f"Commute pressure reached {most_congested.congestion:.0%}, cutting productivity and lifting stress.",
                    most_congested.id,
                )
            )

        housing_ratio = tightest_housing.housing_demand / max(1, tightest_housing.housing_supply)
        if housing_ratio > 1.16 and not self._recent(state, "housing"):
            events.append(
                CityEvent(
                    state.tick,
                    state.day,
                    "housing",
                    min(1.0, housing_ratio - 0.8),
                    f"Housing pressure spikes in {tightest_housing.name}",
                    f"Demand is {housing_ratio:.2f}x supply and average rent reached {tightest_housing.average_rent:,.0f} credits.",
                    tightest_housing.id,
                )
            )

        grid_margin = (weakest_grid.energy_capacity - weakest_grid.energy_demand) / max(1, weakest_grid.energy_demand)
        if grid_margin < -0.14 and not self._recent(state, "energy"):
            events.append(
                CityEvent(
                    state.tick,
                    state.day,
                    "energy",
                    min(1.0, abs(grid_margin)),
                    f"Brownouts roll through {weakest_grid.name}",
                    f"Energy demand exceeded capacity by {abs(grid_margin):.0%}, degrading infrastructure and civic trust.",
                    weakest_grid.id,
                )
            )

        if metrics.get("protest_intensity", 0) > 0.58 and not self._recent(state, "politics"):
            events.append(
                CityEvent(
                    state.tick,
                    state.day,
                    "politics",
                    metrics["protest_intensity"],
                    "Protest movement crosses coordination threshold",
                    f"Approval fell to {metrics.get('approval', 0):.0%} while polarization and housing pressure converged.",
                )
            )

        if highest_crime.crime > 0.55 and not self._recent(state, "crime"):
            events.append(
                CityEvent(
                    state.tick,
                    state.day,
                    "crime",
                    highest_crime.crime,
                    f"Black market expands in {highest_crime.name}",
                    f"Poverty, unemployment, and corruption pushed district crime to {highest_crime.crime:.0%}.",
                    highest_crime.id,
                )
            )

        if metrics.get("unemployment", 0) > 0.22 and metrics.get("gdp", 1) < 35_000_000 and not self._recent(state, "economy"):
            events.append(
                CityEvent(
                    state.tick,
                    state.day,
                    "economy",
                    min(1.0, metrics["unemployment"] * 2.0),
                    "Layoff wave hits automated firms",
                    f"Unemployment reached {metrics['unemployment']:.0%}; weak productivity and congestion tightened company margins.",
                )
            )

        meme_pressure = hottest_meme.adoption * hottest_meme.outrage
        if meme_pressure > 0.12 and not self._recent(state, "culture"):
            events.append(
                CityEvent(
                    state.tick,
                    state.day,
                    "culture",
                    min(1.0, meme_pressure * 3),
                    f"Viral trend surges: {hottest_meme.text}",
                    f"The meme spread through {hottest_meme.adoption:.0%} of citizens and nudged ideological alignment.",
                )
            )

        if metrics.get("pollution", 0) > 0.62 and not self._recent(state, "climate"):
            events.append(
                CityEvent(
                    state.tick,
                    state.day,
                    "climate",
                    metrics["pollution"],
                    "Heat and pollution strain public health",
                    "Pollution crossed civic safety thresholds, increasing stress and lowering health in exposed districts.",
                )
            )

        state.events.extend(events)
        state.events = state.events[-500:]
        return events

