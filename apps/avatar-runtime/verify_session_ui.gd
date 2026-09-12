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

	# 2) 标题事件刷新会话数据（下拉已移除，标题进回忆手账数据源）
	runtime._handle_core_event({
		"type": "session.title",
		"conversationId": 1,
		"title": "天气与问候",
	})
	var found_title := false
	for session in ui.sessions:
		if int(session["id"]) == 1 and str(session["title"]) == "天气与问候":
			found_title = true
	if not found_title:
		_fail("session.title event did not update session data")
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

	# 7) 回忆手账：打开页面、日期分组、搜索过滤、关闭
	var today_dict := Time.get_datetime_dict_from_system()
	var today_str := "%04d-%02d-%02d 10:00:00" % [today_dict.year, today_dict.month, today_dict.day]
	ui.on_session_list([
		{"conversationId": 7, "title": "今日份回忆", "updatedAt": today_str},
		{"conversationId": 8, "title": "更早的回忆", "updatedAt": "2026-01-01 00:00:00"},
	])
	ui._open_history_page()
	if ui.history_page == null or not ui.history_page.visible:
		_fail("history page did not open")
		return
	var group_headers := 0
	for child in ui.history_list_box.get_children():
		if child is Label and str(child.text).begins_with("♪"):
			group_headers += 1
	if group_headers < 2:
		_fail("expected date group headers (今天/更早), got %d" % group_headers)
		return
	ui.history_search.text = "更早"
	ui._refresh_history_list("更早")
	if ui.history_list_box.get_child_count() < 2:
		_fail("search filter did not filter history cards")
		return
	ui._close_history_page()
	if ui.history_page != null and ui.history_page.visible:
		_fail("history page did not close")
		return

	print("GODOT_SESSION_UI_OK", {
		"single_click_dialog": true,
		"title_refresh": true,
		"list_filtered": true,
		"history_page_groups": group_headers,
		"history_search_filter": true,
	})
	quit(0)


func _fail(message: String) -> void:
	push_error(message)
	quit(1)
