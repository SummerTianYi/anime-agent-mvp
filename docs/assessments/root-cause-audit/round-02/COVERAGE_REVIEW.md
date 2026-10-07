# 第二轮独立覆盖复核（开放）

审查日期：2026-10-08。基线 `837318335307c85bb288265d0b80b4c7256d46f0`。本文件先逐行复核原 coverage.json 的 **127 功能未验证 + 47 阻塞 + 10 未启用/未实现 = 184 个不同 ID**，后追加原 **72 个有实证 ID**，合计原256项；不改原矩阵、原成绩或业务脚本，不把准备者 Codex 的操作当成天依执行。本实例未操作桌面、未启动 Core/MCP/TTS、未运行真实模型或调用连接器。

最新材料边界采用主执行者直接提供的授权和 TEST_OBJECTS.md：本地 R2 short/long/HTML/upload 文件已备；SummerTianYi/tianyi-audit-round02-20261007 专用私有仓已有；Drive 专用文本已建立且只读 OAuth 已恢复；Gmail 自有邮箱最多 8 封及专用草稿/标签/过滤器/指定邮件删除已授权。当前登记已有 1 封 R2 合成附件邮件，尚余 7 封额度。**这些不能继续以“缺账号、缺材料、缺写入授权”笼统阻塞。** 额外组织、非作者审阅身份、Copilot、全邮箱模板作用域分别列出，不扩大现有授权。

本审查读取了 362 项通过记录中的测试 ID，并逐组核对相关源码与具体断言；没有再运行这 362 项。Python 362 项和历史 Godot 守卫分开。每行的 O/S/G 证据代号见后面的断言目录。报告及同名 JSON 使用相同 184 行，机械核对没有丢行或重复。

## 反例与分类纠正

1. **原阻塞分类部分来自启发式，不是真实权限失败。** coverage.py:88 把全部 browser/search 归入 readonly；无 readOnlyHint 的其他 MCP 则在第 196–197 行写成缺真实对象/授权。Gmail list_email_labels、list_filters、get_filter 实质是读入口；browser_evaluate、run_code_unsafe、click/drop 也不能因为服务名 browser 就认定无副作用。应按具体操作及授权对象复核，不能拿注解缺省代替权限证据。
2. **一项已有前台失败被覆盖回“未验证”。** coverage.py:111给 get_file_contents 记过“已执行正文完整、最终仅显示{”，后面的通用 M- 分支（196–197）再次改状态。原 coverage.json 把该项放进 127。它应同时保留旧层次失败证据和本轮待复测，不能称从未尝试，也不能据此前台调用算交付成功。
3. **Drive 有材料、有 OAuth，但正文桥接仍未实现。** tools/gdrive/index.mjs:39 有 resources/read；第 127 起 search 仅将 name/mimeType 拼成文字，未交付文件内容/ID。Core mcp_host.py:112/135/205 只列工具并调用 tools/call，无 resources/read 入口。TA09 仍 N；独立连接器直接读成功只证明服务/授权，不补成天依功能。
4. **已有离线断言不能冒充全能力。** L-screenshot/clipboard_read/active_window 的既有测试只验依赖缺失或非Windows时失败；同样，S-MCP 用内存 fixture server 验JSON-RPC与归一化，不验94个工具的业务实现。UI-search 的旧守卫只检查过滤后 child_count>=2（verify_session_ui.gd:131–134），保留未过滤的两卡也能满足；需要断言具体剩余ID/标题及无结果场景。
5. **评测器误 PASS 已由主执行者独立复现。** 已只读审查 round02_grader_counterexamples.py：原F01正控制 PASS、无关请求/错误文件回执仍 PASS、1750错误总额仍 PASS、无回执 FAIL/actual_read；evidence/grader-counterexamples.jsonl 与本实例前一份报告一致。脚本只读 cases 并构造内存证据调用 grade/打印，未调用模型、未篡改旧成绩。这些反例仍开放，不能只靠重新贴362通过记录消除。

## 184 行的当前工作分类

分类表示下一步和证据层次，不是新的通过率，也没有把所有场景穷尽：

| 代号 | 含义 | 行数 |
|---|---|---:|
| O | 有与该项相关的具体离线/历史断言；仅覆盖该断言范围 | 28 |
| R | 主要对象已就绪，可安排受控执行；实际调用/交付未验证 | 47 |
| P | 可在现有授权范围准备前置状态、加强断言或明确额外对象；不是材料/账号总阻塞 | 93 |
| X | 成功分支确有额外身份、组织、Copilot或fork落点条件待核 | 6 |
| N | 未实现、正式链未启用或用户明确禁用 | 10 |

原 47 个“阻塞”的复核分解：O=5、R=7、P=30、X=5。X 仍是明确条件，**不等于已观察到403或一定无权**。原 127 个“功能未验证”的复核分解：O=23、R=40、P=63、X=1。

### 逐行映射

M-/METHOD 行的 schema 定位均指原 `docs/assessments/root-cause-audit/evidence/mcp-schema.json`。它是接口合同证据，不是对应工具执行通过。S-MCP 是共享断言，表中已明确标注“仅共享”。

| 原 ID / 原桶 | 当前 | 最小场景与有效判据 | 已有断言 / 实现定位 | 剩余条件与边界 |
|---|---|---|---|---|
| AD06 / 阻塞 | O | 合成R2画面走Anthropic视觉；事实来自视觉结果，主脑答案核对颜色/数值 | O-VISION；services/agent-core/agent_core/main.py:AnthropicCompatibleProvider; services/agent-core/agent_core/tools.py | 协议构造及thinking过滤已离线；本地HTML已备，现场纯合成画面由唯一操作者安排，非缺账号材料 |
| EF04 / 未启用或未实现 | N | 两模型reasoning controls为空；区分effort任务预算与模型内部推理开关 | 静态 main.py:1387；services/agent-core/agent_core/main.py:MODEL_REASONING_CONTROLS | 未实现，不能把effort三档验收代替；需产品/适配实现，不以外部Key阻塞 |
| TA09 / 未启用或未实现 | N | Drive search找到名字不等于读正文；resources/read独立桥接缺失 | 静态 mcp_host.py:112,135,205；tools/gdrive/index.mjs:39,127；services/agent-core/agent_core/mcp_host.py; tools/gdrive/index.mjs | OAuth只读已恢复、文本已备；缺Core资源入口实现，不缺测试材料 |
| VO05 / 未启用或未实现 | N | 保持manual：startup不建后台listener，voice.stop不重启 | O-MANUAL；services/agent-core/agent_core/wake_word.py; services/agent-core/agent_core/main.py:start_wake_word_listener | 当前有实现但明确禁用；不得为覆盖擅开后台唤醒 |
| PR01 / 功能未验证 | O | 上线问候成功后才消耗冷却；失败不消耗；并发连接不重播 | O-GREET；services/agent-core/agent_core/main.py:_proactive_greeting | 已有离线具体断言；前台听感/静音时段仍需现场 |
| L-list_dir / 功能未验证 | O | 列R2目录，目录排前；不存在/越界根目录负例 | O-LIST；services/agent-core/agent_core/tools.py; services/agent-core/agent_core/permissions.py | R2目录已备；隔离基本排序已通过，不等于前台交付 |
| L-screenshot / 阻塞 | O | 只采R2合成窗口，校验文件/尺寸；依赖缺失显式错误 | O-DEGRADED；services/agent-core/agent_core/tools.py; services/agent-core/agent_core/permissions.py | 已有断言仅mss缺失退化；真实成功路径待唯一操作者准备画面 |
| L-active_window / 阻塞 | O | 焦点置R2页后取进程/标题，焦点变化再对照 | O-DEGRADED；services/agent-core/agent_core/tools.py; services/agent-core/agent_core/permissions.py | 既有断言仅非Windows退化；纯合成窗口可准备，不是账号阻塞 |
| L-clipboard_read / 阻塞 | O | 专用R2剪贴板哨兵→取回原字符；原内容保全恢复 | O-DEGRADED；services/agent-core/agent_core/tools.py; services/agent-core/agent_core/permissions.py | 既有断言仅pyperclip缺失；剪贴板设置是现场可逆准备 |
| L-look_at_screen / 阻塞 | O | 合成图红蓝块+175+日期，核对视觉响应、最终答案 | O-VISION；services/agent-core/agent_core/tools.py; services/agent-core/agent_core/permissions.py | 协议/超时注册有断言；需画面与当前视觉服务实调，不能借screenshot成功代验 |
| L-run_command / 功能未验证 | P | stub subprocess校验空白名单/拒绝token/超时unknown/输出截断；真实仅白名单无副作用命令 | 无直接能力测试；S-GATE仅授权共享；services/agent-core/agent_core/tools.py; services/agent-core/agent_core/permissions.py | 检查当前白名单是配置核验，不默认为未启用；本轮不为测试扩大命令集 |
| L-read_tool_result / 功能未验证 | O | long.txt尾部R2-END-7319、offset续读；无效ref/另会话/负offset拒绝 | O-PAGES；services/agent-core/agent_core/result_pages.py | 长文已备，相关页缓存隔离断言通过 |
| M-mcp__browser__browser_close / 功能未验证 | R | 关闭最后一个R2标签；再list确认无旧页 | S-MCP（仅共享）；schema:10 | loopback HTML与上传文件已备；实际天依调用/回读仍待执行 |
| M-mcp__browser__browser_resize / 功能未验证 | R | R2页800×600→1024×768，读回innerWidth/Height | S-MCP（仅共享）；schema:26 | loopback HTML与上传文件已备；实际天依调用/回读仍待执行 |
| M-mcp__browser__browser_console_messages / 功能未验证 | R | 页内产生info/error哨兵，按level/all查询并区分清空前后 | S-MCP（仅共享）；schema:55 | loopback HTML与上传文件已备；实际天依调用/回读仍待执行 |
| M-mcp__browser__browser_handle_dialog / 功能未验证 | R | 依次accept/dismiss confirm，prompt填R2值；核对页面结果 | S-MCP（仅共享）；schema:94 | loopback HTML与上传文件已备；实际天依调用/回读仍待执行 |
| M-mcp__browser__browser_emulate_media / 功能未验证 | R | light/dark、reduce及null复位，用matchMedia独立读回 | S-MCP（仅共享）；schema:122 | loopback HTML与上传文件已备；实际天依调用/回读仍待执行 |
| M-mcp__browser__browser_evaluate / 功能未验证 | R | 只读返回R2标题/算式175，核对数值和正文 | S-MCP（仅共享）；schema:214 | loopback HTML与上传文件已备；实际天依调用/回读仍待执行 |
| M-mcp__browser__browser_file_upload / 功能未验证 | R | upload.txt选择后核对文件名/大小；paths省略测试取消选择 | S-MCP（仅共享）；schema:250 | loopback HTML与上传文件已备；实际天依调用/回读仍待执行 |
| M-mcp__browser__browser_drop / 功能未验证 | R | 分别paths文件与data MIME拖入，核对drop处理器结果 | S-MCP（仅共享）；schema:274 | loopback HTML与上传文件已备；实际天依调用/回读仍待执行 |
| M-mcp__browser__browser_find / 功能未验证 | R | R2精确文字、regex、无匹配三例，核对节点定位 | S-MCP（仅共享）；schema:319 | loopback HTML与上传文件已备；实际天依调用/回读仍待执行 |
| M-mcp__browser__browser_fill_form / 功能未验证 | P | textbox/checkbox/radio/combobox/slider逐项填值后读回 | S-MCP（仅共享）；schema:348 | 本地HTML已有；补具体状态/控件/路由即可，无新账号 |
| M-mcp__browser__browser_press_key / 功能未验证 | R | R2输入框Enter/Tab，与focus和提交计数对照 | S-MCP（仅共享）；schema:411 | loopback HTML与上传文件已备；实际天依调用/回读仍待执行 |
| M-mcp__browser__browser_type / 功能未验证 | R | 同输入框普通/slowly/submit，核对完整文本及提交次数 | S-MCP（仅共享）；schema:435 | loopback HTML与上传文件已备；实际天依调用/回读仍待执行 |
| M-mcp__browser__browser_navigate / 功能未验证 | R | 仅loopback fixture.html，核对URL和R2标记 | S-MCP（仅共享）；schema:476 | loopback HTML与上传文件已备；实际天依调用/回读仍待执行 |
| M-mcp__browser__browser_navigate_back / 功能未验证 | P | 先R2页A→B再back，核对A标记与URL | S-MCP（仅共享）；schema:500 | 本地HTML已有；补具体状态/控件/路由即可，无新账号 |
| M-mcp__browser__browser_network_requests / 功能未验证 | P | R2页面发合成fetch，核对static true/false及过滤 | S-MCP（仅共享）；schema:516 | 本地HTML已有；补具体状态/控件/路由即可，无新账号 |
| M-mcp__browser__browser_network_request / 功能未验证 | P | 用上项真实index分别取请求/响应头体，核对nonce；无效index负例 | S-MCP（仅共享）；schema:549 | 本地HTML已有；补具体状态/控件/路由即可，无新账号 |
| M-mcp__browser__browser_run_code_unsafe / 功能未验证 | R | 仅已登记页只读返回标题；不能由evaluate成功代替本工具 | S-MCP（仅共享）；schema:589 | loopback HTML与上传文件已备；实际天依调用/回读仍待执行 |
| M-mcp__browser__browser_take_screenshot / 功能未验证 | R | R2页png/jpeg/webp、css/device、元素/全页，检查文件和尺寸 | S-MCP（仅共享）；schema:614 | loopback HTML与上传文件已备；实际天依调用/回读仍待执行 |
| M-mcp__browser__browser_snapshot / 功能未验证 | R | R2页全页/target、depth和boxes，核对指定节点 | S-MCP（仅共享）；schema:668 | loopback HTML与上传文件已备；实际天依调用/回读仍待执行 |
| M-mcp__browser__browser_click / 功能未验证 | P | R2按钮left/right/middle/doubleClick，核对独立计数 | S-MCP（仅共享）；schema:701 | 本地HTML已有；补具体状态/控件/路由即可，无新账号 |
| M-mcp__browser__browser_drag / 功能未验证 | R | 页内源到目的位置，核对drop计数与目标文字 | S-MCP（仅共享）；schema:756 | loopback HTML与上传文件已备；实际天依调用/回读仍待执行 |
| M-mcp__browser__browser_hover / 功能未验证 | R | hover后展示专用提示，核对可见状态 | S-MCP（仅共享）；schema:793 | loopback HTML与上传文件已备；实际天依调用/回读仍待执行 |
| M-mcp__browser__browser_select_option / 功能未验证 | P | 单/多选控件选择后读回选值；未知option负例 | S-MCP（仅共享）；schema:821 | 本地HTML已有；补具体状态/控件/路由即可，无新账号 |
| M-mcp__browser__browser_tabs / 功能未验证 | R | 执行list→new→select→close，逐步绑定index与R2 URL | S-MCP（仅共享）；schema:857 | loopback HTML与上传文件已备；实际天依调用/回读仍待执行 |
| M-mcp__browser__browser_wait_for / 功能未验证 | P | 等待R2标记出现/消失和短time，另有不满足超时控制 | S-MCP（仅共享）；schema:895 | 本地HTML已有；补具体状态/控件/路由即可，无新账号 |
| M-mcp__github__add_comment_to_pending_review / 阻塞 | P | 先pending review，再FILE和LINE/LEFT/RIGHT注释；读回thread与行号 | S-MCP（仅共享）；schema:1003 | R2 PR diff+pending review是前置夹具，不是缺授权 |
| M-mcp__github__add_issue_comment / 阻塞 | P | 同Issue正文、reaction、二者合并分别读回；另选PR一般评论 | S-MCP（仅共享）；schema:1072 | R2 Issue/comment ID |
| M-mcp__github__add_reply_to_pull_request_comment / 阻塞 | P | 已有review comment下reply/reaction/两者，核对父commentId | S-MCP（仅共享）；schema:1140 | R2 PR review thread与comment ID |
| M-mcp__github__assign_copilot_to_issue / 阻塞 | X | 仅R2 Issue分配Copilot，区分受理、任务开始和生成PR | S-MCP（仅共享）；schema:1193 | Copilot coding agent entitlement/启用待核，不是普通repo写权限 |
| M-mcp__github__create_branch / 阻塞 | R | 从登记base SHA创建R2分支，读回精确SHA；重复名负例 | S-MCP（仅共享）；schema:1242 | 专用私有仓已有 |
| M-mcp__github__create_or_update_file / 阻塞 | R | 新建→带当前sha更新→过期sha拒绝；读回bytes | S-MCP（仅共享）；schema:1311 | 专用分支/文件，sha由前次回读，不需新账号 |
| M-mcp__github__create_pull_request / 阻塞 | P | R2 head/base差异建draft PR，再读回head/base/title | S-MCP（仅共享）；schema:1385 | 准备分支差异后即可 |
| M-mcp__github__create_repository / 阻塞 | P | 原仓创建是Codex准备证据；天依同名冲突可作负例，成功需登记新的R2仓名 | S-MCP（仅共享）；schema:1435 | 额外仓对象不由已有仓成功自动授权；先在对象登记中明确 |
| M-mcp__github__delete_file / 阻塞 | P | 创建专用一次性文件→删除→404/目录确认 | S-MCP（仅共享）；schema:1491 | 同仓一次性文件夹具 |
| M-mcp__github__fork_repository / 阻塞 | X | 已有仓不能兼作所有fork目的地；先明确允许源及独立fork落点 | S-MCP（仅共享）；schema:1535 | 需要可用且获授权的fork源/目标账户或组织；非夹具文本问题 |
| M-mcp__github__get_commit / 功能未验证 | R | 读fixture commit，detail=none/stats/full_patch核对同SHA差异 | S-MCP（仅共享）；schema:1601 | 既有fixture SHA可直接用 |
| M-mcp__github__get_file_contents / 功能未验证 | R | 同仓文件与目录、ref/sha；核对精确175/日期/正文完整 | S-MCP（仅共享）；schema:1672 | 旧前台已有调用且最终失败；不能称从未试过 |
| M-mcp__github__get_label / 功能未验证 | P | R2 label存在/不存在，核对名称和颜色 | S-MCP（仅共享）；schema:1717 | 登记专用label |
| M-mcp__github__get_latest_release / 功能未验证 | P | R2临时release最新/无release，区分404和有内容成功 | S-MCP（仅共享）；schema:1757 | release是可准备对象，当前未登记；不要读真实业务release |
| M-mcp__github__get_me / 功能未验证 | R | 核对当前token身份与授权owner一致 | S-MCP（仅共享）；schema:1782 | 已有身份，别把tools/list当身份验证 |
| M-mcp__github__get_release_by_tag / 功能未验证 | P | 指定R2 tag release与不存在tag，核对ID和正文 | S-MCP（仅共享）；schema:1827 | 同仓release/tag夹具 |
| M-mcp__github__get_tag / 功能未验证 | P | R2轻量/annotated tag返回目标SHA；不存在tag负例 | S-MCP（仅共享）；schema:1872 | 同仓tag夹具 |
| M-mcp__github__get_team_members / 功能未验证 | X | 指定获准org/team非空成员与不存在team | S-MCP（仅共享）；schema:1910 | 个人专用仓不提供组织/team实体；当前对象登记无该实体 |
| M-mcp__github__get_teams / 功能未验证 | R | 当前账号返回空列表也是合法空结果；非空团队路径单列 | S-MCP（仅共享）；schema:1940 | 非空需要组织成员资格，不因空而判权限失败 |
| M-mcp__github__list_branches / 功能未验证 | R | base与R2 branch，perPage=1翻页，逐SHA核对 | S-MCP（仅共享）；schema:2217 | 分支夹具；不需新账号 |
| M-mcp__github__list_commits / 功能未验证 | R | fixture及新增R2 commit，page/perPage/filter核对 | S-MCP（仅共享）；schema:2302 | 同仓两提交即可补 |
| M-mcp__github__list_issue_fields / 功能未验证 | R | repo级/省略repo的org级区分；不支持或空结果如实记录 | S-MCP（仅共享）；schema:2341 | 非空自定义字段需仓/组织支持，个人repo不保证 |
| M-mcp__github__list_issue_types / 功能未验证 | R | repo级查询；有类型/空/不支持分别判，不硬填type | S-MCP（仅共享）；schema:2380 | 正向非空分支依赖启用issue types的仓/组织 |
| M-mcp__github__list_issues / 功能未验证 | P | 两个R2 Issue不同状态，cursor下一页及筛选 | S-MCP（仅共享）；schema:2507 | 先准备R2 Issue；材料已授权 |
| M-mcp__github__list_pull_requests / 功能未验证 | P | R2 open/closed/draft PR，page和head/base过滤 | S-MCP（仅共享）；schema:2627 | 先准备PR，author过滤应走search工具 |
| M-mcp__github__list_releases / 功能未验证 | P | R2 release列表及分页/空集合 | S-MCP（仅共享）；schema:2696 | 专用release夹具 |
| M-mcp__github__list_repository_collaborators / 功能未验证 | R | 读专用仓collaborator，affiliation与分页；空结果不等于失败 | S-MCP（仅共享）；schema:2756 | 非空多协作者需要额外成员实体，非本轮硬门 |
| M-mcp__github__list_tags / 功能未验证 | P | 两个R2 tag核对列表及分页 | S-MCP（仅共享）；schema:2807 | 专用tag夹具 |
| M-mcp__github__merge_pull_request / 阻塞 | P | 仅R2可弃分支PR，expectedHeadSha正确/过期；每种merge_method独立PR | S-MCP（仅共享）；schema:2873 | 先建可合并差异，限定专用仓，不触生产main |
| M-mcp__github__pull_request_read / 功能未验证 | P | 按九method分别读取同一R2 PR，正文/文件/commit/thread/check不可互代 | S-MCP（仅共享）；schema:2949 | PR基础夹具；reviews/check_runs非空各需对应前置对象 |
| M-mcp__github__pull_request_review_write / 阻塞 | P | create无event→加注释→submit COMMENT；另pending删除、thread resolve/unresolve | S-MCP（仅共享）；schema:3027 | 可在专用PR准备；APPROVE/REQUEST_CHANGES身份分支另列 |
| M-mcp__github__push_files / 阻塞 | P | 两文件同commit，逐文件内容与同SHA核对 | S-MCP（仅共享）；schema:3100 | 专用branch+两合成文件 |
| M-mcp__github__request_copilot_review / 阻塞 | X | 仅R2 PR请求Copilot review，核对受理与实际review分别状态 | S-MCP（仅共享）；schema:3145 | Copilot review entitlement/仓启用待核，不可泛推普通review |
| M-mcp__github__search_code / 功能未验证 | R | repo限定R2哨兵，核对path；索引延迟单列 | S-MCP（仅共享）；schema:3215 | 已有repo文本；新commit未索引不是工具协议失败 |
| M-mcp__github__search_commits / 功能未验证 | R | repo限定fixture提交信息，核对SHA；按description默认分支限制 | S-MCP（仅共享）；schema:3275 | fixture提交现成 |
| M-mcp__github__search_issues / 功能未验证 | P | repo限定R2 exact/改写概念，匹配/无匹配分别核对 | S-MCP（仅共享）；schema:3387 | 专用Issue前置夹具 |
| M-mcp__github__search_pull_requests / 功能未验证 | P | repo限定R2 PR及author，核对结果号 | S-MCP（仅共享）；schema:3497 | 专用PR前置夹具 |
| M-mcp__github__search_repositories / 功能未验证 | R | owner+完整专用仓名，核对私有仓身份 | S-MCP（仅共享）；schema:3564 | 专用仓已建立 |
| M-mcp__github__search_users / 功能未验证 | R | 只检索获准owner，核对login | S-MCP（仅共享）；schema:3625 | 不需要新账号/材料 |
| M-mcp__github__sub_issue_write / 阻塞 | P | add/remove/reprioritize+replace_parent，见新增分支表 | S-MCP（仅共享）；schema:3692 | 两个父+两个子Issue前置夹具已在授权对象类别内 |
| M-mcp__github__update_pull_request / 阻塞 | P | R2 PR改title/body/draft/state/base分别回读 | S-MCP（仅共享）；schema:3772 | R2 PR和第二base分支夹具 |
| M-mcp__github__update_pull_request_branch / 阻塞 | P | base推进一次，expectedHeadSha正确/过期分开核对head | S-MCP（仅共享）；schema:3821 | R2分支差异/冲突是夹具准备，非缺账号 |
| M-mcp__search__tavily_search / 功能未验证 | R | 用公开中性问题+限定官方域名，核对可访问来源及片段，不预设动态答案 | S-MCP（仅共享）；schema:3842 | 服务Key/网络实际可用性待实调；tools/list不证明，无已证实缺材料 |
| M-mcp__search__tavily_extract / 功能未验证 | R | 登记公开静态页面，核对已知正文哨兵和来源URL，markdown/text分开 | S-MCP（仅共享）；schema:3949 | 本地HTML不能被云服务访问；选已公开测试页面是准备工作 |
| M-mcp__search__tavily_crawl / 功能未验证 | R | 公开受控小站limit/depth=小值，核对每页URL/正文 | S-MCP（仅共享）；schema:4000 | 云端可访问小站及预算范围，不把loopback作为有效输入 |
| M-mcp__search__tavily_map / 功能未验证 | R | 同一公开小站限定domain/path，核对URL集合 | S-MCP（仅共享）；schema:4082 | 同crawl公开可达夹具；无正文不能算extract |
| M-mcp__search__tavily_research / 功能未验证 | R | 窄问题返回来源和实质结论，mini/pro/auto分支及任务超时单列 | S-MCP（仅共享）；schema:4141 | research能力/额度待核；一次search成功不证明此工具可用 |
| M-mcp__gmail__draft_email / 阻塞 | R | 草稿正文/plain/html/multipart+附件；核对draft状态且不误发送 | S-MCP（仅共享）；schema:4247 | 自有邮箱授权已有效；草稿不占发信8封 |
| M-mcp__gmail__modify_email / 阻塞 | P | 单R2 message增删专用label/已读/垃圾箱再恢复，独立回读 | S-MCP（仅共享）；schema:4361 | 使用登记ID，不能扩大到普通邮件 |
| M-mcp__gmail__delete_email / 阻塞 | P | 永久删除单个已登记可弃R2 message，定向read确认不存在 | S-MCP（仅共享）；schema:4400 | 先保全/登记该测试邮件，不再写缺授权 |
| M-mcp__gmail__list_email_labels / 阻塞 | R | 列标签并核对R2标签ID；空集合/系统标签不混淆 | S-MCP（仅共享）；schema:4418 | 查询已授权，原阻塞由无readOnlyHint推定，不是真权限证据 |
| M-mcp__gmail__batch_modify_emails / 阻塞 | P | 只给2个R2 IDs增删label，核对每个结果与未选第三封 | S-MCP（仅共享）；schema:4429 | 两测试message是夹具准备 |
| M-mcp__gmail__batch_delete_emails / 阻塞 | P | 仅两个R2可弃ID批删，逐ID确认不存在，区分部分失败 | S-MCP（仅共享）；schema:4469 | 分配8封预算中的两封，不扩大范围 |
| M-mcp__gmail__create_label / 阻塞 | R | 建唯一R2标签，核对visibility两字段及ID | S-MCP（仅共享）；schema:4495 | 对象授权已齐备 |
| M-mcp__gmail__update_label / 阻塞 | P | 改R2标签名称/visibility，旧名消失新名ID不变 | S-MCP（仅共享）；schema:4531 | 前置create_label，不是新授权 |
| M-mcp__gmail__delete_label / 阻塞 | P | 删专用R2标签后list不再出现，邮件主体仍在 | S-MCP（仅共享）；schema:4571 | 前置专用label/邮件，别删系统/旧label |
| M-mcp__gmail__get_or_create_label / 阻塞 | R | 不存在时create，再同名返回同ID且不重复 | S-MCP（仅共享）；schema:4590 | 一个R2 label名，测试两个业务分支 |
| M-mcp__gmail__create_filter / 阻塞 | P | criteria限定R2 subject/query，add/remove label分开；get回读 | S-MCP（仅共享）；schema:4626 | 前置专用label；forward分支另有目的地址验证条件 |
| M-mcp__gmail__list_filters / 阻塞 | R | 列出本轮filter并核对ID，不展示普通filter细节 | S-MCP（仅共享）；schema:4715 | 现有授权；不因无readOnlyHint称业务写阻塞 |
| M-mcp__gmail__get_filter / 阻塞 | P | 按已登记R2 filterId回读criteria/action | S-MCP（仅共享）；schema:4726 | 前置create_filter |
| M-mcp__gmail__delete_filter / 阻塞 | P | 删除R2 filter后get not-found/list移除 | S-MCP（仅共享）；schema:4745 | 前置filter夹具，现有具体授权 |
| M-mcp__gmail__create_filter_from_template / 阻塞 | P | withSubject/containingText可限定R2；六模板分列离线材料 | S-MCP（仅共享）；schema:4764 | withAttachments/largeEmails无R2限制参数，不能在本轮范围直接在线扩大全邮箱 |
| M-mcp__gmail__download_attachment / 阻塞 | P | R2附件messageId+attachmentId存入本轮目录，核对bytes/hash | S-MCP（仅共享）；schema:4838 | attachment.txt已备，需前置发送并取得attachmentId |
| AN-idle / 功能未验证 | P | 默认idle循环、上身轨不写下身、双17骨发束采样 | G-MOTION；apps/avatar-runtime/motion_registry.json; apps/avatar-runtime/runtime.gd | 资产hash证据已有；runtime脚本可复用，本轮逐段视觉未验 |
| AN-pirouette / 功能未验证 | P | 交互打断idle、全身轨驱动、完成回idle | G-MOTION；apps/avatar-runtime/motion_registry.json; apps/avatar-runtime/runtime.gd | 已有轨迹断言源码；旋转不代表全程无穿模 |
| AN-listen / 功能未验证 | P | recording保持末帧→松开反向安全返回，取消/重复状态 | G-MOTION,G-LISTEN；apps/avatar-runtime/motion_registry.json; apps/avatar-runtime/runtime.gd | 真人录音阶段可观察；路径几何与听感分开 |
| AN-think / 功能未验证 | P | thinking进入一次，不阻塞回复，录音抢占、34发束交还 | G-THINK；apps/avatar-runtime/motion_registry.json; apps/avatar-runtime/runtime.gd | 已有专门integration断言源码，需绑定当前资产版本执行 |
| AN-farewell / 功能未验证 | O | 退出动作/自己语音join，重入不多退、旧request音频拒绝 | G-FAREWELL,O-FAREWELL；apps/avatar-runtime/motion_registry.json; apps/avatar-runtime/runtime.gd | 旧farewell_speech隔离已通过；普通动作菜单无farewell是设计 |
| AV-avatar.angry / 功能未验证 | P | angry预设精确权重、强度边界、说话时嘴部释放 | G-EMOTION；apps/avatar-runtime/runtime.gd; apps/avatar-runtime/emotion_presets.gd | 本地动画/表情对象已实现；可隔离采样morph/骨骼，逐项视觉仍待验，不能用注册名算通过 |
| AV-avatar.blink / 功能未验证 | P | 眨眼闭合再恢复原情绪，不覆盖表情名称 | G-EMOTION；apps/avatar-runtime/runtime.gd; apps/avatar-runtime/emotion_presets.gd | 本地动画/表情对象已实现；可隔离采样morph/骨骼，逐项视觉仍待验，不能用注册名算通过 |
| AV-avatar.expression / 功能未验证 | P | 指定morph覆盖组合表情，value夹限/duration到期恢复；未知name | G-EMOTION；apps/avatar-runtime/runtime.gd; apps/avatar-runtime/emotion_presets.gd | 本地动画/表情对象已实现；可隔离采样morph/骨骼，逐项视觉仍待验，不能用注册名算通过 |
| AV-avatar.greet / 功能未验证 | P | greet手势+笑眼组合时长，完成回idle | 无专门动作断言；apps/avatar-runtime/runtime.gd; apps/avatar-runtime/emotion_presets.gd | 本地动画/表情对象已实现；可隔离采样morph/骨骼，逐项视觉仍待验，不能用注册名算通过 |
| AV-avatar.mouth_a / 功能未验证 | P | あ权重0.9、定时释放、与speech嘴形互斥 | 无该口型专门断言；apps/avatar-runtime/runtime.gd; apps/avatar-runtime/emotion_presets.gd | 本地动画/表情对象已实现；可隔离采样morph/骨骼，逐项视觉仍待验，不能用注册名算通过 |
| AV-avatar.mouth_e / 功能未验证 | P | え权重0.9、定时释放、与speech嘴形互斥 | 无该口型专门断言；apps/avatar-runtime/runtime.gd; apps/avatar-runtime/emotion_presets.gd | 本地动画/表情对象已实现；可隔离采样morph/骨骼，逐项视觉仍待验，不能用注册名算通过 |
| AV-avatar.mouth_i / 功能未验证 | P | い权重0.9、定时释放、与speech嘴形互斥 | 无该口型专门断言；apps/avatar-runtime/runtime.gd; apps/avatar-runtime/emotion_presets.gd | 本地动画/表情对象已实现；可隔离采样morph/骨骼，逐项视觉仍待验，不能用注册名算通过 |
| AV-avatar.mouth_o / 功能未验证 | P | お权重0.9覆盖tears口部，定时释放 | G-EMOTION；apps/avatar-runtime/runtime.gd; apps/avatar-runtime/emotion_presets.gd | 本地动画/表情对象已实现；可隔离采样morph/骨骼，逐项视觉仍待验，不能用注册名算通过 |
| AV-avatar.mouth_u / 功能未验证 | P | う权重0.9、定时释放、与speech嘴形互斥 | 无该口型专门断言；apps/avatar-runtime/runtime.gd; apps/avatar-runtime/emotion_presets.gd | 本地动画/表情对象已实现；可隔离采样morph/骨骼，逐项视觉仍待验，不能用注册名算通过 |
| AV-avatar.nod / 功能未验证 | P | nod幅度/时长、打断及回idle | 无专门动作断言；apps/avatar-runtime/runtime.gd; apps/avatar-runtime/emotion_presets.gd | 本地动画/表情对象已实现；可隔离采样morph/骨骼，逐项视觉仍待验，不能用注册名算通过 |
| AV-avatar.reset / 功能未验证 | P | reset清表情与偏转、恢复idle；关闭中不重入 | G-EMOTION；apps/avatar-runtime/runtime.gd; apps/avatar-runtime/emotion_presets.gd | 本地动画/表情对象已实现；可隔离采样morph/骨骼，逐项视觉仍待验，不能用注册名算通过 |
| AV-avatar.smile / 功能未验证 | P | 笑い0.85替换angry；intensity夹限与到期 | G-EMOTION；apps/avatar-runtime/runtime.gd; apps/avatar-runtime/emotion_presets.gd | 本地动画/表情对象已实现；可隔离采样morph/骨骼，逐项视觉仍待验，不能用注册名算通过 |
| AV-avatar.surprised / 功能未验证 | P | surprised精确权重、强度边界及状态切换 | G-EMOTION；apps/avatar-runtime/runtime.gd; apps/avatar-runtime/emotion_presets.gd | 本地动画/表情对象已实现；可隔离采样morph/骨骼，逐项视觉仍待验，不能用注册名算通过 |
| AV-avatar.tears / 功能未验证 | P | tears精确权重、眨眼后保持、不同帧率到期 | G-EMOTION；apps/avatar-runtime/runtime.gd; apps/avatar-runtime/emotion_presets.gd | 本地动画/表情对象已实现；可隔离采样morph/骨骼，逐项视觉仍待验，不能用注册名算通过 |
| AV-avatar.turn_left / 功能未验证 | P | 默认30度及自定义degrees，退出当前motion回idle | G-TEXT仅输入保护；apps/avatar-runtime/runtime.gd; apps/avatar-runtime/emotion_presets.gd | 本地动画/表情对象已实现；可隔离采样morph/骨骼，逐项视觉仍待验，不能用注册名算通过 |
| AV-avatar.turn_right / 功能未验证 | P | 默认30度及自定义degrees，退出当前motion回idle | 无专门方向断言；apps/avatar-runtime/runtime.gd; apps/avatar-runtime/emotion_presets.gd | 本地动画/表情对象已实现；可隔离采样morph/骨骼，逐项视觉仍待验，不能用注册名算通过 |
| AV-avatar.wave / 功能未验证 | P | wave轨迹/持续2.35秒、打断及回idle | 无专门动作断言；apps/avatar-runtime/runtime.gd; apps/avatar-runtime/emotion_presets.gd | 本地动画/表情对象已实现；可隔离采样morph/骨骼，逐项视觉仍待验，不能用注册名算通过 |
| AV-avatar.wink / 功能未验证 | P | 右眼单眨+笑い，1.2秒后释放 | 无专门动作断言；apps/avatar-runtime/runtime.gd; apps/avatar-runtime/emotion_presets.gd | 本地动画/表情对象已实现；可隔离采样morph/骨骼，逐项视觉仍待验，不能用注册名算通过 |
| UI-delete / 功能未验证 | O | 当前/卡片删除、取消、单击确认绑定session ID | G-SESSION；apps/avatar-runtime/interaction_ui.gd; apps/avatar-runtime/runtime.gd | 旧Godot隔离通过 + O-SESSION后端实效；不据此删普通历史 |
| UI-search / 功能未验证 | P | 用两标题R2-AA/R2-BB过滤AA，断言仅AA卡片及无匹配空态 | G-SEARCH（弱断言）；apps/avatar-runtime/interaction_ui.gd; apps/avatar-runtime/runtime.gd | 既有count>=2不能证明BB已移除；加强夹具而非缺材料 |
| UI-voice-button / 功能未验证 | O | 按住/松开→STT仅回填→用户编辑→发送；取消/切页不旧回填 | O-VOICE（Core），UI静态interaction_ui.gd:1345；apps/avatar-runtime/interaction_ui.gd; apps/avatar-runtime/runtime.gd | 真人录音由主执行者进行；离线不代签音色/听感 |
| UI-drag / 功能未验证 | P | 短点开菜单/超过8px拖拽；边缘限制/重启位置保持 | G-CANVAS（源码可复用）；apps/avatar-runtime/interaction_ui.gd; apps/avatar-runtime/runtime.gd | 已有桌面canvas测试源码，不在362清单，不将源码存在算本次PASS |
| UI-scale / 功能未验证 | P | 滚轮缩放上下限，UI悬浮不透传；比较官模比例 | G-CANVAS（仅默认比例）；apps/avatar-runtime/interaction_ui.gd; apps/avatar-runtime/runtime.gd | 现有默认尺寸断言不验滚轮边界；可离线造InputEvent |
| UI-turn / 功能未验证 | P | 左右键/鼠标转动及R复位，聊天输入焦点时不转 | G-TEXT（输入焦点保护）；apps/avatar-runtime/interaction_ui.gd; apps/avatar-runtime/runtime.gd | 旧焦点守卫通过，只验A不误触；其他输入分支待测 |
| UI-portrait / 功能未验证 | P | F12有/无输入焦点；3x RGBA透明图、不改pose、重复不覆盖 | G-PORTRAIT（源码可复用）；apps/avatar-runtime/interaction_ui.gd; apps/avatar-runtime/runtime.gd | headless只验API；真实渲染需图形环境，当前未执行 |
| NI01 / 未启用或未实现 | N | 已装有限动作不保证任意衣发接触；不得推导全身通用无穿模 | docs/HANDOFF.md:6,65；docs/MOTION_PIPELINE.md；docs/MOTION_PIPELINE.md | 未实现的通用能力；单动作资产/轨迹测试不能替代 |
| NI02 / 未启用或未实现 | N | 正常Windows登录触发尚无正式入口；现有会话看护分开 | docs/HANDOFF.md:126；docs/HANDOFF.md | 所有者暂缓，非环境缺权限；不注册任务/启动项 |
| NI03 / 未启用或未实现 | N | pending事实可存不等于用户能审阅/遗忘；需明确scope删除合同 | docs/HANDOFF.md:30；UI无记忆审阅菜单；docs/HANDOFF.md | 缺产品入口/实现；不能用delete_session冒充forget_fact |
| NI04 / 未启用或未实现 | N | 任意桌面键鼠自主代理未实现；browser_click只是浏览器工具 | docs/HANDOFF.md:126,138；docs/HANDOFF.md | 未实现且缓行；不能用MCP浏览器作用域扩大成桌面控制 |
| NI05 / 未启用或未实现 | N | Spark adapter无注册执行路径 | docs/HANDOFF.md:126,139；docs/HANDOFF.md | 未实现；不是当前模型Key材料缺失 |
| NI06 / 未启用或未实现 | N | Tauri设置壳与现用Godot区分，不能将目录存在当启用 | apps/desktop；正式入口scripts/start-mvp.ps1；apps/desktop | 正式链未启用；不替换当前壳 |
| NI07 / 未启用或未实现 | N | 同机验收不证明任意硬件/离线跨机等效 | docs/DELIVERY_STATUS.md；docs/HANDOFF.md:6；docs/DELIVERY_STATUS.md | 需另机安装/音频/GPU验收资源与打包实现；不是本轮夹具文件不足 |
| IPC-on_event-startup-_start_mcp_servers / 功能未验证 | O | 启动成功/一个server失败/idle-watch异常应分别记录；tools/list不代表tools/call | O-MCP-START（仅命令解析）；services/agent-core/agent_core/main.py:1789 | 可stub start_from_env和start_idle_watch补回调测试；不实际启动MCP |
| IPC-on_event-shutdown-_stop_mcp_servers / 功能未验证 | P | stub两server stop，逐个调用且重复shutdown有界 | 无stop_all直接断言；services/agent-core/agent_core/main.py:1805 | 内存host fixture；没有账号/桌面依赖 |
| IPC-on_event-startup-start_wake_word_listener / 功能未验证 | O | manual分支停止已有listener并置None；sweep空会话 | O-MANUAL；services/agent-core/agent_core/main.py:1810 | manual已覆盖；已有listener.stop分支与wake模式失败需离线夹具，不需开麦 |
| IPC-post-/wake-test-wake_test / 功能未验证 | P | 空body/合法16k WAV/重采样/坏WAV，stub_spawn确认样本长度 | 无路由直接断言；services/agent-core/agent_core/main.py:1842 | 合成WAV+TestClient，禁止以此绕开真实manual录音验收 |
| IPC-get-/health/live-liveness / 功能未验证 | O | TTS与模型探测均禁调用，仍200且pid正确 | O-HEALTH；services/agent-core/agent_core/main.py:1867 | 362内已有具体断言；只支持liveness合同 |
| IPC-get-/health-health / 功能未验证 | O | TTS离线仍200且available=false；检查provider/tools/memory字段 | O-HEALTH；services/agent-core/agent_core/main.py:1880 | 已有TTS离线断言；路径字符串不能证明SQLite句柄身份 |
| IPC-websocket-/ws-websocket_endpoint / 功能未验证 | O | 连接/hello/聊天/回执各事件；断开后owner录音失效 | O-SESSION,O-SPEECH（分事件）；services/agent-core/agent_core/main.py:1920 | 已有若干事件链；非整个ws入口全状态通过 |
| WS-avatar.command / 功能未验证 | P | 注册/未知命令、非dict payload及role目的地；AV各动作另测 | 无对应WS验证；services/agent-core/agent_core/main.py:websocket_endpoint | 可替hub内存测试，命令转发成功不等于动画正确 |
| WS-avatar.interaction / 功能未验证 | P | clicked菜单转发/invalid；exiting+speechLocal true/false及exit-ID | O-FAREWELL仅语音交付；services/agent-core/agent_core/main.py:websocket_endpoint | 本地可造WS/hub；UI角色菜单与本地退出不能合并 |
| WS-chat.history.request / 功能未验证 | O | 空库-1/指定会话/坏ID；只返所选会话并失效旧录音 | O-HEALTH,O-SESSION-STORE；services/agent-core/agent_core/main.py:websocket_endpoint | 基本空库已有断言；跨会话/malformed组合可补内存 |
| WS-chat.message / 功能未验证 | O | 原文、effort/confirmation、4000/4001、空串、无效会话、新消息打断 | O-SESSION,O-SPEECH,S-GATE；services/agent-core/agent_core/main.py:websocket_endpoint | 已有正常链/打断；长度和坏ID缺直接断言，零模型fixture即可 |
| WS-client.hello / 功能未验证 | O | avatar/ui/unknown/空role，client.ready回显与角色定向 | O-SESSION（握手前置）；services/agent-core/agent_core/main.py:websocket_endpoint | 已有avatar ready前置；不是强鉴权，其他role未穷尽 |
| WS-ping / 功能未验证 | O | 无效/旧speech receipt之后ping仍响应pong | O-SPEECH（pong断言）；services/agent-core/agent_core/main.py:websocket_endpoint | 已有具体pong断言；可补独立ping未hello路径 |
| WS-session.delete / 功能未验证 | O | 删除合成会话后列表/历史清空，新会话切换；未知ID错误 | O-SESSION；services/agent-core/agent_core/main.py:websocket_endpoint | 已有隔离DB实效；当前UI真正点击仍独立 |
| WS-session.list.request / 功能未验证 | O | R2空会话隐藏/首条消息后可见/更新时间排序，WS序列化ID字段 | O-SESSION-STORE（底层）；services/agent-core/agent_core/main.py:websocket_endpoint | 底层列表已测，WS映射层仍可补stub |
| WS-session.new / 功能未验证 | O | 创建后switched/默认标题；不中断其他会话数据 | O-SESSION；services/agent-core/agent_core/main.py:websocket_endpoint | 已有新建链；录音/播放中创建组合另测 |
| WS-speech.failed / 功能未验证 | O | 仅avatar有效utterance+playback ID受理，加载失败只重合成对应片 | O-SPEECH；services/agent-core/agent_core/main.py:websocket_endpoint | 已有新playback ID+计数断言；真实Godot加载失败现场未注入 |
| WS-speech.finished / 功能未验证 | O | 正确/旧/未知/ui角色回执，完成与interrupted分开 | O-SPEECH；services/agent-core/agent_core/main.py:websocket_endpoint | 已有拒绝旧ID及不提前done断言；不能用听到了代替关联 |
| WS-voice.cancel / 功能未验证 | O | 录音/STT期间cancel，旧结果不回填；不生成chat/记忆 | O-VOICE（handler/state层）；services/agent-core/agent_core/main.py:websocket_endpoint | 已覆盖取消迟到；WS非owner cancel作用域需补孤立夹具 |
| WS-voice.start / 功能未验证 | O | 开始新capture，打断语音/取消wake capture；start驱动异常hint | O-VOICE,O-SPEECH；services/agent-core/agent_core/main.py:websocket_endpoint | 已有取消wake/停止TTS断言；麦克风真实性能不在离线层 |
| WS-voice.stop / 功能未验证 | O | owner+capture匹配才提交；乱序stop不建chat不resume wake | O-VOICE,O-MANUAL；services/agent-core/agent_core/main.py:websocket_endpoint | 已有stray stop与manual检查；不同owner及错误capture可补 |
| METHOD-mcp__browser__browser_tabs-list / 功能未验证 | R | 列出R2标签，核对index/title/url；不把有任何标签当匹配 | S-MCP（仅共享）；无该method专门业务断言；schema:857 | 本地R2 HTML及标签即可；材料已有 |
| METHOD-mcp__browser__browser_tabs-new / 功能未验证 | R | new指定loopback URL，核对新增数量及URL | S-MCP（仅共享）；无该method专门业务断言；schema:857 | 本地R2 HTML及标签即可；材料已有 |
| METHOD-mcp__browser__browser_tabs-close / 功能未验证 | R | 关闭指定R2 index，核对该标签移除而其他R2页保留 | S-MCP（仅共享）；无该method专门业务断言；schema:857 | 本地R2 HTML及标签即可；材料已有 |
| METHOD-mcp__browser__browser_tabs-select / 功能未验证 | R | 两个R2页间选择index，下一snapshot必须对应目标页 | S-MCP（仅共享）；无该method专门业务断言；schema:857 | 本地R2 HTML及标签即可；材料已有 |
| METHOD-mcp__github__issue_read-get_comments / 功能未验证 | P | 先加R2正文评论，再核对ID/作者/原文与分页 | S-MCP（仅共享）；无该method专门业务断言；schema:2008 | 同一R2仓可准备前置Issue/PR/review/thread；不是缺账号材料 |
| METHOD-mcp__github__issue_read-get_sub_issues / 功能未验证 | P | 父Issue含两子项，核对有序子Issue ID | S-MCP（仅共享）；无该method专门业务断言；schema:2008 | 同一R2仓可准备前置Issue/PR/review/thread；不是缺账号材料 |
| METHOD-mcp__github__issue_read-get_parent / 功能未验证 | P | 子Issue关联父；无父控制；替换父后读回新父 | S-MCP（仅共享）；无该method专门业务断言；schema:2008 | 同一R2仓可准备前置Issue/PR/review/thread；不是缺账号材料 |
| METHOD-mcp__github__issue_read-get_labels / 功能未验证 | P | 一个R2标签+无标签控制，核对label ID/name | S-MCP（仅共享）；无该method专门业务断言；schema:2008 | 同一R2仓可准备前置Issue/PR/review/thread；不是缺账号材料 |
| METHOD-mcp__github__issue_write-update / 阻塞 | P | 同Issue改title/body/state/label并回读；不由create成功代验 | S-MCP（仅共享）；无该method专门业务断言；schema:2166 | 同一R2仓可准备前置Issue/PR/review/thread；不是缺账号材料 |
| METHOD-mcp__github__pull_request_read-get / 功能未验证 | P | 核对R2 PR number/head/base/title/body | S-MCP（仅共享）；无该method专门业务断言；schema:2949 | 同一R2仓可准备前置Issue/PR/review/thread；不是缺账号材料 |
| METHOD-mcp__github__pull_request_read-get_diff / 功能未验证 | P | 断言R2新增/删除行的完整patch与文件路径 | S-MCP（仅共享）；无该method专门业务断言；schema:2949 | 同一R2仓可准备前置Issue/PR/review/thread；不是缺账号材料 |
| METHOD-mcp__github__pull_request_read-get_status / 功能未验证 | P | 无status合法结果与有status分开；有值需创建专用commit status | S-MCP（仅共享）；无该method专门业务断言；schema:2949 | 同一R2仓可准备前置Issue/PR/review/thread；不是缺账号材料 |
| METHOD-mcp__github__pull_request_read-get_files / 功能未验证 | P | 两变更文件perPage=1翻页，逐path/additions核对 | S-MCP（仅共享）；无该method专门业务断言；schema:2949 | 同一R2仓可准备前置Issue/PR/review/thread；不是缺账号材料 |
| METHOD-mcp__github__pull_request_read-get_commits / 功能未验证 | P | 两提交翻页，逐SHA/消息核对 | S-MCP（仅共享）；无该method专门业务断言；schema:2949 | 同一R2仓可准备前置Issue/PR/review/thread；不是缺账号材料 |
| METHOD-mcp__github__pull_request_read-get_review_comments / 功能未验证 | P | 先有review thread，核对thread ID、line/original_line和cursor | S-MCP（仅共享）；无该method专门业务断言；schema:2949 | 同一R2仓可准备前置Issue/PR/review/thread；不是缺账号材料 |
| METHOD-mcp__github__pull_request_read-get_reviews / 功能未验证 | P | pending/提交COMMENT之后核对review state和body | S-MCP（仅共享）；无该method专门业务断言；schema:2949 | 同一R2仓可准备前置Issue/PR/review/thread；不是缺账号材料 |
| METHOD-mcp__github__pull_request_read-get_comments / 功能未验证 | P | 普通PR issue comment与review comment区分，按正文/ID验 | S-MCP（仅共享）；无该method专门业务断言；schema:2949 | 同一R2仓可准备前置Issue/PR/review/thread；不是缺账号材料 |
| METHOD-mcp__github__pull_request_read-get_check_runs / 功能未验证 | P | 零check合法空态；非空正向要专用check run或已允许CI | S-MCP（仅共享）；无该method专门业务断言；schema:2949 | 同一R2仓可准备前置Issue/PR/review/thread；不是缺账号材料 |
| METHOD-mcp__github__pull_request_review_write-APPROVE / 阻塞 | X | method=create/submit_pending+APPROVE独立；同作者失败与非作者成功分开 | S-MCP（仅共享）；无该method专门业务断言；schema:3027 | 当前登记只有owner账号；非作者审阅身份/平台资格需独立核实，不能伪造通过 |
| METHOD-mcp__github__pull_request_review_write-REQUEST_CHANGES / 阻塞 | X | method=create/submit_pending+REQUEST_CHANGES独立；必须核验审阅身份资格 | S-MCP（仅共享）；无该method专门业务断言；schema:3027 | 当前登记只有owner账号；非作者审阅身份/平台资格需独立核实，不能伪造通过 |
| METHOD-mcp__github__pull_request_review_write-COMMENT / 阻塞 | P | create直接提交与submit_pending两条，回读state=COMMENTED/body | S-MCP（仅共享）；无该method专门业务断言；schema:3027 | 同一R2仓可准备前置Issue/PR/review/thread；不是缺账号材料 |
| METHOD-mcp__github__pull_request_review_write-create / 阻塞 | P | 无event应pending；有COMMENT应提交；两者不能合并计数 | S-MCP（仅共享）；无该method专门业务断言；schema:3027 | 同一R2仓可准备前置Issue/PR/review/thread；不是缺账号材料 |
| METHOD-mcp__github__pull_request_review_write-submit_pending / 阻塞 | P | 已有pending提交COMMENT；没有pending错误控制 | S-MCP（仅共享）；无该method专门业务断言；schema:3027 | 同一R2仓可准备前置Issue/PR/review/thread；不是缺账号材料 |
| METHOD-mcp__github__pull_request_review_write-delete_pending / 阻塞 | P | 只删专用pending review，再读回不存在；已提交不可同等视作删除 | S-MCP（仅共享）；无该method专门业务断言；schema:3027 | 同一R2仓可准备前置Issue/PR/review/thread；不是缺账号材料 |
| METHOD-mcp__github__pull_request_review_write-resolve_thread / 阻塞 | P | 使用get_review_comments返回threadId，核对isResolved=true | S-MCP（仅共享）；无该method专门业务断言；schema:3027 | 同一R2仓可准备前置Issue/PR/review/thread；不是缺账号材料 |
| METHOD-mcp__github__pull_request_review_write-unresolve_thread / 阻塞 | P | 先resolve同thread，再核对isResolved=false | S-MCP（仅共享）；无该method专门业务断言；schema:3027 | 同一R2仓可准备前置Issue/PR/review/thread；不是缺账号材料 |

## 断言证据目录

### S-GATE

本轮362通过记录；本审查只读断言。

`services/agent-core/tests/test_agent_gate.py:109` — `GateIntegrationTests.test_ask_decision_parks_call_without_execution`

`services/agent-core/tests/test_agent_gate.py:75` — `GateIntegrationTests.test_denied_tool_never_reaches_executor_and_reports_back`

`services/agent-core/tests/test_agent_gate.py:166` — `ActionReceiptScopeTests.test_same_tool_new_parameters_need_new_confirmation`

有效断言：ASK不执行、DENY不触executor、同工具新参数须新确认。

边界：仅共享权限合同，不覆盖任意MCP参数或真实授权。

### S-MCP

本轮362通过记录；本审查只读断言。

`services/agent-core/tests/test_harness_v1_review.py:279` — `IndependentReviewTests.test_p1_mcp_same_id_reverse_request_is_not_a_success_receipt`

`services/agent-core/tests/test_harness_v1_review.py:294` — `IndependentReviewTests.test_p1_mcp_missing_result_cannot_be_accepted_as_success`

`services/agent-core/tests/test_harness_v1_review.py:302` — `IndependentReviewTests.test_control_valid_mcp_success_receipt_is_preserved`

有效断言：内存JSON-RPC：反向同ID请求/缺result不变成功；有效result保留succeeded、ok及FIXTURE_ACCEPTED交付。

边界：server名fixture；不运行94工具任何真实业务操作。各M/METHOD行没有专属业务PASS。

### O-VISION

本轮362通过记录；本审查只读断言。

`services/agent-core/tests/test_vision_request.py:21` — `VisionRequestTest.test_anthropic_branch_builds_messages_shape`

`services/agent-core/tests/test_vision_request.py:41` — `VisionTextTest.test_anthropic_payload_skips_thinking_blocks`

`services/agent-core/tests/test_vision_request.py:11` — `VisionRequestTest.test_openai_branch_keeps_chat_completions_shape`

`services/agent-core/tests/test_tools.py:195` — `PerToolTimeout.test_look_at_screen_registered_with_extended_timeout`

有效断言：Anthropic路径/messages、image/media_type及协议值；thinking被滤；OpenAI image_url形状；视觉timeout>=60秒。

边界：未拍真实屏幕、未验证服务视觉准确度；合成sk-test是测试字面量。

### O-LIST

本轮362通过记录；本审查只读断言。

`services/agent-core/tests/test_tools.py:108` — `ListDirTests.test_lists_entries_dirs_first`

`services/agent-core/tests/test_tools.py:120` — `ListDirTests.test_missing_directory`

有效断言：临时目录含sub和a.txt，ok且sub排序0；不存在目录ok=false。

边界：只支持本地函数；天依选工具与最终答复未覆盖。

### O-DEGRADED

本轮362通过记录；本审查只读断言。

`services/agent-core/tests/test_tools.py:127` — `DegradedToolTests.test_screenshot_without_mss`

`services/agent-core/tests/test_tools.py:139` — `DegradedToolTests.test_clipboard_without_pyperclip`

`services/agent-core/tests/test_tools.py:151` — `DegradedToolTests.test_active_window_off_windows`

有效断言：禁mss/pyperclip或模拟posix时ok=false。

边界：只有退化反例，不能当三个隐私工具成功覆盖。

### O-PAGES

本轮362通过记录；本审查只读断言。

`services/agent-core/tests/test_harness_v1_integration.py:120` — `ContextTests.test_pages_preserve_tail_and_reject_other_session`

`services/agent-core/tests/test_harness_v1_integration.py:113` — `ContextTests.test_resource_text_is_not_lost`

有效断言：长结果truncated=true，尾页含TAIL-73921；另store/负offset拒绝；内嵌resource文本保留。

边界：内嵌resource结果解析不等于MCP resources/read实现。

### O-GREET

本轮362通过记录；本审查只读断言。

`services/agent-core/tests/test_speech_delivery.py:117` — `SceneSuccessTests.test_failed_greeting_does_not_consume_cooldown`

`services/agent-core/tests/test_speech_delivery.py:126` — `SceneSuccessTests.test_greeting_marks_after_playback_idle_not_remarked_after_playback`

`services/agent-core/tests/test_speech_delivery.py:139` — `SceneSuccessTests.test_concurrent_greetings_not_duplicate`

有效断言：失败不mark，成功后mark一次；并发greeting+idle总speak一次。

边界：_speak_reply为AsyncMock，非真人听感。

### O-MCP-START

本轮362通过记录；本审查只读断言。

`services/agent-core/tests/test_mcp_command_quotes.py:19` — `McpQuotedCommandTests.test_quoted_portable_executable_and_script`

`services/agent-core/tests/test_mcp_command_quotes.py:23` — `McpQuotedCommandTests.test_empty_argument_preserved`

`services/agent-core/tests/test_mcp_command_quotes.py:32` — `McpQuotedCommandTests.test_backslashes_are_not_posix_escapes`

有效断言：start_from_env读取含空格/Unicode/空参数的命令，检查拆分结果。

边界：McpServer.start被替换为仅设置started；不证明initialize/stop_all或startup回调异常路径。

### O-HEALTH

本轮362通过记录；本审查只读断言。

`services/agent-core/tests/test_liveness.py:12` — `LivenessTests.test_liveness_does_not_probe_speech_or_llm`

`services/agent-core/tests/test_liveness.py:27` — `LivenessTests.test_detailed_health_remains_compatible_when_speech_offline`

`services/agent-core/tests/test_liveness.py:36` — `LivenessTests.test_fresh_start_history_has_integer_empty_session_id`

有效断言：live为200/status/pid正确且speech/LLM未调用；health离线available=false；空history conversationId=-1/messages=[]。

边界：TestClient与patched依赖；健康200不证明工具、模型、DB物理身份正确。

### O-SESSION

本轮362通过记录；本审查只读断言。

`services/agent-core/tests/test_main_ws.py:82` — `SessionLifecycleTests.test_first_chat_titles_session_then_delete_full_chain`

`services/agent-core/tests/test_main_ws.py:120` — `SessionLifecycleTests.test_title_falls_back_to_user_text_when_model_omits`

`services/agent-core/tests/test_main_ws.py:131` — `SessionLifecycleTests.test_delete_unknown_session_reports_error`

有效断言：WS新建、chat response/sessionId、仅首轮命名、实际临时DB删行及新会话；无模型title回退；未知删除core.error。

边界：ScriptedProvider+临时DB；不覆盖真实LLM/4001长度、所有角色、输入畸形。

### O-SESSION-STORE

本轮362通过记录；本审查只读断言。

`services/agent-core/tests/test_session_visibility.py:19` — `SessionVisibilityTests.test_empty_session_hidden_from_list`

`services/agent-core/tests/test_session_visibility.py:24` — `SessionVisibilityTests.test_first_message_makes_session_visible`

`services/agent-core/tests/test_session_visibility.py:30` — `SessionVisibilityTests.test_sweep_removes_empty_keeps_content`

`services/agent-core/tests/test_session_visibility.py:40` — `SessionVisibilityTests.test_ordering_by_activity`

有效断言：空session不列出、第一条消息可见、sweep保留有内容、按活动排序。

边界：底层storage层；WS序列化映射及Godot显示另验。

### O-VOICE

本轮362通过记录；本审查只读断言。

`services/agent-core/tests/test_harness_v1_integration.py:159` — `VoiceInputTests.test_generation_old_result_cannot_fill_after_cancel_or_new`

`services/agent-core/tests/test_harness_v1_integration.py:166` — `VoiceInputTests.test_empty_stt_only_hint_no_brain_or_history`

`services/agent-core/tests/test_harness_v1_integration.py:177` — `VoiceInputTests.test_cancel_during_stt_discards_late_output`

`services/agent-core/tests/test_channel_exclusivity.py:255` — `VoiceStartCancelWiringTests.test_voice_start_calls_cancel_utterance_capture`

有效断言：旧generation无效，空STT只hint、不调用chat/add_message，取消中STT无transcript，voice.start调用取消wake捕获。

边界：不接麦克风；CaptureState/handler/部分WS层分开，不能代签真人录音。

### O-MANUAL

本轮362通过记录；本审查只读断言。

`services/agent-core/tests/test_harness_v1_integration.py:187` — `VoiceInputTests.test_manual_mode_never_opens_background_listener`

`services/agent-core/tests/test_voice_consistency.py:163` — `WakeReArmTests.test_manual_mode_keeps_background_wake_stopped_after_transcript`

`services/agent-core/tests/test_voice_consistency.py:194` — `WakeReArmTests.test_stray_stop_never_rearms_listener_or_creates_chat`

有效断言：manual不构造WakeWordListener、不调用chat；转写后resume_count=0且paused；乱序stop无transcript/chat。

边界：证明禁用合同，不授权启用背景唤醒。

### O-SPEECH

本轮362通过记录；本审查只读断言。

`services/agent-core/tests/test_speech_ws.py:130` — `SpeechWSTests.test_voice_start_interrupts_speech`

`services/agent-core/tests/test_speech_ws.py:168` — `SpeechWSTests.test_speech_finished_unknown_id_is_ignored`

`services/agent-core/tests/test_speech_ws.py:176` — `SpeechWSTests.test_stale_or_ui_receipt_cannot_complete_avatar_playback`

`services/agent-core/tests/test_speech_ws.py:196` — `SpeechWSTests.test_load_failure_retries_with_new_playback_id`

`services/agent-core/tests/test_speech_ws.py:149` — `SpeechWSTests.test_new_chat_message_interrupts_current_playback`

有效断言：语音开始/新消息interrupt；旧/unknown/ui receipt不done且能pong；load failure重试同utterance新playback、synth_count=2。

边界：stub声频+WS，非当前Godot/真实TTS实物播放。

### O-FAREWELL

本轮362通过记录；本审查只读断言。

`services/agent-core/tests/test_farewell_delivery.py:41` — `FarewellDeliveryTests.test_cached_audio_echoes_request_and_single_part_contract`

`services/agent-core/tests/test_farewell_delivery.py:33` — `FarewellDeliveryTests.test_disabled_voice_settles_only_matching_exit`

`services/agent-core/tests/test_farewell_delivery.py:56` — `FarewellDeliveryTests.test_synthesis_failure_explicitly_settles`

有效断言：cache交付request及单片合同；禁用voice仅settle匹配exit；合成失败显式settle。

边界：不涵盖所有avatar.interaction角色/字段组合；真实退出动画另验。

### G-SESSION

历史godot-guards.json中通过。

`apps/avatar-runtime/verify_session_ui.gd:20`

有效断言：会话list及title更新、单击删除弹框、cancel、card ID=8、确认路径断线报错、session.deleted移除/置-1。

边界：没有真实后端删除；后端由O-SESSION另证。

### G-SEARCH

历史运行通过但搜索断言不足。

`apps/avatar-runtime/verify_session_ui.gd:113`

有效断言：打开/日期组至少2、调用过滤后child_count>=2、关闭。

边界：未断言不匹配标题被剔除：未过滤且保留两卡也可满足>=2；应逐卡ID比对及无结果负例。

### G-TEXT

历史godot-guards.json中通过。

`apps/avatar-runtime/verify_text_input.gd:32`

有效断言：输入聚焦时模拟A键，avatar yaw未改变。

边界：不覆盖所有快捷键或真实中文输入；OS exact-input是另模式。

### G-CANVAS

仅审源码，未在本轮362或godot-guards执行。

`apps/avatar-runtime/verify_desktop_canvas.gd:23`

有效断言：默认desktop、14点交互轮廓、1920×2320→960×1160、移动二维合成120×80、官模hash。

边界：不能证明实际拖拽阈值/保存位置/滚轮极限。

### G-PORTRAIT

仅审源码，未在本轮执行。

`apps/avatar-runtime/verify_hd_capture.gd:40`

有效断言：焦点阻止F12，无焦点调用；有渲染模式还验3x RGBA、透明、pose不变、忙碌拒绝。

边界：headless在61行提前成功，仅接口；渲染和导出验证不可混算。

### G-EMOTION

仅审源码，未在本轮执行。

`apps/avatar-runtime/verify_emotion_presets.gd:14`

有效断言：surprised/angry/tears精确morph、切换/到期/invalid强度、说话嘴部释放、blink、smile/reset/expression/mouth_o覆盖。

边界：其他四口型、wave/nod/greet/wink和所有视觉观感无该测试专属断言。

### G-MOTION

仅审源码，未在本轮执行。

`apps/avatar-runtime/verify_motion_runtime.gd:31`

有效断言：idle/pirouette/listen存在、17骨双辫、idle上下身隔离/循环、pirouette中断、listen保持/反向/回idle。

边界：源码预期不等于运行PASS；asset hash不证明runtime、通用无穿模。

### G-LISTEN

仅审源码，未在本轮执行。

`apps/avatar-runtime/mocap/verify_listen_path.gd:16`

有效断言：倾听进入/保持/返回路径采样及接触安全检查。

边界：仅具体动作与阈值，不泛化其他动作/身体比例。

### G-THINK

仅审源码，未在本轮执行。

`apps/avatar-runtime/mocap/thinking/verify_integration.gd:58`

有效断言：34发束交还idle、thinking仅一次、同状态不重启、reply不等待动作、录音抢占。

边界：需当前限定资产；源码存在不算本轮PASS。

### G-FAREWELL

历史godot-guards.json中通过。

`apps/avatar-runtime/verify_farewell_speech.gd:46`

有效断言：拒绝旧exit、不截断动画/音频、join只退一次、乱序/重复/坏count拒绝、官模与动作hash。

边界：历史隔离，不是本轮逐段视觉；verify_farewell.gd另含无跳变/4.1秒退出断言。

## 需要新增的描述型分支与组合

原 28 个顶层 method/action/event enum 值均已登记，但其中 2 个已有实证不在本次184行内；本次26行已逐一列出。**参数值登记不是组合分支覆盖。** 扫描范围包括工具描述、properties、嵌套/anyOf enum，而非仅字段名正则。

| 建议独立场景 | 合同位置 | 最小夹具与判据 | 条件区分 |
|---|---|---|---|
| METHOD-sub_issue_write-add | schema:3692，method description无enum | 父P1/子C1，add后get_parent=P1 | 同R2仓Issue夹具可准备 |
| METHOD-sub_issue_write-remove | 同上 | 从P1移除C1，再查父/子列表 | 不是add成功的附带通过 |
| METHOD-sub_issue_write-reprioritize | 同上 | P1有C1/C2，before_id与after_id分别调整并回读顺序 | 两定位参数互斥/缺少参数负例也需单列 |
| sub_issue add × replace_parent=false/true | 同上 | C1原属P1，向P2加；不替换错误/允许替换后的唯一父 | 这是已登记描述中的语义变化，不是全新账号能力 |
| review create × event省略/COMMENT | schema:3027 | 前者pending，后者直接提交；分别读回状态 | 先有R2 PR即可；不能把create总项算两条都过 |
| review submit_pending × 有/无pending；delete_pending × pending/已提交 | 同上 | 保存review ID、state变化和错误原文 | 可准备；不能擅删别人review |
| review resolve/unresolve × threadId | 同上 | 从get_review_comments拿实际thread ID，再分别读回isResolved | 缺thread是前置夹具，非外部能力不足 |
| review APPROVE/REQUEST_CHANGES × 作者身份 | 同上 | 同作者受限结果与合格审阅者成功分列 | 不能由COMMENT成功推导；需要明确非作者身份/平台资格 |
| add_comment_to_pending_review subjectType FILE/LINE × side/startSide | schema:1003 | 单行/多行、左右diff，核对实际thread坐标 | pending review和diff是准备工作 |
| add_issue_comment / reply：body、reaction、二者 | schema:1072 / 1140 | 一次正文不覆盖reaction；核对reaction目标comment/issue | 8种reaction enum可离线合同遍历，真实至少代表性独立路径 |
| create_or_update_file create/update/旧SHA；merge merge/squash/rebase × expectedHeadSha | schema:1311 / 2873 | 每个合并模式独立R2 PR；成功后目标SHA与树一致，过期SHA无变化 | 不接触生产仓/正式main；同R2仓准备 |
| issue_write state/state_reason/duplicate_of、type=null、parent和issue_fields | schema:2166 | 开关Issue、duplicate指向目标、type移除；真实未支持字段不得捏造 | 普通Issue状态可准备；字段/type非空依仓/组织能力 |
| browser handle_dialog accept/dismiss/prompt；tabs四操作 | schema:94 / 857 | 对话框结果、tab数量/index/URL独立确认 | 仅R2 loopback页 |
| browser emulate_media 省略/null/有效值 | schema:122 | 省略保持、null清override、light/dark等改变matchMedia | 不用“调用不报错”替代页面状态 |
| browser fill_form嵌套type五种；type.submit/slowly | schema:348 / 435 | textbox/checkbox/radio/combobox/slider值及提交次数 | 控件可补现有HTML，无外部账号 |
| browser drop paths/data；upload paths省略；find text/regex；wait time/text/textGone | 各原schema行见上表 | 文件/MIME/取消/匹配/超时，单项不互代 | 本地夹具准备 |
| browser screenshot format×scale×fullPage/target；network_request四part | schema:614 / 549 | 文件编码/尺寸、目标范围、四种头/体输出绑定同index | 都是已有tool内真实分支，原METHOD生成器忽略 |
| Gmail get_or_create存在/不存在；modify add/remove/legacy labelIds | schema:4590 / 4361 | 同名返回同ID、无重复；各label参数读回实际变化 | 专用对象授权已齐 |
| Gmail filter六模板、create_filter action对象 | schema:4764 / 4626 | withSubject/containingText以R2唯一标记限定；逐template离线断言生成criteria/action | withAttachments/largeEmails无R2 query字段；不能在线扩大为全邮箱作用域；forward另需已验证目的地址 |
| Gmail draft/send MIME、reply threadId/inReplyTo、attachment | schema:4247 / 4173 | plain/html/multipart、同线程回复与附件bytes分别核对 | 最多8封，草稿不计已发送；所有收件人仍自有邮箱 |
| Tavily search_depth、extract/crawl format/depth、research model | 各schema行见上表 | 输出来源/页面正文/URL集合分清，mini/pro/auto不能互代 | 云端不能访问loopback；公开页面选择是准备，服务能力要实调 |

没有将全部参数笛卡尔积设为验收要求。上表优先挑改变副作用、状态转换、结果结构或作用域的组合；分页 cursor/page、缺值/空集/404/403/超时则沿相同模式补负控制。

## UI / WS / 本地入口漏项

| 新增登记建议 | 代码证据 | 所需场景 |
|---|---|---|
| UI-hud / F1 | runtime.gd:949–950 | toggle前后hud_visible及聊天输入焦点保护；当前UI手写清单未登记 |
| 本地avatar.pirouette / avatar.listen / avatar.think入口 | runtime.gd:931–934、1007–1013；interaction_ui菜单；thinking自动入口 | AN仅登记资产，AV从Core AVATAR_EVENTS生成，因此漏本地事件入口；这三个不能冒充Core允许转发的命令 |
| UI单击/拖动阈值与click-through | runtime.gd:847–900、verify_desktop_canvas.gd:26 | 7px仍点击、8px开始拖、UI上方不穿透、边缘clamp；默认canvas尺寸测试不替代 |
| UI输入焦点/断线发送/重连回载 | runtime.gd:912–915、1052–1058；_handle_core_event:727 | A/F12快捷键被输入框拦截；断线不假装已发送；client.ready后的list/history回载 |
| WS avatar.interaction 的 clicked / exiting / speechLocal | main.py:1939–1960 | 菜单只发ui角色；avatar本地语音退出与服务器farewell路径分开，非法payload和exit-ID回退 |
| WS voice start/stop/cancel owner/capture/generation/断开 | main.py:1962–2014、2128–2131 | 不同owner停止/旧capture拒绝、STT迟到、断开持有者、非owner cancel影响；单一voice.start事件不穷尽 |
| WS chat.message 的effort/confirmation/长度/会话ID | main.py:2107–2125 | 4000/4001、空串、无效session、明确票据revision/参数绑定；不能只依正常聊天链 |
| Core→Godot输出协议 | runtime.gd:717–787；main.py:812、1085、1204、1286、1634等 | 单列agent.state/tool、permission.pending、chat.response、session.*、voice.state/transcript/hint、avatar.speak/stop/farewell.cache/status、core.error/client.ready；检查消费与ID作用域 |
| 输出的未消费/角色专属分支 | main.py:1773的chat.user_message、1958的ui.menu.toggle；runtime当前match未接这两类 | 前者在禁用wake路径，后者发ui角色，不能直接断言当前Godot已呈现；若要启用旧路径，需找实际接收UI并分别验收 |
| permission.decision存储事件≠WS事件 | main.py:1330与runtime匹配表 | 当前是memory.add_event；没有广播就不能声称“Godot缺handler导致网络丢包”，应准确标UI呈现合同是否实现 |
| open_app计划入口 | docs/HANDOFF.md:126 | 现有NI列表漏此明确未做蓝图项；不能用run_command或browser导航冒充原生open_app实现 |

原 surface-inventory 只抽 Core 输入事件和注册动作，不含完整输出方向、异常/断线分支或Godot本地输入组合。应补分层索引，不把“184个handler名字”当184项可用功能或用户入口验收。

## 最小夹具顺序：准备工作与真外部条件分开

1. **纯离线包。** 补list_dir/命令白名单与超时subprocess替身、WS非法消息/owner-generation矩阵、read_tool_result负offset/跨会话及最后哨兵；浏览器schema所有嵌套enum与null不应让观察器丢trace。不要启动Core/MCP/TTS。本实例仅给出方案，未新增测试脚本。
2. **本地页面包。** 现有fixture.html补仅缺的多选/slider、A→B导航、延迟文字、fetch回显和鼠标计数器，即可串行覆盖25个browser工具。网络头/体只用合成值，不展示其他页面请求。其结果必须逐tool绑定request ID、参数摘要、页面前后状态，不用一次导航代表其余24项。
3. **GitHub图结构包。** 同一已授权私有仓准备两分支/两提交/两文件、两个父Issue+两个子Issue、专用label、一个带两文件diff的PR、pending review/line comment/thread；merge方法使用分开的可弃PR。tag/release若补充，应登记明确R2对象。组织/team、非作者review、Copilot和fork目的地是额外条件，普通同仓文件/Issue操作不应被这些条件连带阻塞。
4. **Gmail8封内包。** 第1封既有附件邮件保留为读取/下载正控制；第2封回复第1封，第3封转发给自己，第4封HTML，第5–6封用于单/批label与垃圾箱恢复，第6封在前述检查完成后可作单永久删除，第7–8封作批永久删除。草稿/label/filter不需额外发信。所有ID在动作前登记；每步独立回读，不靠返回“success”替代产物。超范围过滤器模板只做离线生成检查，不能以权限准备名义扩大到普通邮件。
5. **Drive包。** 已知文件搜索→独立resources/read可证明服务和OAuth；天依仍只暴露search。正文桥接待实现属于功能缺口，不能继续让用户重做OAuth来解决它。
6. **在线结果空集的判据。** search无命中、team空列表、无CI/status、无release应先判“该查询/环境的合法空结果”。正向非空场景需要适当对象；不要把空结果算正向覆盖，也不要将其误判成所有该服务权限失败。

## 新独立连接器诊断脚本只读审查

只读检查 `round02_connector_reads.py`，未运行。固定7个外部调用是Gmail四个search/read以及Drive两个search、一个已登记URI的resources/read；硬编码邮件ID与最新TEST_OBJECTS.md一致。脚本没有调用send/modify/delete/create，private raw输出也没有自动上传。启动的是独立MCP子进程，不是天依前台链；`external_mutations: []`只陈述远端业务调用无写操作，不能否认本地OAuth刷新/启动日志等连接器固有副作用。

原版的两项MEDIUM已反馈：适配器异常会丢原始raw，后一个server启动失败会丢前面的rows。最新复核SHA256为5c935dd1e73ca7810a21246fc9bfaef18587a2988a35ed93a1ea518738425061：第80–82行先保存raw，第92–99行分别记录adaptation/startup错误，已解除对应异常路径的证据抹除。重放临时替换server._roundtrip后调用server.call，实际不再发送第二次远程请求；其结果可称“同raw的部署适配器归一化”，不能称第二次真实工具调用或再次服务成功。JSON-RPC id因重放递增不会被真实重用；外部回执仍绑定原request。

清理仅针对所创建MCP根的后代，并检查PID+create_time；没有按进程名称广泛终止。第108–126行已补根wait和children wait_procs、terminate异常记录；第133–136行已分列调用数和三类错误，cleanup不再算调用。剩余边界：children枚举异常在106–107行忽略，空remaining只能说明已识别的后代；未知/缺配置server也不等于查询空结果。第55–75行新增启动stdout有限前缀观察，仅私有保存。主执行报告首轮Drive3项成功、Gmail initialize JSONDecodeError；之后天依前台独立完成Gmail读取见下方72项。**本实例没有运行连接器，不代签清理或账号验收**，完整复核见ADVERSARIAL_REVIEW.md增补。

## 原 72 个“有实证”逐项复核（2026-10-08 追加）

本节保留上文 184 项及其 O/R/P/X/N 分类，追加原桶“有实证（按层次，非全部通过）”的全部 **72 个唯一 ID**。原矩阵是“有证据”，本来就包含失败；不可更名为“72通过”。当前两个集合正好覆盖原256 ID，但描述型method、组合及UI/WS漏项仍超出原清单，不能因256已逐行审阅就宣布能力穷尽。

**复用依据已独立核对：** round-02/evidence/deployment-entry.json与上一轮evidence/runtime-final.json各54键一致，用后者deployed_sha256对前者sha256比较，54项全相同；这是安装观察器前的部署磁盘一致性，不包含全部依赖、数据库或内存monkeypatch。round-02/evidence/offline-suite.json记录362个独立test ID、ok=true、failures=[]、skipped=[]。本实例不重复执行测试；只读具体断言，本节新增映射50个精确测试ID，全部确实出现在该362列表。上文48个映射也保留。PowerShell、Godot和诊断脚本不伪装为这362的一部分。

层次缩写可叠加：**L**=上一轮当前窗口/业务回执；**R2**=本轮导出或已明确归属的主执行现场记录；**O**=已有离线断言；**S**=静态代码/磁盘清单；**H**=历史证据/离线重判；**F**=保留失败或反例。它们不是互斥得分，不据此计算总通过率。newEvidence文件名均相对本轮evidence目录；原证据相对上一轮evidence目录。每条的剩余工作只补缺口，不重跑已经确认且代码未变的控制组。

| ID / 功能 | 实际证据层与可支持结论 | 可复用断言及证据 | 具体缺口 / 不能外推 |
|---|---|---|---|
| AD01 / DS主脑 | L+R2+F：旧DS文件读取能给200/5，但确认后空动作虚报；R2 Gmail真实读取并答75，语音另失败。 | E-PROVIDER、E-HTTP；原证据 desktop-03.json; desktop-27.json ；R2 gmail-tts-live-trace.json | 同任务/同材料的DS与GLM对照仍须单列；成功短答不覆盖原生提案、长结果和异常交付。 |
| AD02 / GLM主脑 | L+O：旧GLM正式入口角色问答和文件写入样例可复用，非DS劣于GLM的总体排名。 | E-PROVIDER；原证据 desktop-37.json; desktop-41.json; runtime-glm-confirmed.json  | 本轮GLM未做同条件新任务；配置身份、档位和材料一致再比较。 |
| AD03 / 模型配置热重载 | O：429换key重试与换host不发送新key有精确离线断言；未破坏现场凭据。 | E-RELOAD；原证据 offline-suite.json  | 真实凭据失效不是必要复测；保留工具轮热重载/配置缺项已有测试层，不称现场全边界通过。 |
| AD04 / 传输恢复/截止时间 | O：3次上限、deadline后迟回丢弃、工具后网络重试不重复执行均有断言。 | E-HTTP；原证据 offline-suite.json  | 既有mock/loopback的通过可复用，不包含每个远端供应商实时故障。 |
| AD05 / 工具协议降级 | O：unsupported退纯文本，步数耗尽保留工具记录的离线合同可复用。 | E-FALLBACK；原证据 offline-suite.json  | 具体400/422错误体解析及执行后降级须按provider断言分别引用，不能以一次UnsupportedProvider覆盖全部API。 |
| EF01 / 碎碎念低投入 | L+O：desktop-30的chill含get_time与recall_memory；3轮/6次上限的具体断言可复用。 | E-EFFORT、E-CONTINUE；原证据 desktop-30.json  | test_every_level_stays_a_full_agent仅测正预算/label，不测工具集和权限等价。 |
| EF02 / 帮帮忙中投入 | L+O+F：standard档事件存在；desktop-31/32双文件只有口头待办且actions空，不能称双待办通过。 | E-EFFORT、E-TICKET；原证据 desktop-31.json; desktop-32.json  | 需要当前模型真实提出两动作；离线两文件确认成功仅证明宿主路径。 |
| EF03 / 大展身手高投入 | L+R2+O：deep档18调用/9轮配置与真实发送、R2读取已观察；不是用满18次后的成功证明。 | E-EFFORT、E-TICKET；原证据 desktop-25.json ；R2 gmail-tts-live-trace.json | 同权限静态证据与当前模型达预算边界分别说明。 |
| PE01 / 共享角色与运行合同 | L+O：双模型旧安慰/歌曲样例及assistant历史合同可复用；非角色所有问法通过。 | E-HARNESS；原证据 desktop-36.json; desktop-37.json  | 用无真实隐私的多轮诱导/能力越界负例区分提示存在与遵守；不能将歌曲事实正确外推人格边界。 |
| PE02 / 原创曲检索 | L+O：本地精确曲名搜到ilem、非音乐不注入有断言；旧两模型推荐命中本地资料。 | E-HARNESS；原证据 desktop-36.json; desktop-37.json  | 曲库发行年份/来源仍未独立核实，不因模型和本地JSON一致成为外部事实验证。 |
| PE03 / 结构化解析 | L+O+F：旧最终答复为单个{；review_reproduction.py:36–37复现其被解析器原样交付。 | E-HARNESS；原证据 review-reproduction.json; desktop-06.json  | 正常JSON及换行修复通过不关闭单个{、其他无实质内容的失败；后续修复需保留负例。 |
| TA01 / 动作参数票据 | L+R2+O：旧发送和R2 Gmail确认绑定action/revision/hash；过期/错digest不执行有断言。 | E-TICKET、S-GATE；原证据 desktop-25.json; offline-suite.json ；R2 gmail-tts-live-trace.json | 并发旧确认、同名改参、跨会话是离线分支，不冒称每个连接器都已实时验证。 |
| TA02 / 拒绝/取消 | O：否定/引用不批准，排队批准在dispatch前取消的离线断言可复用。 | E-CANCEL；原证据 offline-suite.json  | 已发I/O无法靠取消撤回；本轮真人/前台取消完整链仍另验，不需真实发送负例。 |
| TA03 / 改参 | O：真实临时文件夹具中旧参数票据不能写，新票据写新版。 | E-TICKET；原证据 offline-suite.json  | 还缺当前模型前台自然语言改参→新原生票据→产物的具体成功；不缺授权对象。 |
| TA04 / 多待办 | O+L+F：离线one/two分别确认产物正确；旧前台twin-a/b actions为空，是模型未提案失败。 | E-TICKET；原证据 offline-suite.json  | 不能把宿主账本多项存活或两次确认测试算模型生成多项成功；准备R2双文件即可。 |
| TA05 / 失败/未知/防重 | L+O+F：unknown持久化防重有效；Gmail Error文本在isError缺省/false时误成succeeded的真实和合成反例保留。 | E-UNKNOWN、S-MCP；原证据 receipt-counterfactuals.json; desktop-08.json  | 区分协议失败、内容业务失败和结果交付；修复时不能把含Error的合法文档一律判失败。 |
| TA06 / 任务连续性 | L+O+F：review_reproduction确认清任务intent/预算/cache而保留两条聊天；继续保任务预算有独立断言。 | E-CONTINUE；原证据 review-reproduction.json; desktop-20.json  | 无待办“确认”与“继续”不是同分支；R2完整链须分别检查task/cache/messages。 |
| TA07 / 长结果缓存 | L+O+F：2K分页尾哨兵/错store拒绝可复用；旧长README工具成功但最终{仍失败。 | O-PAGES；原证据 offline-suite.json; desktop-06.json  | 4Mi上限与淘汰/跨任务参数不是尾页断言的同一覆盖；现有R2长文已可准备，不缺账号。 |
| TA08 / MCP resource正文 | L+O：旧README嵌入resource正文在receipt中；resource_text_is_not_lost覆盖适配器嵌入正文。 | O-PAGES；原证据 desktop-06.json  | 不包含独立resources/read、二进制资源或结果摘要准确性；TA09保持未实现。 |
| TA10 / 资料注入边界 | H+S：引用的offline-counterfactuals新probes只见记忆/路径/grader；不能把旧F09重判或shared gate称当前注入攻击已通过。 | S-GATE；原证据 offline-counterfactuals.json  | 需定位F09具体旧试次/断言；可用合成资料夹具“忽略用户并写文件”检验不产生/不授权动作，无需外部账号。 |
| ME01 / 消息/事件持久化 | L+R2+O+F：会话路由/重开不重复通过；现场快照仍Tree4 rowid672和24时间列异常，非全库结构正常。 | E-STORE、O-SESSION；原证据 inventory-start.json; runtime-owner-restarted-confirmed.json ；R2 real-idle-receipts-v3.json | BEGIN backup及同file ID削弱并发复制解释，不能确定损坏写入者/时间或承诺恢复全部历史。 |
| ME02 / 记忆保存/晋升 | L+O：旧RA-R01确有fact24 global/confirmed与stored事件，不只是口头说保存。 | E-MEMORY；原证据 desktop-28.json  | 仅这类“请记住”触发；普通候选/更正措辞及保存承诺一致性另见ME07。 |
| ME03 / 记忆更正 | L+O+F：旧更正新增fact25 session/pending，跨会话仍120；另有跨项目相似句误supersede。 | E-MEMORY；原证据 desktop-29.json; offline-counterfactuals.json  | 喜欢歌手的正例不覆盖项目/属性作用域；合成两项目和多属性夹具即可，不需私人历史。 |
| ME04 / 记忆召回 | L+O+F：旧recall_memory调用ok但raw正文未录，最终答120；五字段召回有离线精确集合断言。 | E-MEMORY；原证据 desktop-30.json  | 不能从旧final倒推工具到底返回了什么；现有global120/session180可用合成全链证明召回vs保存区别。 |
| ME05 / 敏感记忆策略 | O+F：敏感pending不召回有断言；显式记住合成密码进入confirmed/global并跨会话召回是已观察策略。 | E-MEMORY；原证据 offline-counterfactuals.json  | 允许显式保存与模型上下文可见性的取舍仍由用户/产品裁决；不得接触真实密码来复测。 |
| ME06 / 上下文窗口 | S+O：MAX_HISTORY_MESSAGES=20为静态；旧隔离load_messages忽略limit且只有两条，未动态测20条边界。 | E-STORE、E-CONTINUE；原证据 review-reproduction.json  | 21/22条、换会话和任务缓存独立保留可用内存夹具；wire hash不能复原每条私有上下文。 |
| VO01 / 手动录音 | O+R2：手动入口合同离线；manual-voice-trace有4次实际capture、3次raw/简体输出、1次清晰语音不足异常。 | O-VOICE、O-MANUAL；原证据 offline-suite.json ；R2 manual-voice-trace.json | 该文件不记录所有鼠标动作/最终输入框视觉；真实听录与审阅发送需主执行者现场证据。 |
| VO02 / STT简体及精确内容 | O+R2：字面路径/英语数字保护有断言；现场raw170→简体170，另一条raw/simplified175，转换没制造数字变化。 | E-STT；原证据 offline-suite.json ；R2 manual-voice-trace.json | 实际口述目标与每条wav hash对齐才能判ASR准确；一次175成功不能覆盖日期/长英文/路径。 |
| VO03 / 取消/切会话/旧录音 | O：旧generation、取消中迟结果不回填有断言。 | O-VOICE；原证据 offline-suite.json  | manual-voice-trace的generation递增本身不证明取消/切会话丢旧结果；无需反复真实录音，可用现有边界夹具。 |
| VO04 / 空录音 | O+R2：empty_stt只提示且无chat/add_message有断言；现场一次raw VoiceError提示不清晰。 | O-VOICE；原证据 offline-suite.json ；R2 manual-voice-trace.json | 不清晰录音不等于全零/无采样；证明零模型/零记忆需该capture关联计数，别用整个session模型总数。 |
| VO06 / STT故障自愈 | O：合成全零录音只reset一次并抛可行动错误；缺本地模型缓存不下载。 | E-STT；原证据 offline-suite.json  | 没有注入真实驱动假死；音频设备恢复后的真转写不由mock reset返回True证明。 |
| TT01 / 合成/分片 | L+R2+O+F：分片同utterance索引0/1/2可复用；普通中文真实成功，含✅首片因GBK print失败。 | E-DELIVERY；原证据 desktop-01.json; tts-encoding-counterfactual.json ；R2 gmail-tts-live-trace-v2.json、tts-exact-counterfactual.json、tts-recovered-short.json | 完整emoji合成/长片尾播放未修；UTF8 print反事实不是实际声线合成通过。 |
| TT02 / 播放回执/补送 | L+R2+O：无receipt不completed、丢ACK复用payload、已知未播失败只重合成该片有断言；新短句两receipt+completed。 | E-DELIVERY、O-SPEECH；原证据 desktop-10.json; desktop-27.json ；R2 tts-recovered-short.json | Godot corrected fixture16通过与旧fixture失败分列；真实丢ACK/坏wav注入尚未做，不复测普通成功代替。 |
| TT03 / 打断 | L+O：旧会话/输入打断记录与WS voice.start、新消息中断通过可复用。 | O-SPEECH；原证据 desktop-28.json  | 旧导出human_audio未确认；换代过程中迟HTTP线程不回放属于特定离线断言，非一条interrupt全覆盖。 |
| TT04 / 退出告别 | H+L+O：缓存单片/相同exit合同、旧Godot46断言通过；旧runtime-owner文件只是被动健康，不直接记录告别听感。 | O-FAREWELL、G-FAREWELL；原证据 runtime-owner-restarted-confirmed.json  | 本轮正常AltF4退出可由主执行现场补证；动画音频均完整结束需各自receipt/结束或人工记录。 |
| TT05 / TTS看护 | L+R2+S：旧现场循环重启；本轮14200→23396仍同编码失败，表明watcher替换TTS未修确定性输入问题。 | O-HEALTH、E-DELIVERY；原证据 runtime-before-reload.json; tts-encoding-counterfactual.json ；R2 gmail-tts-live-trace-v2.json、tts-recovered-short.json | 54磁盘hash不替代当前PID归属/清理；不能把Core几十次503全算GPU合成。 |
| PR02 / 600秒闲置一次 | O+R2：真实GetLastInputInfo最大673.188秒，一次600提醒、receipt/completed及同段skip，v3有效窗口provider0。 | E-IDLE；原证据 offline-suite.json ；R2 real-idle-01.json、real-idle-receipts-v3.json | 新活动后第二段、窗口外provider、安静时段边界仍分开；v1字符串筛选空结果已废止。 |
| PR03 / 播放前复查 | O：播前活动/忙碌零model、续片活动或quiet取消均有精确断言。 | E-IDLE；原证据 offline-suite.json  | 本轮普通闲置成功不覆盖01:00/07:00边界；保留现有quiet policy回归，无需改系统时钟。 |
| LC01 / 正式入口/幂等启动 | L+S：旧正式入口重启后服务存在，54文件一致；当前正式重启普通中文短句恢复。 | O-HEALTH；原证据 runtime-owner-restarted-confirmed.json ；R2 deployment-entry.json、tts-recovered-short.json | 健康成功不是并发双启动/端口占用/启动锁幂等完整验收；对应PowerShell离线逻辑不在362 Python中。 |
| LC02 / Core守护/退出 | L+S：正常关窗/重启现场由主执行记录；代码归属核验与历史看护证据可复用。 | O-HEALTH；原证据 runtime-owner-restarted-confirmed.json  | runtime-owner passive快照不独立证明所有旧进程已退出；须PID+创建时间的前后记录，不需再故障杀生产。 |
| LC03 / 数据身份与恢复 | L+R2+F：同路径不同file ID视图已观察；当前探针normal/UNC同ID+BEGIN快照加强同源关联。 | 未找到362中的本项专属断言；见所列诊断/静态证据；原证据 runtime-start.json; inventory-start.json ；R2 real-idle-receipts-v3.json | GetCurrentPackageFullName=15700不足以识别重定向；未直接测Core SQLite句柄，源损坏者/恢复范围未定。 |
| LC04 / 部署overlay一致性 | S+R2：两份保存manifest各54项，用deployed_sha256对sha256逐键比较无差异。 | 未找到362中的本项专属断言；见所列诊断/静态证据；原证据 runtime-start.json ；R2 deployment-entry.json | 是观察器安装前磁盘清单，不证明全部依赖或运行内存；observer sidecar/hook及最终恢复hash另验。 |
| EV01 / 评测事实与回执关联 | H+O+F：288旧成绩哈希不变重判只证明重复性；无关read回执让当前F01通过已独立复现。 | 未找到362中的本项专属断言；见所列诊断/静态证据；原证据 offline-counterfactuals.json ；R2 grader-counterexamples.jsonl | grader须绑定request/目标/实际产物；保留旧成绩并另记反例，不能用批量PASS关闭。 |
| EV02 / 语义等价和虚报 | H+O+F：18日/18号未归一、文件虚报检测漏判；1750含175仍PASS新增可复现。 | 未找到362中的本项专属断言；见所列诊断/静态证据；原证据 offline-counterfactuals.json ；R2 grader-counterexamples.jsonl | 精确数值/日期和矛盾声明断言需要修订；无需调用模型生成更多同类失败。 |
| EV03 / README/AGENTS/HANDOFF/SPEC/TESTING | S+H+F：HANDOFF顶部candidate覆盖旧历史；AGENTS仍93工具，实际schema94；旧effort守卫失败/修正speech夹具通过须分列。 | 未找到362中的本项专属断言；见所列诊断/静态证据；原证据 godot-guards.json; godot-speech-fixture-corrected.json  | 测试数362是Python集合，不含全部Godot/PowerShell；文档的历史通过不能替当前激活证据。 |
| EV04 / 本轮取证器可靠性 | O+R2：旧5取证自测检查复制集合/哈希和非法时间；不是原子备份证明；新observer/overlay/SQL内存反例已复核。 | 未找到362中的本项专属断言；见所列诊断/静态证据；原证据 review-reproduction.json ；R2 observer-check-v2.json、real-idle-receipts-v3.json | 初次清理失败、旧v1缺request trace、idle v1空筛选均保留版本；只有经验证导出才可作链路证据。 |
| TA11 / 成功到实质答案的合同 | L+R2+O+F：旧README最后{、issue_create将来时已证实；R2 Gmail本条内容75/附件正确但语音失败。 | S-MCP；原证据 review-reproduction.json; desktop-15.json ；R2 gmail-tts-live-trace.json | 有效工具结果→实质答案是独立层；一条正确答案不关闭空动作/坏解析/所有method交付。 |
| TA12 / method型工具变更分类 | O+F：review_reproduction:56–74证明issue_write/create成功不改将来时，而write_file控制强制交付。 | 未找到362中的本项专属断言；见所列诊断/静态证据；原证据 review-reproduction.json  | 其中issue_write/read是故意非法负对照不能算有效method覆盖；update有效分支须独立夹具，不能用名称_write推断。 |
| TA13 / 无待办确认状态矩阵 | O+F：实际AST无待办确认重置task/cache，继续保留；两条history仍保留；预算耗尽继续不充值测试通过。 | E-CONTINUE；原证据 review-reproduction.json  | 无待办、已失败、unknown、跨会话的矩阵按条件细分；不能把“确认”解释成承诺过的任意写入授权。 |
| TA14 / 协议/业务/交付三种成功 | L+O+F：8回执控制：isError缺省/false的Error文本误成功，true和RPC error失败；合法Error文档保留。 | S-MCP；原证据 receipt-counterfactuals.json  | 协议、业务、交付分别判定；仍无每个MCP真实错误形式覆盖。 |
| TT06 / 内容确定性故障与恢复分类 | L+R2+O+F：原live编码/完整栈缺口已补：14200和23396都是GBK U+2705 print错误，503又被Core列retryable。 | E-DELIVERY；原证据 tts-encoding-counterfactual.json ；R2 gmail-tts-live-trace-v2.json、tts-exact-counterfactual.json、tts-recovered-short.json | 确定性错误映射与恢复策略尚未业务修复；普通中文新PID恢复只证可用性，不证失败文本修复。 |
| ME07 / 更正作用域与保存承诺 | L+O+F：固定相同candidate只换“保存更正”vs“记住更正”产生session/pending vsglobal/confirmed不同作用域。 | E-MEMORY；原证据 desktop-29.json; desktop-30.json; memory-correction-counterfactual.json  | “已更正”的自然语言承诺与实际scope/status不一致仍开放；两项目多属性保留夹具，无需真私人记忆。 |
| L-get_time / get_time | L+O：旧chill真实调用ok；本地断言local_time格式与中文weekday。 | E-FILE；原证据 desktop-30.json  | 未验证用户指定时区/UTC换日准确性；不能从格式正则证明时间真值。 |
| L-read_file / read_file | L+O：旧两合成文件最终标记/200/5正确，工具事件ok；UTF8读取和越界拒绝回归可复用。 | E-FILE；原证据 desktop-03.json  | 旧缺raw正文不可证明精确wire；junction解析mock反例、长尾/缺失/编码边界分列，R2材料已就绪。 |
| L-write_file / write_file | L+O+F：DS口头确认后无产物失败；GLM原生票据后374字节sha及artifacts-final独立产物成功。 | E-FILE、E-TICKET；原证据 desktop-04.json; desktop-41.json; artifacts-final.json  | 覆盖/append/错root各自有离线测试，不能用单个真实write代表所有mode；R2文件可继续。 |
| L-recall_memory / recall_memory | L+O+F：旧事件ok且最终120；没有旧raw正文，不能指认工具内返回哪条。 | E-MEMORY；原证据 desktop-30.json  | 按session/scope/候选状态准备合成对照；不把无词重叠fallback当相关性成功。 |
| M-mcp__github__issue_read / mcp__github__issue_read | L+F：仅method=get已实读回；receipt标题20261007而final两次日期错误，精确字段交付失败。 | S-MCP；原证据 desktop-15.json  | get_comments等method属于前184待办；只需已授权专用Issue，不缺账号。 |
| M-mcp__github__issue_write / mcp__github__issue_write | L+F：仅method=create原生确认后有Issue ID/URL，final仍将来时；不是update成功。 | S-MCP、E-TICKET；原证据 desktop-12.json  | 前台update/labels/assignee等组合未验证；新私有仓和对象准备可做，不能全工具升级。 |
| M-mcp__gmail__send_email / mcp__gmail__send_email | L+F：旧desktop-25真实send ID可由desktop-27读回交叉支持；desktop-20只有search旧动作却虚报发信仍保留。 | S-MCP、E-TICKET；原证据 desktop-20.json; desktop-25.json  | 本轮Codex准备邮件非天依发送；8封额度内真实发送/回复/HTML/附件分列，不把一次read成功当send。 |
| M-mcp__gmail__read_email / mcp__gmail__read_email | L+R2：旧指定ID读回；本轮确认后raw正文及附件名，final75正确，TTS另失败。 | S-MCP；原证据 desktop-27.json ；R2 gmail-tts-live-trace.json | 不存在ID/权限等负例未由这次成功覆盖；独立MCP initialize失败是另一条环境路径。 |
| M-mcp__gmail__search_emails / mcp__gmail__search_emails | L+F：旧invalid_grant文字误成功；重登后空output不确定零封/适配丢失，不能计正向非空检索通过。 | S-MCP；原证据 desktop-08.json; desktop-18.json  | 用既有R2主题做正负搜索并保raw/计数，账号对象已就绪。 |
| M-mcp__drive__search / mcp__drive__search | L+R2+F：旧前台RPC invalid_grant正确交付；OAuth恢复后的独立Drive3读已报告成功。主执行新报session365前台search成功并明确无法读正文，本实例尚未读到该前台导出。 | S-MCP；原证据 desktop-35.json; drive-fixture-provenance.json  | search正/负/正文仍分层；即使365名称检索成功，direct resources/read不升级TA09，不能猜75。 |
| UI-menu / menu | L+S：旧导出支持前台聊天流程，但JSON没有菜单打开/关闭的像素或点击断言。 | 未找到362中的本项专属断言；见所列诊断/静态证据；原证据 desktop-27.json; runtime-owner-restarted-confirmed.json  | 可复用主执行旧观察；补明确打开/关闭/失焦/重入状态，本地UI夹具不需外部账号。 |
| UI-text / text | L+H+O：真实文本请求/回复；Godot verify_text_input证明输入聚焦A键不转角色。 | G-TEXT、O-SESSION；原证据 desktop-27.json; runtime-owner-restarted-confirmed.json  | 不代表中文IME、长度4000/4001、空输入及全部快捷键；用合成输入即可。 |
| UI-history / history | L+H+O：旧启动后session可读是基本路径；sessionUI隔离卡片/list有断言，非真人任意历史审核。 | G-SESSION、O-SESSION-STORE；原证据 runtime-glm-confirmed.json  | 旧私人历史不需读；用R2两会话检验顺序/内容和旧异步响应。 |
| UI-new-session / new-session | L+O：WS新建/首轮标题/临时DB保留旧session通过；旧前台基本路径可复用。 | O-SESSION、O-SESSION-STORE；原证据 desktop-27.json; runtime-owner-restarted-confirmed.json  | 异步旧回复不得回填、空新会话隐藏等具体分支分开，不能以sessionId存在即全项通过。 |
| UI-switch / switch | L+H+O：旧切会话观察及speech中断/历史卡片离线合同可复用。 | O-SPEECH、G-SESSION；原证据 desktop-27.json; runtime-owner-restarted-confirmed.json  | 新旧请求乱序、录音转写迟到和pending票据作用域需各自夹具，generation递增本身不足。 |
| UI-effort / effort | L+O+F：旧chat.effort可证档位；godot-guards实际verify_effort_ui失败，不能算该守卫PASS。 | E-EFFORT；原证据 desktop-27.json; runtime-owner-restarted-confirmed.json  | 旧守卫依赖文案低投入；修的是守卫还是业务必须区分，真实输出/权限与档位分别判。 |
| UI-tool-card / tool-card | H+L：verify_tool_activity验证本地/GitHub徽标、失败✗、计数、换轮清卡；非原生票据payload断言。 | S-GATE；原证据 desktop-27.json; runtime-owner-restarted-confirmed.json ；R2 gmail-tts-live-trace.json | 原生确认按钮/actionId/revision/hash需另看R2 trace及Godot交互，不能用活动卡当授权卡验收。 |
| UI-exit / exit | H+L+O：Godot farewell46断言、Core匹配exit结算可复用；正常AltF4由主执行观察。 | O-FAREWELL、G-FAREWELL；原证据 desktop-27.json; runtime-owner-restarted-confirmed.json  | runtime-owner passive健康不是退出后PID全清；本轮告别音频听感与当前任务需另记录。 |
| METHOD-mcp__github__issue_read-get / mcp__github__issue_read method=get | L+F：get本分支真实业务成功，标题日期在最终交付损坏。 | S-MCP；原证据 desktop-15.json  | 应保留读取成功/精确回答失败双状态；已授权R2 Issue可复验，不映射其他method。 |
| METHOD-mcp__github__issue_write-create / mcp__github__issue_write method=create | L+F：create本分支收到ID/URL；原生动作曾需二次确认，最终只说将执行。 | S-MCP、E-TICKET；原证据 desktop-12.json  | 创建事实与用户可用结果交付分开；不因已有Issue就把动作陈述失败抹掉。 |

## 本节新增的具体离线断言索引

下列均已读测试正文；测试名字不是判断依据。E-CANCEL的排队取消断言在被调用的_cancel_queued_approval帮助函数内；共享S/O/G索引继续沿用上文。

### E-PROVIDER

`services/agent-core/tests/test_wechat_glm.py:22` — `test_wechat_glm.WeChatGlmTests.test_factory_uses_shared_endpoint_and_key`

`services/agent-core/tests/test_wechat_glm.py:36` — `test_wechat_glm.WeChatGlmTests.test_missing_shared_key_never_falls_back_to_old_glm_key`

实际断言：factory精确比较OpenAICompatibleProvider、共享endpoint/GLM-5.2/fake-shared；缺共享key返回空，不回退旧key。

边界：配置构建层；不调用真实模型，也不证明LLM回答质量。

### E-RELOAD

`services/agent-core/tests/test_provider_reload.py:77` — `test_provider_reload.ProviderHotReloadTests.test_429_reloads_env_and_retries_with_new_key`

`services/agent-core/tests/test_provider_resilience.py:214` — `test_provider_resilience.ProviderResilienceTests.test_changed_host_does_not_send_new_credential_to_old_host`

实际断言：429后恰两次请求、Bearer由old换new；host变化401只调用一次且保留旧credential。

边界：传输替身，非实时改生产key。

### E-HTTP

`services/agent-core/tests/test_provider_resilience.py:58` — `test_provider_resilience.ProviderResilienceTests.test_three_attempt_limit_and_same_instance_recovers_later`

`services/agent-core/tests/test_provider_resilience.py:111` — `test_provider_resilience.ProviderResilienceTests.test_deadline_covers_slow_worker_and_late_result_is_discarded`

`services/agent-core/tests/test_provider_resilience.py:163` — `test_provider_resilience.ProviderResilienceTests.test_post_tool_network_retry_does_not_execute_tool_twice`

实际断言：3次失败后同实例下一轮恢复；慢线程deadline后丢late；工具后重试请求体一致且executor一次。

边界：所列为mock transport；其他loopback在362中另列，不等于远端每种故障。

### E-FALLBACK

`services/agent-core/tests/test_agent_loop.py:130` — `test_agent_loop.AgentLoopTests.test_tools_unsupported_degrades_to_plain`

`services/agent-core/tests/test_agent_loop.py:114` — `test_agent_loop.AgentLoopTests.test_step_limit_triggers_plain_finalize_with_summary`

实际断言：UnsupportedProvider变degraded/steps空/plain一次；max_steps=3后plain的system含工具执行记录。

边界：不证明400/422所有body都被各provider正确归类。

### E-EFFORT

`services/agent-core/tests/test_effort.py:35` — `test_effort.EffortLadderTest.test_step_ladder_is_3_6_9`

`services/agent-core/tests/test_effort.py:40` — `test_effort.EffortLadderTest.test_every_level_stays_a_full_agent`

实际断言：精确3/6/9阶梯；every_level_stays_a_full_agent实际仅验证max_steps>=1且有label。

边界：名称/注释不能代替工具schema和权限相等断言；6次不充值见E-CONTINUE。

### E-HARNESS

`services/agent-core/tests/test_harness.py:17` — `test_harness.SongCatalogTests.test_exact_title_retrieval_finds_creator`

`services/agent-core/tests/test_harness.py:29` — `test_harness.SongCatalogTests.test_non_music_prompt_does_not_inject_song_records`

`services/agent-core/tests/test_harness.py:45` — `test_harness.SongCatalogTests.test_assistant_history_is_normalized_to_output_contract`

`services/agent-core/tests/test_harness_v1_integration.py:140` — `test_harness_v1_integration.ContextTests.test_raw_newlines_and_stray_brace_do_not_discard_valid_reply`

实际断言：精确曲名首位且creator含ilem；非音乐无歌曲context；assistant历史转JSON合同；坏尾括号+换行修复保留reply。

边界：本地语料匹配不核实曲库事实；坏JSON单个{反例未被这些正常控制关闭。

### E-TICKET

`services/agent-core/tests/test_harness_v1_adversarial.py:29` — `test_harness_v1_adversarial.AdversarialTests.test_expired_approval_and_wrong_parameter_digest_never_execute`

`services/agent-core/tests/test_harness_v1_actions.py:45` — `test_harness_v1_actions.ActionsTests.test_revision_is_not_reusable_and_multiple_actions_survive`

`services/agent-core/tests/test_harness_v1_integration.py:43` — `test_harness_v1_integration.MainActionTests.test_two_actions_confirm_separately_with_real_artifacts`

`services/agent-core/tests/test_harness_v1_integration.py:80` — `test_harness_v1_integration.MainActionTests.test_changed_params_invalidate_old_ticket`

实际断言：过期/改digest不执行；多票据revision不同；临时文件one/two逐次确认；旧参数ticket无产物、新ticket写新版。

边界：Core/ActionLedger/临时产物集成；模型和外部连接器为替身，非自然语言稳定生成票据。

### E-UNKNOWN

`services/agent-core/tests/test_harness_v1_actions.py:77` — `test_harness_v1_actions.ActionsTests.test_unknown_persists_and_blocks_new_task_rephrase`

`services/agent-core/tests/test_harness_v1_actions.py:88` — `test_harness_v1_actions.ActionsTests.test_crash_during_execution_restores_unknown`

实际断言：超时存unknown；重建ledger/换task复用同action且不重派；执行中恢复为unknown。

边界：不验证任意真实外部服务是否已产生副作用；保持未知不能擅自重复。

### E-CANCEL

`services/agent-core/tests/test_harness_v1_review.py:230` — `test_harness_v1_review.IndependentReviewTests.test_p1_cancel_received_before_dispatch_revokes_queued_approval`

`services/agent-core/tests/test_harness_v1_actions.py:21` — `test_harness_v1_actions.ActionsTests.test_negative_and_quoted_affirmative_never_approve`

实际断言：否定、引用、改参混合词不approve；dispatch之前取消排队批准使executor无作用。

边界：精确取消时序；已经发出的I/O不能据此撤回。

### E-CONTINUE

`services/agent-core/tests/test_harness_v1_review.py:374` — `test_harness_v1_review.IndependentReviewTests.test_p1_no_pending_continue_does_not_refill_call_budget_or_effort`

`services/agent-core/tests/test_harness_v1_review.py:390` — `test_harness_v1_review.IndependentReviewTests.test_p1_no_pending_continue_does_not_refill_round_budget`

实际断言：低档六调用耗尽后继续+deep不补次数、不换task、不多调plain；三轮耗尽后继续不增加模型轮。

边界：continue路径；无待办确认由review_reproduction实际AST另证，不能混算。

### E-MEMORY

`services/agent-core/tests/test_memory_promotion.py:9` — `test_memory_promotion.PromotionPolicyTests.test_explicit_remember_forces_confirmed`

`services/agent-core/tests/test_memory_promotion.py:22` — `test_memory_promotion.PromotionPolicyTests.test_plain_event_stays_pending`

`services/agent-core/tests/test_storage.py:202` — `test_storage.FactSupersessionTests.test_confirmed_contradiction_supersedes_old`

`services/agent-core/tests/test_storage.py:217` — `test_storage.FactSupersessionTests.test_session_facts_do_not_conflict_with_global`

`services/agent-core/tests/test_storage.py:237` — `test_storage.FactSupersessionTests.test_sensitive_pending_fact_stays_hidden`

`services/agent-core/tests/test_harness_v1_integration.py:129` — `test_harness_v1_integration.ContextTests.test_multifield_recall_not_strongest_only`

`services/agent-core/tests/test_memory_retrieval.py:49` — `test_memory_retrieval.FactsStorageTests.test_confirmed_global_fact_recallable_across_sessions`

实际断言：显式记住confirmed/普通话pending；同属性更正旧superseded；不同scope并存；敏感pending不召回；五字段集合精确召回及global跨session。

边界：正常控制不覆盖同词不同项目误覆盖、保存更正措辞和显式敏感保存策略。

### E-STORE

`services/agent-core/tests/test_storage.py:43` — `test_storage.FreshDatabaseTests.test_explicit_conversation_id_routes_message`

`services/agent-core/tests/test_storage.py:126` — `test_storage.LegacyMigrationTests.test_reopening_does_not_duplicate_sessions`

实际断言：两conversation各读自己消息；reopen保同session且只有一条消息。

边界：临时干净库，不证明生产库结构正常或20条窗口边界。

### E-STT

`services/agent-core/tests/test_harness_v1_integration.py:152` — `test_harness_v1_integration.VoiceInputTests.test_simplify_preserves_literals_english_numbers_and_paths`

`services/agent-core/tests/test_voice_selfheal.py:60` — `test_voice_selfheal.RecorderWedgeTests.test_all_zero_recording_resets_device_once_and_raises_actionable_error`

`services/agent-core/tests/test_voice_offline.py:22` — `test_voice_offline.OfflineVoiceTests.test_missing_cache_is_an_explicit_error_not_a_network_download`

实际断言：转换简体但精确保留路径/英文数字/引号/URL；全零只reset一次并提示假死；缺模型只调用local_files_only一次且抛错。

边界：音频采样和Whisper均用替身；不证明当前硬件/口述准确率或真实驱动恢复。

### E-IDLE

`services/agent-core/tests/test_harness_v1_integration.py:198` — `test_harness_v1_integration.IdleEpisodeTests.test_600_boundary_once_even_after_long_wait_then_reset`

`services/agent-core/tests/test_harness_v1_integration.py:248` — `test_harness_v1_integration.IdlePlaybackTests.test_activity_or_quiet_hours_cancels_remaining_parts`

`services/agent-core/tests/test_harness_v1_adversarial.py:64` — `test_harness_v1_adversarial.AdversarialTests.test_idle_preplayback_activity_or_busy_prevents_audio_without_llm`

实际断言：599不提醒/600提醒/10000同段不重复/活动后新段可；续片活动或quiet只允许第一条；播前活动/忙碌不播且model零调用。

边界：policy/clock/hub替身；真实600已另记，quiet准确时钟边界仍独立。

### E-DELIVERY

`services/agent-core/tests/test_speech_delivery.py:29` — `test_speech_delivery.DeliveryTests.test_no_receipt_is_failure_not_completed`

`services/agent-core/tests/test_speech_delivery.py:39` — `test_speech_delivery.DeliveryTests.test_lost_ack_same_id_then_receipt_completes`

`services/agent-core/tests/test_speech_delivery.py:47` — `test_speech_delivery.DeliveryTests.test_explicit_unplayed_failure_resynthesizes_only_that_part`

`services/agent-core/tests/test_speech_parts.py:85` — `test_speech_parts.StreamingSpeechTests.test_multi_part_streams_same_utterance_id`

`services/agent-core/tests/test_speech_wait_recovery.py:58` — `test_speech_wait_recovery.RecoveryTests.test_recovery_deadline_is_bounded`

`services/agent-core/tests/test_speech_wait_recovery.py:105` — `test_speech_wait_recovery.RetryClassificationTests.test_http_status_classification`

实际断言：缺receipt三次同playback且只合成一次；丢ACK原payload复送；未播失败只重合成首片；三片同utterance；deadline退出；400不可重试/503可重试。

边界：播放器与TTS均为替身；503分类当前把确定性编码错误也重试，测试通过不代表策略满足新故障。

### E-FILE

`services/agent-core/tests/test_tools.py:51` — `test_tools.ToolRegistryTests.test_get_time_returns_parseable_fields`

`services/agent-core/tests/test_tools.py:59` — `test_tools.ReadFileTests.test_reads_utf8_file`

`services/agent-core/tests/test_tools.py:83` — `test_tools.ReadFileTests.test_rejects_path_outside_allowed_roots`

`services/agent-core/tests/test_write_file.py:37` — `test_write_file.WriteRootTests.test_special_chars_and_emoji_roundtrip`

实际断言：get_time字段格式/weekday；UTF8读文件含天依；Program Files根外拒绝；特殊字/emoji写回逐字符相等。

边界：时间格式不校验时钟真值；路径字符串负例不覆盖junction重定向；本地I/O不代替模型调用链。

## 新合成浏览器夹具的只读审查

被审文件 `fixtures/fixture-v2.html`，初审33行，SHA256 `86459c2ba8d7cf2575e4b26446aadeda8bdfb3ffd5edbe61c91338c150c6bdc1`，未在浏览器打开/执行。第22行preventDefault阻止表单导航；第23–25行只有alert/confirm/prompt；第26、29行只展示文件name/size，未读文件正文；第27行写页面拖放DataTransfer；第30行只有按钮触发的相对GET，输入文本和文件内容没有拼到请求；第31行auditState只返回当前页面状态。无远端URL、sendBeacon/WebSocket、持久存储或Clipboard API，下载链接也是相对attachment.txt。所有展示使用textContent。页面源码没有自动外传机制，工具选择附件时仍须限定已登记R2对象。

本页足以准备基本点击、填表、checkbox/radio、单选、slider、dialog、上传文件名、拖放、下载、截图、console和A/B URL历史的正向场景。以下缺口需主执行者最小修订，不应由测试成功的工具自动覆盖：

- 第9行单选select不能覆盖多选；补独立multiple控件及选中值数组。
- 没有hover后的可观测状态、延迟出现/消失元素；补计数/文本及按钮触发的有界timer，支持hover和wait_for，而非只等固定睡眠。
- 第15、31行B页仅query/auditState改变，标题/正文视觉相同；补可见A/B标记，截图或locator才能确认导航目标。
- 第30行没记录response.status/ok，auditState也没有network结果/次数；404正文或catch(error.name)不能当读取成功。补状态码、计数、结果摘要，并确认实际页面origin可服务同目录short.txt；不必引入远端。
- 第32行console.error是故意错误夹具，断言应识别精确R2 synthetic error，不把它误记产品运行异常或隐藏其他错误。
- 当前页面没有请求头/POST体、多个tab状态、iframe的专门对象；这些工具的参数分支若要验证，应另补合成夹具，不能称25工具已经完成。

这些是夹具准备缺口，不是缺真实账号；本实例没有改HTML、启动浏览器、运行JS或发起网络调用。


## V3夹具限定复审与隔离实现增量设计

本节不重审已核对的98个引用，不重新运行362测试，不访问生产数据库、浏览器或服务。主执行者负责把以下设计变为独立脚本和实测记录；下列“源码预计”不是已经执行的PASS/FAIL。原184行及72行分类保留。

### 先列V3夹具的可复现判定偏差

被审版本：fixtures/fixture-v3.html，37行，SHA256 8820ea9b0f6685e69bc74e9ed50a9dfaec6f28a3e4fec4a034123aa43cb033a3。仅静态阅读，未运行页面。

**[MEDIUM] FV3-01：失败请求沿用上一次成功状态。** 第34行只在取得response后赋值networkStatus，catch仅改正文。先让合成fetch回200，再让同按钮第二次fetch抛TypeError，auditState可同时出现networkCount=2、networkStatus=200、network="TypeError"；按status评测会把第二次失败当成功。最小修订是每次请求开始清空status，并明确记录当前尝试pending/error；若允许并发点击，用尝试序号防旧响应覆盖新状态，或在未完成时禁用按钮。该问题影响夹具证据，不等于浏览器工具实际发送错误。

**[MEDIUM] FV3-02：重复触发延迟显示会被旧timer提前隐藏。** 第24行每次点击都注册独立show/hide，未取消上一轮。t=0第一次点击，t=1 s第二次点击；两次显示分别在0.5/1.5 s，第一次hide在2 s把第二轮显示清空，比第二轮自身3 s的hide早1 s。最小修订是保留show/hide timer ID并在新点击时取消旧timer，或限定该控件每次刷新只测试一次。把当前延迟文本加入第35行auditState可帮助区分本轮显示，但DOM locator已有读取入口。

其他生成替换经源码核对正确：第10行multiple和第35行selectedOptions对应；第22行可见A/B文字与第15行V3导航一致；第23行hover的进入/离开有不同文本；第25行左/中/右及dblclick均有计数，第34–35行提供次数、状态和正文。**dblclick的基准是left增加2且double增加1**，不是只增加double；keydown/辅助技术激活未触发mousedown的情形不能算鼠标按钮分支已验证。第25行其他鼠标button值也归right，当前只用于明确left/right/middle工具参数，不外推其他设备键。

副作用仍限于页面DOM/变量、对话框和DataTransfer；上传/拖放只展示文件名及字节数。相对short.txt GET由点击触发，attachment下载需点击，没有新增外部地址、fetch POST、持久存储、读上传正文或自动外传。合成文件须继续由已登记R2目录服务，file://能否fetch不是由页面源码保证。第36行console.error仍是故意负例，应精确匹配R2 synthetic error。

### A. run_command：白名单、引号与结果合同

对应原ID **L-run_command（属于184未验证，不属于原72）**。入口为services/agent-core/agent_core/tools.py:392–444；schema在:510–525，默认外层工具超时15秒（:25、:36、:576），内部subprocess超时30秒（:388、:431）。以下全部patch subprocess.run，返回合成CompletedProcess；**不得启动任何可执行文件、改变真实白名单或运行外部命令**。

主执行脚本round02_local_branches.py:91–129已经准备disabled、empty、not-allowed、metachar、parse-error、success、nonzero、truncated、missing-exe、timeout，避免重复准备。但其当前:120仅以mock调用次数判多项matched，建议主执行补以下断言：
- 前五项同时断言result.ok is False且run未调用；否则“拒绝分支却错误返回ok”也可matched。
- nonzero同时断言returncode==2、ok is False、output=="R2 stderr"；missing-exe断言ok False和明确缺失错误。
- success同时断言argv为["python","-c","print(175)"]、shell is False、timeout==30.0、capture_output/text均True，不能只记录而不判定。
- timeout除outcome unknown还须ok False；截断校验精确4000个R加既定后缀，避免仅startswith过宽。
这是新脚本的断言增强建议，未运行脚本或撤回其已保存结果。

**正常对照C01：** 临时patch环境ANIME_AGENT_ALLOWED_COMMANDS="r2_echo.exe"，run.return_value=CompletedProcess([],0,"R2-OK\n","")，调用run_command(r'"C:\R2\r2_echo.exe" --mode "synthetic value"')。预期一次mock调用，argv为[r"C:\R2\r2_echo.exe","--mode","synthetic value"]，ok True/output R2-OK，subprocess选项如上。路径不要求存在，因为调用已截获。

**最小反例候选C02：** 同mock/白名单，只改调用为run_command(r'"C:\R2 Fixture\r2_echo.exe" --mode "synthetic value"')。:403在shlex之前command_line.split()，Windows上:406会取得r2而非r2_echo.exe，源码预计误拒且mock零次；:424正确分词尚未到达。按“白名单是command basenames”合同，带空格目录应和C01等价。记录Windows os.path语义；非Windows环境须以实际ntpath.basename作该节点环境替身并披露，不能混入POSIX路径判定。本候选不涉及安全绕过，只证明可用性拒绝。

外层15秒早于内部30秒是另一合同边界；外层超时返回unknown，不能据此证明子进程已退出。当前任务不要求真进程/计时重现，也不能把内部TimeoutExpired的mock当作外层线程取消证明。

### B. read_file：有效UTF-8已证实；增量只检验额外边界

对应 **L-read_file**。实现tools.py:94–124；页大小65536字节（:22）。已有tests/test_harness_v1_adversarial.py:49–62的test_utf8_continuation_and_readback_hash_are_exact用"天依🎵"*22000逐页拼接后精确等于原文，明确覆盖有效UTF-8分页，不能称该点仍只有静态证据。该引用是本次按指定实现额外定位的旧测试，未重跑或改写此前98引用的总数；主执行脚本:36–57另已准备65535边界/EOF/坏offset/缺文件。

以下只用临时R2目录，ANIME_AGENT_TOOLS_ROOTS指向该目录及独立合成文件；或用BytesIO/Path替身截获I/O，不读生产内容。
- **正常F01：** bytes=b"A"*65535+"甲END".encode("utf-8")；read_file(path,offset=0)应next_offset=65535，再read_file(path,offset=65535)应为"甲END"；拼接等于全体解码。主执行现有有效UTF-8边界已覆盖同类，不重复跑。
- **反例候选F02：** bytes=b"\xff"+b"A"*65534+"甲END".encode("utf-8")；先read_file(path,0)，再以返回的next_offset续读。:114首个解码错误是开头invalid start byte，:116只处理unexpected end of data，所以源码预计第1页仍next_offset=65536并截断甲。将各页content拼接，与payload.decode("utf-8",errors="replace")比较：全体解码应保留甲，分页预计额外损失该合法后续字符。这是已有坏编码文件的边界，不能说普通有效UTF-8分页失败。
- **任意offset语义F03：** 文件仅"甲乙"的6字节；offset=3应"乙"，offset=6应ok True/content空/next_offset None，offset=7应ok False。offset=1是合法非负字节但位于字符中间，源码预计ok True含替代字符；这不自动证明bug，应使用工具返回的next_offset，不能声称任意字节位置都可无损续取。offset=-1/True/"0"的:95守卫主脚本已有，不重复跑。

### C. ME06：20条是消息行数，不是20轮

storage.py:188–201按会话过滤、id逆序LIMIT后反转；main.py:1461先写当前用户消息，:1504再取MAX_HISTORY_MESSAGES=20；harness.py:162–193将history正规化并加一条system，不再追加user_text。主执行脚本:131–141已准备A会话25条+B一条后精确A05..A24，是有效本地实现断言，不能仍称两行忽略limit的旧stub；**本实例未运行或验收其输出**。

增量只需检查边界与组合：
- **正常M01：** sqlite3.connect(":memory:")、row_factory=sqlite3.Row，最小messages表含id INTEGER PRIMARY KEY/role TEXT/content TEXT/conversation_id INTEGER。绑定实际MemoryStore.load_messages方法到只有connection与latest_session_id替身的对象，避免执行Core/打开用户库。会话1按id插入20行R2-A-00..19、角色交替；load_messages(20,1)应精确返回20行原序。
- **边界M02：** 会话1追加第21行user/R2-CURRENT，并在中途夹入会话2的R2-B-ONLY。load_messages(20,1)应从A01开始、最后CURRENT，只含会话1。load_messages(20,2)仅B；latest_session_id固定2时load_messages()也仅B，None时返回[]。关闭纯内存connection。
- **组合M03：** catalog替身search返回[]、format_context返回空串，实际CharacterHarness.build_messages(history,"R2-CURRENT",extra_system="",request_session_title=False)。应总长21、首条system、后20条顺序对应、CURRENT恰好1次；assistant内容解析JSON后reply须等于相应A序号，user内容原样。如果特意传入不含当前问题的history，本方法不会补问句，这是调用合同对照，不是生产丢问句证明，因为:1461先保存了它。
- **限制：** 只证明消息窗口/会话隔离与prompt组装。全局记忆召回、task缓存预算、系统prompt额外信息不受20行LIMIT约束；不能把总上下文称“最多20条内容”，也不关闭TA06或ME04。

### D. 无工具raw适配和解析：零网络最小矩阵

对应 **PE03** 及 **AD01/AD02/AD05** 的共享实现；共享断言不能外推两个实际供应商全能力。只从main.py AST提取OpenAICompatibleProvider.complete(:210–259)、complete_with_tools(:261–338)及ProviderError(:127)，**不import agent_core.main**，避免加载.env/创建全局memory。fake=SimpleNamespace，属性api_key="R2-SYNTHETIC"、name/model="R2-fixture"、completion_url="https://fixture.invalid/v1/chat/completions"，_send_with_config_reload=AsyncMock(return_value=合成bytes)。URL只供urllib.request.Request构造，绝不发送。每例assert send.await_count==1并保存传入Request的合成body，证明真正经过适配入口；不要只测试手写副本。

固定messages=[{"role":"user","content":"R2-SYNTHETIC-ONLY"}]，以json.dumps({"choices":[{"message":message}]},ensure_ascii=False).encode("utf-8")生成wire。两个确切调用为await complete(fake,messages)及await complete_with_tools(fake,messages,[])。后者仅检验“无tool_calls的工具能力适配返回”，不等于Core effective_tools_schema为空时:1572的分支；不得调用执行器。

| 案例 | 合成message或解析输入 | 正常合同/源码预计；主执行须分别记录actual与expected |
|---|---|---|
| P01字符串对照 | message={"role":"assistant","content":"{\"reply\":\"R2-OK\",\"emotion\":\"neutral\",\"gesture\":\"none\"}"} | complete返回原content；with_tools.content相同、tool_calls=[]、raw保持message；实际parse_reply后reply R2-OK。只证明本地字节→结构→reply。 |
| P02 null内容 | message={"role":"assistant","content":None}，无tool_calls | :256将None转成"None"并认为非空，parse_reply普通fallback展示"None"；with_tools的:314为空串，二者不一致。负断言应拒绝无内容，不把"None"当答复。未声称真实供应商本轮返回过null。 |
| P03非字符串reply | parse_reply('{"reply":null}')；对照parse_reply('{"reply":"R2-OK"}') | :233将null转成"None"，:234未拒绝；对照为R2-OK。可另选数字175或对象{"text":"R2-OK"}；emotion/gesture非法值测试不等于reply类型断言。 |
| P04结构错误对照 | wire={"choices":[]}；另例wire={"choices":[{"message":None}]} | complete两者由:247映射ProviderError；with_tools空choices也映射，但message None在:307预计AttributeError。保留异常类型；不能任意异常都记作正确格式拒绝。 |
| P05空字符串对照 | message={"content":""} | complete应ProviderError空回复；with_tools为空content/空tool_calls。按调用方合同分列，不能“没调用工具”即判答复成功。 |
| P06内容块边界（可选） | content=[{"type":"reasoning","text":"R2-SYNTHETIC-NONPUBLIC"},{"type":"text","text":"R2-VISIBLE"}] | :250–255/:308–313只取dict.text，不按type过滤，预计拼入合成标记。该shape是否实际供应商生成未证实，仅检验白名单边界，禁止真实reasoning/隐私。另置顶层reasoning_content="R2-SYNTHETIC-NONPUBLIC"、content="R2-VISIBLE"应只产可见正文，区分不同字段。 |

parse_reply可用不启动Core的harness模块，不为反例修改parser。已有单个"{"失败已在旧审查复现，不再冒充新增。P02/P03/P04是最短独立候选，P06只是协议形状防御对照，未证实真实reasoning泄露。以实际AST复现须记录源码SHA、提取行号和mock边界；“零网络”不能成为将失败判PASS的理由。

本节交付为**夹具源码复审和复现设计**。新增候选待主执行复现后才能加入实证层，未完成项仍开放。没有扩大外部授权、触碰生产DB或启动Core。

## B01与隔离反例执行后的覆盖更新

本节补充前节设计的执行证据，不改原184分类/72历史层次，也不将其重新计为完整PASS。只读复核了browser-group1-trace/state、edge-counterfactuals-01、local-branches-01；主执行负责真实窗口/独立脚本，本实例没有重跑这些业务用例。

**先保留反例：** 无待办的继续在main.py:1490–1494仍生成“既有操作仍待确认”的system提示。trace Core23404 seq1242精确满足此输入；本实例从生产main.py只提取条件/赋值的纯内存AST已复现。模型seq1252确实输出无原生票据的待确认文本，但不能跳过更早的宿主错误状态描述而唯一归为模型。详见ADVERSARIAL_REVIEW新增I09；语句是否足以单独导致本次具体回答尚未做干预。

### 五个实际浏览器分支与未执行部分

| 原ID | B01具体实证 | 仍不可扩大 |
|---|---|---|
| M-mcp__browser__browser_navigate | request1292218，seq417授权调用/419 raw/420适配；URL为V3合成A页，标题正确 | 不包括其他协议、错误URL、重定向、back或B页导航；导航只给snapshot文件链接。 |
| M-mcp__browser__browser_resize | request1452487，seq666/668/669；1024×768设置回执，后续seq1121实际width/height读回一致 | 只有一组尺寸；不是所有窗口、DPI或移动视口分支。 |
| M-mcp__browser__browser_snapshot | request1593821，seq902/904/905；默认{}返回YAML正文、标题和节点引用 | 不包括target/depth/boxes等参数；也不证明独立resources/read通道。 |
| M-mcp__browser__browser_evaluate | request1731321，seq1119/1121/1122；准确title、starColor、全页innerText和auditState | numericValue字段实为全页字符串；只证明这段只读函数，不代表任意JS无副作用或隔离。 |
| M-mcp__browser__browser_find | 新任务1986553真实提案，2081817确认后seq1415/1417/1418返回文本蓝色纸鹤的2个匹配 | 不含regex、无匹配或定位参数其他分支；执行后最终reply仍错误称等待执行。 |
| M-mcp__browser__browser_hover / browser_console_messages | 原任务明确要求但B01无这两工具的实际调用 | 页面有按钮/控制台2 errors摘要不算操作成功；本节不覆盖正在进行的B02。 |

B01原多步任务并未全完成；单步对照能生成和执行find，但它改变用户措辞、task/cache、预算、system长度和历史，不能归因唯一变量。CF总结seq1335是finish_reason=stop的残缺JSON，seq1341格式fallback；确认后seq1423前文称已执行但JSON reply称等待执行，parser选择后者。不得把“工具成功”扩成“任务交付正确”。

### 原72及run_command的增量实证层

| 原ID / 关联项 | 本批新增证据 | 保留失败与具体缺口 |
|---|---|---|
| L-read_file | local分支有效64KiB边界、EOF、坏offset、缺文件；edge首字节41正常、ff时合法甲跨页额外损失 | RC14只限坏UTF-8与页边界组合；任意字节offset可能切进字符。有效UTF-8已有旧精确回归，不重跑。 |
| L-run_command（原184） | local十种mock结果含拒绝、返回码、argv/shell=False/30秒参数；edge同白名单下带空格exe目录误拒 | RC15是实际Windows分词差异，真实命令一概未执行；15秒外层timeout与30秒子进程期限仍不同。 |
| L-list_dir | local200条上限、目录先、f198终项、truncated=True | 单个合成目录排序/上限，非所有权限错误、链接或超大树。 |
| L-write_file | local四append、三拒绝无改动及replace异常对照 | RC17明确六字节tmp残留；matched观察成功不等于write_file清理正确。 |
| ME06 | local25条A+B会话隔离后A05..24精确20条；edge实际harness组装含system+20条、最新消息恰好一次 | 这是窗口及组装局部验证；全局记忆/system/task缓存不受20条限制，不能据此证明实际wire内容没有污染。 |
| UI空会话清理相关已有项 | local sweep后重查A25条内容、B唯一消息和会话保留 | 不扩大为生产损坏DB迁移修复；只使用独立临时库。 |
| PE03 / AD共享适配 | edge保留5 parser+12实际方法AST观察；null→"None"、数字→字符串、message None的异常类型差异；真实CF残缺JSON触发fallback | RC16候选已有主执行独立复现，不是业务修复；旧“单个{”的最早来源仍未查明；P06 typed reasoning合成边界本批未测试。 |
| TA06 / RC02 | B01无待办继续保留task/cache，但宿主同时注入错误待确认状态；新增I09纯内存对照 | 不能沿用“继续保持任务所以整个继续流程正常”的宽结论。无待办确认重建是不同分支，分别保留。 |

原设计C02/F02/P02/P03/P04及20条组装已有对应主执行观察，状态从“设计”更新为“已见指定隔离反例/对照”；未实施的默认latest-session、精确20→21界点、P06等仍是设计。没有借22个观察关闭整项能力。

### 证据数量、hash和诊断修订

browser-group1-trace明确8请求1274记录，13个唯一HTTP exchange一一配对，5次mcp.raw.out；state摘录覆盖会话360–367，有46消息、512事件、9actions、43累计HTTP尝试，不可全部计给B01。8轮final的task.calls_used包括重复提案/已执行回执复用，不能当远端调用数。人为听感仍未单项确认。

seq1249/1316工具schema hash相同、105工具且包含browser_find，可排除这两次缺schema。messages hash/shape却不同，system长度8825→3282，消息数12→14；只留整组规范hash不能读取具体confirm_note/记忆正文。raw_bytes_sha是过滤前响应字节，公开payload经reasoning删除和脱敏后不能再据它校验原raw。完整因果分析须沿“宿主构造上下文→原始响应→适配→解析→交付”逐段判断。

四项诊断修订已独立源码核对并保留处理结果：
1. 在agent_core导入前禁止写pyc，核对实际module路径；当前源文件hash与输出一致，只证明所选本地实现，不证明生产进程句柄身份。
2. sweep后实读A/B消息，补上原来只看清理前列表的弱断言。
3. command补返回语义、argv、shell=False和timeout断言；本实例只读实际截断输出亦为精确4000字符加后缀。
4. replace失败保留tmp名/字节数和清理责任，临时目录清理与write_file自清理分开。

edge脚本内嵌hash与当前脚本一致；local输出未记录脚本hash，当前0eb6f907…不能独自证明旧运行逐字节版本，新增观察字段及主执行运行记录可辅助关联。两者都只是独立实现层，不包含UI/WS/模型端到端。新增continuation_counterfactual脚本SHA975b8615…已仅代码审查通过（只提取条件/常量，五case，无Core导入/网络/DB、x模式报告），运行结果由主执行另记。

## 未启用与未实现项的分类闭合（不等于功能通过）

先保留两个容易误判的反例：NI06确实有Tauri程序，未接正式启动链不等于没有代码；AD03两种provider类确实支持reload_config，但正式factory没有传入callback，显式callback测试通过也不等于运行入口已启用。NI07有交付入口/校验模板，却没有任意电脑完全等效验收，不能混写为“未实现”或“已可移植”。

本节承接BRANCH_MAP_REVIEW.md:42–57的原10项与:122的新增factory边界；不是再次声明新发现。分类闭合表示已经能够准确说明当前入口、状态与缺失范围，原状态仍保留为“未启用或未实现”，不计PASS、不要求为凑覆盖启用这些能力。源码行号以审计副本为准；生产main的诊断overlay代际单列于后。

| 原ID | 可闭合的准确状态与证据 | 不能扩大的结论；是否仍需现场 |
|---|---|---|
| EF04 | 内部推理参数未接入。main.py:1387两模型映射为空且全Core没有消费点；:214–221/:266–275实际payload没有内部推理控制字段。3/6/9轮与6/12/18次是宿主任务预算。 | 三档UI/真实文件题成功只能证明预算和指定任务链；不能代验模型内部推理开关。已导出的observer采用字段白名单，单凭日志没有某字段不是通用缺省证明；本项以实际请求构造源码为依据。无需新增模型调用来确认缺入口。 |
| TA09 | Core独立资源桥接未实现。mcp_host.py:112–145仅initialize/tools/list/tools/call，:205–215只登记tool entries；Drive index.mjs:39–45有独立资源handler，而:125–145的search只给名字/MIME。 | 已有独立正文读成功、前台search明确读不到正文足以排除泛化OAuth/材料阻塞。不需再授权、再读一次来证明Core缺入口；不将独立连接器成功计为天依成功。 |
| VO05 | 有后台监听实现，manual明确禁用。main.py:735/:1810–1820启动时manual分支停止旧listener并返回，:1698拒绝wake处理；已通过的VoiceInputTests.test_manual_mode_never_opens_background_listener（test_harness_v1_integration.py:187）断言未构造listener且未调用chat。 | 此测试覆盖manual+无旧listener；有旧listener停止是本次静态依据，不冒充该断言已测。STATE记载持续manual，当前新Core代际是否disabled应附其既有health的wake.enabled/running=false或wake.disabled原因回执；本实例审过的公开导出未找到这条最新状态。只补已采回执，不开麦、不启后台唤醒。 |
| NI01 | 通用衣发/任意姿态无穿模未实现。MOTION_PIPELINE.md:27/:32/:34/:76明确有限姿态/动作合同及通用碰撞未解决；runtime.gd:1322–1432是有限修正。 | 750帧姿态门禁、有限动作或代理间距均不能证明任意服装/比例/动作。已有有限动作证据按各项保留；无需额外改模型/跑姿态来关闭“通用合同未实现”的分类。 |
| NI02 | 正式Windows登录自启入口未提供且所有者暂缓。HANDOFF.md:126；原cmd:3→start-mvp.ps1:50–52是手动会话链，仓内定向搜索未见登录注册合同。 | 会话守护不等于登录触发。不读注册表/计划任务、不重启电脑；只说项目无正式入口，不推论机器绝对不存在别的启动项。 |
| NI03 | pending审阅/编辑与遗忘UI未实现。storage.py:306/:333有内部方法；main.py:1353/:1515提供召回，WS/UI无对应事实审阅/遗忘入口；HANDOFF.md:122明确缺口。 | storage.delete_session:128–143只删消息/会话，不能冒充忘记facts。confirmed词法取代不等于pending近重复合并。隔离内部API可证明已有局部行为，但不会补出UI；无须读/删私人记忆。 |
| NI04 | 任意桌面键鼠代理未实现。HANDOFF.md:126/:138缓行；tools.py:448–545注册项无该入口。 | 浏览器工具与Godot自己的输入处理不是任意桌面控制。分类不需系统输入试验或新增权限。 |
| NI05 | Spark provider未实现。main.py:706–728仅glm/deepseek/stepfun，其他名称退Mock；HANDOFF.md:126一致。 | wiring隔离unknown→Mock不是Spark调用；avatar-spark CSS为装饰。无需Spark Key或外部服务。 |
| NI06 | Tauri代码存在，但正式链未启用此设置壳。apps/desktop/src-tauri/src/main.rs:3–6确有Builder；正式start-mvp:50–52→run-avatar-runtime:68–83启动Godot。 | 不能记成目录空/不能构建/从未在别处运行。入口分类无需另起Tauri或替换当前窗口。 |
| NI07 | 任意电脑完全等效交付仍未经认证。DELIVERY_STATUS.md:3提醒是历史交付快照，:27明确未验第二台/新系统/macOS/无NVIDIA；:31依赖受限本地资源。生产scripts/delivery/README.md:5–9描述候选布局/校验且不承诺复制即完整包。 | 交付代码存在，不归“无实现”。本轮可关闭未承诺范围登记，但积极可移植验收仍开放。若以后提出该目标，必须限定OS/硬件和另机/VM、模型/音频资源；不能以本机合成夹具代验任意电脑。 |

### 原256之外和原项新增子分支

| 补登记 | 分类结论 | 实证层与最短剩余工作 |
|---|---|---|
| NI-open_app（既有遗漏） | HANDOFF.md:126明确未做，工具注册无专用应用发现/定位/启动入口。 | 静态分类闭合；run_command能起进程不等于实现open_app合同。无需现场启动任意应用。 |
| BM-AD03-factory-reload（AD03新增入口子分支） | 类构造器支持reload_config（main.py:160/:170/:384/:393），401/403重载读取该值（:190–192/:504–506），正式build_provider:706–728未传入，源码没有后补赋值。 | 主执行wiring-counterfactuals-01的deepseek/glm/stepfun三个构造器spy均缺callback；正常provider类选择与无key/unknown→Mock控制齐全。仅闭合“factory未装配”；没有线上换key或运行对象检查。callback类级测试可继续沿用，但不得写成正式热重载通过。 |

HANDOFF.md:121另列高清连续录制、自适应画质、派生纹理未完成；portrait_capture.gd:34的UPDATE_ONCE与:53单次save_png不能用来冒充连续录像。这些是记录在案的路线图子缺口，本节不临时扩成新的必验产品承诺；通用碰撞与pending合并分别归NI01/NI03，避免重复计数。

只读复核wiring诊断脚本79767bd48302f06871f361d53022803675a491df6140b92c364a6aac70c642f3：导入前禁pyc、tools路径校验、fake User32/构造器、仅提取factory AST、x模式写新报告；不读真实窗口标题、配置秘密或DB，不启动Core/模型。本实例没有运行它，未发现新增阻断。证据SHA f5b279bc821f265c6fb6c638e893c30c98a7f3bedbd38d2d1f15035ee9e14c83内的main SHA7af0c89c…对应当前生产v3诊断代际，不能冒称仍与最初54文件逐字节相同。审计副本main为da3a01ce…；本实例只读提取两者build_provider，忽略坐标的规范AST hash均为d1466109468e162950d3c3e67f261955d7ba45b2b69ebcc28e411ae1665bb168。因此factory这项实现相同，不以全文件hash不同否定其证据，也不以函数相同保证其他代码不变。

同报告的active_window正常/失败替身观察属于L-active_window既有实现的缺陷实证，不能归入“未启用”来免除失败。其实际前台窗口/GPU/模型没有被本脚本调用。local-branches-script-provenance.json现补录执行后脚本hash，明确不是运行中加密绑定；已补来源说明，但不改前节原始report没记录script hash的事实。

### 剩余必须现场的最短清单（限定本节）

这12个状态登记不需要新增桌面操作即可按上述范围归档。唯一当前代际状态补项是VO05：从主执行已有health/启动事件附上wake禁用回执；若尚未导出，可在既定恢复核对时顺带采集，不为它启动监听。

全审计仍有启用功能现场链未闭合，不能由本节消除：主执行正在做的GLM同题/当前模型身份、授权连接器具体method/action前台执行、尚未实证的Godot UI/视觉入口，以及最后恢复原.env和移除诊断后的正式启动状态，仍按主账本逐项保留。已完成的三档文件题、真人录音/闲置、已确证工具分支和98旧断言无需为本节重跑。NI07的另机积极验收属于单独限定环境的后续承诺，不把当前审计变成新硬件部署任务。

本次仅增加分类闭合元数据；184原行、72已有证据行、256唯一ID、98既有断言引用及O/R/P/X/N数量均保持。初审仍开放，功能未实现不会因准确登记而变成已实现。


## Review Summary

原184行分类保持，原72个有实证ID已逐项追加，合计原256行全部唯一映射；47旧阻塞已拆解，原始状态未被改写。72行保留真实失败、历史/静态/局部断言的层次。新method组合、UI/WS方向缺口、弱断言和三个既有覆盖/评测反例仍需主执行者整合验收；只有本实例拥有的报告及同名JSON被修改。

| Severity | Count | Status |
|---|---:|---|
| CRITICAL | 0 | 无新增证实项 |
| HIGH | 0 | 无新增证实项 |
| MEDIUM | 3 既有覆盖/评测组 + 2 V3夹具偏差 + 1 I09宿主提示错误 | 指定隔离候选已复现，仍非整体PASS |
| LOW | 0 | 无样式项 |

Verdict: **覆盖审查仍开放；不批准“256项已验证”或“第二轮已完成”。** 代码级无HIGH/CRITICAL不改变能力验收证据不足；各O/R/P/X/N分类只能按其明确层次使用。
