# War Room

Multi-agent system that simulates a product launch war room.
Analyses metrics + user feedback and produces a structured launch decision: **Proceed / Pause / Roll Back**.

Built for Assessment 1 — PurpleMerit AI/ML Engineer position.

---

## The scenario

**Feature:** NovaMind Search — replaces keyword search with AI-powered natural language search at PurpleMerit.

**What happened:** Launched to 50% of users on Day 4. Engagement went up immediately. But the AI silently returns wrong results on complex multi-condition queries (~11% error rate). Users don't see an error — they just get wrong answers. Some acted on those results for real business decisions. A new indexing lag emerged on Day 7. Churn is rising.

**The question the war room answers:** Do we proceed with full rollout, pause and fix, or roll back?

---

## How it works

```
data/
  metrics.json       6 metrics x 7 days
  feedback.json      25 user feedback entries
  release_notes.md   feature context + known issues at launch

tools/
  analyze_metrics()    health score per metric, trend direction
  detect_anomalies()   z-score spikes
  analyze_sentiment()  sentiment counts, themes, trajectory
  flag_risks()         high-severity items, enterprise escalations

agents/                each agent calls tools then prompts the LLM
  data_analyst    →    PHASE 1 (run concurrently)
  pm_agent        →    PHASE 1
  marketing_agent →    PHASE 1
  risk_agent      →    PHASE 2 (runs after phase 1, challenges their conclusions)

orchestrator.py
  phase 1: asyncio.gather(DA + PM + Marketing)
  phase 2: Risk agent reviews all phase 1 outputs
  phase 3: weighted vote → final decision JSON
```

The orchestrator collects votes from all agents, applies a weighted score, and gives the risk agent veto power over any PROCEED recommendation.

---

## Setup

```bash
pip install -r requirements.txt

# pull a model if you haven't already
ollama pull llama3.1:8b

# run
python main.py

# or test without ollama
python main.py --dry-run
```

---

## Options

```
--dry-run            skip LLM calls, use mock responses
--model <name>       use a different ollama model
--log-level DEBUG    more verbose output
```

---

## Output

`outputs/war_room_decision.json` — the structured decision:

```json
{
  "decision": "PAUSE",
  "confidence_score": 0.73,
  "rationale": "...",
  "agent_votes": { "data_analyst": "PAUSE", "pm_agent": "PAUSE", ... },
  "key_drivers": ["..."],
  "risk_register": [
    { "risk": "...", "severity": "critical", "mitigation": "...", "owner": "..." }
  ],
  "action_plan": [
    { "action": "...", "owner": "...", "deadline": "24h" }
  ],
  "communication_plan": { "internal": "...", "external": "...", ... },
  "proceed_conditions": ["..."],
  "metric_snapshot": { ... },
  "feedback_snapshot": { ... }
}
```

`logs/trace.log` — what each agent did, how long it took, structured JSON at the bottom.

---

## Config

All settings in `config.py`. Override via env or `.env` file:

| var | default | what it does |
|-----|---------|--------------|
| OLLAMA_URL | http://localhost:11434 | where ollama is running |
| OLLAMA_MODEL | llama3.1:8b | model to use |
| OLLAMA_TIMEOUT | 120 | seconds per llm call |
| DRY_RUN | false | skip llm, use mocks |
| LOG_LEVEL | INFO | DEBUG / INFO / WARNING |

Copy `.env.example` to `.env` if you want to customise.

---

## Troubleshooting

**ollama not running:**
```bash
ollama serve
ollama pull llama3.1:8b
```

**model not found:**
```bash
python main.py --model mistral:7b
# or whatever model you have pulled
```

**just want to see the output format without running llm:**
```bash
python main.py --dry-run
```
