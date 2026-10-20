I'm building a hackathon prototype called "TokenGate" — an org-level LLM token
compression gateway. It routes AI agent traffic through Headroom
(https://github.com/headroomlabs-ai/headroom) via LiteLLM, then measures and
visualizes token + dollar savings with compression ON vs OFF.

TECH STACK (do not deviate):
- Python 3.13 (required — LiteLLM won't install on 3.14, and dollar pricing needs LiteLLM)
- headroom-ai[all], litellm, google-adk, streamlit
- Keep dependencies minimal beyond these.

DESIGN PRINCIPLES:
- Simple, readable code a junior dev can follow. Small files, clear names,
  docstrings on every module. No clever abstractions, no async unless required.
- Everything configurable from ONE file: config.yaml (model name, API keys via
  env vars, headroom on/off toggle, proxy port, number of benchmark runs,
  org extrapolation defaults like devs count and requests/day).
- Each phase must run and be testable on its own before we move to the next.
  After finishing a phase, STOP, show me how to run/verify it, and wait for my
  confirmation before starting the next phase.

BUILD IN THESE PHASES:

Phase 1 — Setup & baseline
- Project scaffold: config.yaml, requirements.txt, README.md, src/ layout.
- A minimal script that makes one LiteLLM completion call using the model from
  config.yaml and prints input/output tokens and cost (litellm.completion_cost).
- A check script that verifies headroom is installed (headroom doctor) and can
  start its proxy.

Phase 2 — Demo agent with token-heavy tools
- A small Google ADK agent ("DevOps Triage Agent") using LiteLLM as the model
  layer, with 2-3 mock tools that return LARGE realistic JSON payloads
  (e.g., 100 log entries, a list of 50 GitHub-style issues, API search results).
  Mock data lives in a data/ folder as JSON files — no external services needed.
- Running the agent on a sample question should work end-to-end and print
  total tokens used.

Phase 3 — Headroom integration with a toggle
- Two integration modes, selected in config.yaml:
  (a) callback mode: litellm.callbacks = [HeadroomCallback()]
  (b) proxy mode: start headroom proxy and point LiteLLM's api_base at it
- A single boolean "compression_enabled" in config.yaml flips it on/off.
  No code changes needed to switch — config only.

Phase 4 — Benchmark harness
- A runner that executes the SAME fixed list of 5-8 agent tasks (defined in a
  tasks.yaml) twice: once with compression off, once with it on.
- For every LLM call, record input tokens, output tokens, and cost from
  LiteLLM's usage/cost APIs. Aggregate per task and per run.
- Save results to results/run_<timestamp>.json with: tokens before/after,
  % compression, $ before/after, $ saved, and the agent's final answers from
  both runs (so we can show answers are equivalent).
- Also compute a monthly org extrapolation: savings_per_request × devs ×
  requests_per_day × 22, using values from config.yaml.

Phase 5 — Streamlit dashboard
- Reads the latest results JSON. Shows: big headline "$ saved" metric,
  per-task bar chart of tokens with vs without compression, compression %
  summary, cost comparison, side-by-side answers per task, and sliders for
  devs/requests-per-day that recompute the monthly extrapolation live.
- Clean and demo-ready but simple — no custom CSS frameworks.

Phase 6 — Demo polish
- A single demo.sh (or make targets) to: run baseline task, run compressed
  task, run full benchmark, launch dashboard.
- Update README.md with setup steps, architecture diagram (ASCII is fine),
  and a 3-minute demo script narrative.

Start with Phase 1 now.