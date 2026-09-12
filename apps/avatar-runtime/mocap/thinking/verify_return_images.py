"""Codex: compare real return renders to the original idle at the same phase."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from encode import compose


def compare_rgba(a, b):
    delta = np.abs(a - b)
    large = delta.max(axis=2) > 2
    # Four-sample MSAA can change one coverage sample (about 64/255) at
    # an isolated silhouette pixel after sub-micrometre bone round-off.
    # Never exempt opaque interior pixels or a displaced silhouette.
    coverage = (a[:, :, 3] < 255) & (b[:, :, 3] < 255) & (delta.max(axis=2) <= 64)
    bounds_a, bounds_b = np.argwhere(a[:, :, 3] > 0), np.argwhere(b[:, :, 3] > 0)
    same_bounds = np.array_equal(bounds_a.min(axis=0), bounds_b.min(axis=0)) and np.array_equal(bounds_a.max(axis=0), bounds_b.max(axis=0))
    return {'max_rgba_error_255': int(delta.max()), 'mean_rgba_error_255': float(delta.mean()),
            'large_edge_pixels': int(large.sum()), 'same_bounds': bool(same_bounds),
            'pass': bool(same_bounds and large.sum() <= 4 and np.all(coverage[large]))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('old', type=Path)
    args = parser.parse_args()
    output = args.root / 'delivery'
    report_path = output / 'idle-image-check-v2.json'
    image_path = output / 'returned-full-comparison.png'
    if report_path.exists() or image_path.exists():
        raise FileExistsError('Do not overwrite existing return evidence')
    rows = []
    for yaw in (0, 55, -55, 180):
        name = f't9.50-y{yaw}.png'
        with Image.open(args.root / 'idle-reference' / name) as original:
            a = np.asarray(original.convert('RGBA'), dtype=np.int16)
        with Image.open(args.root / 'final-detail' / name) as returned:
            b = np.asarray(returned.convert('RGBA'), dtype=np.int16)
        rows.append({'yaw': yaw, **compare_rgba(a, b)})
    negative = a.copy()
    y, x = np.argwhere(a[:, :, 3] == 255)[0]
    negative[y, x, 0] += 10 if negative[y, x, 0] <= 245 else -10
    negative_rejected = not compare_rgba(a, negative)['pass']
    source_body = hashlib.sha256((args.old / 'final-detail/thinking_preview.tres').read_bytes()).hexdigest()
    returned_body = hashlib.sha256((args.root / 'final-detail/thinking_preview.tres').read_bytes()).hexdigest()
    report = {'agent': 'Codex', 'body_clip_identical': source_body == returned_body,
              'body_clip_sha256': returned_body, 'idle_views': rows,
              'opaque_pixel_negative_rejected': negative_rejected,
              'pass': source_body == returned_body and all(r['pass'] for r in rows) and negative_rejected}
    output.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    if not report['pass']:
        raise AssertionError(report)
    compose(args.old / 'full-check/t9.50-y0.png', args.root / 'full-check/t9.50-y0.png',
            285, returning=True).save(image_path)
    print(json.dumps(report))


if __name__ == '__main__':
    main()
