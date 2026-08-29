extends Node3D


const MIN_CAMERA_DISTANCE := 2.7
const MAX_CAMERA_DISTANCE := 5.2
const CAMERA_FOCUS := Vector3(0.0, 0.88, 0.0)
const PIGTAIL_TILT_ANGLE := 0.0
const PIGTAIL_INWARD_ANGLE := -30.0
const PIGTAIL_DEPTH_ANGLE := 0.0
const PIGTAIL_SWAY_AMPLITUDE := 1.6
const WINDOW_SETTINGS_PATH := "user://avatar_window.cfg"
const DEFAULT_CORE_WS_URL := "ws://127.0.0.1:8765/ws"
const CORE_RECONNECT_DELAY := 2.0
const SPEAKING_MOUTHS := ["あ", "い", "う", "え", "お"]

@onready var model: Node3D = $LuoTianyi
@onready var camera: Camera3D = $Camera3D

var elapsed := 0.0
var target_yaw := 0.0
var current_yaw := 0.0
var target_distance := 3.8
var current_distance := 3.8
var rotation_dragging := false
var last_pointer := Vector2.ZERO
var left_pressing := false
var left_dragging := false
var left_press_position := Vector2.ZERO
var interaction_ui: Node

var base_model_rotation := Vector3.ZERO
var base_model_position := Vector3.ZERO
var skeleton: Skeleton3D
var bone_ids: Dictionary = {}
var base_bone_rotations: Dictionary = {}
var rest_bone_rotations: Dictionary = {}
var pigtail_root_ids: Array[int] = []
var pigtail_base_rotations: Dictionary = {}
var pigtail_rest_rotations: Dictionary = {}

var face_mesh: MeshInstance3D
var expression_ids: Dictionary = {}
var expression_values: Dictionary = {}
var expression_targets: Dictionary = {}
var expression_timers: Dictionary = {}
var blink_timer := 3.8
var expression_name := "自然"
var agent_state := "idle"
var speaking_mouth_elapsed := 0.0
var speaking_mouth_index := -1

var core_socket: WebSocketPeer
var core_ws_url := DEFAULT_CORE_WS_URL
var core_connection_state := "offline"
var core_reconnect_timer := 0.0
var core_client_announced := false

var action_name := "idle"
var action_elapsed := 0.0
var action_duration := 0.0

var action_label: Label
var camera_label: Label
var expression_label: Label
var core_label: Label
var hud_canvas: CanvasLayer
var hud_visible := false


func _ready() -> void:
	var configured_core_url := OS.get_environment("AGENT_CORE_WS_URL").strip_edges()
	if not configured_core_url.is_empty():
		core_ws_url = configured_core_url
	_configure_desktop_window()
	base_model_rotation = model.rotation
	base_model_position = model.position
	camera.position = Vector3(0.0, CAMERA_FOCUS.y, current_distance)
	camera.look_at(CAMERA_FOCUS, Vector3.UP)

	skeleton = _find_skeleton(model)
	_cache_bones()
	_cache_expressions()
	_restore_bone_poses()
	_create_hud()
	_create_interaction_ui()
	_set_hud_visible(false)
	_update_hud()
	_connect_core()
	print("GODOT_AVATAR_INTERACTION_READY", {
		"skeleton": skeleton != null,
		"cached_bones": bone_ids.size(),
		"pigtail_roots": pigtail_root_ids.size(),
		"expressions": expression_ids.size(),
		"desktop_overlay": DisplayServer.get_name() != "headless",
		"core_url": core_ws_url,
		"controls": "left-drag=move right-drag=turn wheel=zoom F1=hud arrows=turn R=reset N=nod W=wave Space=greet B=blink S=smile O=surprised X=angry L=wink T=tears",
	})

	await get_tree().process_frame
	await get_tree().process_frame
	if DisplayServer.get_name() != "headless":
		var viewport_texture := get_viewport().get_texture()
		var image := viewport_texture.get_image()
		image.save_png("res://avatar_runtime_preview.png")
		print("GODOT_AVATAR_PREVIEW_SAVED res://avatar_runtime_preview.png")
	else:
		print("GODOT_AVATAR_PREVIEW_SKIPPED dummy display driver")

	if DisplayServer.get_name() == "headless":
		get_tree().quit()


func _process(delta: float) -> void:
	elapsed += delta
	_process_core_bridge(delta)
	current_yaw = lerp_angle(current_yaw, target_yaw, 1.0 - exp(-delta * 8.0))
	current_distance = lerp(current_distance, target_distance, 1.0 - exp(-delta * 8.0))

	model.rotation = base_model_rotation + Vector3(0.0, current_yaw, 0.0)
	model.position = base_model_position + Vector3(0.0, sin(elapsed * 1.6) * 0.004, 0.0)
	camera.position = Vector3(0.0, CAMERA_FOCUS.y, current_distance)
	camera.look_at(CAMERA_FOCUS, Vector3.UP)

	if action_name != "idle":
		action_elapsed += delta
		if action_elapsed >= action_duration:
			action_name = "idle"
			action_elapsed = 0.0
			_restore_bone_poses()
			_update_hud()
	_apply_action_pose()
	_apply_pigtail_pose()
	_process_speaking_mouth(delta)
	_process_expressions(delta)


func _connect_core() -> void:
	if core_socket != null:
		return
	var socket := WebSocketPeer.new()
	var connection_error := socket.connect_to_url(core_ws_url)
	if connection_error != OK:
		core_connection_state = "offline"
		core_reconnect_timer = CORE_RECONNECT_DELAY
		_update_hud()
		return
	core_socket = socket
	core_connection_state = "connecting"
	core_client_announced = false
	_update_hud()


func _process_core_bridge(delta: float) -> void:
	if core_socket == null:
		core_reconnect_timer -= delta
		if core_reconnect_timer <= 0.0:
			_connect_core()
		return

	core_socket.poll()
	var socket_state := core_socket.get_ready_state()
	if socket_state == WebSocketPeer.STATE_OPEN:
		if not core_client_announced:
			core_client_announced = true
			core_connection_state = "online"
			core_socket.send_text(JSON.stringify({
				"type": "client.hello",
				"role": "avatar",
			}))
			print("GODOT_AVATAR_CORE_CONNECTED", core_ws_url)
			_update_hud()
		while core_socket.get_available_packet_count() > 0:
			var packet_text := core_socket.get_packet().get_string_from_utf8()
			var payload: Variant = JSON.parse_string(packet_text)
			if payload is Dictionary:
				_handle_core_event(payload)
	elif socket_state == WebSocketPeer.STATE_CLOSED:
		_schedule_core_reconnect()


func _schedule_core_reconnect() -> void:
	if core_connection_state == "online":
		print("GODOT_AVATAR_CORE_DISCONNECTED")
	core_socket = null
	core_connection_state = "offline"
	core_client_announced = false
	core_reconnect_timer = CORE_RECONNECT_DELAY
	_update_hud()


func _create_interaction_ui() -> void:
	var interaction_script = preload("res://interaction_ui.gd")
	interaction_ui = interaction_script.new(self)
	add_child(interaction_ui)


func _handle_core_event(payload: Dictionary) -> void:
	var event_type := str(payload.get("type", ""))
	match event_type:
		"core.status":
			core_connection_state = str(payload.get("status", "online"))
			_update_hud()
		"client.ready":
			print("GODOT_AVATAR_CORE_READY", payload)
		"agent.state":
			_set_agent_state(str(payload.get("state", "idle")))
		"chat.response":
			if interaction_ui != null:
				interaction_ui.add_message("洛天依", str(payload.get("text", "")))
		"voice.state":
			if interaction_ui != null:
				interaction_ui.on_voice_state(str(payload.get("state", "idle")))
		"voice.transcript":
			if interaction_ui != null:
				interaction_ui.on_voice_transcript(str(payload.get("text", "")))
		"avatar.command":
			var command := str(payload.get("event", ""))
			var command_payload: Variant = payload.get("payload", {})
			if command_payload is Dictionary:
				print("GODOT_AVATAR_COMMAND", command)
				handle_agent_event(command, command_payload)
		"core.error":
			_set_agent_state("error")
			if interaction_ui != null:
				interaction_ui.show_error(str(payload.get("message", "Core 发生错误")))


func _set_agent_state(next_state: String) -> void:
	if next_state not in ["idle", "thinking", "speaking", "working", "error"]:
		return
	agent_state = next_state
	print("GODOT_AVATAR_AGENT_STATE", agent_state)
	_clear_mouth_shapes()
	_clear_emotions()
	match agent_state:
		"thinking":
			_set_expression("じと目", 0.28)
			expression_name = "思考中"
		"speaking":
			_set_expression("笑い", 0.18)
			speaking_mouth_elapsed = 0.0
			speaking_mouth_index = -1
			expression_name = "说话中"
		"working":
			_set_expression("じと目", 0.18)
			expression_name = "工作中"
		"error":
			_set_expression("困る", 0.72)
			expression_name = "连接异常"
		_:
			expression_name = "自然"
	_update_hud()


func _clear_mouth_shapes() -> void:
	for mouth_name in SPEAKING_MOUTHS:
		_set_expression(mouth_name, 0.0)


func _process_speaking_mouth(delta: float) -> void:
	if agent_state != "speaking":
		return
	speaking_mouth_elapsed += delta
	var next_index := int(floor(speaking_mouth_elapsed * 8.0)) % SPEAKING_MOUTHS.size()
	if next_index == speaking_mouth_index:
		return
	speaking_mouth_index = next_index
	_clear_mouth_shapes()
	_set_expression(SPEAKING_MOUTHS[speaking_mouth_index], 0.62)


func _input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mouse_event := event as InputEventMouseButton
		if mouse_event.button_index == MOUSE_BUTTON_LEFT:
			if interaction_ui != null and interaction_ui.is_pointer_over_ui(mouse_event.position):
				return
			if mouse_event.pressed:
				left_pressing = true
				left_dragging = false
				left_press_position = mouse_event.position
			else:
				if left_dragging:
					call_deferred("_save_window_position")
				elif left_pressing and interaction_ui != null:
					interaction_ui.toggle_menu()
				left_pressing = false
				left_dragging = false
			get_viewport().set_input_as_handled()
		elif mouse_event.button_index == MOUSE_BUTTON_RIGHT:
			rotation_dragging = mouse_event.pressed
			last_pointer = mouse_event.position
			get_viewport().set_input_as_handled()
		elif mouse_event.pressed and mouse_event.button_index == MOUSE_BUTTON_WHEEL_UP:
			target_distance = max(MIN_CAMERA_DISTANCE, target_distance - 0.25)
			_update_hud()
			get_viewport().set_input_as_handled()
		elif mouse_event.pressed and mouse_event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			target_distance = min(MAX_CAMERA_DISTANCE, target_distance + 0.25)
			_update_hud()
			get_viewport().set_input_as_handled()
		return

	if event is InputEventMouseMotion and left_pressing and not left_dragging:
		var move_event := event as InputEventMouseMotion
		if move_event.position.distance_to(left_press_position) >= 8.0:
			left_dragging = true
			if interaction_ui != null:
				interaction_ui.hide_all()
			DisplayServer.window_start_drag()
			get_viewport().set_input_as_handled()
		return

	if event is InputEventMouseMotion and rotation_dragging:
		var motion_event := event as InputEventMouseMotion
		target_yaw -= motion_event.relative.x * 0.012
		last_pointer = motion_event.position
		_update_hud()
		get_viewport().set_input_as_handled()
		return

	if event is InputEventKey:
		var focus_owner := get_viewport().gui_get_focus_owner()
		if focus_owner is LineEdit or focus_owner is TextEdit:
			return
		var key_event := event as InputEventKey
		if not key_event.pressed or key_event.echo:
			return
		var shortcut_handled := true
		match key_event.keycode:
			KEY_LEFT, KEY_A:
				handle_agent_event("avatar.turn_left")
			KEY_RIGHT, KEY_D:
				handle_agent_event("avatar.turn_right")
			KEY_R:
				handle_agent_event("avatar.reset")
			KEY_N:
				handle_agent_event("avatar.nod")
			KEY_W:
				handle_agent_event("avatar.wave")
			KEY_SPACE:
				handle_agent_event("avatar.greet")
			KEY_B:
				handle_agent_event("avatar.blink")
			KEY_S:
				handle_agent_event("avatar.smile")
			KEY_O:
				handle_agent_event("avatar.surprised")
			KEY_X:
				handle_agent_event("avatar.angry")
			KEY_L:
				handle_agent_event("avatar.wink")
			KEY_T:
				handle_agent_event("avatar.tears")
			KEY_F1:
				_set_hud_visible(not hud_visible)
			KEY_ESCAPE:
				get_tree().quit()
			_:
				shortcut_handled = false
		if shortcut_handled:
			get_viewport().set_input_as_handled()


func handle_agent_event(event_type: String, payload: Dictionary = {}) -> void:
	match event_type:
		"avatar.turn_left":
			target_yaw -= deg_to_rad(float(payload.get("degrees", 30.0)))
			action_name = "idle"
			_restore_bone_poses()
		"avatar.turn_right":
			target_yaw += deg_to_rad(float(payload.get("degrees", 30.0)))
			action_name = "idle"
			_restore_bone_poses()
		"avatar.reset":
			target_yaw = 0.0
			action_name = "idle"
			_restore_bone_poses()
			_clear_emotions()
			expression_name = "自然"
		"avatar.nod":
			_start_action("nod", 1.35)
		"avatar.wave":
			_start_action("wave", 2.35)
		"avatar.greet":
			_start_action("greet", 2.35)
			_show_emotion("笑い", "微笑", 0.78, 2.35)
			_set_expression("ウィンク", 0.72, 1.1)
		"avatar.blink":
			_trigger_blink()
		"avatar.smile":
			_show_emotion("笑い", "微笑", clampf(float(payload.get("intensity", 0.85)), 0.0, 1.0), 2.4)
		"avatar.surprised":
			_show_emotion("びっくり", "惊讶", clampf(float(payload.get("intensity", 0.9)), 0.0, 1.0), 1.6)
		"avatar.angry":
			_show_emotion("怒り", "生气", clampf(float(payload.get("intensity", 0.82)), 0.0, 1.0), 1.8)
		"avatar.wink":
			_set_expression("ウィンク右", 0.95, 1.2)
			_set_expression("笑い", 0.45, 1.2)
			expression_name = "右眼单眨"
		"avatar.tears":
			_show_emotion("眼泪", "眼泪", clampf(float(payload.get("intensity", 0.92)), 0.0, 1.0), 2.4)
		"avatar.mouth_a":
			_show_mouth("あ", "口型 あ")
		"avatar.mouth_i":
			_show_mouth("い", "口型 い")
		"avatar.mouth_u":
			_show_mouth("う", "口型 う")
		"avatar.mouth_e":
			_show_mouth("え", "口型 え")
		"avatar.mouth_o":
			_show_mouth("お", "口型 お")
		"avatar.expression":
			var expression_key := str(payload.get("name", ""))
			var expression_value := clampf(float(payload.get("value", 1.0)), 0.0, 1.0)
			var expression_duration := maxf(float(payload.get("duration", 1.5)), 0.0)
			_set_expression(expression_key, expression_value, expression_duration)
			expression_name = expression_key if expression_key != "" else "自定义"
	_update_hud()


func send_chat_message(text: String) -> void:
	var normalized_text := text.strip_edges()
	if normalized_text.is_empty():
		return
	if core_socket == null or core_socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
		if interaction_ui != null:
			interaction_ui.show_error("Core 尚未连接，消息暂时没有发送。")
		return
	var request_id := "avatar-chat-%d" % Time.get_ticks_msec()
	core_socket.send_text(JSON.stringify({
		"type": "chat.message",
		"text": normalized_text,
		"messageId": request_id,
	}))
	_set_agent_state("thinking")


func start_voice_recording() -> void:
	if core_socket == null or core_socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
		if interaction_ui != null:
			interaction_ui.show_error("Core 尚未连接，无法录音。")
		return
	core_socket.send_text(JSON.stringify({"type": "voice.start"}))


func stop_voice_recording() -> void:
	if core_socket == null or core_socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
		return
	core_socket.send_text(JSON.stringify({"type": "voice.stop"}))


func _start_action(next_action: String, duration: float) -> void:
	action_name = next_action
	action_elapsed = 0.0
	action_duration = duration
	_restore_bone_poses()


func _apply_action_pose() -> void:
	if skeleton == null or action_name == "idle":
		return

	var progress: float = clampf(action_elapsed / action_duration, 0.0, 1.0)
	var fade: float = minf(minf(progress / 0.18, (1.0 - progress) / 0.22), 1.0)

	if action_name == "nod" or action_name == "greet":
		var nod_angle := sin(action_elapsed * PI * 3.5) * deg_to_rad(11.0) * fade
		_set_bone_offset("首", Quaternion(Vector3.RIGHT, nod_angle * 0.45))
		_set_bone_offset("頭", Quaternion(Vector3.RIGHT, nod_angle))

	if action_name == "wave" or action_name == "greet":
		var lift := deg_to_rad(110.0) * fade
		var wave_angle := sin(action_elapsed * PI * 4.5) * deg_to_rad(22.0) * fade
		_set_bone_offset("腕.R", Quaternion(Vector3.RIGHT, lift))
		_set_bone_offset("ひじ.R", Quaternion(Vector3.UP, wave_angle))
		_set_bone_offset("手首.R", Quaternion(Vector3.FORWARD, wave_angle * 0.7))

	if action_name == "greet":
		model.rotation.z = base_model_rotation.z + sin(action_elapsed * PI * 2.0) * deg_to_rad(1.8) * fade


func _apply_pigtail_pose() -> void:
	if skeleton == null:
		return
	for position in range(pigtail_root_ids.size()):
		var bone_index: int = pigtail_root_ids[position]
		var side_sign := -1.0 if position == 0 else 1.0
		var phase := float(position) * PI
		var sway := sin(elapsed * 1.1 + phase) * deg_to_rad(PIGTAIL_SWAY_AMPLITUDE)
		var settle := cos(elapsed * 0.8 + phase) * deg_to_rad(0.6)
		var offset := Quaternion(Vector3.RIGHT, deg_to_rad(PIGTAIL_TILT_ANGLE) + sway) \
			* Quaternion(Vector3.UP, deg_to_rad(PIGTAIL_INWARD_ANGLE * side_sign)) \
			* Quaternion(Vector3.FORWARD, deg_to_rad(PIGTAIL_DEPTH_ANGLE * side_sign) + settle)
		skeleton.set_bone_pose_rotation(bone_index, pigtail_base_rotations[bone_index] * offset)


func _set_bone_offset(bone_name: String, offset: Quaternion) -> void:
	if not bone_ids.has(bone_name):
		return
	var bone_index: int = bone_ids[bone_name]
	skeleton.set_bone_pose_rotation(bone_index, rest_bone_rotations[bone_index] * offset)


func _restore_bone_poses() -> void:
	if skeleton == null:
		return
	for bone_index in base_bone_rotations:
		skeleton.set_bone_pose_rotation(bone_index, rest_bone_rotations[bone_index])


func _find_skeleton(node: Node) -> Skeleton3D:
	if node is Skeleton3D:
		return node as Skeleton3D
	for child in node.get_children():
		var found := _find_skeleton(child)
		if found:
			return found
	return null


func _cache_bones() -> void:
	if skeleton == null:
		return
	for bone_name in ["首", "頭", "腕.R", "ひじ.R", "手首.R", "腕.L", "ひじ.L", "手首.L"]:
		var bone_index := skeleton.find_bone(bone_name)
		if bone_index >= 0:
			bone_ids[bone_name] = bone_index
			base_bone_rotations[bone_index] = skeleton.get_bone_pose_rotation(bone_index)
			var rest_offset := Quaternion.IDENTITY
			if bone_name == "腕.R":
				rest_offset = Quaternion(Vector3.RIGHT, deg_to_rad(-48.0))
			elif bone_name == "腕.L":
				rest_offset = Quaternion(Vector3.RIGHT, deg_to_rad(48.0))
			rest_bone_rotations[bone_index] = base_bone_rotations[bone_index] * rest_offset

	for pigtail_name in ["MaWei_R_0_1", "MaWei_L_0_1"]:
		var pigtail_index := skeleton.find_bone(pigtail_name)
		if pigtail_index >= 0:
			pigtail_root_ids.append(pigtail_index)
			var pigtail_base := skeleton.get_bone_pose_rotation(pigtail_index)
			base_bone_rotations[pigtail_index] = pigtail_base
			pigtail_base_rotations[pigtail_index] = pigtail_base
			var side_sign := -1.0 if pigtail_name == "MaWei_R_0_1" else 1.0
			var pigtail_rest_offset := Quaternion(Vector3.RIGHT, deg_to_rad(PIGTAIL_TILT_ANGLE)) \
				* Quaternion(Vector3.UP, deg_to_rad(PIGTAIL_INWARD_ANGLE * side_sign)) \
				* Quaternion(Vector3.FORWARD, deg_to_rad(PIGTAIL_DEPTH_ANGLE * side_sign))
			var pigtail_rest := pigtail_base * pigtail_rest_offset
			pigtail_rest_rotations[pigtail_index] = pigtail_rest
			rest_bone_rotations[pigtail_index] = pigtail_rest


func _find_mesh_instance(node: Node) -> MeshInstance3D:
	if node is MeshInstance3D:
		return node as MeshInstance3D
	for child in node.get_children():
		var found := _find_mesh_instance(child)
		if found != null:
			return found
	return null


func _cache_expressions() -> void:
	face_mesh = _find_mesh_instance(model)
	if face_mesh == null or face_mesh.mesh == null:
		return
	var mesh: Mesh = face_mesh.mesh
	for blend_index in range(mesh.get_blend_shape_count()):
		var blend_name: String = mesh.get_blend_shape_name(blend_index)
		expression_ids[blend_name] = blend_index
		expression_values[blend_name] = 0.0
		expression_targets[blend_name] = 0.0
		expression_timers[blend_name] = 0.0


func _set_expression(name: String, value: float, duration: float = 0.0) -> void:
	if not expression_ids.has(name):
		return
	expression_targets[name] = clampf(value, 0.0, 1.0)
	expression_timers[name] = maxf(duration, 0.0)


func _clear_emotions() -> void:
	for name in ["笑い", "にやり", "じと目", "びっくり", "困る", "怒り", "怒り２", "眼泪", "汗", "愛心眼", "星星眼", "圈圈眼"]:
		_set_expression(name, 0.0)


func _show_emotion(name: String, label: String, value: float, duration: float) -> void:
	_clear_emotions()
	_set_expression(name, value, duration)
	expression_name = label


func _show_mouth(name: String, label: String) -> void:
	for mouth_name in ["あ", "い", "う", "え", "お", "ん"]:
		_set_expression(mouth_name, 0.0)
	_set_expression(name, 0.9, 1.15)
	expression_name = label


func _trigger_blink() -> void:
	_set_expression("まばたき", 1.0, 0.18)
	blink_timer = 4.0
	expression_name = "眨眼"


func _process_expressions(delta: float) -> void:
	if face_mesh == null:
		return
	blink_timer -= delta
	if action_name == "idle" and blink_timer <= 0.0:
		_trigger_blink()
		blink_timer = 3.4 + fmod(elapsed * 0.37, 1.8)
	for name in expression_timers.keys():
		var remaining := float(expression_timers[name])
		if remaining > 0.0:
			remaining -= delta
			if remaining <= 0.0:
				expression_targets[name] = 0.0
			expression_timers[name] = maxf(remaining, 0.0)
	for name in expression_ids.keys():
		var current := float(expression_values[name])
		var target := float(expression_targets[name])
		current = lerpf(current, target, 1.0 - exp(-delta * 18.0))
		expression_values[name] = current
		face_mesh.set_blend_shape_value(int(expression_ids[name]), current)
	if expression_name != "自然" and _expressions_are_neutral():
		expression_name = "自然"
		_update_hud()


func _expressions_are_neutral() -> bool:
	for name in expression_values.keys():
		if float(expression_values[name]) > 0.06:
			return false
	return true


func _configure_desktop_window() -> void:
	get_viewport().transparent_bg = true
	if DisplayServer.get_name() == "headless":
		return
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_BORDERLESS, true)
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_ALWAYS_ON_TOP, true)
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_RESIZE_DISABLED, true)
	var interaction_region := PackedVector2Array([
		Vector2(232.0, 138.0),
		Vector2(328.0, 138.0),
		Vector2(352.0, 232.0),
		Vector2(438.0, 330.0),
		Vector2(430.0, 402.0),
		Vector2(356.0, 358.0),
		Vector2(354.0, 650.0),
		Vector2(314.0, 690.0),
		Vector2(246.0, 690.0),
		Vector2(206.0, 650.0),
		Vector2(204.0, 358.0),
		Vector2(130.0, 402.0),
		Vector2(122.0, 330.0),
		Vector2(208.0, 232.0),
	])
	DisplayServer.window_set_mouse_passthrough(interaction_region)
	call_deferred("_restore_window_position")


func _restore_window_position() -> void:
	var config := ConfigFile.new()
	if config.load(WINDOW_SETTINGS_PATH) != OK:
		return
	var saved_position: Variant = config.get_value("window", "position", null)
	if saved_position is not Vector2i:
		return
	var screen_count := DisplayServer.get_screen_count()
	var screen_index := int(config.get_value("window", "screen", -1))
	if screen_index < 0 or screen_index >= screen_count:
		screen_index = DisplayServer.window_get_current_screen()
		for candidate_screen in range(screen_count):
			if DisplayServer.screen_get_usable_rect(candidate_screen).has_point(saved_position):
				screen_index = candidate_screen
				break
	DisplayServer.window_set_current_screen(screen_index)
	var usable_rect := DisplayServer.screen_get_usable_rect(screen_index)
	var window_size := DisplayServer.window_get_size()
	var maximum := usable_rect.position + usable_rect.size - window_size
	var clamped_position := Vector2i(
		clampi(saved_position.x, usable_rect.position.x, maximum.x),
		clampi(saved_position.y, usable_rect.position.y, maximum.y)
	)
	DisplayServer.window_set_position(clamped_position)


func _save_window_position() -> void:
	if DisplayServer.get_name() == "headless":
		return
	var config := ConfigFile.new()
	config.set_value("window", "position", DisplayServer.window_get_position())
	config.set_value("window", "screen", DisplayServer.window_get_current_screen())
	var save_error := config.save(WINDOW_SETTINGS_PATH)
	if save_error != OK:
		push_warning("Unable to save avatar window position: %s" % error_string(save_error))


func _set_hud_visible(next_visible: bool) -> void:
	hud_visible = next_visible
	if hud_canvas != null:
		hud_canvas.visible = hud_visible


func _create_hud() -> void:
	var canvas := CanvasLayer.new()
	canvas.name = "InteractionHud"
	add_child(canvas)
	hud_canvas = canvas

	var panel := ColorRect.new()
	panel.position = Vector2(22.0, 22.0)
	panel.size = Vector2(520.0, 168.0)
	panel.color = Color(0.025, 0.025, 0.04, 0.86)
	panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	canvas.add_child(panel)

	var title := Label.new()
	title.position = Vector2(18.0, 12.0)
	title.text = "洛天依 · 3D AVATAR MVP"
	title.add_theme_color_override("font_color", Color(0.75, 0.82, 1.0))
	title.add_theme_font_size_override("font_size", 18)
	title.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.add_child(title)

	action_label = Label.new()
	action_label.position = Vector2(20.0, 48.0)
	action_label.add_theme_color_override("font_color", Color(0.96, 0.96, 1.0))
	action_label.add_theme_font_size_override("font_size", 14)
	action_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.add_child(action_label)

	camera_label = Label.new()
	camera_label.position = Vector2(20.0, 76.0)
	camera_label.add_theme_color_override("font_color", Color(0.68, 0.68, 0.78))
	camera_label.add_theme_font_size_override("font_size", 12)
	camera_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.add_child(camera_label)

	expression_label = Label.new()
	expression_label.position = Vector2(20.0, 100.0)
	expression_label.add_theme_color_override("font_color", Color(0.83, 0.78, 0.98))
	expression_label.add_theme_font_size_override("font_size", 12)
	expression_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.add_child(expression_label)

	core_label = Label.new()
	core_label.position = Vector2(20.0, 124.0)
	core_label.add_theme_color_override("font_color", Color(0.56, 0.86, 0.78))
	core_label.add_theme_font_size_override("font_size", 12)
	core_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.add_child(core_label)

	var footer := Label.new()
	footer.position = Vector2(22.0, 684.0)
	footer.text = "左键拖动人物位置 · 右键拖拽转身 · 滚轮缩放 · F1 调试信息\n←/→ 转身 · R 回正 · N 点头 · W 挥手 · Space 打招呼 · Esc 退出"
	footer.add_theme_color_override("font_color", Color(0.78, 0.78, 0.86))
	footer.add_theme_font_size_override("font_size", 13)
	footer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	canvas.add_child(footer)


func _update_hud() -> void:
	if action_label == null:
		return
	var action_text: String = str({
		"idle": "状态：待机 · 呼吸中",
		"nod": "状态：点头",
		"wave": "状态：挥手",
		"greet": "状态：打招呼",
	}.get(action_name, "状态：互动"))
	action_label.text = action_text
	camera_label.text = "朝向：%d°    距离：%.1f" % [roundi(rad_to_deg(current_yaw)), current_distance]
	if expression_label != null:
		expression_label.text = "表情：%s" % expression_name
	if core_label != null:
		core_label.text = "Core：%s    Agent：%s" % [core_connection_state, agent_state]
