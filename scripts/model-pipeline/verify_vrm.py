from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import blender_arguments, enable_addons  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Import and summarize a VRM avatar")
    parser.add_argument("--input", required=True)
    args = parser.parse_args(blender_arguments())
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.is_file():
        raise FileNotFoundError(input_path)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    enable_addons(bpy, "bl_ext.blender_org.vrm")
    result = bpy.ops.import_scene.vrm(filepath=str(input_path))
    objects = list(bpy.context.scene.objects)
    meshes = [obj for obj in objects if obj.type == "MESH"]
    armatures = [obj for obj in objects if obj.type == "ARMATURE"]
    shape_keys = sum(
        len(obj.data.shape_keys.key_blocks) - 1
        for obj in meshes
        if obj.data.shape_keys
    )
    summary = {"objects": len(objects), "meshes": len(meshes), "armatures": len(armatures), "shape_keys": shape_keys}
    if armatures:
        extension = armatures[0].data.vrm_addon_extension
        summary.update(
            {
                "vrm_spec": str(extension.spec_version),
                "spring_bone_colliders": len(extension.spring_bone1.colliders),
                "spring_bone_collider_groups": len(extension.spring_bone1.collider_groups),
            }
        )
    print("IMPORT_RESULT", result)
    print("VRM_SUMMARY", summary)


if __name__ == "__main__":
    main()
