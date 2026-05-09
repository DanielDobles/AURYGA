from __future__ import annotations

import os
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import Callable

import paramiko
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn


console = Console()


class RemoteCommandError(Exception):
    def __init__(self, cmd: str, exit_code: int, stderr: str):
        self.cmd = cmd
        self.exit_code = exit_code
        self.stderr = stderr
        super().__init__(f"[exit {exit_code}] {cmd}\n{stderr}")


class DropletController:
    REMOTE_BASE = PurePosixPath("/root/arcaios_run")
    SC_EXTENSIONS = PurePosixPath("/root/.local/share/SuperCollider/Extensions")

    def __init__(self, host: str, key_path: str, user: str = "root", port: int = 22):
        self._host = host
        self._key_path = Path(key_path).expanduser().resolve()
        self._user = user
        self._port = port
        self._client: paramiko.SSHClient | None = None
        self._sftp: paramiko.SFTPClient | None = None

    def connect(self) -> None:
        console.print(f"[bold yellow]SSH[/bold yellow] → {self._user}@{self._host}:{self._port}")
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._client.connect(
            hostname=self._host,
            port=self._port,
            username=self._user,
            key_filename=str(self._key_path),
            timeout=30,
        )
        self._sftp = self._client.open_sftp()
        console.print("[bold green]SSH connected[/bold green]")

    def _exec(self, cmd: str, timeout: int = 600, tips: list[str] | None = None) -> str:
        import time
        assert self._client is not None, "Call connect() first"
        
        # Prevent TCP window buffer deadlock by redirecting all output to a file
        safe_cmd = f"({cmd}) > /tmp/arcaios_cmd.log 2>&1"
        _, stdout, _ = self._client.exec_command(safe_cmd, timeout=timeout)
        
        if tips:
            status_text = tips[0]
            with console.status(f"[bold cyan]{status_text}[/bold cyan]", spinner="bouncingBar") as status:
                start_time = time.time()
                tip_idx = 0
                while not stdout.channel.exit_status_ready():
                    time.sleep(1)
                    elapsed = int(time.time() - start_time)
                    if elapsed % 4 == 0:
                        tip_idx = (tip_idx + 1) % len(tips)
                        status.update(f"[bold cyan]{tips[tip_idx]}[/bold cyan] [dim]({elapsed}s)[/dim]")
        else:
            with console.status(f"[dim]Executing: {cmd[:40]}...[/dim]", spinner="dots"):
                while not stdout.channel.exit_status_ready():
                    time.sleep(0.5)

        exit_code = stdout.channel.recv_exit_status()
        
        # Retrieve the buffered output
        _, cat_out, _ = self._client.exec_command("cat /tmp/arcaios_cmd.log")
        out = cat_out.read().decode("utf-8", errors="replace")
        
        if exit_code != 0:
            raise RemoteCommandError(cmd, exit_code, out)
        return out

    def _mkdir_remote(self, remote_path: PurePosixPath) -> None:
        assert self._sftp is not None
        try:
            self._sftp.stat(str(remote_path))
        except FileNotFoundError:
            self._mkdir_remote(remote_path.parent)
            self._sftp.mkdir(str(remote_path))

    def clean_remote_cache(self) -> None:
        assert self._sftp is not None
        console.print("[dim]Cleaning cache and residual files on Droplet...[/dim]")
        # Borrar el directorio de trabajo y vaciar logs de docker para evitar saturación de disco
        self._exec("rm -rf /root/arcaios_run/* 2>/dev/null || true")
        self._exec("truncate -s 0 $(docker inspect --format='{{.LogPath}}' vllm-coder vllm-reasoning 2>/dev/null) 2>/dev/null || true")

    def install_python_audio(self) -> None:
        console.print("[bold cyan]Installing Python Audio Ecosystem (Pedalboard, DawDreamer)...[/bold cyan]")
        # Install system dependencies for audio processing
        self._exec("apt-get update && apt-get install -y libasound2-dev libjack-jackd2-dev", tips=["Installing ALSA/JACK headers..."])
        self._exec("pip install pedalboard dawdreamer numpy scipy", tips=["Installing Python packages via pip..."])
        console.print("[green]Python Audio Ecosystem ready.[/green]")

    def upload_workspace(self, local_dir: Path) -> None:
        assert self._sftp is not None
        files = [f for f in local_dir.iterdir() if f.is_file()]
        if not files:
            raise FileNotFoundError(f"No files to upload in {local_dir}")

        self._mkdir_remote(self.REMOTE_BASE)
        self.clean_remote_cache()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Uploading workspace", total=len(files))
            for f in files:
                remote = self.REMOTE_BASE / f.name
                self._sftp.put(str(f), str(remote))
                progress.update(task, advance=1, description=f"Uploading {f.name}")

        console.print(f"[green]Uploaded {len(files)} files → {self.REMOTE_BASE}[/green]")

    def deploy_vault(self) -> None:
        console.print("[bold cyan]Deploying DSP Vault to Droplet (One-Time Compilation)...[/bold cyan]")
        assert self._sftp is not None
        
        vault_dir = Path("auryga/vault")
        if not vault_dir.exists():
            return
            
        vault_files = [f for f in vault_dir.iterdir() if f.is_file()]
        
        self._mkdir_remote(self.REMOTE_BASE)
        
        for f in vault_files:
            remote = self.REMOTE_BASE / f.name
            self._sftp.put(str(f), str(remote))
            
        out = self._exec(f"ls {self.REMOTE_BASE}/Auryga*.dsp 2>/dev/null || echo NONE")
        if "NONE" in out:
            return

        dsp_files = [line.strip() for line in out.strip().splitlines() if line.strip().endswith(".dsp")]
        for dsp in dsp_files:
            # Skip empty files that might have been created by failed curls
            size_check = self._exec(f"wc -c < {dsp}")
            try:
                if int(size_check.strip()) < 10:
                    continue
            except:
                pass
            
            name = PurePosixPath(dsp).stem
            # Check if already installed
            ext_check = self._exec(f"ls /root/.local/share/SuperCollider/Extensions/{name}.so 2>/dev/null || echo MISSING")
            if "MISSING" not in ext_check:
                console.print(f"  [dim]✓ {name}.so already installed in SuperCollider Extensions.[/dim]")
                continue
                
            tips = [
                f"Compiling Vault Engine: {name}.dsp...",
                f"Translating Faust architecture to LLVM...",
                f"Generating UGen class '{name}' for SuperCollider..."
            ]
            self._exec(f"cd {self.REMOTE_BASE} && faust2supercollider {dsp}", timeout=300, tips=tips)
            console.print(f"  [green]✓ {name}.dsp compiled to UGen.[/green]")
            
        # Move to extensions
        self._exec("mkdir -p /root/.local/share/SuperCollider/Extensions")
        self._exec(f"mv {self.REMOTE_BASE}/*.so {self.REMOTE_BASE}/*.sc /root/.local/share/SuperCollider/Extensions/ 2>/dev/null || true")
        console.print("[green]Vault deployment complete.[/green]")


    def render_python(self, script_name: str) -> None:
        console.print(f"[bold cyan]Executing Python Render: {script_name}[/bold cyan]")
        tips = [
            f"Loading {script_name} into Python interpreter...",
            "Initializing DawDreamer Render Engine...",
            "Applying Pedalboard effects chain...",
            "Writing WAV buffer to disk..."
        ]
        self._exec(f"cd {self.REMOTE_BASE} && python3 {script_name}", timeout=600, tips=tips)
        console.print(f"  [green]✓ {script_name} completed.[/green]")

    def render_nrt(self) -> None:
        console.print("[bold cyan]Starting Offline Rendering Engine (NRT)...[/bold cyan]")
        tips = [
            "Instantiating SuperCollider Non-Realtime server (sclang)...",
            "Loading Faust plugins into memory bus...",
            "Executing musical matrix and OSC events (Score)...",
            "Applying Sidechain algorithms on master...",
            "Rendering audio spectrum to multichannel WAV...",
            "Calculating spatialization (Reverb/Delay)...",
            "Synthesizing oscillators... keep connection open..."
        ]
        self._exec(
            f"cd {self.REMOTE_BASE} && xvfb-run --auto-servernum sclang master.scd",
            timeout=1800,
            tips=tips
        )
        console.print("[green]✓ NRT audio rendered.[/green]")

    def package_output(self) -> None:
        tips = [
            "Compressing WAV audio files...",
            "Preparing zip package for secure download...",
            "Aligning PCM headers of stems..."
        ]
        self._exec(
            f"cd {self.REMOTE_BASE} && zip -r output.zip *.wav",
            timeout=120,
            tips=tips
        )

    def download_results(self, local_dir: Path) -> None:
        assert self._sftp is not None
        local_dir.mkdir(parents=True, exist_ok=True)
        remote_zip = self.REMOTE_BASE / "output.zip"
        local_zip = local_dir / "output.zip"

        console.print(f"[bold cyan]Downloading {remote_zip}...[/bold cyan]")
        self._sftp.get(str(remote_zip), str(local_zip))

        with zipfile.ZipFile(local_zip, "r") as zf:
            zf.extractall(local_dir)

        local_zip.unlink()
        wav_files = list(local_dir.glob("*.wav"))
        console.print(f"[green]Downloaded and extracted {len(wav_files)} WAV files → {local_dir}[/green]")

    def run_pipeline(self, workspace: Path, results: Path) -> None:
        try:
            self.connect()
            self.upload_workspace(workspace)
            self.compile_faust()
            self.install_ugens()
            self.render_nrt()
            self.package_output()
            self.download_results(results)
        finally:
            self.close()

    def close(self) -> None:
        if self._sftp:
            self._sftp.close()
            self._sftp = None
        if self._client:
            self._client.close()
            self._client = None
        console.print("[dim]SSH connection closed[/dim]")

    def abort_all(self) -> None:
        try:
            self.connect()
            self._exec("pkill -9 faust2supercollider || true")
            self._exec("pkill -9 sclang || true")
            self._exec("pkill -9 xvfb-run || true")
            self._exec("pkill -9 zip || true")
        except Exception:
            pass
        finally:
            self.close()
