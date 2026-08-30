from __future__ import annotations

import argparse
import json
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
    meshes = [
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH"
        and any(
            modifier.type == "ARMATURE" and modifier.object == armature
            for modifier in obj.modifiers
        )
    ]
    chain_names: dict[str, list[str]] = {}
    for side in ("R", "L"):
        side_names: list[str] = []
        for index in range(17):
            name = f"MaWei_{side}_{index}_1"
            bone = armature.data.bones.get(name)
            if bone is None:
                continue
            side_names.append(name)
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
        chain_names[side] = side_names

    missing = {
        side: [f"MaWei_{side}_{index}_1" for index in range(17) if f"MaWei_{side}_{index}_1" not in names]
        for side, names in chain_names.items()
    }
    continuity_errors: list[str] = []
    for side, names in chain_names.items():
        for index, name in enumerate(names):
            expected_parent = "首" if index == 0 else names[index - 1]
            parent = armature.data.bones[name].parent
            if parent is None or parent.name != expected_parent:
                continuity_errors.append(
                    f"{name}: expected parent {expected_parent}, got {parent.name if parent else None}"
                )

    weight_summary: dict[str, dict[str, float | int]] = {}
    for names in chain_names.values():
        for name in names:
            influenced_vertices = 0
            total_weight = 0.0
            maximum_weight = 0.0
            meshes_with_group = 0
            for mesh in meshes:
                group = mesh.vertex_groups.get(name)
                if group is None:
                    continue
                meshes_with_group += 1
                for vertex in mesh.data.vertices:
                    for assignment in vertex.groups:
                        if assignment.group != group.index or assignment.weight <= 0.0:
                            continue
                        influenced_vertices += 1
                        total_weight += assignment.weight
                        maximum_weight = max(maximum_weight, assignment.weight)
                        break
            weight_summary[name] = {
                "meshes": meshes_with_group,
                "vertices": influenced_vertices,
                "total_weight": round(total_weight, 6),
                "maximum_weight": round(maximum_weight, 6),
            }

    unweighted = [name for name, summary in weight_summary.items() if summary["vertices"] == 0]
    result = {
        "armature": armature.name,
        "deformed_meshes": [mesh.name for mesh in meshes],
        "chain_lengths": {side: len(names) for side, names in chain_names.items()},
        "roots": {side: names[0] if names else None for side, names in chain_names.items()},
        "missing": missing,
        "continuity_errors": continuity_errors,
        "unweighted_bones": unweighted,
        "weight_summary": weight_summary,
    }
    if any(missing.values()) or continuity_errors or unweighted:
        raise RuntimeError(f"Pigtail validation failed: {json.dumps(result, ensure_ascii=False)}")
    print("PIGTAIL_INSPECTION_OK", json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
