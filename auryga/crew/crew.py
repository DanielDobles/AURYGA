from __future__ import annotations

from crewai import Crew, LLM, Process

from auryga.crew.agents import build_agents
from auryga.crew.tasks import build_tasks


def build_crew(coder_llm: LLM, reasoning_llm: LLM, audio_llm: LLM | None = None) -> Crew:
    agents = build_agents(coder_llm, reasoning_llm, audio_llm)
    tasks = build_tasks(agents)

    return Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )
