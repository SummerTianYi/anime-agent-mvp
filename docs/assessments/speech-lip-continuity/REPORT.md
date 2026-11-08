# 口型与语音同步、长回复连续播放

2026-11-08，Codex。**可见天依已在静音和供音空档闭口，有声时随音量开合。** 三段固定回复中，同一段音频故意迟到时，双段预取使两次额外等待从 1.540 / 1.583 秒降为 0。该收益来自实际角色和播放器配合可重复的准备时序。真实 GPU 重做负载下的收益尚待验证，因此候选默认仍预取一段。等待 ChatGPT 独立验收。

## 现场基线

正式 Godot PID 39956 在 MVP 安装目录的 `apps/avatar-runtime`，Core PID 1960 在同一安装的 `services/agent-core`。该检出 HEAD 为 `d3ed6d68f2509ad51bea15cf8224c5f3a165d957`，含本地未提交修改。TTS PID 28804 在独立的 tianyi-tts 安装的 `GPT-SoVITS` 下运行，所在仓库 HEAD 为 `3814b4c9d32bb17c3638cf851e5649d9c7d17fa7`。正式目录和两个候选目录分离。核验通过 PID、工作目录、loopback 健康及源码指纹进行，既有进程加载的每个字节未知。结束前这三个 PID 仍在，TTS 为 ready，selfCheck 启用、阈值 0.9。

两仓候选父提交分别为 `c282d8a387d3004fe6422228ab71978ea7e137ea`、`dcc3787d6b86190895ef570040a5d846b4324159`。正式磁盘的 7 份受影响源码已有独立本地逐字节快照。Godot 修前实验直接使用快照中的 runtime.gd、speech_output.gd；Core 修前回放直接导入快照中的 speech.py。本候选从实际磁盘带入原有的语音专用增益总线和启动器对已有本地增益配置的读取，实测为 +5 dB。Core 仅改两个版本中相同的语音管理器装配及语音回执记录位置，保留证据分支原有的 8 行 HTTP 非重试错误处理。正式 main.py 的其他差异没有复制。TTS 两个文件按 LF 与证据版本一致。[7 份快照哈希](baseline.json) · [上轮 MVP 报告](../tts-stream-latency/REPORT.md) · [配套 sidecar 固定报告](https://github.com/SummerTianYi/anime-agent-tts/blob/f3027fd14f889c3413d9e19e1c9fd4729a5b1765/docs/assessments/speech-lip-continuity/REPORT.md)

## 口型

原运行时代码在全局 speaking 期间每秒切换 8 次元音，即使下一段尚未生成。候选从 AudioStreamPlayer 的播放位置，加上距上次音频混合的时间，再扣除输出延迟，在对应 PCM 位置计算 20 ms 窗内的均方根音量。无声区回到闭口，声音驱动一个开口形状，叠加在现有表情混合之后。每帧采样数量有上限，支持当前 16-bit WAV 及 8-bit、单双声道 PCM；其他 Godot WAV 编码退到语音专用总线峰值，该分支未用本轮声线测过。完成、取消、加载失败均清掉语音对嘴形的贡献。正常眨眼、笑容和手工表情保留。

| 实际脸部 blend shape / 场景 | 修前 | 修后 |
|---|---:|---:|
| 首段等待、两段空档、取消后、失败后，各阶段最大说话嘴形 | 四处均 0.564 | 四处均 0 |
| 播放中的 WAV 内部静音，源位置 1.85–2.17 秒 | 最大 0.564，9 帧 | 最大 0，10 帧 |
| 检测到有声时，最大 / 中位开度 | 0.564 / 0.433 | 0.720 / 0.683 |
| 眨眼峰值 / 笑容 | 0.950 / 0.18 | 0.950 / 0.18 |

实验加载实际角色（703 根骨、48 个表情），Godot 4.7.2 可见窗口、WASAPI、30 FPS 上限。运行原有每帧动画、表情混合与 WAV 播放代码，隔离桌面桥、窗口配置及私有 UI。等待阶段故意保持全局 speaking。文件内部插入的 480 ms 静音只用于口型反例。fix 录屏还包括取消后启动新播放，注入同一旧 utterance 的全新 playbackId，新播放继续，随后按指定 ID 停止。成功、取消和缺文件分别得到完成、interrupted 和 failed；失败的 startedAtMs 为 0。逐帧核对包含真实语音总线采样及网格开度。人耳与音箱处的绝对同步误差、不同输出设备和用户主观观感待验。

录屏仅含隔离角色窗口与该语音总线。私有目录 `final-video/before/role.mp4` 和 `final-video/after/role.mp4` 的 SHA-256 分别为 `55448da41a1ba3076c1fc627de7ebd341248486373afe07c9ce7b71bb1e32078`、`3bfeca5adaeb87858c66bea900ea2f682018f5521d4135d1750a003108ec40e1`。对应的 trace.json 留在各自目录。远端只存合成实验的数值记录。[逐帧数值](mesh.tsv) · [区间结果与回执](visible.json)

## 长回复的等待

以前在当前段播放期间预取下一段；即便文件已经就绪，也要等播放结束才开始准备更后一段。现在播放和有界后台准备分别推进。队列持有至多一或两个未来段的路径与元数据，Godot 每次加载当前 WAV，Core 不缓冲 PCM。每个管理器只有一个实际 HTTP 合成工作槽；即便 asyncio 等待者已取消，旧 HTTP 线程结束后才释放槽。新回复在锁内接管，旧队列取消，已进入 sidecar 的旧合成可能做完并产生由原 spool 策略清理的文件。既有回执补送仍用原播放 ID，明确未播放才重新生成；Godot 另保留最近 64 个结束或撤销的语句 ID，忽略其迟到的新片段。

固定短答“我在，请讲。”。三段回复为“你好呀，我是天依。现在的声音听得清楚吗？”、“今天也辛苦啦。我们可以慢慢聊，一起把想做的事情安排好。”、“我在，请讲。”。五个片段来自同一批归档 v2Pro 声音，在原有句间静音处分界，拼回逐字节等于每个源文件。原语速、句末空白、文字和顺序都保留。准备时间人为固定为 650、700、550、3000、900 ms；短答固定 900 ms。测试从实际 SpeechManager.speak 起，穿过真实 Godot 加载、播放与回执，首声取实际输出总线阈值 0.003；两端的采样精度受约 33 ms 帧间隔影响。该实验没有 DS 耗时。

| 两次重复，毫秒 | 实际基线，预取 1 | 候选实验，预取 2 |
|---|---:|---:|
| 短答，开始准备至首声 | 1000 / 1031 | 1037 / 1000 |
| 三段回复，开始准备至首声 | 832 / 831 | 832 / 833 |
| 每篇额外空档次数（等文件 >80 ms） | 1 / 1 | 0 / 0 |
| 每篇最长额外空档 | 1540 / 1583 | 0 / 0 |
| 同一故意迟到边界，前段末声到后段首声 | 1966 / 1966 | 400 / 433 |
| 已就绪未来文件峰值 / 合成工作线程峰值 | 1 / 1 | 2 / 1 |
| 该批隔离 Godot 进程峰值工作集 / 系统最低可用内存（MiB） | 363 / 1638 | 425 / 1956 |

额外空档取 `max(0, 下一文件就绪 − 上段完成回执到达)`。它与音频自身停顿、设备和桥接开销分别记录。长答首声配对差 0 / +2 ms，短答 +37 / −31 ms；没有故意增加开口前等待。真实播放保留约 0.4 秒的自然段间停顿。内存是整次运行实测峰值，不能把差值全部归因于缓存。[修前逐段时序](queue-before.json) · [修后逐段时序](queue-after.json)

## 合成、自检与播放的归属

Core 为每次准备分配 preparationId，记录 requestId、utteranceId、partIndex、请求和就绪时刻。sidecar 可在对应 HTTP 回包附各 take 的合成开始/结束、自检开始/结束、最终选中编号与时刻。dispatch 将准备与 playbackId 相连。Avatar 回执附播放器启动与终止时间，仅匹配的 avatar 回执进入原事件记录。旧 sidecar 或 Avatar 缺少新增字段时照常播放。播放器启动时刻与首个有声采样见上表时序的不同列。

随机 loopback 端口上的实际 SpeechClient、HTTP Handler、择优循环和 SpeechManager 完成了一次关联测试。人工分数使首段重做后选 take 2，注入明确加载失败后新准备选 take 1。两次准备、两次播放 ID 以及各自的时间可独立回读。该测试使用替身合成器、分数及播放器回执。可见长答回放各段使用已成品音频，当次重做数为 0。上轮真实语音的 26 段有 11 次重做；本轮未取得新 GPU 重做率或真实 Whisper 耗时。[跨仓 HTTP 原始记录](take-link.json)

## 回归、复现与回退

- Core 隔离语音组 63 项通过，告别组 9 项通过。新用例验证排队上限、首次派发、ID 关联、抢占时丢弃旧段与旧 HTTP 在途期间保持单工。原有用例覆盖超时、明确加载失败后重做、重复 ID、过期回执和断连恢复。Godot 原播放/告别回归 17 个断言通过，故意损坏的 WAV 如期产生 Godot 加载错误。sidecar 39 项通过。文档检查发现 678 个 Core 用例并通过一致性与隔离检查。只运行受影响回归，V1.2 全量历史结果保留。
- 两套 Python 环境分别使用原 Core 依赖与 sidecar 依赖。在候选 Core 的 `services/agent-core` 设 `ANIME_AGENT_DATA_DIR` 为新临时目录，执行 `python -B -m unittest discover -s tests -p "test_speech*.py"`，再对 `test_farewell_delivery.py` 执行一次。在 TTS 根目录执行 `python -B -m unittest discover -s tests`。用 sidecar Python 运行 `verify_take_link.py <MVP候选> <TTS候选> <输出JSON>`。该脚本仅启动临时 HTTP 服务。
- 可见复现需已授权的本地角色、导入缓存、Godot、归档音频与充足内存。把 avatar-runtime 和必要资源复制至独立项目，项目名改为 `Tianyi private lipsync lab`，不得以正式目录作测试项目。两次分别复制正式基线和候选 runtime.gd，保留实际 speech_output.gd；以 ack.wav 的 PCM 构造“原文件 + 480 ms 零样本 + 原文件”的 32 kHz 单声道 WAV。执行 `visible_run.py --godot EXE --project PROJECT --wav WAV --output VIDEO/before` 和对应的 after 目录，再执行 `review_role.py VIDEO FFMPEG visible.json`。输出目录应由操作者创建，before 与 after 应为空。脚本从窗口渲染目标和语音总线采样，未读取其他窗口或麦克风。
- 长答用 `replay_queue.py --godot EXE --project PROJECT --speech SPEECH_PY --audio ARCHIVE --private SCRATCH --output RESULT --window N`。对应基线 N=0、候选双段 N=2，ARCHIVE 放原 ack.wav、short.wav、long.wav。脚本验证分界不损失 PCM，仅访问随机本机端口。先前探针首次启动因隔离子类方法签名不一致未取得结果；已修正并双方重跑。早期监控误取 Godot 控制台包装进程的工作集，表中及最终录屏改用实际引擎进程。
- 默认和回退使用 `ANIME_AGENT_SPEECH_LOOKAHEAD=1`。值 2 仅供已授权隔离窗口实验，其他值回到 1。源码回退应在隔离检出反向应用调度、口型和计时差异，按 baseline.json 恢复原 runtime.gd；保留既有语音输出模块和启动配置。不要用证据分支整个目录替换正式安装。sidecar 可独立回退两份 Python 源码，详见配套报告。

资源预检为一块 8151 MiB GPU，可用约 5116 MiB；开工时系统可用物理内存约 1.4–1.8 GB。正式 TTS 的既有峰值工作集约 3.1 GB、私有提交约 8.8 GB。没有启动第二份 GPU 模型。所需补验窗口为具有独立 RAM、显存余量且可加载同权重、同参考、同 0.9 自检和真实角色的本机窗口。在同一组固定文本复测首声、准备迟到、重做、取消时丢弃的计算量、峰值资源及实际听感，再决定是否将双段预取设为默认。现场未部署，未重启正式桌面，未对正式实例发起测试合成。
