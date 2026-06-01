from dataclasses import dataclass, field
from typing import Literal


WarningType = Literal["unsupported_date", "missing_entity", "vague_reference", "input_error"]
Severity = Literal["high", "medium", "low"]
Action = Literal["proceed", "review"]


@dataclass
class Warning:
    severity: Severity
    type: WarningType
    text: str
    suggestion: str


@dataclass
class Summary:
    high: int = 0
    medium: int = 0
    low: int = 0


@dataclass
class VerifyResult:
    action: Action
    warnings: list[Warning] = field(default_factory=list)
    summary: Summary = field(default_factory=Summary)

    @classmethod
    def input_error(cls, message: str) -> "VerifyResult":
        w = Warning(severity="high", type="input_error", text=message, suggestion="Check input before calling verify().")
        return cls(action="review", warnings=[w], summary=Summary(high=1))
