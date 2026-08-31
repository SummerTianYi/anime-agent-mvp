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
END_FRAME = 256

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

LEFT_OPEN = {
    "腕.L": (34.0, 0.0, -5.0),
    "ひじ.L": (0.0, 10.0, 0.0),
    "手首.L": (0.0, 0.0, -12.0),
    "__curl.L": -6.0,
}

# Reference-video timeline (0.0–8.5 s). The later camera push-in and costume
# transition are edits, not skeletal motion. The observed order is open palm by
# the ear -> gentle fist hold -> open palm hold, with the other arm kept open.
POSE_SEQUENCE = (
    (1, {**REST_POSE, **LEFT_OPEN}),
    (12, {
        **LEFT_OPEN,
        "腕.R": (-8.0, 0.0, 34.0), "ひじ.R": (58.0, 0.0, 0.0),
        "手首.R": (0.0, -6.0, -2.0), "__curl.R": -8.0,
        "上半身": (1.0, 0.0, -1.0), "上半身2": (1.0, 0.0, -1.5),
    }),
    (25, {
        **LEFT_OPEN,
        "手捩.R": (0.0, 75.0, 0.0), "腕.R": (55.0, 0.0, 12.0),
        "ひじ.R": (95.0, 0.0, 0.0), "手首.R": (0.0, 0.0, -4.0),
        "__curl.R": -12.0, "頭": (0.5, 0.0, 2.0), "首": (0.0, 0.0, 1.0),
        "上半身": (1.5, 0.0, -1.5), "上半身2": (1.0, 0.0, -2.0),
    }),
    (55, {
        **LEFT_OPEN,
        "手捩.R": (0.0, 75.0, 0.0), "腕.R": (58.0, 0.0, 14.0),
        "ひじ.R": (98.0, 0.0, 0.0), "手首.R": (0.0, -5.0, -7.0),
        "__curl.R": -10.0, "頭": (1.5, 0.0, 1.0), "首": (0.0, 0.0, 0.5),
        "上半身": (2.0, 0.0, -2.0), "上半身2": (1.5, 0.0, -2.5),
    }),
    (72, {
        **LEFT_OPEN,
        "手捩.R": (0.0, 58.0, 0.0), "腕.R": (43.0, 0.0, 22.0),
        "ひじ.R": (92.0, 0.0, 0.0), "手首.R": (0.0, -7.0, -2.0),
        "__curl.R": 24.0, "頭": (1.0, 0.0, -1.0), "首": (0.0, 0.0, -0.5),
        "上半身": (1.5, 0.0, -1.0), "上半身2": (1.0, 0.0, -1.5),
    }),
    (82, {
        **LEFT_OPEN,
        "手捩.R": (0.0, 46.0, 0.0), "腕.R": (25.0, 0.0, 31.0),
        "ひじ.R": (90.0, 0.0, 0.0), "手首.R": (0.0, -8.0, 0.0),
        "__curl.R": 42.0, "頭": (0.5, 0.0, -2.0), "首": (0.0, 0.0, -1.0),
        "上半身": (1.0, 0.0, -0.5), "上半身2": (0.5, 0.0, -1.0),
    }),
    (145, {
        **LEFT_OPEN,
        "手捩.R": (0.0, 50.0, 0.0), "腕.R": (27.0, 0.0, 29.0),
        "ひじ.R": (92.0, 0.0, 0.0), "手首.R": (0.0, -5.0, 1.0),
        "__curl.R": 40.0, "頭": (1.5, 0.0, -1.0), "首": (0.0, 0.0, -0.5),
        "上半身": (2.0, 0.0, -1.5), "上半身2": (1.0, 0.0, -2.0),
    }),
    (168, {
        **LEFT_OPEN,
        "手捩.R": (0.0, 65.0, 0.0), "腕.R": (48.0, 0.0, 20.0),
        "ひじ.R": (94.0, 0.0, 0.0), "手首.R": (0.0, -3.0, -3.0),
        "__curl.R": 8.0, "頭": (1.0, 0.0, 0.5),
        "上半身": (1.5, 0.0, -1.5), "上半身2": (1.0, 0.0, -2.0),
    }),
    (181, {
        **LEFT_OPEN,
        "手捩.R": (0.0, 75.0, 0.0), "腕.R": (57.0, 0.0, 14.0),
        "ひじ.R": (97.0, 0.0, 0.0), "手首.R": (0.0, 0.0, -5.0),
        "__curl.R": -12.0, "頭": (0.5, 0.0, 1.5), "首": (0.0, 0.0, 0.5),
        "上半身": (1.5, 0.0, -1.5), "上半身2": (1.0, 0.0, -2.0),
    }),
    (210, {
        **LEFT_OPEN,
        "手捩.R": (0.0, 75.0, 0.0), "腕.R": (55.0, 0.0, 16.0),
        "ひじ.R": (94.0, 0.0, 0.0), "手首.R": (0.0, -8.0, -2.0),
        "__curl.R": -9.0, "頭": (1.0, 0.0, 0.5),
        "上半身": (2.0, 0.0, -2.0), "上半身2": (1.5, 0.0, -2.5),
    }),
    (239, {
        **LEFT_OPEN,
        "手捩.R": (0.0, 75.0, 0.0), "腕.R": (58.0, 0.0, 14.0),
        "ひじ.R": (98.0, 0.0, 0.0), "手首.R": (0.0, 0.0, -5.0),
        "__curl.R": -12.0, "頭": (0.5, 0.0, 1.5), "首": (0.0, 0.0, 0.5),
        "上半身": (1.5, 0.0, -1.5), "上半身2": (1.0, 0.0, -2.0),
    }),
    (END_FRAME, {
        **LEFT_OPEN,
        "手捩.R": (0.0, 75.0, 0.0), "腕.R": (57.0, 0.0, 14.0),
        "ひじ.R": (97.0, 0.0, 0.0), "手首.R": (0.0, -2.0, -5.0),
        "__curl.R": -12.0, "頭": (0.5, 0.0, 1.0), "首": (0.0, 0.0, 0.5),
        "上半身": (1.5, 0.0, -1.5), "上半身2": (1.0, 0.0, -2.0),
    }),
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
        if END_FRAME not in frames:
            set_rotation(target, bone_name, END_FRAME, REST_POSE.get(bone_name, (0.0, 0.0, 0.0)))

    for curve in action.fcurves:
        for point in curve.keyframe_points:
            point.interpolation = "BEZIER"
            point.handle_left_type = "AUTO_CLAMPED"
            point.handle_right_type = "AUTO_CLAMPED"

    bpy.context.scene.render.fps = fps
    bpy.context.scene.render.fps_base = 1.0
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = END_FRAME
    action.use_frame_range = True
    action.frame_start = 1
    action.frame_end = END_FRAME
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
