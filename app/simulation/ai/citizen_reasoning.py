from __future__ import annotations

from app.simulation.agents.citizen import CitizenDecisionSignals


def citizen_action_bias(signals: CitizenDecisionSignals) -> dict[str, float]:
    """Deterministic behavior weights used for diagnostics and future LLM narration."""

    return {
        "migrate": signals.migration_pressure,
        "protest": signals.protest_pressure,
        "work": max(0.0, signals.job_security - signals.commute_stress * 0.2),
        "withdraw": max(0.0, signals.commute_stress * 0.3 + signals.media_pressure * 0.2),
    }

