# 第二轮根因工作记录（未收工）

基线为第一轮审计提交837318335307c85bb288265d0b80b4c7256d46f0。以下修订保留旧证据，不代表全部覆盖闭合或Manager已批准修复。业务逻辑和正式提示词未修改。

| 根因 | 本轮新增证据与首次偏离 | 正常对照 / 反事实 | 因果边界 |
|---|---|---|---|
| RC01 数据身份与损坏 | 桌面命名空间中normal与UNC的volume_serial3903461716/file_index2533274790580297一致；SQLite显式读事务backup水位一致仍报Tree4/page4/cell14/Rowid672 out of order及24条非法时间戳。Codex同名普通路径打开另一file_index3940649673999336 | 新桌面nonce进入同一事务快照，Codex错误视图被探针拒绝 | 不能从同名路径/HEAD/无package标志推断部署身份；未直接检查Core的SQLite句柄，未查明损坏产生时间及写入者 |
| RC02 无待办确认重置任务 | 前台avatar-chat-1612317输入确认时没有pending，原task目标和6801字符缓存存在；handle_chat_locked的else创建新task/ResultPages，末态intent=确认，缓存对象/引用已更换，随后重新读完整文件 | 同会话avatar-chat-1518168输入继续，task ID/原目标/缓存引用保持不变，未重新读取；有效write_file/Gmail票据确认也保持任务 | 这是宿主分支的确定行为；并非模型删除历史。历史仍在，新目标/预算/工具缓存不同 |
| RC03 输出解析/格式 | F01原始content的reply含双转义换行，parse保留字面反斜杠n，显示/TTS沿用；F03正常单层换行成功。实际raw content会带JSON外前后文，解析器部分能恢复 | F03取全长文件及三字段正确 | 第一轮仅显示左花括号的具体首次偏离尚待本轮同条件捕获；不由这两个格式样本概括所有解析失败 |
| RC04 Gmail业务错误成功化 | 独立真实连接器对不存在合成messageId返回content文本Error: Invalid id value，缺isError；部署适配器重放同一raw返回ok=true。空搜索返回空字符串且ok=true | 同一连接器正常读取本轮邮件成功；当前Godot经票据读取、计算120-45=75及附件名正确 | 首次业务状态丢失在连接器回执表达；适配器依赖isError进一步保留错误成功态。独立调用与天依执行分列 |
| RC05 TTS确定性编码故障与重试分类 | 正常Gmail回答首片“已经读取完毕 ✅”；实际TTS14200 stdout/stderr=gbk、errors=surrogateescape、utf8_mode=0，完整异常栈落在GPT-SoVITS inference_webui.py:844 print目标文本，U+2705不可编码。server catch→503；Core据状态码标retryable=true并重试同片，TTS23396重复同错 | 本轮多个普通中文片段合成/播放成功；相同部署print语句在内存中：原句GBK失败、去字符GBK成功、原句UTF8成功；400/503分类反事实；正常关窗后正式链恢复普通短句播放 | 首个运行异常不是Gmail/数值计算/GPU声学运算。UTF8打印成功不保证完整emoji合成成功；去emoji仅反事实，不是已决业务修改。不能把所有Core重试当GPU合成 |
| RC09 判卷可信度 | 主执行独立复现F01错误请求/错误文件的read回执仍PASS；1750包含175也PASS | 正确样例PASS、无回执FAIL/actual_read | 证明两个判据缺口，不证明所有旧成绩均误判；旧成绩不改 |
| RC11 Drive资源桥接 | 授权后独立真实resources/read读出专用TXT正文；同服务search只返回名字/MIME，不含ID/正文，Core没有resources/read桥接 | search有结果/无结果与独立资源正文读取分列 | OAuth失效已解决，未实现的正文入口不能因独立读取成功而升级为天依已实现 |
| R2-RC13 Gmail启动工作目录 | 仓库根目录启动时先stdout输出OAuth复制提示，MCP initialize JSONDecodeError；改为正式Core工作目录，初始化及4个固定读请求成功 | 唯一改变工作目录；复制后的OAuth文件与仓库源文件逐字节一致 | 属于实际安装连接器的条件性启动副作用/stdio污染；未证明当前正式Godot启动发生同错，不改正式启动方式 |

证据：local-group1-trace-v2.json、longfile-confirm-trace.json、gmail-independent-read.json、drive-independent-read.json、gmail-tts-live-trace-v2.json、tts-exact-counterfactual.json、grader-counterexamples.jsonl、local-mail-state.json，均位于本目录evidence。原始日志、事务快照与OAuth资料只留私有目录。

RC06/07/08/10/12及其余底层遗漏仍按原证据层次与独立COVERAGE_REVIEW逐项处理。本记录尚不构成最终ROOT_CAUSES结论。

修复建议供Manager集中裁决：按任务控制/票据连续性、连接器回执与资源桥接、交付解析、语音编码与错误分类、记忆数据语义、评测与取证判据分组。建议须以对应最小反事实约束范围，不先改提示词来掩盖宿主缺陷。

### RC02新增原始模型证据与独立反例修订（浏览器366）
R2-B01已完成导航/resize/snapshot/evaluate，原始模型avatar-chat-1731321在尚有预算时停止并要求“继续”；继续avatar-chat-1798932返回finish_reason=stop、tool_calls=null，content声称browser_find待确认且列参数。turn.final pending_head=null、calls_used仍6/18、rounds7/9。这证明原始响应已无提案，不能归为适配器丢失tool_calls；但原先“首次偏离在模型”的判断已被独立审查反例修正。

实际main.py:1490把“存在pending”与“已有task且文本为继续”合并，:1494无条件写入“既有操作仍待确认”，:1538随后将该提示加入system。现场input.before证实该请求pending=null、已有task、text=继续，因而更早的可定位语义偏离在宿主状态提示构造。主执行运行continuation-counterfactual-01.json的五个实际AST隔离输入：无pending+继续与真实pending+继续生成相同提示；无task、普通新要求不进入。源码和脚本hash均保留，API=0。

该隔离证据证明宿主提示与状态不一致，尚未证明仅删除这句提示就能改变该次模型行为；不能排除其他上下文影响。现有wire消息观测只留整体hash/角色/长度，不等于逐段正文。两次真实工具schema一致且包含browser_find，可排除这两次未提供工具。主执行未对无票据文本再次输入“确认”。

### RC02单步反事实已执行
同会话366、同页面，R2-B01-CF avatar-chat-1986553改成单步明确工具调用并新建任务，真实tool_calls/browser_find提案产生，但该轮最终content为未闭合JSON并触发格式回退；不能把整个对照称为成功。原生确认avatar-chat-2081817后MCP返回2匹配，pending清空。此控制同时改变措辞、任务预算、历史及system长度8825→3282，不能独立证明唯一诱因。原始content前文说已执行、JSON reply说等待执行；解析丢弃正确前文并保留错误reply，随后交付沿用。证据browser-group1-trace.json（8个前台请求、13个模型HTTP、5个实际MCP回执）；browser-group1-state.json的43次HTTP是本轮累计，非此组消耗。

### R2-RC14：损坏UTF-8与字节分页共同导致额外损失
隔离实际read_file，65535个ASCII后接甲END，正常next_offset=65535且拼接保留甲；仅首字节改0xff，首次decode异常指向开头，未处理末尾半个合法字符，next_offset=65536，后续把甲分成三个替代字符。边界在tools.py:read_file的UnicodeDecodeError分支；不推及所有UTF-8文件。edge-counterfactuals-01.json/read-mixed-utf8。

### R2-RC15：命令白名单校验与实际分词不一致
run_command先line.split取exe，再shlex解析。相同r2_echo.exe白名单、相同参数，带引号且无空格目录到达mock subprocess；只将目录改R2 Fixture即把basename识别成r2而拒绝。全程mock，无实际程序执行，无正式白名单变更。证据edge-counterfactuals-01.json/command-quoted-path。

### R2-RC16：空值/类型错误未在适配和解析边界统一拒绝
实际方法AST隔离：complete content=null→字符串None，complete_with_tools→空content；message=null前者ProviderError后者AttributeError。parse_reply(reply:null)→None，数字reply→字符串175；正常中文控制通过。孤立左花括号仍原样回退；这些反例不证明旧现场左花括号由何层首次产生。证据edge-counterfactuals-01.json。

### R2-RC17：原子写失败留下临时文件（单点）
合成PermissionError注入os.replace，原文件保持完整且返回错误，但write.txt.tmp-*六字节保留。temp目录最终由审计脚本清理，不能把它描述为write_file自清理；正常append四分支和拒绝三分支另有控制。证据local-branches-01.json/write-replace-error。

### RC02/TA11追加跨场景边界（B02/B03）
浏览器367的有效确认avatar-chat-3514020后，info确实执行，但raw content又声称有level=error待办，实际pending=null且没有工具调用。该请求走approve真实回执分支，与无待办继续的1494错误提示不同，不能将所有伪待办都归为该分支。明确新任务avatar-chat-3792376仍raw finish_reason=stop/tool_calls=null/calls_used=0，却声称error读取成功；错误内容与历史info回执一致，可能复用历史，但未证明具体内容来源。首次可见虚假完成在原始响应，尚不能排除其他宿主上下文影响。error分支记录为Agent未执行，不能当作工具功能通过；不刷重试。证据browser-group2-trace.json。

### R2-RC18：Windows前台窗口API装配层级错误
实际tools.active_window将ctypes.windll当作user32库使用。忠实的LibraryLoader→user32双层替身在GetForegroundWindow查找失败；仅改传入对象为user32后同一实际函数返回固定合成窗口标题。证据wiring-counterfactuals-01.json前两例；真实前台查询次数0，不声称已有现场失败。正常控制证明函数其余路径在该替身合同下可行，未修改业务。

### R2-RC19：凭据重载类能力未接到正式factory
实际build_provider的AST构造器spy显示deepseek/glm/stepfun有合成key时均不传reload_config；无key/未知provider返回Mock。源码全局调用关系由独立审查复核。证据wiring-counterfactuals-01.json后五例。必须将类参数支持和隔离重载测试与正式装配分开；未检查运行中provider对象，也未实测线上换key。

### RC07/RC10：记忆更正作用域的现场闭环与相似度反事实
GLM前台372对仅会话请求MEM01保持candidate=null；MEM02/03/04显式请记住生成fact26/27/28 confirmed/global。MEM05普通更正的raw candidate含晨星175且保留另一实体/日期，但memory.promotion首次将其定为pending，main随后保存fact29 scope=session；新会话373实际recall_memory两查询只能取得global晨星120、暮云180及日期，答案忠实沿用旧值120。两个同身份事务快照证实落库状态，25条既有事实未发生变化。
正常保存与跨会话召回为控制。memory-counterfactual-01在临时库固定同一candidate、仅给user文本追加请记住，promotion变confirmed/global、跨会话可见175；但词法替换superseded的是复合暮云条目，原晨星120仍confirmed。新candidate本身仍含暮云180，不能说暮云语义全部丢失。由此分离两层：晋升/作用域没有识别更正操作；词法相似度缺实体/属性键，且复合candidate进一步模糊替换单元。事实保存事件存在，但用户只看到模型的条件性承诺，没有fact_id/最终scope回执。
证据memory-frontend-trace、memory-before-correction、memory-after-correction、memory-counterfactual-01。未清理或恢复真实库，未把隔离替换结果冒称现场已发生。

## R2-RC20：工具成功后补答超时，成功回执未在当次交付

前台session374 / avatar-chat-820517已真实创建Label_1，随后模型请求另一待确认动作，再进入agent_loop.py:173的plain fallback；45秒transport deadline触发ProviderError，未进入parse/delivery。当次UI只见API超时；不是标签未创建，也未证明网关永久故障。后续961745创建草稿、1131184搜索成功并交付为正常控制；独立Gmail API回读Label_1和草稿/60字节附件一致。首次可见偏离边界为工具提交后的补答异常未降级交付已持久回执；原始成功应保留，重试不得重复写。证据[现场](evidence/gmail-group2-trace.json)、[独立核验](evidence/gmail-draft-label-readback.json)。未做同条件故意超时的隔离反事实，本条因果边界限于所观测执行链，不能概括所有“无答案”。
