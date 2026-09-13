# Anime Agent MVP — 项目说明与文件手册

本文用于项目文档提交，介绍当前已实现的功能，以及各目录和关键文件的职责；不是运行安装包，也不是开发过程、训练记录或问卷答案。

项目仓库：<https://github.com/SummerTianYi/anime-agent-mvp>

整理日期：2026-09-13

整理者：Codex。项目由所有者与 Codex、Claude、zcode 协作完成，具体贡献保留在 `docs/CONTRIBUTIONS.md` 和 Git 提交记录中；本文不改变既有归属。

## 1. 当前交付的功能

| 功能 | 当前实现 |
|---|---|
| 3D 桌面角色 | Godot 独立透明窗口显示洛天依；透明区域鼠标穿透，支持拖动、缩放、转身、位置保存和角色菜单。角色渲染与桌面画布分离，减少窗口边界裁切和离轴比例失真。 |
| 外观与截图 | 当前验收外观为 1.4（五官 A2），包含此前的清晰度、光照层次和五官优化；保留身体比例与既有骨架。F12 可导出角色透明高清截图，不截取其他桌面内容。 |
| 待机与互动 | 保守 A-pose 待机，配合身体轻晃及转头；已接入倾听、思考、点头、挥手、转身等互动。部分动捕动作经过骨骼重定向和人工接触适配，不是任意视频的一比一自动复刻。 |
| 表情与口型 | 已接入微笑、眨眼、惊讶、生气、流泪等表情，以及说话口型；增强表情使用已有形变组合，处理表情切换、眨眼、说话和恢复的衔接。 |
| 思考动作 | 托下巴、另一手轻托肘部、左右观察；两条完整辫子的动作与身体一起烘焙，结束后回到待机。运行时不依赖离线物理预览工具。 |
| 退出告别 | 正常关闭 Godot 窗口时播放挥手、轻摇头、闭眼微笑；正常情况下等待本次告别动画和语音共同结束后退出。异常情况下有 8 秒退出兜底，强制终止进程不保证播放动画。 |
| 文字对话 | 角色内聊天浮层、流式回复、工具执行状态、推理强度选择；支持新建、切换、删除会话、自动标题和历史回载。 |
| 文本与视觉协作 | 当前验收配置为 DS 文本主脑与 StepFun 视觉模型：视觉工具获得画面分析后由主脑组织回答。访问屏幕需要权限确认，不默认采集桌面。 |
| 语音输入 | 按键录音、唤醒词、语音转文字及取消；包含录音设备异常检测与有限恢复。真实使用需要麦克风、驱动及本地识别模型。 |
| 角色语音 | Core 调用 GPT-SoVITS sidecar，支持分片合成、播放、口型联动和打断。启动链等待语音预热，看护进程负责运行期恢复及关窗后的资源释放。 |
| 本地记忆 | SQLite 保存会话、消息、事件和经过规则筛选的记忆；支持事实检索与记忆手帐卡片管理。公开仓库只包含实现和初始数据结构，不包含所有者的真实记忆库。 |
| 工具与权限 | 文件读取、检索、目录查看、时间、屏幕视觉等工具；写文件和命令执行受路径、白名单及确认约束。通过 MCP 接入浏览器、搜索、GitHub、邮件、网盘等外部能力，需另行配置和授权。 |
| 启动与恢复 | 日常唯一入口为根目录 `start-anime-agent.cmd`；启动器识别既有会话并避免重复拉起，守护按项目和进程身份管理 Core/TTS，不通过批量结束全部 Python 进程来恢复服务。 |

## 2. 总体结构

用户通过 Godot 角色窗口输入文字或语音。Godot 与 Python Core 通过本地 WebSocket 交换消息，Core 负责对话、权限、记忆、工具以及语音调度；回复携带的状态和表情信息驱动角色动画。TTS 是独立语音服务，不与 Core 共用 Python 环境。`apps/desktop` 是辅助调试/设置界面，不是正式角色窗口。

```text
anime-agent-mvp/
├── PRD.md                  本项目说明与文件手册
├── README.md               仓库入口、当前状态和启动说明
├── start-anime-agent.cmd    Windows 日常启动入口
├── .env.example            配置字段模板，不含真实密钥
├── apps/
│   ├── avatar-runtime/     Godot 角色、交互、动画、外观及验证代码
│   └── desktop/            Tauri / React 辅助桌面界面
├── services/agent-core/    Python 后端、对话与工具服务、单元测试
├── scripts/                启动/守护、资产管理和自动验证脚本
├── tools/                  邮件、网盘 MCP 启动适配与兼容实现
├── docs/                   协议、部署边界、维护说明与协作手册
├── model-versions/         外观版本清单、哈希和恢复说明
├── packages/shared/        共享模块预留目录，当前不是独立运行服务
└── .github/workflows/      GitHub 自动检查
```

以下路径均相对本仓库，不依赖开发者电脑上的绝对路径。目录中的第三方安装依赖由锁文件描述，不逐项列出生成的依赖文件。

## 3. Godot 角色与动画文件

| 文件或目录 | 用途 |
|---|---|
| `apps/avatar-runtime/project.godot` | Godot 项目配置、窗口及渲染设置。 |
| `apps/avatar-runtime/main.tscn` | 角色运行场景及其节点组织。 |
| `apps/avatar-runtime/launcher.gd` | 运行入口与场景启动衔接。 |
| `apps/avatar-runtime/runtime.gd` | 角色主控制器：加载模型、连接 Core、响应事件、调度动画/表情/口型及输入。 |
| `apps/avatar-runtime/interaction_ui.gd` | 聊天、互动、会话与工具状态等角色界面逻辑。 |
| `apps/avatar-runtime/effort_slider.gd` | 推理强度选择控件。 |
| `apps/avatar-runtime/motion_registry.json` | 动作注册、资源位置、用途及播放配置；包括待机、旋转样片、倾听、思考和退出告别。 |
| `apps/avatar-runtime/emotion_presets.gd` | 正式表情 1.0：惊讶、生气、折中版哭泣的形变组合、强度与持续时间。 |
| `apps/avatar-runtime/farewell_exit.gd` | 正常退出时的告别动画、一次性触发与异常退出兜底。 |
| `apps/avatar-runtime/farewell_speech_gate.gd` | 将本次退出请求的动画完成与语音完成关联，排除旧语音或迟到事件。 |
| `apps/avatar-runtime/model_look_v13.gd`、`model_look_v14.gd` | 已有外观版本的运行时材质/细节配置。当前验收使用 1.4，旧版本用于兼容与回退。 |
| `apps/avatar-runtime/face_detail_v14.gdshader` | 1.4 五官细节的着色器实现。 |
| `apps/avatar-runtime/portrait_capture.gd` | 角色专用高清透明截图导出。 |
| `apps/avatar-runtime/assets/README.md` | 受限角色、纹理及动作资源的本地放置说明；二进制不公开入库。 |
| `apps/avatar-runtime/mocap/` | 倾听、思考、告别的动作制作、冻结和回归代码及资源契约；原始真人视频、候选成片不属于公开交付。 |
| `apps/avatar-runtime/lookdev/` | 外观与表情的离线对照渲染、验证工具；不是日常运行必需的后台服务。 |
| `apps/avatar-runtime/verify_*.gd` | 输入、UI、动作、画布、表情和告别行为的回归入口；不是给最终用户运行的交互菜单。 |

### 表情与物理的边界

正式增强表情复用原模型形变槽，并处理与眨眼、说话口型的切换；哭泣使用既有泪滴效果，不是流体模拟。当前动作为逐条验收的角色适配结果，**没有交付适用于所有未来动捕动作的全身零穿模物理系统**。旋转样片主要用于测试，不作为任意高难度动作都自然且无接触问题的保证。

## 4. Core 服务文件

下表文件均位于 `services/agent-core/`。

| 文件或目录 | 用途 |
|---|---|
| `pyproject.toml` | Python 包声明、版本要求，以及测试、语音和工具的可选依赖。 |
| `agent_core/main.py` | FastAPI/HTTP/WebSocket 服务入口；连接会话、文本/语音消息、Provider 配置和运行状态。 |
| `agent_core/harness.py` | 角色身份与回复协议、模型请求/回复规范化、表情及手势映射。当前运行规则不是私人训练对话集。 |
| `agent_core/agent_loop.py` | 模型与工具之间的多步执行循环、预算及错误反馈。 |
| `agent_core/tools.py` | 内置工具实现、工具注册与执行边界。 |
| `agent_core/permissions.py` | allow/ask/deny 权限判断、用户确认、路径和命令约束。 |
| `agent_core/mcp_host.py` | 外部 MCP 子进程的连接、工具清单及调用；兼容 Windows 带空格和引号的启动参数。 |
| `agent_core/storage.py` | SQLite 数据结构、会话/消息/事件/记忆持久化。 |
| `agent_core/memory_retrieval.py` | 从已有事实中检索与本轮对话相关的记忆。 |
| `agent_core/proactive.py` | 主动问候、免打扰时段和冷却规则。 |
| `agent_core/voice.py` | 麦克风采集、取消、语音识别及设备异常处理。 |
| `agent_core/wake_word.py`、`voice_text.py` | 唤醒词、忙碌/回声抑制及识别文本清理。 |
| `agent_core/speech.py` | TTS sidecar 客户端、健康状态、合成和播放事件调度；不包含声线模型权重。 |
| `agent_core/song_catalog.py`、`data/luotianyi_original_songs.json` | 原创曲种子资料及按需检索；不包含完整歌词或录音。 |
| `agent_core/data/wake_tianyi.txt` | 唤醒相关的文本资源，不是声学模型。 |
| `tests/` | 可复现的自动回归代码，使用模拟服务与临时数据；不包含用户真实测试聊天。 |

## 5. 启动、辅助界面与工具文件

| 文件或目录 | 用途 |
|---|---|
| `start-anime-agent.cmd` | 用户正常启动入口，委托 PowerShell 启动链。 |
| `scripts/start-mvp.ps1` | 配置与依赖检查，拉起或复用当前项目的 Core、Godot 及语音链。 |
| `scripts/startup-common.ps1` | 端口、健康、进程归属、会话状态等启动公共逻辑。 |
| `scripts/core_watchdog.ps1` | Core 会话看护、恢复与退出清理。 |
| `scripts/watch-tts-session.ps1`、`tts-lifecycle.ps1` | TTS 就绪、看护、恢复、代际归属与关窗清理。 |
| `scripts/run-core.ps1`、`run-avatar-runtime.ps1` | 分别启动后端或角色的开发辅助入口。 |
| `scripts/start-tianyi.ps1`、`start-tianyi.bat` | 旧入口兼容；日常仍使用根 CMD。 |
| `scripts/check-local-assets.ps1` | 核对受限本地资源是否在位及哈希是否符合契约。 |
| `scripts/model-versions/`、`model-versions/` | 外观版本登记、快照/切换/核验工具与哈希清单；旧二进制档案不随公开仓库上传。 |
| `scripts/model-pipeline/` | 资产导入、重定向、视频参考提取与动作验证工具；不是必须随角色常驻的程序。 |
| `scripts/test-startup.ps1`、`test-tts-lifecycle.ps1`、`scripts/tests/` | 启动、退出与语音恢复的隔离验证。进程故障测试必须使用独立副本，不能作用于正在使用的角色窗口。 |
| `scripts/check_docs_consistency.py` | 检查文档测试数量、环境变量和工具描述是否与代码一致。 |
| `tools/gmail-mcp.cmd` | 邮件 MCP 启动适配；实际账户授权由使用者提供。 |
| `tools/gdrive-mcp.cmd` | 启动仓库内网盘兼容实现，并传递外部配置。 |
| `tools/gdrive/index.mjs` | Google Drive 只读 MCP 资源/搜索实现，保留上游业务处理逻辑。 |
| `tools/gdrive/oauth.mjs` | OAuth 应用身份及令牌加载、刷新兼容处理；无内置账户凭据。 |
| `tools/gdrive/check-auth.mjs` | 可选鉴权诊断；需要账户所有者明确授权，不是普通离线测试。 |
| `tools/gdrive/oauth.test.mjs` | 无真实凭据、无远程请求的 OAuth 回归测试。 |
| `tools/gdrive/package.json`、`package-lock.json`、`LICENSE` | 网盘模块依赖、锁定版本及上游 MIT 许可；`node_modules` 不入库。 |
| `apps/desktop/src/App.tsx`、`main.tsx`、`styles.css` | Tauri/React 辅助界面、启动挂载与样式。 |
| `apps/desktop/src-tauri/` | 辅助桌面壳的 Rust/Tauri 配置。 |
| `package.json`、`pnpm-workspace.yaml`、`pnpm-lock.yaml` | 前端工作区命令、包组织及依赖锁定。 |
| `.github/workflows/ci.yml` | 自动运行 Core 测试、启动/语音逻辑检查、文档一致性和前端构建。 |

## 6. 文档入口

| 文档 | 用途 |
|---|---|
| `README.md` | 项目概览和使用入口。 |
| `docs/DELIVERY_STATUS.md` | 本次源码整合的公开范围、验证与未交付边界；不附私人原始日志。 |
| `docs/AVATAR_BRIDGE.md` | Core 与 Godot 的事件、工具及状态协议。 |
| `docs/HANDOFF.md` | 开发接手总纲、模块边界与恢复流程。 |
| `docs/CONTRIBUTIONS.md` | Codex、Claude、zcode 的贡献与阶段归属。 |
| `docs/TESTING.md`、`VERIFICATION_SPEC.md` | 自动测试入口和实机验证规范。 |
| `docs/STARTUP_REPAIR_STATUS.md`、`TTS_REPAIR_STATUS.md` | 已有启动与语音恢复实现说明及限制。 |
| `docs/FAREWELL_EXIT.md`、`MOTION_PIPELINE.md` | 退出动作与动捕资源契约。 |
| `docs/TTS_HANDOFF.md`、`ZCODE_HANDOFF.md` | 语音及其他模块的历史交接索引，不替代当前 PRD 状态。 |
| `docs/plans/README.md` | 所有 Agent 长远方案手册入口。 |
| `docs/plans/MODEL_OPTIMIZATION.md` 等 | 模型、Agent、UI 等长期方案入口；计划不等于已经实现的功能。 |

仓库既有历史说明保留其时间语境，不在本次重新上传训练历史、过程成片或测试正文。最终功能判断以本文及当前实现为准。

## 7. 运行依赖与资源边界

| 部分 | 保存位置与交付方式 |
|---|---|
| 可公开的项目实现 | 本 MVP 仓库：Godot、Core、辅助界面、启动/看护、测试代码和配置模板。 |
| TTS 服务本体 | 独立私有仓库 `SummerTianYi/anime-agent-tts`；部署时按语音交接文档准备相邻 `tianyi-tts` 目录和独立环境。主仓保留客户端与看护，不擅自公开私仓内容。 |
| 官模、贴图、最终动作二进制 | 依 `apps/avatar-runtime/assets/README.md` 和资源清单在本地提供；受再分发授权约束，不因项目提交而自动公开。 |
| 声线权重、参考音频、识别模型 | 由有权使用者独立准备；不包含历史训练数据或个人录制素材。 |
| API 与外部账户 | 使用者的私有配置/OAuth 文件；`.env.example` 仅列字段，真实密钥与令牌不入 Git。 |
| 私人记录和开发过程 | 会话数据库、训练测试集、录屏、日志、原始视频和历次大文件归档均不随本次公开提交。 |

公开仓库不是一份“克隆后任意电脑无需准备即可完整脱机运行”的安装包。已验收主环境为 Windows；完整角色需要 Godot、本地资源和 Core 环境，真实语音另需 TTS/识别依赖，文本主脑、视觉和外部 MCP 仍依赖网络与有效授权。macOS、普通无 NVIDIA 显卡设备与全新系统的等效体验尚未完成验收。

配置先参考 `.env.example`：它保留兼容默认值，不代表开发机私有的 DS/StepFun 配置。复现当前外观需使用 `ANIME_AGENT_MODEL_LOOK=1.4`；复现对话/视觉需配置实际选定的文本 Provider 和 `ANIME_AGENT_VISION_*`，不能把开发者 Key 写进文档。可用 `ANIME_AGENT_CONFIG_PATH` 指向独立私有配置，Core 启动与凭据热重载使用同一来源；启动器、资源和语音依赖还需按对应说明准备。

准备完成后，以仓库根 `start-anime-agent.cmd` 正常启动。缺少语音或外部工具依赖时，降级到文字或工具不可用不算“完整等效体验”。本次提交交付的是**项目说明与可公开源码**，不是此前数 GB 的运行环境、模型权重或内部过程文件。
