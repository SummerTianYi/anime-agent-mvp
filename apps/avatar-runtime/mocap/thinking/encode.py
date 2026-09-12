"""Codex: encode actual GPU frames; MP4 + lossless RGB APNG. No generated art."""
import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path

import av
from PIL import Image, ImageDraw, ImageFont


def compose(full_path, detail_path, frame, comparison=False, physics=False, returning=False):
    canvas = Image.new('RGB', (1440, 960), (14, 17, 21))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 25)
    small = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 18)
    labels = ('调整前 · 原有辫子摆动', '调整后 · 辫子绕臂 / 发梢下垂') if comparison else ('全身 · 进入 / 思考 / 退出', '近景 · 拇指食指托下巴 + 托肘')
    if physics:
        labels = ('上一版 · 固定绕臂路径', '本轮试验 · 动画引导 + 发束物理')
    if returning:
        labels = ('修正前 · 辫子未回位', '修正后 · 回落并衔接原待机')
    for x, path, label in [(0, full_path, labels[0]), (720, detail_path, labels[1])]:
        with Image.open(path) as source:
            rgba = source.convert('RGBA').resize((720, 870), Image.Resampling.LANCZOS)
        canvas.paste(rgba, (x, 64), rgba)
        draw.text((x + 20, 18), label, font=font, fill=(212, 232, 240))
    description = '手臂代理碰撞 · 非全身物理 / 非零穿模承诺' if physics else '视频参考 + 手势适配 | 1.4外观'
    if returning:
        description = '仅退出段调整 · 身体 / 手型 / 官模不变'
    draw.text((20, 937), f'Codex | {description} | 离线候选 · 未实装 | {frame / 30:.2f}s', font=small, fill=(159, 185, 203))
    return canvas


def review_contacts(frames_dir, output):
    """Dense, chronological crops for the two contact transitions, not retouching."""
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 18)
    for label, indices in [('entry', range(33, 57, 2)), ('release', range(210, 270, 5))]:
        sheet = Image.new('RGB', (1200, 1080), (14, 17, 21))
        draw = ImageDraw.Draw(sheet)
        for cell, frame in enumerate(indices):
            with Image.open(Path(frames_dir) / f'{frame:04d}.png') as source:
                crop = source.convert('RGBA').crop((250, 400, 830, 1050)).resize((290, 325), Image.Resampling.LANCZOS)
            x, y = (cell % 4) * 300, (cell // 4) * 360
            sheet.paste(crop, (x + 5, y + 30), crop)
            draw.text((x + 8, y + 5), f'{frame / 30:.3f}s', font=font, fill=(220, 230, 240))
        sheet.save(Path(output) / f'{label}-review.png')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('full', type=Path)
    parser.add_argument('detail', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--hair-comparison', action='store_true')
    parser.add_argument('--physics-comparison', action='store_true')
    parser.add_argument('--return-comparison', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    full = sorted((args.full / 'frames').glob('*.png'))
    detail = sorted((args.detail / 'frames').glob('*.png'))
    if len(full) != 286 or len(detail) != 286:
        raise ValueError(f'Expected 286 ordered frames in each view, got {len(full)}, {len(detail)}')
    if [p.name for p in full] != [f'{i:04d}.png' for i in range(286)]:
        raise ValueError('Missing full-view frame')
    if [p.name for p in detail] != [p.name for p in full]:
        raise ValueError('Views are not synchronized')
    stem = 'thinking-hair-comparison' if args.hair_comparison else 'thinking-thumb-index-preview'
    if args.physics_comparison:
        stem = 'thinking-hair-contact-preview'
    if args.return_comparison:
        stem = 'thinking-hair-return-preview'
    mp4 = args.output / f'{stem}.mp4'
    apng = args.output / f'{stem}.apng'
    previews = []
    hashes = []
    with av.open(str(mp4), 'w') as container:
        stream = container.add_stream('libx264', rate=30)
        stream.width, stream.height = 1440, 960
        stream.pix_fmt = 'yuv420p'
        stream.options = {'crf': '17', 'preset': 'medium'}
        for i, (left, right) in enumerate(zip(full, detail)):
            rgb = compose(left, right, i, args.hair_comparison, args.physics_comparison, args.return_comparison)
            if i == (285 if args.return_comparison else 60):
                rgb.save(args.output / f'{stem}-still.png')
            frame = av.VideoFrame.from_image(rgb)
            frame.pts, frame.time_base = i, Fraction(1, 30)
            for packet in stream.encode(frame):
                container.mux(packet)
            if i % 2 == 0:
                proxy = rgb.resize((960, 640), Image.Resampling.LANCZOS)
                previews.append(proxy)
                hashes.append(hashlib.sha256(proxy.tobytes()).hexdigest())
        for packet in stream.encode():
            container.mux(packet)
    previews[0].save(apng, format='PNG', save_all=True, append_images=previews[1:], duration=1000 / 15, loop=0, disposal=0, blend=0)
    with Image.open(apng) as decoded:
        assert decoded.n_frames == len(previews)
        for i in range(decoded.n_frames):
            decoded.seek(i)
            assert hashlib.sha256(decoded.convert('RGB').tobytes()).hexdigest() == hashes[i], f'APNG color mismatch at {i}'
    with av.open(str(mp4)) as decoded:
        frames = list(decoded.decode(video=0))
        assert len(frames) == 286
        assert frames[0].width == 1440 and frames[0].height == 960
        assert abs(float(frames[-1].time) - 9.5) < 0.001
    report = {'agent': 'Codex', 'mp4_frames': 286, 'mp4_fps': 30, 'duration_seconds': 286 / 30,
              'apng_frames': len(previews), 'apng_rgb_roundtrip': 'exact',
              'note': 'MP4 is lossy; APNG preserves composed reference RGB. Both views are actual Godot rendering, not generated images.'}
    (args.output / 'encoding-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    if args.physics_comparison or args.return_comparison:
        review_contacts(args.detail / 'frames', args.output)
    print(json.dumps(report))


if __name__ == '__main__':
    main()
