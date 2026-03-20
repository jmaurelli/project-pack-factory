from __future__ import annotations

from .__about__ import DISTRIBUTION_NAME, MODULE_NAME, PACKAGE_NAME, SCAFFOLD_VERSION
from .version import __version__


def get_package_metadata() -> dict[str, str]:
    return {
        "package_name": PACKAGE_NAME,
        "module_name": MODULE_NAME,
        "distribution_name": DISTRIBUTION_NAME,
        "scaffold_version": SCAFFOLD_VERSION,
        "version": __version__,
    }
