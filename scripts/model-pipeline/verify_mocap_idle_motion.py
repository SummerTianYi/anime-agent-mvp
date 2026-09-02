from __future__ import annotations

"""Validate the Codex-owned monocular idle clip before local runtime replacement."""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import blender_arguments  # noqa: E402


CONTROLLED_BONES = (
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
)
LOWER_BODY_TOKENS = ("下半身", "足.", "ひざ.", "足首.", "つま先.", "スカート")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify a looping monocular idle Blend")
    parser.add_argument("--input", required=True)
    parser.add_argument("--action", default="idle_mocap_v1")
    parser.add_argument("--loop-tolerance", type=float, default=0.00001)
    parser.add_argument("--maximum-step-radians", type=float, default=0.08)
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
            if obj.type == "ARMATURE" and all(name in obj.data.bones for name in CONTROLLED_BONES)
        ),
        None,
    )
    if target is None:
        raise RuntimeError("Could not find the target humanoid armature")
    action = bpy.data.actions.get(args.action)
    if action is None or target.animation_data is None or target.animation_data.action != action:
        raise RuntimeError(f"Target does not have active action {args.action!r}")

    groups = {curve.group.name for curve in action.fcurves if curve.group is not None}
    unexpected_groups = sorted(groups - set(CONTROLLED_BONES))
    if unexpected_groups:
        raise RuntimeError(f"Unexpected animated bone groups: {unexpected_groups}")
    forbidden_curves = [
        curve.data_path
        for curve in action.fcurves
        if "scale" in curve.data_path
        or "location" in curve.data_path
        or any(token in curve.data_path for token in LOWER_BODY_TOKENS)
    ]
    if forbidden_curves:
        raise RuntimeError(f"Idle contains forbidden transform tracks: {forbidden_curves[:5]}")

    start_frame = int(round(action.frame_range[0]))
    end_frame = int(round(action.frame_range[1]))
    first_pose = None
    last_pose = None
    previous_rotations = None
    maximum_step = 0.0
    chest_start = None
    head_start = None
    maximum_chest_delta = 0.0
    maximum_head_delta = 0.0
    for frame in range(start_frame, end_frame + 1):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        rotations = {
            name: target.pose.bones[name].matrix.to_quaternion().normalized()
            for name in CONTROLLED_BONES
        }
        matrices = {
            name: tuple(value for row in target.pose.bones[name].matrix for value in row)
            for name in CONTROLLED_BONES
        }
        if not all(math.isfinite(value) for values in matrices.values() for value in values):
            raise RuntimeError(f"Non-finite pose matrix at frame {frame}")
        if previous_rotations is not None:
            maximum_step = max(
                maximum_step,
                max(
                    min(
                        previous_rotations[name].rotation_difference(rotations[name]).angle,
                        2.0
                        * math.pi
                        - previous_rotations[name].rotation_difference(rotations[name]).angle,
                    )
                    for name in CONTROLLED_BONES
                ),
            )
        previous_rotations = rotations
        if frame == start_frame:
            first_pose = matrices
            chest_start = rotations["上半身2"]
            head_start = rotations["頭"]
        maximum_chest_delta = max(
            maximum_chest_delta,
            chest_start.rotation_difference(rotations["上半身2"]).angle,
        )
        maximum_head_delta = max(
            maximum_head_delta,
            head_start.rotation_difference(rotations["頭"]).angle,
        )
        if frame == end_frame:
            last_pose = matrices

    maximum_loop_deviation = max(
        abs(first_pose[name][index] - last_pose[name][index])
        for name in CONTROLLED_BONES
        for index in range(16)
    )
    if maximum_loop_deviation > args.loop_tolerance:
        raise RuntimeError(
            f"Loop deviation {maximum_loop_deviation:.8f} exceeds {args.loop_tolerance:.8f}"
        )
    if maximum_step > args.maximum_step_radians:
        raise RuntimeError(
            f"Per-frame rotation step {maximum_step:.6f} exceeds {args.maximum_step_radians:.6f}"
        )
    if maximum_chest_delta < math.radians(0.5):
        raise RuntimeError("Chest motion is too small to constitute a captured idle")
    if maximum_head_delta < math.radians(3.0):
        raise RuntimeError("Head motion is too small to preserve the captured glance")
    if maximum_chest_delta > math.radians(15.0) or maximum_head_delta > math.radians(40.0):
        raise RuntimeError("Captured idle exceeds the conservative desktop-motion envelope")

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
        "controlled_bones": len(CONTROLLED_BONES),
        "target_bones": len(target.data.bones),
        "shape_keys": len(mesh.data.shape_keys.key_blocks) if mesh.data.shape_keys else 0,
        "maximum_loop_deviation": maximum_loop_deviation,
        "maximum_step_radians": maximum_step,
        "maximum_chest_delta_degrees": math.degrees(maximum_chest_delta),
        "maximum_head_delta_degrees": math.degrees(maximum_head_delta),
    }
    print("MOCAP_IDLE_VERIFY_OK", json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
