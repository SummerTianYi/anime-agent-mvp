from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import blender_arguments, enable_addons  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Import an authorized MMD PMX into Blender")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--scale", type=float, default=0.08)
    args = parser.parse_args(blender_arguments())
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    enable_addons(bpy, "bl_ext.blender_org.mmd_tools", "bl_ext.blender_org.vrm")
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    result = bpy.ops.mmd_tools.import_model(
        filepath=str(input_path),
        types={"MESH", "ARMATURE", "PHYSICS", "DISPLAY", "MORPHS"},
        scale=args.scale,
        clean_model=True,
        remove_doubles=False,
        import_adduv2_as_vertex_colors=False,
        fix_bone_order=True,
        fix_ik_links=False,
        ik_loop_factor=5,
        apply_bone_fixed_axis=False,
        rename_bones=True,
        use_underscore=False,
        use_mipmap=True,
        sph_blend_factor=1.0,
        spa_blend_factor=1.0,
        log_level="INFO",
    )
    objects = list(bpy.context.scene.objects)
    meshes = [obj for obj in objects if obj.type == "MESH"]
    armatures = [obj for obj in objects if obj.type == "ARMATURE"]
    shape_keys = sum(
        len(obj.data.shape_keys.key_blocks) - 1
        for obj in meshes
        if obj.data.shape_keys
    )
    print("IMPORT_RESULT", result)
    print("SUMMARY", {"objects": len(objects), "meshes": len(meshes), "armatures": len(armatures), "shape_keys": shape_keys})
    bpy.ops.wm.save_as_mainfile(filepath=str(output_path))
    print("SAVED", output_path)


if __name__ == "__main__":
    main()
