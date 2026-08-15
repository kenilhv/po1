"""PO1 — LLM configuration.

Every CrewAI agent in this system thinks on an open-weight model served by
Pioneer (Fastino Labs). Pioneer exposes an OpenAI-compatible endpoint, so it
drops in as the provider for the whole crew rather than sitting off to one
side as a single fine-tuned model.

Two tiers, matching how a real AP team allocates attention:
  cheap      — high-volume mechanical work (parsing, matching, coding)
  expensive  — judgment calls (fraud, exception classification, severity)

The fraud agent can additionally be pointed at a model fine-tuned on real
human labels collected through Terac during the hackathon; set
PIONEER_FRAUD_MODEL_ID once that training job deploys.
"""

from __future__ import annotations

import os

from crewai import LLM

PIONEER_BASE_URL = os.getenv("PIONEER_BASE_URL", "https://api.pioneer.ai") + "/v1"

# Open-weight models available for training and inference on Pioneer.
CHEAP_MODEL = os.getenv("CHEAP_MODEL", "Qwen/Qwen3-4B-Instruct-2507")
EXPENSIVE_MODEL = os.getenv("EXPENSIVE_MODEL", "Qwen/Qwen3-8B")

# Set after the Terac-labelled fine-tune deploys; overrides the fraud agent only.
FRAUD_MODEL_ID = os.getenv("PIONEER_FRAUD_MODEL_ID", "")


def _api_key() -> str:
    return os.getenv("PIONEER_API_KEY", "")


def model_name(*, expensive: bool = False, agent_id: str | None = None) -> str:
    if agent_id == "fraud_signal" and FRAUD_MODEL_ID:
        return FRAUD_MODEL_ID
    return EXPENSIVE_MODEL if expensive else CHEAP_MODEL


def get_llm(*, expensive: bool = False, agent_id: str | None = None) -> LLM:
    """Build a CrewAI LLM bound to Pioneer's OpenAI-compatible endpoint."""
    model = model_name(expensive=expensive, agent_id=agent_id)
    # LiteLLM (inside CrewAI) needs the openai/ prefix to route a custom base_url.
    return LLM(
        model=f"openai/{model}",
        api_key=_api_key(),
        base_url=PIONEER_BASE_URL,
        temperature=0.1,  # AP decisions should be reproducible, not creative
    )


def is_configured() -> bool:
    return bool(_api_key())
