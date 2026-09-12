"""Codex: compose synchronized real Godot frames; verify the encoded preview."""
import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path

import av
from PIL import Image, ImageDraw, ImageFont

COUNT = 124
FONT = "C:/Windows/Fonts/msyh.ttc"


def compose(full, near, index):
    canvas = Image.new("RGB", (1440, 960), (14, 17, 21))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(FONT, 25)
    small = ImageFont.truetype(FONT, 18)
    for x, path, label in [
        (0, full, "全身 · 抬手 / 挥别 / 放回"),
        (720, near, "近景 · 轻摇头，闭眼微笑"),
    ]:
        with Image.open(path) as source:
            rgba = source.convert("RGBA").resize((720, 870), Image.Resampling.LANCZOS)
        canvas.paste(rgba, (x, 64), rgba)
        draw.text((x + 20, 18), label, font=font, fill=(212, 232, 240))
    draw.text((20, 937), f"Codex | 挥别 v3 · 保留原手臂动作 | 1.4外观 | 仅预览 · 未实装 | {index / 30:.2f}s",
              font=small, fill=(159, 185, 203))
    return canvas


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("full", type=Path)
    parser.add_argument("near", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    views = []
    for directory in [args.full, args.near]:
        report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
        assert report["failures"] == [], "Do not encode failed gates"
        frames = sorted((directory / "frames").glob("*.png"))
        assert [p.name for p in frames] == [f"{i:04d}.png" for i in range(COUNT)]
        views.append(frames)
    args.output.mkdir(parents=True)
    mp4 = args.output / "farewell-preview.mp4"
    proxies, hashes = [], []
    with av.open(str(mp4), "w") as container:
        stream = container.add_stream("libx264", rate=30)
        stream.width, stream.height = 1440, 960
        stream.pix_fmt = "yuv420p"
        stream.options = {"crf": "17", "preset": "medium"}
        for i, (full, near) in enumerate(zip(*views)):
            rgb = compose(full, near, i)
            if i == 39:
                rgb.save(args.output / "farewell-still.png")
            frame = av.VideoFrame.from_image(rgb)
            frame.pts, frame.time_base = i, Fraction(1, 30)
            for packet in stream.encode(frame):
                container.mux(packet)
            if i % 2 == 0:
                proxy = rgb.resize((960, 640), Image.Resampling.LANCZOS)
                proxies.append(proxy)
                hashes.append(hashlib.sha256(proxy.tobytes()).hexdigest())
        for packet in stream.encode():
            container.mux(packet)
    apng = args.output / "farewell-preview.apng"
    proxies[0].save(apng, format="PNG", save_all=True, append_images=proxies[1:],
                    duration=1000 / 15, loop=0, disposal=0, blend=0)
    with Image.open(apng) as decoded:
        assert decoded.n_frames == len(proxies)
        for i in range(decoded.n_frames):
            decoded.seek(i)
            assert hashlib.sha256(decoded.convert("RGB").tobytes()).hexdigest() == hashes[i]
    with av.open(str(mp4)) as decoded:
        frames = list(decoded.decode(video=0))
        assert len(frames) == COUNT
        assert frames[0].width == 1440 and frames[0].height == 960
        assert abs(float(frames[-1].time) - 4.1) < 0.001
    # Chronological evidence, with no generative editing or perspective changes.
    for label, indices in [
        ("entry", range(6, 31, 2)), ("wave", range(30, 96, 5)), ("release", range(94, 124, 2))
    ]:
        sheet = Image.new("RGB", (1440, 1080), (14, 17, 21))
        draw = ImageDraw.Draw(sheet)
        for cell, index in enumerate(indices):
            with Image.open(views[1][index]) as source:
                image = source.convert("RGBA").resize((270, 326), Image.Resampling.LANCZOS)
            x, y = (cell % 5) * 288, (cell // 5) * 360
            sheet.paste(image, (x + 9, y + 28), image)
            draw.text((x + 12, y + 6), f"{index / 30:.3f}s", font=ImageFont.truetype(FONT, 18),
                      fill=(212, 232, 240))
        sheet.save(args.output / f"{label}-review.png")
    report = {"agent": "Codex", "mp4_frames": COUNT, "fps": 30, "last_frame_seconds": 4.1,
              "apng_frames": len(proxies), "apng_rgb_roundtrip": "exact",
              "mp4_sha256": hashlib.sha256(mp4.read_bytes()).hexdigest(),
              "note": "Actual saved Godot Animation replay, not generated art or automatic mocap. Offline preview only."}
    (args.output / "encoding-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
