# 模型版本档案

这里保存可公开提交的版本清单、优化记录和切换规则；受限的 PMX、Blend、GLB、纹理和预览图保存在仓库同级的本地 `model-archive`，不会上传 GitHub。一个可复现版本由“不可变模型文件 + 对应 Git 运行时提交 + 视觉证据 + 验证结果”共同组成，只有验收通过的状态才获得 `1.0`、`1.1`、`1.2` 这样的正式版本号，失败或比例异常的实验态不占版本号、也不会替代已验收快照。

## 当前版本

2026-09-10 Codex：所有者批准正式1.4，源码与本地资产已经冻结，尚未推送远程。[交付、证据与回退](1.4/README.md)。

| 版本 | 状态 | 模型文件 | 运行时提交 | 说明 |
|---|---|---|---|---|
| `1.0` | accepted | 官模运行 GLB `DF55806D…DC6E4A` | `b192291c7a26615c67dae7e4e003ee2d5fa50adb` | 优化前的正常比例基线，旧 560×760 透明窗口 |
| `1.1` | accepted | 与 `1.0` 字节一致 | `0b4f1d061cf19d20aedf59da68ee2a80cf6797a8` | 固定光轴、2× SubViewport、4× MSAA、高 DPI 与防裁切清晰版 |
| `1.2` | accepted | 与 `1.1` 字节一致 | `0629e02e08309667287c0c53fdbcd837f0694b97` | 外部 Toon 调色与立体感版；高光溢出降低，四视角轮廓和官模比例不变 |
| `1.3` | accepted（Codex） | 与 `1.2` 字节一致 | `581a856c51b1de4387896ce5ae283e279ff67d22` | 保守 A-pose、已批准材质精修及 F12 高清截图；[验证与下一阶段](1.3/README.md) |
| `1.4` | accepted（当前，Codex） | 与 `1.3` 字节一致 | `7bb1aa1599e85d60adf329d79d507352a4e6eb9a` | 五官A2材质细节、表情兼容门禁；独立归档注册动作与支持纹理，[正式档案](1.4/README.md) |

`1.0` 至 `1.4` 的 GLB 与可编辑 Blend 都分别保存；虽然当前文件哈希相同，仍保留五个独立副本。1.4起增加带哈希的运行支持资源快照，旧版本清单不追改。中间未通过比例验收的实验态不在档案中。下一次正式优化分配1.5（BaseVersion 1.4）；下方1.3命令仅为历史示例，不可重复创建。

## 本地目录

```text
work/
├─ anime-agent-mvp/
│  ├─ model-versions/              # GitHub：清单、方案、验证记录
│  └─ scripts/model-versions/      # GitHub：快照、验证、切换工具
├─ model-archive/                  # 本地：不可上传的大文件
│  ├─ 1.0/artifacts/
│  ├─ 1.0/previews/
│  ├─ 1.1/artifacts/
│  ├─ 1.1/previews/
│  ├─ 1.2/artifacts/
│  ├─ 1.2/previews/
│  ├─ 1.3/artifacts/
│  ├─ 1.3/previews/
│  ├─ 1.4/artifacts/
│  ├─ 1.4/previews/
│  ├─ 1.4/resources/              # 注册动作含TRES、支持纹理，哈希锁定
│  └─ _recovery/
└─ model-worktrees/                # 本地：按历史提交创建的隔离运行目录
```

## 常用命令

| 目的 | 命令 | 行为 |
|---|---|---|
| 校验全部快照 | `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\model-versions\verify-model-versions.ps1` | 校验清单、Git 提交、文件大小和 SHA-256 |
| 当前目录只换模型资产 | `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\model-versions\switch-model-version.ps1 -Version 1.0` | 原子替换运行 GLB；遇到未知文件先放入 `_recovery` |
| 精确打开历史视觉版本 | `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\model-versions\open-model-version.ps1 -Version 1.0 -Launch` | 在独立 worktree 打开对应代码和模型，不覆盖当前开发目录 |
| 接受下一版 | `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\model-versions\snapshot-model-version.ps1 -Version 1.3 -BaseVersion 1.2 -DisplayName '<版本名称>' -OptimizationPlan '<优化计划>' -OptimizationChanges '<实际改动>' -PreviewDirectory '<验收截图目录>'` | 强制连续版本号和七类标准截图；拒绝覆盖已有版本，复制 Blend/GLB/预览、生成哈希与清单 |

资产切换只改变当前目录的 GLB；当相机、灯光、材质代码或合成方式也发生变化时，必须使用隔离 worktree 才是完整 A/B 对比。不要在有未提交工作的目录里 checkout 历史提交。

## 每版必须记录

| 类别 | 必填内容 |
|---|---|
| 身份与来源 | 版本号、基准版本、状态、时间、源 PMX 哈希、版权/再分发边界 |
| 模型文件 | 可编辑 Blend 与运行 GLB 的本地相对路径、字节数、SHA-256 |
| 结构 | 骨架数、骨骼数、表情数、左右马尾链长度、材质/UV/权重是否变化 |
| 几何比例 | 与基准版本对比网格顶点/面、表情形变、骨架静置结构、对象变换、世界边界，以及 Godot 四视角 Alpha 轮廓；视觉调色版必须全部完全一致 |
| 优化 | 原目标、计划、实际改动、明确未改内容、被放弃方案、已知问题 |
| 运行环境 | Blender、Godot、MMD Tools、VRM 插件版本和对应 Git 提交 |
| 视觉证据 | 正面、左右侧面、背面、最大缩放、中性脸、极端表情；动画版另加关键帧 |
| 性能与回归 | 帧耗时、最大缩放裁切、透明穿透、旋转、动作、聊天和哈希门禁 |
| 回退 | 资产切换命令、精确历史运行命令和上一已验收版本 |

每次优化按“确认当前版本完整 → 建立实验 → 通过结构/视觉/性能门禁 → 分配下一个版本号 → 复制不可变快照 → 更新清单与截图 → 提交 Git”的顺序执行。未来版本必须在传入目录中提供 `front`、`left`、`right`、`back`、`max-zoom`、`neutral-face`、`expression-extremes` 七张 PNG/JPG；预览图默认留在本地，清单只记录文件名和哈希，避免未经确认重新分发角色素材。`1.0`/`1.1` 是建立制度前补录的历史版本，当前预览槽位为空，但代码和模型均可通过隔离 worktree 重现，下一轮优化前应先补拍两版基准图。
