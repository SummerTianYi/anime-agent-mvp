"""Extract deterministic reference frames from a video with Blender's decoder.

This keeps the motion-authoring workflow independent from a separately installed
FFmpeg/OpenCV runtime. The output is reference evidence only and is not a runtime
animation asset.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import bpy


def _script_args() -> list[str]:
    if "--" not in sys.argv:
        return []
    return sys.argv[sys.argv.index("--") + 1 :]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--interval", type=float, default=0.75)
    parser.add_argument("--max-width", type=int, default=600)
    return parser.parse_args(_script_args())


def main() -> None:
    args = _parse_args()
    video_path = args.input.resolve()
    output_dir = args.output_dir.resolve()
    if not video_path.is_file():
        raise FileNotFoundError(video_path)
    if args.interval <= 0.0:
        raise ValueError("--interval must be positive")
    output_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    sequence_editor = scene.sequence_editor_create()
    strip = sequence_editor.strips.new_movie(
        name="reference",
        filepath=str(video_path),
        channel=1,
        frame_start=1,
    )

    source_fps = float(strip.fps)
    source_frames = int(strip.frame_final_duration)
    source_width = int(strip.elements[0].orig_width)
    source_height = int(strip.elements[0].orig_height)
    scale = min(1.0, args.max_width / max(source_width, 1))

    scene.render.resolution_x = max(1, round(source_width * scale))
    scene.render.resolution_y = max(1, round(source_height * scale))
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.fps = max(1, round(source_fps))
    scene.frame_start = 1
    scene.frame_end = source_frames

    seconds = source_frames / source_fps
    sample_times: list[float] = []
    sample_time = 0.0
    while sample_time < seconds:
        sample_times.append(sample_time)
        sample_time += args.interval
    if not sample_times or seconds - sample_times[-1] > 0.05:
        sample_times.append(max(0.0, seconds - 1.0 / source_fps))

    for index, timestamp in enumerate(sample_times):
        frame = min(source_frames, 1 + round(timestamp * source_fps))
        scene.frame_set(frame)
        output_path = output_dir / f"frame_{index:02d}_{timestamp:06.2f}s.png"
        scene.render.filepath = str(output_path)
        bpy.ops.render.render(write_still=True)
        print(f"VIDEO_REFERENCE_FRAME index={index} time={timestamp:.3f} frame={frame} path={output_path}")

    print(
        "VIDEO_REFERENCE_EXTRACT_OK "
        f"size={source_width}x{source_height} fps={source_fps:.6f} "
        f"frames={source_frames} seconds={seconds:.3f} samples={len(sample_times)}"
    )


if __name__ == "__main__":
    main()
