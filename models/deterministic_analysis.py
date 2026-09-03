from __future__ import annotations

from dataclasses import dataclass, field, asdict
from models.training_volume import TrainingVolume

@dataclass(slots=True)
class DeterministicAnalysis:
    bewegungsmuster: dict[str, int] = field(default_factory=dict)
    muskelgruppen: dict[str, int] = field(default_factory=dict)
    movements: dict[str, int] = field(default_factory=dict)
    movement_categories: dict[str, int] = field(default_factory=dict)
    trainingsziele: dict[str, float] = field(default_factory=dict)      
    belastungsarten: dict[str, float] = field(default_factory=dict)
    trainingsvolumen: TrainingVolume = field(default_factory=TrainingVolume)

    def to_dict(self) -> dict:
        return asdict(self)