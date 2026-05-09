from __future__ import annotations

import re


class Sanitizer:
    """Strip markdown fences, conversational preamble, and trailing chatter from LLM output.

    Designed to produce raw Faust (.dsp) and SuperCollider (.scd) source
    that compiles without leftover markdown artefacts.
    """

    _FENCE_RE = re.compile(r"```[\w]*\n?", re.MULTILINE)

    _CONVERSATIONAL_RE = re.compile(
        r"^("
        r"Here(?:'s| is).*?:|"
        r"Sure.*?:|"
        r"Certainly.*?:|"
        r"Of course.*?:|"
        r"Below is.*?:|"
        r"I'll.*?:|"
        r"Let me.*?:|"
        r"This (?:code|file|script).*?:"
        r").*$",
        re.MULTILINE | re.IGNORECASE,
    )

    _TRAILING_NOTE_RE = re.compile(
        r"\n(?:Note:|Explanation:|---|\*\*Note).*",
        re.DOTALL | re.IGNORECASE,
    )

    @classmethod
    def clean(cls, raw: str) -> str:
        text = cls._FENCE_RE.sub("", raw)
        text = cls._CONVERSATIONAL_RE.sub("", text)
        text = cls._TRAILING_NOTE_RE.sub("", text)
        lines = [ln for ln in text.splitlines() if ln.strip()]
        return "\n".join(lines) + "\n"
