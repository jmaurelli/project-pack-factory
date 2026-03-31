from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final, Iterable, Mapping, MutableMapping, Sequence, cast

try:  # pragma: no cover - dependency availability is environment-specific
    from jsonschema import FormatChecker
    from jsonschema.validators import validator_for
except Exception:  # pragma: no cover - handled deterministically at runtime
    FormatChecker = None  # type: ignore[assignment]
    validator_for = None  # type: ignore[assignment]


FACTORY_SCHEMA_DIRNAME: Final = Path("docs/specs/project-pack-factory/schemas")
PERSONALITY_TEMPLATE_CATALOG_PATH: Final = Path(
    "docs/specs/project-pack-factory/agent-personality-template-catalog.json"
)
ROLE_DOMAIN_TEMPLATE_CATALOG_PATH: Final = Path(
    "docs/specs/project-pack-factory/agent-role-domain-template-catalog.json"
)
REGISTRY_TEMPLATE_PATH: Final = Path("registry/templates.json")
REGISTRY_BUILD_PATH: Final = Path("registry/build-packs.json")
PROMOTION_LOG_PATH: Final = Path("registry/promotion-log.json")
RETIREMENT_STATE_PATH: Final = Path("status/retirement.json")
LIFECYCLE_STATE_PATH: Final = Path("status/lifecycle.json")
READINESS_STATE_PATH: Final = Path("status/readiness.json")
DEPLOYMENT_STATE_PATH: Final = Path("status/deployment.json")
PACK_MANIFEST_PATH: Final = Path("pack.json")
PRIMARY_PACK_DIRECTORIES: Final = ("templates", "build-packs")
DEPLOYMENT_ENVIRONMENTS: Final = ("testing", "staging", "production")


@dataclass(frozen=True)
class PackLocation:
    factory_root: Path
    pack_id: str
    pack_kind: str
    pack_root: Path
    registry_path: Path
    registry: dict[str, Any]
    registry_index: int
    manifest: dict[str, Any]


@dataclass(frozen=True)
class EnvironmentAssignment:
    environment: str
    pack_id: str
    pointer_path: Path
    pointer_relative_path: str
    pointer_payload: dict[str, Any]
    deployment_path: Path
    deployment_payload: dict[str, Any]
    registry_index: int
    registry_entry: dict[str, Any]
    promotion_event: dict[str, Any]
    promotion_report_path: Path
    promotion_report_relative_path: str
    promotion_report: dict[str, Any]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(dump_json(data))
        temp_path = Path(handle.name)
    temp_path.replace(path)


def remove_file(path: Path) -> bool:
    if path.exists():
        path.unlink()
        return True
    return False


def resolve_factory_root(factory_root: str | Path) -> Path:
    root = Path(factory_root).expanduser().resolve()
    if not root.is_absolute():
        raise ValueError("factory_root must resolve to an absolute path")
    return root


def read_now() -> datetime:
    fixed_now = os.environ.get("PROJECT_PACK_FACTORY_FIXED_NOW") or os.environ.get(
        "PACK_FACTORY_FIXED_NOW"
    )
    if fixed_now:
        value = fixed_now.strip()
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).replace(microsecond=0)
    return datetime.now(timezone.utc).replace(microsecond=0)


def isoformat_z(moment: datetime | None = None) -> str:
    current = read_now() if moment is None else moment.astimezone(timezone.utc).replace(microsecond=0)
    return current.isoformat().replace("+00:00", "Z")


def timestamp_token(moment: datetime | None = None) -> str:
    current = read_now() if moment is None else moment.astimezone(timezone.utc).replace(microsecond=0)
    return current.strftime("%Y%m%d") + "t" + current.strftime("%H%M%S") + "z"


def pack_root_for_kind(pack_kind: str, pack_id: str) -> Path:
    if pack_kind == "template_pack":
        return Path("templates") / pack_id
    if pack_kind == "build_pack":
        return Path("build-packs") / pack_id
    raise ValueError(f"unsupported pack kind: {pack_kind}")


def is_pack_root(path: Path) -> bool:
    return path.parent.name in PRIMARY_PACK_DIRECTORIES


def relative_path(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _load_registry_entries(registry_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = load_json(registry_path)
    if not isinstance(payload, dict):
        raise ValueError(f"{registry_path}: registry file must contain a JSON object")
    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError(f"{registry_path}: entries must be an array")
    return cast(dict[str, Any], payload), cast(list[dict[str, Any]], entries)


def discover_pack(factory_root: Path, pack_id: str) -> PackLocation:
    registry_candidates: list[tuple[Path, dict[str, Any], int]] = []
    for registry_path in (factory_root / REGISTRY_TEMPLATE_PATH, factory_root / REGISTRY_BUILD_PATH):
        if not registry_path.exists():
            continue
        registry, entries = _load_registry_entries(registry_path)
        for index, entry in enumerate(entries):
            if isinstance(entry, dict) and entry.get("pack_id") == pack_id:
                registry_candidates.append((registry_path, registry, index))

    pack_roots = [factory_root / kind / pack_id for kind in PRIMARY_PACK_DIRECTORIES]
    existing_roots = [path for path in pack_roots if path.exists()]

    if len(existing_roots) == 0:
        raise FileNotFoundError(f"pack `{pack_id}` does not exist in templates/ or build-packs/")
    if len(existing_roots) > 1:
        raise ValueError(f"pack `{pack_id}` exists in multiple pack roots: {', '.join(str(path) for path in existing_roots)}")
    if len(registry_candidates) == 0:
        raise FileNotFoundError(f"pack `{pack_id}` is not registered in factory registry state")
    if len(registry_candidates) > 1:
        raise ValueError(f"pack `{pack_id}` is registered in more than one registry")

    registry_path, registry, registry_index = registry_candidates[0]
    entry = cast(dict[str, Any], registry["entries"][registry_index])
    pack_kind = cast(str, entry.get("pack_kind", "unknown"))
    pack_root = factory_root / pack_root_for_kind(pack_kind, pack_id)
    if not pack_root.exists():
        raise FileNotFoundError(f"registered pack root is missing: {relative_path(factory_root, pack_root)}")
    manifest_path = pack_root / PACK_MANIFEST_PATH
    if not manifest_path.exists():
        raise FileNotFoundError(f"missing pack manifest: {relative_path(factory_root, manifest_path)}")
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise ValueError(f"{relative_path(factory_root, manifest_path)} must contain a JSON object")
    manifest_dict = cast(dict[str, Any], manifest)
    if manifest_dict.get("pack_id") != pack_id:
        raise ValueError(f"{relative_path(factory_root, manifest_path)} pack_id does not match registry state")
    if manifest_dict.get("pack_kind") != pack_kind:
        raise ValueError(f"{relative_path(factory_root, manifest_path)} pack_kind does not match registry state")
    return PackLocation(
        factory_root=factory_root,
        pack_id=pack_id,
        pack_kind=pack_kind,
        pack_root=pack_root,
        registry_path=registry_path,
        registry=registry,
        registry_index=registry_index,
        manifest=manifest_dict,
    )


def schema_dir(factory_root: Path) -> Path:
    return factory_root / FACTORY_SCHEMA_DIRNAME


def schema_path(factory_root: Path, filename: str) -> Path:
    return schema_dir(factory_root) / filename


def personality_template_catalog_path(factory_root: Path) -> Path:
    return factory_root / PERSONALITY_TEMPLATE_CATALOG_PATH


def _validator_for_schema(schema: dict[str, Any]):
    if validator_for is None or FormatChecker is None:
        raise RuntimeError("jsonschema is required for schema validation")
    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    return validator_class(schema, format_checker=FormatChecker())


def validate_json_document(document_path: Path, schema_path_: Path) -> list[str]:
    if validator_for is None or FormatChecker is None:
        return ["jsonschema is required for schema validation"]
    payload = load_json(document_path)
    if not isinstance(payload, dict):
        return [f"{document_path}: JSON document must contain an object"]
    schema = load_json(schema_path_)
    if not isinstance(schema, dict):
        return [f"{schema_path_}: schema file must contain a JSON object"]
    try:
        validator = _validator_for_schema(cast(dict[str, Any], schema))
    except Exception as exc:
        return [f"{schema_path_}: invalid schema: {exc}"]
    errors: list[str] = []
    for error in validator.iter_errors(payload):
        location = ".".join(str(piece) for piece in error.absolute_path)
        prefix = f"{document_path}: " if not location else f"{document_path} [{location}]: "
        errors.append(f"{prefix}{error.message}")
    return errors


def load_personality_template_catalog(factory_root: Path) -> dict[str, dict[str, Any]]:
    catalog_path = personality_template_catalog_path(factory_root)
    schema_errors = validate_json_document(
        catalog_path,
        schema_path(factory_root, "agent-personality-template-catalog.schema.json"),
    )
    if schema_errors:
        raise ValueError("; ".join(schema_errors))

    payload = load_json(catalog_path)
    if not isinstance(payload, dict):
        raise ValueError(f"{catalog_path}: catalog file must contain a JSON object")
    templates = payload.get("templates", [])
    if not isinstance(templates, list):
        raise ValueError(f"{catalog_path}: templates must be an array")

    resolved: dict[str, dict[str, Any]] = {}
    for entry in templates:
        if not isinstance(entry, dict):
            raise ValueError(f"{catalog_path}: template entries must be objects")
        template_id = entry.get("template_id")
        if not isinstance(template_id, str) or not template_id.strip():
            raise ValueError(f"{catalog_path}: template entries must include a non-empty template_id")
        if template_id in resolved:
            raise ValueError(f"{catalog_path}: duplicate personality template_id `{template_id}`")
        resolved[template_id] = cast(dict[str, Any], entry)
    return resolved


def resolve_personality_template(factory_root: Path, template_id: str) -> dict[str, Any]:
    catalog = load_personality_template_catalog(factory_root)
    if template_id in catalog:
        return catalog[template_id]
    available = ", ".join(sorted(catalog)) or "<none>"
    raise ValueError(
        f"{personality_template_catalog_path(factory_root)}: unknown personality template "
        f"`{template_id}`; available templates: {available}"
    )


def load_role_domain_template_catalog(factory_root: Path) -> dict[str, dict[str, Any]]:
    catalog_path = factory_root / ROLE_DOMAIN_TEMPLATE_CATALOG_PATH
    schema_errors = validate_json_document(
        catalog_path,
        schema_path(factory_root, "agent-role-domain-template-catalog.schema.json"),
    )
    if schema_errors:
        raise ValueError("; ".join(schema_errors))

    payload = load_json(catalog_path)
    if not isinstance(payload, dict):
        raise ValueError(f"{catalog_path}: catalog file must contain a JSON object")
    templates = payload.get("templates", [])
    if not isinstance(templates, list):
        raise ValueError(f"{catalog_path}: templates must be an array")

    resolved: dict[str, dict[str, Any]] = {}
    for entry in templates:
        if not isinstance(entry, dict):
            raise ValueError(f"{catalog_path}: template entries must be objects")
        template_id = entry.get("template_id")
        if not isinstance(template_id, str) or not template_id.strip():
            raise ValueError(f"{catalog_path}: template entries must include a non-empty template_id")
        if template_id in resolved:
            raise ValueError(f"{catalog_path}: duplicate role/domain template_id `{template_id}`")
        resolved[template_id] = cast(dict[str, Any], entry)
    return resolved


def resolve_role_domain_template(factory_root: Path, template_id: str) -> dict[str, Any]:
    catalog = load_role_domain_template_catalog(factory_root)
    if template_id in catalog:
        return catalog[template_id]
    available = ", ".join(sorted(catalog)) or "<none>"
    raise ValueError(
        f"{factory_root / ROLE_DOMAIN_TEMPLATE_CATALOG_PATH}: unknown role/domain template "
        f"`{template_id}`; available templates: {available}"
    )


def load_role_domain_template_catalog(factory_root: Path) -> dict[str, dict[str, Any]]:
    catalog_path = factory_root / ROLE_DOMAIN_TEMPLATE_CATALOG_PATH
    schema_errors = validate_json_document(
        catalog_path,
        schema_path(factory_root, "agent-role-domain-template-catalog.schema.json"),
    )
    if schema_errors:
        raise ValueError("; ".join(schema_errors))

    payload = load_json(catalog_path)
    if not isinstance(payload, dict):
        raise ValueError(f"{catalog_path}: catalog file must contain a JSON object")
    templates = payload.get("templates", [])
    if not isinstance(templates, list):
        raise ValueError(f"{catalog_path}: templates must be an array")

    resolved: dict[str, dict[str, Any]] = {}
    for entry in templates:
        if not isinstance(entry, dict):
            raise ValueError(f"{catalog_path}: template entries must be objects")
        template_id = entry.get("template_id")
        if not isinstance(template_id, str) or not template_id.strip():
            raise ValueError(f"{catalog_path}: template entries must include a non-empty template_id")
        if template_id in resolved:
            raise ValueError(f"{catalog_path}: duplicate role/domain template_id `{template_id}`")
        resolved[template_id] = cast(dict[str, Any], entry)
    return resolved


def resolve_role_domain_template(factory_root: Path, template_id: str) -> dict[str, Any]:
    catalog = load_role_domain_template_catalog(factory_root)
    if template_id in catalog:
        return catalog[template_id]
    available = ", ".join(sorted(catalog)) or "<none>"
    raise ValueError(
        f"{factory_root / ROLE_DOMAIN_TEMPLATE_CATALOG_PATH}: unknown role/domain template "
        f"`{template_id}`; available templates: {available}"
    )


def validate_schema_file(schema_path_: Path) -> list[str]:
    if validator_for is None or FormatChecker is None:
        return ["jsonschema is required for schema validation"]
    schema = load_json(schema_path_)
    if not isinstance(schema, dict):
        return [f"{schema_path_}: schema file must contain a JSON object"]
    try:
        _validator_for_schema(cast(dict[str, Any], schema))
    except Exception as exc:
        return [f"{schema_path_}: invalid schema: {exc}"]
    return []


def existing_relative_file(root: Path, relative_path: str | None) -> bool:
    if relative_path is None:
        return False
    return (root / relative_path).exists()


def existing_relative_files(root: Path, relative_paths: Sequence[str]) -> list[str]:
    return [relative_path for relative_path in relative_paths if (root / relative_path).exists()]


def path_is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def pack_state_file(pack_root: Path, relative_path: Path) -> Path:
    return pack_root / relative_path


def read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def find_registry_entry(registry_path: Path, pack_id: str) -> tuple[dict[str, Any], int] | None:
    registry, entries = _load_registry_entries(registry_path)
    for index, entry in enumerate(entries):
        if entry.get("pack_id") == pack_id:
            return registry, index
    return None


def scan_deployment_pointer_paths(factory_root: Path, pack_id: str) -> list[Path]:
    matches: list[Path] = []
    for environment in DEPLOYMENT_ENVIRONMENTS:
        pointer = factory_root / "deployments" / environment / f"{pack_id}.json"
        if pointer.exists():
            matches.append(pointer)
    return matches


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _canonical_pointer_relative_path(environment: str, pack_id: str) -> str:
    return f"deployments/{environment}/{pack_id}.json"


def _find_matching_promotion_event(
    promotion_log: dict[str, Any],
    *,
    promotion_id: str,
    pack_id: str,
    environment: str,
    report_relative_path: str,
) -> dict[str, Any]:
    events = promotion_log.get("events", [])
    if not isinstance(events, list):
        raise ValueError(f"{PROMOTION_LOG_PATH}: events must be an array")
    matches = [
        event
        for event in events
        if isinstance(event, dict)
        and event.get("event_type") == "promoted"
        and event.get("promotion_id") == promotion_id
        and event.get("build_pack_id") == pack_id
        and event.get("target_environment") == environment
        and event.get("promotion_report_path") == report_relative_path
    ]
    if len(matches) != 1:
        raise ValueError(
            f"canonical promotion evidence is inconsistent for {environment}: "
            f"expected exactly one matching promoted event for {pack_id}"
        )
    return cast(dict[str, Any], matches[0])


def _validate_pointer_assignment(
    factory_root: Path,
    environment: str,
    pointer_path: Path,
) -> EnvironmentAssignment:
    pointer_relative_path = relative_path(factory_root, pointer_path)
    pointer_payload = _load_object(pointer_path)
    pack_id = maybe_string(pointer_payload.get("pack_id"))
    if not pack_id:
        raise ValueError(f"{pointer_relative_path}: pack_id is required")
    if pointer_payload.get("environment") != environment:
        raise ValueError(
            f"{pointer_relative_path}: pointer environment does not match target environment {environment}"
        )
    expected_pointer_relative_path = _canonical_pointer_relative_path(environment, pack_id)
    if pointer_relative_path != expected_pointer_relative_path:
        raise ValueError(
            f"{pointer_relative_path}: pointer path does not match canonical environment assignment"
        )

    location = discover_pack(factory_root, pack_id)
    if location.pack_kind != "build_pack":
        raise ValueError(f"{pack_id} is not a build_pack")

    deployment_relative_path = f"build-packs/{pack_id}/status/deployment.json"
    if pointer_payload.get("source_deployment_file") != deployment_relative_path:
        raise ValueError(
            f"{pointer_relative_path}: source_deployment_file does not match canonical deployment path"
        )
    deployment_path = location.pack_root / "status/deployment.json"
    deployment_payload = _load_object(deployment_path)
    if deployment_payload.get("deployment_state") != environment:
        raise ValueError(
            f"{relative_path(factory_root, deployment_path)}: deployment_state does not match {environment}"
        )
    if deployment_payload.get("active_environment") != environment:
        raise ValueError(
            f"{relative_path(factory_root, deployment_path)}: active_environment does not match {environment}"
        )
    if deployment_payload.get("deployment_pointer_path") != pointer_relative_path:
        raise ValueError(
            f"{relative_path(factory_root, deployment_path)}: deployment_pointer_path does not match {pointer_relative_path}"
        )
    if deployment_payload.get("active_release_id") != pointer_payload.get("active_release_id"):
        raise ValueError(
            f"{relative_path(factory_root, deployment_path)}: active_release_id does not match deployment pointer"
        )

    registry = _load_object(factory_root / REGISTRY_BUILD_PATH)
    entries = registry.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError(f"{REGISTRY_BUILD_PATH}: entries must be an array")
    registry_index = location.registry_index
    registry_entry = dict(entries[registry_index])
    if registry_entry.get("deployment_state") != environment:
        raise ValueError(f"{REGISTRY_BUILD_PATH}: {pack_id} deployment_state does not match {environment}")
    if registry_entry.get("deployment_pointer") != pointer_relative_path:
        raise ValueError(f"{REGISTRY_BUILD_PATH}: {pack_id} deployment_pointer does not match {pointer_relative_path}")
    if registry_entry.get("active_release_id") != pointer_payload.get("active_release_id"):
        raise ValueError(f"{REGISTRY_BUILD_PATH}: {pack_id} active_release_id does not match deployment pointer")

    promotion_id = maybe_string(pointer_payload.get("deployment_transaction_id"))
    report_relative_path = maybe_string(pointer_payload.get("promotion_evidence_ref"))
    if not promotion_id or not report_relative_path:
        raise ValueError(f"{pointer_relative_path}: promotion evidence references are incomplete")
    promotion_log = _load_object(factory_root / PROMOTION_LOG_PATH)
    promotion_event = _find_matching_promotion_event(
        promotion_log,
        promotion_id=promotion_id,
        pack_id=pack_id,
        environment=environment,
        report_relative_path=report_relative_path,
    )
    promotion_report_path = location.pack_root / report_relative_path
    if not promotion_report_path.exists():
        raise ValueError(
            f"{pointer_relative_path}: promotion report is missing at {relative_path(factory_root, promotion_report_path)}"
        )
    promotion_report = _load_object(promotion_report_path)
    if promotion_report.get("promotion_id") != promotion_id:
        raise ValueError(f"{relative_path(factory_root, promotion_report_path)}: promotion_id does not match pointer")
    if promotion_report.get("build_pack_id") != pack_id:
        raise ValueError(f"{relative_path(factory_root, promotion_report_path)}: build_pack_id does not match pointer")
    if promotion_report.get("target_environment") != environment:
        raise ValueError(
            f"{relative_path(factory_root, promotion_report_path)}: target_environment does not match pointer"
        )
    if promotion_report.get("release_id") != pointer_payload.get("active_release_id"):
        raise ValueError(f"{relative_path(factory_root, promotion_report_path)}: release_id does not match pointer")
    post_state = promotion_report.get("post_promotion_state")
    if not isinstance(post_state, dict):
        raise ValueError(
            f"{relative_path(factory_root, promotion_report_path)}: post_promotion_state must be an object"
        )
    if post_state.get("deployment_pointer_path") != pointer_relative_path:
        raise ValueError(
            f"{relative_path(factory_root, promotion_report_path)}: post_promotion_state.deployment_pointer_path does not match pointer"
        )

    return EnvironmentAssignment(
        environment=environment,
        pack_id=pack_id,
        pointer_path=pointer_path,
        pointer_relative_path=pointer_relative_path,
        pointer_payload=pointer_payload,
        deployment_path=deployment_path,
        deployment_payload=deployment_payload,
        registry_index=registry_index,
        registry_entry=registry_entry,
        promotion_event=promotion_event,
        promotion_report_path=promotion_report_path,
        promotion_report_relative_path=report_relative_path,
        promotion_report=promotion_report,
    )


def discover_environment_assignment(factory_root: Path, environment: str) -> EnvironmentAssignment | None:
    deployment_dir = factory_root / "deployments" / environment
    pointer_paths = sorted(deployment_dir.glob("*.json")) if deployment_dir.exists() else []
    registry = _load_object(factory_root / REGISTRY_BUILD_PATH)
    entries = registry.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError(f"{REGISTRY_BUILD_PATH}: entries must be an array")

    if len(pointer_paths) > 1:
        raise ValueError(
            f"inconsistent current assignee state for {environment}: multiple deployment pointers exist"
        )
    if len(pointer_paths) == 1:
        assignment = _validate_pointer_assignment(factory_root, environment, pointer_paths[0])
        registry_claims: list[str] = []
        pack_claims: list[str] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if entry.get("pack_kind") != "build_pack":
                continue
            pack_id = maybe_string(entry.get("pack_id"))
            if not pack_id or pack_id == assignment.pack_id:
                continue
            expected_pointer_relative_path = _canonical_pointer_relative_path(environment, pack_id)
            if (
                entry.get("deployment_state") == environment
                or entry.get("deployment_pointer") == expected_pointer_relative_path
            ):
                registry_claims.append(pack_id)

            deployment_path = factory_root / "build-packs" / pack_id / "status/deployment.json"
            if not deployment_path.exists():
                continue
            deployment_payload = _load_object(deployment_path)
            if (
                deployment_payload.get("deployment_state") == environment
                or deployment_payload.get("active_environment") == environment
                or deployment_payload.get("deployment_pointer_path") == expected_pointer_relative_path
            ):
                pack_claims.append(pack_id)
        if registry_claims or pack_claims:
            problems: list[str] = []
            if registry_claims:
                problems.append(f"registry claims: {', '.join(sorted(set(registry_claims)))}")
            if pack_claims:
                problems.append(f"pack-local claims: {', '.join(sorted(set(pack_claims)))}")
            raise ValueError(
                f"inconsistent current assignee state for {environment}: "
                f"{assignment.pack_id} owns the deployment pointer but other packs also claim the environment; "
                + "; ".join(problems)
            )
        return assignment

    registry_claims: list[str] = []
    pack_claims: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("pack_kind") != "build_pack":
            continue
        pack_id = maybe_string(entry.get("pack_id"))
        if not pack_id:
            continue
        expected_pointer_relative_path = _canonical_pointer_relative_path(environment, pack_id)
        if entry.get("deployment_state") == environment or entry.get("deployment_pointer") == expected_pointer_relative_path:
            registry_claims.append(pack_id)

        pack_root = factory_root / "build-packs" / pack_id
        deployment_path = pack_root / "status/deployment.json"
        if not deployment_path.exists():
            continue
        deployment_payload = _load_object(deployment_path)
        if (
            deployment_payload.get("deployment_state") == environment
            or deployment_payload.get("active_environment") == environment
            or deployment_payload.get("deployment_pointer_path") == expected_pointer_relative_path
        ):
            pack_claims.append(pack_id)

    if registry_claims or pack_claims:
        problems: list[str] = []
        if registry_claims:
            problems.append(f"registry claims: {', '.join(sorted(set(registry_claims)))}")
        if pack_claims:
            problems.append(f"pack-local claims: {', '.join(sorted(set(pack_claims)))}")
        raise ValueError(
            f"inconsistent current assignee state for {environment}: no deployment pointer exists but "
            + "; ".join(problems)
        )

    return None


def maybe_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return None


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def sorted_unique(paths: Iterable[str]) -> list[str]:
    return sorted(set(paths))


def registry_entry_copy(registry: dict[str, Any], index: int) -> dict[str, Any]:
    entries = cast(list[dict[str, Any]], registry["entries"])
    return dict(entries[index])


def update_registry_entry(registry: dict[str, Any], index: int, updated_entry: Mapping[str, Any]) -> None:
    entries = cast(list[dict[str, Any]], registry["entries"])
    entries[index] = dict(updated_entry)


def load_existing_report(report_path: Path) -> dict[str, Any] | None:
    if not report_path.exists():
        return None
    payload = load_json(report_path)
    if not isinstance(payload, dict):
        raise ValueError(f"{report_path}: retirement report must contain a JSON object")
    return cast(dict[str, Any], payload)
