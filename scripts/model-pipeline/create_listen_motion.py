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


UPPER_BONES = (
    "上半身", "上半身2", "首", "頭",
    "肩.L", "腕.L", "ひじ.L", "手首.L",
    "肩.R", "腕.R", "ひじ.R", "手首.R",
)

FINGER_BONES = (
    "親指０", "親指１",
    "人指１", "人指２",
    "中指１", "中指２",
    "薬指１", "薬指２",
    "小指１", "小指２",
)

CONTROLLED_BONES = UPPER_BONES + tuple(finger + side for side in (".L", ".R") for finger in FINGER_BONES) + ("手捩.R",)

REST_POSE = {
    "上半身": (0.0, 0.0, 0.0),
    "上半身2": (0.0, 0.0, 0.0),
    "首": (0.0, 0.0, 0.0),
    "頭": (0.0, 0.0, 0.0),
    "肩.L": (0.0, 0.0, 0.0),
    "肩.R": (0.0, 0.0, 0.0),
    "腕.L": (48.0, 0.0, 0.0),
    "腕.R": (-48.0, 0.0, 0.0),
    "ひじ.L": (0.0, 4.0, 0.0),
    "ひじ.R": (0.0, -4.0, 0.0),
    "手首.L": (0.0, 0.0, 0.0),
    "手首.R": (0.0, 0.0, 0.0),
}

# 参考帧序列：握拳提示 -> 举手到头侧 -> 张开手掌停住轻摆 -> 前伸挥手收尾。
# 每个姿势只写偏离上一姿势的骨骼；未提到的骨骼沿用上一次关键帧。
POSE_SEQUENCE = (
    (1, REST_POSE),
    (26, {
        "腕.R": (12.0, 0.0, 30.0),
        "ひじ.R": (85.0, 0.0, 0.0),
        "手首.R": (0.0, -8.0, 0.0),
        "__curl.R": 42.0,
        "頭": (3.0, 0.0, 0.0),
        "上半身": (3.0, 0.0, 0.0),
        "上半身2": (2.0, 0.0, 0.0),
    }),
    (52, {
        "腕.R": (15.0, 0.0, 35.0),
        "ひじ.R": (88.0, 0.0, 0.0),
        "__curl.R": 38.0,
        "頭": (0.0, 0.0, -4.0),
        "首": (0.0, 0.0, -2.0),
        "上半身": (2.0, 0.0, 0.0),
        "上半身2": (1.5, 0.0, 0.0),
    }),
    (82, {
        "手捩.R": (0.0, 75.0, 0.0),
        "腕.R": (55.0, 0.0, 12.0),
        "ひじ.R": (95.0, 0.0, 0.0),
        "手首.R": (0.0, 0.0, -4.0),
        "__curl.R": -12.0,
        "頭": (1.0, 0.0, -7.0),
        "首": (0.0, 0.0, -3.0),
        "上半身": (2.0, 0.0, 0.0),
        "上半身2": (1.0, 0.0, 0.0),
    }),
    (112, {
        "手捩.R": (0.0, 75.0, 0.0),
        "腕.R": (58.0, 0.0, 14.0),
        "ひじ.R": (98.0, 0.0, 0.0),
        "手首.R": (0.0, 0.0, -4.0),
        "__curl.R": -12.0,
        "頭": (2.0, 0.0, -8.0),
        "首": (0.0, 0.0, -3.0),
        "上半身": (2.0, 0.0, 0.0),
        "上半身2": (-2.0, 0.0, 0.0),
    }),
    (142, {
        "手捩.R": (0.0, 75.0, 0.0),
        "腕.R": (55.0, 0.0, 16.0),
        "ひじ.R": (94.0, 0.0, 0.0),
        "手首.R": (0.0, -8.0, -2.0),
        "__curl.R": -8.0,
        "頭": (0.0, 0.0, -9.0),
        "首": (0.0, 0.0, -4.0),
        "上半身": (1.0, 0.0, 0.0),
        "上半身2": (2.0, 0.0, 0.0),
    }),
    (172, {
        "手捩.R": (0.0, 75.0, 0.0),
        "腕.R": (58.0, 0.0, 14.0),
        "ひじ.R": (98.0, 0.0, 0.0),
        "手首.R": (0.0, 0.0, -4.0),
        "__curl.R": -12.0,
        "頭": (2.0, 0.0, -8.0),
        "首": (0.0, 0.0, -3.0),
        "上半身": (2.0, 0.0, 0.0),
        "上半身2": (-2.0, 0.0, 0.0),
    }),
    (195, {
        "腕.R": (18.0, 0.0, 55.0),
        "ひじ.R": (30.0, 0.0, 0.0),
        "手首.R": (0.0, 0.0, 0.0),
        "__curl.R": 0.0,
        "頭": (0.0, 0.0, 0.0),
        "首": (0.0, 0.0, 0.0),
        "上半身": (0.0, 0.0, 0.0),
        "上半身2": (0.0, 0.0, 0.0),
    }),
    (211, REST_POSE),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create an upper-body listening gesture on the prepared Luo Tianyi rig"
    )
    parser.add_argument("--target", required=True)
    parser.add_argument("--output-blend", required=True)
    parser.add_argument("--output-glb", required=True)
    parser.add_argument("--action-name", default="listen_gesture")
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


def finger_curl_values(curl: float, side: str) -> dict[str, tuple[float, float, float]]:
    pose: dict[str, tuple[float, float, float]] = {}
    for finger in FINGER_BONES:
        weight = 0.7 if finger in ("親指０", "小指２") else (0.9 if finger in ("小指１", "親指１") else 1.0)
        pose[finger + side] = (curl * weight, 0.0, 0.0)
    return pose


def expand_pose(pose: dict[str, object]) -> dict[str, tuple[float, float, float]]:
    expanded: dict[str, tuple[float, float, float]] = {}
    for bone_name, value in pose.items():
        if isinstance(bone_name, str) and bone_name.startswith("__curl."):
            expanded.update(finger_curl_values(float(value), bone_name[len("__curl"):]))
        else:
            expanded[str(bone_name)] = value  # type: ignore[assignment]
    return expanded


def create_listen_action(
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

    keyed_frames: dict[str, set[int]] = {bone: set() for bone in CONTROLLED_BONES}
    for frame, pose in POSE_SEQUENCE:
        for bone_name, degrees in expand_pose(pose).items():
            set_rotation(target, bone_name, frame, degrees)
            keyed_frames[bone_name].add(frame)

    # 每根受控骨骼的首尾都要有键：未提到的骨骼从 REST 直接过渡，避免收尾悬空
    for bone_name in CONTROLLED_BONES:
        frames = keyed_frames[bone_name]
        if 1 not in frames:
            set_rotation(target, bone_name, 1, REST_POSE.get(bone_name, (0.0, 0.0, 0.0)))
        if 211 not in frames:
            set_rotation(target, bone_name, 211, REST_POSE.get(bone_name, (0.0, 0.0, 0.0)))

    for curve in action.fcurves:
        for point in curve.keyframe_points:
            point.interpolation = "BEZIER"
            point.handle_left_type = "AUTO_CLAMPED"
            point.handle_right_type = "AUTO_CLAMPED"

    bpy.context.scene.render.fps = fps
    bpy.context.scene.render.fps_base = 1.0
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 211
    action.use_frame_range = True
    action.frame_start = 1
    action.frame_end = 211
    bpy.context.scene.frame_set(1)
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
        raise RuntimeError(f"Listen rig mapping is missing bones: {missing_bones}")
    action = create_listen_action(target, args.action_name, args.fps)

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
    print("LISTEN_MOTION_REPORT", json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
