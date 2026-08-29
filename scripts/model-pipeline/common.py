from __future__ import annotations

import sys
from typing import Any


def blender_arguments() -> list[str]:
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def enable_addons(bpy: Any, *modules: str) -> None:
    for module in modules:
        result = bpy.ops.preferences.addon_enable(module=module)
        print("ENABLE", module, result)
