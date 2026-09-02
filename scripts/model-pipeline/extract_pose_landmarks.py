from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np


POSE_LANDMARK_NAMES = (
    "nose",
    "left_eye_inner",
    "left_eye",
    "left_eye_outer",
    "right_eye_inner",
    "right_eye",
    "right_eye_outer",
    "left_ear",
    "right_ear",
    "mouth_left",
    "mouth_right",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_pinky",
    "right_pinky",
    "left_index",
    "right_index",
    "left_thumb",
    "right_thumb",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract deterministic MediaPipe pose landmarks from a local video"
    )
    parser.add_argument("--video", required=True)
    parser.add_argument("--model", required=True, help="MediaPipe Pose Landmarker .task file")
    parser.add_argument("--output", required=True)
    parser.add_argument("--start-seconds", type=float, default=0.0)
    parser.add_argument("--end-seconds", type=float)
    parser.add_argument("--min-confidence", type=float, default=0.5)
    return parser.parse_args()


def landmark_dict(landmark: object) -> dict[str, float]:
    return {
        "x": float(landmark.x),
        "y": float(landmark.y),
        "z": float(landmark.z),
        "visibility": float(getattr(landmark, "visibility", 1.0) or 0.0),
        "presence": float(getattr(landmark, "presence", 1.0) or 0.0),
    }


def main() -> None:
    args = parse_args()
    video_path = Path(args.video).expanduser().resolve()
    model_path = Path(args.model).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    for path in (video_path, model_path):
        if not path.is_file():
            raise FileNotFoundError(path)

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")
    source_fps = float(capture.get(cv2.CAP_PROP_FPS))
    source_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if source_fps <= 0 or source_frames <= 0:
        raise RuntimeError("Video is missing usable FPS or frame-count metadata")

    start_frame = max(0, int(round(args.start_seconds * source_fps)))
    end_frame = source_frames - 1
    if args.end_seconds is not None:
        end_frame = min(end_frame, int(round(args.end_seconds * source_fps)))
    if start_frame >= end_frame:
        raise ValueError(f"Invalid extraction range: {start_frame}..{end_frame}")
    capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    options = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=args.min_confidence,
        min_pose_presence_confidence=args.min_confidence,
        min_tracking_confidence=args.min_confidence,
        output_segmentation_masks=False,
    )

    frames: list[dict[str, object]] = []
    detected_frames = 0
    visibility_samples: dict[str, list[float]] = {
        name: [] for name in POSE_LANDMARK_NAMES
    }
    try:
        with mp.tasks.vision.PoseLandmarker.create_from_options(options) as landmarker:
            for source_frame in range(start_frame, end_frame + 1):
                ok, bgr = capture.read()
                if not ok:
                    break
                timestamp_ms = int(round(source_frame * 1000.0 / source_fps))
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result = landmarker.detect_for_video(image, timestamp_ms)
                item: dict[str, object] = {
                    "source_frame": source_frame,
                    "time_seconds": source_frame / source_fps,
                    "normalized": None,
                    "world": None,
                }
                if result.pose_landmarks and result.pose_world_landmarks:
                    normalized = [landmark_dict(value) for value in result.pose_landmarks[0]]
                    world = [landmark_dict(value) for value in result.pose_world_landmarks[0]]
                    if len(normalized) != len(POSE_LANDMARK_NAMES) or len(world) != len(
                        POSE_LANDMARK_NAMES
                    ):
                        raise RuntimeError("Pose Landmarker returned an unexpected landmark count")
                    item["normalized"] = normalized
                    item["world"] = world
                    detected_frames += 1
                    for name, landmark in zip(POSE_LANDMARK_NAMES, normalized, strict=True):
                        visibility_samples[name].append(float(landmark["visibility"]))
                frames.append(item)
    finally:
        capture.release()

    if not frames:
        raise RuntimeError("No video frames were decoded")
    if detected_frames == 0:
        raise RuntimeError("No human pose was detected")

    median_visibility = {
        name: float(np.median(samples)) if samples else 0.0
        for name, samples in visibility_samples.items()
    }
    report = {
        "schema_version": 1,
        "source_video": str(video_path),
        "source_width": width,
        "source_height": height,
        "source_fps": source_fps,
        "source_frames": source_frames,
        "range_start_frame": start_frame,
        "range_end_frame": start_frame + len(frames) - 1,
        "extracted_frames": len(frames),
        "detected_frames": detected_frames,
        "detection_rate": detected_frames / len(frames),
        "landmark_names": list(POSE_LANDMARK_NAMES),
        "median_visibility": median_visibility,
        "frames": frames,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    print(
        "POSE_LANDMARK_REPORT",
        json.dumps(
            {
                key: report[key]
                for key in (
                    "source_width",
                    "source_height",
                    "source_fps",
                    "source_frames",
                    "extracted_frames",
                    "detected_frames",
                    "detection_rate",
                )
            },
            ensure_ascii=False,
        ),
    )


if __name__ == "__main__":
    main()
