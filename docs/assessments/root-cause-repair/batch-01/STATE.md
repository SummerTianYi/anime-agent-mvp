# Batch 01 STATE — 2026-10-12

实现基线 b2d871316b35287f17b0771dcd02212b4be2bb72。分支 codex/root-cause-repair-batch01-20261012。尚未桌面验收，不合并 main。

本机实现工作树：C:/Users/26052/Documents/Codex/2026-10-12/tianyi-repair-batch-01；TTS：同级 tianyi-tts-repair-batch-01，基线3814b4c9d32bb17c3638cf851e5649d9c7d17fa7。

已实现：无待办确认/继续分支；执行后模型/解析异常回执交付；ALLOW读取结果保存；MCP原始结果持久化/模型投影、Gmail业务/空/未知和GitHub method合同；物理路径判断、默认系统Desktop重定向；TTS日志UTF8/安全输出、确定性编码分类与排队健康复核。正式人格提示词、声线、权重、动作未改。自由reply无工具调用时的伪完成语义仍未完整治理，不得宣布此项闭环。

验证：基线362项通过；最终Core387项、TTS43项通过，DOCS_CONSISTENCY_OK。指定基线24项定向17失败/3缺新接口报错/4通过，候选24项通过，随后增加原始回执投影控制随387全套通过。主仓首次全套376项唯一失败是默认Desktop重定向，已修并验证。两位独立审查提出的只读摘要回退、method坏类型、确认标点、TTS混合排队健康、HTTP错误体中断及batch不确定副作用均已修并复核。原closure写入后读回失败/迟到worker探针已实际执行，见新证据。

生产目录未修改。主仓生产HEAD d3ed6d68f2509ad51bea15cf8224c5f3a165d957，85项dirty；TTS生产HEAD3814b4c9d32bb17c3638cf851e5649d9c7d17fa7，7项untracked。私有代码/配置备份在同级batch01-private/preflight-01；不提交任何私有材料。

数据门禁：preflight再次实测普通路径/UNC对应不同文件ID，未进入SQLite查询/备份，更未迁移/清库/写入。配置来源路径不能认作当前实例数据库。8765/8770 health本轮不可达；CIM未找到匹配进程，尚未看到桌面窗口，不能宣布天依当前可用或不在运行。桌面阶段按用户授权使用新的持久测试数据目录，保留旧聊天记忆，禁止将错身份库恢复或复制进活动库。

桌面阻塞：node_repl + @oai/sky启动报windows sandbox failed/helper_unknown_error/setup refresh had errors；已重置并重试一次仍失败，未绕过工具限制。没有启动或停止生产Godot/Core/TTS，尚未新开验收窗口。客户端恢复后先重新读computer-use指导和sky.list_windows，确认实例/正式链/身份，才能进入可见可听验收。用户无需查看日志或设计用例。

本轮真实模型、TTS/STT、Gmail/GitHub业务测试调用均0；只运行合成离线回归。保留前轮自有测试邮箱8封中剩余7封及登记专用GitHub对象授权；未清理旧对象。不要重跑259项。

版本：TTS已本地提交fb681d0a93bd6bd3d8b2785924dbaf264810dc5e；主仓本地候选SHA见Git HEAD/本轮交付答复。真实验收前遵守VERIFICATION_SPEC本地commit、不push门禁，未合并main。集中REPORT及脱敏证据已落盘；原始新测试日志转存batch01-private/raw-test-logs并按hash核对，旧审计材料未改。

最短下一步：客户端重启恢复桌面执行器后，以正式入口启动一个新Godot窗口、独立持久测试数据、同声线/模型配置；先短对话可见可听，再DS/GLM代表任务；持久聊天重新打开和重启验收必须真实完成才可标通过。不要重跑已通过离线用例；只有后续代码变化或新反例需要相应重测。
