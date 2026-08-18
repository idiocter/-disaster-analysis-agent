"""Swappable disaster-risk model interface.

v1 = RuleBasedRiskModel: a transparent weighted composite index, NOT a
trained classifier -- there is no labeled Nepal disaster-incident dataset
available at municipality granularity (see plan.md's risk section). Do not
present this as validated; `explain()` exists specifically so the narrative
agent can show its work instead of implying more confidence than it has.

v1.5 upgrade path (documented, not built): RegressionRiskModel, trained on a
real labeled proxy dataset if one becomes available (e.g. DesInventar Nepal,
BIPAD/NDRRMA), same interface, swapped in via model_registry.py.
"""

from abc import ABC, abstractmethod
from typing import TypedDict


class ZoneFeatures(TypedDict):
    zone_name: str
    forest_loss_pct: float
    mean_slope_deg: float
    rainfall_intensity_norm: float  # pre-normalized 0-1; real value in Phase 4


class ZoneRisk(TypedDict):
    zone_name: str
    risk_score: float  # 0-100
    risk_class: str  # "Low" | "Medium" | "High" | "Very High"
    contributions: dict[str, float]  # per-feature weighted contribution, for explain()


DEFAULT_WEIGHTS = {
    "forest_loss_pct": 0.4,
    "mean_slope_deg": 0.3,
    "rainfall_intensity_norm": 0.2,
    # river proximity omitted until Phase 4 hydrology layer exists; when
    # added, rebalance weights to sum to 1.0 again.
    "_reserved_river_proximity": 0.1,
}


class RiskModel(ABC):
    model_version: str

    @abstractmethod
    def predict(self, zones: list[ZoneFeatures]) -> list[ZoneRisk]: ...

    @abstractmethod
    def explain(self, zone_risk: ZoneRisk) -> str: ...


def _normalize(values: list[float]) -> list[float]:
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.5 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def _classify(score: float) -> str:
    if score < 25:
        return "Low"
    if score < 50:
        return "Medium"
    if score < 75:
        return "High"
    return "Very High"


class RuleBasedRiskModel(RiskModel):
    model_version = "rule-based-v1"

    def __init__(self, weights: dict[str, float] | None = None):
        self.weights = weights or DEFAULT_WEIGHTS

    def predict(self, zones: list[ZoneFeatures]) -> list[ZoneRisk]:
        if not zones:
            return []

        forest_loss_norm = _normalize([z["forest_loss_pct"] for z in zones])
        slope_norm = _normalize([z["mean_slope_deg"] for z in zones])
        rainfall_norm = [z["rainfall_intensity_norm"] for z in zones]  # already 0-1

        results: list[ZoneRisk] = []
        for zone, fl, sl, rf in zip(zones, forest_loss_norm, slope_norm, rainfall_norm):
            contributions = {
                "forest_loss_pct": fl * self.weights["forest_loss_pct"] * 100,
                "mean_slope_deg": sl * self.weights["mean_slope_deg"] * 100,
                "rainfall_intensity_norm": rf * self.weights["rainfall_intensity_norm"] * 100,
            }
            score = sum(contributions.values())
            results.append(
                ZoneRisk(
                    zone_name=zone["zone_name"],
                    risk_score=round(score, 1),
                    risk_class=_classify(score),
                    contributions={k: round(v, 1) for k, v in contributions.items()},
                )
            )
        return results

    def explain(self, zone_risk: ZoneRisk) -> str:
        ranked = sorted(zone_risk["contributions"].items(), key=lambda kv: kv[1], reverse=True)
        parts = [f"{name} contributed {value:.1f} points" for name, value in ranked]
        return (
            f"{zone_risk['zone_name']}: {zone_risk['risk_class']} risk "
            f"(score {zone_risk['risk_score']:.1f}/100). "
            f"Heuristic composite index (model={self.model_version}), not a validated "
            f"predictive model. Breakdown: {'; '.join(parts)}."
        )
