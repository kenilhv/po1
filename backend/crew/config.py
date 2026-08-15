from __future__ import annotations

import os

from crewai import LLM

# OpenAI-compatible providers: groq (default), openai, truefoundry (later)
PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()

PROFILES = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "cheap": "llama-3.1-8b-instant",
        "expensive": "llama-3.3-70b-versatile",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "cheap": "gpt-4o-mini",
        "expensive": "gpt-4o",
    },
    "truefoundry": {
        "base_url_env": "OPENAI_API_BASE",
        "api_key_env": "OPENAI_API_KEY",
        "cheap_env": "CHEAP_MODEL",
        "expensive_env": "EXPENSIVE_MODEL",
        "cheap": "gpt-4o-mini",
        "expensive": "gpt-4o",
    },
}


def get_llm(*, expensive: bool = False) -> LLM:
    profile = PROFILES.get(PROVIDER, PROFILES["groq"])

    if PROVIDER == "truefoundry":
        base_url = os.getenv(profile.get("base_url_env", "OPENAI_API_BASE"), "")
        api_key = os.getenv(profile["api_key_env"], "")
        model = os.getenv(
            profile["expensive_env" if expensive else "cheap_env"],
            profile["expensive" if expensive else "cheap"],
        )
    else:
        base_url = profile["base_url"]
        api_key = os.getenv(profile["api_key_env"], "")
        model = os.getenv(
            "EXPENSIVE_MODEL" if expensive else "CHEAP_MODEL",
            profile["expensive" if expensive else "cheap"],
        )

    return LLM(model=model, api_key=api_key, base_url=base_url)


def model_name(*, expensive: bool = False) -> str:
    profile = PROFILES.get(PROVIDER, PROFILES["groq"])
    if PROVIDER == "truefoundry":
        return os.getenv(
            profile["expensive_env" if expensive else "cheap_env"],
            profile["expensive" if expensive else "cheap"],
        )
    return os.getenv(
        "EXPENSIVE_MODEL" if expensive else "CHEAP_MODEL",
        profile["expensive" if expensive else "cheap"],
    )
