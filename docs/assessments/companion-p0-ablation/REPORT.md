# 陪伴 P0 根因审查与上下文对照实验

2026-11-09 · Windows 桌面洛天依 · 待独立验收

**借“小天才帽子”时，A、B 各有 2/2 次把话带回练习，C 为 0/2。恢复求助时，A 有 2/2 次满足交付要求，B、C 各为 1/2。** 24 次真实请求里，DS 生成的可见正文经产品解析后，24/24 与拟发送的陪伴气泡逐字相同。本轮有证据支持调整历史呈现能改善这一个玩笑，尚不能把 C 作为默认替换。[预注册口径](https://github.com/SummerTianYi/anime-agent-mvp/blob/f10069264f9a7eb27375a77dd2c7e009cce4b09a/docs/assessments/companion-p0-ablation/PROTOCOL.md) · [全部请求及返回](https://github.com/SummerTianYi/anime-agent-mvp/blob/4c2c1ca78131959b3154d54740ddba7a21b1cac6/docs/assessments/companion-p0-ablation/requests.jsonl) · [逐条评阅](https://github.com/SummerTianYi/anime-agent-mvp/blob/4c2c1ca78131959b3154d54740ddba7a21b1cac6/docs/assessments/companion-p0-ablation/ratings.json)

| 预注册指标 | A 固定候选 | B 加来源及接纳状态 | C 再按当前交流行为组织历史 |
|---|---:|---:|---:|
| 无端延续未接纳目标，玩笑＋转题，越低越好 | 2/4 | 2/4 | 0/4 |
| 接住当前意图，四场景合计 | 7/8 | 7/8 | 7/8 |
| 明确拒绝后停止教学与索要复述 | 2/2 | 2/2 | 2/2 |
| 主动恢复后给出可用的两句并兼顾限制 | 2/2 | 1/2 | 1/2 |
| 再问已问而未接纳的同一个问题 | 1/8 | 0/8 | 0/8 |
| 与同场其他回复复用核心句式的样本 | 2/8 | 5/8 | 2/8 |
| 至少一处未经提供的事实或个人经历 | 3/8 | 2/8 | 2/8 |

**得到支持。** 按预注册门槛，C 对 B 减少了两条错误延续，意图通过数和两个保护场景的通过数持平。收益全部来自帽子场景。用户没有承诺再弹一遍。B 已经正确标出“未确认”，DS 仍把练稳当成还帽子的条件。C 识别出打趣，把历史练习提议移入助手消息的背景字段，两次都能把夸奖还给用户。显式问句从 B 消失时，旧目标仍在，语义判分能看出这项差别。

**未得到支持。** B 对 A 的主要错误数没有下降。C 对 A 的玩笑改善没有满足整体验收门槛，因为恢复求助从 2/2 降到 1/2。三组都能在明确拒绝时停下，也都曾在用户重新求助时给出具体开头。样本里没有一组消除套话或补写事实。

**证据不足。** C 同时改变交流行为标记、历史相关性索引和提议的呈现位置。仅凭这三组不能分离三者的贡献，也无法确定某个提示词条款或 DS 训练特性是主因。自然转题在 A 已经是 0/2 错误延续，没有观察到可再降低的错误。四份历史各重复两次，不能估计日常发生率、听感或跨模型效果。实现停在实验分支。

## 从用户原话到气泡

候选的 `handle_chat` 先经现有守卫划分陪伴与操作，按会话和请求记录用户原话。`model_history` 在当前用户行之前截取近期消息，把迟到的助手答复配回原请求，过滤任务回执。Harness 保留 user/assistant 角色，把历史助手正文放进 JSON 的 `reply`，再拼 V1.2、203 字策略、有效事实、首轮标题条件和本轮歌曲资料。这个过程能告诉模型谁说过什么，却没有单独表示某个建议被用户接下。上轮的 28 条归档、8 对固定输入、两组连续六轮已完整重读并用原校验器重算。催第二遍练习和重复问拼图方向在原始返回中已经出现。[上一轮全量对照](https://github.com/SummerTianYi/anime-agent-mvp/blob/8025c6bacca57461653090e646ac100ce36e7a27/docs/assessments/companion-experience-p0/REPORT.md) · [原历史装配](https://github.com/SummerTianYi/anime-agent-mvp/blob/8025c6bacca57461653090e646ac100ce36e7a27/services/agent-core/agent_core/conversation_context.py#L14) · [原 Harness](https://github.com/SummerTianYi/anime-agent-mvp/blob/8025c6bacca57461653090e646ac100ce36e7a27/services/agent-core/agent_core/harness.py#L180)

本轮通过实际的 `handle_chat → _companion_turn → provider.complete → parse_reply → _present → hub.send_roles`。A 直接调用原 Harness。B 保留每条历史及顺序，把助手发问／建议所在消息、字符区间、接纳状态和证据所在用户消息编成短索引。C 在 B 上判断当前交流行为。对打趣、拒绝或分享，它能把尚未接纳的提议原文移入同角色历史的背景字段；遇到恢复、求助、明确承接或不确定时保留整条答复。每个样本都能用原位置拼回历史，所有用户消息逐字相同。系统层的索引仅含程序生成的标签、数字和位置，事实和引语保留其原角色。当前状态在本次装配后释放，仅测量记录保存副本。[投影实现](https://github.com/SummerTianYi/anime-agent-mvp/blob/f10069264f9a7eb27375a77dd2c7e009cce4b09a/docs/assessments/companion-p0-ablation/projection.py) · [陪伴与交付入口](https://github.com/SummerTianYi/anime-agent-mvp/blob/8025c6bacca57461653090e646ac100ce36e7a27/services/agent-core/agent_core/main.py#L1546)

| 场景 | 来自用户的事实、意图及限制 | 助手提议与接纳证据 | C 实际送模的呈现 |
|---|---|---|---|
| 借帽子，复用历史反例 | 间奏弹顺，自己愣了一下；随后夸助手并借帽子 | 助手先问起曲目和过程，后建议再弹并问第二遍。用户未表示接受或拒绝 | 判为“赞许或玩笑”。历史消息 2、4、6 的五个询问／提议片段进入背景，其中包含练习建议及后续追问。弹顺和愣住的原话在场 |
| 路口小狗，新措辞 | 配过海报颜色、喜欢大家一起涂字；当前分享红灯倒数与狗叫的巧合 | 换配色、再试一版由助手提出。用户谈涂字体验，随后转题，状态为未确认 | 判为“分享”。消息 2、4 的提议进入背景。B 两次、C 一次顺带提回海报／涂字，均未要求再试配色 |
| 拒绝复盘，复用正例 | 发言卡住、有些丢脸。先要缓缓，又明确要求别教、别让自己复述 | 助手曾提议聊卡住的地方或想办法；用户消息 3 已婉拒 | 判为“拒绝”。将已拒绝的询问移入背景，当前两个禁止条件完整保留 |
| 恢复开场白，新措辞 | 录了三种雨声、台上不能播放录音；现在要两句能念的话，别让观众闭眼 | 助手曾提议想开场，用户消息 3 当时拒绝。当前由用户重新发起求助 | 判为“恢复并求助”，保留旧拒绝和整段对话。早先的“不能播放”只在用户历史中出现，也完整送模 |

标签来自运行时所见原话和历史，评判锚点与场景编号没有作为投影函数参数。可区分两种错误。四份固定历史上，B/C 对目标建议的接纳状态符合锚点，C 对四种当前行为也相符；B 的两条催练和 C 的虚构雨声地点发生在相应状态已经判断正确之后。离线另有识别本身出错的用例。[固定原话](https://github.com/SummerTianYi/anime-agent-mvp/blob/f10069264f9a7eb27375a77dd2c7e009cce4b09a/docs/assessments/companion-p0-ablation/scenes.json) · [状态、依据、解析、气泡和每轮用时](https://github.com/SummerTianYi/anime-agent-mvp/blob/4c2c1ca78131959b3154d54740ddba7a21b1cac6/docs/assessments/companion-p0-ablation/dialogues.jsonl)

## 24 个目标回复

下面每格按第一次、第二次列出送出序号及阅读结果。全部 24 次均收到官方回复，HTTP 失败 0、重试 0、缺项 0。语义未通过的样本同样保留。源正文、标点、断行、响应 ID 和 usage 可按序号核对。[原始返回](https://github.com/SummerTianYi/anime-agent-mvp/blob/4c2c1ca78131959b3154d54740ddba7a21b1cac6/docs/assessments/companion-p0-ablation/requests.jsonl) · [带盲读号和理由的评分](https://github.com/SummerTianYi/anime-agent-mvp/blob/4c2c1ca78131959b3154d54740ddba7a21b1cac6/docs/assessments/companion-p0-ablation/ratings.json)

| 当前轮 | A | B | C |
|---|---|---|---|
| 借帽子 | #1 等弹完整首换大帽子，还自称在旁听着拍手。#24 直接重问第二遍 | #5 第二遍稳了就转还帽子。#20 下次弹顺整首才归还 | #9 明天还帽子，认可练顺间奏。#16 戴上帽子，把“小天才”还给弹完后愣住的用户 |
| 路口小狗 | #10 接管红绿灯，就当下问是在赶路还是凑热闹。#15 假想小狗每天上班 | #2 接住节奏，又提涂字。#23 接住发令，比起海报配色更难忘 | #6 路口“总指挥”，又提涂字。#19 绿灯是否“遵命”亮起，追问服务于当下的玩笑 |
| 别教也别追问 | #7 接到丢脸，答应不催。#18 陪用户缓一会儿，“就当我没听见”可能显得轻忽 | #11 不讲经过、不出主意。#14 接到丢脸，陪用户待一会儿，两条结构相近 | #3 明确停止教学与复盘。#22 允许缓一会儿，“不用按掉它”的指代生硬 |
| 重新求两句开头 | #4 两句口述，知道没有录音可放，把“三种”说成“三场”。#21 可跟着讲述听差别，“闭眼时雨只剩一种声音”没有依据 | #8 “一段一段听”没有落实不能播放时如何口述。#17 两句可念、请观众看台口，对大厅、话筒及“没有录音”的描述需校正 | #12 给出三句且虚构雨棚、树叶、操场三个录音地点。#13 给出可念的主选两句，保留睁眼和无播放条件，但补写了屋檐与瓦片 |

同一个输入“好好好，这顶小天才帽子先借你戴一天。”，A 的 #24 结尾是“不过说起来，帽子给我了，你那边第二遍到底弹了没呀？”，B 的 #5 是“不过说真的，你第二遍要是也稳稳过去，小天才的帽子就该转回你头上。”。C 的 #16 则说“不过真正的小天才应该是刚弹完间奏还愣在原地的你吧。”。三条回复分别展示了重复追问、没有问号的旧目标，以及使用用户事实来接梗。

评分先打乱顺序、隐藏组别与重复号，由本轮审查者逐条阅读并记录理由，再还原位置。没有引入外部裁判。能接住部分玩笑又在末尾给出练习条件，两个指标可分别记分。#23 比较了海报与小狗，但没有再建议换色，按预注册定义计为多余回带、旧目标延续为 0。重复套话按语义和对应的盲读样本配对，单个“嗯”或问号不计。对恢复组，前表的“可用”按两句、可念、场景和限制评分，未经提供的细节另计。B、C 各一条恢复通过，不代表这两条的每个事实都可靠。

## 对抗审查

20 份合成对抗历史在 DS 调用前固定。对照人工锚点，B/C 对每条历史的**全套接纳状态 18/20 完全一致**；C 的**当前行为 16/20 一致**；两者同时符合为 15/20。20/20 可无损还原全部用户和助手文字。明确同意紧邻的唯一提议、拒绝后重新求助、说“前者”承接助手的必要问题、同话题改为分享、显式引用／反讽，以及多项提议时避免笼统授权，都有通过样本。[对抗原话和人工锚点](https://github.com/SummerTianYi/anime-agent-mvp/blob/f10069264f9a7eb27375a77dd2c7e009cce4b09a/docs/assessments/companion-p0-ablation/adversarial.json) · [逐案自动判断与证据](https://github.com/SummerTianYi/anime-agent-mvp/blob/f10069264f9a7eb27375a77dd2c7e009cce4b09a/docs/assessments/companion-p0-ablation/adversarial-results.json)

| 未解决的对抗例 | 实际错在何处 |
|---|---|
| 两次未接建议后说“遇到帮我挑纸的人” | 两项均正确保留未确认，但叙述句因“帮我”误判求助 |
| “还是刚才那两张票。换作是你，会挑哪张？” | 保留了历史拒绝，却把含蓄的恢复求助判作分享 |
| “这件事明天再碰吧，今晚就陪我坐坐” | 未识别延期，状态仍为未确认，行为为不确定 |
| “可以呀，你这个玩笑我给满分” | 没把评价错当接受，但漏识别了夸奖 |
| 两个提议里只说“字体先放一放，颜色保留” | 识别到拒绝，未能把拒绝绑定到字体那一项 |

另对冻结代码做了零 DS 的事后措辞核查，未并入上述分母。把帽子换成胡萝卜勋章、保留连说“好”再说“归你”的形式，仍判玩笑；把同一夸奖改成“从今天起你就是接梗协会会长了”却判分享。字面借书“好好，书明天借你，我得记得带”也被判玩笑。把交通巧合改成“信号灯一灭，那条狗汪了一声，它当上值班员啦”会得到不确定。规则依赖表层措辞，固定场景的识别成绩不足以证明换一种说法也能工作。所有真实组均保持冻结代码。

## 控制、用量与验证

| 版本或静态分段 | 完整指纹 |
|---|---|
| 本地独立 worktree 起点／远端原候选 `codex/companion-platform-chat-ui-20261108` | `8025c6bacca57461653090e646ac100ce36e7a27` |
| 已确认 V1.2 主线对照 | `cf62b484ca8f075d97c2d4c41496480c7c82501c` |
| 预注册、代码冻结及全部真实生成 SHA | `f10069264f9a7eb27375a77dd2c7e009cce4b09a` |
| 最终实验数据与盲读评分 SHA | `4c2c1ca78131959b3154d54740ddba7a21b1cac6` |
| 交付分支 `codex/companion-p0-ablation-20261109`，最终报告所在提交（Git 归档展开） | `$Format:%H$` |
| ROLE_PROMPT，UTF-8 SHA-256 | `7f57bf41e8f2764fe9bfbf6797c5323d253d7d1f1a73440873c65d067582207e` |
| RUNTIME_CONTRACT，UTF-8 SHA-256 | `e43c97d067285fe88688c63c53f97789e6aa306f1d11b8983d2f10a271dc7910` |
| 有效静态前缀 ACTIVE_PROMPT_OVERRIDE | `714ae650ce060f0a645f2fa1055878790438a5e93566ceda18a3ecbdc9d9c9f6` |
| 既有 203 字陪伴策略 | `9b43195d4297fe4e402c7b276b9b1f20bc8f8e3cfc4becbc2e0fe0369f78c28d` |

Git 源码页的固定链接在 `blob/` 后给出最终报告提交；从同一提交执行 `git archive` 会在上表展开完整 SHA。预注册提交在第一笔真实调用前已推到远端。两条旧例的 A 请求与上轮候选正文完全相等，另外两条为新合成历史。三组均按宿主的首轮条件处理标题，本轮均有历史，条件均为假。离线额外覆盖了首轮标题为真、有多行事实和保留合理问句。24 份请求逐一通过预固定正文哈希；除上下文内容，字段全部相同，只有 `model=deepseek-flash`、`stream=false`、`thinking.type=disabled` 和 `messages`。采样沿用接入默认值，请求未显式指定温度。未读取或导入参考项目素材。[交错顺序](https://github.com/SummerTianYi/anime-agent-mvp/blob/f10069264f9a7eb27375a77dd2c7e009cce4b09a/docs/assessments/companion-p0-ablation/order.json) · [冻结的请求指纹](https://github.com/SummerTianYi/anime-agent-mvp/blob/f10069264f9a7eb27375a77dd2c7e009cce4b09a/docs/assessments/companion-p0-ablation/request-pins.json)

| 8 次请求合计或中位数 | A | B | C |
|---|---:|---:|---:|
| 输入／输出 tokens | 15,804／596 | 16,216／660 | 16,460／683 |
| 输入缓存命中 tokens | 14,070 | 13,952 | 14,080 |
| HTTP 总耗时（秒） | 17.860 | 16.233 | 17.735 |
| HTTP 中位（秒） | 2.164 | 2.008 | 2.204 |
| 整轮中位（秒） | 2.180 | 2.008 | 2.219 |
| 额外本地状态判断与投影中位（微秒） | 0 | 62.85 | 175.75 |

合计输入 48,480、输出 1,939 tokens；HTTP 累计 51.828 秒。每组 8 次，每个目标只生成一次，额外分类、裁判和辅助请求均为 0。B、C 相比 A 平均每次多用 51.5、82 个输入 tokens。网络、缓存和输出长度随样本变化，三组耗时不足以证明提速或减速。[可重算汇总](https://github.com/SummerTianYi/anime-agent-mvp/blob/4c2c1ca78131959b3154d54740ddba7a21b1cac6/docs/assessments/companion-p0-ablation/verification.json)

- **隔离与关闭。** 单独 Windows Python 3.12 进程，只在内存选读既有官方 DS 配置的白名单项。新建测试配置、用户目录、日志和数据库，每条从自己的空库预填。线上调用前持久化编号，并检查目标、方法、请求体和二次 POST。测试禁止派发业务工具，没有启动 Core 服务、监听端口或连接 WebSocket；客户端计数为零。TTS、麦克风、唤醒和业务工具关闭，idle、启动问候和告别缓存未运行。测试进程正常退出并关闭数据库。全量单测需要的 HTTP 夹具使用进程自己监听的临时回环端口。生产桌面、Core 与 TTS 均未连接或重启。[运行终态](https://github.com/SummerTianYi/anime-agent-mvp/blob/4c2c1ca78131959b3154d54740ddba7a21b1cac6/docs/assessments/companion-p0-ablation/run.jsonl) · [发送前计数与事件采集](https://github.com/SummerTianYi/anime-agent-mvp/blob/f10069264f9a7eb27375a77dd2c7e009cce4b09a/docs/assessments/companion-p0-ablation/evaluate.py)
- **回归。** 起点相关 44/44，冻结实验后相关 44/44。全量首轮 560/561，唯一失败是新建测试用户目录缺少 Desktop 子目录；补齐空夹具后原断言通过，全量 561/561，零跳过，40.187 秒。24 个位置的离线入口预演、错误／重复／第 25 个位置的发送守卫、旧证据复算和仓库文档检查通过，文档守卫返回 `DOCS_CONSISTENCY_OK`。离线预演的固定回复只验证接线。语义结果只使用后续 24 个真实 DS 样本。[隔离回归入口](https://github.com/SummerTianYi/anime-agent-mvp/blob/f10069264f9a7eb27375a77dd2c7e009cce4b09a/docs/assessments/companion-p0-ablation/isolated_checks.py) · [离线预演](https://github.com/SummerTianYi/anime-agent-mvp/blob/f10069264f9a7eb27375a77dd2c7e009cce4b09a/docs/assessments/companion-p0-ablation/preflight.py)
- **范围与阻塞。** 变更集中在独立评估目录，以及 README、接手总纲和贡献声明中的索引。产品 Core、Harness 人设、Agent 授权、Godot 和部署配置均沿用起点。取消同义表达失效、混合请求丢失禁止条件、解释性问答误入任务、新建会话接纳旧回执、旧语音恢复通知缺少会话归属这五项仍开放。文本证据只核对拟发送事件，Godot 控件、真人听感、正式桌面激活和独立验收均未执行。[五项既有阻塞证据](https://github.com/SummerTianYi/anime-agent-mvp/blob/8025c6bacca57461653090e646ac100ce36e7a27/docs/assessments/companion-experience-p0/agent-edges.json)

24 个返回的结束原因均为 `stop`，其中长期记忆候选为 0。报告内 20 个固定提交引用和三个仓库入口已核对。仓库接手总纲 §7 的两份零上下文答卷留待独立验收；本轮只调用获准的 DS 文本接口，未将本次盲读或文档守卫记作独立签收。

## 独立核对与回退

在实验分支的仓库根目录使用带 Core 依赖的 Python 3.12。以下命令全部离线，汇总会核对预注册顺序、真实请求体与响应、状态、来源历史、气泡、语义评分对应位置，以及已保存指标。对抗用例的人工锚点只在核验程序读取。

```text
python docs/assessments/companion-p0-ablation/verify.py run
python docs/assessments/companion-p0-ablation/summarize.py
python docs/assessments/companion-p0-ablation/verify.py adversarial
python docs/assessments/companion-p0-ablation/isolated_checks.py full <新的仓库外目录>
python docs/assessments/companion-p0-ablation/isolated_checks.py docs <另一个新的仓库外目录>
```

本轮 24 次配额已用完，独立评阅可直接使用保存的全部原文。实验装配只在测量进程挂接；正常入口始终使用 A。需要一份起点代码时，另建检出指向 `8025c6bacca57461653090e646ac100ce36e7a27` 即可，没有数据库迁移或正式进程恢复步骤。若需撤销整批 Git 变更，可在**另建的本地分支**从报告所在提交执行 `git revert --no-commit 8025c6bacca57461653090e646ac100ce36e7a27..HEAD`，核对 diff 后再决定是否保存。原候选、主线和本实验的远端历史均可保留。
