"""Phase 3: turns Headroom compression on/off based on config.yaml (no code changes needed).

headroom.compression_enabled: false -> plain LiteLLM calls (baseline)
headroom.mode: "callback"           -> HeadroomCallback compresses messages in-process
headroom.mode: "proxy"              -> we start `headroom proxy` and point LiteLLM's api_base at it

Usage:
    with compression_session() as model:    # model is a ready-to-use ADK LiteLlm
        ...build the agent with `model`...
"""

import socket
import subprocess
import time
from contextlib import contextmanager

import litellm
from google.adk.models.lite_llm import LiteLlm, LiteLLMClient

from src.config import load_config

PROXY_STARTUP_TIMEOUT_SECONDS = 30


class CompressingClient(LiteLLMClient):
    """LiteLLM client that runs the Headroom callback on messages before each call.

    LiteLLM only triggers callback pre-call hooks itself inside its own proxy server,
    so for plain SDK calls we invoke the hook here.
    """

    def __init__(self, callback):
        self.callback = callback

    async def acompletion(self, model, messages, tools, **kwargs):
        data = {"model": model, "messages": messages}
        data = await self.callback.async_pre_call_hook(data=data, call_type="acompletion")
        return await super().acompletion(model=model, messages=data["messages"], tools=tools, **kwargs)


def _port_is_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


@contextmanager
def _headroom_proxy(port: int):
    """Start `headroom proxy` for the duration of the block, then stop it."""
    if _port_is_open(port):
        raise RuntimeError(f"Port {port} is already in use. Change headroom.proxy_port in config.yaml.")
    proc = subprocess.Popen(
        ["headroom", "proxy", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + PROXY_STARTUP_TIMEOUT_SECONDS
        while not _port_is_open(port):
            if proc.poll() is not None or time.time() > deadline:
                raise RuntimeError("headroom proxy failed to start. Run `python -m src.check_headroom`.")
            time.sleep(0.5)
        yield
    finally:
        proc.terminate()
        proc.wait()


@contextmanager
def compression_session(enabled: bool | None = None):
    """Yield an ADK LiteLlm model set up according to config.yaml's headroom section.

    `enabled` overrides headroom.compression_enabled (the benchmark uses it to run both modes).
    """
    config = load_config()
    model_name = config["llm"]["model"]
    headroom = config["headroom"]

    if enabled is None:
        enabled = headroom["compression_enabled"]

    if not enabled:
        yield LiteLlm(model=model_name)
    elif headroom["mode"] == "callback":
        from headroom.integrations.litellm_callback import HeadroomCallback

        callback = HeadroomCallback()
        litellm.callbacks = [callback]
        yield LiteLlm(model=model_name, llm_client=CompressingClient(callback))
    elif headroom["mode"] == "proxy":
        port = headroom["proxy_port"]
        with _headroom_proxy(port):
            yield LiteLlm(model=model_name, api_base=f"http://127.0.0.1:{port}/v1")
    else:
        raise ValueError(f"Unknown headroom.mode '{headroom['mode']}' (use 'callback' or 'proxy').")
