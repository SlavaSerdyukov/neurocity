from __future__ import annotations

from app.simulation.world_state import CityEvent, WorldState


def deterministic_newspaper(state: WorldState, new_events: list[CityEvent]) -> list[str]:
    headlines: list[str] = ["METROGRID TIMES"]
    if new_events:
        for event in sorted(new_events, key=lambda item: item.severity, reverse=True)[:4]:
            headlines.append(event.title)
    else:
        metrics = state.metrics
        dominant_meme = max(state.memes, key=lambda meme: meme.adoption * meme.outrage)
        headlines.extend(
            [
                f"GDP at {metrics.get('gdp', 0) / 1_000_000:.1f}M as productivity index reaches {metrics.get('productivity', 0):.2f}",
                f"Housing pressure {metrics.get('housing_pressure', 0):.0%}; average rent {metrics.get('average_rent', 0):,.0f}",
                f"City watches '{dominant_meme.text}' trend across district feeds",
            ]
        )
    headlines.append(
        f"Approval {state.government.approval:.0%}, unemployment {state.metrics.get('unemployment', 0):.0%}, commute {state.metrics.get('commute_time', 0):.0f} min"
    )
    return headlines[:5]

