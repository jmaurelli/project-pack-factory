from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .__about__ import DISTRIBUTION_NAME, __version__


def resolve_version() -> str:
    try:
        return version(DISTRIBUTION_NAME)
    except PackageNotFoundError:
        return __version__
