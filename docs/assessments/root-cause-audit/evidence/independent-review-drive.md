本轮零 API、零文件修改；仅执行源码切片＋内存 stub。结论限于以下5项：

1. **OAuth 阻塞证实，但不能归因到文件权限或资源桥。** [desktop-35:485](desktop-35.json#L485) 是 `ok:false / invalid_grant / failed`，最终回复也正确告知失败。该次尚未到正文读取，不能证明文件不存在、ACL 拒绝或 resource handler 故障。ChatGPT 上传/readback 只证明其集成身份可访问；[provenance](drive-fixture-provenance.json#L1) 不证明桌面使用相同账号、令牌或 scopes。令牌失效的具体原因仍待验证。

2. **独立资源桥缺失证实；“重新授权即可读正文”过强。** [Drive handler:125](../../../../tools/gdrive/index.mjs#L125) 把 ID 转成 `fullText contains 'ID'`，不是按 ID 定向读取；成功结果也只输出名称、类型，连已取到的 ID 都未返回。正文入口在同文件42行，而[宿主:139](../../../../services/agent-core/agent_core/mcp_host.py#L139)固定发送 `tools/call`。已离线运行真实 handler，固定合成文件 `F` 存在且授权成功：

   ```js
   await h["tools/call"]({params:{name:"search",arguments:{query:"F"}}})
   // isError:false；仅 "Found 1 files:\nfixture.txt (text/plain)"

   await h["resources/read"]({params:{uri:"gdrive:///F"}})
   // contents[0].text === "BODY=synthetic"

   await h["tools/call"]({params:{name:"resources/read",arguments:{uri:"gdrive:///F"}}})
   // 抛出 "Tool not found"
   ```

   因而 OAuth 错误与桥缺失是独立阻碍；当前失败不能算桥缺失的线上复现。生产与工作树此文件去除 CRLF 差异后相同。

3. **coverage 存在确定误标。** [coverage.py:117](../../../../scripts/root_cause_audit/coverage.py#L117) 将所有 method 默认标为“无对象/授权”，后续只覆盖父工具行，导致已有 desktop-12/15 实测的 `issue_write/create`、`issue_read/get` 仍被标阻塞。[Drive 行:1774](../coverage.json#L1774)也仍称“未指定对象”，与新增 fixture、desktop-35 冲突。应分别表述为“执行成功但交付失败”和“已执行、OAuth 失败”，不能统一归为未授权或未测。

4. **method 清单仍漏重要操作分支。** [coverage.py:118](../../../../scripts/root_cause_audit/coverage.py#L118) 只展开 `method/action`，跳过 `event`。[schema:2969](mcp-schema.json#L2969)明确：`pull_request_review_write(method=create)` 不带 event 创建待审稿；带 `event=APPROVE` 则直接提交批准。两者同一个 METHOD 行，却有不同外部效果。此为可确认的分支覆盖遗漏，不是声称真实执行失败。

5. **显式 HTTP/WS 入口未发现漏项，但登记 ID 冲突。** 源码对照覆盖了3个显式 HTTP 路由、1个 WS 路由和14类输入事件；这不等于参数、角色、失败分支已覆盖。[coverage.py:112](../../../../scripts/root_cause_audit/coverage.py#L112)以 `kind+name` 生成 ID，两个不同 startup handler 均成为 `IPC-on_event-startup`。当前列表尚未丢行，但按 ID 汇总/关联证据会发生碰撞；三个生命周期钩子也不应计作 HTTP/WS 网络入口。
