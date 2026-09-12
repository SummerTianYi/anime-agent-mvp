extends SceneTree
## Codex: actual production per-frame path/player/menu, isolated from Core and persistence.
const Review = preload("res://lookdev/render_candidate.gd")
const Guard = preload("res://mocap/thinking/verify_integration.gd")
const UI = preload("res://interaction_ui.gd")
class Runtime extends Review.OfflineRuntime:
	func _process_core_bridge(_delta: float) -> void:
		pass
	func _update_mouse_passthrough(_force: bool = false) -> void:
		pass
var output: String
var runtime: Node
var viewport: SubViewport
func _init() -> void:
	call_deferred("_run")
func _run() -> void:
	output = OS.get_environment("THINKING_OUTPUT")
	assert(DisplayServer.get_name() != "headless")
	assert(not output.is_empty() and not DirAccess.dir_exists_absolute(output))
	assert(DirAccess.make_dir_recursive_absolute(output + "/frames") == OK)
	root.size = Vector2i(16, 16)
	root.position = Vector2i(-100, -100)
	root.always_on_top = false
	viewport = SubViewport.new()
	viewport.size = Vector2i(720, 960)
	viewport.own_world_3d = true
	viewport.transparent_bg = true
	viewport.msaa_3d = Viewport.MSAA_4X
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(viewport)
	runtime = load("res://main.tscn").instantiate()
	runtime.set_script(Runtime)
	viewport.add_child(runtime)
	runtime.set_model_look_version("1.4")
	runtime.current_distance = runtime.MIN_CAMERA_DISTANCE
	runtime.target_distance = runtime.MIN_CAMERA_DISTANCE
	runtime.elapsed = 123.4
	var ui = UI.new(runtime)
	viewport.add_child(ui)
	var button: Button
	for node in ui.interaction_panel.find_children("*", "Button", true, false):
		if node.text == "思考":
			button = node
	assert(button != null)
	button.pressed.emit()
	assert(runtime.authored_motion_name == &"think")
	var player: AnimationPlayer = runtime.authored_motion_player
	var clip := player.get_animation(&"think")
	var checked := 0
	for frame in range(301):
		if frame > 0:
			player.advance(1.0 / 30.0)
		runtime._process(1.0 / 30.0)
		if runtime.authored_motion_name == &"think":
			var t := player.current_animation_position
			if t >= 0.3 and t <= 9.3:
				for track in clip.get_track_count():
					var name := String(clip.track_get_path(track).get_subname(0))
					var bone: int = runtime.skeleton.find_bone(name)
					assert(Guard.rotation_equal(runtime.skeleton.get_bone_pose_rotation(bone), clip.rotation_track_interpolate(track, t)), "real per-frame playback " + name)
					checked += 1
		await capture(output + "/frames/%04d.png" % frame)
		if frame % 60 == 0:
			print("THINKING_LIVE_RENDER ", frame)
	assert(runtime.authored_motion_name == &"idle", "real finished signal returns to idle")
	for time in [1.65, 3.7, 7.8, 9.5]:
		runtime.handle_agent_event("avatar.think")
		player.advance(0.3)
		for yaw in [0, 55, -55, 180]:
			player.seek(time, true)
			runtime.elapsed = 123.4 + time
			runtime.current_yaw = deg_to_rad(yaw)
			runtime.target_yaw = runtime.current_yaw
			runtime._process(0.0)
			await capture(output + "/t%.2f-y%d.png" % [time, yaw])
	var report := {"owner": "Codex", "result": "PASS", "sequential_frames_30hz": 301,
		"multiview_stills": 16, "production_rotation_checks": checked,
		"menu_button": "思考", "real_animation_finished": true, "model_version": runtime.model_look_version,
		"model_sha256": FileAccess.get_sha256("res://assets/luotianyi_v4.glb")}
	FileAccess.open(output + "/report.json", FileAccess.WRITE).store_string(JSON.stringify(report, "  "))
	print("THINKING_RENDER_INTEGRATION_PASS ", JSON.stringify(report))
	quit()
func capture(path: String) -> void:
	await process_frame
	await RenderingServer.frame_post_draw
	var pixels := viewport.get_texture().get_image()
	assert(not pixels.is_empty() and pixels.get_used_rect().has_area())
	assert(pixels.save_png(path) == OK)
