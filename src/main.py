"""Dedupe synthetic alerts and rank representatives without using ground-truth labels."""

import json
import random
from collections import Counter
from pathlib import Path


def key(alert: dict) -> tuple:
    return (alert["asset"], alert["family"], int(alert["at"] // 60))


def dedupe(alerts: list[dict]) -> list[dict]:
    counts = Counter(a["family"] for a in alerts)
    groups = {}
    for alert in alerts:
        signature = key(alert)
        existing = groups.get(signature)
        if existing is None or alert["severity"] > existing["severity"]:
            groups[signature] = alert
    return sorted(
        [
            {
                **a,
                "novelty_score": 1 / counts[a["family"]],
                "rank_score": a["severity"] + 1 / counts[a["family"]],
            }
            for a in groups.values()
        ],
        key=lambda a: (-a["rank_score"], a["id"]),
    )


def generate() -> list[dict]:
    rng = random.Random(42)
    alerts = []
    for incident in range(100):
        positive = incident % 7 == 0
        for repeat in range(rng.randint(4, 10)):
            alerts.append(
                {
                    "id": f"alert-{incident}-{repeat}",
                    "incident": f"incident-{incident}",
                    "asset": f"SYN-HOST-{incident % 20}",
                    "family": ["auth-failure", "process-start", "port-scan", "health-check"][
                        incident % 4
                    ],
                    "at": incident * 120 + repeat,
                    "severity": 8 if positive else rng.choice([1, 2, 3]),
                    "true_positive": positive,
                }
            )
    # A genuine collision: two distinct labeled events share the observed dedupe signature.
    alerts.extend(
        [
            {
                "id": "collision-a",
                "incident": "distinct-a",
                "asset": "SYN-COLLISION",
                "family": "auth-failure",
                "at": 10,
                "severity": 9,
                "true_positive": True,
            },
            {
                "id": "collision-b",
                "incident": "distinct-b",
                "asset": "SYN-COLLISION",
                "family": "auth-failure",
                "at": 11,
                "severity": 8,
                "true_positive": True,
            },
        ]
    )
    return alerts


def benchmark() -> dict:
    alerts = generate()
    kept = dedupe(alerts)
    truth = {a["incident"] for a in alerts if a["true_positive"]}
    retained = {a["incident"] for a in kept if a["true_positive"]}
    raw_positive = sum(a["true_positive"] for a in alerts)
    kept_positive = sum(a["true_positive"] for a in kept)
    Path("evidence/triaged.json").write_text(json.dumps(kept, indent=2))
    Path("evidence/collisions.json").write_text(
        json.dumps([a for a in alerts if a["incident"] in truth - retained], indent=2)
    )
    return {
        "input_alerts": len(alerts),
        "retained_alerts": len(kept),
        "volume_reduction_percent": 100 * (1 - len(kept) / len(alerts)),
        "true_positive_incident_recall": len(truth & retained) / len(truth),
        "raw_positive_alert_retention": kept_positive / raw_positive,
        "true_incidents": len(truth),
        "retained_true_incidents": len(retained),
    }


if __name__ == "__main__":
    print(json.dumps(benchmark(), indent=2))
