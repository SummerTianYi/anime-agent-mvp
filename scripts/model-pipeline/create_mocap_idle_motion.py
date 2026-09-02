from __future__ import annotations

"""Create a conservative Codex-owned idle clip from monocular pose landmarks."""

import argparse
import json
import math
import statistics
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a smooth looping idle clip from MediaPipe pose landmarks"
    )
    parser.add_argument("--target", required=True)
    parser.add_argument("--landmarks", required=True)
    parser.add_argument("--output-blend", required=True)
    parser.add_argument("--output-glb", required=True)
    parser.add_argument("--action-name", default="idle_mocap_v1")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--smooth-frames", type=int, default=11)
    parser.add_argument("--loop-blend-seconds", type=float, default=2.0)
    return parser.parse_args(blender_arguments())


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def smoothstep(value: float) -> float:
    value = clamp(value, 0.0, 1.0)
    return value * value * (3.0 - 2.0 * value)


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def moving_average(values: list[float], window: int) -> list[float]:
    radius = max(0, window // 2)
    result: list[float] = []
    for index in range(len(values)):
        start = max(0, index - radius)
        end = min(len(values), index + radius + 1)
        result.append(mean(values[start:end]))
    return result


def unwrap_degrees(values: list[float]) -> list[float]:
    if not values:
        return []
    result = [values[0]]
    for value in values[1:]:
        delta = (value - result[-1] + 180.0) % 360.0 - 180.0
        result.append(result[-1] + delta)
    return result


def angle_delta_degrees(value: float, baseline: float) -> float:
    return (value - baseline + 180.0) % 360.0 - 180.0


def vector(left: list[float], right: list[float]) -> tuple[float, float, float]:
    return (right[0] - left[0], right[1] - left[1], right[2] - left[2])


def midpoint(left: list[float], right: list[float]) -> tuple[float, float, float]:
    return (
        (left[0] + right[0]) * 0.5,
        (left[1] + right[1]) * 0.5,
        (left[2] + right[2]) * 0.5,
    )


def length(value: tuple[float, float, float]) -> float:
    return math.sqrt(sum(component * component for component in value))


def joint_angle_degrees(
    first: list[float], center: list[float], last: list[float]
) -> float:
    left = vector(center, first)
    right = vector(center, last)
    denominator = max(1e-8, length(left) * length(right))
    cosine = clamp(sum(a * b for a, b in zip(left, right, strict=True)) / denominator, -1.0, 1.0)
    return math.degrees(math.acos(cosine))


def landmark_xyz(frame: dict[str, object], space: str, index: int) -> list[float]:
    landmarks = frame.get(space)
    if not isinstance(landmarks, list):
        raise RuntimeError(f"Frame {frame.get('source_frame')} is missing {space} landmarks")
    item = landmarks[index]
    return [float(item[axis]) for axis in ("x", "y", "z")]


def extract_signals(payload: dict[str, object], smooth_frames: int) -> dict[str, list[float]]:
    frames = payload.get("frames")
    if not isinstance(frames, list) or len(frames) < 60:
        raise RuntimeError("The landmark sequence is too short for an idle loop")
    raw: dict[str, list[float]] = {
        name: []
        for name in (
            "torso_roll",
            "torso_yaw",
            "head_yaw",
            "head_roll",
            "head_pitch",
            "shoulder_balance",
            "left_arm_swing",
            "right_arm_swing",
            "left_arm_depth",
            "right_arm_depth",
            "left_elbow",
            "right_elbow",
        )
    }
    for frame in frames:
        left_shoulder = landmark_xyz(frame, "world", 11)
        right_shoulder = landmark_xyz(frame, "world", 12)
        left_elbow = landmark_xyz(frame, "world", 13)
        right_elbow = landmark_xyz(frame, "world", 14)
        left_wrist = landmark_xyz(frame, "world", 15)
        right_wrist = landmark_xyz(frame, "world", 16)
        left_hip = landmark_xyz(frame, "world", 23)
        right_hip = landmark_xyz(frame, "world", 24)
        left_ear = landmark_xyz(frame, "world", 7)
        right_ear = landmark_xyz(frame, "world", 8)
        nose = landmark_xyz(frame, "world", 0)

        left_shoulder_2d = landmark_xyz(frame, "normalized", 11)
        right_shoulder_2d = landmark_xyz(frame, "normalized", 12)
        left_elbow_2d = landmark_xyz(frame, "normalized", 13)
        right_elbow_2d = landmark_xyz(frame, "normalized", 14)
        left_eye_2d = landmark_xyz(frame, "normalized", 2)
        right_eye_2d = landmark_xyz(frame, "normalized", 5)
        left_hip_2d = landmark_xyz(frame, "normalized", 23)
        right_hip_2d = landmark_xyz(frame, "normalized", 24)

        shoulder_mid_2d = midpoint(left_shoulder_2d, right_shoulder_2d)
        hip_mid_2d = midpoint(left_hip_2d, right_hip_2d)
        torso_height = max(1e-6, abs(hip_mid_2d[1] - shoulder_mid_2d[1]))
        raw["torso_roll"].append(
            math.degrees(math.atan2(shoulder_mid_2d[0] - hip_mid_2d[0], torso_height))
        )

        shoulder_width = max(1e-6, abs(left_shoulder[0] - right_shoulder[0]))
        raw["torso_yaw"].append(
            math.degrees(
                math.atan2(right_shoulder[2] - left_shoulder[2], shoulder_width)
            )
        )
        ear_mid = midpoint(left_ear, right_ear)
        face = vector(list(ear_mid), nose)
        raw["head_yaw"].append(math.degrees(math.atan2(face[0], -face[2])))
        raw["head_pitch"].append(math.degrees(math.atan2(-face[1], -face[2])))
        eye_line = vector(left_eye_2d, right_eye_2d)
        raw["head_roll"].append(math.degrees(math.atan2(eye_line[1], eye_line[0])))
        raw["shoulder_balance"].append(
            math.degrees(
                math.atan2(
                    right_shoulder_2d[1] - left_shoulder_2d[1],
                    abs(right_shoulder_2d[0] - left_shoulder_2d[0]),
                )
            )
        )

        for side, shoulder, elbow, wrist, shoulder_2d, elbow_2d in (
            (
                "left",
                left_shoulder,
                left_elbow,
                left_wrist,
                left_shoulder_2d,
                left_elbow_2d,
            ),
            (
                "right",
                right_shoulder,
                right_elbow,
                right_wrist,
                right_shoulder_2d,
                right_elbow_2d,
            ),
        ):
            arm_2d = vector(shoulder_2d, elbow_2d)
            raw[f"{side}_arm_swing"].append(
                math.degrees(math.atan2(arm_2d[0], arm_2d[1]))
            )
            arm_world = vector(shoulder, elbow)
            raw[f"{side}_arm_depth"].append(
                math.degrees(
                    math.atan2(
                        arm_world[2],
                        math.sqrt(arm_world[0] ** 2 + arm_world[1] ** 2),
                    )
                )
            )
            raw[f"{side}_elbow"].append(joint_angle_degrees(shoulder, elbow, wrist))

    return {
        name: moving_average(unwrap_degrees(values), smooth_frames)
        for name, values in raw.items()
    }


def close_loop(signals: dict[str, list[float]], blend_frames: int) -> None:
    frame_count = len(next(iter(signals.values())))
    blend_frames = min(max(2, blend_frames), frame_count - 1)
    for values in signals.values():
        first = values[0]
        start = frame_count - blend_frames
        source = values[start]
        for index in range(start, frame_count):
            alpha = smoothstep((index - start) / max(1, blend_frames - 1))
            values[index] = source * (1.0 - alpha) + first * alpha
        values[-1] = first


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


def create_action(
    target: bpy.types.Object,
    signals: dict[str, list[float]],
    action_name: str,
    fps: int,
) -> tuple[bpy.types.Action, dict[str, tuple[float, float]]]:
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

    baseline_frames = min(20, len(next(iter(signals.values()))))
    baselines = {
        name: statistics.fmean(values[:baseline_frames]) for name, values in signals.items()
    }
    ranges: dict[str, tuple[float, float]] = {}
    for name, values in signals.items():
        deltas = [angle_delta_degrees(value, baselines[name]) for value in values]
        ranges[name] = (min(deltas), max(deltas))

    frame_count = len(next(iter(signals.values())))
    for index in range(frame_count):
        frame = index + 1
        delta = {
            name: angle_delta_degrees(values[index], baselines[name])
            for name, values in signals.items()
        }
        torso_roll = clamp(delta["torso_roll"] * 0.55, -4.5, 4.5)
        torso_yaw = clamp(delta["torso_yaw"] * 0.45, -5.0, 5.0)
        head_yaw = clamp(delta["head_yaw"] * 0.72 - torso_yaw, -24.0, 24.0)
        head_roll = clamp(delta["head_roll"] * 0.75 - torso_roll, -9.0, 9.0)
        head_pitch = clamp(delta["head_pitch"] * 0.55, -9.0, 9.0)
        shoulder_balance = clamp(delta["shoulder_balance"] * 0.35, -3.0, 3.0)
        left_arm_swing = clamp(delta["left_arm_swing"] * 0.32, -5.0, 5.0)
        right_arm_swing = clamp(delta["right_arm_swing"] * 0.32, -5.0, 5.0)
        left_arm_depth = clamp(delta["left_arm_depth"] * 0.28, -4.0, 4.0)
        right_arm_depth = clamp(delta["right_arm_depth"] * 0.28, -4.0, 4.0)
        left_elbow = clamp((180.0 - signals["left_elbow"][index]) * 0.35, 1.0, 12.0)
        right_elbow = clamp((180.0 - signals["right_elbow"][index]) * 0.35, 1.0, 12.0)

        set_rotation(target, "上半身", frame, (0.0, torso_yaw * 0.35, torso_roll * 0.45))
        set_rotation(target, "上半身2", frame, (0.0, torso_yaw * 0.65, torso_roll * 0.55))
        set_rotation(
            target,
            "首",
            frame,
            (head_pitch * 0.32, head_yaw * 0.35, head_roll * 0.35),
        )
        set_rotation(
            target,
            "頭",
            frame,
            (head_pitch * 0.68, head_yaw * 0.65, head_roll * 0.65),
        )
        set_rotation(target, "肩.L", frame, (0.0, 0.0, shoulder_balance))
        set_rotation(target, "肩.R", frame, (0.0, 0.0, -shoulder_balance))
        set_rotation(
            target,
            "腕.L",
            frame,
            (48.0 + left_arm_swing, left_arm_depth, 0.0),
        )
        set_rotation(
            target,
            "腕.R",
            frame,
            (-48.0 - right_arm_swing, -right_arm_depth, 0.0),
        )
        set_rotation(target, "ひじ.L", frame, (0.0, left_elbow, 0.0))
        set_rotation(target, "ひじ.R", frame, (0.0, -right_elbow, 0.0))
        set_rotation(target, "手首.L", frame, (0.0, 0.0, 0.0))
        set_rotation(target, "手首.R", frame, (0.0, 0.0, 0.0))

    for curve in action.fcurves:
        for point in curve.keyframe_points:
            point.interpolation = "BEZIER"
            point.handle_left_type = "AUTO_CLAMPED"
            point.handle_right_type = "AUTO_CLAMPED"
    bpy.context.scene.render.fps = fps
    bpy.context.scene.render.fps_base = 1.0
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = frame_count
    action.use_frame_range = True
    action.frame_start = 1
    action.frame_end = frame_count
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    return action, ranges


def main() -> None:
    args = parse_args()
    target_path = Path(args.target).expanduser().resolve()
    landmarks_path = Path(args.landmarks).expanduser().resolve()
    output_blend = Path(args.output_blend).expanduser().resolve()
    output_glb = Path(args.output_glb).expanduser().resolve()
    for path in (target_path, landmarks_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    payload = json.loads(landmarks_path.read_text(encoding="utf-8"))
    source_fps = float(payload.get("source_fps", 0.0))
    if abs(source_fps - args.fps) > 0.01:
        raise RuntimeError(
            f"The first implementation requires matching source/output FPS, got {source_fps} and {args.fps}"
        )
    signals = extract_signals(payload, args.smooth_frames)
    close_loop(signals, int(round(args.loop_blend_seconds * args.fps)))

    bpy.ops.wm.open_mainfile(filepath=str(target_path))
    target = one_armature(list(bpy.context.scene.objects), "target")
    missing_bones = [name for name in CONTROLLED_BONES if name not in target.data.bones]
    if missing_bones:
        raise RuntimeError(f"Mocap idle rig mapping is missing bones: {missing_bones}")
    action, ranges = create_action(target, signals, args.action_name, args.fps)
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
        "source_detection_rate": payload.get("detection_rate"),
        "loop_blend_seconds": args.loop_blend_seconds,
        "raw_signal_delta_ranges_degrees": ranges,
        "output_blend": str(output_blend),
        "output_glb": str(output_glb),
    }
    print("MOCAP_IDLE_REPORT", json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
