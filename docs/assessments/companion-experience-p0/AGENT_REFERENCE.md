# 八千代任务链的静态核对与天依后续选项

读取所有者提供的完整安装目录，只分析六个指定的 CPython 3.13 代码文件。用独立的官方 CPython 3.13.9 核对 magic `f30d0d0a`，跳过 16 字节头，递归读取代码对象并用 `dis.get_instructions` 追踪函数实参、条件跳转、等待点和返回。未启动或导入参考程序。下文的 L 是编译文件保留的源码行，@ 是相应函数内字节码偏移。运行时模型决策、跨设备交付顺序、工具外部效果以及朋友的源码和服务均无实测证据。没有复制角色、提示词、代码或业务数据。

| 后端模块 | 文件 SHA-256 | 递归代码对象数 |
|---|---|---:|
| live_task_router | 90b5f29bc80dc1456dfba74b755c2001c8fd12976ac9038b35e0ad80b0ff9fa0 | 4 |
| main | e2dbf35723ce15baa7a0eb4f8d46826fc24d8d1e6b3c87ca0013a8d20f5c74f8 | 325 |
| platform_core | 308cef797a63661daf9552ba5498aa530964778389c396a86a446af739718a61 | 55 |
| task_control | 454279fa8bd2961c9874e91911b8fc93167d3c750b5720a02cf938bac139f8e8 | 14 |
| live_confirmation | 9bd95a3a3378ed2c3420b1c9c77bf2142fc3e686f8602a89eef2b138a39217be | 7 |
| agent_workflow | bcf15e2fffa86f35531f22e5b295969f6c0f9a26361aacede2e3949d005d8bdf | 69 |

## 原话、限制与分流

| 已确认机制与位置 | 天依现状 | 借鉴点、成本与风险 | 证据缺口 |
|---|---|---|---|
| 批量语音入口 `main.process_batch_voice_turn` L2576–2596 取最近对话，去掉与 spoken 重复的末条用户消息，按需补上下文。将 **spoken、工具定义、执行回调、历史、control** 传给 `route_live_task`；有待确认项就播报并返回，否则传 `application_result=result, dialogue_history=history` 给对话函数。路由器 L15–66 将最近最多八条历史和最后一条完整 text 组成请求。无 tool_calls 返回 None；有提案则核对数量、工具集合与参数类型，调用 execute(name, arguments)。两种检索任务另将 arguments.task 设回 text。 | 天依普通聊天已有本地分流，一次直接请求无工具正文。混合输入虽会落下完整原文，Agent 送模用 `route.operation`，单独的否定限制可能被切到聊天侧。 | 保留原话、作用对象、禁止条件及来源片段随任务一起进入规划和确认。只给现有任务信封补来源并增加入口对照，成本低至中等；不要给每句闲聊新增串行模型路由。 | 原话仅在所见路径保留，检索参数的特殊处理不能推广为所有工具均保留约束。 |
| `AgentWorkflow.handle_user_message` L439–494 先清理文本到 4000 字，按 task_id 取任务，追加 userMessages 和 conversation，记录 request，然后等待 `_interaction_decide(task,message)`。后者 L765–789 提供 brief、进度、最近 12 条对话并补当前原话。返回 chat、progress、cancel、ask_user 或 dispatch 后分别走对应分支。progress 读具体任务；ask_user/dispatch 用 `_merge_brief` L637–658 合并 goal、expectedResult、constraints 等数组，逐项去重并截断至 30 项。已有 goal 的特定追问会把 chat 改判 dispatch；决策缺失且有 goal 时也有 dispatch 回退。 | 天依解释性问答仍有误入任务的改述，已有账本负责真实状态。 | 在已有明确动作入口和执行前都校验用户说的是请求、询问还是限制；普通换话题保留原任务。不要用“已有目标”自动补新授权。工作量中等，错误分类直接影响安全边界。 | brief 来自模型且有限长，没看到逐条证明每条否定限制都保真。 |
| `AgentPlatform.create_task` L395–412 把限制长度后的 prompt 和 slot、connector、独立 ID、状态存入任务；连接就绪产生 queued，否则 awaiting_config。`ToolRegistry.execute` L210–224 先调用 guard(name,arguments)，被阻止则直接返回，之后才取 handler 并 await。普通值有 completed 包装。 | 天依已有批准、派发和产物读回。 | 统一使用已有 taskId/原始意图传递，不把“返回普通值”升级成核验成功。需要针对具体工具验证执行与交付。 | 这些状态本身不证明外部真实完成。 |

## 取消、确认与执行边界

| 已确认机制与位置 | 天依现状 | 借鉴点、成本与风险 | 证据缺口 |
|---|---|---|---|
| `route_live_task` L7 @6–116 先认 stop_requested 且当前定义存在 task_stop，直接 await execute 处理停止。普通路径 @118–330 取 stamp，写入 kind=voice 和新 ID，在 task_scope 内进入路由。进度工具 swarm_status 的特殊后续只接受从查询结果取得的 job_id，校验后才允许一次 swarm_cancel（L67–96）。 | 天依有待办或活动任务时先检查控制意图，但某些“作罢／别寄”表达没有进入取消。 | 将原话解释、范围选择、撤权结果分开；同会话指向唯一才撤权。成本中等，必须保留引述、否定与其他会话的反例。 | 参考停止短语的实际覆盖率、模型对模糊指向的效果未知。 |
| `TaskControl.halt/allow_new` L34–44 更改 epoch；`cancel(kind,id)` 单列取消项。blocked L48–52 依次核对 halted、epoch、(kind,id)；stamp_operation 保留原标记。`AgentWorkflow.cancel` L547–565 标记 cancelRequested、取消 runner 并等待，on_cancel 继续清理归属项。`main.cancel_owned_tasks` L933–938 依操作 stamp、浏览器槽 ownerKind/ownerId 清理对应项。`AgentWorkflow._call_tool` L1195–1222 取得执行槽后查取消、绑定任务 epoch，再传 agent/name/arguments 给 execute，等待批准后重查取消。`main.execute_reviewed_operation` L1260 @6–66 在执行回调之前检查原操作标记。 | 天依已有票据版本、确认、撤权与派发前校验。用户取消未入路由时，这些保护接不到信号。 | 复用现有账本和票据，在排队获准、实际派发、等待结果之后验证归属。按任务撤权；已派发只报告真实状态。增加代际比较成本中等，需要保护正在执行的副作用。 | 进程内取消集合与可持久化的 halted/epoch 不同；无证据证明所有外部业务可回滚或重启后逐项取消可恢复。 |
| `LiveConfirmation.begin` L27–30 把语音序号与当前且已宣读的 (approvalId,challenge) 绑定。finish L33–61 消费序号、拒绝重复/陈旧录音，通过音频检查及转写后优先处理停止，否则在调用 confirm 前再次核对绑定与已宣读项。 | 天依已经绑定确认对象与参数版本。 | 可以移植“等待的两侧重新核对所有者”的方法，保留已有确认体验，增加少量竞态测试。 | 无参考实机录音，不给它的识别准确率或语音鉴权效果定级。 |

## 任务回执与旧语音

| 已确认机制与位置 | 天依现状 | 借鉴点、成本与风险 | 证据缺口 |
|---|---|---|---|
| `AgentWorkflow._deliver_user` L695–703 将 taskId、kind、text、status、statusLabel 交给 deliver，捕获异常并返回。`main.deliver_workflow_message` L5412–5425 将工作流消息按 kind 发布，带 taskId/status；随后也调用 **set_reply(text, source=workflow)**。set_reply L1750–1760 会更新全局字幕/回复编号，并加入 assistant 对话历史。`AgentPlatform.publish_reply` L586–594 发布角色回复事件。 | 天依已用独立 task/memory 回执和会话归属；新建页等待真实 ID 时仍有接收旧回执的窗口。 | 借鉴结构化类型与归属，保留天依独立气泡。新会话确认中拒收未绑定回执，旧结果仍归旧历史。低至中等成本，须覆盖快速连点、历史加载。 | 参考后端存在写入共同回复状态的直接证据；前端是否进一步隔离所有事件、投递失败能否恢复，未知。 |
| `main.schedule_windows_reply` L1764–1768 捕获 expected_reply_id。`generate_and_play_reply` L2828–2843 在合成前及等待后核对编号。play_prepared_reply L2883–2911 捕获编号和字幕，取消时设置线程事件，结束清理须核对归属。play_audio_on_windows L2924–2936 把取消事件传入播放路径。 | 天依按 utteranceId/playbackId 去重，普通播报检查所有者；`_broadcast_speech_recovery` 的错误通知缺少会话及前台标记。 | 所有异步通知沿用来源 turn/session/utterance，切会话后留后台，不更新当前角色或气泡。增加发送与消费两处验证，成本低至中等。 | 参考的回复编号是全局值；看不到足够证据证明跨设备、跨会话的每个迟到音频帧都失效。 |

优先选项是先修三条会影响操作意图的入口，使用合成账本验证“原话及禁止条件到达执行边界”；随后修新会话过渡期和语音恢复通知的归属。五项各自验收。整套克隆参考路由会增加串行请求，复制完整共享回复通道还会重新引入消息串扰，两种方案本轮均未采用。
