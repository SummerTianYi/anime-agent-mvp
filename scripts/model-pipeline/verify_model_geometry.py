from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import blender_arguments  # noqa: E402


def _hash_floats(digest: Any, values: Any) -> None:
    for value in values:
        digest.update(struct.pack("<d", float(value)))


def _mesh_digest(mesh_object: bpy.types.Object) -> str:
    digest = hashlib.sha256()
    mesh = mesh_object.data
    for vertex in mesh.vertices:
        _hash_floats(digest, vertex.co)
    for polygon in mesh.polygons:
        digest.update(struct.pack("<I", len(polygon.vertices)))
        for vertex_index in polygon.vertices:
            digest.update(struct.pack("<I", vertex_index))
    if mesh.shape_keys is not None:
        for key_block in mesh.shape_keys.key_blocks:
            digest.update(key_block.name.encode("utf-8"))
            for point in key_block.data:
                _hash_floats(digest, point.co)
    return digest.hexdigest()


def _armature_digest(armature_object: bpy.types.Object) -> str:
    digest = hashlib.sha256()
    for bone in sorted(armature_object.data.bones, key=lambda item: item.name):
        digest.update(bone.name.encode("utf-8"))
        digest.update((bone.parent.name if bone.parent else "").encode("utf-8"))
        _hash_floats(digest, bone.head_local)
        _hash_floats(digest, bone.tail_local)
        for row in bone.matrix_local:
            _hash_floats(digest, row)
    return digest.hexdigest()


def _rounded(values: Any) -> list[float]:
    return [round(float(value), 9) for value in values]


def _snapshot(path: Path) -> dict[str, Any]:
    bpy.ops.wm.open_mainfile(filepath=str(path))
    meshes = sorted((obj for obj in bpy.data.objects if obj.type == "MESH"), key=lambda obj: obj.name)
    armatures = sorted((obj for obj in bpy.data.objects if obj.type == "ARMATURE"), key=lambda obj: obj.name)
    if not meshes or not armatures:
        raise RuntimeError(f"Expected mesh and armature objects in {path}")

    world_corners: list[Vector] = []
    mesh_summary: dict[str, Any] = {}
    for mesh_object in meshes:
        corners = [mesh_object.matrix_world @ Vector(corner) for corner in mesh_object.bound_box]
        world_corners.extend(corners)
        shape_key_count = (
            max(len(mesh_object.data.shape_keys.key_blocks) - 1, 0)
            if mesh_object.data.shape_keys is not None
            else 0
        )
        mesh_summary[mesh_object.name] = {
            "vertices": len(mesh_object.data.vertices),
            "polygons": len(mesh_object.data.polygons),
            "shape_keys": shape_key_count,
            "dimensions": _rounded(mesh_object.dimensions),
            "matrix_world": [_rounded(row) for row in mesh_object.matrix_world],
            "geometry_sha256": _mesh_digest(mesh_object),
        }

    minimum = [min(corner[axis] for corner in world_corners) for axis in range(3)]
    maximum = [max(corner[axis] for corner in world_corners) for axis in range(3)]
    return {
        "meshes": mesh_summary,
        "armatures": {
            armature.name: {
                "bones": len(armature.data.bones),
                "matrix_world": [_rounded(row) for row in armature.matrix_world],
                "rest_pose_sha256": _armature_digest(armature),
            }
            for armature in armatures
        },
        "world_bounds": {
            "minimum": _rounded(minimum),
            "maximum": _rounded(maximum),
            "dimensions": _rounded(maximum[axis] - minimum[axis] for axis in range(3)),
        },
    }


def _snapshot_digest(snapshot: dict[str, Any]) -> str:
    payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    meshes = snapshot["meshes"]
    largest_mesh_name = max(meshes, key=lambda name: meshes[name]["vertices"])
    return {
        "geometry_snapshot_sha256": _snapshot_digest(snapshot),
        "mesh_objects": len(meshes),
        "total_vertices": sum(mesh["vertices"] for mesh in meshes.values()),
        "total_polygons": sum(mesh["polygons"] for mesh in meshes.values()),
        "total_shape_keys": sum(mesh["shape_keys"] for mesh in meshes.values()),
        "largest_mesh": {"name": largest_mesh_name, **meshes[largest_mesh_name]},
        "armatures": snapshot["armatures"],
        "world_bounds": snapshot["world_bounds"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify that a candidate Blend keeps the baseline mesh, shape-key, rig, transform and bounds geometry"
    )
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    args = parser.parse_args(blender_arguments())
    baseline_path = Path(args.baseline).expanduser().resolve()
    candidate_path = Path(args.candidate).expanduser().resolve()
    for path in (baseline_path, candidate_path):
        if not path.is_file():
            raise FileNotFoundError(path)

    baseline = _snapshot(baseline_path)
    candidate = _snapshot(candidate_path)
    if baseline != candidate:
        baseline_meshes = baseline["meshes"]
        candidate_meshes = candidate["meshes"]
        mesh_names = set(baseline_meshes) | set(candidate_meshes)
        changed_meshes = sorted(
            name for name in mesh_names if baseline_meshes.get(name) != candidate_meshes.get(name)
        )
        raise RuntimeError(
            "MODEL_GEOMETRY_CHANGED "
            + json.dumps(
                {
                    "baseline": _summary(baseline),
                    "candidate": _summary(candidate),
                    "changed_mesh_count": len(changed_meshes),
                    "changed_meshes_first_20": changed_meshes[:20],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    print(
        "MODEL_GEOMETRY_PARITY_OK",
        json.dumps(
            {
                "baseline": str(baseline_path),
                "candidate": str(candidate_path),
                "geometry": _summary(candidate),
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
    )


if __name__ == "__main__":
    main()
