extends SceneTree

## Codex: actual Godot A/B renders, not generated concept art. Never runs the
## production _ready, bridge, UI, window persistence, or startup screenshot.
const Candidate := preload("res://model_look_v13.gd")
const SHA := "df55806d343d149b41c20d0ef074373cafca2379212fd8691e998ea6cddc6e4a"
var output := ""
var runtime: Node
var viewport: SubViewport
var baseline_materials: Dictionary = {}
var candidate_materials: Dictionary = {}
var failures: Array[String] = []

class OfflineRuntime extends "res://runtime.gd":
	func _ready() -> void:
		set_process(false)
		set_process_input(false)
		base_model_rotation = model.rotation
		base_model_position = model.position
		camera.fov = _avatar_composite_fov()
		camera.position = Vector3(0.0, CAMERA_FOCUS.y, MIN_CAMERA_DISTANCE)
		camera.look_at(CAMERA_FOCUS, Vector3.UP)
		skeleton = _find_skeleton(model)
		_cache_bones()
		_cache_deform_bone_mirrors()
		_cache_expressions()
		set_model_look_preview(true)
		_restore_bone_poses()
		_cache_action_axes()
		_prepare_authored_motions()
		authored_motion_player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	func _update_hud() -> void:
		pass

class Sheet extends Control:
	var left: Texture2D
	var right: Texture2D
	func _draw() -> void:
		var width := left.get_width()
		draw_rect(Rect2(Vector2.ZERO, size), Color(0.055, 0.06, 0.07))
		draw_texture(left, Vector2(0, 72))
		draw_texture(right, Vector2(width + 24, 72))
		draw_string(ThemeDB.fallback_font, Vector2(24, 32), "1.2  BASELINE", HORIZONTAL_ALIGNMENT_LEFT, -1, 24)
		draw_string(ThemeDB.fallback_font, Vector2(width + 48, 32), "1.3  ACCEPTED", HORIZONTAL_ALIGNMENT_LEFT, -1, 24)
		draw_string(ThemeDB.fallback_font, Vector2(24, 57), "SAME POSE / CAMERA / RESOLUTION", HORIZONTAL_ALIGNMENT_LEFT, -1, 15, Color(0.65, 0.70, 0.78))
		draw_string(ThemeDB.fallback_font, Vector2(width + 48, 57), "REVIEWED MATERIAL PROFILE", HORIZONTAL_ALIGNMENT_LEFT, -1, 15, Color(0.65, 0.70, 0.78))

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	if DisplayServer.get_name() == "headless":
		push_error("Use a real rendering driver; headless is not visual evidence")
		quit(1)
		return
	output = "user://lookdev-1.3-candidate/" + Time.get_datetime_string_from_system().replace(":", "-") + "-" + str(OS.get_process_id())
	if DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(output)) != OK:
		quit(1)
		return
	# Minimizing the main window suppresses frame_post_draw on this driver.
	# Keep a tiny offscreen diagnostic window so GPU captures can complete.
	root.always_on_top = false
	root.size = Vector2i(16, 16)
	root.position = Vector2i(-100, -100)
	viewport = SubViewport.new()
	viewport.size = Vector2i(1920, 2320)
	viewport.own_world_3d = true
	viewport.transparent_bg = true
	viewport.msaa_3d = Viewport.MSAA_4X
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(viewport)
	RenderingServer.viewport_set_measure_render_time(viewport.get_viewport_rid(), true)
	runtime = load("res://main.tscn").instantiate()
	runtime.set_script(OfflineRuntime)
	viewport.add_child(runtime)
	_check(FileAccess.get_sha256("res://assets/luotianyi_v4.glb") == SHA, "official GLB hash before")
	_check(runtime.skeleton.get_bone_count() == 703, "703 runtime bones")
	_check(runtime.face_mesh.mesh.get_blend_shape_count() == 48, "48 expressions")
	_check(runtime.face_mesh.mesh.get_surface_count() == 23, "23 surfaces")
	_check(runtime.pigtail_chains.size() == 2 and runtime.pigtail_chains[0].size() == 17 and runtime.pigtail_chains[1].size() == 17, "complete pigtail chains")
	for index in runtime.model_look_preview_materials:
		var material: StandardMaterial3D = runtime.face_mesh.get_active_material(index)
		var surface: String = runtime.face_mesh.mesh.surface_get_name(index)
		baseline_materials[index] = material
		candidate_materials[index] = Candidate.make_material(material, surface)
		_check(candidate_materials[index].albedo_texture == material.albedo_texture, "same official texture " + surface)
		_check(candidate_materials[index].transparency == material.transparency, "same transparency " + surface)
	_check(candidate_materials.size() == 10, "10 material copies")
	for selection in ["1.1", "1.2", "1.3", "", "baseline", "1.2-preview"]:
		runtime.set_model_look_version(selection)
		var expected: String = "1.3" if selection.is_empty() else ("1.1" if selection == "baseline" else ("1.2" if selection == "1.2-preview" else selection))
		_check(runtime.model_look_version == expected, "profile selection " + selection)
	_apply(true)
	for index in candidate_materials:
		var actual: StandardMaterial3D = runtime.face_mesh.get_active_material(index)
		var expected: StandardMaterial3D = candidate_materials[index]
		for property in ["albedo_color", "emission_energy_multiplier", "roughness", "rim", "diffuse_mode", "specular_mode", "metallic_specular", "albedo_texture"]:
			_check(actual.get(property) == expected.get(property), "accepted candidate parity " + property)
	# Negative controls: prove the tests detect a changed silhouette and pose.
	var transparent_probe := Image.create(4, 4, false, Image.FORMAT_RGBA8)
	transparent_probe.fill(Color.TRANSPARENT)
	var opaque_probe := Image.create(4, 4, false, Image.FORMAT_RGBA8)
	opaque_probe.fill(Color.WHITE)
	_check(_compare(transparent_probe, opaque_probe).alpha_differences > 0, "alpha negative control")
	var original_pose := _invariants()
	var original_transform: Transform3D = runtime.model.transform
	runtime.model.position.x += 0.01
	_check(original_pose != _invariants(), "transform negative control")
	runtime.model.transform = original_transform
	var cases := [
		{"id": "front", "yaw": 0.0}, {"id": "left", "yaw": 90.0},
		{"id": "right", "yaw": -90.0}, {"id": "back", "yaw": 180.0},
		{"id": "three-quarter", "yaw": 35.0}, {"id": "daily-size", "yaw": 0.0, "distance": 3.8},
		{"id": "max-zoom", "yaw": 0.0}, {"id": "neutral-face", "yaw": 0.0},
		{"id": "expression-extremes", "yaw": 0.0, "expression": true},
	]
	var reports: Array = []
	for view in cases:
		_pose(float(view.yaw), 2.0)
		runtime.camera.position.z = float(view.get("distance", runtime.MIN_CAMERA_DISTANCE))
		if view.get("expression", false):
			runtime.face_mesh.set_blend_shape_value(runtime.expression_ids["笑い"], 0.88)
		var invariants := _invariants()
		_apply(false)
		var before: Image = await _capture()
		_apply(true)
		var after: Image = await _capture()
		_check(invariants == _invariants(), "pose/camera/geometry unchanged " + str(view.id))
		var metrics := _compare(before, after)
		_check(metrics.alpha_differences == 0 and before.get_used_rect() == after.get_used_rect(), "silhouette parity " + str(view.id))
		_check(metrics.rgb_mean_difference > 0.001, "visible pixel change " + str(view.id))
		_check(metrics.luminance_ratio > 0.80 and metrics.luminance_ratio < 1.20, "bounded exposure " + str(view.id))
		var rect := before.get_used_rect()
		_check(rect.position.x > 8 and rect.position.y > 8 and rect.end.x < 1912 and rect.end.y < 2312, "inside render target " + str(view.id))
		_save(before, "1.2-" + str(view.id) + ".png")
		_save(after, "1.3-candidate-" + str(view.id) + ".png")
		_save(after, str(view.id) + ".png")
		await _sheet(before, after, rect.grow(48).intersection(Rect2i(Vector2i.ZERO, before.get_size())), "ab-" + str(view.id) + ".png")
		if view.id == "front":
			var face_rect := Rect2i(rect.position.x + rect.size.x / 4, rect.position.y, rect.size.x / 2, rect.size.y / 3)
			await _sheet(before, after, face_rect, "ab-face.png")
		_apply(false)
		var rollback: Image = await _capture()
		var rollback_difference := _compare(before, rollback)
		_check(rollback_difference.rgb_mean_difference < 0.000001 and rollback_difference.alpha_differences == 0, "pixel rollback " + str(view.id))
		metrics["view"] = view.id
		metrics["rollback_rgb_mean_difference"] = rollback_difference.rgb_mean_difference
		reports.append(metrics)
		print("LOOKDEV_VIEW ", metrics)
	# Additional moving idle samples with changing view direction. This verifies
	# look parity, NOT collision safety or universal temporal stability.
	for sample in range(12):
		_pose(float(sample) * 30.0, float(sample) * 0.6)
		_apply(false)
		var before: Image = await _capture()
		_apply(true)
		var after: Image = await _capture()
		_check(_compare(before, after).alpha_differences == 0, "moving-pose silhouette " + str(sample))
	_pose(0.0, 2.0)
	var timings: Array = []
	for enabled in [false, true, false, true]:
		_apply(enabled)
		for warmup in range(8):
			await process_frame
		var start := Time.get_ticks_usec()
		var gpu_samples: Array[float] = []
		for sample in range(60):
			await process_frame
			gpu_samples.append(RenderingServer.viewport_get_measured_render_time_gpu(viewport.get_viewport_rid()))
		gpu_samples.sort()
		var gpu_mean := 0.0
		for sample in gpu_samples:
			gpu_mean += sample / gpu_samples.size()
		_check(gpu_mean > 0 and gpu_samples[56] < 16.7, "GPU render p95 under 16.7ms " + str(enabled))
		timings.append({"candidate": enabled, "wall_frame_ms": (Time.get_ticks_usec() - start) / 60000.0,
			"gpu_mean_ms": gpu_mean, "gpu_p95_ms": gpu_samples[56]})
	_apply(false)
	_check(FileAccess.get_sha256("res://assets/luotianyi_v4.glb") == SHA, "official GLB hash after")
	var report := {"status": "PASS" if failures.is_empty() else "FAIL", "failures": failures,
		"baseline": "1.2 material profile, current conservative idle", "candidate": "1.3 accepted candidate A, production profile API verified",
		"render_size": str(viewport.size), "msaa": "4x on both", "light_camera_parity": true,
		"official_glb_sha256": SHA, "material_profiles": Candidate.PROFILES,
		"views": reports, "moving_pose_checks": 12, "timings": timings,
		"performance_note": "GPU render time is measured per 3D viewport; wall interval includes background throttling; not whole desktop end-to-end latency",
		"output": ProjectSettings.globalize_path(output)}
	var file := FileAccess.open(output + "/report.json", FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t"))
	file.close()
	print("LOOKDEV_CANDIDATE_", report.status, " ", JSON.stringify(report))
	quit(0 if failures.is_empty() else 1)

func _pose(yaw: float, time: float) -> void:
	runtime._cancel_authored_motion()
	runtime.skeleton.reset_bone_poses()
	runtime._play_authored_motion(&"idle")
	runtime.authored_motion_player.seek(time, true)
	runtime.elapsed = time
	runtime._apply_pigtail_pose()
	runtime.model.rotation = runtime.base_model_rotation + Vector3(0, deg_to_rad(yaw), 0)
	for index in range(runtime.face_mesh.mesh.get_blend_shape_count()):
		runtime.face_mesh.set_blend_shape_value(index, 0.0)

func _invariants() -> Array:
	var result: Array = [runtime.model.transform, runtime.camera.transform, runtime.camera.fov, runtime.face_mesh.get_aabb()]
	for light in [runtime.key_light, runtime.fill_light]:
		result.append([light.transform, light.light_color, light.light_energy])
	for index in range(runtime.skeleton.get_bone_count()):
		result.append(runtime.skeleton.get_bone_pose(index))
	return result

func _apply(candidate: bool) -> void:
	runtime.set_model_look_version("1.3" if candidate else "1.2")

func _capture() -> Image:
	await process_frame
	await process_frame
	await RenderingServer.frame_post_draw
	return viewport.get_texture().get_image()

func _save(image: Image, name: String) -> void:
	_check(image.save_png(output + "/" + name) == OK, "save " + name)

func _compare(a: Image, b: Image) -> Dictionary:
	var changed_alpha := 0
	var count := 0
	var difference := 0.0
	var luminance_a := 0.0
	var luminance_b := 0.0
	# Explicit 2-pixel grid; full-frame used rectangles are checked separately.
	for y in range(0, a.get_height(), 2):
		for x in range(0, a.get_width(), 2):
			var p := a.get_pixel(x, y)
			var q := b.get_pixel(x, y)
			if absf(p.a - q.a) > 0.001:
				changed_alpha += 1
			if p.a < 0.99 or q.a < 0.99:
				continue
			count += 1
			difference += (absf(p.r-q.r) + absf(p.g-q.g) + absf(p.b-q.b)) / 3.0
			luminance_a += p.get_luminance()
			luminance_b += q.get_luminance()
	return {"alpha_differences": changed_alpha, "opaque_samples": count,
		"rgb_mean_difference": difference / maxf(1, count), "luminance_ratio": luminance_b / maxf(0.001, luminance_a)}

func _sheet(before: Image, after: Image, crop: Rect2i, name: String) -> void:
	var target := SubViewport.new()
	target.size = Vector2i(crop.size.x * 2 + 24, crop.size.y + 72)
	target.disable_3d = true
	target.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(target)
	var sheet := Sheet.new()
	sheet.left = ImageTexture.create_from_image(before.get_region(crop))
	sheet.right = ImageTexture.create_from_image(after.get_region(crop))
	sheet.size = target.size
	target.add_child(sheet)
	await process_frame
	await RenderingServer.frame_post_draw
	_save(target.get_texture().get_image(), name)
	target.queue_free()

func _check(condition: bool, label: String) -> void:
	if not condition:
		failures.append(label)
		push_error("LOOKDEV_CHECK_FAILED " + label)
