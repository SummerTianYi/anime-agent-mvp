# 五仓分工与当前实装依赖

Codex，2026-10-04。按所有者要求核对五仓远端、对应本地工作树、正式启动链和运行资产引用。所有者确认：**保留分仓，补齐现用声线；官模/动作暂留本地。** 本轮不搬动运行目录、不重启天依、不删实验/历史数据，不改变仓库可见性。

## 1. 哪个是主仓

**本仓 `anime-agent-mvp` 是唯一产品主仓。** Godot、Core、正常启动入口、语音看护、当前产品文档与所有 agent 的有效长期规划都在这里。五仓不是五套都要同时运行的程序。

| 仓库 | 可见性 | 作用 | 当前天依是否直接依赖 | 本轮处理 |
|---|---|---|---|---|
| [anime-agent-mvp](https://github.com/SummerTianYi/anime-agent-mvp) | 公开 | Godot/UI、Agent Core、人设/工具/记忆/权限、STT、TTS客户端、双看护、启动与退出 | **是，产品主仓** | 统一记录分工、依赖与恢复入口 |
| [anime-agent-tts](https://github.com/SummerTianYi/anime-agent-tts) | 私有 | GPT-SoVITS sidecar、真实声线、参考音频、训练与验收脚本 | **是，独立进程配套仓** | 补齐当前 SoVITS e5，保留已有 GPT 与旧 e20；增加哈希清单和只读校验 |
| [anime-agent-workbench](https://github.com/SummerTianYi/anime-agent-workbench) | 公开 | 人设/记忆/权限/工具的沙箱考试与开发工作台 | **否**；已交付能力迁入 MVP，不从工作台动态导入 | 保留考试开发用途，不把历史 `vendor` 覆盖主仓新代码 |
| [anime-agent-roadmap](https://github.com/SummerTianYi/anime-agent-roadmap) | 私有 | 历史规划证据与回链 | **否**；有效规划已并入主仓手册 | 继续作为档案，不双头维护 |
| [anime-agent-cloth-physics](https://github.com/SummerTianYi/anime-agent-cloth-physics) | 私有 | 旧基线重现、服饰/接触/物理实验 | **否**；未验收的通用物理方案没有接入正式版 | 未提交实验保留原位，不混入已交付代码、不冒称防穿模完成 |

正常关系：`MVP启动器 → Core/Godot及TTS会话看护 → tianyi-tts sidecar → WAV → Godot播放器`。Workbench、Roadmap、Cloth Physics 不在此链路中。

## 2. 已实装功能的代码在哪

以下均为仓库相对路径；不是另造一套实现，也不改变原作者归属。

| 功能 | 主仓/配套仓文件 | 核对结果 |
|---|---|---|
| 角色窗口、透明画布、渲染/五官与表情 | MVP `apps/avatar-runtime/runtime.gd`、`main.tscn`、`emotion_presets.gd`、`lookdev/`、`model-versions/` | 源码与版本清单已跟踪；官模及纹理二进制按授权留本地 |
| 待机、倾听、思考、退出挥别 | MVP `apps/avatar-runtime/motion_registry.json`、`mocap/`、`farewell_exit.gd`、`farewell_speech_gate.gd` | 控制/构建/验证源码已跟踪；运行 GLB/TRES 动作资产仍为本地限定 |
| 聊天、会话、工具卡、记忆界面 | MVP `apps/avatar-runtime/interaction_ui.gd` 等及 Core 协议 | 已在主仓，不依赖其他开发 agent 运行 |
| 人设与考试通过能力 | MVP `services/agent-core/agent_core/harness.py`、`memory_retrieval.py`、`permissions.py`、`tools.py` | Workbench 已验收内容的落地点；以当前主仓为准，不再从工作台复制旧快照 |
| 主脑/视觉、持久化及MCP | MVP `services/agent-core/agent_core/`、`tools/gdrive/` 与 `tools/*-mcp.cmd` | 接入源码已在主仓；API Key、OAuth、真实聊天/记忆不在 Git |
| 唤醒/识别、四场景语音、实际播放 | MVP `voice.py`、`speech.py`、`main.py`（Core目录）、Godot播放器与退出门禁 | 2026-10-03 已配套发布；不是本次重做功能 |
| 启动/退出、Core/TTS恢复 | MVP `start-anime-agent.cmd`、`scripts/start-mvp.ps1`、`startup-common.ps1`、`tts-lifecycle.ps1`、`watch-tts-session.ps1` | 主入口默认定位兄弟目录 `tianyi-tts`，或显式 `TTS_WORKSPACE` |
| 真声线合成、自检/健康 | TTS `scripts/tts_server.py`、`voice_selfcheck.py`、`service_health.py`、`configs/tianyi_voice_v2.json` | **这一项本就不在 MVP**，应保留私仓配套，不搬声线进公开仓 |
| 全项目后续方向 | MVP [`docs/plans/README.md`](plans/README.md) | 唯一有效长期方案正文；专项仓提供实现/证据 |

## 3. 本次发现并补齐的实际缺口

声线配置指定 SoVITS **`tianyi_v2pro_e5_s140.pth`**，但原 TTS LFS 只保存 **e20_s560**。两者 SHA-256 不同，不能把“已有权重备份”当成“当前声音已备份”。现在按所有者授权在原私仓补齐 e5；GPT e15 与旧备份哈希一致，无需重复迁移。配置及其三条参考音频已在该私仓。

TTS 中新增 `configs/runtime_assets.lock.json`、`scripts/verify_runtime_assets.py` 和 [当前声线恢复清单](https://github.com/SummerTianYi/anime-agent-tts/blob/main/docs/ACCEPTED_RUNTIME_ASSETS.md)。含安装映射、权重/参考音频 SHA、上游 GPT-SoVITS 基线及 Windows 补丁。补丁与本地上游改动的稳定 patch-id 一致，已有补丁不重复搬运。

私仓已推送提交 [`3814b4c9d32bb17c3638cf851e5649d9c7d17fa7`](https://github.com/SummerTianYi/anime-agent-tts/commit/3814b4c9d32bb17c3638cf851e5649d9c7d17fa7)。从空的独立 LFS 缓存重新向 GitHub 下载现用 e5 与 GPT e15，两份真实对象的 SHA-256 均与安装权重一致；不是只核对本地缓存或 Git 指针。TTS 全部38项回归、备份/安装资产检查、主仓文档一致性检查通过。此次未重新启动服务或重跑真实云端/麦克风验收，官模 SHA 与冻结记录一致。

未发现 Workbench、Roadmap 或 Cloth Physics 中还有需要搬入 MVP 才能使**当前已交付功能**成立的运行源码。Cloth 的脏工作树是保留中的未实装实验，不能为追求“全在GitHub”无差别发布。Workbench 另有一个落后远端的旧本地副本；本次以已经同步的主工作副本及远端核对，不用旧副本覆盖正式代码，也不执行目录清理。

## 4. 恢复范围：哪些已在GitHub，哪些故意不在

- **功能源码**：MVP + TTS 配套保存；原 Claude/zcode/Codex 归属保留。开发工作台不作为运行依赖。
- **现用训练声线**：TTS 私仓 Git LFS、当前配置与参考音频。恢复时必须下载 LFS 实体并校验，不能只看到指针文件就判定成功。
- **官模/纹理/运行动作**：遵从本次明确选择，仍只留本地；定位、版本与哈希见 [模型版本索引](../model-versions/README.md)、[资产说明](ASSET_PIPELINE.md)、[动作管线](MOTION_PIPELINE.md) 及各动作 README。没有上传或迁移这些二进制。
- **第三方运行依赖**：Godot、Python/Node及包、GPT-SoVITS上游/底模、离线Whisper、KWS、字典/ffmpeg、外部MCP程序等需另行准备；GitHub源码不是这些依赖的完整离线安装包。
- **个人配置/数据**：`.env`、API Key、OAuth、个人历史与记忆、恢复档案、私人原始训练/验收材料仍不迁入公开仓；本轮不把任何其他私人文件新增到Git。

因此准确结论是“当前功能源码与已选择备份的现用声线分仓保存”，**不是“只克隆MVP即可完全复现本机”，也不是“所有模型和个人数据都上了GitHub”**。换机恢复仍需所有者本地受限资产和环境准备。

## 5. 审计基线与后续规则

本轮变更前，已核对的远端基线（不是未推送状态）：

| 仓库 | main 提交 |
|---|---|
| MVP | `dc1b386e1dc90b7596ffce28e8565987fa24c348` |
| TTS | `f289b4cdb20c102c8104a0df610c6e2bd5758b82` |
| Workbench | `acfc898cc7bd166d7d4fe7bcb590641ddb6bee1e` |
| Roadmap | `df80738f52b54facadbba9980ee7d0757c19ba1a` |
| Cloth Physics | `d9b5d45a37d1847ea4f03a0bdd96b638a271802e`（远端基线；本地另有未提交实验） |

后续新增功能先指定责任仓；提交带 agent 标记，并在本仓贡献记录中声明范围。涉及公共语音协议时两仓配套验证/发布；变更声线时新建不可变快照和哈希清单，不覆盖旧版本。长期目标只更新主仓手册。不能把迁移备份称为新增模型/物理功能，不能把一次代码盘点称为完整跨机/脱机验收。
