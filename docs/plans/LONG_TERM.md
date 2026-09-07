# 跨仓长期方案（Long-Term Direction Board）

> 定位：存放"暂不排期但方向已定"的长期项，覆盖洛天依项目的四个仓库（anime-agent-mvp 主仓、anime-agent-workbench 训练场、anime-agent-tts 声线、anime-agent-cloth-physics 裙摆物理）。每项标注：归属仓、当前状态、下一步。执行时不在此立项，而是拆进主仓 HANDOFF §3 未开工清单或对应专项仓，并把状态回写到这里。
>
> 维护：当值 agent 收工时更新状态；新增长期项需所有者点头。

| 方向 | 归属仓 | 当前状态 | 下一步 |
|---|---|---|---|
| 语音训练（声线迭代） | anime-agent-tts（私有） | GPT-SoVITS v2Pro 天依声线已训练并上线 sidecar（2026-09-04），语料切片/转写/训练/评测脚本齐备（`scripts/run_training.py` 等）；仓内**零文档**（README 已补） | 情绪/语速细分音色、长句稳定性评测（`eval_grid.py` 已有底子）；训练语料扩充由所有者定 |
| 基模训练 | anime-agent-tts | GPT-SoVITS 底模微调能力随仓具备，未做专项微调 | 若做：所有者提供语料与目标；沿用"先沙箱评测、后上线"的验收口径 |
| 动作模组（角色动作集） | anime-agent-mvp | 已验收：待机/旋转/倾听 + 程序化手势；thinking/speaking/greeting 三片缺失（KI-004） | 采买/动捕三片 → 走 MOTION_PIPELINE 门禁；裙子物理独立推进（cloth-physics 仓，KI-014） |
| 键鼠控制（最高危） | anime-agent-mvp | 蓝图明确缓行，零实现 | 设计专用考试（T4？）：单步确认执行 + 屏幕视觉闭环 + 急停；未过考试绝不接入 |
| 真实视觉 | anime-agent-mvp | ✅ 2026-09-07 上线：GLM 原生多模态 + 隐私 ask 档（换模型=改 .env 三行） | 本地 VLM 保留为隐私/断网备胎，不排期 |
| Spark Adapter | anime-agent-mvp | Spike 暂缓，不阻塞本地闭环 | 有官方可调用面时再做 Spike（MVP.md §6 验证清单） |
| 考试回归自动化 | anime-agent-workbench | T0-T3/C/D 均为一次性脚本，人工跑（KI-017） | 把题库固化为可重跑回归管线，能力变更可廉价复检 |
| 记忆成熟化 | anime-agent-mvp | facts 分级落库+词法检索已上线；pending 审阅 UI 缺（KI-016）；矛盾记忆更新未考 | T2+ 进阶考试（矛盾记忆、长对话压测）→ 审阅 UI |
| 常驻生命感（M3） | anime-agent-mvp | 开机自启/守护、Idle 触发未做（KI-002/KI-003） | 主仓当前主战场，见 HANDOFF §3 |
| 打包分发 | anime-agent-mvp | 未开始 | 自启与守护稳定后再评估安装器形态 |
