extends "res://runtime.gd"
## Codex test subclass: production startup/process/exit, only OS placement
## isolated. No focus, no mouse, no desktop-wide capture, no production socket.
var frames := 0
var sampled := {}
var configured := false
func _ready() -> void:
	if not FileAccess.file_exists("res://../../.farewell-test-fixture") or OS.get_environment("FAREWELL_EVIDENCE").is_empty() or OS.get_environment("AGENT_CORE_WS_URL").is_empty() or OS.get_environment("AGENT_CORE_WS_URL") == DEFAULT_CORE_WS_URL:
		push_error("Exit probe requires a disposable fixture and isolated Core URL")
		set_process(false)
		get_tree().quit(1)
		return
	super._ready()
func _configure_desktop_window() -> void:
	canvas_mode = CANVAS_MODE_DESKTOP
	get_tree().root.title = "Codex Farewell Isolated Probe"
	get_tree().root.unfocusable = true
	get_tree().root.always_on_top = false
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_MOUSE_PASSTHROUGH, true)
	DisplayServer.window_set_size(Vector2i(16, 16))
	DisplayServer.window_set_position(Vector2i(-100, -100))
func _update_mouse_passthrough(_force: bool = false) -> void:
	pass
func _process(delta: float) -> void:
	super._process(delta)
	frames += 1
	var scenario := OS.get_environment("FAREWELL_SCENARIO")
	if frames == 5:
		if scenario in ["listen", "think", "pirouette"]:
			_play_authored_motion(StringName(scenario))
			authored_motion_player.seek(3.7 if scenario == "think" else 1.5, true)
		elif scenario == "speaking":
			_set_agent_state("speaking")
		configured = true
		print("FAREWELL_PROBE_READY ", OS.get_process_id(), " ", OS.get_user_data_dir())
	if not farewell_exit.closing:
		return
	if scenario == "paused":
		get_tree().paused = true
	if scenario == "zero_scale":
		Engine.time_scale = 0.0
	# Simulate late Core/UI messages without any real Provider call.
	_handle_core_event({"type":"agent.state", "state":"speaking"})
	_handle_core_event({"type":"voice.state", "state":"recording"})
	handle_agent_event("avatar.reset")
	var sample := {"seconds":farewell_exit.time, "frame":frames, "closing":true,
		"eyes":face_mesh.get_blend_shape_value(expression_ids["笑い"]),
		"smile":face_mesh.get_blend_shape_value(expression_ids["にやり"]),
		"authored_playing":authored_motion_player.is_playing()}
	var out := OS.get_environment("FAREWELL_EVIDENCE")
	var f := FileAccess.open(out.path_join("frames.jsonl"), FileAccess.READ_WRITE if FileAccess.file_exists(out.path_join("frames.jsonl")) else FileAccess.WRITE)
	f.seek_end()
	f.store_line(JSON.stringify(sample))
	f.close()
	for threshold in [0.05, 0.3, 0.6, 1.3, 2.5, 3.6, 4.0]:
		if farewell_exit.time >= threshold and not sampled.has(threshold):
			sampled[threshold] = true
			capture_probe(out.path_join("%04d.png" % roundi(threshold * 100)))
func capture_probe(path: String) -> void:
	await RenderingServer.frame_post_draw
	var img := avatar_render_viewport.get_texture().get_image()
	img.save_png(path)
