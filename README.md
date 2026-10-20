# Token Gate - An Org-Wide LLM Compression Gateway

TokenGate routes AI agent traffic through [Headroom](https://github.com/headroomlabs-ai/headroom)
via LiteLLM, then measures the token and dollar savings with compression ON vs OFF.
A demo "DevOps Triage Agent" calls tools that return large JSON payloads (logs, issues,
runbooks) - exactly the kind of traffic Headroom compresses well.

## Setup

Requires **Python 3.13** (LiteLLM does not install on 3.14).

```bash
python3.13 -m venv .venv && source .venv/bin/activate   # or: uv venv --python 3.13 .venv
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...        # whichever env var config.yaml's llm.api_key_env names
```

Everything is configured in [config.yaml](config.yaml): model, API key env var, compression
on/off, Headroom mode (`callback` or `proxy`), proxy port, benchmark runs, and org defaults.

Sanity checks:

```bash
python -m src.baseline_call         # one LLM call: prints tokens + cost
python -m src.check_headroom        # headroom doctor + proxy start check
```

## Architecture

```
                        config.yaml (model, mode, toggle, org numbers)
                                      |
  tasks.yaml --> benchmark.py ------> agent.py (Google ADK "DevOps Triage Agent")
                    |  runs each          |  calls tools -> data/*.json (large payloads)
                    |  task OFF, then ON  v
                    |             compression.py
                    |        +------------+-------------+
                    |        | off        | callback    | proxy
                    |        v            v             v
                    |     LiteLLM      HeadroomCallback  headroom proxy (localhost)
                    |        |         compresses msgs        |
                    |        +------------+-------------+----+
                    |                     v
                    |                  LLM provider  --> usage + cost (litellm)
                    v
            results/run_<timestamp>.json --> dashboard.py (Streamlit)
```

## Commands

| Command | What it does |
| --- | --- |
| `./demo.sh baseline` | one triage question, compression OFF |
| `./demo.sh compressed` | same question, compression ON |
| `./demo.sh benchmark` | all tasks in `tasks.yaml`, OFF then ON, saves `results/run_*.json` |
| `./demo.sh dashboard` | Streamlit dashboard for the latest results |
| `./demo.sh all` | the four steps above in order |

Manual equivalents: `python -m src.agent [--compression on|off] ["question"]`,
`python -m src.benchmark`, `streamlit run src/dashboard.py`. Without `--compression`,
the agent follows `headroom.compression_enabled` in config.yaml. The benchmark always runs both.
`python -m src.make_mock_data` regenerates `data/*.json`.

## 3-minute demo script

**0:00 - The problem (20s).** "Our agents call tools that return huge JSON: 100 log lines,
50 issues, 60 search results. All of it is re-sent to the model on every step, and we pay
for every token. Multiply by every developer in the company."

**0:20 - Baseline (40s).** Run `./demo.sh baseline`. "This is a triage agent asking why
checkout is failing. Without compression it makes several LLM calls and uses N input tokens
at a cost of $X." Point at the token and cost lines.

**1:00 - Compressed (40s).** Run `./demo.sh compressed`. "Same question, same agent, same
code. The only change is one switch in config.yaml. Headroom compresses the tool output
before it reaches the model: input tokens drop to M, and the answer is still correct."

**1:40 - Benchmark and dashboard (50s).** Run `./demo.sh dashboard` (run
`./demo.sh benchmark` beforehand; it takes several minutes). Show the headline $ saved, the
per-task bar chart, and open one task's answers side by side. "Six different tasks, answers
are equivalent, tokens are down by P%."

**2:30 - The org view (30s).** Drag the sliders for developers and requests per day.
"At 50 developers and 40 requests a day, that is $Z saved per month, from a config change
and no changes to the agents themselves."
