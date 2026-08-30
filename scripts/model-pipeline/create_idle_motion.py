from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import blender_arguments  # noqa: E402
from retarget_bvh import export_animated_glb, one_armature, reset_pose  # noqa: E402


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


IDLE_POSES = (
    # frame, torso, chest, neck, head, shoulder, arm_sway, elbow, wrist
    (1, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 0.0, 0.0, 4.0, 0.0),
    (61, (0.15, 0.0, 0.25), (-1.1, 0.0, 0.35), (0.35, 0.0, -0.25), (-0.45, 0.0, 0.35), 0.4, 0.7, 4.8, 0.7),
    (121, (0.0, 0.0, -0.25), (0.2, 0.0, -0.35), (0.0, 1.1, 0.45), (0.15, 1.8, 0.75), 0.0, -0.25, 4.0, -0.4),
    (181, (-0.1, 0.0, 0.2), (0.75, 0.0, 0.25), (-0.25, -0.65, -0.55), (0.35, -1.2, -0.9), -0.3, -0.55, 3.5, -0.3),
    (241, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 0.0, 0.0, 4.0, 0.0),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a subtle looping idle animation on the prepared Luo Tianyi rig"
    )
    parser.add_argument("--target", required=True)
    parser.add_argument("--output-blend", required=True)
    parser.add_argument("--output-glb", required=True)
    parser.add_argument("--action-name", default="idle_breathing")
    parser.add_argument("--fps", type=int, default=30)
    return parser.parse_args(blender_arguments())


def euler_offset(degrees_xyz: tuple[float, float, float]) -> Quaternion:
    x, y, z = (math.radians(value) for value in degrees_xyz)
    return (
        Quaternion(Vector((1.0, 0.0, 0.0)), x)
        @ Quaternion(Vector((0.0, 1.0, 0.0)), y)
        @ Quaternion(Vector((0.0, 0.0, 1.0)), z)
    )


def set_rotation(
    target: bpy.types.Object,
    bone_name: str,
    frame: int,
    degrees_xyz: tuple[float, float, float],
) -> None:
    pose_bone = target.pose.bones[bone_name]
    pose_bone.rotation_mode = "QUATERNION"
    pose_bone.rotation_quaternion = euler_offset(degrees_xyz)
    pose_bone.keyframe_insert(
        data_path="rotation_quaternion",
        frame=frame,
        group=bone_name,
    )


def create_idle_action(
    target: bpy.types.Object,
    action_name: str,
    fps: int,
) -> bpy.types.Action:
    if target.animation_data is None:
        target.animation_data_create()
    target.animation_data.action = None
    existing_action = bpy.data.actions.get(action_name)
    if existing_action is not None:
        bpy.data.actions.remove(existing_action)
    action = bpy.data.actions.new(action_name)
    target.animation_data.action = action

    for pose_bone in target.pose.bones:
        for constraint in pose_bone.constraints:
            constraint.mute = True
    reset_pose(target)
    bpy.context.view_layer.update()

    for frame, torso, chest, neck, head, shoulder, arm_sway, elbow, wrist in IDLE_POSES:
        set_rotation(target, "上半身", frame, torso)
        set_rotation(target, "上半身2", frame, chest)
        set_rotation(target, "首", frame, neck)
        set_rotation(target, "頭", frame, head)
        set_rotation(target, "肩.L", frame, (0.0, 0.0, shoulder))
        set_rotation(target, "肩.R", frame, (0.0, 0.0, -shoulder))
        set_rotation(target, "腕.L", frame, (48.0 + arm_sway, 0.0, 0.0))
        set_rotation(target, "腕.R", frame, (-48.0 - arm_sway, 0.0, 0.0))
        set_rotation(target, "ひじ.L", frame, (0.0, elbow, 0.0))
        set_rotation(target, "ひじ.R", frame, (0.0, -elbow, 0.0))
        set_rotation(target, "手首.L", frame, (0.0, 0.0, wrist))
        set_rotation(target, "手首.R", frame, (0.0, 0.0, -wrist))

    for curve in action.fcurves:
        for point in curve.keyframe_points:
            point.interpolation = "BEZIER"
            point.handle_left_type = "AUTO_CLAMPED"
            point.handle_right_type = "AUTO_CLAMPED"

    bpy.context.scene.render.fps = fps
    bpy.context.scene.render.fps_base = 1.0
    bpy.context.scene.frame_start = IDLE_POSES[0][0]
    bpy.context.scene.frame_end = IDLE_POSES[-1][0]
    action.use_frame_range = True
    action.frame_start = IDLE_POSES[0][0]
    action.frame_end = IDLE_POSES[-1][0]
    bpy.context.scene.frame_set(IDLE_POSES[0][0])
    bpy.context.view_layer.update()
    return action


def main() -> None:
    args = parse_args()
    target_path = Path(args.target).expanduser().resolve()
    output_blend = Path(args.output_blend).expanduser().resolve()
    output_glb = Path(args.output_glb).expanduser().resolve()
    if not target_path.is_file():
        raise FileNotFoundError(target_path)

    bpy.ops.wm.open_mainfile(filepath=str(target_path))
    target = one_armature(list(bpy.context.scene.objects), "target")
    missing_bones = [name for name in CONTROLLED_BONES if name not in target.data.bones]
    if missing_bones:
        raise RuntimeError(f"Idle rig mapping is missing bones: {missing_bones}")
    action = create_idle_action(target, args.action_name, args.fps)

    output_blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_blend))
    mesh = export_animated_glb(target, output_glb)
    report = {
        "action": action.name,
        "frames": int(action.frame_end - action.frame_start + 1),
        "fps": args.fps,
        "duration_seconds": (action.frame_end - action.frame_start) / args.fps,
        "controlled_bones": len(CONTROLLED_BONES),
        "target_bones": len(target.data.bones),
        "shape_keys": len(mesh.data.shape_keys.key_blocks) if mesh.data.shape_keys else 0,
        "output_blend": str(output_blend),
        "output_glb": str(output_glb),
    }
    print("IDLE_MOTION_REPORT", json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
