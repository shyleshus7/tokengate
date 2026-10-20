"""Generates the large mock JSON payloads in data/ (deterministic, no external services).

Run from the repo root:  python -m src.make_mock_data
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SERVICES = ["checkout-api", "auth-service", "payments-worker", "inventory-db", "search-gateway"]
LEVELS = ["INFO", "INFO", "INFO", "WARN", "ERROR"]
MESSAGES = {
    "INFO": ["Request completed successfully", "Cache hit for session lookup", "Health check passed"],
    "WARN": ["Connection pool at 85% capacity", "Slow query detected (1.8s)", "Retrying upstream call"],
    "ERROR": ["Timeout connecting to payments-db after 5000ms", "NullPointerException in OrderMapper.map",
              "Upstream returned 503 Service Unavailable"],
}


def make_logs(rng: random.Random) -> list:
    """100 application log entries."""
    start = datetime(2026, 10, 19, 9, 0, 0)
    logs = []
    for i in range(100):
        level = rng.choice(LEVELS)
        logs.append({
            "timestamp": (start + timedelta(seconds=i * 17)).isoformat() + "Z",
            "level": level,
            "service": rng.choice(SERVICES),
            "message": rng.choice(MESSAGES[level]),
            "trace_id": f"{rng.getrandbits(64):016x}",
            "host": f"ip-10-0-{rng.randint(1, 20)}-{rng.randint(1, 250)}",
            "latency_ms": rng.randint(5, 4000),
            "http_status": rng.choice([200, 200, 200, 404, 500, 503]),
        })
    return logs


def make_issues(rng: random.Random) -> list:
    """50 GitHub-style issues."""
    titles = ["Checkout fails with 503 under load", "Auth token refresh loops", "Slow search queries",
              "Payment retry duplicates charges", "Inventory count drifts", "Flaky integration test"]
    labels = ["bug", "incident", "performance", "tech-debt", "p1", "p2"]
    issues = []
    for n in range(1, 51):
        issues.append({
            "number": 1000 + n,
            "title": f"{rng.choice(titles)} (#{n})",
            "state": rng.choice(["open", "open", "closed"]),
            "labels": rng.sample(labels, 2),
            "author": f"dev{rng.randint(1, 15)}",
            "assignee": f"dev{rng.randint(1, 15)}",
            "created_at": f"2026-10-{rng.randint(1, 19):02d}T{rng.randint(0, 23):02d}:00:00Z",
            "comments": rng.randint(0, 30),
            "body": "Steps to reproduce: deploy the latest build, send traffic to the affected "
                    "endpoint, and observe errors in the dashboard. Expected normal behavior. " * 2,
        })
    return issues


def make_search_results(rng: random.Random) -> dict:
    """60 runbook / docs search results."""
    topics = ["database timeout", "503 errors", "connection pool", "rollback procedure", "cache invalidation"]
    results = []
    for i in range(60):
        topic = rng.choice(topics)
        results.append({
            "id": f"doc-{i:03d}",
            "title": f"Runbook: handling {topic}",
            "url": f"https://wiki.example.com/runbooks/{topic.replace(' ', '-')}-{i}",
            "score": round(rng.uniform(0.3, 0.99), 3),
            "snippet": f"When you see {topic}, first check the dashboards, then inspect recent deploys, "
                       "then escalate to the on-call engineer if the error rate stays above 5%. " * 2,
            "last_updated": f"2026-0{rng.randint(1, 9)}-{rng.randint(10, 28)}",
        })
    return {"query": "production incident runbooks", "total": len(results), "results": results}


def main() -> None:
    rng = random.Random(42)
    DATA_DIR.mkdir(exist_ok=True)
    files = {"logs.json": make_logs(rng), "issues.json": make_issues(rng),
             "search_results.json": make_search_results(rng)}
    for name, payload in files.items():
        (DATA_DIR / name).write_text(json.dumps(payload, indent=2))
        print(f"wrote data/{name}")


if __name__ == "__main__":
    main()
