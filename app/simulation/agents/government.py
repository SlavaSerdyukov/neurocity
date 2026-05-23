from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PolicyPressure:
    approval: float
    crime: float
    housing: float
    blackout: float
    protests: float

    @property
    def infrastructure_need(self) -> float:
        return max(0.0, self.blackout * 0.45 + self.housing * 0.25 + self.protests * 0.12)

    @property
    def coercion_need(self) -> float:
        return max(0.0, self.crime * 0.4 + self.protests * 0.28 - self.approval * 0.18)

