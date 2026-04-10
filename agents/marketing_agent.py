from agents.base import BaseAgent
from agents.schemas import MarketingAgentOutput
from tools.feedback_tools import analyze_sentiment


class MarketingAgent(BaseAgent):
    name         = "marketing_agent"
    output_class = MarketingAgentOutput

    def call_tools(self):
        return {"sentiment": analyze_sentiment(self.data["feedback"])}

    @property
    def system_prompt(self):
        return (
            "You run comms and marketing at PurpleMerit. "
            "Your job right now is to assess the brand damage from the NovaMind Search launch "
            "and figure out what to tell people — internally and externally. "
            "The tricky part: this is a silent failure. Users don't see an error, "
            "they just get wrong answers. That's harder to communicate than a crash. "
            "Be practical. Reply with a single JSON object only."
        )

    def user_prompt(self, tool_out):
        s = tool_out["sentiment"]

        themes_str = "\n".join(
            f"  {cnt}x  {theme}"
            for theme, cnt in list(s["top_themes"].items())[:5]
        )

        daily_str = "  " + "  |  ".join(
            f"day{d}: {sc:+.1f}"
            for d, sc in s["daily_scores"].items()
        )

        quotes_str = "\n".join(
            f'  "{q[:90]}"'
            for q in s["power_user_quotes"]
        ) or "  none"

        return f"""
NovaMind Search — Day 7 feedback summary

SENTIMENT:
  total      : {s['total']}
  positive   : {s['counts']['positive']}
  neutral    : {s['counts']['neutral']}
  negative   : {s['counts']['negative']}
  net score  : {s['net_score']} (scale: -100 to +100)
  trajectory : {s['trajectory']}

Daily scores (+1 = all positive, -1 = all negative):
{daily_str}

Top feedback themes:
{themes_str}

Users who actually love the feature (keep this in mind):
{quotes_str}

Brand risks:
- Two public social complaints already posted (F08, F20)
- Globex Corp enterprise escalation — board meeting was affected
- The problem is invisible: users think search is working until they verify manually
- 24 cancellations today vs 7/day baseline

Respond with:
{{
  "verdict": "POSITIVE|CAUTIOUS|HOLD|CRISIS",
  "confidence": 0.0-1.0,
  "brand_risk": "low|medium|high|critical",
  "sentiment_summary": "2 sentences on where customer perception is right now",
  "internal_message": "what to tell the team today",
  "external_message": "what (if anything) to say publicly to affected users",
  "enterprise_action": "what specifically to do about Globex Corp",
  "summary": "2-3 sentences on the comms situation"
}}"""
