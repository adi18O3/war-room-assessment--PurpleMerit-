# Output schemas for each agent.
# Using stdlib dataclasses — no pydantic dependency needed.

from __future__ import annotations
import dataclasses
from dataclasses import dataclass, field


class _Base:
    @classmethod
    def from_dict(cls, data: dict):
        if not isinstance(data, dict):
            return cls()
        known = {f.name for f in dataclasses.fields(cls)}
        clean = {k: v for k, v in data.items() if k in known}
        try:
            return cls(**clean)
        except Exception:
            return cls()

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass
class DataAnalystOutput(_Base):
    verdict:          str   = "PAUSE"
    confidence:       float = 0.5
    health_score:     float = 0.5
    critical_metrics: list  = field(default_factory=list)
    positive_signals: list  = field(default_factory=list)
    key_finding:      str   = ""
    summary:          str   = ""


@dataclass
class PMAgentOutput(_Base):
    verdict:             str   = "PAUSE"
    confidence:          float = 0.5
    criteria_met:        list  = field(default_factory=list)
    criteria_failed:     list  = field(default_factory=list)
    user_impact:         str   = ""
    recommended_actions: list  = field(default_factory=list)
    summary:             str   = ""


@dataclass
class MarketingAgentOutput(_Base):
    verdict:           str   = "HOLD"
    confidence:        float = 0.5
    brand_risk:        str   = "high"
    sentiment_summary: str   = ""
    internal_message:  str   = ""
    external_message:  str   = ""
    enterprise_action: str   = ""
    summary:           str   = ""


@dataclass
class RiskAgentOutput(_Base):
    verdict:            str   = "PAUSE"
    confidence:         float = 0.5
    overall_risk:       str   = "high"
    challenges:         list  = field(default_factory=list)
    risk_register:      list  = field(default_factory=list)
    proceed_conditions: list  = field(default_factory=list)
    critical_finding:   str   = ""
    summary:            str   = ""


@dataclass
class FinalDecision(_Base):
    decision:            str   = "PAUSE"
    confidence_score:    float = 0.5
    rationale:           str   = ""
    key_drivers:         list  = field(default_factory=list)
    risk_register:       list  = field(default_factory=list)
    action_plan:         list  = field(default_factory=list)
    communication_plan:  dict  = field(default_factory=dict)
    proceed_conditions:  list  = field(default_factory=list)
    agent_votes:         dict  = field(default_factory=dict)
    metric_snapshot:     dict  = field(default_factory=dict)
    feedback_snapshot:   dict  = field(default_factory=dict)
    feature:             str   = ""
    company:             str   = ""
    date:                str   = ""
    model:               str   = ""
