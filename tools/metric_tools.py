import statistics


def analyze_metrics(metrics_data: dict) -> dict:
    """
    For each metric, compute status vs target and trend direction.
    Returns a dict agents can read directly in their prompts.
    """
    results = {}

    for name, m in metrics_data["metrics"].items():
        vals     = [d["value"] for d in m["daily"]]
        target   = m["target"]
        latest   = vals[-1]

        pre_vals = [d["value"] for d in m["daily"] if d["phase"] == "pre_launch"]
        baseline = statistics.mean(pre_vals) if pre_vals else target

        # for tickets/latency/churn, going up is bad
        lower_is_better = any(k in name for k in ["ticket", "time", "churn"])

        if lower_is_better:
            pct = round(((latest - baseline) / baseline) * -100, 1)
        else:
            pct = round(((latest - baseline) / baseline) * 100, 1)

        if pct >= 5:
            status = "healthy"
        elif pct >= -5:
            status = "at_risk"
        elif pct >= -20:
            status = "degraded"
        else:
            status = "critical"

        # simple trend: just compare last two days
        if len(vals) >= 2:
            if lower_is_better:
                trend = "improving" if vals[-1] < vals[-2] else "worsening"
            else:
                trend = "improving" if vals[-1] > vals[-2] else "worsening"
        else:
            trend = "unknown"

        results[name] = {
            "latest":           latest,
            "baseline":         round(baseline, 1),
            "target":           target,
            "pct_vs_baseline":  pct,
            "status":           status,
            "trend":            trend,
            "unit":             m["unit"],
            "description":      m["description"],
        }

    statuses = [v["status"] for v in results.values()]
    results["__summary__"] = {
        "healthy":  statuses.count("healthy"),
        "at_risk":  statuses.count("at_risk"),
        "degraded": statuses.count("degraded"),
        "critical": statuses.count("critical"),
    }
    return results


def detect_anomalies(metrics_data: dict, z_threshold: float = 2.0) -> list:
    """
    Z-score based anomaly detection. Anything beyond z_threshold gets flagged.
    Sorted bad-first so agents see the worst stuff at the top.
    """
    found = []

    for name, m in metrics_data["metrics"].items():
        vals = [d["value"] for d in m["daily"]]
        if len(vals) < 4:
            continue

        mean = statistics.mean(vals)
        std  = statistics.stdev(vals)
        if std == 0:
            continue

        lower_is_better = any(k in name for k in ["ticket", "time", "churn"])

        for entry in m["daily"]:
            z = (entry["value"] - mean) / std
            if abs(z) < z_threshold:
                continue

            bad = (z > 0) if lower_is_better else (z < 0)

            found.append({
                "metric":  name,
                "day":     entry["day"],
                "value":   entry["value"],
                "z_score": round(z, 2),
                "type":    "bad_spike" if bad else "good_spike",
            })

    found.sort(key=lambda x: (x["type"] != "bad_spike", -abs(x["z_score"])))
    return found
