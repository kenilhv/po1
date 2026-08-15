from __future__ import annotations

from crewai import Agent

from crew.agents.registry import AgentSpec, get_agent
from crew.config import get_llm


def build_agent(spec_id: str) -> Agent:
    spec: AgentSpec = get_agent(spec_id)
    expensive = spec.model_tier == "expensive"
    return Agent(
        role=spec.name,
        goal=spec.description,
        backstory=f"InvoiceOS {spec.name} operating at tier {spec.tier}. Agent ID: {spec.id}.",
        llm=get_llm(expensive=expensive),
        verbose=True,
        allow_delegation=False,
    )
