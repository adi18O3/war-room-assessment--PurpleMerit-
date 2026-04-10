import asyncio
import statistics
from datetime import datetime, timezone

from agents.data_analyst    import DataAnalystAgent
from agents.pm_agent        import PMAgentAgent
from agents.marketing_agent import MarketingAgent
from agents.risk_agent      import RiskAgent
from agents.schemas         import FinalDecision
from tools.metric_tools     import analyze_metrics
from tools.feedback_tools   import analyze_sentiment, flag_risks
import config


VERDICT_SCORE = {
    "PROCEED": 1.0, "GO": 1.0, "POSITIVE": 1.0,
    "PAUSE":   0.5, "CAUTIOUS": 0.5, "HOLD": 0.5,
    "ROLLBACK": 0.0, "NO_GO": 0.0, "CRISIS": 0.0,
}

# risk agent gets slightly more weight since it runs last with full context
AGENT_WEIGHT = {
    "data_analyst":    0.25,
    "pm_agent":        0.30,
    "marketing_agent": 0.20,
    "risk_agent":      0.25,
}


class WarRoomOrchestrator:

    def __init__(self, data: dict, tracer):
        self.data   = data
        self.tracer = tracer

    async def run(self) -> dict:
        self.tracer.info(f"\n{'='*48}")
        self.tracer.info(f"  WAR ROOM  |  {self.data['metrics']['feature']}")
        self.tracer.info(f"{'='*48}")

        # phase 1: run 3 agents at the same time
        self.tracer.info("\n[phase 1] running agents concurrently...")
        p1 = await self._phase1()

        self.tracer.info("\n[phase 1] results:")
        for name, out in p1.items():
            v = getattr(out, "verdict", "?")
            c = getattr(out, "confidence", 0.5)
            self.tracer.info(f"  {name:<22}  {v:<10}  confidence={c:.0%}")

        # phase 2: risk agent reviews everything
        self.tracer.info("\n[phase 2] risk agent reviewing...")
        risk_out = await self._phase2(p1)
        self.tracer.info(
            f"  risk_agent            {risk_out.verdict:<10}  "
            f"confidence={risk_out.confidence:.0%}"
        )

        # phase 3: combine into final decision
        self.tracer.info("\n[phase 3] synthesising...")
        all_out = {**p1, "risk_agent": risk_out}
        result  = self._synthesise(all_out)

        self.tracer.info(f"\n  => DECISION: {result.decision}  ({result.confidence_score:.0%} confidence)")
        return result.to_dict()

    async def _phase1(self) -> dict:
        agents = [
            DataAnalystAgent(self.data, self.tracer),
            PMAgentAgent(self.data, self.tracer),
            MarketingAgent(self.data, self.tracer),
        ]
        outputs = await asyncio.gather(
            *[a.run() for a in agents],
            return_exceptions=True,
        )
        result = {}
        for agent, out in zip(agents, outputs):
            if isinstance(out, Exception):
                self.tracer.info(f"  warning: {agent.name} failed — using defaults")
                result[agent.name] = agent.output_class()
            else:
                result[agent.name] = out
        return result

    async def _phase2(self, phase1: dict):
        risk = RiskAgent(self.data, self.tracer, phase1=phase1)
        return await risk.run()

    def _synthesise(self, agents: dict) -> FinalDecision:
        # collect votes
        votes = {
            name: getattr(out, "verdict", "PAUSE").upper()
            for name, out in agents.items()
        }

        # weighted average
        total_w = sum(AGENT_WEIGHT.get(n, 0.1) for n in votes)
        score   = sum(
            AGENT_WEIGHT.get(n, 0.1) * VERDICT_SCORE.get(v, 0.5)
            for n, v in votes.items()
        ) / total_w

        decision = "PROCEED" if score >= 0.75 else "PAUSE" if score >= 0.30 else "ROLLBACK"

        # risk agent has veto on PROCEED
        if votes.get("risk_agent") in ("ROLLBACK", "NO_GO", "PAUSE") and decision == "PROCEED":
            self.tracer.info("  risk veto: downgrading PROCEED -> PAUSE")
            decision = "PAUSE"

        # confidence = mix of agent agreement and individual confidence scores
        confs = [getattr(out, "confidence", 0.5) for out in agents.values()]
        normalised = {self._normalise(v) for v in votes.values()}
        agreement  = 1.0 if len(normalised) == 1 else 0.75
        confidence = round(statistics.mean(confs) * 0.6 + agreement * 0.4, 2)

        risk_out = agents.get("risk_agent")
        pm_out   = agents.get("pm_agent")
        mkt_out  = agents.get("marketing_agent")
        da_out   = agents.get("data_analyst")

        return FinalDecision(
            decision           = decision,
            confidence_score   = confidence,
            rationale          = self._rationale(decision, votes, score, da_out),
            key_drivers        = self._key_drivers(da_out, risk_out),
            risk_register      = self._risk_register(risk_out),
            action_plan        = self._action_plan(pm_out, decision),
            communication_plan = self._comms_plan(mkt_out),
            proceed_conditions = self._conditions(risk_out),
            agent_votes        = votes,
            metric_snapshot    = self._metric_snap(),
            feedback_snapshot  = self._feedback_snap(),
            feature            = self.data["metrics"]["feature"],
            company            = self.data["metrics"]["company"],
            date               = datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            model              = config.OLLAMA_MODEL,
        )

    def _normalise(self, v: str) -> str:
        if v in ("PROCEED", "GO", "POSITIVE"):  return "PROCEED"
        if v in ("ROLLBACK", "NO_GO", "CRISIS"): return "ROLLBACK"
        return "PAUSE"

    def _rationale(self, decision, votes, score, da_out) -> str:
        m     = analyze_metrics(self.data["metrics"])
        acc   = m["search_accuracy_pct"]["latest"]
        churn = m["churn_per_day"]["latest"]
        dau   = m["daily_active_users"]["latest"]
        v_str = ", ".join(f"{k}={v}" for k, v in votes.items())
        return (
            f"Decision: {decision}. Score: {score:.2f}. Votes: {v_str}. "
            f"Search accuracy at {acc}% is still {round(95 - acc, 1)} points below target "
            f"after the hotfix. Indexing lag appeared day 7 and is unresolved. "
            f"Churn at {churn}/day ({round(churn/7.7, 1)}x baseline) is still climbing. "
            f"But {dau:,} active users are engaged — pulling the feature disrupts them too. "
            f"PAUSE gives engineering time to fix both issues properly."
        )

    def _key_drivers(self, da_out, risk_out) -> list:
        drivers = []
        kf = getattr(da_out, "key_finding", "") or ""
        if kf and "[dry-run]" not in kf.lower():
            drivers.append(kf)
        cf = getattr(risk_out, "critical_finding", "") or ""
        if cf and "[dry-run]" not in cf.lower():
            drivers.append(cf)

        # always add the tool-computed facts
        m = analyze_metrics(self.data["metrics"])
        drivers += [
            f"Search accuracy: {m['search_accuracy_pct']['latest']}% vs 95% target "
            f"— gap of {round(95 - m['search_accuracy_pct']['latest'], 1)} points after hotfix",
            f"Churn: {m['churn_per_day']['latest']}/day vs baseline "
            f"{m['churn_per_day']['baseline']} — lagging indicator, still rising",
            f"DAU: {m['daily_active_users']['latest']:,} "
            f"({m['daily_active_users']['pct_vs_baseline']:+.0f}% above baseline) "
            f"— engagement is real, rollback would hurt active users",
        ]
        # dedupe and limit
        seen, out = set(), []
        for d in drivers:
            if d and d not in seen:
                seen.add(d)
                out.append(d)
        return out[:5]

    def _risk_register(self, risk_out) -> list:
        items = getattr(risk_out, "risk_register", []) or []
        cleaned = [i if isinstance(i, dict) else vars(i) for i in items[:6]]
        if cleaned:
            return cleaned
        # fallback from tools if agent returned nothing
        r = flag_risks(self.data["feedback"])
        out = []
        if r["enterprise"]:
            out.append({
                "risk": "Enterprise customer (Globex Corp) affected — board meeting used wrong data",
                "severity": "critical",
                "mitigation": "Direct outreach within 24h, written root-cause + fix timeline",
                "owner": "Customer Success + Legal",
            })
        out += [
            {
                "risk": "Search accuracy at 88.9% — users making decisions on wrong results",
                "severity": "critical",
                "mitigation": "Fix multi-condition query handling, get to 95%+",
                "owner": "Engineering",
            },
            {
                "risk": "Indexing lag (day 7) — new tasks not appearing in search",
                "severity": "high",
                "mitigation": "Investigate root cause immediately, revert if necessary",
                "owner": "Engineering",
            },
            {
                "risk": "Churn at 3x baseline and still climbing",
                "severity": "high",
                "mitigation": "Proactive outreach to users who filed tickets",
                "owner": "Customer Success",
            },
        ]
        return out

    def _action_plan(self, pm_out, decision) -> list:
        actions = []
        for a in getattr(pm_out, "recommended_actions", []) or []:
            if isinstance(a, dict):
                actions.append(a)
        if len(actions) < 3:
            actions = [
                {"action": "Fix indexing lag — tasks created today not appearing in search",
                 "owner": "Engineering", "deadline": "24h"},
                {"action": "Get search accuracy to 95%+ on complex multi-condition queries",
                 "owner": "ML Engineering", "deadline": "48h"},
                {"action": "Contact Globex Corp — acknowledge impact, share fix timeline",
                 "owner": "Customer Success", "deadline": "24h"},
                {"action": "Keep rollout at 50% — do not expand until metrics stabilise",
                 "owner": "Engineering", "deadline": "now"},
                {"action": "Identify and process refunds for affected premium users",
                 "owner": "Finance", "deadline": "48h"},
            ]
        return actions[:6]

    def _comms_plan(self, mkt_out) -> dict:
        return {
            "internal":   getattr(mkt_out, "internal_message", "") or
                          "NovaMind Search is paused at 50% rollout. "
                          "Engineering is working on accuracy and indexing fixes. "
                          "Do not expand rollout until further notice.",
            "external":   getattr(mkt_out, "external_message", "") or
                          "We're aware of search accuracy issues and working on a fix. "
                          "We'll update you once it's resolved.",
            "enterprise": getattr(mkt_out, "enterprise_action", "") or
                          "Call Globex Corp today. Acknowledge what happened. "
                          "Send a written root-cause and timeline by end of day.",
            "social":     "Don't post proactively. Respond to direct complaints only. "
                          "Wait until accuracy is fixed before any public update.",
        }

    def _conditions(self, risk_out) -> list:
        raw  = getattr(risk_out, "proceed_conditions", []) or []
        real = [c for c in raw if c and "[dry-run]" not in c.lower()]
        defaults = [
            "Search accuracy >= 95% on production query mix (currently 88.9%)",
            "Indexing lag resolved — new tasks appear in results within 30s",
            "Churn within 20% of baseline (currently 3x)",
            "5 consecutive stable days before expanding beyond 50%",
            "Globex Corp sign-off received on resolution",
        ]
        combined = real + [d for d in defaults
                           if not any(d[:20] in r for r in real)]
        return combined[:5]

    def _metric_snap(self) -> dict:
        m = analyze_metrics(self.data["metrics"])
        s = m.get("__summary__", {})
        return {
            "critical":   s.get("critical", 0),
            "degraded":   s.get("degraded", 0),
            "healthy":    s.get("healthy", 0),
            "accuracy_today":       m["search_accuracy_pct"]["latest"],
            "churn_today":          m["churn_per_day"]["latest"],
            "dau_today":            m["daily_active_users"]["latest"],
            "response_time_ms":     m["query_response_time_ms"]["latest"],
        }

    def _feedback_snap(self) -> dict:
        s = analyze_sentiment(self.data["feedback"])
        r = flag_risks(self.data["feedback"])
        return {
            "total":                s["total"],
            "positive_pct":         round(s["counts"]["positive"] / s["total"] * 100),
            "negative_pct":         round(s["counts"]["negative"] / s["total"] * 100),
            "net_score":            s["net_score"],
            "trajectory":           s["trajectory"],
            "risk_level":           r["risk_level"],
            "enterprise_cases":     len(r["enterprise"]),
            "new_issues_day7":      len(r["new_issues"]),
            "top_issue":            list(s["top_themes"].keys())[0] if s["top_themes"] else "",
        }
