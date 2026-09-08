# Listening mocap v2 — Codex, 2026-09-09

Local implementation for the owner's `33409f9c0cb4dfb10e0ac54bfe27e3da.mp4` and back-hand photo. The right wrist-to-ear trajectory, elbow plane and shoulder/head yaw come from MediaPipe world landmarks; the occluded left arm, open palm and modest forward lean are authored adaptations. This is **not full-finger capture or a claim of exact monocular 3D reconstruction**. The official GLB, rest rig, weights, textures, scale and accepted 1.3 look remain unchanged.

| Surface | Current behavior |
|---|---|
| Local active asset | `../assets/motions/listen_mocap_v2_corrected.tres`, SHA-256 `1a372bd5e436f817ae5db43bea925f35533cbe49febd8ea1e28f7649211becdf` |
| Timing | 61 keys at 30fps, 2 seconds entering; recording holds the last pose; stopping reverses the same path from the current time, then resumes A-pose idle |
| Left arm | Fixed-length two-bone IK; wrist goes outside first, then behind the waist. It is genuinely occluded by the torso, not hidden or deleted |
| Rig binding | Native Godot rotation tracks on 74 upper-body bones; avoids Blender import/export rest-axis differences. Not another exported character model |
| Interruption | Six early/late stop points, repeated recording state, resumed recording during exit and repeated G/menu trigger covered; explicit reset/other-action overrides retain their existing immediate semantics |
| Evidence | 20 real GPU stills, front/left/back/right; 181 sequential playback frames and MP4/GIF preview. Scope is this clip, not universal cloth collision safety |
| Preserved legacy | Original `luotianyi_listen.glb` SHA-256 `975146830fec6920d959334fbb0ffd7539b4c7eb4716703cf600d0de705fe770` remains untouched |

## Local-only archive and reproduction

Repository root on this machine is `D:/UserData/Administrator/Documents/Codex/2026-08-28/https-github-com-summertianyi-anime-agent/work/anime-agent-mvp`. Its sibling `../motion-output/listen-mocap-v2/` contains `source.mp4`, `pose-landmarks.json`, the new TRES and provenance JSON, and `legacy-listen.glb`. These are local assets, not redistributable repository content. Source video SHA-256: `3bc87bb8cab0bad7c645feec0c9d70d69d61112b67f9bf9978de0f344220da48`; landmarks: `7d1327f6761a680c1e39a63e147e8235b1666850f77aa510f708bcb19a88b922`. Do not upload the person's footage by default. Copy archived `listen_mocap_v2_corrected.tres` into the active assets directory on another authorized local checkout, or rebuild with the existing `scripts/model-pipeline/extract_pose_landmarks.py` and the following commands (Git Bash, repo root):

```bash
LISTEN_LANDMARKS="$(pwd -W)/../motion-output/listen-mocap-v2/pose-landmarks.json" ../tools/godot-4.7.2/Godot_v4.7.2-stable_win64_console.exe --headless --path apps/avatar-runtime --script res://mocap/build_listen.gd
../tools/godot-4.7.2/Godot_v4.7.2-stable_win64_console.exe --headless --path apps/avatar-runtime --script res://mocap/verify_listen.gd
../tools/godot-4.7.2/Godot_v4.7.2-stable_win64_console.exe --display-driver windows --path apps/avatar-runtime --script res://mocap/review_listen.gd
```

The builder defaults to a separate `listen_mocap_v2_corrected_candidate.tres` and **refuses to overwrite** an existing output. `LISTEN_OUTPUT` can select a new path. Verification/rendering operate on the registry's **active** clip; they do not silently install a rebuilt candidate. The review skips production Core/UI/voice and uses the real model and animation player. Pass its printed review directory to `../motion-tools/.venv/Scripts/python.exe apps/avatar-runtime/mocap/encode_review.py <directory>` to encode the actual frame sequence. Current review: `C:/Users/26052/AppData/Roaming/Godot/app_userdata/Luo Tianyi Desktop Avatar MVP/listen-mocap-v2/2026-09-09T00-22-34`.

## Verification and rollback

Latest elbow correction: original v2 measured 148.908° elbow flex, 48.819° wrist bend and 0.7523 off-hinge quaternion component; it fails all three added gates. Corrected v2 measures 125.000°, 35.000° and 0.00000108 respectively; it passes, including the actual GPU large-motion skin/alpha/menu regression. Source and corrected resource are archived separately; no overwrite was used. After parallel zcode changes, the isolated Core suite was rerun at 00:27 and **191 tests passed**. First 187-test results below describe the earlier baseline, not the latest count. A rejected trial generated 46°/28° starting-angle jumps; these intermediate files are not the active registry target. No claim that every camera-visible contour proves absence of mesh contact.

`LISTEN_VERIFY_OK`: 74 rotation tracks, finite unit quaternions, 61 whole-rig samples, no bone translation/scale or lower-body change, 10.925° maximum adjacent-key angle, ≤125° elbow flex, ≤35° wrist bend, elbow off-hinge quaternion component <0.000002, behind-torso left wrist, no camera-driven pose correction, voice/manual exit and re-entry checks. Existing motion asset/runtime, 750-frame A-pose idle, input and large-motion safety gates also pass; 187 isolated Core tests and desktop TypeScript/Vite build pass. These are sampled rendering and state/structure checks, **not a triangle-level no-contact proof**. Large-motion GPU tests retain skin, alpha continuity and viewport checks; their camera-readability threshold applies only to clips requesting it. The tucked arm also has four-view review; alpha alone is not proof of no collision. Final naturalness remains owner review.

To roll back only listening, restore the listen registry path to `res://assets/motions/luotianyi_listen.glb`, minimum duration to `8.3`, sample time to `1.0`, remove `return_via_reverse` and `preserve_limb_readability`; restart Avatar. The loader remains backward-compatible and official model-version archives 1.0–1.3 are unchanged. Do not revert unrelated shared runtime changes or the other agents' work. Codex has not committed/pushed this turn, restarted production Core/TTS, or claimed live microphone/voice acceptance. Parallel zcode commit `a0d98dc` included the first Codex candidate without visual acceptance; do not misattribute it or rewrite that history. The subsequent elbow correction remains a separately declared Codex change. The pre-existing docs guard currently reports 181-vs-187 test-count drift from the parallel wake-word work; that unrelated baseline mismatch is recorded rather than hidden.
