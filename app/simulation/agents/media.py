from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MediaPulse:
    outrage: float
    novelty: float
    adoption: float
    polarization: float

    @property
    def virality(self) -> float:
        return max(0.0, self.outrage * 0.38 + self.novelty * 0.27 + self.adoption * 0.22 + self.polarization * 0.13)

