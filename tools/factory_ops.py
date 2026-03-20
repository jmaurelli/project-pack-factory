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
