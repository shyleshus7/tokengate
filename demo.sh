#!/usr/bin/env bash
# TokenGate demo launcher. Usage: ./demo.sh [baseline|compressed|benchmark|dashboard|all]
set -euo pipefail
cd "$(dirname "$0")"

# Use the project's venv so `python` is 3.13 and the `headroom` CLI is on PATH.
if [ ! -x .venv/bin/python ]; then
  echo "Missing .venv - see README.md 'Setup'." >&2
  exit 1
fi
source .venv/bin/activate

step="${1:-all}"

case "$step" in
  baseline)   python -m src.agent --compression off ;;
  compressed) python -m src.agent --compression on ;;
  benchmark)  python -m src.benchmark ;;
  dashboard)  streamlit run src/dashboard.py ;;
  all)
    echo "=== 1/4 Baseline (compression OFF) ==="; python -m src.agent --compression off
    echo; echo "=== 2/4 Compressed (compression ON) ==="; python -m src.agent --compression on
    echo; echo "=== 3/4 Full benchmark ==="; python -m src.benchmark
    echo; echo "=== 4/4 Dashboard ==="; streamlit run src/dashboard.py
    ;;
  *) echo "Usage: ./demo.sh [baseline|compressed|benchmark|dashboard|all]"; exit 1 ;;
esac
