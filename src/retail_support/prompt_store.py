from dataclasses import dataclass
from functools import cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"

ACTIVE_VERSIONS = {
    "routing_system": "v2",
    "support_system": "v2",
    "support_status_guide": "v2",
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


def call_metadata(node: str, *prompts: Prompt) -> dict[str, str]:
    """What one model call says about itself; LLMCallLogger reads these keys.

    prompts maps each prompt's name to its version, so a call built from
    two prompt files names both.
    """
    return {
        "node": node,
        "prompts": {prompt.name: prompt.version for prompt in prompts},
    }
