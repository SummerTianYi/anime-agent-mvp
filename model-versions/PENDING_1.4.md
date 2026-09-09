# Codex — 1.4 A2 本地实装，待提交冻结（2026-09-10）

所有者已批准 A2 效果与实装，未在本轮授权 commit/push。当前运行时默认 1.4；正式 `index.json` 仍记录最后冻结版 1.3。这是明确的本地增量，不伪造运行时提交，不覆盖任何 1.0–1.3 快照。已有四版的文件/提交校验全部通过。

| 项目 | 内容 |
|---|---|
| 改动 | `model_look_v14.gd` + `face_detail_v14.gdshader`，复制 face 材质叠加已批准 A2：更宽柔和鼻部色彩线索、更清晰原有唇色、轻微耳内细节；其余表面复用 1.3 |
| 不变 | 网格、UV、法线、原纹理、蒙皮、骨架、48 形变、身体比例、瞳色、全部动作、Core/TTS/UI |
| GLB SHA-256 | `df55806d343d149b41c20d0ef074373cafca2379212fd8691e998ea6cddc6e4a` |
| Blend SHA-256 | `886b61339707c289157f7d762a9b44df26e9cfdfa92bd1d5ac518d7116b7672d` |
| 正式表情门禁 | `apps/avatar-runtime/lookdev/verify_face_expressions.gd`：48形变×两权重、8组合、180帧插值/回中、五朝向及回中，共122对照；两轮通过，非声学/真实 TTS 测试 |
| 最终 GPU 证据 | `C:/Users/26052/AppData/Roaming/Godot/app_userdata/Luo Tianyi Desktop Avatar MVP/face-expression-regression/2026-09-10T00-18-08-35684/`，report.json、104对照原图、9张拼图、180序列帧；拼图已逐页人工检查 |
| 独立像素复核 | `check_face_expression_images.py <证据目录>`：104对照全像素 Alpha 差异0；180帧非空；材质回退 RGB 平均误差最大0.000000936 |
| 性能范围 | 640×640离屏视口 GPU P95：1.3约0.171ms、1.4约0.156ms，仅门禁范围内无明显退化，不解释为性能提升或整桌面帧率 |
| 本地独立备份 | `D:/UserData/Administrator/Documents/Codex/2026-08-28/https-github-com-summertianyi-anime-agent/work/model-archive/_pending/1.4-A2-20260910/`，保存本轮 GLB/Blend、原 HEAD 源码压缩包、修改源码覆盖层及实际启动预览；不是正式版本清单 |
| 回退 | 在本地 `.env` 设置 `ANIME_AGENT_MODEL_LOOK=1.3` 后重启 Avatar；1.1/1.2 同样可选。完整旧版用既有隔离 worktree 工具，不在脏工作树 checkout |

正式冻结的最短路径：获提交授权后只提交 Codex 文件，使用真实新提交及七类标准预览运行 `scripts/model-versions/snapshot-model-version.ps1 -Version 1.4 -BaseVersion 1.3 ...`，再校验并按授权推送。不能拿父提交3eef97d冒充新外观。A1/A2离线资源独立保留。脸部改善属于色彩线索，不是新增鼻部几何；小桌宠尺寸及头发遮挡耳朵的收益有限，未解决通用穿模。
