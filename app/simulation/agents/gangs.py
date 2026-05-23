from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GangPressure:
    poverty: float
    unemployment: float
    policing: float
    corruption: float

    @property
    def recruitment_rate(self) -> float:
        return max(0.0, self.poverty * 0.34 + self.unemployment * 0.32 + self.corruption * 0.18 - self.policing * 0.2)

