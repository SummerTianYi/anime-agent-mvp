extends CanvasLayer


const VIEWPORT_SIZE := Vector2(560.0, 760.0)

var avatar: Node
var backdrop: ColorRect
var menu_panel: PanelContainer
var chat_panel: PanelContainer
var interaction_panel: PanelContainer
var chat_history: Label
var chat_input: LineEdit
var chat_status: Label
var voice_button: Button
var history_lines: Array[String] = []

var menu_visible := false
var chat_visible := false
var interaction_visible := false


func _init(avatar_node: Node) -> void:
	avatar = avatar_node


func _ready() -> void:
	layer = 20
	_build_backdrop()
	_build_menu()
	_build_chat()
	_build_interaction()
	hide_all()
	add_message("洛天依", "你好呀。点击我可以打开聊天或互动菜单。")


func _build_backdrop() -> void:
	backdrop = ColorRect.new()
	backdrop.position = Vector2.ZERO
	backdrop.size = VIEWPORT_SIZE
	backdrop.color = Color(0.0, 0.0, 0.0, 0.001)
	backdrop.mouse_filter = Control.MOUSE_FILTER_STOP
	backdrop.gui_input.connect(_on_backdrop_input)
	add_child(backdrop)


func _build_menu() -> void:
	menu_panel = _make_panel(Vector2(326.0, 240.0), Vector2(204.0, 182.0))
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	menu_panel.add_child(box)

	var title := _make_label("和洛天依做什么？", 16, Color(0.96, 0.96, 1.0))
	box.add_child(title)
	box.add_child(_make_button("聊天", _open_chat))
	box.add_child(_make_button("互动", _open_interaction))
	var hint := _make_label("点击空白处收起", 11, Color(0.64, 0.66, 0.76))
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(hint)
	add_child(menu_panel)


func _build_chat() -> void:
	chat_panel = _make_panel(Vector2(20.0, 105.0), Vector2(520.0, 310.0))
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 9)
	chat_panel.add_child(box)

	var title_row := HBoxContainer.new()
	var title := _make_label("和洛天依聊天", 17, Color(0.96, 0.96, 1.0))
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	title_row.add_child(title)
	var close_button := _make_button("×", _close_overlay)
	close_button.custom_minimum_size = Vector2(34.0, 30.0)
	title_row.add_child(close_button)
	box.add_child(title_row)

	chat_history = _make_label("", 13, Color(0.86, 0.87, 0.94))
	chat_history.custom_minimum_size = Vector2(0.0, 176.0)
	chat_history.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	chat_history.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
	chat_history.size_flags_vertical = Control.SIZE_EXPAND_FILL
	box.add_child(chat_history)

	var composer := HBoxContainer.new()
	composer.add_theme_constant_override("separation", 7)
	chat_input = LineEdit.new()
	chat_input.placeholder_text = "输入消息，按 Enter 发送"
	chat_input.custom_minimum_size = Vector2(0.0, 38.0)
	chat_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	chat_input.focus_mode = Control.FOCUS_ALL
	chat_input.text_submitted.connect(_on_chat_submitted)
	composer.add_child(chat_input)

	voice_button = _make_button("语音", _on_voice_pressed)
	voice_button.custom_minimum_size = Vector2(54.0, 38.0)
	voice_button.pressed.disconnect(_on_voice_pressed)
	voice_button.button_down.connect(_on_voice_down)
	voice_button.button_up.connect(_on_voice_up)
	voice_button.tooltip_text = "按住说话，松开后转成文字"
	composer.add_child(voice_button)
	composer.add_child(_make_button("发送", _send_current_message))
	box.add_child(composer)

	chat_status = _make_label("当前优先接入 GLM 5.3 Flash", 10, Color(0.64, 0.66, 0.76))
	box.add_child(chat_status)
	add_child(chat_panel)


func _build_interaction() -> void:
	interaction_panel = _make_panel(Vector2(315.0, 175.0), Vector2(225.0, 405.0))
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 6)
	interaction_panel.add_child(box)

	var title_row := HBoxContainer.new()
	var title := _make_label("互动", 17, Color(0.96, 0.96, 1.0))
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	title_row.add_child(title)
	var close_button := _make_button("×", _close_overlay)
	close_button.custom_minimum_size = Vector2(34.0, 30.0)
	title_row.add_child(close_button)
	box.add_child(title_row)

	for action in [
		["挥手", "avatar.wave"],
		["点头", "avatar.nod"],
		["打招呼", "avatar.greet"],
		["转身", "avatar.turn_right"],
		["回到正面", "avatar.reset"],
		["微笑", "avatar.smile"],
		["眨眼", "avatar.blink"],
		["惊讶", "avatar.surprised"],
		["生气", "avatar.angry"],
		["流泪", "avatar.tears"],
	]:
		var action_button := _make_button(str(action[0]), _run_action.bind(str(action[1])))
		action_button.custom_minimum_size = Vector2(0.0, 29.0)
		box.add_child(action_button)

	var hint := _make_label("动作会立即在角色身上执行", 10, Color(0.64, 0.66, 0.76))
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(hint)
	add_child(interaction_panel)


func _make_panel(panel_position: Vector2, panel_size: Vector2) -> PanelContainer:
	var panel := PanelContainer.new()
	panel.position = panel_position
	panel.size = panel_size
	panel.mouse_filter = Control.MOUSE_FILTER_STOP
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.055, 0.065, 0.12, 0.95)
	style.border_color = Color(0.38, 0.42, 0.68, 0.9)
	style.set_border_width_all(1)
	style.set_corner_radius_all(16)
	style.shadow_color = Color(0.0, 0.0, 0.0, 0.35)
	style.shadow_size = 12
	panel.add_theme_stylebox_override("panel", style)
	return panel


func _make_label(text: String, font_size: int, color: Color) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	return label


func _make_button(text: String, callback: Callable) -> Button:
	var button := Button.new()
	button.text = text
	button.custom_minimum_size = Vector2(0.0, 38.0)
	button.focus_mode = Control.FOCUS_NONE
	button.add_theme_font_size_override("font_size", 13)
	button.pressed.connect(callback)
	return button


func _open_chat() -> void:
	menu_visible = false
	interaction_visible = false
	chat_visible = true
	menu_panel.visible = false
	interaction_panel.visible = false
	chat_panel.visible = true
	backdrop.visible = true
	_set_passthrough(false)
	chat_input.grab_focus()


func _open_interaction() -> void:
	menu_visible = false
	chat_visible = false
	interaction_visible = true
	menu_panel.visible = false
	chat_panel.visible = false
	interaction_panel.visible = true
	backdrop.visible = true
	_set_passthrough(false)


func toggle_menu() -> void:
	if menu_visible:
		hide_all()
		return
	menu_visible = true
	chat_visible = false
	interaction_visible = false
	menu_panel.visible = true
	chat_panel.visible = false
	interaction_panel.visible = false
	backdrop.visible = true
	_set_passthrough(false)


func hide_all() -> void:
	menu_visible = false
	chat_visible = false
	interaction_visible = false
	if chat_input != null:
		chat_input.release_focus()
	if menu_panel != null:
		menu_panel.visible = false
	if chat_panel != null:
		chat_panel.visible = false
	if interaction_panel != null:
		interaction_panel.visible = false
	if backdrop != null:
		backdrop.visible = false
	_set_passthrough(true)


func _close_overlay() -> void:
	hide_all()


func is_pointer_over_ui(pointer: Vector2) -> bool:
	for panel in [menu_panel, chat_panel, interaction_panel]:
		if panel != null and panel.visible and Rect2(panel.position, panel.size).has_point(pointer):
			return true
	return false


func _on_backdrop_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mouse_event := event as InputEventMouseButton
		if mouse_event.button_index == MOUSE_BUTTON_LEFT and not mouse_event.pressed:
			if not is_pointer_over_ui(mouse_event.position):
				hide_all()


func _run_action(action_name: String) -> void:
	avatar.handle_agent_event(action_name)


func _on_chat_submitted(_text: String) -> void:
	_send_current_message()


func _send_current_message() -> void:
	if chat_input == null:
		return
	var text := chat_input.text.strip_edges()
	if text.is_empty():
		return
	add_message("你", text)
	chat_input.clear()
	avatar.send_chat_message(text)


func _on_voice_pressed() -> void:
	chat_status.text = "按住语音按钮说话，松开后转成文字"


func _on_voice_down() -> void:
	chat_status.text = "正在录音，松开结束"
	avatar.start_voice_recording()


func _on_voice_up() -> void:
	chat_status.text = "正在识别语音……"
	avatar.stop_voice_recording()


func on_voice_state(next_state: String) -> void:
	if chat_status == null:
		return
	match next_state:
		"recording":
			chat_status.text = "正在录音，松开结束"
		"transcribing":
			chat_status.text = "正在识别语音……"
		_:
			chat_status.text = "当前优先接入 GLM 5.3 Flash"


func on_voice_transcript(text: String) -> void:
	if chat_input == null:
		return
	chat_input.text = text
	chat_input.grab_focus()
	chat_status.text = "请确认转写内容后发送"


func add_message(role: String, text: String) -> void:
	var safe_text := text.replace("\n", " ").strip_edges()
	if safe_text.is_empty():
		return
	history_lines.append("%s：%s" % [role, safe_text])
	if history_lines.size() > 6:
		history_lines.pop_front()
	if chat_history != null:
		chat_history.text = "\n\n".join(history_lines)


func show_error(message: String) -> void:
	add_message("系统", message)
	chat_status.text = message


func _set_passthrough(enabled: bool) -> void:
	if DisplayServer.get_name() == "headless":
		return
	if enabled:
		var interaction_region := PackedVector2Array([
			Vector2(232.0, 138.0), Vector2(328.0, 138.0), Vector2(352.0, 232.0),
			Vector2(438.0, 330.0), Vector2(430.0, 402.0), Vector2(356.0, 358.0),
			Vector2(354.0, 650.0), Vector2(314.0, 690.0), Vector2(246.0, 690.0),
			Vector2(206.0, 650.0), Vector2(204.0, 358.0), Vector2(130.0, 402.0),
			Vector2(122.0, 330.0), Vector2(208.0, 232.0),
		])
		DisplayServer.window_set_mouse_passthrough(interaction_region)
	else:
		DisplayServer.window_set_mouse_passthrough(PackedVector2Array())
