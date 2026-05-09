from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
import requests
import time

from auryga.config import Settings, build_coder_llm, build_reasoning_llm, build_audio_llm
from auryga.crew.crew import build_crew
from auryga.remote.remote_exec import DropletController

console = Console()

WORKSPACE = Path("./workspace")
RESULTS = Path("./results")


def banner() -> None:
    console.print(
        Panel.fit(
            "[bold magenta]█▀▀█ █▀▀█ █▀▀ █▀▀█ ▀█▀ █▀▀█ █▀▀\n"
            "█▄▄█ █▄▄▀ █   █▄▄█  █  █  █ ▀▀█\n"
            "▀  ▀ ▀ ▀▀ ▀▀▀ ▀  ▀ ▀▀▀ ▀▀▀▀ ▀▀▀\n"
            "      [bold cyan]F O R G E[/bold cyan][/bold magenta]",
            border_style="bright_magenta",
            title="[bold white]ARCAIOS[/bold white]",
            subtitle="[dim]Melodic Techno · STEM Pipeline · CLI[/dim]",
        )
    )


def run_agents(settings: Settings, user_prompt: str) -> None:
    console.print("\n[bold green]▶ Fase 1:[/bold green] Iniciando agentes CrewAI...\n")

    coder_llm = build_coder_llm(settings)
    reasoning_llm = build_reasoning_llm(settings)
    audio_llm = build_audio_llm(settings)

    model_table = Table(title="Modelos LLM", border_style="magenta")
    model_table.add_column("Rol", style="cyan")
    model_table.add_column("Modelo", style="white")
    model_table.add_column("Endpoint", style="dim")
    model_table.add_row("Código (Faust/SC)", settings.VLLM_MODEL_NAME, settings.VLLM_API_BASE)
    model_table.add_row("Razonamiento", settings.VLLM_REASONING_MODEL, settings.VLLM_REASONING_BASE)
    if settings.has_audio_model:
        model_table.add_row("Audio (Multimodal)", settings.VLLM_AUDIO_MODEL, settings.VLLM_AUDIO_BASE)
    else:
        model_table.add_row("Audio", "[dim]No configurado[/dim]", "—")
    console.print(model_table)

    crew = build_crew(coder_llm, reasoning_llm, audio_llm)
    result = crew.kickoff(inputs={"prompt": user_prompt})
    console.print("\n[bold green]✓ Fase 1 completa.[/bold green] Archivos generados en ./workspace/\n")

    if WORKSPACE.exists():
        table = Table(title="Archivos generados", border_style="green")
        table.add_column("Archivo", style="cyan")
        table.add_column("Tamaño", justify="right", style="white")
        for f in sorted(WORKSPACE.iterdir()):
            if f.is_file():
                table.add_row(f.name, f"{f.stat().st_size:,} bytes")
        console.print(table)


def run_remote(settings: Settings) -> None:
    console.print("\n[bold green]▶ Fase 2:[/bold green] Pipeline de ejecución remota...\n")
    controller = DropletController(
        host=settings.DROPLET_IP,
        key_path=str(settings.ssh_key_resolved),
    )
    controller.run_pipeline(workspace=WORKSPACE, results=RESULTS)
    console.print("\n[bold green]✓ Fase 2 completa.[/bold green]\n")


def summary() -> None:
    if not RESULTS.exists():
        console.print("[bold red]No results directory found.[/bold red]")
        return

    wav_files = sorted(RESULTS.glob("*.wav"))
    if not wav_files:
        console.print("[bold red]No WAV files found in results.[/bold red]")
        return

    table = Table(title="Stems y Master", border_style="cyan")
    table.add_column("Archivo", style="bold white")
    table.add_column("Tamaño", justify="right", style="green")
    for f in wav_files:
        size_mb = f.stat().st_size / (1024 * 1024)
        table.add_row(f.name, f"{size_mb:.1f} MB")
    console.print(table)

    console.print(
        Panel(
            f"[bold cyan]{RESULTS.resolve()}[/bold cyan]",
            title="[bold white]Stems disponibles en[/bold white]",
            border_style="bright_green",
        )
    )


def main() -> None:
    banner()

    settings = Settings.load()
    console.print(f"[dim]Droplet:[/dim] {settings.DROPLET_IP}")
    console.print(f"[dim]SSH Key:[/dim] {settings.ssh_key_resolved}\n")

    if len(sys.argv) > 1:
        user_prompt = " ".join(sys.argv[1:])
        console.print(f"\n[bold cyan]Estilo seleccionado:[/bold cyan] {user_prompt}")
    else:
        user_prompt = Prompt.ask("\n[bold cyan]¿Qué estilo de track quieres crear?[/bold cyan]\n[dim](Ej: Techno oscuro a 128 BPM con pads espaciales o Groove rítmico percusivo)[/dim]")

    with console.status("[bold yellow]Esperando a que los modelos en el Droplet estén online... (Esto puede tomar 1-2 minutos)[/bold yellow]") as status:
        ready = False
        while not ready:
            try:
                # Checar ambos endpoints
                r_reason = requests.get(f"{settings.VLLM_REASONING_BASE}/models", timeout=3)
                r_coder = requests.get(f"{settings.VLLM_API_BASE}/models", timeout=3)
                if r_reason.status_code == 200 and r_coder.status_code == 200:
                    ready = True
            except requests.exceptions.RequestException:
                time.sleep(5)
    
    console.print("[bold green]¡Modelos Online y listos![/bold green]\n")

    run_agents(settings, user_prompt)
    run_remote(settings)
    summary()

    console.print("\n[bold green]█ ARCAIOS FORGE — Misión completa.[/bold green]\n")


if __name__ == "__main__":
    main()
