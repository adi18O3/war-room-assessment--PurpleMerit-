from agents.base import BaseAgent
from agents.schemas import PMAgentOutput
from tools.metric_tools import analyze_metrics


class PMAgentAgent(BaseAgent):
    name         = "pm_agent"
    output_class = PMAgentOutput

    def call_tools(self):
        return {"metrics": analyze_metrics(self.data["metrics"])}

    @property
    def system_prompt(self):
        return (
            "You are the product manager who owns NovaMind Search at PurpleMerit. "
            "You defined the success criteria for this launch and you need to be honest "
            "about whether they're being met. Don't defend the feature just because it's yours. "
            "Be specific about user impact. Reply with a single JSON object only."
        )

    def user_prompt(self, tool_out):
        m = tool_out["metrics"]

        acc   = m.get("search_accuracy_pct", {})
        nps   = m.get("nps_score", {})
        tick  = m.get("support_tickets_per_day", {})
        churn = m.get("churn_per_day", {})

        # hard success criteria
        criteria = {
            "accuracy_at_least_95pct":           acc.get("status") == "healthy",
            "nps_not_dropped_more_than_5pts":     (nps.get("pct_vs_baseline") or -99) >= -5,
            "support_tickets_under_2x_baseline":  (tick.get("latest") or 999) <= 36,
            "churn_within_20pct_of_baseline":     (churn.get("latest") or 999) <= 9.6,
        }
        met    = [k for k, v in criteria.items() if v]
        failed = [k for k, v in criteria.items() if not v]

        da_note = ""
        if "data_analyst" in self.phase1:
            da_note = f"\nDA says: {getattr(self.phase1['data_analyst'], 'summary', '')}"

        return f"""
NovaMind Search — Day 7 launch review
{da_note}

SUCCESS CRITERIA CHECK:
  met    : {met or "none"}
  failed : {failed or "none"}

METRICS:
{self._metric_table(m)}

Context:
- We compressed the timeline from 6 weeks to 4. The intent model wasn't tested on complex queries.
- Globex Corp (enterprise account) formally escalated — their PM used search results for a board briefing and the data was wrong.
- Hotfix on day 6 improved accuracy from ~85% to 88.9% but target is 95%.
- New problem day 7: search index lagging — newly created tasks aren't showing up in results.
- 13,500 users active right now. Pulling the feature would hurt them too.

Respond with:
{{
  "verdict": "GO|PAUSE|NO_GO",
  "confidence": 0.0-1.0,
  "criteria_met": ["..."],
  "criteria_failed": ["..."],
  "user_impact": "rough description of how many users are affected and how badly",
  "recommended_actions": [
    {{"action": "...", "owner": "...", "deadline": "24h or 48h"}}
  ],
  "summary": "2-3 sentences as PM"
}}"""
