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
        pkey = paramiko.RSAKey.from_private_key_file(str(self._key_path))
        self._client.connect(
            hostname=self._host,
            port=self._port,
            username=self._user,
            pkey=pkey,
            timeout=30,
        )
        self._sftp = self._client.open_sftp()
        console.print("[bold green]SSH connected[/bold green]")

    def _exec(self, cmd: str, timeout: int = 600) -> str:
        assert self._client is not None, "Call connect() first"
        console.print(f"  [dim]$ {cmd}[/dim]")
        _, stdout, stderr = self._client.exec_command(cmd, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        if exit_code != 0:
            raise RemoteCommandError(cmd, exit_code, err)
        if out.strip():
            for line in out.strip().splitlines()[:20]:
                console.print(f"    [dim]{line}[/dim]")
        return out

    def _mkdir_remote(self, remote_path: PurePosixPath) -> None:
        assert self._sftp is not None
        try:
            self._sftp.stat(str(remote_path))
        except FileNotFoundError:
            self._mkdir_remote(remote_path.parent)
            self._sftp.mkdir(str(remote_path))

    def upload_workspace(self, local_dir: Path) -> None:
        assert self._sftp is not None
        files = [f for f in local_dir.iterdir() if f.is_file()]
        if not files:
            raise FileNotFoundError(f"No files to upload in {local_dir}")

        self._mkdir_remote(self.REMOTE_BASE)

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

    def compile_faust(self) -> None:
        console.print("[bold cyan]Compiling Faust DSP files...[/bold cyan]")
        out = self._exec(f"ls {self.REMOTE_BASE}/*.dsp 2>/dev/null || echo NONE")
        if "NONE" in out:
            console.print("[yellow]No .dsp files found — skipping Faust compilation[/yellow]")
            return

        dsp_files = [line.strip() for line in out.strip().splitlines() if line.strip().endswith(".dsp")]
        for dsp in dsp_files:
            name = PurePosixPath(dsp).stem
            console.print(f"  [cyan]Compiling {name}.dsp[/cyan]")
            self._exec(
                f"cd {self.REMOTE_BASE} && faust2supercollider {dsp}",
                timeout=300,
            )

    def install_ugens(self) -> None:
        console.print("[bold cyan]Installing UGens to SC Extensions...[/bold cyan]")
        self._mkdir_remote(self.SC_EXTENSIONS)
        self._exec(
            f"find {self.REMOTE_BASE} -name '*.so' -exec cp {{}} {self.SC_EXTENSIONS}/ \\;"
        )
        self._exec(
            f"find {self.REMOTE_BASE} -name '*.sc' -not -name '*.scd' -exec cp {{}} {self.SC_EXTENSIONS}/ \\;"
        )
        console.print("[green]UGens installed[/green]")

    def render_nrt(self) -> None:
        console.print("[bold cyan]Rendering NRT via sclang...[/bold cyan]")
        self._exec(
            f"cd {self.REMOTE_BASE} && xvfb-run --auto-servernum sclang master.scd",
            timeout=1800,
        )
        console.print("[green]NRT render complete[/green]")

    def package_output(self) -> None:
        console.print("[bold cyan]Packaging WAV output...[/bold cyan]")
        self._exec(
            f"cd {self.REMOTE_BASE} && zip -r output.zip *.wav",
            timeout=120,
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
