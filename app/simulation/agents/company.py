from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CompanyDecisionSignals:
    productivity: float
    energy_margin: float
    congestion: float
    tax_rate: float
    labor_availability: float

    @property
    def expansion_pressure(self) -> float:
        return self.productivity * 0.45 + max(0.0, self.energy_margin) * 0.2 + self.labor_availability * 0.2 - self.tax_rate * 0.18

    @property
    def bankruptcy_pressure(self) -> float:
        return max(0.0, -self.energy_margin) * 0.36 + self.congestion * 0.2 + self.tax_rate * 0.08 - self.productivity * 0.22

