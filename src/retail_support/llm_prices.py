"""Prices per million tokens, used to work out the cost of each LLM call.

Checked on 9 Oct 2026 on Groq's model page for openai/gpt-oss-120b.
Prices change: when they do, update this table and the date above.

Reasoning tokens are already inside output_tokens (a reply reported
62 output tokens, 52 of them reasoning), so they are not added again.
"""

from decimal import Decimal

MILLION = Decimal(1_000_000)

PRICES_PER_MILLION: dict[str, dict[str, Decimal]] = {
    "openai/gpt-oss-120b": {
        "input": Decimal("0.15"),
        "cached_input": Decimal("0.075"),
        "output": Decimal("0.60"),
    },
}


def cost_usd(
    model: str, input_tokens: int, output_tokens: int, cached_tokens: int = 0
) -> Decimal:
    """Cost in US dollars of one call. Cached input tokens are billed at the
    cached price; the rest of the input at the normal price."""
    if model not in PRICES_PER_MILLION:
        raise ValueError(f"no price for model: {model!r}")
    price = PRICES_PER_MILLION[model]
    uncached = input_tokens - cached_tokens
    total = (
        uncached * price["input"]
        + cached_tokens * price["cached_input"]
        + output_tokens * price["output"]
    )
    return total / MILLION
