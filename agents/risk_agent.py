from agents.base import BaseAgent
from agents.schemas import RiskAgentOutput
from tools.feedback_tools import flag_risks
from tools.metric_tools import detect_anomalies


class RiskAgent(BaseAgent):
    """
    Runs in phase 2, after all other agents have reported.
    Its job is to push back, find what was missed, and make sure
    we're not sleepwalking into a bigger problem.
    """
    name         = "risk_agent"
    output_class = RiskAgentOutput

    def call_tools(self):
        return {
            "risks":     flag_risks(self.data["feedback"]),
            "anomalies": detect_anomalies(self.data["metrics"]),
        }

    @property
    def system_prompt(self):
        return (
            "You are the risk and quality voice in this war room. "
            "The other agents have already given their takes — your job is to challenge them. "
            "Find what they glossed over, what could go worse, and what conditions "
            "would need to be true before you'd feel comfortable proceeding. "
            "Silent wrong results are more dangerous than crashes — "
            "users act on bad data without knowing it. Weight that heavily. "
            "Reply with a single JSON object only."
        )

    def user_prompt(self, tool_out):
        r    = tool_out["risks"]
        anom = tool_out["anomalies"]

        da_v  = getattr(self.phase1.get("data_analyst"),   "verdict",  "N/A")
        pm_v  = getattr(self.phase1.get("pm_agent"),        "verdict",  "N/A")
        mkt_v = getattr(self.phase1.get("marketing_agent"), "verdict",  "N/A")
        da_s  = getattr(self.phase1.get("data_analyst"),   "summary",  "")
        pm_s  = getattr(self.phase1.get("pm_agent"),        "summary",  "")

        high_sev_str = "\n".join(
            f"  [{e['id']}] day {e['day']}: {e['text'][:100]}"
            for e in r["high_severity"][:4]
        ) or "  none"

        new_issues_str = "\n".join(
            f"  [{e['id']}] day {e['day']}: {e['text'][:100]}"
            for e in r["new_issues"]
        ) or "  none"

        enterprise_str = "\n".join(
            f"  [{e['id']}] {e['text'][:100]}"
            for e in r["enterprise"]
        ) or "  none"

        return f"""
NovaMind Search — Day 7 — Phase 2 risk review

PHASE 1 VERDICTS (push back where you disagree):
  Data Analyst : {da_v} — "{da_s[:120]}"
  PM Agent     : {pm_v}
  Marketing    : {mkt_v}

RISK SCORE: {r['risk_score']} / 10 — {r['risk_level'].upper()}

High-severity feedback:
{high_sev_str}

Enterprise escalations:
{enterprise_str}

New issues (appeared post-hotfix, unresolved):
{new_issues_str}

Churn signals: {len(r['churn_signals'])} entries mention cancellation

Key facts:
- Accuracy is 88.9% after hotfix. Target is 95%. That's not close.
- Indexing lag appeared day 7 — tasks created today don't show in search. Root cause unknown.
- Churn is 24/day vs 7 baseline. Still rising. It'll keep rising for a few more days even if we fix everything today.
- Globex Corp enterprise complaint: their board meeting was based on wrong search output.
- F05 and F10: users acted on wrong results without knowing. That's liability, not just UX.
- 13,500 users are active — rollback disrupts them too.

Respond with:
{{
  "verdict": "PROCEED|PAUSE|ROLLBACK",
  "confidence": 0.0-1.0,
  "overall_risk": "low|medium|high|critical",
  "challenges": [
    "a specific pushback on something a phase 1 agent said or missed"
  ],
  "risk_register": [
    {{
      "risk": "specific risk",
      "severity": "low|medium|high|critical",
      "mitigation": "concrete action",
      "owner": "Engineering|PM|Support|Legal|Marketing"
    }}
  ],
  "proceed_conditions": [
    "specific, measurable condition that has to be true before we proceed"
  ],
  "critical_finding": "the most important thing the other agents may have missed",
  "summary": "2-3 sentences from a risk perspective"
}}"""
