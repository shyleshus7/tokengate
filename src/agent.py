"""Phase 2: the DevOps Triage Agent (Google ADK + LiteLLM) and a runner that counts tokens.

Run from the repo root:  python -m src.agent [--compression on|off] ["your question"]
"""

import os
import sys

import litellm
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

from src.compression import compression_session
from src.config import load_config
from src.tools import get_recent_logs, list_github_issues, search_runbooks

DEFAULT_QUESTION = (
    "Checkout is failing in production. Check the recent logs, the open GitHub issues, "
    "and the runbooks, then tell me the most likely cause and what to do first."
)

INSTRUCTION = (
    "You are a DevOps triage assistant. Use your tools to gather evidence "
    "(logs, issues, runbooks), then answer concisely with the likely cause and next steps."
)


def build_agent(model) -> LlmAgent:
    """Create the agent around an ADK model (see compression_session)."""
    return LlmAgent(
        name="devops_triage_agent",
        model=model,
        instruction=INSTRUCTION,
        tools=[get_recent_logs, list_github_issues, search_runbooks],
    )


def run_agent(question: str, model) -> dict:
    """Run the agent once with an ADK model (from compression_session).

    Returns the final answer, token and cost totals, and one record per LLM call.
    """
    calls = []
    model_name = load_config()["llm"]["model"]

    def count_usage(callback_context, llm_response):
        """Runs after every LLM call; records tokens and dollar cost."""
        meta = llm_response.usage_metadata
        if meta:
            inp, out = meta.prompt_token_count or 0, meta.candidates_token_count or 0
            in_cost, out_cost = litellm.cost_per_token(model=model_name, prompt_tokens=inp, completion_tokens=out)
            calls.append({"input_tokens": inp, "output_tokens": out, "cost": in_cost + out_cost})
        return None

    agent = build_agent(model)
    agent.after_model_callback = count_usage

    runner = InMemoryRunner(agent=agent, app_name="tokengate")
    session = runner.session_service.create_session_sync(app_name="tokengate", user_id="demo")
    message = types.Content(role="user", parts=[types.Part(text=question)])

    answer = ""
    for event in runner.run(user_id="demo", session_id=session.id, new_message=message):
        if event.is_final_response() and event.content and event.content.parts:
            answer = event.content.parts[0].text or ""

    return {
        "answer": answer,
        "llm_calls": len(calls),
        "input_tokens": sum(c["input_tokens"] for c in calls),
        "output_tokens": sum(c["output_tokens"] for c in calls),
        "cost": sum(c["cost"] for c in calls),
        "calls": calls,
    }


def main() -> int:
    llm = load_config()["llm"]
    if not os.environ.get(llm["api_key_env"]):
        print(f"Missing API key: set the {llm['api_key_env']} environment variable.")
        return 1

    # Optional first argument "--compression on|off" overrides config.yaml for this run only.
    args = sys.argv[1:]
    enabled = None
    if len(args) >= 2 and args[0] == "--compression":
        enabled = args[1] == "on"
        args = args[2:]

    question = " ".join(args) or DEFAULT_QUESTION
    with compression_session(enabled=enabled) as model:  # default: config.yaml decides
        result = run_agent(question, model)

    headroom = load_config()["headroom"]
    if enabled is None:
        enabled = headroom["compression_enabled"]
    mode = headroom["mode"] if enabled else "off"
    print(f"Compression:   {mode}")
    print(f"Answer:\n{result['answer']}\n")
    print(f"LLM calls:     {result['llm_calls']}")
    print(f"Input tokens:  {result['input_tokens']}")
    print(f"Output tokens: {result['output_tokens']}")
    print(f"Total tokens:  {result['input_tokens'] + result['output_tokens']}")
    print(f"Cost (USD):    ${result['cost']:.6f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
