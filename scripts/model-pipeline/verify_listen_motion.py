from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import blender_arguments  # noqa: E402


SAMPLE_FRAMES = (1, 25, 82, 181, 256)
POSE_BONE_PATTERN = re.compile(r'pose\.bones\["(.+?)"\]')
LOWER_BODY_ROOTS = ("センター", "下半身", "足.", "ひざ.", "足首.", "つま先.", "スカート")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the reference-rebuilt listening motion")
    parser.add_argument("--input", required=True)
    parser.add_argument("--action", default="listen_gesture")
    return parser.parse_args(blender_arguments())


def _pose_point(target: bpy.types.Object, bone_name: str) -> tuple[float, float, float]:
    point = target.pose.bones[bone_name].head
    return (float(point.x), float(point.y), float(point.z))


def _finger_angle(target: bpy.types.Object, bone_name: str) -> float:
    return float(target.pose.bones[bone_name].rotation_quaternion.angle)


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    bpy.ops.wm.open_mainfile(filepath=str(input_path))

    action = bpy.data.actions.get(args.action)
    target = next(
        (
            obj for obj in bpy.context.scene.objects
            if obj.type == "ARMATURE" and all(name in obj.data.bones for name in ("頭", "肩.L", "肩.R", "手首.L", "手首.R"))
        ),
        None,
    )
    if target is None or action is None or target.animation_data is None:
        raise RuntimeError("Listening action or target armature is missing")
    if target.animation_data.action != action:
        raise RuntimeError(f"Target does not have active action {args.action!r}")

    start_frame = int(round(action.frame_range[0]))
    end_frame = int(round(action.frame_range[1]))
    if (start_frame, end_frame) != (1, 256):
        raise RuntimeError(f"Expected reference range 1..256, found {start_frame}..{end_frame}")

    animated_bones: set[str] = set()
    for curve in action.fcurves:
        match = POSE_BONE_PATTERN.search(curve.data_path)
        if match:
            animated_bones.add(match.group(1))
    lower_body_tracks = sorted(
        bone for bone in animated_bones
        if bone.startswith(LOWER_BODY_ROOTS)
    )
    if lower_body_tracks:
        raise RuntimeError(f"Listening action leaked into lower-body tracks: {lower_body_tracks}")

    samples: dict[int, dict[str, object]] = {}
    maximum_scale_error = 0.0
    for frame in range(start_frame, end_frame + 1):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        for bone_name in animated_bones:
            pose_bone = target.pose.bones[bone_name]
            matrix_values = [value for row in pose_bone.matrix for value in row]
            if not all(math.isfinite(value) for value in matrix_values):
                raise RuntimeError(f"Non-finite pose matrix at frame {frame}, bone {bone_name}")
            maximum_scale_error = max(
                maximum_scale_error,
                max(abs(float(axis) - 1.0) for axis in pose_bone.scale),
            )
        if frame in SAMPLE_FRAMES:
            samples[frame] = {
                "head": _pose_point(target, "頭"),
                "right_shoulder": _pose_point(target, "肩.R"),
                "right_elbow": _pose_point(target, "ひじ.R"),
                "right_wrist": _pose_point(target, "手首.R"),
                "left_shoulder": _pose_point(target, "肩.L"),
                "left_wrist": _pose_point(target, "手首.L"),
                "right_index_angle": _finger_angle(target, "人指１.R"),
            }

    for frame in (25, 82, 181, 256):
        right_shoulder = samples[frame]["right_shoulder"]
        right_wrist = samples[frame]["right_wrist"]
        if right_wrist[2] <= right_shoulder[2]:
            raise RuntimeError(f"Right listening hand is not above the shoulder at frame {frame}")
        left_shoulder = samples[frame]["left_shoulder"]
        left_wrist = samples[frame]["left_wrist"]
        if left_wrist[2] >= left_shoulder[2]:
            raise RuntimeError(f"Left support hand is not naturally lowered at frame {frame}")

    open_first = float(samples[25]["right_index_angle"])
    closed_middle = float(samples[82]["right_index_angle"])
    open_last = float(samples[181]["right_index_angle"])
    if closed_middle < open_first + math.radians(20.0):
        raise RuntimeError("Middle fist is not measurably more closed than the first open palm")
    if closed_middle < open_last + math.radians(20.0):
        raise RuntimeError("Middle fist is not measurably more closed than the final open palm")
    if maximum_scale_error > 1e-6:
        raise RuntimeError(f"Pose-bone scale changed by {maximum_scale_error:.8f}")

    report = {
        "input": str(input_path),
        "action": action.name,
        "frames": end_frame - start_frame + 1,
        "fps": bpy.context.scene.render.fps / bpy.context.scene.render.fps_base,
        "duration_seconds": (end_frame - start_frame) / (bpy.context.scene.render.fps / bpy.context.scene.render.fps_base),
        "animated_bones": len(animated_bones),
        "lower_body_tracks": lower_body_tracks,
        "maximum_scale_error": maximum_scale_error,
        "gesture_order": ["open", "fist", "open"],
        "samples": samples,
    }
    print("LISTEN_MOTION_VERIFY_OK", json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
