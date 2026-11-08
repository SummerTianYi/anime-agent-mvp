# 桌面四项同步到主仓

2026-11-08，Codex。以原 `main` 的 `d3ed6d68f2509ad51bea15cf8224c5f3a165d957` 为基线，在独立工作树提取以下四项，再使用同一份代码做组合验证。

| 同步项 | 对应的桌面行为 | 本次核对 |
|---|---|---|
| 桌面 Harness V1 | 按会话显示和确认版本化操作票据，执行前复核权限。支持任务内结果续读、可见记忆检索、手动录音失效保护及三档投入度 | 取激活提交的运行文件和回归，再对照桌面源码。保留拒绝、改参、跨会话、重复确认和迟到录音反例。[V1 激活记录](https://github.com/SummerTianYi/anime-agent-mvp/blob/acc7bd4227c8e99a4adb7ed7266a8e1d06105ebd/docs/assessments/harness-v1/evidence/activation-delivery.json) |
| 官方 DeepSeek Flash | `api.deepseek.com` 配合 `deepseek-flash` 时，普通聊天和工具请求均发送 `thinking.type=disabled` | 从 HTTP 请求体断言域名、模型和开关，旧网关与其他模型保留原参数。公开示例列明官方模型名，凭据留空 |
| 常驻唤醒恢复 | 选择常驻模式后，先说“我在，请讲”，采集就绪才提示倾听。仅有唤醒词时不新建聊天 | 合成麦克风覆盖取消、设备失败、恢复、切会话和断线。组合测试从唤醒音频进入真实聊天入口 |
| 角色语音增益与限幅 | Godot 通过 `TianyiSpeech` 给天依的声音单独增益，正增益启用 −1 dB 峰值限幅 | 混音测量覆盖 0、+3、+6 dB，组合测试读取 +5 dB 配置。公开默认值 +3 dB，本机所选 +5 dB 保存在私人配置 |

## 来源核对

Harness V1 的激活源码基点为 `c212cba3622f6f2a7f008c6a8ad01e4f585a097b`。下列桌面磁盘源码按 LF 计算 SHA-256。除表后注明的旧配置兼容行，集成文件内容均与相应来源逐一核对。正式运行目录保持原状。代码指纹核对的是源码版本，进程内存及实际机器本次均未重新部署。

| 文件 | SHA-256 |
|---|---|
| `agent_core/main.py` | `24866f37c461520001af14d82ee9f745ab42d5ac6397804dd0d25f754f4c5e85` |
| `agent_core/actions.py` | `1a288be2c657e6f28caee38eb683b8ed06d37fe6593c7d28ab8c9920db4cf068` |
| `agent_core/harness.py` | `f4b0a888d14bc2b20b994971be601cc72255c6a8976a0e271e2881770a170e25` |
| `agent_core/wake_word.py` | `d0d9ea6a44c46d72c4db6e59e6a4bacf5aeea267d548bba91dbbf3e033fcef23` |
| `runtime.gd` | `bd0bc23d458b580217a4f466d416c87e332e945d1acb9f0bf0860585e262a56f` |
| `speech_output.gd` | `2fdf1a4a283ef71ce45b75a3bb245d2f23f93c3d9f93b4a4030c95ac551e67da` |

两位独立接手人发现旧主线允许用 `ANIME_AGENT_IDLE_THRESHOLD=0` 关闭闲置监测，而桌面 V1 启动时忽略它。集成保留这个配置约定：非正数阻止后台启动，启用后依旧按 V1 固定的 600 秒和每段一次计时。该兼容判断是产品代码与桌面快照的唯一差异，集成版 `main.py` 的 SHA-256 为 `ef8e9374d28c1f8588661119a71d4cac5c882631f26e8eb8b1064d8f0c612c45`。同时校正协议与测试说明中的旧档位数值。

对比原主仓，`speech.py` 与 `storage.py` 的 Git 内容均相同。排队优先级、音频驱动口型、明确记忆更正、Provider 异常响应解析、文件／Issue／邮件专项流程、通用 A4 和 V1.2 人设均继续留在各自候选。已有 V1 中的票据、可见记忆检索和原版聊天能力随 V1 同步。

## 组合验证

| 检查 | 结果 |
|---|---|
| 原主仓完整 Core 回归 | 273/273，14.015 秒，跳过 0 |
| 提取四项后的完整 Core 回归 | 389/389，67.281 秒，跳过 0。另建仅安装 `services/agent-core[test]` 的环境再次通过 389/389，66.843 秒，跳过 0 |
| 旧配置兼容回归 | 修前，设置 0、0.0 或 −1 时后台仍会启动。修后这三种输入均不启动线程，600、1200、无效值三组均按 600 秒记录启用；定向 8/8。 |
| 最终组合回归 | 在仅安装测试依赖的独立环境通过 390/390，跳过 0，66.703 秒。用同一最终代码重跑唤醒至两条播放回执的完整链路和文档一致性检查，均通过。 |
| 唤醒 → DS 请求 → V1 回复 → Godot 播放 | 已完成首轮历史加载的独立 Godot 和临时 Core 通过真实 WebSocket 通信。合成输入“嗨天依”“今天一起听歌吧”，在 HTTP 边界观察到 1 个带系统上下文、工具表和官方参数的请求。Godot 返回唤醒应答与“好呀。”各 1 个完成回执，同一请求、不同语音 ID。临时历史仅含对应的一问一答，语音总线读回 +5 dB、限幅开启 |
| Godot 4.7.2 | 输入焦点／快捷键守卫、思考档位守卫通过。公共播放 19/19，告别 46/46，语音增益 54/54。强信号在 +3、+6 dB 时输出峰值均为 −1.00 dBFS。使用独立进程和 Dummy 音频输出 |
| 其他门禁 | 启动生命周期 18/18、TTS 生命周期 13/13。TypeScript 类型检查与 Vite 构建通过。文档一致性通过。既有本地模型、Idle、Pirouette 的大小与 SHA-256 全部符合清单 |

首次组合探针使用 headless 主场景，触发已有的预览后退出。随后在历史初始化结束前注入一次唤醒，未取得两条回执。验收探针改为等待真实 Avatar 的首轮历史响应，因为 `chat.history.request` 会使旧录音失效。以上回执取自完成初始化的独立 Godot 实例。本次合成了模型响应、录音和测试音频；真实模型请求为 0，未重新测试物理麦克风、扬声器听感或外部业务。

首轮 GitHub Windows CI 的 Core 有一项失败。短退避用例将两次单调时钟读数相减得到 47 ms，断言下限为 50 ms。该用例现直接验证 Provider 向等待接口传入精确的 0.05 秒，并用事件暂停等待：释放前 HTTP 仅发送一次，释放后才发送第二次并交付成功。生产传输逻辑及 CI 工作流沿用原实现。[首轮 CI 记录](https://github.com/SummerTianYi/anime-agent-mvp/actions/runs/42477858407)

更新断言后，Provider 传输回归 27/27 通过，故意将请求间隔替换为 0 秒的负对照被检出。最终完整 Core 回归 390/390，跳过 0，67.078 秒。

## 复现与回退

1. 在独立检出安装 `python -m pip install -e "services/agent-core[test]"`。依照 [TESTING.md](../../TESTING.md) 指定临时 `ANIME_AGENT_DATA_DIR`、指向不存在文件的 `ANIME_AGENT_CONFIG_PATH`、Mock 和关闭的 TTS、唤醒、MCP。在 `services/agent-core` 执行 `python -m unittest discover -s tests -v`。测试额外依赖包含合成麦克风阵列用的 NumPy。
2. 复制已导入本地角色资产的隔离 Godot 工程，把本次提交的 Avatar 源码放入 `<fixture>/apps/avatar-runtime`。在 fixture 根放空标记 `.farewell-test-fixture`，在副本 `project.godot` 的 `[application]` 内设置 `config/use_custom_user_dir=true` 和专用的 `config/custom_user_dir_name="TianyiCodexFourTest"`。运行 `python scripts/tests/verify_desktop_four.py --godot <Godot可执行路径> --fixture <fixture>`，通过时打印 `DESKTOP_FOUR_OK requests=1 external=0 speech_completed=2 voice_gain_db=5 limiter=on`。
3. 根目录运行 `python scripts/check_docs_consistency.py`、`pnpm install --frozen-lockfile`、`pnpm build:desktop`。在隔离 Avatar 工程运行 `verify_text_input.gd`、`verify_effort_ui.gd`、`verify_speech_delivery.gd`、`verify_farewell_speech.gd`。增益守卫 `verify_speech_gain.gd` 读取 `SPEECH_GAIN_TEST_DIR` 下的 `.voice-gain-fixture` 和四个合成 WAV（`ack`、`short`、`long`、`peak-probe`）。
4. 若需撤销主仓本次运行代码，在干净分支对整批区间执行 `git revert --no-commit d3ed6d68f2509ad51bea15cf8224c5f3a165d957..<本轮主线最终SHA>`，复核后提交并重跑组合验证。运行配置可独立切换 Provider、设置手动录音、或设置 `ANIME_AGENT_SPEECH_GAIN_DB=0` 旁路增益与限幅。此次同步不涉及生产数据库和桌面进程切换。
