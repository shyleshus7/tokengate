"""Phase 1 baseline: make one LiteLLM completion and print tokens and cost.

Run from the repo root:  python -m src.baseline_call
"""

import os
import sys

import litellm

from src.config import load_config

PROMPT = "In two sentences, explain what an LLM token is."


def main() -> int:
    llm = load_config()["llm"]

    if not os.environ.get(llm["api_key_env"]):
        print(f"Missing API key: set the {llm['api_key_env']} environment variable.")
        return 1

    response = litellm.completion(
        model=llm["model"],
        messages=[{"role": "user", "content": PROMPT}],
        max_tokens=llm["max_tokens"],
    )

    usage = response.usage
    cost = litellm.completion_cost(completion_response=response)

    print(f"Model:         {llm['model']}")
    print(f"Answer:        {response.choices[0].message.content}")
    print(f"Input tokens:  {usage.prompt_tokens}")
    print(f"Output tokens: {usage.completion_tokens}")
    print(f"Cost (USD):    ${cost:.6f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
