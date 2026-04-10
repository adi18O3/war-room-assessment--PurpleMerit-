# NovaMind Search — Release Notes

**Version:** 2.0.0 → Hotfix 2.0.1
**Launch Date:** Day 4 | **Hotfix Date:** Day 6
**Current Status:** ⚠️ Partial Recovery — Rollout Paused at 50%

---

## What Is NovaMind Search?

Replaces keyword search with AI-powered natural language search.
Users type queries like *"overdue tasks assigned to John this week"*
instead of exact keywords. Results ranked by relevance using an
intent classification model.

---

## Known Issues at Launch

| ID | Issue | Severity |
|----|-------|----------|
| K1 | Intent model trained on simple queries only — multi-condition accuracy not tested | HIGH |
| K2 | No fallback to keyword search if AI confidence is low | MEDIUM |
| K3 | Search index not load-tested above 10k concurrent users | HIGH |
| K4 | No confidence score shown to users — silent wrong results invisible | HIGH |

> **Note:** K1 and K3 were flagged before launch. Decision to proceed
> was based on internal testing (simple queries only — did not reflect
> real user query complexity).

---

## Hotfix 2.0.1 (Day 6)

**Fixed:** Improved intent parser for 2-condition queries. Accuracy
improved from ~85% to ~89% overall. 3+ condition queries still
degrade to ~72% accuracy.

**Not Fixed:** K2, K4 remain open. A new issue appeared post-hotfix:
search index falling behind under load — newly created tasks take
up to 15 minutes to appear in results (reported Day 7: F20, F21).

---

## Engineering Lead Note (Day 7)

> "Do not expand beyond 50% until: accuracy reaches 95%+ on
> production query mix, indexing lag is resolved, and we hold
> stable for 3 consecutive days. Estimated: 5–7 days if v2.0.2
> ships on schedule."
