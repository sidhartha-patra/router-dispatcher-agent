from __future__ import annotations

from fastapi.testclient import TestClient

from router_dispatcher_agent.api import create_app


def test_health_endpoint_lists_tools() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert "research_handler" in response.json()["tools"]


def test_run_endpoint_executes_request() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/agent/run",
        json={"prompt": "Research zero-downtime rollout practices and include citations."},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert "research route" in payload["final_answer"].lower()
