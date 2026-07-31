from __future__ import annotations

from collections.abc import Iterable

from .models import ModelDecision, StepRecord, ToolCapability


class FakeDeterministicModel:
    _routes: dict[str, tuple[str, list[str]]] = {
        "research_handler": (
            "research",
            ["research", "source", "cite", "investigate", "brief", "rollout", "memo"],
        ),
        "code_handler": (
            "code",
            ["code", "bug", "stack", "test", "refactor", "debug"],
        ),
        "data_handler": (
            "data",
            ["sql", "data", "dataset", "metric", "analysis", "dashboard"],
        ),
        "scheduling_handler": (
            "scheduling",
            ["meeting", "calendar", "schedule", "book", "invite"],
        ),
    }

    def next_decision(
        self,
        prompt: str,
        steps: list[StepRecord],
        capabilities: Iterable[ToolCapability],
    ) -> ModelDecision:
        lowered = prompt.lower()
        capability_names = {capability.name for capability in capabilities}

        if steps:
            last = steps[-1]
            if last.tool_name == "research_handler":
                response = str(last.tool_output["response"])
                if "ignore previous instructions" in response.lower():
                    return ModelDecision(
                        kind="final",
                        rationale="research content is untrusted data",
                        final_answer=(
                            "Research content included prompt-injection text. "
                            "It was treated as data only and not executed."
                        ),
                    )
                citations = ", ".join(
                    str(value) for value in last.tool_output.get("citations", [])
                )
                return ModelDecision(
                    kind="final",
                    rationale="research route completed",
                    final_answer=(
                        f"Research route selected with citations {citations}. "
                        f"{response}"
                    ),
                )
            if last.tool_name in {
                "code_handler",
                "data_handler",
                "scheduling_handler",
                "fallback_handler",
            }:
                route = str(last.tool_output["route"])
                confidence = float(last.tool_output["confidence"])
                return ModelDecision(
                    kind="final",
                    rationale=f"{route} route completed",
                    final_answer=(
                        f"Route={route} confidence={confidence:.2f}. "
                        f"{last.tool_output['response']}"
                    ),
                )

        scores: dict[str, int] = {}
        for tool_name, (_, keywords) in self._routes.items():
            scores[tool_name] = sum(1 for keyword in keywords if keyword in lowered)

        best_tool = (
            max(scores.items(), key=lambda item: item[1])[0]
            if scores
            else "fallback_handler"
        )
        best_score = scores.get(best_tool, 0)
        ranked = sorted(scores.values(), reverse=True)
        second_score = ranked[1] if len(ranked) > 1 else 0
        confidence = best_score / 3 if best_score else 0.0

        if best_score == 0 or confidence < 0.34 or best_score == second_score:
            return ModelDecision(
                kind="tool",
                rationale="intent confidence is too low, use fallback route",
                tool_name="fallback_handler",
                arguments={"message": prompt},
            )

        if best_tool not in capability_names:
            return ModelDecision(
                kind="tool",
                rationale="selected route is unavailable, use fallback",
                tool_name="fallback_handler",
                arguments={"message": prompt},
            )

        route_name = self._routes[best_tool][0]
        return ModelDecision(
            kind="tool",
            rationale=f"dispatch to {route_name} with confidence {confidence:.2f}",
            tool_name=best_tool,
            arguments={"message": prompt},
        )
