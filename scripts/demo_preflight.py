"""Live TrialIQ demo preflight using only the Python standard library.

Run this after the API, MCP server, Neo4j, and configured LLM provider are up.
It verifies the exact demo path rather than only checking that environment
variables exist.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


CANONICAL_DEMO_QUESTION = (
    "Find completed trials connected to NCT03416088 through its conditions or "
    "interventions. Explain exactly why they are connected, compare their "
    "completion timelines and enrollment, and show the evidence supporting each "
    "conclusion."
)


class PreflightFailure(RuntimeError):
    """Raised when the live demo contract is not satisfied."""


def _request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - explicit local/demo URL
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise PreflightFailure(f"HTTP {exc.code} from {url}: {detail[:500]}") from exc
    except URLError as exc:
        raise PreflightFailure(f"Could not reach {url}: {exc.reason}") from exc
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PreflightFailure(f"Non-JSON response from {url}: {raw[:300]}") from exc
    if not isinstance(value, dict):
        raise PreflightFailure(f"Expected a JSON object from {url}.")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PreflightFailure(message)


def _component(readiness: dict[str, Any], name: str) -> dict[str, Any]:
    components = readiness.get("components")
    _require(isinstance(components, dict), "Readiness response has no components map.")
    value = components.get(name)
    _require(isinstance(value, dict), f"Readiness response has no '{name}' component.")
    return value


def run_preflight(base_url: str, *, timeout: float = 30.0) -> None:
    base_url = base_url.rstrip("/")

    health = _request_json(f"{base_url}/health", timeout=timeout)
    _require(health.get("status") == "ok", "Backend /health did not report status=ok.")
    print("[PASS] API health")

    readiness = _request_json(f"{base_url}/ready", timeout=timeout)
    for name in ("api", "neo4j", "mcp", "llm"):
        component = _component(readiness, name)
        _require(component.get("healthy") is True, f"{name.upper()} is not healthy: {component}")
        if name == "llm":
            provider = component.get("provider") or "unknown"
            model = component.get("model") or "unknown"
            print(f"[PASS] LLM readiness: {provider} / {model}")
        else:
            print(f"[PASS] {name.upper()} readiness")

    run = _request_json(
        f"{base_url}/api/v1/query/agent",
        method="POST",
        payload={"question": CANONICAL_DEMO_QUESTION, "limit": 20},
        timeout=max(timeout, 60.0),
    )
    _require(run.get("status") == "SUCCESS", f"Agent run status was {run.get('status')!r}.")

    retrieval = run.get("retrieval")
    _require(isinstance(retrieval, dict), "Agent response did not include retrieval metadata.")
    _require(retrieval.get("transport") == "mcp", "Agent retrieval did not report MCP transport.")
    related = retrieval.get("related_trial_response")
    _require(isinstance(related, dict), "Canonical demo did not return related-trial evidence.")
    matches = related.get("matches")
    _require(isinstance(matches, list) and matches, "Canonical demo returned no related trials.")

    aggregate = related.get("metrics")
    _require(isinstance(aggregate, dict), "Related-trial aggregate metrics are missing.")
    _require(
        isinstance(aggregate.get("evidence_path_count"), int),
        "Evidence-path aggregate metric is missing.",
    )

    for match in matches:
        _require(isinstance(match, dict), "Related-trial match has an invalid shape.")
        metrics = match.get("metrics")
        _require(isinstance(metrics, dict), f"Metrics missing for {match.get('nct_id')}.")
        paths = match.get("connected_via")
        _require(isinstance(paths, list) and paths, f"Connection evidence missing for {match.get('nct_id')}.")
        for path in paths:
            _require(
                isinstance(path, dict) and isinstance(path.get("entity_id"), str),
                f"Stable entity ID missing from a connection path for {match.get('nct_id')}.",
            )

    generation = run.get("generation")
    _require(isinstance(generation, dict), "Agent response did not include generation metadata.")
    _require(generation.get("method") == "LLM", "Canonical demo did not complete the second LLM synthesis call.")
    _require(run.get("structured_synthesis") is not None, "Structured synthesis is missing.")

    trace = run.get("trace")
    _require(isinstance(trace, list), "Agent execution trace is missing.")
    stages = [item.get("stage") for item in trace if isinstance(item, dict)]
    for expected in ("intent", "retrieval", "metrics", "validation", "synthesis"):
        _require(expected in stages, f"Execution trace is missing the '{expected}' stage.")

    print(f"[PASS] Agentic demo path: {len(matches)} related trial(s), MCP retrieval, deterministic metrics, validated structured synthesis")
    print("[SUCCESS] TrialIQ demo preflight passed.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the live TrialIQ demo path.")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="TrialIQ API base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    try:
        run_preflight(args.base_url, timeout=args.timeout)
    except PreflightFailure as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
