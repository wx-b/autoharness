from __future__ import annotations

from pydantic import BaseModel, Field


class NonGameDomain(BaseModel):
    domain_id: str
    constraints: list[str]
    objective_metrics: list[str]
    weights: dict[str, float] = Field(default_factory=dict)


class NonGameEvaluationResult(BaseModel):
    domain_id: str
    constraints_satisfied: bool
    metrics: dict[str, float]
    objective_value: float


def fixture_non_game_domains() -> list[NonGameDomain]:
    return [
        NonGameDomain(
            domain_id="tests-passing",
            constraints=["no network", "all required checks green"],
            objective_metrics=["tests_passing", "failure_count"],
            weights={"tests_passing": 1.0, "failure_count": -1.0},
        ),
        NonGameDomain(
            domain_id="cost-latency",
            constraints=["cost <= 1.0", "latency_ms <= 1000"],
            objective_metrics=["cost", "latency_ms"],
            weights={"cost": -0.2, "latency_ms": -0.001},
        ),
        NonGameDomain(
            domain_id="correctness-risk",
            constraints=["correctness >= 0.8", "risk <= 0.2"],
            objective_metrics=["correctness", "risk"],
            weights={"correctness": 1.0, "risk": -1.0},
        ),
        NonGameDomain(
            domain_id="synthetic-profit-like",
            constraints=["no live trading", "no external side effects"],
            objective_metrics=["synthetic_profit", "cost", "latency_ms", "risk"],
            weights={
                "synthetic_profit": 1.0,
                "cost": -0.1,
                "latency_ms": -0.001,
                "risk": -0.5,
            },
        ),
    ]


def evaluate_non_game_domains(
    domains: list[NonGameDomain],
    observations: dict[str, dict[str, float]],
) -> list[NonGameEvaluationResult]:
    results: list[NonGameEvaluationResult] = []
    for domain in domains:
        metrics = {
            metric: float(observations.get(domain.domain_id, {}).get(metric, 0.0))
            for metric in domain.objective_metrics
        }
        objective_value = sum(
            metrics.get(metric, 0.0) * weight for metric, weight in domain.weights.items()
        )
        results.append(
            NonGameEvaluationResult(
                domain_id=domain.domain_id,
                constraints_satisfied=_constraints_satisfied(domain, metrics),
                metrics=metrics,
                objective_value=objective_value,
            )
        )
    return results


def _constraints_satisfied(domain: NonGameDomain, metrics: dict[str, float]) -> bool:
    if domain.domain_id == "tests-passing":
        return metrics.get("tests_passing", 0.0) >= 1.0 and metrics.get("failure_count", 1.0) == 0.0
    if domain.domain_id == "cost-latency":
        return metrics.get("cost", 2.0) <= 1.0 and metrics.get("latency_ms", 2000.0) <= 1000.0
    if domain.domain_id == "correctness-risk":
        return metrics.get("correctness", 0.0) >= 0.8 and metrics.get("risk", 1.0) <= 0.2
    return (
        "no live trading" in domain.constraints
        and "no external side effects" in domain.constraints
    )
