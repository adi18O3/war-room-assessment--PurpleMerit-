from agents.base import BaseAgent
from agents.schemas import DataAnalystOutput
from tools.metric_tools import analyze_metrics, detect_anomalies


class DataAnalystAgent(BaseAgent):
    name         = "data_analyst"
    output_class = DataAnalystOutput

    def call_tools(self):
        return {
            "metrics":   analyze_metrics(self.data["metrics"]),
            "anomalies": detect_anomalies(self.data["metrics"]),
        }

    @property
    def system_prompt(self):
        return (
            "You are a data analyst in a product launch war room at PurpleMerit. "
            "Your job is to look at the metrics and tell it like it is — "
            "no spinning, no sugarcoating. If numbers are bad, say so. "
            "Focus on what's recovering vs what's stuck. "
            "Reply with a single JSON object, nothing outside it."
        )

    def user_prompt(self, tool_out):
        m    = tool_out["metrics"]
        anom = tool_out["anomalies"]
        s    = m.get("__summary__", {})

        anom_str = "\n".join(
            f"  day {a['day']} | {a['metric']} | z={a['z_score']} | {a['type']}"
            for a in anom[:4]
        ) or "  none above threshold"

        return f"""
Feature: {self.data['metrics']['feature']} — Day 7

METRICS:
{self._metric_table(m)}

Summary: {s.get('critical', 0)} critical  {s.get('degraded', 0)} degraded  {s.get('healthy', 0)} healthy

ANOMALIES (z >= 2.0):
{anom_str}

Things to keep in mind:
- search_accuracy_pct dropped to 88.9% — still 6 points below target after the hotfix
- query_response_time spiked to 1240ms on day 5, now 590ms — still above 400ms target
- churn_per_day is at 24 today vs baseline ~7 — still climbing (lags the experience by 3-4 days)
- daily_active_users is ABOVE baseline — people are using the feature, just getting wrong results

Respond with:
{{
  "verdict": "PROCEED|PAUSE|ROLLBACK",
  "confidence": 0.0-1.0,
  "health_score": 0.0-1.0,
  "critical_metrics": ["worst metrics right now"],
  "positive_signals": ["metrics that argue against rolling back"],
  "key_finding": "the single most important thing you found in the data",
  "summary": "2-3 sentences, data analyst perspective"
}}"""
