extends CanvasLayer


const VIEWPORT_SIZE := Vector2(560.0, 760.0)
const AVATAR_TEXTURE_PATH := "res://assets/luotianyi_avatar.jpg"
const MAX_BUBBLE_WIDTH := 330.0
const HISTORY_SCROLL_STICK_RANGE := 60.0

# 洛天依主题（docs/design/chat-form-upgrade.md）
const COLOR_PANEL := Color(0.039, 0.063, 0.11, 0.94)
const COLOR_PANEL_LINE := Color(0.4, 0.8, 1.0, 0.16)
const COLOR_TIANI_BLUE := Color(0.4, 0.8, 1.0)
const COLOR_BUBBLE_YI := Color(0.949, 0.961, 0.98)
const COLOR_BUBBLE_YI_TEXT := Color(0.165, 0.192, 0.251)
const COLOR_BUBBLE_USER_TEXT := Color(0.039, 0.141, 0.204)
const COLOR_JADE := Color(0.498, 0.831, 0.659)
const COLOR_TEXT := Color(0.91, 0.925, 0.957)
const COLOR_TEXT_DIM := Color(0.541, 0.576, 0.659)

var avatar: Node
var backdrop: ColorRect
var menu_panel: PanelContainer
var chat_panel: PanelContainer
var interaction_panel: PanelContainer
var bubbles_scroll: ScrollContainer
var bubbles_box: VBoxContainer
var empty_hint: Label
var session_option: OptionButton
var chat_input: LineEdit
var chat_status: Label
var voice_button: Button
var avatar_texture: Texture2D

var sessions: Array = []
var current_conversation_id := -1

var menu_visible := false
var chat_visible := false
var interaction_visible := false


func _init(avatar_node: Node) -> void:
	avatar = avatar_node


func _ready() -> void:
	layer = 20
	avatar_texture = _make_avatar_texture(AVATAR_TEXTURE_PATH)
	_build_backdrop()
	_build_menu()
	_build_chat()
	_build_interaction()
	hide_all()


# ---------------------------------------------------------------- 会话与消息

func on_session_list(items: Array) -> void:
	sessions = []
	for item in items:
		if item is Dictionary:
			sessions.append({
				"id": int(item.get("conversationId", 0)),
				"title": str(item.get("title", "会话")),
			})
	if current_conversation_id < 0 and not sessions.is_empty():
		current_conversation_id = int(sessions[0]["id"])
		avatar.request_chat_history(current_conversation_id)
	_sync_session_options()


func on_session_switched(conversation_id: int, title: String) -> void:
	current_conversation_id = conversation_id
	_upsert_session(conversation_id, title)
	_sync_session_options()
	_clear_bubbles()
	if chat_visible:
		chat_status.text = "已切换到「%s」" % title


func on_chat_history(conversation_id: int, messages: Array) -> void:
	if current_conversation_id > 0 and conversation_id != current_conversation_id:
		return
	_clear_bubbles()
	for item in messages:
		if not (item is Dictionary):
			continue
		var role := "你" if str(item.get("role", "")) == "user" else "洛天依"
		_append_bubble(role, str(item.get("text", "")), _short_time(str(item.get("createdAt", ""))))
	_scroll_to_bottom()


func add_message(role: String, text: String, conversation_id: int = -1) -> void:
	var safe_text := text.strip_edges()
	if safe_text.is_empty():
		return
	if conversation_id > 0 and current_conversation_id > 0 and conversation_id != current_conversation_id:
		return
	var time_text := Time.get_time_string_from_system().substr(0, 5)
	_append_bubble(role, safe_text, time_text)
	_scroll_to_bottom()


func show_error(message: String) -> void:
	add_message("系统", message)
	chat_status.text = message


func get_current_conversation_id() -> int:
	return current_conversation_id


func _upsert_session(conversation_id: int, title: String) -> void:
	for item in sessions:
		if int(item["id"]) == conversation_id:
			item["title"] = title
			return
	sessions.push_front({"id": conversation_id, "title": title})


func _sync_session_options() -> void:
	if session_option == null:
		return
	session_option.clear()
	var selected := 0
	for index in range(sessions.size()):
		var item: Dictionary = sessions[index]
		session_option.add_item(str(item["title"]))
		if int(item["id"]) == current_conversation_id:
			selected = index
	if not sessions.is_empty():
		session_option.select(selected)


func _on_session_selected(index: int) -> void:
	if index < 0 or index >= sessions.size():
		return
	var conversation_id := int(sessions[index]["id"])
	if conversation_id == current_conversation_id:
		return
	current_conversation_id = conversation_id
	_clear_bubbles()
	chat_status.text = "正在载入历史……"
	avatar.request_chat_history(conversation_id)


func _on_new_session_pressed() -> void:
	avatar.request_new_session()


# ---------------------------------------------------------------- 界面构建

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

	var title := _make_label("和洛天依做什么？", 16, COLOR_TEXT)
	box.add_child(title)
	box.add_child(_make_button("聊天", _open_chat))
	box.add_child(_make_button("互动", _open_interaction))
	var hint := _make_label("点击空白处收起", 11, COLOR_TEXT_DIM)
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(hint)
	add_child(menu_panel)


func _build_chat() -> void:
	chat_panel = _make_panel(Vector2(10.0, 330.0), Vector2(540.0, 420.0), COLOR_PANEL, COLOR_PANEL_LINE)
	var margin := MarginContainer.new()
	for side in ["margin_left", "margin_right", "margin_top", "margin_bottom"]:
		margin.add_theme_constant_override(side, 12)
	chat_panel.add_child(margin)

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	margin.add_child(box)
	box.add_child(_build_chat_header())

	bubbles_scroll = ScrollContainer.new()
	bubbles_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	bubbles_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	bubbles_box = VBoxContainer.new()
	bubbles_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bubbles_box.add_theme_constant_override("separation", 10)
	bubbles_scroll.add_child(bubbles_box)
	box.add_child(bubbles_scroll)

	chat_status = _make_label("按住「语音」说话，松开后转写回输入框", 10, COLOR_TEXT_DIM)
	box.add_child(chat_status)
	box.add_child(_build_composer())
	add_child(chat_panel)
	_show_empty_hint()


func _build_chat_header() -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)

	if avatar_texture != null:
		var badge := TextureRect.new()
		badge.texture = avatar_texture
		badge.custom_minimum_size = Vector2(22.0, 22.0)
		badge.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		badge.stretch_mode = TextureRect.STRETCH_SCALE
		row.add_child(badge)
	row.add_child(_make_label("洛天依", 14, COLOR_TIANI_BLUE))

	session_option = OptionButton.new()
	session_option.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	session_option.focus_mode = Control.FOCUS_NONE
	session_option.add_theme_font_size_override("font_size", 12)
	session_option.tooltip_text = "切换会话"
	session_option.item_selected.connect(_on_session_selected)
	row.add_child(session_option)

	var new_button := _make_accent_button("＋ 新对话", _on_new_session_pressed)
	new_button.custom_minimum_size = Vector2(88.0, 30.0)
	row.add_child(new_button)
	return row


func _build_composer() -> Control:
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

	var send_button := _make_accent_button("发送", _send_current_message)
	send_button.custom_minimum_size = Vector2(64.0, 38.0)
	composer.add_child(send_button)
	return composer


func _build_interaction() -> void:
	interaction_panel = _make_panel(Vector2(315.0, 140.0), Vector2(225.0, 440.0))
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 6)
	interaction_panel.add_child(box)

	var title_row := HBoxContainer.new()
	var title := _make_label("互动", 17, COLOR_TEXT)
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	title_row.add_child(title)
	var close_button := _make_button("×", _close_overlay)
	close_button.custom_minimum_size = Vector2(34.0, 30.0)
	title_row.add_child(close_button)
	box.add_child(title_row)

	for action in [
		["旋转动作（样片）", "avatar.pirouette"],
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

	var hint := _make_label("动作会立即在角色身上执行", 10, COLOR_TEXT_DIM)
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(hint)
	add_child(interaction_panel)


# ---------------------------------------------------------------- 气泡

func _append_bubble(role: String, text: String, time_text: String) -> void:
	_remove_empty_hint()
	var is_user := role == "你"

	var row := HBoxContainer.new()
	row.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_theme_constant_override("separation", 8)

	var bubble := PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.set_corner_radius_all(14)
	style.content_margin_left = 10.0
	style.content_margin_right = 10.0
	style.content_margin_top = 7.0
	style.content_margin_bottom = 7.0
	if is_user:
		style.bg_color = COLOR_TIANI_BLUE
		style.corner_radius_top_right = 4
	else:
		style.bg_color = COLOR_BUBBLE_YI
		style.corner_radius_top_left = 4
	bubble.add_theme_stylebox_override("panel", style)

	var bubble_box := VBoxContainer.new()
	bubble_box.add_theme_constant_override("separation", 2)
	var label := Label.new()
	label.text = text
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.add_theme_font_size_override("font_size", 13)
	label.add_theme_color_override(
		"font_color",
		COLOR_BUBBLE_USER_TEXT if is_user else COLOR_BUBBLE_YI_TEXT
	)
	var font := ThemeDB.fallback_font
	var text_width := font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, 13).x
	var label_min_width := maxf(44.0, minf(text_width, MAX_BUBBLE_WIDTH - 20.0))
	label.custom_minimum_size = Vector2(label_min_width, 0.0)
	bubble_box.add_child(label)
	if time_text != "":
		var time_label := _make_label(
			time_text, 9,
			COLOR_BUBBLE_USER_TEXT if is_user else COLOR_TEXT_DIM
		)
		time_label.horizontal_alignment = (
			HORIZONTAL_ALIGNMENT_RIGHT if is_user else HORIZONTAL_ALIGNMENT_LEFT
		)
		bubble_box.add_child(time_label)
	bubble.add_child(bubble_box)

	if is_user:
		row.alignment = BoxContainer.ALIGNMENT_END
		row.add_child(bubble)
		row.add_child(_make_user_dot())
	else:
		row.alignment = BoxContainer.ALIGNMENT_BEGIN
		row.add_child(_make_yi_dot())
		row.add_child(bubble)
	bubbles_box.add_child(row)
	_stick_scroll_if_needed()


func _make_yi_dot() -> Control:
	if avatar_texture != null:
		var dot := TextureRect.new()
		dot.texture = avatar_texture
		dot.custom_minimum_size = Vector2(26.0, 26.0)
		dot.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		dot.stretch_mode = TextureRect.STRETCH_SCALE
		dot.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		return dot
	var label := _make_label("♪", 14, COLOR_TIANI_BLUE)
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.custom_minimum_size = Vector2(26.0, 26.0)
	return label


func _make_user_dot() -> Control:
	var dot := PanelContainer.new()
	dot.custom_minimum_size = Vector2(26.0, 26.0)
	dot.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var style := StyleBoxFlat.new()
	style.bg_color = Color(COLOR_JADE.r, COLOR_JADE.g, COLOR_JADE.b, 0.25)
	style.border_color = Color(COLOR_JADE.r, COLOR_JADE.g, COLOR_JADE.b, 0.7)
	style.set_border_width_all(1)
	style.set_corner_radius_all(13)
	dot.add_theme_stylebox_override("panel", style)
	var label := _make_label("我", 11, COLOR_JADE)
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	dot.add_child(label)
	return dot


func _show_empty_hint() -> void:
	if empty_hint != null or bubbles_box == null:
		return
	empty_hint = _make_label("♪ 开始和天依聊天吧", 12, COLOR_TEXT_DIM)
	empty_hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	empty_hint.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bubbles_box.add_child(empty_hint)


func _remove_empty_hint() -> void:
	if empty_hint == null:
		return
	if empty_hint.get_parent() != null:
		empty_hint.get_parent().remove_child(empty_hint)
	empty_hint.queue_free()
	empty_hint = null


func _clear_bubbles() -> void:
	if bubbles_box == null:
		return
	for child in bubbles_box.get_children():
		child.queue_free()
	empty_hint = null
	_show_empty_hint()


func _stick_scroll_if_needed() -> void:
	if bubbles_scroll == null:
		return
	var bar := bubbles_scroll.get_v_scroll_bar()
	if bar.value >= bar.max_value - HISTORY_SCROLL_STICK_RANGE:
		_scroll_to_bottom()


func _scroll_to_bottom() -> void:
	await get_tree().process_frame
	if bubbles_scroll == null:
		return
	var bar := bubbles_scroll.get_v_scroll_bar()
	bubbles_scroll.scroll_vertical = int(bar.max_value)


func _short_time(created_at: String) -> String:
	# SQLite CURRENT_TIMESTAMP 形如 2026-08-29 18:08:38，取时分即可
	if created_at.length() >= 16:
		return created_at.substr(11, 5)
	return ""


# ---------------------------------------------------------------- 头像

func _make_avatar_texture(path: String) -> Texture2D:
	var image := Image.load_from_file(ProjectSettings.globalize_path(path))
	if image == null:
		push_warning("Avatar texture not found: %s" % path)
		return null
	image.convert(Image.FORMAT_RGBA8)
	var texture_size := image.get_width()
	var radius := texture_size * 0.5
	var center := Vector2(radius, radius)
	for y in range(texture_size):
		for x in range(texture_size):
			var distance := Vector2(x + 0.5, y + 0.5).distance_to(center)
			var alpha := clampf((radius - distance) / 1.5, 0.0, 1.0)
			if alpha <= 0.0:
				image.set_pixel(x, y, Color(0.0, 0.0, 0.0, 0.0))
			elif alpha < 1.0:
				var pixel := image.get_pixel(x, y)
				pixel.a *= alpha
				image.set_pixel(x, y, pixel)
	return ImageTexture.create_from_image(image)


# ---------------------------------------------------------------- 通用控件

func _make_panel(
	panel_position: Vector2,
	panel_size: Vector2,
	bg_color: Color = Color(0.055, 0.065, 0.12, 0.95),
	border_color: Color = Color(0.38, 0.42, 0.68, 0.9)
) -> PanelContainer:
	var panel := PanelContainer.new()
	panel.position = panel_position
	panel.size = panel_size
	panel.mouse_filter = Control.MOUSE_FILTER_STOP
	var style := StyleBoxFlat.new()
	style.bg_color = bg_color
	style.border_color = border_color
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


func _make_accent_button(text: String, callback: Callable) -> Button:
	var button := _make_button(text, callback)
	var normal := StyleBoxFlat.new()
	normal.bg_color = COLOR_TIANI_BLUE
	normal.set_corner_radius_all(8)
	var hover := normal.duplicate()
	hover.bg_color = Color(0.49, 0.85, 1.0)
	var pressed := normal.duplicate()
	pressed.bg_color = Color(0.32, 0.68, 0.88)
	button.add_theme_stylebox_override("normal", normal)
	button.add_theme_stylebox_override("hover", hover)
	button.add_theme_stylebox_override("pressed", pressed)
	button.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	button.add_theme_color_override("font_color", COLOR_BUBBLE_USER_TEXT)
	button.add_theme_color_override("font_hover_color", COLOR_BUBBLE_USER_TEXT)
	button.add_theme_color_override("font_pressed_color", COLOR_BUBBLE_USER_TEXT)
	return button


# ---------------------------------------------------------------- 开合与输入

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
	_scroll_to_bottom()


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
			chat_status.text = "按住「语音」说话，松开后转写回输入框"


func on_voice_transcript(text: String) -> void:
	if chat_input == null:
		return
	chat_input.text = text
	chat_input.grab_focus()
	chat_status.text = "请确认转写内容后发送"


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
