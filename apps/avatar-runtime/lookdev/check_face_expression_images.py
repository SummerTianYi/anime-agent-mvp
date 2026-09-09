"""Codex: independent, read-only full-pixel audit of Godot expression evidence."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

folder = Path(sys.argv[1])
report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
assert report["status"] == "PASS", report
pairs = sorted(folder.glob("pair-*.png"))
assert len(pairs) == 104, len(pairs)
changed = 0
for path in pairs:
    pixels = np.asarray(Image.open(path).convert("RGBA"))
    left, right = np.split(pixels, 2, axis=1)
    assert np.array_equal(left[:, :, 3], right[:, :, 3]), path.name
    assert np.count_nonzero(left[:, :, 3]) > 10000, path.name
    changed += int(np.count_nonzero(np.any(left[:, :, :3] != right[:, :, :3], axis=2)))
assert changed > 0, "A disabled or missing face overlay must not pass"
frames = sorted(folder.glob("sequence-*.png"))
assert len(frames) == 180, len(frames)
for path in frames:
    pixels = np.asarray(Image.open(path).convert("RGBA"))
    assert np.count_nonzero(pixels[:, :, 3]) > 10000, path.name
print(f"FACE_IMAGES_OK pairs={len(pairs)} frames={len(frames)} alpha_changes=0 rgb_changed_pixels={changed}")
