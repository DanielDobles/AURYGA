from __future__ import annotations

import json
from pathlib import Path
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from auryga.sanitizer import Sanitizer

WORKSPACE = Path("./workspace")


class FileWriteInput(BaseModel):
    filename: str = Field(description="Name of the file to write (e.g. kick.dsp, seq_kick.scd)")
    content: str = Field(description="Full raw content of the file")


class FileWriterTool(BaseTool):
    name: str = "write_file"
    description: str = (
        "Write sanitized content to a file inside the ./workspace/ directory. "
        "Use this for every .dsp, .scd, or .json file you produce. "
        "The content will be automatically stripped of markdown fences and conversational text."
    )
    args_schema: Type[BaseModel] = FileWriteInput

    def _run(self, filename: str, content: str) -> str:
        WORKSPACE.mkdir(exist_ok=True)
        clean = Sanitizer.clean(content)
        target = WORKSPACE / filename
        target.write_text(clean, encoding="utf-8")
        return f"OK — {len(clean)} bytes → {target}"


class FileReadInput(BaseModel):
    filename: str = Field(description="Name of the file to read from ./workspace/")


class FileReaderTool(BaseTool):
    name: str = "read_file"
    description: str = (
        "Read the contents of a file from the ./workspace/ directory. "
        "Use this to inspect .dsp, .scd, or .json files produced by previous agents."
    )
    args_schema: Type[BaseModel] = FileReadInput

    def _run(self, filename: str) -> str:
        target = WORKSPACE / filename
        if not target.exists():
            return f"ERROR — file not found: {target}"
        return target.read_text(encoding="utf-8")


class ListWorkspaceInput(BaseModel):
    pass


class ListWorkspaceTool(BaseTool):
    name: str = "list_workspace"
    description: str = "List all files currently in the ./workspace/ directory."
    args_schema: Type[BaseModel] = ListWorkspaceInput

    def _run(self, **kwargs) -> str:
        if not WORKSPACE.exists():
            return "workspace/ does not exist yet"
        files = sorted(WORKSPACE.iterdir())
        if not files:
            return "workspace/ is empty"
        return "\n".join(f.name for f in files)
