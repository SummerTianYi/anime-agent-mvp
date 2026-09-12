extends SceneTree

# 离线预览捕获：真实 UI 组件 + 模拟工具事件（零 GLM 调用）。
# 用法（窗口模式，渲染需要真实显示驱动）：
#   ..\tools\godot-4.7.2\Godot_v4.7.2-stable_win64_console.exe --display-driver windows --path apps\avatar-runtime --script res://capture_tool_activity.gd

const OUTPUT_PATH := "C:/Users/26052/AppData/Local/Temp/tool_activity_preview.png"
const OUTPUT_EFFORT_PATH := "C:/Users/26052/AppData/Local/Temp/effort_dial_preview.png"
const OUTPUT_HISTORY_PATH := "C:/Users/26052/AppData/Local/Temp/history_page_preview.png"


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var scene := load("res://main.tscn") as PackedScene
	if scene == null:
		push_error("Unable to load main scene")
		quit(1)
		return
	var runtime := scene.instantiate()
	root.add_child(runtime)
	var ui: Node = runtime.interaction_ui
	if ui == null:
		push_error("Interaction UI missing")
		quit(1)
		return

	ui._open_chat()
	ui.chat_status.text = "按住「语音」说话，松开后转写回输入框"
	ui.add_message("你", "天依，帮我看看 GitHub 上有什么新动静？")
	ui.on_agent_tool("get_time", true)
	ui.on_agent_tool("mcp__github__get_me", true)
	ui.on_agent_tool("mcp__browser__navigate", false)
	ui.add_message("洛天依", "看过啦！GitHub 上有一条新的 CI 通知；浏览器那条没打开，是网络的小脾气～")

	await process_frame
	await process_frame
	await RenderingServer.frame_post_draw
	var full := root.get_texture().get_image()
	if full == null or full.is_empty():
		push_error("Renderer returned an empty capture")
		quit(1)
		return
	# 裁到 角色上方 + 聊天面板 的有效区域，避免透明画布的大片黑边
	var panel_rect: Rect2 = ui.chat_panel.get_global_rect()
	var origin: Vector2 = ui.canvas_origin
	var top_left: Vector2 = origin + panel_rect.position
	var from := Vector2(maxf(0.0, top_left.x - 500.0), maxf(0.0, top_left.y - 520.0))
	var to := Vector2(
		minf(full.get_width(), top_left.x + panel_rect.size.x + 30.0),
		minf(full.get_height(), top_left.y + panel_rect.size.y + 140.0)
	)
	var img := full.get_region(Rect2i(from, to - from))
	if img == null or img.is_empty():
		push_error("Crop returned an empty capture")
		quit(1)
		return
	var err := img.save_png(OUTPUT_PATH)
	if err != OK:
		push_error("Cannot save capture: " + error_string(err))
		quit(1)
		return
	print("TOOL_ACTIVITY_CAPTURE_SAVED ", OUTPUT_PATH, " size=", img.get_width(), "x", img.get_height())

	# 第二张：思考强度弹窗（档位移到"标准"展示联动）
	ui._open_effort_popover()
	ui.effort_slider.value = 1.0
	await process_frame
	await RenderingServer.frame_post_draw
	var full2 := root.get_texture().get_image()
	if full2 == null or full2.is_empty():
		push_error("Renderer returned an empty effort capture")
		quit(1)
		return
	var img2 := full2.get_region(Rect2i(from, to - from))
	if img2 == null or img2.is_empty():
		push_error("Crop returned an empty effort capture")
		quit(1)
		return
	var err2 := img2.save_png(OUTPUT_EFFORT_PATH)
	if err2 != OK:
		push_error("Cannot save effort capture: " + error_string(err2))
		quit(1)
		return
	print("EFFORT_DIAL_CAPTURE_SAVED ", OUTPUT_EFFORT_PATH, " size=", img2.get_width(), "x", img2.get_height())

	# 第三张：回忆手账（历史会话列表页）
	ui._hide_effort_popover()
	ui.on_session_list([
		{"conversationId": 21, "title": "熬夜的危害聊哪", "updatedAt": _recent_stamp(0)},
		{"conversationId": 22, "title": "认证训练复盘", "updatedAt": _recent_stamp(0)},
		{"conversationId": 23, "title": "谁的仓鼠最大", "updatedAt": _recent_stamp(1)},
		{"conversationId": 24, "title": "帮我读一下笔记", "updatedAt": _recent_stamp(2)},
		{"conversationId": 25, "title": "歌单计划讨论", "updatedAt": _recent_stamp(9)},
	])
	ui.chat_status.text = "按住「语音」说话，松开后转写回输入框"
	ui._open_history_page()
	await process_frame
	await RenderingServer.frame_post_draw
	var full3 := root.get_texture().get_image()
	if full3 == null or full3.is_empty():
		push_error("Renderer returned an empty history capture")
		quit(1)
		return
	var img3 := full3.get_region(Rect2i(from, to - from))
	if img3 == null or img3.is_empty():
		push_error("Crop returned an empty history capture")
		quit(1)
		return
	var err3 := img3.save_png(OUTPUT_HISTORY_PATH)
	if err3 != OK:
		push_error("Cannot save history capture: " + error_string(err3))
		quit(1)
		return
	print("HISTORY_PAGE_CAPTURE_SAVED ", OUTPUT_HISTORY_PATH, " size=", img3.get_width(), "x", img3.get_height())
	quit(0)


func _recent_stamp(days_ago: int) -> String:
	var d := Time.get_datetime_dict_from_system()
	var unix := Time.get_unix_time_from_datetime_string(
		"%04d-%02d-%02dT08:30:00" % [d.year, d.month, d.day]
	) - days_ago * 86400
	var dict := Time.get_datetime_dict_from_unix_time(int(unix))
	return "%04d-%02d-%02d %02d:%02d:00" % [dict.year, dict.month, dict.day, dict.hour, dict.minute]
