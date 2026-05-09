import sys
import time
import requests
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.prompt import Prompt
from rich.table import Table
from rich.align import Align

from auryga.config import Settings, build_coder_llm, build_reasoning_llm, build_audio_llm
from auryga.crew.crew import build_crew
from auryga.remote.remote_exec import DropletController

console = Console()

def draw_banner():
    banner = """
[bold white]  █████╗ ██╗   ██╗██████╗ ██╗   ██╗ ██████╗  █████╗ [/bold white]
[bold white] ██╔══██╗██║   ██║██╔══██╗╚██╗ ██╔╝██╔════╝ ██╔══██╗[/bold white]
[bold cyan] ███████║██║   ██║██████╔╝ ╚████╔╝ ██║  ███╗███████║[/bold cyan]
[bold magenta] ███████║██║   ██║██████╔╝ ╚████╔╝ ██║  ███╗███████║[/bold magenta]
[bold yellow] ██╔══██║██║   ██║██╔══██╗  ╚██╔╝  ██║   ██║██╔══██║[/bold yellow]
[bold white] ██║  ██║╚██████╔╝██║  ██║   ██║   ╚██████╔╝██║  ██║[/bold white]
[bold white] ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝[/bold white]

[bold white]                     D S P[/bold white]
    """
    console.print(Align.center(banner))

def deploy_gpus(settings: Settings):
    console.print("\n[bold cyan]▶ PHASE 1:[/bold cyan] [white]Initializing GPU Swarm on Droplet...[/white]")
    controller = DropletController(
        host=settings.DROPLET_IP,
        key_path=str(settings.ssh_key_resolved),
    )
    
    with Progress(
        SpinnerColumn("dots2", style="cyan"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40, style="magenta", complete_style="green"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task1 = progress.add_task("[yellow]Connecting via SSH...", total=100)
        
        try:
            controller.connect()
            progress.update(task1, advance=30, description="[yellow]Restarting Docker containers...")
            
            # Lanzamos el deploy en background para no bloquear si queremos ver progreso
            controller._exec("docker rm -f vllm-coder vllm-reasoning 2>/dev/null || true")
            controller._exec("nohup bash /root/deploy_models.sh > /root/deploy.log 2>&1 &")
            
            progress.update(task1, advance=30, description="[yellow]Compiling ROCm tensors (Wait ~2 min)...")
            
            tips = [
                "Reserving 80GB VRAM on MI300X accelerators...",
                "Injecting PyTorch graphs into PagedAttention cache...",
                "Quantizing KV Cache memory...",
                "Awaiting TCP signal from Coder model (Port 8000)...",
                "Booting Reasoning model Qwen3-32B...",
                "Compiling Triton kernels on AMD backend...",
                "Aligning 32 Billion parameter tensors..."
            ]
            
            start_time = time.time()
            tip_idx = 0
            
            # Polling Health Check
            ready = False
            while not ready:
                try:
                    r_reason = requests.get(f"{settings.VLLM_REASONING_BASE}/models", timeout=2)
                    r_coder = requests.get(f"{settings.VLLM_API_BASE}/models", timeout=2)
                    if r_reason.status_code == 200 and r_coder.status_code == 200:
                        ready = True
                        progress.update(task1, completed=100, description="[bold green]vLLM Engines Ready and Synchronized!")
                        break
                except Exception:
                    pass
                
                time.sleep(1)
                elapsed = int(time.time() - start_time)
                if elapsed % 4 == 0:
                    tip_idx = (tip_idx + 1) % len(tips)
                    progress.update(task1, description=f"[yellow]{tips[tip_idx]} [dim]({elapsed}s)[/dim]")
            
        finally:
            controller.close()

def orchestrate_agents(settings: Settings, user_prompt: str):
    console.print("\n[bold cyan]▶ PHASE 2:[/bold cyan] [white]CrewAI Agent Orchestration[/white]")
    
    # Preparar el workspace
    WORKSPACE = Path("./workspace")
    WORKSPACE.mkdir(exist_ok=True)
    for f in WORKSPACE.glob("*"):
        f.unlink()

    coder_llm = build_coder_llm(settings)
    reasoning_llm = build_reasoning_llm(settings)
    audio_llm = build_audio_llm(settings)

    crew = build_crew(coder_llm, reasoning_llm, audio_llm)
    
    console.print(Panel(f"[bold yellow]Creative Prompt:[/bold yellow] {user_prompt}", border_style="yellow"))
    console.print("[dim]Agents have started interacting. Observe live reasoning:[/dim]\n")
    
    import threading
    
    tips = [
        "Manager is decomposing the musical request...",
        "Theorist is calculating the MIDI matrix and scales...",
        "Sound Designer is writing functional Faust DSP blocks...",
        "QA Linter is checking for hallucinated syntax...",
        "Producer is writing SuperCollider NRT scores...",
        "Mix Engineer is routing sidechain compression...",
        "Allocating 32B parameters on the MI300X..."
    ]
    
    status = console.status("[bold magenta]Agents are waking up...[/bold magenta]", spinner="bouncingBar")
    status.start()
    
    def update_tips():
        idx = 0
        start_time = time.time()
        while status.status != "done":
            elapsed = int(time.time() - start_time)
            status.update(f"[bold magenta]{tips[idx]}[/bold magenta] [dim]({elapsed}s)[/dim]")
            idx = (idx + 1) % len(tips)
            time.sleep(4)

    t = threading.Thread(target=update_tips, daemon=True)
    t.start()
    
    try:
        # Run the crew (esto imprimirá verbosamente a la consola)
        crew.kickoff(inputs={"prompt": user_prompt})
    finally:
        status.status = "done"
        status.stop()

def sanitize_workspace():
    WORKSPACE = Path("./workspace")
    console.print("[dim]Running static Python linter on workspace...[/dim]")
    for scd in WORKSPACE.glob("*.scd"):
        content = scd.read_text(encoding="utf-8")
        if "0.exit" not in content:
            console.print(f"[yellow]Auto-fixing missing 0.exit; in {scd.name}[/yellow]")
            scd.write_text(content.rstrip() + "\n0.exit;\n", encoding="utf-8")
    for dsp in WORKSPACE.glob("*.dsp"):
        content = dsp.read_text(encoding="utf-8")
        if 'import("stdfaust.lib");' not in content:
            console.print(f"[yellow]Auto-fixing missing import in {dsp.name}[/yellow]")
            dsp.write_text('import("stdfaust.lib");\n' + content, encoding="utf-8")

def compile_and_download(settings: Settings):
    console.print("\n[bold cyan]▶ PHASE 3:[/bold cyan] [white]Audio Synthesis and Mastering[/white]")
    WORKSPACE = Path("./workspace")
    RESULTS = Path("./results")
    RESULTS.mkdir(exist_ok=True)
    
    sanitize_workspace()
    
    controller = DropletController(
        host=settings.DROPLET_IP,
        key_path=str(settings.ssh_key_resolved),
    )
    
    try:
        controller.connect()
        controller.upload_workspace(WORKSPACE)
        
        # Render stems
        for stem_py in WORKSPACE.glob("seq_*.py"):
            controller.render_python(stem_py.name)
            
        # Render master
        controller.render_python("master.py")
        
        controller.package_output()
        controller.download_results(RESULTS)
    finally:
        controller.close()
        
    console.print(Panel("[bold green]ALL GENERATION SUCCESSFULLY COMPLETED.[/bold green]", border_style="green"))

def main():
    draw_banner()
    settings = Settings.load()
    
    if len(sys.argv) > 1:
        user_prompt = " ".join(sys.argv[1:])
    else:
        user_prompt = Prompt.ask("\n[bold cyan]Input:[/bold cyan] What type of Melodic Techno or Techno do you want to forge?\n[dim](e.g., Deep Afterlife style, Dark driving techno, Orchestral melodic)[/dim]\n[dim]>[/dim]")

    try:
        # Preguntamos si queremos saltar el deploy de gpus en caso de que ya estén vivas
        try:
            r = requests.get(f"{settings.VLLM_REASONING_BASE}/models", timeout=2)
            if r.status_code == 200:
                console.print("[dim]VLLM servers are already running. Skipping reboot...[/dim]")
            else:
                deploy_gpus(settings)
        except Exception:
            deploy_gpus(settings)
            
        # Compile the vault and install Python audio stack
        console.print("[dim]Checking Audio Ecosystem state...[/dim]")
        audio_ctrl = DropletController(settings.DROPLET_IP, str(settings.ssh_key_resolved))
        audio_ctrl.connect()
        audio_ctrl.install_python_audio() # Ensure pedalboard/dawdreamer
        audio_ctrl.deploy_vault()
        audio_ctrl.close()

        orchestrate_agents(settings, user_prompt)
        compile_and_download(settings)
        
    except KeyboardInterrupt:
        console.print("\n[bold red]Aborted by user (Ctrl+C).[/bold red]")
        console.print("[dim]Stopping residual processes on Droplet...[/dim]")
        try:
            abort_ctrl = DropletController(settings.DROPLET_IP, str(settings.ssh_key_resolved))
            abort_ctrl.abort_all()
        except Exception:
            pass
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Critical Error:[/bold red] {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Forzar encoding UTF-8 para evitar errores de simbolos en consola Windows
    sys.stdout.reconfigure(encoding='utf-8')
    main()
