from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .demo_data import RESEARCH_SNIPPETS, SAMPLE_TIMES
from .models import RiskLevel, ToolCapability


class ToolExecutionError(RuntimeError):
    pass


@dataclass(slots=True)
class ToolContext:
    workspace_root: Path
    trace_id: str


class RouteInput(BaseModel):
    message: str


class RouteOutput(BaseModel):
    route: str
    confidence: float
    response: str
    citations: list[str] = Field(default_factory=list)


class BaseTool:
    input_model: type[BaseModel]
    output_model: type[BaseModel]

    def __init__(
        self,
        *,
        name: str,
        description: str,
        input_model: type[BaseModel],
        output_model: type[BaseModel],
        risk_level: RiskLevel = RiskLevel.LOW,
        requires_approval: bool = False,
        side_effects: list[str] | None = None,
    ) -> None:
        self.input_model = input_model
        self.output_model = output_model
        self.capability = ToolCapability(
            name=name,
            description=description,
            input_schema=input_model.model_json_schema(),
            output_schema=output_model.model_json_schema(),
            risk_level=risk_level,
            requires_approval=requires_approval,
            side_effects=side_effects or [],
        )

    def execute(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        raise NotImplementedError

    def invoke(self, arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        payload = self.input_model.model_validate(arguments)
        result = self.execute(payload, context)
        return result.model_dump()


class ResearchHandlerTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="research_handler",
            description="Route research questions to a citation-aware research handler.",
            input_model=RouteInput,
            output_model=RouteOutput,
        )

    def execute(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        query = RouteInput.model_validate(payload).message.lower()
        wants_override = "override memo" in query or "memo" in query
        snippets = []
        citations = []
        for item in RESEARCH_SNIPPETS:
            if item["title"] == "Override Memo" and not wants_override:
                continue
            matches_query = any(
                token in item["content"].lower() or token in item["title"].lower()
                for token in query.split()
            )
            if matches_query:
                snippets.append(item["content"])
                citations.append(item["title"])
        if not snippets:
            snippets = ["No direct research match was found. Use fallback clarification."]
            citations = ["Fallback research note"]
        return RouteOutput(
            route="research",
            confidence=0.9,
            response=f"Research synthesis: {' '.join(snippets[:2])}",
            citations=citations[:2],
        )


class CodeHandlerTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="code_handler",
            description="Route debugging and code tasks to a code-focused handler.",
            input_model=RouteInput,
            output_model=RouteOutput,
        )

    def execute(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        message = RouteInput.model_validate(payload).message
        return RouteOutput(
            route="code",
            confidence=0.88,
            response=(
                "Code debugging plan: reproduce the issue, capture failing inputs, "
                "inspect the affected module, add a targeted test, then patch safely."
            ),
            citations=[message[:40]],
        )


class DataHandlerTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="data_handler",
            description="Route data analysis questions to a bounded analysis handler.",
            input_model=RouteInput,
            output_model=RouteOutput,
        )

    def execute(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        return RouteOutput(
            route="data",
            confidence=0.86,
            response=(
                "Data analysis plan: validate the dataset shape, profile nulls, compute "
                "key aggregates, and visualize only the metrics needed for the decision."
            ),
            citations=["Deterministic analysis playbook"],
        )


class SchedulingHandlerTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="scheduling_handler",
            description="Stage a meeting recommendation or invite for scheduling requests.",
            input_model=RouteInput,
            output_model=RouteOutput,
            risk_level=RiskLevel.HIGH,
            requires_approval=True,
            side_effects=["calendar invite staging"],
        )

    def execute(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        message = RouteInput.model_validate(payload).message
        return RouteOutput(
            route="scheduling",
            confidence=0.93,
            response=(
                f"Scheduling recommendation for '{message}': staged invite candidates "
                f"{', '.join(SAMPLE_TIMES[:2])}."
            ),
            citations=SAMPLE_TIMES[:2],
        )


class FallbackHandlerTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="fallback_handler",
            description="Fallback handler for low-confidence or ambiguous messages.",
            input_model=RouteInput,
            output_model=RouteOutput,
        )

    def execute(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        return RouteOutput(
            route="fallback",
            confidence=0.2,
            response=(
                "Fallback route: ask a clarifying question before dispatching because "
                "intent confidence did not clear the threshold."
            ),
            citations=[],
        )


class FailingTool(BaseTool):
    def __init__(self, name: str = "failing_tool") -> None:
        super().__init__(
            name=name,
            description="Tool used in tests to simulate failures.",
            input_model=RouteInput,
            output_model=RouteOutput,
        )

    def execute(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        raise ToolExecutionError("simulated tool failure")


class SlowTool(BaseTool):
    def __init__(self, delay_seconds: float) -> None:
        super().__init__(
            name="slow_tool",
            description="Tool used in tests to simulate timeouts.",
            input_model=RouteInput,
            output_model=RouteOutput,
        )
        self.delay_seconds = delay_seconds

    def execute(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        import time

        time.sleep(self.delay_seconds)
        return RouteOutput(route="slow", confidence=0.0, response="slow tool completed")


def build_default_tools() -> dict[str, BaseTool]:
    tools: list[BaseTool] = [
        ResearchHandlerTool(),
        CodeHandlerTool(),
        DataHandlerTool(),
        SchedulingHandlerTool(),
        FallbackHandlerTool(),
    ]
    return {tool.capability.name: tool for tool in tools}
