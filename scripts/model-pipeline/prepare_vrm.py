from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import blender_arguments, enable_addons  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Assign VRM humanoid bones and export a prepared avatar")
    parser.add_argument("--input", required=True)
    parser.add_argument("--prepared", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(blender_arguments())
    input_path = Path(args.input).expanduser().resolve()
    prepared_path = Path(args.prepared).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    prepared_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.open_mainfile(filepath=str(input_path))
    enable_addons(bpy, "bl_ext.blender_org.mmd_tools", "bl_ext.blender_org.vrm")
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"Expected one armature, found {len(armatures)}")
    armature = armatures[0]
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)

    assign_result = bpy.ops.vrm.assign_vrm1_humanoid_human_bones_automatically(
        armature_object_name=armature.name
    )
    extension = armature.data.vrm_addon_extension
    human_bones = extension.vrm1.humanoid.human_bones
    mapping = human_bones.human_bone_name_to_human_bone()
    assigned = {
        str(name): bone.node.bone_name
        for name, bone in mapping.items()
        if bone.node.bone_name
    }
    print("AUTO_ASSIGN_RESULT", assign_result)
    print("HUMANOID", {"assigned": len(assigned), "valid": human_bones.bones_are_correctly_assigned(), "mapping": assigned})

    export_result = bpy.ops.export_scene.vrm(
        filepath=str(output_path),
        armature_object_name=armature.name,
        use_addon_preferences=False,
        export_invisibles=False,
        export_only_selections=False,
        enable_advanced_preferences=False,
        export_all_influences=False,
        export_lights=False,
        export_gltf_animations=False,
        export_try_sparse_sk=True,
        ignore_warning=True,
    )
    if not output_path.is_file():
        raise RuntimeError("VRM exporter did not create the output file")
    print("EXPORT_RESULT", export_result, "BYTES", output_path.stat().st_size)
    bpy.ops.wm.save_as_mainfile(filepath=str(prepared_path))
    print("SAVED", prepared_path)


if __name__ == "__main__":
    main()
