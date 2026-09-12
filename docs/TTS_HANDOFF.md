# TTS 语音链交接清单（zcode → Codex，2026-09-12）

**交付状态（Codex，2026-09-13）**：所有者验证通过并批准实装与配套推送两仓。原CMD真预热、Godot会话内恢复及双看护已激活；两轮真实声线冷恢复60.187/58.765秒，Godot实际音频输出、274项离线回归两轮及复合故障/快速重开测试通过。禁止操作正式数据，不要求24h观察，不再重启当前健康窗口。实现、复现与边界见[TTS_REPAIR_STATUS.md](TTS_REPAIR_STATUS.md)顶部；下文保留zcode原始交接及归属，其40秒/24h旧指标不是当前承诺，旧启动器保留为原CMD兼容转发。

交接目标：**彻底修复 TTS 的运行期复活缺口**（OPS-08）。启动链已由 zcode 修复并验证，剩余缺口、全部相关文件路径、建议方案与验收口径如下。

## 现状快照

- 语音链**当前在线**：sidecar 8770（cuda）→ Core `speech.py` 合成 → avatar 播放，真机验证通过（合成 5.9s 音频 + 播放 + 状态机 speaking→idle 完整）。
- 已修复：**启动链回归**——09-11 启动重写丢了 TTS 钩子导致每次重启都哑巴；zcode 已把语音链折回 `start-mvp.ps1` 头部（杀旧 watcher → 启动 bat → 启动 watcher），任何入口启动都带语音。
- **未修复（本次交接主体）**：运行期 sidecar 死亡无人复活——她静默变哑直到下次重启整个栈。

## 文件清单

| 文件/目录 | 角色 |
|---|---|
| `work/tianyi-tts/scripts/tts_server.py` | sidecar 服务本体：8770 端口，GPT-SoVITS（cuda），`/health` 含 selfCheck（阈值 0.9，takes/retries 计数） |
| `work/tianyi-tts/scripts/tts_autostart.bat` | 幂等启动器：8770 已监听则 no-op；运行日志落 `work/tianyi-tts/out/tts_server_auto.log` |
| `work/tianyi-tts/venv/` | sidecar 独立运行环境（**不是** services/agent-core/.venv，勿混用） |
| `scripts/watch-tts-session.ps1` | VRAM 看护：等她窗口出现→保持；她关窗→停 sidecar 释放显存。**不负责拉起** |
| `scripts/start-tianyi.ps1` | 【孤儿】全链启动器（TTS bat + watcher + start-mvp 三件套），当前无任何入口引用它 |
| `scripts/start-mvp.ps1` | 正式入口（Codex 09-11 重写版）；头部已有 zcode 的语音链块（TTS 启动 + watcher 拉起） |
| `services/agent-core/agent_core/speech.py` | Core 侧客户端：`SpeechClient`/`SpeechManager`（8770 合成、分片流水线、selfCheck 阈值）——**E 期冻结区，改协议前先跑 TTS 管线单测** |
| `services/agent-core/tests/` | TTS 语音管线相关单测（sidecar HTTP 客户端、utterance 生命周期、打断/顶替、barge-in） |
| `%LOCALAPPDATA%\AnimeAgent\logs\tts-watch.log` | watcher 历史（**2026-09-09 起断档 = 链条断裂的首次证据**） |
| `work/tianyi-tts/out/tts_server_auto.log` | sidecar 运行日志（合成流水线、whisper 自检可见） |

## 已知问题清单

1. **运行期无复活（主体缺口）**：sidecar 崩溃/被误杀 → Core 的 `tts.available` 翻 false → 她静默变哑，直到下次重启整个栈。无任何守护覆盖 8770。
2. **运维连坐风险**：`taskkill /IM python.exe` 会同时杀掉 Core 和 sidecar（两者都是 python 镜像）。2026-09-12 晚 zcode 测试期间误伤两次。运维时必须按 PID/端口定向杀。
3. **孤儿启动器**：`start-tianyi.ps1` 是唯一带完整 TTS 链的启动器但无入口引用；需决策——废弃并入 start-mvp（zcode 已折入核心部分）或恢复为独立入口（需确认其 30s 健康轮询与新 start-mvp 90s 冷启动锁流程的兼容性）。
4. **首合成预热**：sidecar 冷启动后首次合成需加载模型（约 1 分钟慢）——可接受，但守护复活后的"恢复判活"要等预热完成再判。
5. **长稳数据缺失**：sidecar 连续运行纪录仅数小时级，长跑稳定性未知（正好由接手方的长测补齐）。

## 修复方向建议（二选一或组合）

- **方案 α（推荐）**：升级 `watch-tts-session.ps1` 为双向看护——保留现有"她关窗→停 sidecar 释放显存"，新增"8770 探测失败 → 重跑 tts_autostart.bat（幂等）+ 双确认判活"；与 core_watchdog 的轮询节奏对齐。
- **方案 β**：core_watchdog.ps1 循环加一路 8770 健康探测（与 Core 探测同套双确认逻辑），复活动作同 α。
- 两者都需处理：预热期判活（复活后给 90s 再判）、她关窗后的停止语义不变、不与 VRAM 释放逻辑打架。

## 验收口径（OPS-08）

1. 真机 kill 8770 监听进程 → ≤40s 恢复 `tts.available:true`，期间 Core 不重启、对话不中断；
2. 她正常对话与待机期间不误杀 sidecar；
3. 连续 24h 无"哑巴窗口"；
4. 她关窗后 sidecar 释放 VRAM（现有语义保留）；
5. 复活与释放全程落 `tts-watch.log` 可审计。

## 交接边界

- zcode 已交付：启动链修复（已合并推送）+ 本清单 + 验收口径。
- Codex 接手：运行期复活方案选型与实现、24h 长测、本清单问题 3 的入口决策（问所有者）。
- 冻结区提醒：`speech.py` 为 E 期冻结区；改动前必跑 TTS 管线单测；协议变更须同步 AVATAR_BRIDGE.md。
