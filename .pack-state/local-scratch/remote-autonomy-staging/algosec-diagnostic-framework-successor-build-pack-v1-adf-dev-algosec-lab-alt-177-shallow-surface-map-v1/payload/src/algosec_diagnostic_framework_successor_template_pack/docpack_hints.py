from __future__ import annotations

import json
import re
import shlex
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ARTIFACT_ROOT = Path("dist/candidates/adf-docpack-hints")
DEFAULT_HINT_FILENAME = "asms-docpack-hints.json"
DEFAULT_SSH_DESTINATION = "adf-dev"
DEFAULT_REMOTE_DOCPACK_ROOT = "/ai-workflow/out/asms/A33.10/asms-docpack"
TITLE_PREFIXES = (
    "welcome to ",
    "about ",
    "configure ",
    "configuring ",
    "add ",
    "adding ",
    "manage ",
    "managing ",
    "using ",
    "understanding ",
    "working with ",
    "introduction to ",
    "introduction ",
    "define ",
    "defining ",
)
STOP_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "for",
    "from",
    "in",
    "into",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
    "your",
}
PRODUCT_AREA_MAP = {
    "afa-admin": "afa",
    "afa-ug": "afa",
    "ff-ug": "fireflow",
    "bf-ug": "appviz",
    "api-guide": "api",
    "auto-disc-guide": "application_discovery",
    "install-guide": "installation",
    "shared-files": "shared",
    "cloud-common": "cloud",
}
PORT_PATTERN = re.compile(
    r"(?i)(?:default\s+port|port(?:s)?(?:\s+number)?)(?:\s*(?:is|are|of|=|:))?\s*(\d{2,5})|https?://[^\s:]+:(\d{2,5})"
)
WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")


def import_docpack_hints(
    *,
    project_root: Path,
    ssh_destination: str = DEFAULT_SSH_DESTINATION,
    remote_docpack_root: str = DEFAULT_REMOTE_DOCPACK_ROOT,
    artifact_root: str | Path | None = None,
) -> dict[str, Any]:
    manifest = _capture_remote_json(
        ssh_destination=ssh_destination,
        remote_path=f"{remote_docpack_root}/manifest.json",
    )
    toc = _capture_remote_json(
        ssh_destination=ssh_destination,
        remote_path=f"{remote_docpack_root}/toc.json",
    )
    pages = _capture_remote_jsonl(
        ssh_destination=ssh_destination,
        remote_path=f"{remote_docpack_root}/pages.jsonl",
    )
    chunks = _capture_remote_jsonl(
        ssh_destination=ssh_destination,
        remote_path=f"{remote_docpack_root}/chunks.jsonl",
    )

    product_areas = _build_product_areas(pages)
    term_hints = _build_term_hints(pages=pages, product_areas=product_areas)
    port_hints = _build_port_hints(chunks=chunks, pages_by_doc_id={page["doc_id"]: page for page in pages})

    root = project_root / (Path(artifact_root) if artifact_root else DEFAULT_ARTIFACT_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    hint_path = root / DEFAULT_HINT_FILENAME
    payload = {
        "schema_version": "adf-docpack-hints/v1",
        "generated_at": _isoformat_z(),
        "authority_rule": {
            "runtime_evidence_precedence": True,
            "summary": "Imported doc-pack hints are supplementary naming and prioritization inputs. They must not override live runtime evidence for ownership, dependency order, or active-state proof.",
        },
        "source": {
            "ssh_destination": ssh_destination,
            "remote_docpack_root": remote_docpack_root,
            "docpack_id": manifest.get("docpack_id"),
            "version": manifest.get("version"),
            "created_at": manifest.get("created_at"),
            "counts": manifest.get("counts", {}),
            "files": manifest.get("files", {}),
            "toc_bundle_count": toc.get("bundle_count"),
        },
        "product_areas": product_areas,
        "term_hints": term_hints,
        "port_hints": port_hints,
        "summary": {
            "product_area_count": len(product_areas),
            "term_hint_count": len(term_hints),
            "port_hint_count": len(port_hints),
        },
    }
    hint_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "status": "pass",
        "artifact_root": str(root.relative_to(project_root)),
        "generated_files": [str(hint_path.relative_to(project_root))],
        "summary": payload["summary"],
        "source": {
            "docpack_id": payload["source"]["docpack_id"],
            "version": payload["source"]["version"],
            "ssh_destination": ssh_destination,
        },
    }


def load_docpack_hints(project_root: Path, hint_path: str | Path | None = None) -> dict[str, Any] | None:
    selected_path = project_root / (Path(hint_path) if hint_path else DEFAULT_ARTIFACT_ROOT / DEFAULT_HINT_FILENAME)
    if not selected_path.exists():
        return None
    payload = json.loads(selected_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{selected_path}: doc-pack hint artifact must contain a JSON object")
    if payload.get("schema_version") != "adf-docpack-hints/v1":
        raise ValueError(f"{selected_path}: unsupported doc-pack hint schema_version")
    payload["_loaded_from"] = str(selected_path.relative_to(project_root))
    return payload


def _build_product_areas(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    areas: dict[str, dict[str, Any]] = {}
    for page in pages:
        relpath = str(page.get("source_relpath") or "")
        path_parts = relpath.split("/")
        area_key = PRODUCT_AREA_MAP.get(path_parts[1] if len(path_parts) > 1 else "", "general")
        area = areas.setdefault(
            area_key,
            {
                "area_id": area_key,
                "page_count": 0,
                "source_prefixes": set(),
                "source_doc_ids": [],
                "surface_terms": set(),
            },
        )
        area["page_count"] += 1
        if len(path_parts) > 1:
            area["source_prefixes"].add(path_parts[1])
        doc_id = str(page.get("doc_id") or "")
        if doc_id and doc_id not in area["source_doc_ids"]:
            area["source_doc_ids"].append(doc_id)
        for term in _extract_title_terms(str(page.get("title") or "")):
            area["surface_terms"].add(term)

    result = []
    for area in sorted(areas.values(), key=lambda item: item["area_id"]):
        result.append(
            {
                "area_id": area["area_id"],
                "page_count": area["page_count"],
                "source_prefixes": sorted(area["source_prefixes"]),
                "source_doc_ids": sorted(area["source_doc_ids"])[:20],
                "surface_terms": sorted(area["surface_terms"])[:30],
            }
        )
    return result


def _build_term_hints(
    *,
    pages: list[dict[str, Any]],
    product_areas: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    term_index: dict[str, dict[str, Any]] = {}
    area_by_prefix = {
        prefix: area["area_id"]
        for area in product_areas
        for prefix in area.get("source_prefixes", [])
    }

    for page in pages:
        title = str(page.get("title") or "")
        relpath = str(page.get("source_relpath") or "")
        path_parts = relpath.split("/")
        product_area = area_by_prefix.get(path_parts[1] if len(path_parts) > 1 else "", "general")
        for term in _extract_title_terms(title):
            entry = term_index.setdefault(
                term,
                {
                    "normalized_term": term,
                    "term": term,
                    "categories": set(),
                    "product_areas": set(),
                    "source_doc_ids": set(),
                    "source_titles": set(),
                    "evidence_count": 0,
                },
            )
            entry["categories"].update(_categorize_term(term))
            entry["product_areas"].add(product_area)
            if page.get("doc_id"):
                entry["source_doc_ids"].add(str(page["doc_id"]))
            if title:
                entry["source_titles"].add(title)
            entry["evidence_count"] += 1

    result = []
    for term, entry in sorted(term_index.items()):
        result.append(
            {
                "normalized_term": term,
                "term": entry["term"],
                "categories": sorted(entry["categories"]),
                "product_areas": sorted(entry["product_areas"]),
                "source_doc_ids": sorted(entry["source_doc_ids"])[:20],
                "source_titles": sorted(entry["source_titles"])[:10],
                "evidence_count": entry["evidence_count"],
            }
        )
    return result


def _build_port_hints(
    *,
    chunks: list[dict[str, Any]],
    pages_by_doc_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    index: dict[int, dict[str, Any]] = {}
    for chunk in chunks:
        markdown = str(chunk.get("markdown") or "")
        doc_id = str(chunk.get("doc_id") or "")
        title = str(chunk.get("title") or "")
        page = pages_by_doc_id.get(doc_id, {})
        relpath = str(page.get("source_relpath") or "")
        path_parts = relpath.split("/")
        product_area = PRODUCT_AREA_MAP.get(path_parts[1] if len(path_parts) > 1 else "", "general")
        context_terms = sorted(set(_extract_title_terms(title)))
        for match in PORT_PATTERN.finditer(markdown):
            port_text = match.group(1) or match.group(2)
            if not port_text or not port_text.isdigit():
                continue
            port = int(port_text)
            if port < 2 or port > 65535:
                continue
            entry = index.setdefault(
                port,
                {
                    "port": port,
                    "categories": set(),
                    "product_areas": set(),
                    "context_terms": set(),
                    "source_doc_ids": set(),
                    "source_titles": set(),
                    "evidence_count": 0,
                },
            )
            entry["categories"].update(_categorize_term(title))
            entry["product_areas"].add(product_area)
            entry["context_terms"].update(context_terms[:6])
            if doc_id:
                entry["source_doc_ids"].add(doc_id)
            if title:
                entry["source_titles"].add(title)
            entry["evidence_count"] += 1

    result = []
    for port in sorted(index):
        entry = index[port]
        result.append(
            {
                "port": port,
                "categories": sorted(entry["categories"]),
                "product_areas": sorted(entry["product_areas"]),
                "context_terms": sorted(entry["context_terms"]),
                "source_doc_ids": sorted(entry["source_doc_ids"])[:20],
                "source_titles": sorted(entry["source_titles"])[:10],
                "evidence_count": entry["evidence_count"],
            }
        )
    return result


def _extract_title_terms(title: str) -> list[str]:
    cleaned = _normalize_phrase(title)
    terms = {cleaned} if cleaned else set()
    stripped = cleaned
    for prefix in TITLE_PREFIXES:
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix) :]
            break
    if stripped and stripped != cleaned:
        terms.add(stripped)

    tokens = [
        token
        for token in WORD_PATTERN.findall(cleaned)
        if token.lower() not in STOP_WORDS
    ]
    for token in tokens:
        normalized = token.lower()
        if len(normalized) >= 3:
            terms.add(normalized)
    return sorted(term for term in terms if len(term) >= 3)


def _normalize_phrase(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", value).strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _categorize_term(term: str) -> set[str]:
    normalized = _normalize_phrase(term)
    categories = {"surface_term"}
    tokens = set(normalized.split())
    if tokens & {"auth", "ldap", "saml", "keycloak", "authentication", "authorization"}:
        categories.add("identity_or_access")
    if tokens & {"proxy", "apache", "httpd", "nginx"}:
        categories.add("edge_proxy")
    if tokens & {
        "api",
        "apis",
        "rest",
        "soap",
        "workflow",
        "discovery",
        "appviz",
        "fireflow",
        "afa",
        "asms",
        "objectflow",
        "horizon",
    }:
        categories.add("application_service")
    if tokens & {"syslog", "log", "logging", "logs"}:
        categories.add("logging_surface")
    if tokens & {"activemq", "kafka", "rabbitmq"}:
        categories.add("queue_or_messaging")
    if tokens & {"postgres", "oracle", "mysql", "mariadb", "redis"}:
        categories.add("data_store")
    if tokens & {"integration", "integrations"}:
        categories.add("integration_surface")
    if tokens & {"api", "apis"}:
        categories.add("api_surface")
    return categories


def _capture_remote_json(*, ssh_destination: str, remote_path: str) -> dict[str, Any]:
    text = _capture_remote_text(
        ssh_destination=ssh_destination,
        remote_command=f"cat {shlex.quote(remote_path)}",
        timeout_seconds=30,
    )
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError(f"{remote_path}: expected a JSON object")
    return payload


def _capture_remote_jsonl(*, ssh_destination: str, remote_path: str) -> list[dict[str, Any]]:
    text = _capture_remote_text(
        ssh_destination=ssh_destination,
        remote_command=f"cat {shlex.quote(remote_path)}",
        timeout_seconds=90,
    )
    records: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _capture_remote_text(*, ssh_destination: str, remote_command: str, timeout_seconds: int) -> str:
    argv = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "PreferredAuthentications=publickey",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "ServerAliveInterval=15",
        "-o",
        "ServerAliveCountMax=2",
        ssh_destination,
        remote_command,
    ]
    completed = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout_seconds,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"remote capture failed for {ssh_destination}: {stderr}")
    return completed.stdout


def _isoformat_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
