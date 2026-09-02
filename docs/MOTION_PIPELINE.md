# Authored motion pipeline

The authored-motion path now contains a tracked registry plus three local clips: a 12.47-second monocular-mocap looping idle, a CMU BVH pirouette used as a full-body stress test, and an 8.53-second reference-rebuilt listening gesture. Godot keeps `assets/luotianyi_v4.glb` for materials and mesh appearance, extracts animation tracks from each ignored motion GLB, filters them by semantic bone layer, rewrites their bone paths to the static skeleton and discards the generated model instances. This avoids the washed-out materials produced by Blender's generic glTF export; idle starts automatically, interactions interrupt it, and completion returns to idle.

## Current artifact and behavior

| Property | Verified value |
|---|---|
| Registry | `apps/avatar-runtime/motion_registry.json`; tracked; defines clip IDs, local paths, semantic `bone_layer`, loop policy and cross-fade duration |
| Idle | `idle_mocap_v1`, 374 Blender frames at 30 FPS, 12.47 seconds; 12 captured upper-body bones; lower body fixed; exact first/last pose match; maximum per-frame rotation 0.03459 rad |
| Pirouette source | CMU BVH mirrored by the Three.js examples; 592 frames at 120 FPS, 4.925 seconds; [CMU usage terms](https://mocap.cs.cmu.edu/) permit use of the data but not direct resale |
| Retarget | 19 core humanoid bones; target has 751 bones and 49 shape keys including Basis |
| Output | `cmu_pirouette`, 149 frames at 30 FPS; horizontal root motion removed; lowest foot locked to the original ground height by default |
| Listening gesture | `listen_gesture`, 256 Blender frames at 30 FPS, 8.5 seconds (8.533 seconds after glTF import); 33 upper-body/hand bones; reference order is open palm by ear → gentle fist → open palm hold; lower body has no tracks |
| Runtime motion assets | `luotianyi_idle.glb`: 23,070,740 bytes, SHA-256 `5CF15A1D3E657CF76E5F58E33C9D3593A14494B89817AD2A910D57CABF9D433A`; `luotianyi_pirouette.glb`: 23,114,580 bytes, SHA-256 `1FEFBF0667711845E4FC6E0574D57D74C8982E15AA76A2A25BB9192BE1FAA284`; `luotianyi_listen.glb`: 23,136,336 bytes, SHA-256 `975146830FEC6920D959334FBB0FFD7539B4C7EB4716703CF600D0DE705FE770` |
| Godot bridge | 106 upper-body idle, 124 full-body pirouette and 127 upper-body listen tracks retained after rebinding; `voice.state=recording` starts listen, its final pose is held while recording, and transcribing/idle returns to authored idle |
| Bone masks | `upper_body` follows `上半身` descendants and explicitly includes both complete 17-bone `MaWei` chains; `lower_body` covers center/waist, `下半身`, legs, skirt and foot IK; `full_body` accepts every target bone |
| Pigtail validation | One mesh; 34/34 pigtail bones present; both parent chains continuous from `首`; every chain bone has non-zero skin weights; runtime check confirms upper-only classification |
| Garment baseline | The official model exposes 16 complete three-bone skirt chains, but this repository intentionally applies no custom cloth/contact solver. The previous runtime spring/panel/vertex-overlay experiment was removed after it failed topology and natural-motion acceptance; work continues in `SummerTianYi/anime-agent-cloth-physics` |
| Trigger | Press `P` for pirouette, `G` for listen, use the interaction menu, or hold the Voice button to start the semantic listen path; `ANIME_AGENT_USE_AUTHORED_MOTION=0` disables local motion loading |
| Fallback | If the ignored motion asset is absent, the avatar and all existing procedural actions still start normally |

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
