# Local model asset pipeline

The Luo Tianyi model and all derived PMX, texture, Blend, VRM, GLB and preview files remain local because the runtime binary exceeds GitHub's regular file limit and redistribution rights are not proven in this repository. The versioned pipeline exists to make transformation reproducible for a user who already possesses an authorized source; it is not an acquisition or redistribution mechanism.

## Current accepted artifact

| Property | Value |
|---|---|
| Runtime path | `apps/avatar-runtime/assets/luotianyi_v4.glb` |
| Current-machine path | `D:\UserData\Administrator\Documents\Codex\2026-08-28\https-github-com-summertianyi-anime-agent\work\anime-agent-mvp\apps\avatar-runtime\assets\luotianyi_v4.glb` |
| Bytes | 128,621,144 |
| SHA-256 | `DF55806D343D149B41C20D0EF074373CAFCA2379212FD8691E998EA6CDDC6E4A` |
| Source-stage equivalent | Local `luotianyi_v4_preview.vrm`; byte-identical because VRM is a binary glTF container |
| Runtime checks | One skeleton, eight cached action bones, two pigtail roots and 48 expressions |

## Reproduction stages

| Stage | Input → output | Versioned command |
|---|---|---|
| 1. PMX import | Authorized `.pmx` → imported `.blend` | `blender.exe --background --python scripts/model-pipeline/import_pmx.py -- --input <source.pmx> --output <imported.blend>` |
| 2. Humanoid/VRM export | Imported `.blend` → prepared `.blend` + `.vrm` | `blender.exe --background --python scripts/model-pipeline/prepare_vrm.py -- --input <imported.blend> --prepared <prepared.blend> --output <avatar.vrm>` |
| 3. VRM inspection | `.vrm` → console summary | `blender.exe --background --python scripts/model-pipeline/verify_vrm.py -- --input <avatar.vrm>` |
| 4. Optional preview | Prepared `.blend` → `.png` | `blender.exe --background --python scripts/model-pipeline/render_preview.py -- --input <prepared.blend> --output <preview.png>` |
| 5. Runtime placement | Accepted `.vrm` → `apps/avatar-runtime/assets/luotianyi_v4.glb` | Copy locally, then run `scripts/check-local-assets.ps1` |
| 6. Godot import | Local GLB → ignored `.godot` cache and extracted textures | Open/run Godot project; generated files stay ignored |
| 7. Authored motion | Prepared `.blend` + authorized `.bvh` → grounded animation `.blend` + local motion `.glb` | Use `scripts/model-pipeline/retarget_bvh.py`, then the Blender/Godot gates in `docs/MOTION_PIPELINE.md` |

The original import used scale `0.08`, cleaned the MMD model, preserved morphs and fixed bone order. VRM humanoid assignment is automatic and the accepted visual export excludes animation because the source contains no useful authored clips. Blender 5.2.1 plus VRM add-on 4.5.0 currently emits duplicate VRM0 humanoid-bone warnings while importing this VRM, but the verified command exits successfully and reports VRM 1.0, 321 objects, one mesh, one armature, 48 shape keys, 160 spring-bone colliders and 160 collider groups; treat a changed summary or nonzero exit as a regression, while the known warnings alone are not a failure. Authored clips are separate ignored GLBs whose tracks are rebound by `runtime.gd`; never replace the accepted visual model with Blender's generic animated GLB because its materials are visibly degraded in Godot. Pigtail front-drape offsets are not baked into the model. Before replacing the current GLB, verify the exact pigtail roots `MaWei_R_0_1` and `MaWei_L_0_1`, inspect front and rear hair separately, and reject any result that clips through the torso or lifts rear hair incorrectly.

## Local-only artifact map

The source archive, extracted PMX/textures, imported/prepared Blend files and exported VRM paths are listed in `docs/LOCAL_MACHINE.md`. Do not copy BowlRoll cookies, download headers, source archives, model binaries or renders into this repository. If redistribution rights are later confirmed, treat that as a separate owner-approved publishing decision and review Git LFS or release assets; do not rewrite history or force-add the current ignored files.
