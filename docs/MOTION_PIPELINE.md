# Authored motion pipeline

The authored-motion path now contains a tracked registry plus two local clips: an 8.03-second subtle looping idle generated from sparse Blender poses, and a CMU BVH pirouette used as a full-body stress test. Godot keeps `assets/luotianyi_v4.glb` for materials and mesh appearance, extracts animation tracks from each ignored motion GLB, rewrites their bone paths to the static skeleton and discards the generated model instances. This avoids the washed-out materials produced by Blender's generic glTF export; idle starts automatically, interactions interrupt it, and completion returns to idle.

## Current artifact and behavior

| Property | Verified value |
|---|---|
| Registry | `apps/avatar-runtime/motion_registry.json`; tracked; defines clip IDs, local paths, loop policy and cross-fade duration |
| Idle | `idle_breathing`, 241 Blender frames at 30 FPS, 8.0 seconds (8.033 seconds after glTF import); 12 authored upper-body bones; feet fixed; exact first/last pose match |
| Pirouette source | CMU BVH mirrored by the Three.js examples; 592 frames at 120 FPS, 4.925 seconds; [CMU usage terms](https://mocap.cs.cmu.edu/) permit use of the data but not direct resale |
| Retarget | 19 core humanoid bones; target has 751 bones and 49 shape keys including Basis |
| Output | `cmu_pirouette`, 149 frames at 30 FPS; horizontal root motion removed; lowest foot locked to the original ground height by default |
| Runtime motion assets | `luotianyi_idle.glb`: 23,057,704 bytes, SHA-256 `33E3FE13721F0D01929C6CB4AF22A408C3485F20512066975ED102DC693CC21B`; `luotianyi_pirouette.glb`: 23,114,580 bytes, SHA-256 `1FEFBF0667711845E4FC6E0574D57D74C8982E15AA76A2A25BB9192BE1FAA284` |
| Godot bridge | 115 idle and 124 pirouette tracks retained after rebinding; normal-material static model preserved; idle loops and resumes after interaction |
| Trigger | Press `P`, or click the character → `互动` → `旋转动作（样片）`; `ANIME_AGENT_USE_AUTHORED_MOTION=0` disables local motion loading |
| Fallback | If the ignored motion asset is absent, the avatar and all existing procedural actions still start normally |

## Rebuild on this machine

Run from the repository root. Inputs and intermediate outputs remain outside Git. The idle clip is generated without an external motion file; the pirouette command remains the retargeting reference.

```powershell
& 'D:\steam\steamapps\common\Blender\blender.exe' -b --python scripts\model-pipeline\create_idle_motion.py -- --target '..\luotianyi_v4_prepared.blend' --output-blend '..\motion-output\idle\luotianyi_idle.blend' --output-glb 'apps\avatar-runtime\assets\motions\luotianyi_idle.glb' --action-name idle_breathing --fps 30
```

```powershell
& 'D:\steam\steamapps\common\Blender\blender.exe' -b --python scripts\model-pipeline\retarget_bvh.py -- --target '..\luotianyi_v4_prepared.blend' --motion '..\motion-sources\cmu\pirouette.bvh' --output-blend '..\motion-output\cmu-pirouette\luotianyi_pirouette.blend' --output-glb 'apps\avatar-runtime\assets\motions\luotianyi_pirouette.glb' --action-name cmu_pirouette --fps 30
```

`--keep-horizontal-root-motion` preserves source X/Y travel; `--allow-airborne` disables the desktop-oriented lowest-foot lock for genuine jumps. After rebuilding, run the Blender and Godot motion gates in `docs/TESTING.md`; for idle also pass `--require-loop` to `verify_retarget.py`. Do not judge the result only from one render: the verifier samples every frame for finite transforms, ground stability and optional first/last equality, while the Godot checks exercise idle→interaction→idle state transitions.

## Implementation map and next motion work

| Path | Responsibility |
|---|---|
| `scripts/model-pipeline/retarget_bvh.py` | BVH import, rest-orientation retarget, 120→30 FPS sampling, in-place root policy, foot lock, one-action GLB export |
| `scripts/model-pipeline/create_idle_motion.py` | Sparse authored breathing/head/arm poses and an exact 8-second loop on the prepared rig |
| `scripts/model-pipeline/verify_retarget.py` | Whole-clip Blender structural and ground verification |
| `scripts/model-pipeline/render_preview.py` | Keyframe visual renders via `--frame` |
| `apps/avatar-runtime/motion_registry.json` | Clip IDs, paths, loop roles and blend timing; adding a clip should not require another hard-coded loader |
| `apps/avatar-runtime/runtime.gd` | Registry loading, track-path rebinding, idle autoplay, interaction interruption, playback/cancel/reset and keyboard/bridge trigger |
| `apps/avatar-runtime/verify_motion_asset.gd` | Imported source duration, track, skeleton and sampled-pose gate |
| `apps/avatar-runtime/verify_motion_runtime.gd` | Static-model motion bridge, required-bone and idle-reset gate |

The pirouette remains a technical acceptance clip, while the idle is the first character-facing motion. Next add thinking, speaking-body and greeting clips to the registry; facial mouth shapes remain driven independently by Agent state. Hair, long pigtails and skirt still lack convincing secondary dynamics, so spring-bone or targeted physics tuning is required. Reference video may be supplied as the original MP4/WebM/MOV—the user does not need to split frames—but this machine currently has no `ffmpeg`/OpenCV decoder, so the Agent must provision a local decoder and extract motion-reference frames automatically before analysis. Do not switch to video-to-frames as the runtime, Unity or Unreal: reference frames guide skeletal authoring but do not replace the working 3D Godot stack.
