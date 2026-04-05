from __future__ import annotations

from pathlib import Path
from typing import Any

from .assistant_contracts import load_context_routing


def _normalize(value: str) -> str:
    return value.strip().lower()


def route_context(project_root: Path, topic: str) -> dict[str, Any]:
    routing = load_context_routing(project_root)
    routes = routing.get("routes", [])
    if not isinstance(routes, list):
        raise ValueError("contracts/context-routing.json must contain a routes array")

    requested = _normalize(topic)
    best_route: dict[str, Any] | None = None
    best_score = -1
    for route in routes:
        if not isinstance(route, dict):
            continue
        score = 0
        route_id = route.get("route_id")
        if isinstance(route_id, str) and _normalize(route_id) == requested:
            score += 5
        keywords = route.get("keywords", [])
        if isinstance(keywords, list):
            for keyword in keywords:
                if isinstance(keyword, str) and _normalize(keyword) in requested:
                    score += 2
        summary = route.get("summary")
        if isinstance(summary, str) and requested and requested in _normalize(summary):
            score += 1
        if score > best_score:
            best_score = score
            best_route = route

    available_topics = [
        route.get("route_id")
        for route in routes
        if isinstance(route, dict) and isinstance(route.get("route_id"), str)
    ]
    if best_route is None or best_score <= 0:
        return {
            "status": "fail",
            "requested_topic": topic,
            "available_topics": available_topics,
            "matched_route": None,
            "paths": [],
        }

    return {
        "status": "pass",
        "requested_topic": topic,
        "matched_route": best_route.get("route_id"),
        "summary": best_route.get("summary"),
        "paths": best_route.get("paths", []),
        "available_topics": available_topics,
    }
