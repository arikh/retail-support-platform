from dataclasses import dataclass
from functools import cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"

ACTIVE_VERSIONS = {
    "routing_system": "v1",
    "support_system": "v1",
    "support_status_guide": "v1",
    "analysis_system": "v1",
    "analysis_status_guide": "v1",
    "format_findings": "v1",
}

@dataclass(frozen=True)
class Prompt:
    name: str
    version: str
    text: str


@cache
def load_prompt(name: str) -> Prompt:
    if name not in ACTIVE_VERSIONS:
        raise ValueError(f"unknown prompt: {name!r}")
    version = ACTIVE_VERSIONS[name]
    text = (PROMPTS_DIR / f"{name}.{version}.txt").read_text(encoding="utf-8")
    return Prompt(name=name, version=version, text=text)

            