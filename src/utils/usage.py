"""Per-run token/cost accounting for the two LLM nodes (parse_query,
generate_narrative). Simpler than autonomous-dev-agent's equivalent: this
pipeline is a fixed linear graph with no retry loop, so there's nothing to
abort mid-run -- this is reporting, not a safety guard.

Pricing is OpenAI's published per-million-token rate as of this project's
initial build -- verify against https://openai.com/api/pricing before
relying on it, since prices change. Unknown models fall back to a mid-tier
rate rather than zero, so a model swap can't silently report $0.00.
"""

from dataclasses import dataclass, field

# USD per million tokens: (input, output)
PRICING_PER_MILLION_TOKENS: dict[str, tuple[float, float]] = {
    "gpt-4.1": (2.00, 8.0),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4o": (2.50, 10.0),
    "gpt-4o-mini": (0.15, 0.60),
}
_DEFAULT_PRICING = (2.00, 8.0)


@dataclass
class RunUsage:
    calls: list[dict] = field(default_factory=list)

    @property
    def total_input_tokens(self) -> int:
        return sum(c["input_tokens"] for c in self.calls)

    @property
    def total_output_tokens(self) -> int:
        return sum(c["output_tokens"] for c in self.calls)

    @property
    def total_cost_usd(self) -> float:
        return sum(c["cost_usd"] for c in self.calls)


_usage = RunUsage()


def record_usage(model: str, input_tokens: int, output_tokens: int) -> float:
    in_rate, out_rate = PRICING_PER_MILLION_TOKENS.get(model, _DEFAULT_PRICING)
    cost = (input_tokens / 1_000_000) * in_rate + (output_tokens / 1_000_000) * out_rate
    _usage.calls.append(
        {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost,
        }
    )
    return cost


def get_usage() -> RunUsage:
    return _usage


def format_usage() -> str:
    if not _usage.calls:
        return "no LLM calls recorded"
    lines = [f"{'model':<20}{'calls':>7}{'in':>12}{'out':>10}{'usd':>12}"]
    by_model: dict[str, dict[str, float]] = {}
    for call in _usage.calls:
        agg = by_model.setdefault(call["model"], {"calls": 0, "in": 0, "out": 0, "usd": 0.0})
        agg["calls"] += 1
        agg["in"] += call["input_tokens"]
        agg["out"] += call["output_tokens"]
        agg["usd"] += call["cost_usd"]
    for model, agg in sorted(by_model.items()):
        lines.append(
            f"{model:<20}{int(agg['calls']):>7}{int(agg['in']):>12,}"
            f"{int(agg['out']):>10,}{agg['usd']:>12.6f}"
        )
    lines.append(
        f"{'TOTAL':<20}{len(_usage.calls):>7}{_usage.total_input_tokens:>12,}"
        f"{_usage.total_output_tokens:>10,}{_usage.total_cost_usd:>12.6f}"
    )
    return "\n".join(lines)
