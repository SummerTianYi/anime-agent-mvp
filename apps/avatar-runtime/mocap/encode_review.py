"""Codex: encode the actual 30fps Godot review frames; no generated motion."""
import argparse
from pathlib import Path

import cv2
from PIL import Image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("review_dir", type=Path)
    args = parser.parse_args()
    frames = sorted((args.review_dir / "frames").glob("*.png"))
    if len(frames) != 181:
        raise ValueError(f"Expected 181 rendered frames, got {len(frames)}")
    output = args.review_dir / "listen-preview.mp4"
    if output.exists():
        raise FileExistsError(output)
    first = cv2.imread(str(frames[0]))
    height, width = first.shape[:2]
    writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"mp4v"), 30, (width, height))
    if not writer.isOpened():
        raise RuntimeError("Local MP4 encoder unavailable")
    try:
        for frame in frames:
            pixels = cv2.imread(str(frame))
            if pixels is None or pixels.shape[:2] != (height, width):
                raise ValueError(f"Invalid rendered frame: {frame.name}")
            writer.write(pixels)
    finally:
        writer.release()
    capture = cv2.VideoCapture(str(output))
    try:
        assert int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) == 181
        assert capture.read()[0]
    finally:
        capture.release()
    # GIF fallback for clients without MPEG-4 Part 2 playback. Same uncropped
    # render frames; half the frame rate, not a different model/animation.
    images = [Image.open(frame).convert("RGB") for frame in frames[::2]]
    try:
        images[0].save(args.review_dir / "listen-preview.gif", save_all=True,
                       append_images=images[1:], duration=67, loop=0)
    finally:
        for item in images:
            item.close()
    print(f"LISTEN_VIDEO_OK {output} 181 frames / 30fps")


if __name__ == "__main__":
    main()
