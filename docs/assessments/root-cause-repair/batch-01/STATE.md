# Batch 01 当前停点 — 2026-10-12 20:27

首批已实装，部分桌面验收通过；A4自由正文假待办仍未闭环，不能宣布全部修复。集中事实、证据、回退与剩余范围见[REPORT](REPORT.md)。不合并main；按VERIFICATION_SPEC只做本地提交，待验收再push。

## 版本与运行

- 主仓：`C:/Users/26052/Documents/Codex/2026-10-12/tianyi-repair-batch-01`，分支`codex/root-cause-repair-batch01-20261012`，基线`b2d871316b35287f17b0771dcd02212b4be2bb72`。初次代码提交44ae32e0b02da100ac62c6ef0a642df3c8755880，最终增量完整SHA见本文件所在提交/交付答复。
- TTS：同级`tianyi-tts-repair-batch-01`，最终`ea5c4abf04518c684a3da5c56994ff8f6f927d49`；代码与`fb681d0a93bd6bd3d8b2785924dbaf264810dc5e`相同。
- 唯一Godot进程21368、窗口2232366，20:06经候选根`start-anime-agent.cmd`正式重开，最新main/actions修正已加载。Deepseek-v4-flash恢复，Core角色avatar=1，TTS可用、protocol2、告别缓存3；最后回答已完整播放，待办0。保留当前窗口。
- 候选.env已按对照前备份逐字节恢复，hash f1c9a485676126d2a1a851069b768b9ff233cc34ff32bc8dc0e9dbaa23769e26。未改模型、动作、声线。所有者最新音量10保留。

## 已完成验证

Core395项、定向33项及TTS43项通过；独立交付7/7、确认20分类+3状态通过。最终源码hash见evidence/desktop-followup-regressions.json。独立材料审查的听感归属/旧摘要链接两处问题已修正。复用已通过结果，不重复全套。

DS/GLM均在Godot完成真实文件确认、后续完整原文读回、保留待办先聊天、Gmail空查询与Invalid id业务失败。DS专用Issue #1标题更新经真实issue_write票据成功，远端只读核验一致；GLM仅写出假待办文字，下一次确认因无票据被拦，保留失败。GLM文件成功后补答45.016秒超时、DS Issue读取后补答45.031秒超时，都交付既有真实结果。旧pending覆盖聊天/读回丢失/否定误取消已复现后修复。

首次声音问候真人未听到或不清楚；B01-VOICE-03声音测试真人明确听清。GLM含✅短聊只有真实合成及完整播放回执，未代签真人听感。前台10次新消息/会话打断，快照内无这些utterance后续回执；强制晚到音频仅有隔离证据，误点“取消录音”不计播放取消验收。

19:21、20:06正式重启后查历史并打开旧会话；20:26又从“回忆”打开最新“GitHub Issue标题更新”。全部62条消息、814事件、11动作保存在持久测试库；失败也保留。

## 数据、对象和授权

当前数据`D:/TianyiRepair/batch-01-20261012/data/anime-agent.sqlite3`，health关联、普通/UNC文件ID一致、显式读事务backup及quick_check=ok。最终私有快照identity-final，脱敏公开desktop-final/deployment-final。生产原数据库身份有歧义，未打开/迁移/清空/恢复；不能把候选直接接回旧库。

生产主仓174个/TTS19个源码及生产.env、声线配置与进入本轮备份一致。原主仓HEAD d3ed6d68f2509ad51bea15cf8224c5f3a165d957及85项dirty保留，原TTS3814b4c9d32bb17c3638cf851e5649d9c7d17fa7及7项untracked保留。备份在同级batch01-private/preflight-01。

本轮44次真实模型传输：DS30、GLM14，40成功、4超时。新发信0；此前8封授权还剩7封。专用文件ds.txt/glm02.txt/ds-final.txt保留；ds04取消未创建。专用仓tianyi-audit-round02-20261007 Issue #1保留[B01-DS]标题标记，正文/状态未请求修改。无额外OAuth/权限待办，不清理对象。

## 最短下一步与禁止误判

A4需可信操作状态输出与自由正文边界的工程设计；仅关键词、action_refs或第二模型自评不能保证任意正文没有假声明。不要把本批已通过机制冒充A4已修好。多动作后续自动推进、生产数据身份、迟到worker对账/跨会话路由、junction TOCTOU仍按REPORT保留，不重跑259项，不回滚真实已发生操作。

正常启动复用私有`batch01-private/open-repair-window.ps1`；先正常关闭已确认归属Godot并等待其Core/TTS代际退出。原始证据保留D:/TianyiRepair/batch-01-20261012，不公开数据库、认证或资产。
