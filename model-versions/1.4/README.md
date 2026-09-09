# 1.4 五官 A2 正式版 — Codex，2026-09-10

所有者已认可实装效果并批准正式交付。源码固定在 `7bb1aa1599e85d60adf329d79d507352a4e6eb9a`，本轮为本地冻结，尚未推送远程。相比1.3，只在脸部材质叠加更宽柔和的鼻部线索、较清晰的原有唇色和轻微耳内细节；未修改官模几何、UV、法线、蒙皮、比例、原纹理、眼睛、48形变或已验收动作。材质不是鼻部几何重建；小尺寸收益有限，耳朵仍受头发遮挡。

| 交付项 | 证据与边界 |
|---|---|
| 结构与兼容 | 官模 GLB/Blend 哈希与1.3一致；703运行骨、48形变、其他22材质不变；122组表情对照、48形变×两权重、8组叠加、180帧连续口型和回中通过；104对照全像素Alpha差异0 |
| 回归 | 输入、会话、工具卡、透明画布、750帧待机、倾听进退及路径、大动作GPU渲染通过；191项隔离Core测试、桌面构建、文档守卫通过。未重新测试真实语音，不声称解决通用穿模 |
| 实装 | 前轮已重启Avatar，日志确认1.4、48形变及Core已连接；本轮仅冻结归档，不再次打断角色或重启Core/TTS |
| 独立恢复演练 | 从冻结源码和归档重建 `../model-worktrees/1.4`，三条动作/倾听路径/输入及完整122对照、180帧GPU表情门禁均通过；证据 `user://face-expression-regression/2026-09-10T00-40-47-29868`，全像素Alpha复核通过。首次测试早于导入完成而失败，等导入结束重跑；旧倾听参考缺失也在冻结完成前补入 |
| 正式资产 | 仓库同级 `model-archive/1.4/artifacts/` 为独立只读 GLB/Blend；`previews/` 为七类真实Godot截图；`resources/` 为三条注册动作（含倾听TRES）及八个支持纹理，逐项路径/大小/哈希见manifest |
| 测试原始证据 | `C:/Users/26052/AppData/Roaming/Godot/app_userdata/Luo Tianyi Desktop Avatar MVP/face-expression-regression/2026-09-10T00-18-08-35684/`；本地 `_pending/1.4-A2-20260910/expression-evidence/` 亦有独立备份 |
| 七类预览 | `C:/Users/26052/AppData/Roaming/Godot/app_userdata/Luo Tianyi Desktop Avatar MVP/model-1.4-freeze/2026-09-10T00-35-03-34848/`；全身四视图、最大缩放、面部中性/极值，manifest记录副本哈希 |

仅切换外观：本地 `.env` 设置 `ANIME_AGENT_MODEL_LOOK=1.3` 后重启Avatar；清空该值或设1.4恢复本版。完整恢复本版：从主仓运行 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/model-versions/open-model-version.ps1 -Version 1.4 -Launch`，它使用独立 `../model-worktrees/1.4`，不覆盖当前开发目录，1.4起优先读取归档的动作/纹理而非未来工作树素材。保留1.0–1.3历史：它们的旧清单没有运行支持资源快照，外观/模型仍按旧提交恢复，动作仍走历史兼容分支，不把旧版完整动作依赖声明为已补档。后续正式优化分配1.5，不覆盖1.4。
