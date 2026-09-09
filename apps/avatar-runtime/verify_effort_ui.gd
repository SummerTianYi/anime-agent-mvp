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

	# 1) 默认档 = 全力（保持历史行为），按钮文案可见
	if str(ui.effort_level) != "deep":
		_fail("default effort must be deep, got %s" % str(ui.effort_level))
		return
	if str(ui.effort_button.text) != "思考·全力":
		_fail("effort button text wrong: " + str(ui.effort_button.text))
		return

	# 2) 打开弹窗：档位名 + 模型名 + 滑杆位置
	ui._open_effort_popover()
	if ui.effort_overlay == null:
		_fail("effort popover did not open")
		return
	if str(ui.effort_big_label.text) != "全力":
		_fail("popover level label wrong: " + str(ui.effort_big_label.text))
		return
	if int(ui.effort_slider.value) != 2:
		_fail("slider not at deep position")
		return

	# 3) 拖到闲聊：档位名与说明联动
	ui.effort_slider.value = 0.0
	if str(ui.effort_level) != "chill":
		_fail("slider did not drive effort_level")
		return
	if str(ui.effort_big_label.text) != "闲聊":
		_fail("popover label did not follow slider")
		return
	if not str(ui.effort_hint_label.text).contains("最省额度"):
		_fail("chill hint missing")
		return

	# 4) 关闭后按钮文案同步
	ui._hide_effort_popover()
	if ui.effort_overlay != null:
		_fail("effort popover did not close")
		return
	if str(ui.effort_button.text) != "思考·闲聊":
		_fail("button label not synced after close: " + str(ui.effort_button.text))
		return

	# 5) 再切到标准档，作为下一条消息的发送档
	ui._open_effort_popover()
	ui.effort_slider.value = 1.0
	ui._hide_effort_popover()
	if str(ui.effort_level) != "standard":
		_fail("expected standard to be queued for next message")
		return

	# 6) 发送路径携带档位（离线时走尚未连接提示，但档位值保持在发送参数上）
	ui.chat_input.text = "在吗"
	ui._send_current_message()
	if str(ui.effort_level) != "standard":
		_fail("effort level mutated by send")
		return
	if not str(ui.chat_status.text).contains("尚未连接"):
		_fail("offline send path did not report connection state")
		return

	print("GODOT_EFFORT_UI_OK", {
		"default": "deep",
		"levels": ["闲聊", "标准", "全力"],
		"slider_follows": true,
		"send_effort": "standard",
	})
	quit(0)


func _fail(message: String) -> void:
	push_error(message)
	quit(1)
