# 本轮对象登记（持续更新）

标记R2-20261007 / [R2-*]。所有夹具均为合成资料；Codex准备与独立核验不计为天依执行。

| 对象 | 身份 / 允许操作 | 当前处置 |
|---|---|---|
| 本地专用目录 | {PRODUCTION}/work/tianyi-exam-t1/R2-20261007，既有write-root内；本轮文件读/写/覆写/拒绝/取消 | 保留；只清理登记对象，不动目录外文件 |
| short.txt | 100+75=175；2026-10-18；蓝色纸鹤。哈希见local-fixtures.json | 前台读取成功 |
| long.txt | 320行，BEGIN=松果，END=纸鸢，CODE=R2-END-7319 | 长文、offset、缓存待验证 |
| attachment.txt / upload.txt | 纯合成文本；仅用于自有邮箱和测试网页 | 已备齐；Codex已发送1封自有邮箱附件夹具 |
| fixture.html | loopback页面：文字、颜色、表单、提示、拖拽、上传下载、console | 已备齐；不以普通桌面私人画面测试视觉 |
| result-a.txt | 58字节；SHA614c618606f767e6510e73403b17d52a50a5c3295ddc528b4bbfafff948b3a36 | 天依确认后写入、独立回读一致；保留 |
| GitHub私有仓库 | SummerTianYi/tianyi-audit-round02-20261007；仅本仓合成branch/file/Issue/PR/评论/标签 | 已创建/读回；fixture commit4be028cba40a7de38c36d4b8110a7400b1c8046f |
| Drive目录 | R2-TIANYI-AUDIT-20261007；14W3ajQ82dn2atuaCJKLJeISS8S0zGkMf | 已建立；保留 |
| Drive文件 | R2-TIANYI-Drive-evidence.txt；1A8qruMefQjK-q1Bca1zSnCzo2KhYSETH；合成120-45=75 | Codex连接器已写入/读回；天依尚未验证 |
| Gmail本轮对象 | 已核验OWNER_TEST_MAILBOX；最多8封自发自收，附件/回复/转发；R2草稿/标签/仅匹配R2的过滤器；垃圾箱/删除仅登记邮件 | 已获所有者具体授权；当前发送1封，剩余额度7封；message/thread ID 1a1170bf8fa1edf8，subject=[R2-20261007] Fixture inbox 01，附件R2-attachment.txt。Codex准备，不计天依成功 |
| 审计会话 | 360开场，361文件组，362录音组；后续仅合成事实 | 保留，不清库、不恢复旧库 |
| 私有证据 | workspace/work/private-round02，含事务快照、OAuth备份、诊断日志 | 不提交/上传。原证据保留 |
| 诊断代际 | v1根目录；v2 phase02；控制可关闭，入口有原字节备份/哈希 | v1已正常退出并精确恢复；v2经正式入口重启 |

Gmail和Drive具体授权来自所有者“同意全部上述范围”；随后“已完成”代表Google授权操作完成，经API再核验有效、账号一致。Drive只读范围未扩大。最终正式配置应恢复原字节；不恢复已被用户批准替换的过期OAuth令牌。

最终清理尚未执行；未来清理不得借本登记扩大到旧审计或普通业务数据。

- 追加fixture-v2.html（原fixture.html保留）：radio/slider、confirm/prompt、文件/文本drop、可读回auditState、合成fetch及A/B导航。仅在R2专用目录提供loopback服务；不承载私人数据。

- 浏览器fixture-v3.html：v2保留；新增多选、hover、延迟显隐、A/B视觉标记、鼠标独立计数、网络status/count；SHA 8820ea9b0f6685e69bc74e9ed50a9dfaec6f28a3e4fec4a034123aa43cb033a3。只允许专用loopback网页交互及相对合成资源读取，控制台R2 synthetic error为预期夹具。
- Loopback HTTP helper PID36916，启动00:32:30，本轮专用127.0.0.1:8768，只服务登记R2目录，独立GET short.txt HTTP200；结束核对PID+starttime后停止，不关闭其他进程。

## 2026-10-08 GitHub夹具增补（Codex准备层）
在已登记专用私有仓库中计划创建 r2-fixture-pr 分支、r2-pr-fixture.txt、一个标记Issue和PR；允许读取、评论、更新、合成分支/合并等本轮检查，禁止指向生产仓库。仅处置登记对象；完成后关闭Issue/PR并按实际授权清理专用分支，保留审计证据。准备过程不算天依成功。

GitHub准备结果已独立读回：Issue #1（OPEN），PR #2（OPEN，main←r2-fixture-pr），头提交94ee311a99fec08d8f66388dd62fe9f108a7b117，r2-pr-fixture.txt blob c643db9a0f3bf432a040cf2e10fb4ffcddb22bf5。PR已附本任务。仅专用仓库；本次4次远端写入，CLI验证不是天依执行。

- R2-MEM-20261007：仅合成项目R2-晨星和R2-暮云，预算120/180/更正175、日期2026-10-18，使用当前Godot会话372输入。请求限定当前会话，用于实体/属性/作用域/更正/保存回执检查；若宿主提升全局，仅登记实际fact_id，不删库，不以删除会话冒充遗忘。最终按可用入口处理，缺正式遗忘入口则保留登记并向Manager说明。
- R2-MEM正常保存对照：后续只对上述两个合成项目显式允许跨会话事实保存，用于与会话限定请求比较；更正只限R2-晨星预算，其他实体/属性须保留。清理边界同上，不接触任何私人事实。

- Gmail M02前台组：专用标签R2-20261007-Audit，专用草稿主题[R2-20261007] Draft 02（收件人为已授权自有测试邮箱，正文合成日期2026-10-18/余额75，附件本轮attachment.txt）。允许创建/读取/改名/删除本轮标签与该草稿，不扩大邮件发送额度；所有ID从真实回执登记。仅作用于原本轮fixture邮件及本轮新草稿。

## 02:32 收尾处置（覆盖早先“待验证”时点）

长文件分页、Drive前台search、GitHub Issue1读取/标题更新已取证。新Gmail Label_1、草稿r-7540607348453029159/消息1a1178f7d42d19da及60字节attachment.txt经独立回读；发送仍1/8。全部登记资料/合成会话360–375/facts26–29保留供Manager复现，未删除历史/业务数据。helper36916按创建时间和专用目录核验后停止。诊断全部关闭并恢复原入口/.env；用户批准的Drive有效OAuth保留。未实施清理删除，未来只可清理本轮登记对象，不扩及旧轮。
