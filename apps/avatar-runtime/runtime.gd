extends Node3D


const MIN_CAMERA_DISTANCE := 2.7
const MAX_CAMERA_DISTANCE := 5.2
const CAMERA_FOCUS := Vector3(0.0, 0.88, 0.0)
const BASE_VIEWPORT_SIZE := Vector2(560.0, 760.0)
const BASE_AVATAR_CENTER := BASE_VIEWPORT_SIZE * 0.5
const BASE_CAMERA_DISTANCE := 3.8
const BASE_CAMERA_FOV := 35.0
## The desktop compositor keeps extra transparent room around the avatar. The
## camera FOV is derived from this size, so the model keeps the same apparent
## size while large gestures have room to leave the idle silhouette.
const AVATAR_COMPOSITE_SIZE := Vector2(960.0, 1160.0)
const AVATAR_RENDER_SCALE := 2.0
const CANVAS_MODE_ENV := "ANIME_AGENT_CANVAS_MODE"
const CANVAS_MODE_DESKTOP := "desktop"
const CANVAS_MODE_COMPACT := "compact"
const PIGTAIL_TILT_ANGLE := 0.0
const PIGTAIL_INWARD_ANGLE := -30.0
const PIGTAIL_DEPTH_ANGLE := 0.0
const PIGTAIL_SWAY_AMPLITUDE := 1.6
const PIGTAIL_CHAIN_SWAY_AMPLITUDE := 0.32
const PIGTAIL_CHAIN_PHASE_DELAY := 0.16
const WAVE_UPPER_ARM_ANGLE := 72.0
const WAVE_ELBOW_BEND_ANGLE := 68.0
const WAVE_ELBOW_SWAY_ANGLE := 8.0
const WAVE_WRIST_ROLL_ANGLE := 70.0
const WAVE_WRIST_SWAY_ANGLE := 14.0
## Keep animated arm chains readable from the fixed desktop camera. A value of
## 1.0 means a segment lies in the camera plane; 0.0 means it points directly
## into the camera and collapses to almost no visible pixels.
const MIN_LIMB_CAMERA_PLANE_VISIBILITY := 0.72
const MAX_LIMB_READABILITY_CORRECTION := 60.0
const READABILITY_ARM_CHAINS := [
	["腕.R", "ひじ.R", "手首.R", "中指先.R"],
	["腕.L", "ひじ.L", "手首.L", "中指先.L"],
]
## The official MMD mesh is weighted to the D deform-leg chain while imported
## humanoid clips animate the parallel control chain. Mirror control movement
## in skeleton space so the vertices follow the authored leg motion.
const MMD_DEFORM_BONE_MIRRORS := [
	["足.L", "足D.L"], ["ひざ.L", "ひざD.L"], ["足首.L", "足首D.L"],
	["足.R", "足D.R"], ["ひざ.R", "ひざD.R"], ["足首.R", "足首D.R"],
]
const MOTION_LAYER_FULL_BODY := "full_body"
const MOTION_LAYER_UPPER_BODY := "upper_body"
const MOTION_LAYER_LOWER_BODY := "lower_body"
const WINDOW_SETTINGS_PATH := "user://avatar_window.cfg"
const DEFAULT_CORE_WS_URL := "ws://127.0.0.1:8765/ws"
const CORE_RECONNECT_DELAY := 2.0
const SPEAKING_MOUTHS := ["あ", "い", "う", "え", "お"]
const AUTHORED_MOTION_REGISTRY_PATH := "res://motion_registry.json"
const AUTHORED_MOTION_ENV := "ANIME_AGENT_USE_AUTHORED_MOTION"
const AUTHORED_MOTION_AUTOPLAY_ENV := "ANIME_AGENT_AUTOPLAY_MOTION"
const MODEL_LOOK_ENV := "ANIME_AGENT_MODEL_LOOK"
const MODEL_LOOK_V12 := "1.2"
const MODEL_LOOK_CURRENT := "1.3"
const ModelLookV13 := preload("res://model_look_v13.gd")
const MODEL_LOOK_TARGETS := {
	"face": {"albedo": 0.24, "emission": 0.86, "roughness": 0.92, "rim": 0.04},
	"body": {"albedo": 0.24, "emission": 0.86, "roughness": 0.92, "rim": 0.04},
	"hand": {"albedo": 0.24, "emission": 0.86, "roughness": 0.92, "rim": 0.04},
	"leg": {"albedo": 0.24, "emission": 0.86, "roughness": 0.92, "rim": 0.04},
	"fronthair": {"albedo": 0.42, "emission": 0.72, "roughness": 0.86, "rim": 0.10},
	"backhair": {"albedo": 0.42, "emission": 0.72, "roughness": 0.86, "rim": 0.10},
	"tail": {"albedo": 0.42, "emission": 0.72, "roughness": 0.86, "rim": 0.10},
	"clothes1": {"albedo": 0.36, "emission": 0.78, "roughness": 0.88, "rim": 0.07},
	"clothes2": {"albedo": 0.36, "emission": 0.78, "roughness": 0.88, "rim": 0.07},
	"skirt": {"albedo": 0.36, "emission": 0.78, "roughness": 0.88, "rim": 0.07},
}

@onready var model: Node3D = $LuoTianyi
@onready var camera: Camera3D = $Camera3D
@onready var world_environment: WorldEnvironment = $Environment
@onready var key_light: DirectionalLight3D = $KeyLight
@onready var fill_light: DirectionalLight3D = $FillLight

var authored_motion_player: AnimationPlayer
var portrait_capture = preload("res://portrait_capture.gd").new()
var authored_motion_name: StringName = &""
var authored_motion_clips: Dictionary = {}
var default_idle_motion: StringName = &""
var authored_motion_active := false
var model_uses_authored_motion := false
var voice_recording_active := false

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
var canvas_mode := CANVAS_MODE_DESKTOP
var avatar_screen_center := BASE_AVATAR_CENTER
var ui_overlay_active := false
var desktop_screen_index := 0
var last_passthrough_signature := ""
var avatar_render_viewport: SubViewport
var avatar_render_canvas: CanvasLayer
var avatar_texture_rect: TextureRect
var avatar_interaction_region := PackedVector2Array([
	Vector2(232.0, 138.0), Vector2(328.0, 138.0), Vector2(352.0, 232.0),
	Vector2(438.0, 330.0), Vector2(430.0, 402.0), Vector2(356.0, 358.0),
	Vector2(354.0, 650.0), Vector2(314.0, 690.0), Vector2(246.0, 690.0),
	Vector2(206.0, 650.0), Vector2(204.0, 358.0), Vector2(130.0, 402.0),
	Vector2(122.0, 330.0), Vector2(208.0, 232.0),
])

var base_model_rotation := Vector3.ZERO
var base_model_position := Vector3.ZERO
var skeleton: Skeleton3D
var bone_ids: Dictionary = {}
var base_bone_rotations: Dictionary = {}
var rest_bone_rotations: Dictionary = {}
var action_axes: Dictionary = {}
var deform_bone_mirrors: Array = []
var deform_mirror_base_global_poses: Dictionary = {}
var pigtail_root_ids: Array[int] = []
var pigtail_chains: Array = []
var pigtail_base_rotations: Dictionary = {}
var pigtail_rest_rotations: Dictionary = {}
var motion_layer_bones: Dictionary = {}

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

# E-phase TTS playback state
var speech_player: AudioStreamPlayer = null
var current_utterance_id := ""
var model_look_preview_enabled := false
var model_look_version := "1.1"
var model_look_original_overrides: Dictionary = {}
var model_look_preview_materials: Dictionary = {}
var model_look_v13_materials: Dictionary = {}

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
	## AnimationPlayer is a child node. Run this controller after child animation
	## tracks so camera-readability and pigtail corrections are the final pose
	## written before rendering, rather than being overwritten in the same frame.
	process_priority = 100
	var configured_core_url := OS.get_environment("AGENT_CORE_WS_URL").strip_edges()
	if not configured_core_url.is_empty():
		core_ws_url = configured_core_url
	_configure_desktop_window()
	_configure_avatar_render_surface()
	base_model_rotation = model.rotation
	base_model_position = model.position
	camera.position = Vector3(0.0, CAMERA_FOCUS.y, current_distance)
	camera.look_at(CAMERA_FOCUS, Vector3.UP)

	skeleton = _find_skeleton(model)
	_cache_bones()
	_cache_deform_bone_mirrors()
	_cache_expressions()
	_configure_model_look()
	_restore_bone_poses()
	_cache_action_axes()
	_prepare_authored_motions()
	_create_hud()
	_create_interaction_ui()
	_set_hud_visible(false)
	_update_hud()
	_connect_core()
	print("GODOT_AVATAR_INTERACTION_READY", {
		"skeleton": skeleton != null,
		"cached_bones": bone_ids.size(),
		"pigtail_roots": pigtail_root_ids.size(),
		"pigtail_chain_lengths": pigtail_chains.map(func(chain: Array) -> int: return chain.size()),
		"motion_layers": _motion_layer_sizes(),
		"expressions": expression_ids.size(),
		"model_look": model_look_version,
		"authored_motions": authored_motion_clips.keys(),
		"desktop_overlay": DisplayServer.get_name() != "headless",
		"core_url": core_ws_url,
		"controls": "left-drag=move right-drag=turn wheel=zoom F1=hud F12=portrait arrows=turn R=reset N=nod W=wave P=authored-motion G=listen Space=greet B=blink S=smile O=surprised X=angry L=wink T=tears",
	})
	if model_uses_authored_motion:
		var requested_motion := OS.get_environment(AUTHORED_MOTION_AUTOPLAY_ENV).strip_edges()
		if requested_motion.is_empty():
			call_deferred("_play_default_idle_motion")
		elif requested_motion.to_lower() in ["1", "true", "yes", "on"]:
			call_deferred("_play_authored_motion", &"pirouette")
		else:
			call_deferred("_play_authored_motion", StringName(requested_motion))

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
	if canvas_mode == CANVAS_MODE_DESKTOP:
		var center_before_clamp := avatar_screen_center
		_clamp_avatar_screen_center()
		if not avatar_screen_center.is_equal_approx(center_before_clamp):
			_sync_avatar_texture_rect()
			_sync_interaction_ui_origin()

	model.rotation = base_model_rotation + Vector3(0.0, current_yaw, 0.0)
	var procedural_bob := 0.0 if authored_motion_active else sin(elapsed * 1.6) * 0.004
	model.position = base_model_position + Vector3(0.0, procedural_bob, 0.0)
	camera.position = Vector3(0.0, CAMERA_FOCUS.y, current_distance)
	camera.look_at(CAMERA_FOCUS, Vector3.UP)
	_update_mouse_passthrough()

	if not authored_motion_active and action_name != "idle":
		action_elapsed += delta
		if action_elapsed >= action_duration:
			action_name = "idle"
			action_elapsed = 0.0
			_restore_bone_poses()
			_update_hud()
			_play_default_idle_motion()
	if not authored_motion_active:
		_apply_action_pose()
	_sync_deform_bone_mirrors()
	_preserve_limb_readability()
	_apply_pigtail_pose()
	_process_speaking_mouth(delta)
	_process_expressions(delta)


func _prepare_authored_motions() -> void:
	if not _environment_flag(AUTHORED_MOTION_ENV, true):
		return
	if skeleton == null or not FileAccess.file_exists(AUTHORED_MOTION_REGISTRY_PATH):
		return
	var registry_data: Variant = JSON.parse_string(
		FileAccess.get_file_as_string(AUTHORED_MOTION_REGISTRY_PATH)
	)
	if registry_data is not Dictionary or registry_data.get("clips", null) is not Array:
		push_warning("Invalid authored motion registry: %s" % AUTHORED_MOTION_REGISTRY_PATH)
		return

	authored_motion_player = AnimationPlayer.new()
	authored_motion_player.name = "AuthoredMotionPlayer"
	authored_motion_player.root_node = NodePath("..")
	add_child(authored_motion_player)
	var motion_library := AnimationLibrary.new()
	var remapped_tracks := 0
	default_idle_motion = StringName(str(registry_data.get("default_idle", "")))
	for clip_data in registry_data.get("clips", []):
		if clip_data is not Dictionary:
			continue
		var clip_id := StringName(str(clip_data.get("id", "")))
		var clip_path := str(clip_data.get("path", ""))
		if clip_id.is_empty() or clip_path.is_empty() or not ResourceLoader.exists(clip_path):
			continue
		var track_count := _load_authored_motion_clip(clip_id, clip_path, clip_data, motion_library)
		if track_count <= 0:
			continue
		remapped_tracks += track_count
		authored_motion_clips[String(clip_id)] = clip_data.duplicate(true)
	authored_motion_player.add_animation_library(&"", motion_library)
	if authored_motion_clips.is_empty():
		push_warning("Authored motion had no tracks matching the runtime skeleton")
		authored_motion_player.queue_free()
		authored_motion_player = null
		default_idle_motion = &""
		return
	authored_motion_player.animation_finished.connect(_on_authored_motion_finished)
	model_uses_authored_motion = true
	print("GODOT_AUTHORED_MOTIONS_READY", {
		"registry": AUTHORED_MOTION_REGISTRY_PATH,
		"clips": authored_motion_clips.keys(),
		"default_idle": default_idle_motion,
		"remapped_tracks": remapped_tracks,
	})


func _load_authored_motion_clip(
	clip_id: StringName,
	clip_path: String,
	clip_data: Dictionary,
	motion_library: AnimationLibrary,
) -> int:
	var packed_scene := load(clip_path) as PackedScene
	if packed_scene == null:
		return 0
	var motion_source := packed_scene.instantiate() as Node3D
	if motion_source == null:
		return 0
	var source_player := _find_animation_player(motion_source)
	if source_player == null:
		motion_source.free()
		return 0
	var playable_names: Array[StringName] = []
	for candidate in source_player.get_animation_list():
		if candidate != &"RESET":
			playable_names.append(candidate)
	if playable_names.size() != 1:
		push_warning("Motion clip %s must contain exactly one playable animation" % clip_id)
		motion_source.free()
		return 0
	var source_animation := source_player.get_animation(playable_names[0])
	var retargeted_animation := source_animation.duplicate(true) as Animation
	var bone_layer := str(clip_data.get("bone_layer", MOTION_LAYER_FULL_BODY))
	var remapped_tracks := _remap_animation_tracks(retargeted_animation, bone_layer)
	if remapped_tracks > 0:
		if bool(clip_data.get("relaxed_arms", false)):
			_use_reference_arm_tracks(retargeted_animation)
			remapped_tracks = retargeted_animation.get_track_count()
		retargeted_animation.loop_mode = (
			Animation.LOOP_LINEAR if bool(clip_data.get("loop", false)) else Animation.LOOP_NONE
		)
		motion_library.add_animation(clip_id, retargeted_animation)
	if not motion_library.has_animation(&"__RESET") and source_player.has_animation(&"RESET"):
		var reset_animation := source_player.get_animation(&"RESET").duplicate(true) as Animation
		_remap_animation_tracks(reset_animation, MOTION_LAYER_FULL_BODY)
		motion_library.add_animation(&"__RESET", reset_animation)
	motion_source.free()
	return remapped_tracks


func _use_reference_arm_tracks(animation: Animation) -> void:
	## Codex 2026-09-08: conservative idle fallback. Modify only the in-memory
	## animation copy, not the mocap GLB or official mesh/rig. Constant tracks
	## also reset fingers/twist helpers after an interaction. Reuse the original
	## runtime's 48-degree arm lowering: the GLB bind pose alone is a T-pose,
	## whereas the requested reference is the old diagonal-down A-pose.
	var arm_bones := {}
	for side in ["L", "R"]:
		_collect_bone_descendants("肩." + side, arm_bones)
	for track_index in range(animation.get_track_count() - 1, -1, -1):
		var path := animation.track_get_path(track_index)
		if path.get_subname_count() == 0:
			continue
		var bone_index := skeleton.find_bone(str(path.get_subname(path.get_subname_count() - 1)))
		if arm_bones.has(bone_index):
			animation.remove_track(track_index)
	var skeleton_path := get_path_to(skeleton)
	for bone_index in arm_bones:
		var reference := skeleton.get_bone_rest(bone_index)
		var rotation: Quaternion = rest_bone_rotations.get(bone_index, reference.basis.get_rotation_quaternion())
		var path := NodePath("%s:%s" % [skeleton_path, skeleton.get_bone_name(bone_index)])
		var position_track := animation.add_track(Animation.TYPE_POSITION_3D)
		animation.track_set_path(position_track, path)
		animation.position_track_insert_key(position_track, 0.0, reference.origin)
		var rotation_track := animation.add_track(Animation.TYPE_ROTATION_3D)
		animation.track_set_path(rotation_track, path)
		animation.rotation_track_insert_key(rotation_track, 0.0, rotation)
		var scale_track := animation.add_track(Animation.TYPE_SCALE_3D)
		animation.track_set_path(scale_track, path)
		animation.scale_track_insert_key(scale_track, 0.0, reference.basis.get_scale())


func _remap_animation_tracks(animation: Animation, bone_layer: String = MOTION_LAYER_FULL_BODY) -> int:
	var skeleton_path := get_path_to(skeleton)
	var tracks_to_remove: Array[int] = []
	var remapped_tracks := 0
	for track_index in range(animation.get_track_count()):
		var source_path := animation.track_get_path(track_index)
		if source_path.get_subname_count() == 0:
			tracks_to_remove.append(track_index)
			continue
		var bone_name := String(source_path.get_subname(source_path.get_subname_count() - 1))
		var bone_index := skeleton.find_bone(bone_name)
		if bone_index < 0 or not _bone_in_motion_layer(bone_index, bone_layer):
			tracks_to_remove.append(track_index)
			continue
		animation.track_set_path(track_index, NodePath("%s:%s" % [skeleton_path, bone_name]))
		remapped_tracks += 1
	tracks_to_remove.reverse()
	for track_index in tracks_to_remove:
		animation.remove_track(track_index)
	return remapped_tracks


func _bone_in_motion_layer(bone_index: int, bone_layer: String) -> bool:
	if bone_layer == MOTION_LAYER_FULL_BODY:
		return bone_index >= 0 and bone_index < skeleton.get_bone_count()
	if not motion_layer_bones.has(bone_layer):
		push_warning("Unknown motion bone layer '%s'; rejecting track" % bone_layer)
		return false
	return (motion_layer_bones[bone_layer] as Dictionary).has(bone_index)


func _motion_layer_sizes() -> Dictionary:
	var sizes := {}
	for layer_name in motion_layer_bones:
		sizes[layer_name] = (motion_layer_bones[layer_name] as Dictionary).size()
	return sizes


func _environment_flag(name: String, default_value: bool) -> bool:
	var raw_value := OS.get_environment(name).strip_edges().to_lower()
	if raw_value.is_empty():
		return default_value
	return raw_value not in ["0", "false", "no", "off"]


func _play_authored_motion(clip_id: StringName = &"pirouette") -> void:
	if authored_motion_player == null or not authored_motion_clips.has(String(clip_id)):
		print("GODOT_AUTHORED_MOTION_UNAVAILABLE", clip_id)
		return
	if authored_motion_active:
		_cancel_authored_motion(false)
	_restore_bone_poses()
	authored_motion_name = clip_id
	action_name = String(clip_id)
	action_elapsed = 0.0
	action_duration = authored_motion_player.get_animation(clip_id).length
	authored_motion_active = true
	var clip_data: Dictionary = authored_motion_clips[String(clip_id)]
	authored_motion_player.play(clip_id, float(clip_data.get("blend_seconds", 0.0)))
	_update_hud()
	print("GODOT_AUTHORED_MOTION_STARTED", clip_id)


func _play_default_idle_motion() -> void:
	if default_idle_motion.is_empty() or authored_motion_active:
		return
	_play_authored_motion(default_idle_motion)


func _cancel_authored_motion(return_to_idle: bool = false) -> void:
	if authored_motion_player == null or not authored_motion_active:
		return
	authored_motion_active = false
	authored_motion_name = &""
	if authored_motion_player.has_animation(&"__RESET"):
		authored_motion_player.play(&"__RESET")
		authored_motion_player.advance(0.0)
		authored_motion_player.stop(true)
	else:
		authored_motion_player.stop()
	action_name = "idle"
	action_elapsed = 0.0
	_restore_bone_poses()
	_update_hud()
	if return_to_idle:
		_play_default_idle_motion()


func _on_authored_motion_finished(animation_name: StringName) -> void:
	if animation_name != authored_motion_name:
		return
	var clip_data: Dictionary = authored_motion_clips.get(String(animation_name), {})
	if voice_recording_active and bool(clip_data.get("hold_last_while_recording", false)):
		var animation := authored_motion_player.get_animation(animation_name)
		authored_motion_player.pause()
		authored_motion_player.seek(animation.length, true)
		print("GODOT_AUTHORED_MOTION_HELD", animation_name)
		return
	var should_return_to_idle := animation_name != default_idle_motion
	_cancel_authored_motion(should_return_to_idle)
	print("GODOT_AUTHORED_MOTION_FINISHED", animation_name)


func _set_voice_motion_state(next_state: String) -> void:
	var was_recording := voice_recording_active
	voice_recording_active = next_state == "recording"
	if voice_recording_active:
		if authored_motion_name != &"listen":
			handle_agent_event("avatar.listen")
		return
	if was_recording and authored_motion_name == &"listen":
		_cancel_authored_motion(true)
		_set_expression("まばたき", 0.0)
		_clear_emotions()
		expression_name = "自然"


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
	_sync_interaction_ui_origin()


func _handle_core_event(payload: Dictionary) -> void:
	var event_type := str(payload.get("type", ""))
	match event_type:
		"avatar.speak":
			_handle_avatar_speak(payload)
		"avatar.speech.stop":
			_handle_speech_stop(payload)
		"core.status":
			core_connection_state = str(payload.get("status", "online"))
			_update_hud()
		"client.ready":
			print("GODOT_AVATAR_CORE_READY", payload)
			request_session_list()
			request_chat_history(-1)
		"agent.state":
			_set_agent_state(str(payload.get("state", "idle")))
		"chat.response":
			if interaction_ui != null:
				interaction_ui.add_message("洛天依", str(payload.get("text", "")), int(payload.get("conversationId", -1)))
		"session.switched":
			if interaction_ui != null:
				interaction_ui.on_session_switched(int(payload.get("conversationId", -1)), str(payload.get("title", "新对话")))
		"session.list.response":
			if interaction_ui != null and payload.get("sessions") is Array:
				interaction_ui.on_session_list(payload.get("sessions", []))
		"chat.history.response":
			if interaction_ui != null and payload.get("messages") is Array:
				interaction_ui.on_chat_history(int(payload.get("conversationId", -1)), payload.get("messages", []))
		"wake.triggered":
			if interaction_ui != null:
				interaction_ui.on_wake_triggered()
		"voice.state":
			var voice_state := str(payload.get("state", "idle"))
			_set_voice_motion_state(voice_state)
			if interaction_ui != null:
				interaction_ui.on_voice_state(voice_state)
		"session.title":
			if interaction_ui != null:
				interaction_ui.on_session_title(int(payload.get("conversationId", -1)), str(payload.get("title", "")))
		"session.deleted":
			if interaction_ui != null:
				interaction_ui.on_session_deleted(int(payload.get("conversationId", -1)))
		"wake.idle":
			if interaction_ui != null:
				interaction_ui.on_wake_idle()
		"agent.tool":
			if interaction_ui != null:
				interaction_ui.on_agent_tool(str(payload.get("tool", "")), bool(payload.get("ok", true)))
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
			if interaction_ui != null and interaction_ui.is_pointer_over_ui(mouse_event.position):
				return
			rotation_dragging = mouse_event.pressed
			last_pointer = mouse_event.position
			get_viewport().set_input_as_handled()
		elif mouse_event.pressed and mouse_event.button_index == MOUSE_BUTTON_WHEEL_UP:
			if interaction_ui != null and interaction_ui.is_pointer_over_ui(mouse_event.position):
				return
			target_distance = max(MIN_CAMERA_DISTANCE, target_distance - 0.25)
			_update_hud()
			get_viewport().set_input_as_handled()
		elif mouse_event.pressed and mouse_event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			if interaction_ui != null and interaction_ui.is_pointer_over_ui(mouse_event.position):
				return
			target_distance = min(MAX_CAMERA_DISTANCE, target_distance + 0.25)
			_update_hud()
			get_viewport().set_input_as_handled()
		return

	if event is InputEventMouseMotion and left_pressing:
		var move_event := event as InputEventMouseMotion
		if not left_dragging and move_event.position.distance_to(left_press_position) >= 8.0:
			left_dragging = true
			if interaction_ui != null:
				interaction_ui.hide_all()
			if canvas_mode == CANVAS_MODE_COMPACT and DisplayServer.get_name() != "headless":
				DisplayServer.window_start_drag()
		if left_dragging and canvas_mode == CANVAS_MODE_DESKTOP:
			avatar_screen_center += move_event.relative
			_clamp_avatar_screen_center()
			_sync_avatar_texture_rect()
			_sync_interaction_ui_origin()
			_update_mouse_passthrough(true)
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
			KEY_P:
				handle_agent_event("avatar.pirouette")
			KEY_G:
				handle_agent_event("avatar.listen")
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
			KEY_F12:
				capture_hd_portrait()
			KEY_ESCAPE:
				get_tree().quit()
			_:
				shortcut_handled = false
		if shortcut_handled:
			get_viewport().set_input_as_handled()


func capture_hd_portrait() -> Dictionary:
	var source: Viewport = avatar_render_viewport if avatar_render_viewport != null else get_viewport()
	var result: Dictionary = await portrait_capture.capture(camera, source)
	if bool(result.get("ok", false)):
		print("GODOT_PORTRAIT_SAVED ", result)
	else:
		push_warning("Portrait capture: " + str(result.get("error", "unknown error")))
	return result


func handle_agent_event(event_type: String, payload: Dictionary = {}) -> void:
	match event_type:
		"avatar.speak":
			_handle_avatar_speak(payload)
		"avatar.speech.stop":
			_handle_speech_stop(payload)
		"avatar.turn_left":
			_cancel_authored_motion()
			target_yaw -= deg_to_rad(float(payload.get("degrees", 30.0)))
			action_name = "idle"
			_restore_bone_poses()
			_play_default_idle_motion()
		"avatar.turn_right":
			_cancel_authored_motion()
			target_yaw += deg_to_rad(float(payload.get("degrees", 30.0)))
			action_name = "idle"
			_restore_bone_poses()
			_play_default_idle_motion()
		"avatar.reset":
			_cancel_authored_motion()
			target_yaw = 0.0
			action_name = "idle"
			_restore_bone_poses()
			_clear_emotions()
			expression_name = "自然"
			_play_default_idle_motion()
		"avatar.nod":
			_start_action("nod", 1.35)
		"avatar.wave":
			_start_action("wave", 2.35)
		"avatar.greet":
			_start_action("greet", 2.35)
			_show_emotion("笑い", "微笑", 0.78, 2.35)
			_set_expression("ウィンク", 0.72, 1.1)
		"avatar.pirouette":
			_play_authored_motion()
		"avatar.listen":
			_play_authored_motion(&"listen")
			_set_expression("まばたき", 1.0, 2.1)
			_show_emotion("笑い", "专注倾听", 0.28, 8.5)
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
	var chat_payload := {
		"type": "chat.message",
		"text": normalized_text,
		"messageId": request_id,
	}
	var conversation_id: int = interaction_ui.get_current_conversation_id() if interaction_ui != null else -1
	if conversation_id > 0:
		chat_payload["conversationId"] = conversation_id
	core_socket.send_text(JSON.stringify(chat_payload))
	_set_agent_state("thinking")


func request_session_list() -> void:
	if not _core_connected():
		return
	core_socket.send_text(JSON.stringify({"type": "session.list.request"}))


func request_chat_history(conversation_id: int) -> void:
	if not _core_connected():
		return
	if conversation_id > 0:
		core_socket.send_text(JSON.stringify({
			"type": "chat.history.request",
			"conversationId": conversation_id,
		}))
	else:
		core_socket.send_text(JSON.stringify({"type": "chat.history.request"}))


func request_new_session() -> void:
	if not _core_connected():
		if interaction_ui != null:
			interaction_ui.show_error("Core 尚未连接，无法新建会话。")
		return
	core_socket.send_text(JSON.stringify({"type": "session.new"}))


func request_delete_session(conversation_id: int) -> void:
	if not _core_connected():
		if interaction_ui != null:
			interaction_ui.show_error("Core 尚未连接，无法删除会话。")
		return
	core_socket.send_text(JSON.stringify({
		"type": "session.delete",
		"conversationId": conversation_id,
	}))


func _core_connected() -> bool:
	return core_socket != null and core_socket.get_ready_state() == WebSocketPeer.STATE_OPEN


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
	_cancel_authored_motion()
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
		var wave_phase := sin(action_elapsed * PI * 4.5)
		var lift := deg_to_rad(WAVE_UPPER_ARM_ANGLE) * fade
		var elbow_bend := deg_to_rad(WAVE_ELBOW_BEND_ANGLE + wave_phase * WAVE_ELBOW_SWAY_ANGLE) * fade
		var wrist_roll := deg_to_rad(WAVE_WRIST_ROLL_ANGLE) * fade
		var wrist_sway := deg_to_rad(WAVE_WRIST_SWAY_ANGLE) * wave_phase * fade
		_set_bone_offset("腕.R", Quaternion(_action_axis("lift.R", Vector3.FORWARD), lift))
		_set_bone_offset("ひじ.R", Quaternion(_action_axis("elbow.R", Vector3.FORWARD), elbow_bend))
		_set_bone_offset(
			"手首.R",
			Quaternion(_action_axis("wrist.R", Vector3.UP), wrist_roll)
				* Quaternion(_action_axis("wrist_wave.R", Vector3.FORWARD), wrist_sway)
		)

	if action_name == "greet":
		model.rotation.z = base_model_rotation.z + sin(action_elapsed * PI * 2.0) * deg_to_rad(1.8) * fade


func _cache_action_axes() -> void:
	"""Derive gesture axes from the rest pose instead of assuming world axes.

	MMD armatures contain twist/helper bones and their local bases are generally
	not aligned with Godot's global XYZ axes. A world-axis quaternion can put a
	skinned limb edge-on or rotate it through the torso. These axes are cached
	after the preserved rest offsets are applied, then converted into each bone's
	local pose space.
	"""
	action_axes.clear()
	if skeleton == null:
		return
	for side in ["R", "L"]:
		var arm_name := "腕.%s" % side
		var elbow_name := "ひじ.%s" % side
		var wrist_name := "手首.%s" % side
		var arm_index: int = bone_ids.get(arm_name, -1)
		var elbow_index: int = bone_ids.get(elbow_name, -1)
		var wrist_index: int = bone_ids.get(wrist_name, -1)
		if arm_index < 0 or elbow_index < 0:
			continue

		var arm_origin := _bone_pose_origin(arm_index)
		var elbow_origin := _bone_pose_origin(elbow_index)
		var upper_direction := elbow_origin - arm_origin
		if upper_direction.length_squared() < 0.000001:
			continue
		upper_direction = upper_direction.normalized()
		var skeleton_up := skeleton.global_transform.basis.orthonormalized().inverse() * Vector3.UP
		if skeleton_up.length_squared() < 0.000001:
			skeleton_up = Vector3.UP
		skeleton_up = skeleton_up.normalized()
		var lift_axis := _axis_that_moves_toward(upper_direction, skeleton_up)
		action_axes["lift.%s" % side] = _to_bone_local_axis(arm_index, lift_axis)

		if wrist_index < 0:
			continue
		var wrist_origin := _bone_pose_origin(wrist_index)
		var forearm_direction := wrist_origin - elbow_origin
		if forearm_direction.length_squared() < 0.000001:
			forearm_direction = upper_direction
		else:
			forearm_direction = forearm_direction.normalized()
		var elbow_axis := upper_direction.cross(forearm_direction)
		if elbow_axis.length_squared() < 0.000001:
			elbow_axis = lift_axis
		else:
			elbow_axis = elbow_axis.normalized()
		action_axes["elbow.%s" % side] = _to_bone_local_axis(elbow_index, elbow_axis)
		action_axes["wrist.%s" % side] = _to_bone_local_axis(wrist_index, forearm_direction)
		var skeleton_forward := skeleton.global_transform.basis.orthonormalized().inverse() * Vector3.FORWARD
		action_axes["wrist_wave.%s" % side] = _to_bone_local_axis(wrist_index, skeleton_forward)


func _bone_pose_origin(bone_index: int) -> Vector3:
	if skeleton == null or bone_index < 0:
		return Vector3.ZERO
	return skeleton.get_bone_global_pose(bone_index).origin


func _axis_that_moves_toward(direction: Vector3, target: Vector3) -> Vector3:
	var candidate := direction.cross(target)
	if candidate.length_squared() < 0.000001:
		return Vector3.FORWARD
	candidate = candidate.normalized()
	var positive_gain := (Quaternion(candidate, 0.05) * direction).dot(target)
	var negative_gain := (Quaternion(-candidate, 0.05) * direction).dot(target)
	return candidate if positive_gain >= negative_gain else -candidate


func _to_bone_local_axis(bone_index: int, axis: Vector3) -> Vector3:
	if skeleton == null or bone_index < 0 or axis.length_squared() < 0.000001:
		return Vector3.FORWARD
	var pose_basis := skeleton.get_bone_global_pose(bone_index).basis.orthonormalized()
	var local_axis := pose_basis.inverse() * axis.normalized()
	if local_axis.length_squared() < 0.000001:
		return Vector3.FORWARD
	return local_axis.normalized()


func _action_axis(axis_name: String, fallback: Vector3) -> Vector3:
	var axis: Variant = action_axes.get(axis_name, fallback)
	if axis is Vector3 and axis.length_squared() >= 0.000001:
		return axis.normalized()
	return fallback.normalized()


func _cache_deform_bone_mirrors() -> void:
	deform_bone_mirrors.clear()
	deform_mirror_base_global_poses.clear()
	if skeleton == null:
		return
	for mirror_names in MMD_DEFORM_BONE_MIRRORS:
		var source_index := skeleton.find_bone(str(mirror_names[0]))
		var target_index := skeleton.find_bone(str(mirror_names[1]))
		if source_index < 0 or target_index < 0:
			continue
		deform_bone_mirrors.append([source_index, target_index])
		deform_mirror_base_global_poses[source_index] = skeleton.get_bone_global_pose(source_index)
		deform_mirror_base_global_poses[target_index] = skeleton.get_bone_global_pose(target_index)
		for bone_index in [source_index, target_index]:
			var base_rotation := skeleton.get_bone_pose_rotation(bone_index)
			base_bone_rotations[bone_index] = base_rotation
			rest_bone_rotations[bone_index] = base_rotation


func _sync_deform_bone_mirrors() -> void:
	if not authored_motion_active or authored_motion_name.is_empty():
		return
	var clip_data: Dictionary = authored_motion_clips.get(String(authored_motion_name), {})
	if str(clip_data.get("bone_layer", MOTION_LAYER_FULL_BODY)) != MOTION_LAYER_FULL_BODY:
		return
	if not bool(clip_data.get("sync_mmd_deform_bones", true)):
		return
	for mirror in deform_bone_mirrors:
		var source_index: int = mirror[0]
		var target_index: int = mirror[1]
		var source_base: Transform3D = deform_mirror_base_global_poses[source_index]
		var target_base: Transform3D = deform_mirror_base_global_poses[target_index]
		var source_current := skeleton.get_bone_global_pose(source_index)
		var global_delta := (
			source_current.basis.orthonormalized()
			* source_base.basis.orthonormalized().inverse()
		)
		var target_pose := target_base
		target_pose.origin = source_current.origin
		target_pose.basis = (global_delta * target_base.basis.orthonormalized()).orthonormalized()
		skeleton.set_bone_global_pose(target_index, target_pose)


func _preserve_limb_readability() -> void:
	## A fixed desktop camera turns depth-aligned limbs into a few pixels even
	## though the skin is intact. Apply the smallest camera-relative correction
	## to every animated arm segment, independent of how the action was started.
	if skeleton == null or action_name in ["idle", "nod"]:
		return
	for chain in READABILITY_ARM_CHAINS:
		for segment_index in range(chain.size() - 1):
			_constrain_limb_segment(str(chain[segment_index]), str(chain[segment_index + 1]))


func _constrain_limb_segment(parent_name: String, child_name: String) -> void:
	var parent_index := skeleton.find_bone(parent_name)
	var child_index := skeleton.find_bone(child_name)
	if parent_index < 0 or child_index < 0:
		return
	var parent_pose := skeleton.get_bone_global_pose(parent_index)
	var child_pose := skeleton.get_bone_global_pose(child_index)
	var direction := child_pose.origin - parent_pose.origin
	if direction.length_squared() < 0.000001:
		return
	direction = direction.normalized()

	var skeleton_basis := skeleton.global_transform.basis.orthonormalized()
	var camera_forward: Vector3 = skeleton_basis.inverse() * -camera.global_transform.basis.z.normalized()
	if camera_forward.length_squared() < 0.000001:
		return
	camera_forward = camera_forward.normalized()
	var depth := direction.dot(camera_forward)
	var visibility := sqrt(maxf(0.0, 1.0 - depth * depth))
	if visibility >= MIN_LIMB_CAMERA_PLANE_VISIBILITY:
		return

	var lateral := direction - camera_forward * depth
	if lateral.length_squared() < 0.000001:
		lateral = skeleton_basis.inverse() * camera.global_transform.basis.x.normalized()
	if lateral.length_squared() < 0.000001:
		return
	lateral = lateral.normalized()
	var depth_sign := signf(depth)
	if is_zero_approx(depth_sign):
		depth_sign = 1.0
	var target_depth := sqrt(maxf(0.0, 1.0 - MIN_LIMB_CAMERA_PLANE_VISIBILITY * MIN_LIMB_CAMERA_PLANE_VISIBILITY))
	var target_direction := (
		lateral * MIN_LIMB_CAMERA_PLANE_VISIBILITY
		+ camera_forward * depth_sign * target_depth
	).normalized()
	var correction := Quaternion(direction, target_direction)
	var correction_angle := minf(correction.get_angle(), deg_to_rad(MAX_LIMB_READABILITY_CORRECTION))
	if correction_angle < 0.0001:
		return
	var global_axis := correction.get_axis()
	var local_axis := parent_pose.basis.orthonormalized().inverse() * global_axis
	if local_axis.length_squared() < 0.000001:
		return
	local_axis = local_axis.normalized()
	var current_rotation := skeleton.get_bone_pose_rotation(parent_index)
	skeleton.set_bone_pose_rotation(
		parent_index,
		(current_rotation * Quaternion(local_axis, correction_angle)).normalized()
	)
	## Only this subtree is dirty; updating all 703 MMD bones for every corrected
	## arm segment is unnecessary and the all-bones API is deprecated in Godot.
	skeleton.force_update_bone_child_transform(parent_index)


func _apply_pigtail_pose() -> void:
	if skeleton == null:
		return
	for chain_position in range(pigtail_chains.size()):
		var chain: Array = pigtail_chains[chain_position]
		var side_sign := -1.0 if chain_position == 0 else 1.0
		var side_phase := float(chain_position) * PI
		for segment_position in range(chain.size()):
			var bone_index: int = chain[segment_position]
			var chain_progress := float(segment_position) / maxf(float(chain.size() - 1), 1.0)
			var delayed_phase := elapsed * 1.1 + side_phase - float(segment_position) * PIGTAIL_CHAIN_PHASE_DELAY
			var sway_amplitude := (
				PIGTAIL_SWAY_AMPLITUDE if segment_position == 0
				else PIGTAIL_CHAIN_SWAY_AMPLITUDE * (0.35 + chain_progress * 0.65)
			)
			var sway := sin(delayed_phase) * deg_to_rad(sway_amplitude)
			var settle := cos(elapsed * 0.8 + side_phase - float(segment_position) * 0.08) \
				* deg_to_rad(0.6 if segment_position == 0 else 0.12 * chain_progress)
			var inward_angle := PIGTAIL_INWARD_ANGLE * side_sign if segment_position == 0 else 0.0
			var depth_angle := PIGTAIL_DEPTH_ANGLE * side_sign if segment_position == 0 else 0.0
			var offset := Quaternion(Vector3.RIGHT, sway) \
				* Quaternion(Vector3.UP, deg_to_rad(inward_angle)) \
				* Quaternion(Vector3.FORWARD, deg_to_rad(depth_angle) + settle)
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


func _find_animation_player(node: Node) -> AnimationPlayer:
	if node is AnimationPlayer:
		return node as AnimationPlayer
	for child in node.get_children():
		var found := _find_animation_player(child)
		if found != null:
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


	for pigtail_side in ["R", "L"]:
		var chain: Array[int] = []
		for segment_position in range(17):
			var pigtail_name := "MaWei_%s_%d_1" % [pigtail_side, segment_position]
			var pigtail_index := skeleton.find_bone(pigtail_name)
			if pigtail_index < 0:
				break
			chain.append(pigtail_index)
			var pigtail_base := skeleton.get_bone_pose_rotation(pigtail_index)
			base_bone_rotations[pigtail_index] = pigtail_base
			pigtail_base_rotations[pigtail_index] = pigtail_base
			var side_sign := -1.0 if pigtail_side == "R" else 1.0
			var pigtail_rest_offset := Quaternion.IDENTITY
			if segment_position == 0:
				pigtail_rest_offset = Quaternion(Vector3.RIGHT, deg_to_rad(PIGTAIL_TILT_ANGLE)) \
					* Quaternion(Vector3.UP, deg_to_rad(PIGTAIL_INWARD_ANGLE * side_sign)) \
					* Quaternion(Vector3.FORWARD, deg_to_rad(PIGTAIL_DEPTH_ANGLE * side_sign))
			var pigtail_rest := pigtail_base * pigtail_rest_offset
			pigtail_rest_rotations[pigtail_index] = pigtail_rest
			rest_bone_rotations[pigtail_index] = pigtail_rest
		if not chain.is_empty():
			pigtail_chains.append(chain)
			pigtail_root_ids.append(chain[0])

	_cache_motion_layers()


func _cache_motion_layers() -> void:
	var upper_bones := {}
	var lower_bones := {}
	_collect_bone_descendants("上半身", upper_bones)
	for chain in pigtail_chains:
		for bone_index in chain:
			upper_bones[bone_index] = true
	for root_name in ["全ての親", "センター", "グルーブ", "腰"]:
		var root_index := skeleton.find_bone(root_name)
		if root_index >= 0:
			lower_bones[root_index] = true
	for lower_root in ["下半身", "足IK親.R", "足IK親.L"]:
		_collect_bone_descendants(lower_root, lower_bones)
	motion_layer_bones[MOTION_LAYER_UPPER_BODY] = upper_bones
	motion_layer_bones[MOTION_LAYER_LOWER_BODY] = lower_bones


func _collect_bone_descendants(root_name: String, target: Dictionary) -> void:
	var root_index := skeleton.find_bone(root_name)
	if root_index < 0:
		return
	var pending: Array[int] = [root_index]
	while not pending.is_empty():
		var bone_index: int = pending.pop_back()
		if target.has(bone_index):
			continue
		target[bone_index] = true
		for child_index in skeleton.get_bone_children(bone_index):
			pending.append(child_index)


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


func _configure_model_look() -> void:
	var requested_look := OS.get_environment(MODEL_LOOK_ENV).strip_edges().to_lower()
	set_model_look_version(requested_look)


func set_model_look_preview(enabled: bool) -> void:
	# Preserve the historical 1.1/1.2 A/B API and its verification scripts.
	set_model_look_version(MODEL_LOOK_V12 if enabled else "1.1")


func set_model_look_version(version: String) -> void:
	var requested := version.strip_edges().to_lower()
	if requested in ["0", "false", "off", "1.1", "baseline"]:
		requested = "1.1"
	elif requested in ["1.2", "1.2-preview"]:
		requested = MODEL_LOOK_V12
	else:
		requested = MODEL_LOOK_CURRENT
	if face_mesh == null or face_mesh.mesh == null:
		model_look_preview_enabled = false
		return
	if requested == model_look_version and not model_look_original_overrides.is_empty():
		return
	_cache_model_look_materials()
	for surface_index in model_look_original_overrides.keys():
		var material: Material = model_look_original_overrides.get(surface_index)
		if requested == MODEL_LOOK_V12:
			material = model_look_preview_materials.get(surface_index)
		elif requested == MODEL_LOOK_CURRENT:
			material = model_look_v13_materials.get(surface_index)
		face_mesh.set_surface_override_material(int(surface_index), material)
	model_look_version = requested
	model_look_preview_enabled = requested != "1.1"


func _cache_model_look_materials() -> void:
	if not model_look_original_overrides.is_empty():
		return
	var mesh: Mesh = face_mesh.mesh
	for surface_index in range(mesh.get_surface_count()):
		var surface_name: String = mesh.surface_get_name(surface_index)
		if not MODEL_LOOK_TARGETS.has(surface_name):
			continue
		var source := mesh.surface_get_material(surface_index) as StandardMaterial3D
		if source == null or source.emission_texture == null:
			continue
		model_look_original_overrides[surface_index] = face_mesh.get_surface_override_material(surface_index)
		model_look_preview_materials[surface_index] = _create_model_look_material(
			source,
			MODEL_LOOK_TARGETS[surface_name],
			surface_name
		)
		model_look_v13_materials[surface_index] = ModelLookV13.make_material(
			model_look_preview_materials[surface_index], surface_name
		)


func _create_model_look_material(
	source: StandardMaterial3D,
	profile: Dictionary,
	surface_name: String
) -> StandardMaterial3D:
	var preview := source.duplicate(true) as StandardMaterial3D
	preview.resource_name = "%s_%s" % [surface_name, MODEL_LOOK_V12]
	preview.albedo_texture = source.emission_texture
	var albedo_strength := float(profile.get("albedo", 0.4))
	preview.albedo_color = Color(albedo_strength, albedo_strength, albedo_strength, 1.0)
	preview.emission = Color.WHITE
	preview.emission_energy_multiplier = float(profile.get("emission", 0.5))
	preview.diffuse_mode = BaseMaterial3D.DIFFUSE_TOON
	preview.specular_mode = BaseMaterial3D.SPECULAR_TOON
	preview.metallic = 0.0
	preview.metallic_specular = 0.18
	preview.roughness = float(profile.get("roughness", 0.9))
	preview.rim_enabled = true
	preview.rim = float(profile.get("rim", 0.08))
	preview.rim_tint = 0.30
	return preview


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
	var requested_mode := OS.get_environment(CANVAS_MODE_ENV).strip_edges().to_lower()
	canvas_mode = CANVAS_MODE_COMPACT if requested_mode == CANVAS_MODE_COMPACT else CANVAS_MODE_DESKTOP
	if DisplayServer.get_name() == "headless":
		return
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_BORDERLESS, true)
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_ALWAYS_ON_TOP, true)
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_RESIZE_DISABLED, true)
	desktop_screen_index = DisplayServer.window_get_current_screen()
	if canvas_mode == CANVAS_MODE_DESKTOP:
		_apply_desktop_canvas(desktop_screen_index)
	else:
		avatar_screen_center = BASE_AVATAR_CENTER
	_update_mouse_passthrough(true)
	call_deferred("_restore_window_position")


func _configure_avatar_render_surface() -> void:
	camera.fov = BASE_CAMERA_FOV
	if canvas_mode != CANVAS_MODE_DESKTOP:
		return
	avatar_render_viewport = SubViewport.new()
	avatar_render_viewport.name = "AvatarRenderViewport"
	avatar_render_viewport.size = Vector2i(AVATAR_COMPOSITE_SIZE * AVATAR_RENDER_SCALE)
	avatar_render_viewport.transparent_bg = true
	avatar_render_viewport.own_world_3d = true
	avatar_render_viewport.render_target_clear_mode = SubViewport.CLEAR_MODE_ALWAYS
	avatar_render_viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	avatar_render_viewport.msaa_3d = Viewport.MSAA_4X
	add_child(avatar_render_viewport)

	var render_world := Node3D.new()
	render_world.name = "AvatarRenderWorld"
	avatar_render_viewport.add_child(render_world)
	for render_node in [model, camera, get_node_or_null("Environment"), get_node_or_null("KeyLight"), get_node_or_null("FillLight")]:
		if render_node != null:
			render_node.reparent(render_world, true)
	camera.fov = _avatar_composite_fov()

	avatar_render_canvas = CanvasLayer.new()
	avatar_render_canvas.name = "AvatarCompositeCanvas"
	avatar_render_canvas.layer = -10
	add_child(avatar_render_canvas)
	avatar_texture_rect = TextureRect.new()
	avatar_texture_rect.name = "AvatarCompositeTexture"
	avatar_texture_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	avatar_texture_rect.stretch_mode = TextureRect.STRETCH_SCALE
	avatar_texture_rect.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	avatar_texture_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	avatar_texture_rect.texture = avatar_render_viewport.get_texture()
	avatar_render_canvas.add_child(avatar_texture_rect)
	avatar_texture_rect.size = AVATAR_COMPOSITE_SIZE
	_sync_avatar_texture_rect()


func _avatar_composite_fov() -> float:
	var vertical_scale := AVATAR_COMPOSITE_SIZE.y / BASE_VIEWPORT_SIZE.y
	return rad_to_deg(2.0 * atan(vertical_scale * tan(deg_to_rad(BASE_CAMERA_FOV) * 0.5)))


func _restore_window_position() -> void:
	var config := ConfigFile.new()
	var has_config := config.load(WINDOW_SETTINGS_PATH) == OK
	if canvas_mode == CANVAS_MODE_DESKTOP:
		var screen_count := DisplayServer.get_screen_count()
		var saved_screen := int(config.get_value("window", "screen", desktop_screen_index)) if has_config else desktop_screen_index
		desktop_screen_index = clampi(saved_screen, 0, maxi(screen_count - 1, 0))
		_apply_desktop_canvas(desktop_screen_index)
		var viewport_size := get_viewport().get_visible_rect().size
		var saved_ratio: Variant = null
		if has_config and config.has_section_key("desktop_canvas", "avatar_center_ratio"):
			saved_ratio = config.get_value("desktop_canvas", "avatar_center_ratio")
		if saved_ratio is Vector2:
			avatar_screen_center = Vector2(saved_ratio) * viewport_size
		elif has_config:
			var legacy_position: Variant = config.get_value("window", "position", null)
			if legacy_position is Vector2i:
				var usable_rect := DisplayServer.screen_get_usable_rect(desktop_screen_index)
				avatar_screen_center = Vector2(legacy_position - usable_rect.position) + BASE_AVATAR_CENTER
			else:
				avatar_screen_center = viewport_size * 0.5
		else:
			avatar_screen_center = viewport_size * 0.5
		_clamp_avatar_screen_center()
		_sync_avatar_texture_rect()
		_sync_interaction_ui_origin()
		_update_mouse_passthrough(true)
		return
	if not has_config:
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
	config.load(WINDOW_SETTINGS_PATH)
	if canvas_mode == CANVAS_MODE_DESKTOP:
		var viewport_size := get_viewport().get_visible_rect().size
		var safe_size := Vector2(maxf(viewport_size.x, 1.0), maxf(viewport_size.y, 1.0))
		config.set_value("desktop_canvas", "avatar_center_ratio", avatar_screen_center / safe_size)
		config.set_value("window", "screen", desktop_screen_index)
	else:
		config.set_value("window", "position", DisplayServer.window_get_position())
		config.set_value("window", "screen", DisplayServer.window_get_current_screen())
	var save_error := config.save(WINDOW_SETTINGS_PATH)
	if save_error != OK:
		push_warning("Unable to save avatar window position: %s" % error_string(save_error))


func _apply_desktop_canvas(screen_index: int) -> void:
	if DisplayServer.get_name() == "headless":
		return
	var usable_rect := DisplayServer.screen_get_usable_rect(screen_index)
	DisplayServer.window_set_current_screen(screen_index)
	DisplayServer.window_set_position(usable_rect.position)
	DisplayServer.window_set_size(usable_rect.size)
	avatar_screen_center = Vector2(usable_rect.size) * 0.5
	_sync_avatar_texture_rect()


func _clamp_avatar_screen_center() -> void:
	var viewport_size := get_viewport().get_visible_rect().size
	var interaction_scale := BASE_CAMERA_DISTANCE / maxf(current_distance, 0.1)
	var minimum := Vector2(
		(BASE_AVATAR_CENTER.x - 122.0) * interaction_scale + 8.0,
		(BASE_AVATAR_CENTER.y - 138.0) * interaction_scale + 8.0
	)
	var maximum := viewport_size - Vector2(
		(438.0 - BASE_AVATAR_CENTER.x) * interaction_scale + 8.0,
		(690.0 - BASE_AVATAR_CENTER.y) * interaction_scale + 8.0
	)
	minimum.x = minf(minimum.x, viewport_size.x * 0.5)
	minimum.y = minf(minimum.y, viewport_size.y * 0.5)
	maximum.x = maxf(maximum.x, viewport_size.x * 0.5)
	maximum.y = maxf(maximum.y, viewport_size.y * 0.5)
	avatar_screen_center = avatar_screen_center.clamp(minimum, maximum)


func _sync_interaction_ui_origin() -> void:
	if interaction_ui == null or not interaction_ui.has_method("set_canvas_origin"):
		return
	var viewport_size := get_viewport().get_visible_rect().size
	var desired_origin := avatar_screen_center - BASE_AVATAR_CENTER
	var maximum_origin := Vector2(
		maxf(viewport_size.x - BASE_VIEWPORT_SIZE.x, 0.0),
		maxf(viewport_size.y - BASE_VIEWPORT_SIZE.y, 0.0)
	)
	var canvas_origin := desired_origin.clamp(Vector2.ZERO, maximum_origin)
	interaction_ui.set_canvas_origin(canvas_origin)
	if interaction_ui.has_method("set_side_panel_direction"):
		var right_panel_end := canvas_origin.x + 438.0 + 24.0 + 225.0
		var left_panel_start := canvas_origin.x + 122.0 - 24.0 - 225.0
		var place_right := right_panel_end <= viewport_size.x - 8.0
		if not place_right and left_panel_start < 8.0:
			place_right = avatar_screen_center.x <= viewport_size.x * 0.5
		interaction_ui.set_side_panel_direction(1 if place_right else -1)


func _sync_avatar_texture_rect() -> void:
	if avatar_texture_rect == null:
		return
	avatar_texture_rect.position = avatar_screen_center - AVATAR_COMPOSITE_SIZE * 0.5


func set_ui_overlay_active(active: bool) -> void:
	ui_overlay_active = active
	_update_mouse_passthrough(true)


func _avatar_interaction_polygon() -> PackedVector2Array:
	var scale := BASE_CAMERA_DISTANCE / maxf(current_distance, 0.1)
	var transformed := PackedVector2Array()
	for point in avatar_interaction_region:
		transformed.append(avatar_screen_center + (point - BASE_AVATAR_CENTER) * scale)
	return transformed


func _update_mouse_passthrough(force: bool = false) -> void:
	if DisplayServer.get_name() == "headless":
		return
	var region := _avatar_interaction_polygon()
	if ui_overlay_active and interaction_ui != null and interaction_ui.has_method("get_visible_interaction_rect"):
		var ui_rect: Rect2 = interaction_ui.get_visible_interaction_rect()
		if ui_rect.size.x > 0.0 and ui_rect.size.y > 0.0:
			region.append(ui_rect.position)
			region.append(ui_rect.position + Vector2(ui_rect.size.x, 0.0))
			region.append(ui_rect.end)
			region.append(ui_rect.position + Vector2(0.0, ui_rect.size.y))
			region = Geometry2D.convex_hull(region)
	var signature_parts: PackedStringArray = []
	for point in region:
		signature_parts.append("%d,%d" % [roundi(point.x), roundi(point.y)])
	var signature := ";".join(signature_parts)
	if force or signature != last_passthrough_signature:
		last_passthrough_signature = signature
		DisplayServer.window_set_mouse_passthrough(region)


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
	footer.text = "左键拖动人物位置 · 右键拖拽转身 · 滚轮缩放 · F1 调试信息\n←/→ 转身 · R 回正 · N 点头 · W 挥手 · P 动作样片 · Space 打招呼\nF12 高清透明截图 · Esc 退出"
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
		"pirouette": "状态：动捕旋转样片",
	}.get(action_name, "状态：互动"))
	action_label.text = action_text
	camera_label.text = "朝向：%d°    距离：%.1f" % [roundi(rad_to_deg(current_yaw)), current_distance]
	if expression_label != null:
		expression_label.text = "表情：%s" % expression_name
	if core_label != null:
		core_label.text = "Core：%s    Agent：%s" % [core_connection_state, agent_state]


func _handle_avatar_speak(payload: Dictionary) -> void:
	if speech_player == null:
		speech_player = AudioStreamPlayer.new()
		speech_player.bus = "Master"
		speech_player.finished.connect(_on_speech_finished)
		add_child(speech_player)
	var path := str(payload.get("audioPath", ""))
	var utterance_id := str(payload.get("utteranceId", ""))
	if path.is_empty() or not FileAccess.file_exists(path):
		return
	var wav := AudioStreamWAV.load_from_file(path)
	if wav == null:
		return
	current_utterance_id = utterance_id
	speech_player.stream = wav
	speech_player.play()


func _handle_speech_stop(payload: Dictionary) -> void:
	var utterance_id := str(payload.get("utteranceId", ""))
	if speech_player != null and speech_player.playing and (utterance_id == "" or utterance_id == current_utterance_id):
		speech_player.stop()
		_report_speech_finished(true)


func _on_speech_finished() -> void:
	_report_speech_finished(false)


func _report_speech_finished(interrupted: bool) -> void:
	if current_utterance_id == "":
		return
	if _core_connected():
		core_socket.send_text(JSON.stringify({"type": "speech.finished", "utteranceId": current_utterance_id, "interrupted": interrupted}))
	current_utterance_id = ""
