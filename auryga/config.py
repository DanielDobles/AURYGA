from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
import os

from crewai import LLM


_REQUIRED = ("DROPLET_IP", "SSH_KEY_PATH", "VLLM_API_BASE", "VLLM_MODEL_NAME")


@dataclass(frozen=True, slots=True)
class Settings:
    DROPLET_IP: str
    SSH_KEY_PATH: str
    VLLM_API_BASE: str
    VLLM_MODEL_NAME: str
    VLLM_REASONING_BASE: str
    VLLM_REASONING_MODEL: str
    VLLM_AUDIO_BASE: str
    VLLM_AUDIO_MODEL: str

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv()
        missing = [k for k in _REQUIRED if not os.getenv(k)]
        if missing:
            from rich.console import Console
            Console(stderr=True).print(
                f"[bold red]ERROR:[/bold red] Variables faltantes en .env: {', '.join(missing)}"
            )
            sys.exit(1)
        return cls(
            DROPLET_IP=os.environ["DROPLET_IP"],
            SSH_KEY_PATH=os.environ["SSH_KEY_PATH"],
            VLLM_API_BASE=os.environ["VLLM_API_BASE"],
            VLLM_MODEL_NAME=os.environ["VLLM_MODEL_NAME"],
            VLLM_REASONING_BASE=os.getenv("VLLM_REASONING_BASE", os.environ["VLLM_API_BASE"]),
            VLLM_REASONING_MODEL=os.getenv("VLLM_REASONING_MODEL", os.environ["VLLM_MODEL_NAME"]),
            VLLM_AUDIO_BASE=os.getenv("VLLM_AUDIO_BASE", ""),
            VLLM_AUDIO_MODEL=os.getenv("VLLM_AUDIO_MODEL", ""),
        )

    @property
    def ssh_key_resolved(self) -> Path:
        return Path(self.SSH_KEY_PATH).expanduser().resolve()

    @property
    def has_audio_model(self) -> bool:
        return bool(self.VLLM_AUDIO_BASE and self.VLLM_AUDIO_MODEL)


def build_coder_llm(settings: Settings) -> LLM:
    return LLM(
        model=f"hosted_vllm/{settings.VLLM_MODEL_NAME}",
        base_url=settings.VLLM_API_BASE,
        api_key="not-needed",
    )


def build_reasoning_llm(settings: Settings) -> LLM:
    return LLM(
        model=f"hosted_vllm/{settings.VLLM_REASONING_MODEL}",
        base_url=settings.VLLM_REASONING_BASE,
        api_key="not-needed",
    )


def build_audio_llm(settings: Settings) -> LLM | None:
    if not settings.has_audio_model:
        return None
    return LLM(
        model=f"openai/{settings.VLLM_AUDIO_MODEL}",
        base_url=settings.VLLM_AUDIO_BASE,
        api_key="not-needed",
    )
