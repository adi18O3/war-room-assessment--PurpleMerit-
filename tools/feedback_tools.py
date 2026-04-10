from collections import Counter


def analyze_sentiment(feedback_data: dict) -> dict:
    entries = feedback_data["entries"]
    total   = len(entries)

    counts = {"positive": 0, "neutral": 0, "negative": 0}
    for e in entries:
        counts[e["sentiment"]] = counts.get(e["sentiment"], 0) + 1

    net = round((counts["positive"] - counts["negative"]) / total * 100, 1)

    # skip system meta-tags when counting themes
    skip = {"REPEATED_ISSUE", "HIGH_SEVERITY", "NEW_ISSUE"}
    all_tags = [t for e in entries for t in e.get("tags", []) if t not in skip]
    top_themes = dict(Counter(all_tags).most_common(6))

    # daily sentiment score: positive=+1, negative=-1, neutral=0
    by_day: dict[int, list] = {}
    for e in entries:
        by_day.setdefault(e["day"], []).append(e["sentiment"])

    daily_scores = {}
    for day, sents in sorted(by_day.items()):
        score = sum(1 if s == "positive" else (-1 if s == "negative" else 0)
                    for s in sents) / len(sents)
        daily_scores[day] = round(score, 2)

    days   = sorted(daily_scores.keys())
    mid    = len(days) // 2
    early  = sum(list(daily_scores.values())[:mid]) / max(mid, 1)
    recent = sum(list(daily_scores.values())[mid:]) / max(len(days) - mid, 1)

    if recent > early + 0.1:
        trajectory = "improving"
    elif recent < early - 0.1:
        trajectory = "degrading"
    else:
        trajectory = "mixed"

    power_quotes = [
        e["text"] for e in entries
        if "power_user" in e.get("tags", []) and e["sentiment"] == "positive"
    ][:3]

    return {
        "total":             total,
        "counts":            counts,
        "net_score":         net,
        "top_themes":        top_themes,
        "trajectory":        trajectory,
        "daily_scores":      daily_scores,
        "power_user_quotes": power_quotes,
    }


def flag_risks(feedback_data: dict) -> dict:
    """Pull out the feedback items that carry real risk — for the risk agent."""
    entries = feedback_data["entries"]

    high_sev    = [{"id": e["id"], "day": e["day"], "text": e["text"]}
                   for e in entries if "HIGH_SEVERITY" in e.get("tags", [])]
    enterprise  = [{"id": e["id"], "day": e["day"], "text": e["text"]}
                   for e in entries if "enterprise_escalation" in e.get("tags", [])]
    biz_impact  = [{"id": e["id"], "day": e["day"], "text": e["text"]}
                   for e in entries if "business_impact" in e.get("tags", [])]
    new_issues  = [{"id": e["id"], "day": e["day"], "text": e["text"]}
                   for e in entries if "NEW_ISSUE" in e.get("tags", [])]
    churn_sigs  = [{"id": e["id"], "day": e["day"], "text": e["text"][:80]}
                   for e in entries
                   if any(t in e.get("tags", []) for t in ["churn", "cancellation"])]

    # rough risk score
    score = min(10, (
        len(high_sev)   * 1.5 +
        len(enterprise) * 2.5 +
        len(biz_impact) * 2.0 +
        len(new_issues) * 1.5
    ))

    level = "critical" if score >= 7 else "high" if score >= 4 else "medium"

    return {
        "risk_score":    round(score, 1),
        "risk_level":    level,
        "high_severity": high_sev,
        "enterprise":    enterprise,
        "biz_impact":    biz_impact,
        "new_issues":    new_issues,
        "churn_signals": churn_sigs,
    }
