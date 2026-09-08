# Authored motion pipeline

The active registry contains three local clips: a 12.47-second monocular-mocap looping idle, a CMU BVH pirouette stress test, and the 2-second listening mocap v2 entry (Codex, 2026-09-09; owner visual review pending). Idle/pirouette retain the GLB-track import path; listening is a native Godot Animation baked on the actual runtime rest skeleton. Both paths filter/rebind tracks to the unchanged official `assets/luotianyi_v4.glb`; no imported motion mesh replaces the character. Listening holds while recording and exits by reversing its entry path. The older 8.53-second GLB remains locally available, not overwritten. See [listening v2 reproduction/evidence/rollback](../apps/avatar-runtime/mocap/README.md).

## Current artifact and behavior

| Property | Verified value |
|---|---|
| Registry | `apps/avatar-runtime/motion_registry.json`; tracked; defines clip IDs, local paths, semantic `bone_layer`, loop policy and cross-fade duration |
| Idle | `idle_mocap_v1`, 374 Blender frames at 30 FPS, 12.47 seconds; 12 captured upper-body bones; lower body fixed; exact first/last pose match; maximum per-frame rotation 0.03459 rad |
| Pirouette source | CMU BVH mirrored by the Three.js examples; 592 frames at 120 FPS, 4.925 seconds; [CMU usage terms](https://mocap.cs.cmu.edu/) permit use of the data but not direct resale |
| Retarget | 19 core humanoid bones; target has 751 bones and 49 shape keys including Basis |
| Output | `cmu_pirouette`, 149 frames at 30 FPS (≈4.97 s after resampling; the 592-frame/120 FPS source is ≈4.93 s); horizontal root motion removed; lowest foot locked to the original ground height by default |
| Listening gesture | Active: `listen_mocap_v2_corrected.tres`, 61 frames / 2s, 74 upper-body rotation tracks, right hand by ear and authored left hand behind back; no lower-body/translation/scale tracks. Legacy: `listen_gesture`, 8.533s open→fist→open GLB, preserved for rollback |
| Runtime motion assets | `luotianyi_idle.glb`: 23,070,740 bytes, SHA-256 `5CF15A1D3E657CF76E5F58E33C9D3593A14494B89817AD2A910D57CABF9D433A`; `luotianyi_pirouette.glb`: 23,114,580 bytes, SHA-256 `1FEFBF0667711845E4FC6E0574D57D74C8982E15AA76A2A25BB9192BE1FAA284`; `luotianyi_listen.glb`: 23,136,336 bytes, SHA-256 `975146830FEC6920D959334FBB0FFD7539B4C7EB4716703CF600D0DE705FE770` |
| Godot bridge | With `relaxed_arms=true`, idle has 289 tracks (79 non-arm + 210 reference tracks); original idle without this policy retains 106. Pirouette stays at 124; new listen uses 74. `voice.state=recording` starts/holds listen; transcribing/idle reverses from current time then returns to authored idle. Re-recording during exit resumes forward without teleporting |
| Bone masks | `upper_body` follows `上半身` descendants and explicitly includes both complete 17-bone `MaWei` chains; `lower_body` covers center/waist, `下半身`, legs, skirt and foot IK; `full_body` accepts every target bone |
| Pigtail validation | One mesh; 34/34 pigtail bones present; both parent chains continuous from `首`; every chain bone has non-zero skin weights; runtime check confirms upper-only classification |
| Garment baseline | The official model exposes 16 complete three-bone skirt chains, but this repository intentionally applies no custom cloth/contact solver. The previous runtime spring/panel/vertex-overlay experiment was removed after it failed topology and natural-motion acceptance; work continues in `SummerTianYi/anime-agent-cloth-physics` |
| Trigger | Press `P` for pirouette, `G` for listen, use the interaction menu, or hold the Voice button to start the semantic listen path; `ANIME_AGENT_USE_AUTHORED_MOTION=0` disables local motion loading |
| Fallback | If the ignored motion asset is absent, the avatar and all existing procedural actions still start normally |

## Conservative idle — Codex, 2026-09-08

The owner chose a bounded fallback rather than another cloth solver: restore the old diagonal-down A-pose arms during idle, retaining the captured torso/head movement. The source GLB bind pose is a horizontal T-pose; the runtime's existing upper-arm ±48° offsets produce the requested relaxed triangle silhouette. `idle.relaxed_arms=true` replaces only shoulder/arm-descendant tracks in the duplicated runtime animation with constant position/rotation/scale keys. These keys include fingers/twist helpers so a previous interaction cannot leave a clenched hand or stale arm pose. No per-frame collision correction, model deformation, rig/proportion edits, new model version, or physics-sandbox code is introduced. The arms still follow the chest naturally through the skeleton hierarchy, and both complete 17-bone pigtails remain in the upper-body layer with their existing sway.

| Boundary | Current behavior / evidence |
|---|---|
| Reversible selection | Set `relaxed_arms` to false (or remove the field) on **idle only** in `apps/avatar-runtime/motion_registry.json`, then restart Avatar. This restores the original close-arm motion without rebuilding anything. The source videos/Blend/GLB and their hashes remain unchanged. |
| Pose gate | `verify_reference_idle.gd`: 750 sequential frames at 30 FPS, both loops and all 70 shoulder/arm descendant transforms checked against the old A-pose; return from pirouette/listen/wave/greet; original model and idle GLB SHA-256 asserted. This gate intentionally does not certify universal collision safety. |
| Actual rendering | The same script with `--display-driver windows` renders front, ±45°, side and back at the same camera/scale/look, plus an original close-arm front comparison loaded without the policy. Local output: `%APPDATA%/Godot/app_userdata/Luo Tianyi Desktop Avatar MVP/reference-idle-2026-09-08/`. |
| Acceptance scope | The sampled idle views separate hands from the skirt. Pirouette is unchanged; listening v2 has its own four-view and transition evidence, still awaiting owner naturalness review. Neither constitutes universal collision-free production acceptance. |
| Phase-1 mocap | Start with gentle torso sway/breathing, small nods and head glances; hands remain clear of skirt, torso and long pigtails. Add a small greeting only after checking its full trajectory. Defer crossed arms, hands on thighs/waist, crouches, high leg lifts and fast spins. Small amplitude alone is not a clearance guarantee. |

## Rebuild on this machine

Run from the repository root. Inputs and intermediate outputs remain outside Git. The idle clip is generated without an external motion file; the pirouette command remains the retargeting reference.

```powershell
& 'D:\steam\steamapps\common\Blender\blender.exe' -b --python scripts\model-pipeline\create_mocap_idle_motion.py -- --target '..\luotianyi_v4_prepared.blend' --landmarks '..\motion-output\mocap-idle-v1\pose-landmarks.json' --output-blend '..\motion-output\mocap-idle-v1\luotianyi_idle_mocap_v1.blend' --output-glb 'apps\avatar-runtime\assets\motions\luotianyi_idle.glb' --action-name idle_mocap_v1 --fps 30
& 'D:\steam\steamapps\common\Blender\blender.exe' -b --python scripts\model-pipeline\verify_mocap_idle_motion.py -- --input '..\motion-output\mocap-idle-v1\luotianyi_idle_mocap_v1.blend' --action idle_mocap_v1
```

```powershell
& 'D:\steam\steamapps\common\Blender\blender.exe' -b --python scripts\model-pipeline\retarget_bvh.py -- --target '..\luotianyi_v4_prepared.blend' --motion '..\motion-sources\cmu\pirouette.bvh' --output-blend '..\motion-output\cmu-pirouette\luotianyi_pirouette.blend' --output-glb 'apps\avatar-runtime\assets\motions\luotianyi_pirouette.glb' --action-name cmu_pirouette --fps 30
```

```powershell
& 'D:\steam\steamapps\common\Blender\blender.exe' -b --python scripts\model-pipeline\create_listen_motion.py -- --target '..\luotianyi_v4_prepared.blend' --output-blend '..\motion-output\listen\luotianyi_listen.blend' --output-glb 'apps\avatar-runtime\assets\motions\luotianyi_listen.glb' --action-name listen_gesture --fps 30
& 'D:\steam\steamapps\common\Blender\blender.exe' -b --python scripts\model-pipeline\verify_listen_motion.py -- --input '..\motion-output\listen\luotianyi_listen.blend' --action listen_gesture
```

`--keep-horizontal-root-motion` preserves source X/Y travel; `--allow-airborne` disables the desktop-oriented lowest-foot lock for genuine jumps. After rebuilding, run the Blender and Godot motion gates in `docs/TESTING.md`; for idle also pass `--require-loop` to `verify_retarget.py`. Do not judge the result only from one render: the verifier samples every frame for finite transforms, ground stability and optional first/last equality, while the Godot checks exercise layer classification, pigtail secondary motion and idle→interaction→idle state transitions.

## Implementation map and next motion work

| Path | Responsibility |
|---|---|
| `scripts/model-pipeline/retarget_bvh.py` | BVH import, rest-orientation retarget, 120→30 FPS sampling, in-place root policy, foot lock, one-action GLB export |
| `scripts/model-pipeline/create_idle_motion.py` | Sparse authored breathing/head/arm poses and an exact 8-second loop on the prepared rig |
| `scripts/model-pipeline/extract_pose_landmarks.py` | Deterministic MediaPipe full-body landmark extraction from a local monocular motion video |
| `scripts/model-pipeline/create_mocap_idle_motion.py` | Smoothed, conservative 12-bone idle retarget with exact loop closure; leaves legs, skirt and model data untouched |
| `scripts/model-pipeline/verify_mocap_idle_motion.py` | Whole-clip finite-transform, loop, per-frame smoothness and motion-envelope gate for the captured idle |
| `scripts/model-pipeline/create_listen_motion.py` | Reference-timed open-palm/fist/open listening sequence on the upper body, both arms and fingers |
| `scripts/model-pipeline/extract_video_reference.py` | Deterministic MP4/MOV/WebM frame extraction through Blender's decoder; reference evidence remains local |
| `scripts/model-pipeline/verify_listen_motion.py` | Whole-action finite-transform, upper-only, scale, hand-height and open/fist/open ordering gate |
| `scripts/model-pipeline/verify_retarget.py` | Whole-clip Blender structural and ground verification |
| `scripts/model-pipeline/render_preview.py` | Keyframe visual renders via `--frame` |
| `apps/avatar-runtime/motion_registry.json` | Clip IDs, paths, loop roles and blend timing; adding a clip should not require another hard-coded loader |
| `apps/avatar-runtime/runtime.gd` | Registry loading, semantic bone-layer filtering, track-path rebinding, idle autoplay, interaction interruption, pigtail secondary motion, playback/cancel/reset and keyboard/bridge trigger |
| `apps/avatar-runtime/verify_motion_asset.gd` | Imported source duration, track, skeleton and sampled-pose gate |
| `apps/avatar-runtime/verify_motion_runtime.gd` | Static-model motion bridge, required-bone and idle-reset gate |

The pirouette remains a technical motion stress clip, while idle and listen are character-facing motions. Next add thinking, speaking-body and greeting clips to the registry; facial mouth shapes remain driven independently by Agent state. The double-pigtail layer covers all 34 skinned bones and retains subtle procedural sway. Garment collision is unresolved and must not be declared complete from proxy-clearance numbers alone. Reference video may be supplied as the original MP4/WebM/MOV—the user does not need to split frames. MediaPipe extraction is used for captured full-body motion, while Blender frame extraction remains available for visual references; neither requires the user to split images manually.
