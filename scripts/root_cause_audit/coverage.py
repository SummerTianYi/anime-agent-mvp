"""Codex: exhaustive registered-surface inventory, never infer PASS from registration."""
import ast,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/assessments/root-cause-audit'
CORE='services/agent-core/agent_core/'
rows=[]
def add(id,name,source,expected,method,enabled='yes',status='待验证',evidence=''):
    rows.append(dict(id=id,name=name,source=source,enabled=enabled,expected=expected,
                     verification=method,status=status,evidence=evidence))

groups='''
AD01|DS主脑|main.py:OpenAICompatibleProvider|共享契约和工具；当前准确ID Deepseek-v4-flash|当前窗口RA-01/F01/G01
AD02|GLM主脑|main.py:_provider_config|GLM-5.2使用同一微信网关/凭据来源|同条件原窗口对照，配置切换需正常重启
AD03|模型配置热重载|main.py:_reload_provider_config|凭据更换后受限重载，不把Key发往不同host|离线配置/传输测试；不人为破坏生产Key
AD04|传输恢复/截止时间|provider_http.py|直连/代理明确；有界重试与错误交付|既有provider_resilience回归，真实故障不注入生产
AD05|工具协议降级|agent_loop.py|不支持工具时明确降级，保留已执行证据|离线unsupported/400/422反事实
AD06|Anthropic视觉适配|main.py:AnthropicCompatibleProvider;tools.py|qwen3.8-flash视觉结果是资料，不代替主脑|配置/源码；仅合成画面才可前台视觉测试
EF01|碎碎念低投入|main.py:EFFORT_LEVELS|3轮6次工具；同权限/人设|前台选择+事件；离线预算
EF02|帮帮忙中投入|main.py:EFFORT_LEVELS|6轮12次工具；同权限/人设|前台选择+事件；离线预算
EF03|大展身手高投入|main.py:EFFORT_LEVELS|9轮18次工具；同权限/人设|前台选择+事件；离线预算
EF04|模型内部推理控制|main.py:MODEL_REASONING_CONTROLS|当前无已确认参数，不冒称已控制内部推理|源码检查，不擅自启用
PE01|共享角色与运行合同|harness.py:CharacterHarness|角色/任务/记忆分层，不虚构身体与能力|前台问答+旧P01/P02反例
PE02|原创曲检索|song_catalog.py;data/luotianyi_original_songs.json|仅检索匹配资料，不冒称会播放或演唱|离线匹配+前台角色问答
PE03|结构化解析|harness.py:parse_reply|坏JSON不泄漏原始碎片，不伪交付|RA-G01及离线边界
TA01|动作参数票据|actions.py|action/revision/hash/confirmationId绑定|原窗口G01；旧证据校准+隔离伪造票据
TA02|拒绝/取消|actions.py:decision;main.py:handle_chat|取消未执行任务，不撤回已发出I/O|原窗口取消/离线并发
TA03|改参|actions.py;main.py:_handle_chat_locked|旧参数票据失效，新参数重新确认|前台合成文件+隔离旧票据反例
TA04|多待办|actions.py|同名不同参数动作不覆盖，逐项确认|前台双文件+隔离账本
TA05|失败/未知/防重|actions.py;main.py:_receipt_delivery|未知不重试；失败不报完成|隔离假连接器；原窗口真实失败
TA06|任务连续性|main.py:_handle_chat_locked|确认/续办保留原意和已取证资料|RA-F01/F02与最小反事实
TA07|长结果缓存|result_pages.py|2K分页、4Mi字符上限、任务隔离|原窗口G01+离线首尾/越界
TA08|MCP resource正文|mcp_host.py:_call_locked|embedded resource正文不丢|RA-G01真实回执+离线resource对照
TA09|MCP独立资源读取|mcp_host.py;tools/gdrive/index.mjs|Drive resources/read存在服务端，但宿主未暴露|静态双端追踪，不把搜索摘要算正文
TA10|资料注入边界|harness.py;agent_loop.py|资料不能授权或改写用户目标|旧F09反例+隔离合成文本，不攻击私有数据
ME01|消息/事件持久化|storage.py|会话读回与当前实例一致，结构完整|稳定main+WAL只读检查，禁止清库
ME02|记忆保存/晋升|storage.py;main.py:_fact_promotion_status|明确保存须有fact回执，不只口头承诺|合成RA-R01；旧R02
ME03|记忆更正|storage.py:add_fact|新事实生效，旧事实标superseded，不误伤其他属性|合成跨会话+离线相似度对照
ME04|记忆召回|memory_retrieval.py|区分未召回与未保存，按任务检索|旧R03语义复核+离线召回
ME05|敏感记忆策略|storage.py:_pending_recallable;main.py:_fact_promotion_status|显式保存敏感信息与普通全局模型上下文的边界需Manager裁决|仅合成秘密离线测试
ME06|上下文窗口|main.py:MAX_HISTORY_MESSAGES;harness.py|20条聊天与工程任务证据边界明确|源码/反事实，不读取私人历史
VO01|手动录音|main.py:websocket_endpoint;voice.py|只由语音按钮开启，用户审阅后发送|原窗口真人待确认+离线事件
VO02|STT简体及精确内容|stt_input.py|本地转换保护英文数字路径|离线样例与真人回填
VO03|取消/切会话/旧录音|stt_input.py:CaptureState;main.py|代际失效；旧结果不回填|离线代际+前台切会话
VO04|空录音|main.py:handle_voice_transcription|只轻提示，无聊天/记忆/LLM|原窗口短空录音，后台关联检查
VO05|后台唤醒|wake_word.py;main.py:start_wake_word_listener|manual模式彻底停监听|当前health及源码，禁擅自开启
VO06|STT故障自愈|voice.py;wake_word.py|驱动数字零检测/有界恢复|隔离既有测试；不破坏真实音频驱动
TT01|合成/分片|speech.py;../tianyi-tts/scripts/tts_server.py|真实声线合成并分片交付|原窗口RA-01/F01播放回执
TT02|播放回执/补送|speech.py;apps/avatar-runtime/runtime.gd|utterance/playback绑定，失败有界恢复|原窗口回执+隔离故障
TT03|打断|speech.py;main.py:websocket_endpoint|新输入/换会话停止旧语音|原窗口消息/会话切换+回执
TT04|退出告别|speech_cache.py;apps/avatar-runtime/farewell_exit.gd|缓存音频与动画共同结束，超时可退出|已有冻结证据；本轮若重启再验
TT05|TTS看护|scripts/watch-tts-session.ps1;../tianyi-tts/scripts/service_health.py|定向PID恢复/退出释放，不误杀|静态追踪+既有隔离证据；本轮不杀生产
PR01|上线问候|main.py:_proactive_greeting|本地台词；尊重免打扰及忙碌|重启时前台观察或旧证据
PR02|600秒闲置一次|main.py:_proactive_idle;proactive.py:IdlePolicy|同闲置段不重复，活动后重计，零LLM|离线边界；真实连续600秒待体验
PR03|播放前复查|main.py:_broadcast_speak|01:00-07:00/活动/忙碌复查，续片不误拦|配置+离线分段边界
LC01|正式入口/幂等启动|scripts/start-mvp.ps1;start-anime-agent.cmd|同数据/同配置，已有健康实例不多开|运行PID/路径/哈希；本轮不凭旧PID
LC02|Core守护/退出|scripts/core_watchdog.ps1;scripts/startup-common.ps1|窗口生命周期绑定，不按进程名杀|实际脚本定位+既有测试；不在线注入故障
LC03|数据身份与恢复|storage.py:default_data_dir|包内外进程同路径应指同数据库|namespace+WAL反事实；只读保全
LC04|部署overlay一致性|scripts/harness_v1/activation_snapshot.py|工作树/候选/运行文件哈希分开|runtime-start与新现场manifest
EV01|评测事实与回执关联|scripts/harness_v1/grader.py|实际产物/授权/回执，拒绝不能冒充能力|旧证据离线重判/反例
EV02|语义等价和虚报|scripts/harness_v1/grader.py|18日/18号等价；矛盾声明不判绿|旧R03/P01/P02+合成反例
EV03|README/AGENTS/HANDOFF/SPEC/TESTING|docs/HANDOFF.md;AGENTS.md;docs/TESTING.md|日期版本范围一致，旧证据不代表现场|静态逐项差异清单
EV04|本轮取证器可靠性|scripts/root_cause_audit/probe.py|文件集合和副本哈希校验；请求关联不依赖消息行|5项自测与独立反例，非原子快照保证
TA11|成功到实质答案的合同|main.py:_receipt_delivery;harness.py:parse_reply|成功回执必须交付所问结果而非符号或将来时|RA-G01/G02/G03与隔离反事实
TA12|method型工具变更分类|main.py:_receipt_delivery|不能用工具名称子串代替method实际副作用|issue_write(create/update)与write_file控制
TA13|无待办确认状态矩阵|main.py:_handle_chat_locked|任务/预算/缓存/聊天历史分别记录|确认与继续反事实及RA-F01/M02
TA14|协议/业务/交付三种成功|mcp_host.py;actions.py;main.py:_receipt_delivery|isError缺省/真假/顶层error分别保留真实错误|8个合成回执及合法Error资料控制
TT06|内容确定性故障与恢复分类|speech.py;../tianyi-tts/scripts/tts_server.py|emoji编码错误不应反复重启重发同片段|现场TTS异常及gbk/utf8离线对照；未修
ME07|更正作用域与保存承诺|main.py:_fact_promotion_status;storage.py:add_fact|保存更正的实际scope/status与承诺一致|RA-R01/R02/R03及同candidate措辞反事实
'''
for line in groups.strip().splitlines():
    id,name,source,expected,method=line.split('|')
    source='; '.join(CORE+s.strip() if '/' not in s.strip().split(':')[0] and s.strip().split(':')[0].endswith('.py') else s.strip() for s in source.split(';'))
    add(id,name,source,expected,method)

local=['get_time','read_file','list_dir','screenshot','active_window','clipboard_read','look_at_screen','run_command','write_file']
for name in local:
    status='前台部分验证' if name=='read_file' else '前台失败' if name=='write_file' else '待验证'
    ev='evidence/desktop-03.json' if name=='read_file' else 'evidence/desktop-03.json; evidence/desktop-05.json' if name=='write_file' else ''
    add('L-'+name,name,CORE+'tools.py; '+CORE+'permissions.py','依schema/根目录/确认执行；核对产物而非调用名','受控本地夹具；隐私工具不触碰真实私人画面/剪贴板',status=status,evidence=ev)
for name,source in [('read_tool_result','result_pages.py'),('recall_memory','main.py:run_tool')]:
    add('L-'+name,name,CORE+source,'仅当前任务缓存或授权可见记忆','隔离合成材料；前台关联')
schema=json.loads((OUT/'evidence/mcp-schema.json').read_text(encoding='utf-8'))
readonly_tools=set()
for server in schema['servers']:
    for tool in server['tools']:
        name='mcp__'+server['server']+'__'+tool['name']
        if tool.get('annotations',{}).get('readOnlyHint') or server['server'] in ('browser','search'):
            readonly_tools.add(name)
        locator={'browser':'installed @playwright/mcp (npx offline cache)','search':'installed tavily-mcp (npx offline cache)','github':'tools/github-mcp-server.exe (local ignored binary)','gmail':'tools/gmail-mcp.cmd -> installed @gongrzhe/server-gmail-autoauth-mcp@1.1.11','drive':'tools/gdrive/index.mjs'}[server['server']]
        add('M-'+name,name,CORE+'mcp_host.py; '+CORE+'permissions.py; '+locator,
            tool.get('description','').split('\n')[0][:180],
            '逐项schema已登记；共享initialize/ASK/回执实现；真实操作另需指定对象，不将tools/list当鉴权成功',
            status='待验证',evidence='evidence/mcp-schema.json')
for clip in json.loads((ROOT/'apps/avatar-runtime/motion_registry.json').read_text())['clips']:
    add('AN-'+clip['id'],clip['id'],'apps/avatar-runtime/motion_registry.json; apps/avatar-runtime/runtime.gd',
        '按注册role/layer播放；不改变官模比例，不承诺通用防穿模','菜单/状态触发；本地资产SHA及既有验收',status='待验证')
tree=ast.parse((ROOT/CORE/'main.py').read_text(encoding='utf-8'))
events=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='AVATAR_EVENTS' for t in n.targets))
for event in sorted(events):
    add('AV-'+event,event,'apps/avatar-runtime/runtime.gd; apps/avatar-runtime/emotion_presets.gd',
        '仅允许注册事件，表情/动作与语义对应','同源handler静态枚举，逐个视觉体验不得用注册代替')
for name,expect in [('menu','点击打开聊天/互动'),('text','文本正常输入/显示/发送'),('history','旧会话回载'),('new-session','新会话不清旧历史'),('switch','切会话不串回填/播放'),('delete','删除需明确授权；本轮不删'),('search','历史分组/筛选'),('effort','三档名称/事件正确'),('tool-card','真实动作及票据可见'),('voice-button','手动录音/取消'),('drag','拖动位置保持'),('scale','缩放保持比例'),('turn','转身/回正'),('portrait','F12输出透明截图'),('exit','告别后正常退出')]:
    add('UI-'+name,name,'apps/avatar-runtime/interaction_ui.gd; apps/avatar-runtime/runtime.gd',expect,'原窗口现场+现有Godot守卫分列')
for id,name,source in [('NI01','通用全身无穿模','docs/MOTION_PIPELINE.md'),('NI02','Windows登录自启','docs/HANDOFF.md'),('NI03','待审记忆UI/遗忘入口','docs/HANDOFF.md'),('NI04','键鼠自主控制','docs/HANDOFF.md'),('NI05','Spark适配器','docs/HANDOFF.md'),('NI06','Tauri设置壳','apps/desktop'),('NI07','任意电脑完全等效部署','docs/DELIVERY_STATUS.md')]:
    add(id,name,source,'不把计划/实验当已实装','文档/入口交叉核对',enabled='no',status='未启用或未实现')
for r in rows:
    if r['id']=='AD02': r['enabled']='tested via formal entry, restored inactive'
    if r['id'] in ('EF04','TA09'): r['enabled']='no';r['status']='未实现'
    if r['id']=='VO05':r['enabled']='no';r['status']='当前明确禁用';r['evidence']='evidence/runtime-start.json'
    if r['id']=='M-mcp__github__get_file_contents': r['status']='前台部分验证';r['evidence']='evidence/desktop-06.json';r['verification']='原窗口已执行且正文完整，但最终仅显示{，任务失败'
# A protocol event is its own capability surface; registration is not acceptance.
surface=json.loads((OUT/'evidence/surface-inventory.json').read_text(encoding='utf-8'))
for route in surface['routes']:
    add('IPC-'+route['kind']+'-'+route['name']+'-'+route['handler'],route['kind']+' '+route['name'],CORE+'main.py:'+str(route['line']),
        '遵守入口数据/生命周期合同；无鉴权入口只限本机信任边界','静态入口+既有隔离回归；禁止在线故障注入',evidence='evidence/surface-inventory.json')
for event in surface['websocket_input_types']:
    add('WS-'+event,event,CORE+'main.py:websocket_endpoint','按角色/会话/代际处理；不把client.hello自报role当强鉴权',
        '逐项事件映射到前台或离线场景；未发送事件不算前台通过',evidence='evidence/surface-inventory.json')
for item in surface['mcp_enum_methods']:
    if item['argument'] not in ('method','action','event'): continue
    for value in item['values']:
        add('METHOD-'+item['tool']+'-'+str(value),item['tool']+' '+item['argument']+'='+str(value),
            CORE+'mcp_host.py; '+CORE+'main.py:_receipt_delivery','按实际method识别副作用；每个操作需要具体测试对象',
            'schema逐method枚举；授权/回执共享实现另有隔离对照，真实业务写入未经批准不执行',
            status='阻塞：无该method的明确真实测试对象/授权',evidence='evidence/surface-inventory.json; evidence/receipt-counterfactuals.json')
        if item['tool'] in readonly_tools:
            rows[-1]['status']='仅静态已枚举，当前前台该分支未验证；不是已证实权限不足'

validated={
 'AD01':('前台已验证，存在失败','desktop-03.json; desktop-27.json'),
 'AD02':('当前桌面真实GLM对照已完成；非全面模型排名','desktop-37.json; desktop-41.json; runtime-glm-confirmed.json'),
 'EF01':('前台已验证低档能用工具','desktop-30.json'),
 'EF02':('前台已验证档位；文件任务失败','desktop-31.json; desktop-32.json'),
 'EF03':('前台已验证高档；任务有成功和失败','desktop-25.json'),
 'PE03':('已证实缺陷','review-reproduction.json; desktop-06.json'),
 'TA01':('前台+离线已验证绑定路径，不宣称穷尽','desktop-25.json; offline-suite.json'),
 'TA05':('已证实业务错误误成功','receipt-counterfactuals.json; desktop-08.json'),
 'TA06':('已证实连续性缺陷','review-reproduction.json; desktop-20.json'),
 'TA07':('离线已验证；真实长结果交付失败','offline-suite.json; desktop-06.json'),
 'TA08':('前台已验证正文传入，不等于答复成功','desktop-06.json'),
 'TA10':('历史反例+本轮离线回归；当前前台未做攻击','offline-counterfactuals.json'),
 'ME01':('已证实所检视图异常，源因果未定','inventory-start.json; runtime-owner-restarted-confirmed.json'),
 'ME02':('前台保存成功控制','desktop-28.json'),
 'ME03':('前台更正失败；另有隔离错覆盖','desktop-29.json; offline-counterfactuals.json'),
 'ME04':('前台调用成功且最终答旧值；工具正文未记录','desktop-30.json'),
 'ME05':('隔离已验证实际策略；取舍待Manager','offline-counterfactuals.json'),
 'ME06':('静态+隔离已验证，非raw wire全量证明','review-reproduction.json'),
 'ME07':('前台+隔离已证实scope偏差','desktop-29.json; desktop-30.json; memory-correction-counterfactual.json'),
 'TT01':('前台有成功及内容相关失败','desktop-01.json; tts-encoding-counterfactual.json'),
 'TT02':('前台有播放回执和180秒超时','desktop-10.json; desktop-27.json'),
 'TT03':('前台换会话及新消息打断；听感未逐条确认','desktop-28.json'),
 'TT04':('正常关窗退出已观察；本轮告别听感未确认','runtime-owner-restarted-confirmed.json'),
 'TT05':('已观察重启循环；隔离/静态机制验证','runtime-before-reload.json; tts-encoding-counterfactual.json'),
 'TT06':('高置信机制，live编码与完整栈仍待补','tts-encoding-counterfactual.json'),
 'LC01':('所有者原入口重启成功；命名空间风险','runtime-owner-restarted-confirmed.json'),
 'LC02':('正常退出/重启已观察；故障仅离线','runtime-owner-restarted-confirmed.json'),
 'LC03':('数据身份差异已观察；损坏来源未定','runtime-start.json; inventory-start.json'),
 'LC04':('磁盘匹配清单已核对；非内存源码证明','runtime-start.json'),
 'EV01':('离线重判已完成，判据仍有反例','offline-counterfactuals.json'),
 'EV02':('已证实旧判据不足，不改原分','offline-counterfactuals.json'),
 'EV04':('5自测通过；修的是取证器非业务','review-reproduction.json'),
 'TA11':('已证实交付缺口','review-reproduction.json; desktop-15.json'),
 'TA12':('已证实method分类遗漏','review-reproduction.json'),
 'TA13':('状态矩阵隔离已验证','review-reproduction.json'),
 'TA14':('8回执反例及成功控制已验证','receipt-counterfactuals.json'),
 'M-mcp__gmail__search_emails':('前台OAuth失败与重登后成功/空结果缺口','desktop-08.json; desktop-18.json'),
 'M-mcp__gmail__send_email':('一次真实发信成功；先前无动作虚报保留','desktop-20.json; desktop-25.json'),
 'M-mcp__gmail__read_email':('前台定向真实读回正确','desktop-27.json'),
 'M-mcp__github__issue_write':('前台create成功但最终未交付完成','desktop-12.json'),
 'M-mcp__github__issue_read':('前台get成功但回答损坏精确日期','desktop-15.json'),
 'L-get_time':('前台时间工具成功','desktop-30.json'),
 'L-recall_memory':('前台调用成功且最终答旧值；工具正文未记录','desktop-30.json'),
 'M-mcp__drive__search':('前台已执行，OAuth invalid_grant；正文未读取','desktop-35.json; drive-fixture-provenance.json'),
 'METHOD-mcp__github__issue_write-create':('前台create成功但最终未交付完成','desktop-12.json'),
 'METHOD-mcp__github__issue_read-get':('前台get成功但回答损坏精确日期','desktop-15.json'),
 'PE01':('DS/GLM前台相同角色样例；非跨模型全通过','desktop-36.json; desktop-37.json'),
 'PE02':('双模型推荐匹配内置曲库；曲库事实来源未独立确证','desktop-36.json; desktop-37.json'),
 'L-write_file':('DS口头待办失败；GLM原生确认后产物正确','desktop-04.json; desktop-41.json; artifacts-final.json'),
 'EV03':('已证实部署旧effort守卫/文档当前与历史混杂','godot-guards.json; godot-speech-fixture-corrected.json'),
 'UI-history':('原窗口重启后旧审计会话可见；未读取私人历史','runtime-glm-confirmed.json'),
}
offline_ids={'AD03','AD04','AD05','TA02','TA03','TA04','VO01','VO02','VO03','VO04','VO06','PR02','PR03'}
ui_seen={'menu','text','new-session','switch','effort','tool-card','exit'}
for r in rows:
    ident=r['id']
    if ident in validated:
        r['status'],ev=validated[ident];r['evidence']='; '.join('evidence/'+s.strip() for s in ev.split(';'))
    elif ident in offline_ids:
        r['status']='离线既有回归已验证；当前前台边界未全部覆盖';r['evidence']='evidence/offline-suite.json'
    elif ident.startswith('UI-') and ident[3:] in ui_seen:
        r['status']='前台观察到基本路径；边界未穷尽';r['evidence']='evidence/desktop-27.json; evidence/runtime-owner-restarted-confirmed.json'
    elif ident.startswith('AN-'):
        r['status']='资产哈希已核对；本轮未逐段视觉验收';r['evidence']='evidence/artifacts-after-file-tests.json'
    elif ident.startswith('M-'):
        r['status']=('仅静态已枚举，当前前台该操作未验证；不是已证实权限不足' if ident[2:] in readonly_tools
                     else '阻塞：未指定该业务写入/私人对象的授权范围；仅schema/共享协议核对')
    elif ident=='AD02':r['status']='当前桌面未验证：需受控原入口切换/重启；历史双模型证据另列'
    elif ident=='AD06' or ident in ('L-screenshot','L-active_window','L-clipboard_read','L-look_at_screen'):
        r['status']='阻塞：当前真实桌面/剪贴板含非测试私人内容；仅隔离验证'
        r['evidence']='evidence/offline-suite.json; evidence/runtime-start.json'
    elif r['status']=='待验证':
        r['status']='仅静态已枚举，功能待验证'
        r['evidence']=r['evidence'] or 'evidence/surface-inventory.json'
    r['bucket']=('未启用或未实现' if r['enabled']=='no' else '阻塞' if r['status'].startswith('阻塞') else
                 '功能未验证' if r['status'].startswith(('仅静态','当前桌面未验证','资产哈希')) else '有实证（按层次，非全部通过）')
assert len({r['id'] for r in rows}) == len(rows), 'Coverage ID collision'
out=OUT/'coverage.json'
out.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
from collections import Counter
counts=dict(Counter(r['bucket'] for r in rows))
lines=['# 能力覆盖清单 — Codex审查登记','',
    '逐项枚举不是通过表。前台、离线、静态证据分层；“待验证”不计通过。MCP条目仅tools/list成功不能证明账号权限或操作成功。',
    '范围：实际注册表94工具、HTTP/WS入口、MCP method分派、UI/语音/任务/资产及明确未实装项。不是所有功能通过；static/离线/前台不混算。完整schema与184个Godot handler见 evidence/mcp-schema.json、evidence/surface-inventory.json。',
    '分布：'+json.dumps(counts,ensure_ascii=False)+'。有实证含失败和离线机制验证，不能理解为前台PASS。','',
    '| ID/能力 | 实现位置 | 启用 | 预期 / 验证 | 状态与证据 |','|---|---|---|---|---|']
for r in rows:
    vals=[r['id']+' / '+r['name'],r['source'],r['enabled'],r['expected']+' / '+r['verification'],r['status']+' '+r['evidence']]
    lines.append('| '+' | '.join(v.replace('|','/').replace('\n',' ') for v in vals)+' |')
(OUT/'COVERAGE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(dict(total=len(rows),mcp=sum(r['id'].startswith('M-') for r in rows),distribution=counts),ensure_ascii=False))
