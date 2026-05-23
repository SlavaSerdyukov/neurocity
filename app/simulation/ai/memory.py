from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CivicMemory:
    incidents: list[str] = field(default_factory=list)

    def remember(self, text: str) -> None:
        self.incidents.append(text)
        self.incidents = self.incidents[-80:]

    def summary(self) -> str:
        return " | ".join(self.incidents[-8:])

