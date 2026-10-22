"""Phase 4: run the same tasks with compression OFF then ON and save a comparison.

Run from the repo root:  python -m src.benchmark
Output: results/run_<timestamp>.json
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

from src.agent import run_agent
from src.compression import compression_session
from src.config import load_config

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"


def load_tasks() -> list:
    with open(ROOT / "tasks.yaml") as f:
        return yaml.safe_load(f)["tasks"]


def run_mode(tasks: list, runs: int, compression_enabled: bool) -> dict:
    """Run every task `runs` times in one mode. Returns {task_id: averaged stats + answer}."""
    results = {}
    with compression_session(enabled=compression_enabled) as model:
        for number, task in enumerate(tasks, start=1):
            print(f"  [{number}/{len(tasks)}] {task['id']}: asking the agent ...", flush=True)
            started = time.time()
            attempts = [run_agent(task["question"], model) for _ in range(runs)]
            results[task["id"]] = {
                "input_tokens": sum(a["input_tokens"] for a in attempts) / runs,
                "output_tokens": sum(a["output_tokens"] for a in attempts) / runs,
                "cost": sum(a["cost"] for a in attempts) / runs,
                "llm_calls": sum(a["llm_calls"] for a in attempts) / runs,
                "answer": attempts[0]["answer"],  # first run's answer, for side-by-side display
            }
            r = results[task["id"]]
            print(
                f"        done in {time.time() - started:.0f}s: {r['llm_calls']:.0f} LLM calls, "
                f"{r['input_tokens']:,.0f} input + {r['output_tokens']:,.0f} output tokens, ${r['cost']:.4f}",
                flush=True,
            )
    return results


def total(mode_results: dict, key: str) -> float:
    return sum(r[key] for r in mode_results.values())


def percent_saved(before: float, after: float) -> float:
    return round(100 * (before - after) / before, 1) if before else 0.0


def extrapolate(cost_off: float, cost_on: float, task_count: int, org: dict) -> dict:
    """Monthly savings = savings_per_request x devs x requests_per_day x working days."""
    savings_per_request = (cost_off - cost_on) / task_count
    requests_per_month = org["devs"] * org["requests_per_day"] * org["working_days_per_month"]
    return {
        "savings_per_request": savings_per_request,
        "devs": org["devs"],
        "requests_per_day": org["requests_per_day"],
        "working_days_per_month": org["working_days_per_month"],
        "monthly_savings": savings_per_request * requests_per_month,
    }


def build_report(tasks: list, off: dict, on: dict, config: dict) -> dict:
    """Combine the two runs into the results structure the dashboard reads."""
    per_task = {}
    for task in tasks:
        tid = task["id"]
        per_task[tid] = {
            "question": task["question"],
            "tokens_before": off[tid]["input_tokens"] + off[tid]["output_tokens"],
            "tokens_after": on[tid]["input_tokens"] + on[tid]["output_tokens"],
            "input_tokens_before": off[tid]["input_tokens"],
            "input_tokens_after": on[tid]["input_tokens"],
            "cost_before": off[tid]["cost"],
            "cost_after": on[tid]["cost"],
            "answer_before": off[tid]["answer"],
            "answer_after": on[tid]["answer"],
        }
        per_task[tid]["compression_pct"] = percent_saved(
            per_task[tid]["tokens_before"], per_task[tid]["tokens_after"]
        )

    tokens_before = sum(t["tokens_before"] for t in per_task.values())
    tokens_after = sum(t["tokens_after"] for t in per_task.values())
    cost_before = total(off, "cost")
    cost_after = total(on, "cost")

    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "model": config["llm"]["model"],
        "headroom_mode": config["headroom"]["mode"],
        "runs_per_task": config["benchmark"]["runs"],
        "totals": {
            "tokens_before": tokens_before,
            "tokens_after": tokens_after,
            "compression_pct": percent_saved(tokens_before, tokens_after),
            "cost_before": cost_before,
            "cost_after": cost_after,
            "cost_saved": cost_before - cost_after,
        },
        "tasks": per_task,
        "extrapolation": extrapolate(cost_before, cost_after, len(tasks), config["org"]),
    }


def main() -> int:
    config = load_config()
    if not os.environ.get(config["llm"]["api_key_env"]):
        print(f"Missing API key: set the {config['llm']['api_key_env']} environment variable.")
        return 1

    tasks = load_tasks()
    runs = config["benchmark"]["runs"]
    print(f"Token Gate benchmark: {len(tasks)} tasks x {runs} run(s) per mode, model {config['llm']['model']}")
    print("Each task is asked twice: first with compression OFF (baseline), then ON "
          f"(Headroom, {config['headroom']['mode']} mode). Same questions, same tools.\n")

    print("Step 1/3  Baseline: compression OFF - the full tool output goes to the model")
    off = run_mode(tasks, runs, compression_enabled=False)
    print("\nStep 2/3  Compressed: compression ON - Headroom shrinks the tool output first")
    on = run_mode(tasks, runs, compression_enabled=True)

    print("\nStep 3/3  Comparing both runs and extrapolating to the org ...")
    report = build_report(tasks, off, on, config)

    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / f"run_{datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(report, indent=2))

    t, e = report["totals"], report["extrapolation"]
    print(f"\nResults:\nTokens:  {t['tokens_before']:.0f} -> {t['tokens_after']:.0f}  ({t['compression_pct']}% fewer)")
    print(f"Cost:    ${t['cost_before']:.4f} -> ${t['cost_after']:.4f}  (saved ${t['cost_saved']:.4f})")
    print(f"Monthly org savings ({e['devs']} devs x {e['requests_per_day']} req/day): ${e['monthly_savings']:,.2f}")
    print(f"Saved: {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
