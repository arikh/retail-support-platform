import os
from dataclasses import dataclass
from typing import Literal
from dotenv import load_dotenv

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_groq import ChatGroq

load_dotenv()  # TODO(env): temporary — centralize at app entry point, strip from modules

Role = Literal["supervisor", "support"]


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model: str
    temperature: float
    max_tokens: int | None


ROLE_SPECS: dict[Role, ModelSpec] = {
    "supervisor": ModelSpec("groq", "openai/gpt-oss-120b", 0.0, None),
    "support": ModelSpec("groq", "openai/gpt-oss-120b", 0.0, None),
}


def get_groq(spec: ModelSpec) -> BaseChatModel:
    groq_api_key = os.environ["GROQ_API_KEY"]
    groq_provider = ChatGroq(
        model=spec.model,
        api_key=groq_api_key,
        temperature=spec.temperature,
        max_tokens=spec.max_tokens,
        reasoning_format="parsed",
        timeout=None,
        max_retries=2,
        # other params...
    )
    return groq_provider


PROVIDER_BUILDERS = {"groq": get_groq}


class ModelProvider:
    @classmethod
    def get(cls, role: Role) -> BaseChatModel:
        if role not in ROLE_SPECS:
            raise ValueError(f"Invalid role: {role}")

        spec = ROLE_SPECS[role]

        if spec.provider not in PROVIDER_BUILDERS:
            raise ValueError(f"Invalid provider: {spec.provider}")

        builder = PROVIDER_BUILDERS[spec.provider]
        return builder(spec)
