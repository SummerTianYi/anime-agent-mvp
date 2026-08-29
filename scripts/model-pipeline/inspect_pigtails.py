from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import blender_arguments  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect MaWei pigtail bone chains in a Blend file")
    parser.add_argument("--input", required=True)
    args = parser.parse_args(blender_arguments())
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    bpy.ops.wm.open_mainfile(filepath=str(input_path))
    armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"Expected one armature, found {len(armatures)}")
    armature = armatures[0]
    for side in ("R", "L"):
        for index in range(17):
            name = f"MaWei_{side}_{index}_1"
            bone = armature.data.bones.get(name)
            if bone is None:
                continue
            head = armature.matrix_world @ bone.head_local
            tail = armature.matrix_world @ bone.tail_local
            direction = tail - head
            print(
                "MAWEI",
                name,
                "parent=",
                bone.parent.name if bone.parent else None,
                "head=",
                tuple(round(value, 4) for value in head),
                "tail=",
                tuple(round(value, 4) for value in tail),
                "direction=",
                tuple(round(value, 4) for value in direction),
            )


if __name__ == "__main__":
    main()
