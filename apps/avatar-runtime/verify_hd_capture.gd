extends SceneTree

## Codex: 1.3 candidate diagnostics. No production Core or source-asset writes.
const OFFICIAL_SHA := "df55806d343d149b41c20d0ef074373cafca2379212fd8691e998ea6cddc6e4a"

class CaptureSpy extends RefCounted:
	var calls := 0
	func capture(_camera: Camera3D, _source: Viewport) -> Dictionary:
		calls += 1
		return {"ok": true, "path": "test-only-no-file-written"}


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	OS.set_environment("AGENT_CORE_WS_URL", "ws://127.0.0.1:1/ws")
	var runtime: Node = load("res://main.tscn").instantiate()
	root.add_child(runtime)
	var mesh: Mesh = runtime.face_mesh.mesh
	var hair_facts: Array = []
	for index in range(mesh.get_surface_count()):
		var surface: String = mesh.surface_get_name(index)
		if surface not in ["fronthair", "backhair", "tail"]:
			continue
		var material: StandardMaterial3D = runtime.face_mesh.get_active_material(index)
		var texture := material.emission_texture
		var texture_image := texture.get_image()
		texture_image.decompress()
		var minimum_alpha := 1.0
		for y in range(0, texture_image.get_height(), 16):
			for x in range(0, texture_image.get_width(), 16):
				minimum_alpha = minf(minimum_alpha, texture_image.get_pixel(x, y).a)
		hair_facts.append({"surface": surface, "transparency": material.transparency,
			"cull": material.cull_mode, "depth_draw": material.depth_draw_mode,
			"texture_size": texture.get_size(), "sampled_min_alpha": minimum_alpha})
	print("HAIR_MATERIAL_FACTS ", hair_facts)
	if not runtime.has_method("capture_hd_portrait"):
		_fail("HD portrait capture is not implemented")
		return
	var real_capture = runtime.portrait_capture
	var spy := CaptureSpy.new()
	runtime.portrait_capture = spy
	var key := InputEventKey.new()
	key.keycode = KEY_F12
	key.pressed = true
	runtime.interaction_ui._open_chat()
	runtime._input(key)
	if spy.calls != 0:
		_fail("F12 escaped the chat-input focus guard")
		return
	runtime.interaction_ui.hide_all()
	runtime.get_viewport().gui_release_focus()
	runtime._input(key)
	if spy.calls != 1:
		_fail("F12 did not invoke portrait capture")
		return
	runtime.portrait_capture = real_capture
	if DisplayServer.get_name() == "headless":
		print("HD_CAPTURE_API_OK; rendered checks require --display-driver windows")
		quit(0)
		return
	await process_frame
	await process_frame
	runtime.set_process(false)
	runtime.authored_motion_player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	runtime._play_authored_motion(&"idle")
	runtime.authored_motion_player.seek(2.0, true)
	runtime.elapsed = 2.0
	runtime._apply_pigtail_pose()
	await process_frame
	await RenderingServer.frame_post_draw
	var before_transform: Transform3D = runtime.model.transform
	var before_camera: Transform3D = runtime.camera.global_transform
	var before_fov: float = runtime.camera.fov
	var before_size: Vector2i = runtime.avatar_render_viewport.size
	var before_center: Vector2 = runtime.avatar_screen_center
	var samples: Array = []
	var previous_path := ""
	for yaw in [0.0, -90.0, 90.0, 180.0, 0.0]:
		if samples.size() == 4:
			runtime.camera.position.z = runtime.MIN_CAMERA_DISTANCE
		runtime.model.rotation.y = deg_to_rad(yaw)
		await process_frame
		await RenderingServer.frame_post_draw
		var before: Image = runtime.avatar_render_viewport.get_texture().get_image()
		# A visible chat panel must not enter the 3D-only export.
		runtime.interaction_ui._open_chat()
		var pose_before: Transform3D = runtime.model.transform
		var camera_before: Transform3D = runtime.camera.global_transform
		var result: Dictionary = await runtime.capture_hd_portrait()
		if runtime.model.transform != pose_before or runtime.camera.global_transform != camera_before:
			_fail("Capture changed the live pose/camera")
			return
		if not bool(result.get("ok", false)) or str(result.get("path", "")) == previous_path:
			_fail("Capture failed or overwrote the last export: " + str(result))
			return
		previous_path = result["path"]
		var captured := Image.load_from_file(previous_path)
		if captured == null or captured.get_size() != Vector2i(2880, 3480):
			_fail("Capture did not save native 3x RGBA pixels")
			return
		if captured.get_pixel(0, 0).a > 0.001 or captured.get_used_rect().size.y < 600:
			_fail("Capture is blank or lost transparent background")
			return
		var before_rect := before.get_used_rect()
		var scaled_rect := Rect2(captured.get_used_rect())
		scaled_rect.position /= 1.5
		scaled_rect.size /= 1.5
		if scaled_rect.position.distance_to(Vector2(before_rect.position)) > 3.0 \
				or scaled_rect.size.distance_to(Vector2(before_rect.size)) > 3.0:
			_fail("Portrait framing/proportions changed")
			return
		captured.resize(before.get_width(), before.get_height(), Image.INTERPOLATE_LANCZOS)
		var color_error := 0.0
		var opaque_samples := 0
		for y in range(before_rect.position.y, before_rect.end.y, 8):
			for x in range(before_rect.position.x, before_rect.end.x, 8):
				var a := before.get_pixel(x, y)
				var b := captured.get_pixel(x, y)
				if a.a > 0.99 and b.a > 0.99:
					color_error += (absf(a.r - b.r) + absf(a.g - b.g) + absf(a.b - b.b)) / 3.0
					opaque_samples += 1
		color_error /= maxf(1.0, opaque_samples)
		if opaque_samples < 100 or color_error > 0.02:
			_fail("HD capture changed color/lighting: " + str(color_error))
			return
		samples.append({"yaw": yaw, "color_error": color_error, "capture": result})
		runtime.interaction_ui.hide_all()
	runtime.model.transform = before_transform
	runtime.camera.global_transform = before_camera
	# Busy requests and invalid inputs must reject without leaving a viewport.
	runtime.portrait_capture.busy = true
	var busy_result: Dictionary = await runtime.capture_hd_portrait()
	runtime.portrait_capture.busy = false
	var invalid_result: Dictionary = await runtime.portrait_capture.capture(null, null)
	if busy_result["ok"] or invalid_result["ok"]:
		_fail("Invalid/busy capture was not rejected")
		return
	await process_frame
	if root.get_node_or_null("PortraitCaptureViewport") != null:
		_fail("Capture leaked a temporary viewport")
		return
	if runtime.model.transform != before_transform or runtime.camera.global_transform != before_camera \
			or runtime.camera.fov != before_fov or runtime.avatar_render_viewport.size != before_size \
			or runtime.avatar_screen_center != before_center:
		_fail("Capture modified live geometry, camera or desktop layout")
		return
	if FileAccess.get_sha256("res://assets/luotianyi_v4.glb") != OFFICIAL_SHA:
		_fail("Official asset was changed")
		return
	print("GODOT_HD_CAPTURE_OK ", {"views": samples, "original_hash": OFFICIAL_SHA,
		"daily_viewport_unchanged": true, "reject_busy_invalid": true, "temporary_viewport_released": true})
	quit(0)


func _fail(message: String) -> void:
	push_error(message)
	quit(1)
