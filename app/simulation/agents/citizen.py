from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CitizenDecisionSignals:
    """Aggregated incentives that drive vectorized citizen behavior."""

    commute_stress: float
    rent_burden: float
    job_security: float
    media_pressure: float
    public_safety: float

    @property
    def migration_pressure(self) -> float:
        return max(0.0, self.rent_burden * 0.55 + self.commute_stress * 0.3 - self.job_security * 0.2)

    @property
    def protest_pressure(self) -> float:
        return max(0.0, self.media_pressure * 0.35 + self.rent_burden * 0.25 + (1 - self.public_safety) * 0.2)

