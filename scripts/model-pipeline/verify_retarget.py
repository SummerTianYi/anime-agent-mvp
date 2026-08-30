from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import blender_arguments  # noqa: E402


REQUIRED_BONES = (
    "センター",
    "上半身",
    "上半身2",
    "首",
    "頭",
    "肩.L",
    "腕.L",
    "ひじ.L",
    "手首.L",
    "肩.R",
    "腕.R",
    "ひじ.R",
    "手首.R",
    "足.L",
    "ひざ.L",
    "足首.L",
    "足.R",
    "ひざ.R",
    "足首.R",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify a grounded humanoid retarget Blend")
    parser.add_argument("--input", required=True)
    parser.add_argument("--action", default="cmu_pirouette")
    parser.add_argument("--ground-tolerance", type=float, default=0.001)
    parser.add_argument("--require-loop", action="store_true")
    parser.add_argument("--loop-tolerance", type=float, default=0.00001)
    return parser.parse_args(blender_arguments())


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    bpy.ops.wm.open_mainfile(filepath=str(input_path))

    target = next(
        (
            obj
            for obj in bpy.context.scene.objects
            if obj.type == "ARMATURE" and all(name in obj.data.bones for name in REQUIRED_BONES)
        ),
        None,
    )
    if target is None:
        raise RuntimeError("Could not find the target humanoid armature")
    action = bpy.data.actions.get(args.action)
    if action is None or target.animation_data is None or target.animation_data.action != action:
        raise RuntimeError(f"Target does not have active action {args.action!r}")

    start_frame = int(round(action.frame_range[0]))
    end_frame = int(round(action.frame_range[1]))
    reference_ground = None
    maximum_ground_deviation = 0.0
    first_pose = None
    last_pose = None
    for frame in range(start_frame, end_frame + 1):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        ground = min(target.pose.bones[name].tail.z for name in ("足首.L", "足首.R"))
        if reference_ground is None:
            reference_ground = ground
        maximum_ground_deviation = max(maximum_ground_deviation, abs(ground - reference_ground))
        for bone_name in REQUIRED_BONES:
            matrix_values = [value for row in target.pose.bones[bone_name].matrix for value in row]
            if not all(math.isfinite(value) for value in matrix_values):
                raise RuntimeError(f"Non-finite pose matrix at frame {frame}, bone {bone_name}")
        sampled_pose = {
            bone_name: tuple(value for row in target.pose.bones[bone_name].matrix for value in row)
            for bone_name in REQUIRED_BONES
        }
        if frame == start_frame:
            first_pose = sampled_pose
        if frame == end_frame:
            last_pose = sampled_pose

    if maximum_ground_deviation > args.ground_tolerance:
        raise RuntimeError(
            f"Foot-ground deviation {maximum_ground_deviation:.6f} exceeds "
            f"tolerance {args.ground_tolerance:.6f}"
        )
    maximum_loop_deviation = 0.0
    if args.require_loop:
        maximum_loop_deviation = max(
            abs(first_pose[bone_name][index] - last_pose[bone_name][index])
            for bone_name in REQUIRED_BONES
            for index in range(16)
        )
        if maximum_loop_deviation > args.loop_tolerance:
            raise RuntimeError(
                f"Loop pose deviation {maximum_loop_deviation:.8f} exceeds "
                f"tolerance {args.loop_tolerance:.8f}"
            )
    mesh = next(
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH"
        and any(modifier.type == "ARMATURE" and modifier.object == target for modifier in obj.modifiers)
    )
    report = {
        "input": str(input_path),
        "action": action.name,
        "frames": end_frame - start_frame + 1,
        "fps": bpy.context.scene.render.fps / bpy.context.scene.render.fps_base,
        "required_bones": len(REQUIRED_BONES),
        "target_bones": len(target.data.bones),
        "shape_keys": len(mesh.data.shape_keys.key_blocks) if mesh.data.shape_keys else 0,
        "ground_height": reference_ground,
        "maximum_ground_deviation": maximum_ground_deviation,
        "maximum_loop_deviation": maximum_loop_deviation,
    }
    print("RETARGET_VERIFY_OK", json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
