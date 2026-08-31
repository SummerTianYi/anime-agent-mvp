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

	# 1) 会话列表载入
	ui.on_session_list([
		{"conversationId": 1, "title": "新对话", "updatedAt": "t0"},
		{"conversationId": 2, "title": "晚风与海", "updatedAt": "t1"},
	])
	if ui.sessions.size() != 2:
		_fail("session list not populated")
		return
	if int(ui.current_conversation_id) != 1:
		_fail("current session not selected from list")
		return

	# 2) 标题事件刷新下拉
	runtime._handle_core_event({
		"type": "session.title",
		"conversationId": 1,
		"title": "天气与问候",
	})
	var selected_text: String = ui.session_option.get_item_text(ui.session_option.selected)
	if selected_text != "天气与问候":
		_fail("session.title event did not update dropdown")
		return

	# 3) 单击删除 → 确认框（修复点：一次点击）
	ui._on_delete_session_pressed()
	if ui.delete_overlay == null:
		_fail("single click did not open confirm dialog")
		return

	# 4) 取消关闭弹框
	ui._hide_delete_dialog()
	if ui.delete_overlay != null:
		_fail("cancel did not close dialog")
		return

	# 5) 确认删除：请求到达 runtime（离线时显示尚未连接错误即证明调用已发生）
	ui._on_delete_session_pressed()
	if ui.delete_overlay == null:
		_fail("dialog did not reopen")
		return
	ui._on_delete_confirmed()
	if ui.delete_overlay != null:
		_fail("confirm did not close dialog")
		return
	if not str(ui.chat_status.text).contains("尚未连接"):
		_fail("confirm did not reach runtime request path")
		return

	# 6) session.deleted 过滤列表并清空当前
	runtime._handle_core_event({
		"type": "session.deleted",
		"conversationId": 1,
	})
	if ui.sessions.size() != 1:
		_fail("deleted session not removed")
		return
	if int(ui.current_conversation_id) != -1:
		_fail("current not cleared after deletion")
		return

	print("GODOT_SESSION_UI_OK", {
		"single_click_dialog": true,
		"title_refresh": selected_text,
		"list_filtered": true,
	})
	quit(0)


func _fail(message: String) -> void:
	push_error(message)
	quit(1)
