# 独立对抗审查 — Codex / Sagan

独立实例Sagan在新上下文首次只读审查；后续恢复同一实例补审邮件/记忆与Drive。不是另一个模型排名，也不把主执行者复测写成独立复测。审查者零模型API、零生产操作、零业务文件修改；现已关闭。首次原始意见见[evidence/independent-review-original.md](evidence/independent-review-original.md)，主执行者复现见[review-reproduction.json](evidence/review-reproduction.json)。

## 反例、分歧和处置

| 独立发现 | 主执行者复核 / 处置 |
|---|---|
| 只比较源前后哈希漏掉迟到WAL及A→B→A复制竞争 | 只修审计probe为源前/复制/源后文件集合+哈希比较；5自测通过。仍非原子SQLite快照，原证据保留 |
| DB检查异常不足以解释全部Agent失败；时间列/命名空间水位不可混用 | RC-01下调原因置信度，不宣称已证明损坏时间、数据损失或某次历史恢复错误 |
| 无待办“确认”重置task/cache，但聊天历史仍在；之后仍可能生成新票据 | RC-02明确保留历史和可恢复反例；文件/M02首轮失败不抹除 |
| 裸“{”可能来自合法JSON的reply字段，不一定是网关截断 | 真实parse_reply与receipt反事实复现；RC-03只确认输出层未拦无效交付，wire首因待验证 |
| issue_write的method=create/update未命中工具名副作用判断 | 实际源码AST复现并给write_file成功控制；不误报成权限绕过 |
| TTS gbk打印反例不等于已取得live sys.stdout和完整栈 | 保留高置信机制而非每条503均同源，UTF8最小反事实与现场日志分开 |
| 邮件虚报会话并非全无旧账本；有旧搜索记录，不足以证明模型错误引用具体回执 | 改为“没有与当前send/query声明对应的新执行”；新会话不是因果修复，因为首轮也只口头确认 |
| 一次send+同账号readback不等于独立收件人送达或全邮箱恰好一次 | 只声称检查链内一次发送、连接器接受并读回指定ID；不重发 |
| 记忆recall事件无完整工具正文，旧值可能来自自动注入 | RC-10区分工具调用与答案来源；现场事实24/25精确反事实相似度0.7241，措辞改为“记住更正”才跨会话180 |
| 否定“不要记住”也命中晋升；candidate含“公司”可自动confirmed | 不泛化成所有“保存更正”失败，不建议只补关键词了事 |
| Drive invalid_grant发生在搜索，不能证明资源接口线上失败 | RC-11拆分OAuth现场阻塞与资源桥静态/离线缺失；ChatGPT上传不代表本机账号权限 |
| 实际Drive handler：search有文件也只给名称/类型；resources/read能给正文；tools/call(resources/read)失败 | 独立内存stub复现。宿主只tools/call，嵌入resource成功不反驳独立资源桥缺口 |
| coverage把已测issue create/get标成无授权；Drive对象已有仍标缺对象 | 修审计清单映射，不改原业务结果 |
| method/action枚举漏review event=APPROVE直接提交等分支 | 加入event枚举；仍未授权执行真实PR审核，不把登记当实测 |
| 两个startup钩子的登记ID相撞，生命周期钩子不等于HTTP路由 | ID加入handler；报告区分3 HTTP+1 WS与3生命周期钩子 |

## 独立性边界

独立审查未操作当前窗口、未访问私有数据、未实发邮件/读Drive，也未复核所有视觉自然度和真人听感。主执行者之后发现的Godot旧effort守卫与首次speech夹具标记遗漏，属于主执行者检查，不冒称独立验收。不存在“独立审查证明没有未知漏洞”的结论。

Drive补审原始意见见[evidence/independent-review-drive.md](evidence/independent-review-drive.md)。收尾进一步将没有执行的只读/可设合成对象分支从笼统“权限阻塞”改为“功能未验证”；真正受业务写入/私有对象范围约束的仍列阻塞。这是审计分类修正，不改变任何原任务成绩或授权。
