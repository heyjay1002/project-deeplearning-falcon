from dataclasses import dataclass
from config import BirdRiskLevel, RunwayRiskLevel, Constants

@dataclass(frozen=True)
class BirdRisk:
    value: int

    def __post_init__(self):
        if self.value not in Constants.BIRD_RISK_MAPPING:
            raise ValueError(f"유효하지 않은 조류 위험도 값: {self.value}")

    @property
    def enum(self) -> BirdRiskLevel:
        return Constants.BIRD_RISK_MAPPING[self.value]

    def __str__(self):
        return f"조류 위험도: {self.enum.value}({self.value})"

@dataclass(frozen=True)
class RunwayRisk:
    runway_id: str  # "A" 또는 "B"
    value: int

    def __post_init__(self):
        if self.runway_id not in ("A", "B"):
            raise ValueError(f"유효하지 않은 활주로 ID: {self.runway_id}")
        if self.value not in Constants.RUNWAY_RISK_MAPPING:
            raise ValueError(f"유효하지 않은 활주로 위험도 값: {self.value}")

    @property
    def enum(self) -> RunwayRiskLevel:
        return Constants.RUNWAY_RISK_MAPPING[self.value]

    def __str__(self):
        return f"활주로 {self.runway_id} 위험도: {self.enum.value}({self.value})"