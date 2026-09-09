extends "res://lookdev/render_candidate.gd"

## Codex: exercise production 1.4 profile, not a separate visual implementation.
var cases_passed := 0
var contact_images: Array[Image] = []
var contact_labels: Array[String] = []
var max_rollback := 0.0
var timings: Array = []

class Contacts extends Control:
	var pictures: Array[Image] = []
	var textures: Array[ImageTexture] = []
	var labels: Array[String] = []
	func _ready() -> void:
		for picture in pictures:
			textures.append(ImageTexture.create_from_image(picture))
	func _draw() -> void:
		draw_rect(Rect2(Vector2.ZERO, size), Color(0.055, 0.06, 0.07))
		for i in pictures.size():
			var p := Vector2((i % 3) * 400, (i / 3) * 224)
			draw_texture_rect(textures[i], Rect2(p + Vector2(0, 24), Vector2(400, 200)), false)
			draw_string(ThemeDB.fallback_font, p + Vector2(6, 19), labels[i] + " | 1.3 / 1.4", HORIZONTAL_ALIGNMENT_LEFT, 390, 14)

func _run() -> void:
	root.size = Vector2i(16, 16)
	root.position = Vector2i(-100, -100)
	root.always_on_top = false
	viewport = SubViewport.new()
	viewport.size = Vector2i(640, 640)
	viewport.own_world_3d = true
	viewport.transparent_bg = true
	viewport.msaa_3d = Viewport.MSAA_4X
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(viewport)
	runtime = load("res://main.tscn").instantiate()
	runtime.set_script(OfflineRuntime)
	viewport.add_child(runtime)
	runtime.set_model_look_version("1.4")
	_check(runtime.model_look_version == "1.4", "production 1.4 selection exists")
	if not failures.is_empty() or DisplayServer.get_name() == "headless":
		quit(1 if not failures.is_empty() else 0)
		return
	output = "user://face-expression-regression/" + Time.get_datetime_string_from_system().replace(":", "-") + "-" + str(OS.get_process_id())
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(output))
	_check(FileAccess.get_sha256("res://assets/luotianyi_v4.glb") == SHA, "official model hash")
	_check(runtime.skeleton.get_bone_count() == 703, "703 bones")
	_check(runtime.face_mesh.mesh.get_blend_shape_count() == 48, "48 shapes")
	var mesh_ref: Mesh = runtime.face_mesh.mesh
	var skin_ref: Skin = runtime.face_mesh.skin
	_pose(0, 2.0)
	var target: Vector3 = runtime.skeleton.global_transform * runtime.skeleton.get_bone_global_pose(runtime.skeleton.find_bone("頭")).origin + Vector3(0, 0.08, 0)
	runtime.camera.position = target + Vector3(0, 0, 0.60)
	runtime.camera.look_at(target, Vector3.UP)
	await _capture()
	# Prove integrated material is identical to owner-approved offline A2.
	_apply(false)
	var face_id := -1
	for index in mesh_ref.get_surface_count():
		if mesh_ref.surface_get_name(index) == "face":
			face_id = index
	var old: StandardMaterial3D = runtime.face_mesh.get_active_material(face_id)
	var other_materials: Dictionary = {}
	for index in mesh_ref.get_surface_count():
		if index != face_id:
			other_materials[index] = runtime.face_mesh.get_active_material(index)
	var preview: StandardMaterial3D = old.duplicate()
	var overlay := ShaderMaterial.new()
	overlay.shader = load("res://lookdev/face_a2.gdshader")
	overlay.set_shader_parameter("face_atlas", old.albedo_texture)
	preview.next_pass = overlay
	runtime.face_mesh.set_surface_override_material(face_id, preview)
	var approved: Image = await _capture()
	_apply(true)
	var installed: Image = await _capture()
	_check(_compare(approved, installed).rgb_mean_difference < 0.000001, "approved A2 production pixel parity")
	_check(old.next_pass == null, "1.3 original material unchanged")
	for index in other_materials:
		_check(runtime.face_mesh.get_active_material(index) == other_materials[index], "other surface unchanged " + str(index))
	for weight in [0.5, 1.0]:
		for index in range(48):
			_reset_expressions()
			runtime.face_mesh.set_blend_shape_value(index, weight)
			var label: String = str(index) + " " + str(runtime.face_mesh.mesh.get_blend_shape_name(index)) + " @" + str(weight)
			await _pair(label, true)
			_check(runtime.face_mesh.get_blend_shape_value(index) == weight, "shape value unchanged " + label)
	var mixes := [
		{"笑い":0.7, "あ":0.8}, {"まばたき":1.0, "お":0.9},
		{"困る":0.8, "口角下げ":0.8}, {"怒り":0.8, "い":0.8},
		{"にやり":0.6, "う":0.6}, {"ウィンク":1.0, "え":0.8},
		{"びっくり":0.8, "あ３":1.0}, {"下瞼上げ":0.5, "ω":1.0}]
	for i in mixes.size():
		_reset_expressions()
		for name in mixes[i]:
			runtime.face_mesh.set_blend_shape_value(runtime.expression_ids[name], mixes[i][name])
		await _pair("mix " + str(i), true)
	await _contact_sheet()
	# Actual runtime interpolation path: speaking vowels + smile/blink targets.
	_reset_expressions()
	for name in runtime.expression_ids:
		runtime.expression_targets[name] = 0.0
		runtime.expression_values[name] = 0.0
		runtime.expression_timers[name] = 0.0
	runtime.blink_timer = 100.0
	var vowels := ["あ", "い", "う", "え", "お"]
	for frame in range(180):
		var active: String = vowels[(frame / 30) % vowels.size()]
		for name in vowels:
			runtime._set_expression(name, 0.85 if name == active and frame < 150 else 0.0)
		runtime._set_expression("笑い", 0.3 if frame < 150 else 0.0)
		runtime._set_expression("まばたき", 1.0 if frame % 60 < 4 and frame < 150 else 0.0)
		runtime._process_expressions(1.0 / 30.0)
		for index in range(48):
			var value: float = runtime.face_mesh.get_blend_shape_value(index)
			_check(is_finite(value) and value >= 0 and value <= 1, "finite animated expression")
		_apply(true)
		var frame_image: Image = await _capture()
		_save(frame_image, "sequence-%03d.png" % frame)
		if frame % 15 == 0:
			await _pair("sequence " + str(frame), false)
	for name in vowels:
		_check(runtime.face_mesh.get_blend_shape_value(runtime.expression_ids[name]) < 0.01, "mouth returns closed " + name)
	_reset_expressions()
	for yaw in [-90.0, -35.0, 35.0, 90.0, 180.0]:
		runtime.model.rotation = runtime.base_model_rotation + Vector3(0, deg_to_rad(yaw), 0)
		await _pair("angle " + str(yaw), false)
	runtime.model.rotation = runtime.base_model_rotation
	await _pair("neutral-return", false)
	RenderingServer.viewport_set_measure_render_time(viewport.get_viewport_rid(), true)
	for version in ["1.3", "1.4"]:
		runtime.set_model_look_version(version)
		for warmup in range(8):
			await process_frame
		var samples: Array[float] = []
		for frame in range(60):
			await process_frame
			samples.append(RenderingServer.viewport_get_measured_render_time_gpu(viewport.get_viewport_rid()))
		samples.sort()
		_check(samples[56] > 0 and samples[56] < 16.7, "viewport GPU budget " + version)
		timings.append({"version":version,"gpu_p95_ms":samples[56]})
	for version in ["1.1", "1.2", "1.3", "1.4", ""]:
		runtime.set_model_look_version(version)
		_check(runtime.model_look_version == (runtime.MODEL_LOOK_CURRENT if version.is_empty() else version), "version switch " + version)
	_check(mesh_ref == runtime.face_mesh.mesh and skin_ref == runtime.face_mesh.skin, "same mesh/skin resources")
	_check(FileAccess.get_sha256("res://assets/luotianyi_v4.glb") == SHA, "official hash after")
	var report := {"status":"PASS" if failures.is_empty() else "FAIL", "failures":failures,"pairs":cases_passed,
		"shapes":48,"weights":[0.5,1.0],"mixes":mixes.size(),"continuous_frames":180,"rollback_max":max_rollback,
		"timings":timings,"model_sha":SHA,"output":ProjectSettings.globalize_path(output)}
	var file := FileAccess.open(output + "/report.json", FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"\t"))
	file.close()
	print("FACE_EXPRESSIONS_",report.status," ",JSON.stringify(report))
	quit(0 if failures.is_empty() else 1)

func _apply(enabled: bool) -> void:
	runtime.set_model_look_version("1.4" if enabled else "1.3")

func _reset_expressions() -> void:
	for index in range(48):
		runtime.face_mesh.set_blend_shape_value(index, 0.0)

func _pair(label: String, contact: bool) -> void:
	var invariant := _invariants()
	_apply(false)
	var a: Image = await _capture()
	_apply(true)
	var b: Image = await _capture()
	_check(_invariants() == invariant, "pose parity " + label)
	_check(_compare(a,b).alpha_differences == 0 and a.get_used_rect() == b.get_used_rect(), "alpha parity " + label)
	_apply(false)
	var back: Image = await _capture()
	var delta: float = _compare(a,back).rgb_mean_difference
	max_rollback = maxf(max_rollback,delta)
	_check(delta < 0.000002, "rollback " + label)
	if contact:
		var combined := Image.create(1280,640,false,Image.FORMAT_RGBA8)
		combined.blit_rect(a,Rect2i(0,0,640,640),Vector2i.ZERO)
		combined.blit_rect(b,Rect2i(0,0,640,640),Vector2i(640,0))
		_save(combined,"pair-%03d.png" % cases_passed)
		contact_images.append(combined)
		contact_labels.append(label)
		if contact_images.size() == 12:
			await _contact_sheet()
	cases_passed += 1
	if cases_passed % 12 == 0:
		print("FACE_EXPRESSION_PROGRESS ",cases_passed)

func _contact_sheet() -> void:
	if contact_images.is_empty():
		return
	var target := SubViewport.new()
	target.size = Vector2i(1200,896)
	target.disable_3d = true
	target.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(target)
	var sheet := Contacts.new()
	sheet.size = target.size
	sheet.pictures = contact_images.duplicate()
	sheet.labels = contact_labels.duplicate()
	target.add_child(sheet)
	await process_frame
	await RenderingServer.frame_post_draw
	_save(target.get_texture().get_image(),"contacts-%03d.png" % cases_passed)
	target.queue_free()
	contact_images.clear()
	contact_labels.clear()
