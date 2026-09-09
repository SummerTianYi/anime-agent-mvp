extends SceneTree


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var scene := load("res://main.tscn") as PackedScene
	if scene == null:
		_fail("Unable to load main scene")
		return
	var runtime := scene.instantiate()
	root.add_child(runtime)
	var ui: Node = runtime.interaction_ui
	if ui == null:
		_fail("Interaction UI missing")
		return

	# 1) 本地工具事件 -> 活动卡出现，首行正确
	ui.on_agent_tool("get_time", true)
	if ui.tool_card == null:
		_fail("tool card not created on first agent.tool")
		return
	if ui.tool_rows_box.get_child_count() != 1:
		_fail("expected 1 tool row after first event")
		return
	var local_row := ui.tool_rows_box.get_child(0) as HBoxContainer
	var local_badge := (local_row.get_child(0) as PanelContainer).get_child(0) as Label
	if local_badge.text != "本地":
		_fail("local tool badge wrong: " + local_badge.text)
		return

	# 2) MCP 长名解析为 服务器徽标 + 工具名
	ui.on_agent_tool("mcp__github__get_me", true)
	if ui.tool_rows_box.get_child_count() != 2:
		_fail("expected 2 tool rows after mcp event")
		return
	var mcp_row := ui.tool_rows_box.get_child(1) as HBoxContainer
	var mcp_badge := (mcp_row.get_child(0) as PanelContainer).get_child(0) as Label
	if mcp_badge.text != "GitHub":
		_fail("mcp server badge not parsed: " + mcp_badge.text)
		return
	var mcp_name := mcp_row.get_child(1) as Label
	if mcp_name.text != "get_me":
		_fail("mcp tool name not parsed: " + mcp_name.text)
		return

	# 3) 失败行有 ✗ 标记（用户可见文本断言）
	ui.on_agent_tool("mcp__browser__navigate", false)
	var fail_row := ui.tool_rows_box.get_child(2) as HBoxContainer
	var fail_mark := fail_row.get_child(2) as Label
	if fail_mark.text != "✗":
		_fail("failure mark missing on failed tool row")
		return

	# 4) 计数标签随调用次数更新
	if not str(ui.tool_count_label.text).contains("3"):
		_fail("call count label not updated: " + str(ui.tool_count_label.text))
		return

	# 5) 用户发新消息 -> 重置；下一个工具事件开新卡
	ui.chat_input.text = "现在几点"
	ui._send_current_message()
	if ui.tool_card != null:
		_fail("tool card not reset when user sends a new message")
		return
	ui.on_agent_tool("active_window", true)
	if ui.tool_rows_box.get_child_count() != 1:
		_fail("new turn did not start a fresh tool card")
		return

	# 6) 清空气泡（切会话/载历史）-> 活动卡引用同步清空
	ui._clear_bubbles()
	if ui.tool_card != null:
		_fail("tool card reference not cleared with bubbles")
		return

	print("GODOT_TOOL_ACTIVITY_OK", {
		"rows": 3,
		"mcp_badge": str(mcp_badge.text),
		"reset_on_new_turn": true,
		"cleared_on_session_switch": true,
	})
	quit(0)


func _fail(message: String) -> void:
	push_error(message)
	quit(1)
