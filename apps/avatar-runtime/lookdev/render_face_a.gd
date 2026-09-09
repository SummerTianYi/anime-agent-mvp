extends "res://lookdev/render_candidate.gd"

## Codex: isolated face-material experiment. Never selected by production.
var original: StandardMaterial3D
var face_candidate: StandardMaterial3D
var overlay: ShaderMaterial
var face_index := -1
var shader_path := "res://lookdev/face_a.gdshader"
var revision := "A1"
var sheet_left_label := "v1.3 BASELINE"

class FaceSheet extends Control:
	var left: Texture2D
	var right: Texture2D
	var left_label := "v1.3 BASELINE"
	var right_label := "FACE A1 / PREVIEW ONLY"
	func _draw() -> void:
		var w := left.get_width()
		draw_rect(Rect2(Vector2.ZERO, size), Color(0.055, 0.06, 0.07))
		draw_texture(left, Vector2(0, 72))
		draw_texture(right, Vector2(w + 24, 72))
		draw_string(ThemeDB.fallback_font, Vector2(16, 30), left_label, HORIZONTAL_ALIGNMENT_LEFT, -1, 22)
		draw_string(ThemeDB.fallback_font, Vector2(w + 40, 30), right_label, HORIZONTAL_ALIGNMENT_LEFT, -1, 22)
		draw_string(ThemeDB.fallback_font, Vector2(16, 55), "SAME CAMERA / POSE / LIGHT", HORIZONTAL_ALIGNMENT_LEFT, -1, 14)
		draw_string(ThemeDB.fallback_font, Vector2(w + 40, 55), "NO GEOMETRY CHANGES", HORIZONTAL_ALIGNMENT_LEFT, -1, 14)

func _run() -> void:
	if OS.get_environment("FACE_REVIEW_REVISION") == "A2":
		revision = "A2"
		shader_path = "res://lookdev/face_a2.gdshader"
	if DisplayServer.get_name() == "headless":
		quit(1)
		return
	output = "user://lookdev-face-a/" + Time.get_datetime_string_from_system().replace(":", "-") + "-" + str(OS.get_process_id())
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(output))
	var hash_before := FileAccess.get_sha256("res://assets/luotianyi_v4.glb")
	_check(hash_before == SHA, "official source baseline")
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
	runtime = load("res://main.tscn").instantiate()
	runtime.set_script(OfflineRuntime)
	viewport.add_child(runtime)
	runtime.set_model_look_version("1.3")
	for index in range(runtime.face_mesh.mesh.get_surface_count()):
		if runtime.face_mesh.mesh.surface_get_name(index) == "face":
			face_index = index
			original = runtime.face_mesh.get_active_material(index)
	_check(face_index >= 0 and original != null, "face material found")
	if not failures.is_empty():
		quit(1)
		return
	_check(original.next_pass == null, "no existing face next pass")
	face_candidate = original.duplicate()
	overlay = ShaderMaterial.new()
	overlay.shader = load(shader_path)
	overlay.set_shader_parameter("face_atlas", original.albedo_texture)
	face_candidate.next_pass = overlay
	_check(face_candidate.albedo_texture == original.albedo_texture, "atlas shared read only")
	var mesh_ref: Mesh = runtime.face_mesh.mesh
	var skin_ref: Skin = runtime.face_mesh.skin
	var untouched: Array = []
	for i in range(mesh_ref.get_surface_count()):
		untouched.append(runtime.face_mesh.get_active_material(i))
	var views := [
		{"id":"front", "yaw":0.0}, {"id":"three-quarter", "yaw":35.0},
		{"id":"side", "yaw":-90.0}, {"id":"other-side", "yaw":90.0},
		{"id":"smile", "yaw":0.0, "expression":"にやり"},
		{"id":"speaking-a", "yaw":0.0, "expression":"あ"},
		{"id":"speaking-o", "yaw":35.0, "expression":"お"},
		{"id":"daily-size", "yaw":0.0, "daily":true}]
	var reports: Array = []
	for view in views:
		_pose(float(view.yaw), 2.0)
		if view.has("expression"):
			runtime.face_mesh.set_blend_shape_value(runtime.expression_ids[view.expression], 0.8)
		if view.get("daily", false):
			viewport.size = Vector2i(560, 760)
			runtime.camera.position = Vector3(0, runtime.CAMERA_FOCUS.y, 3.8)
			runtime.camera.look_at(runtime.CAMERA_FOCUS, Vector3.UP)
		else:
			viewport.size = Vector2i(1200, 1200)
			var head_index: int = runtime.skeleton.find_bone("頭")
			_check(head_index >= 0, "head bone exists")
			var target: Vector3 = runtime.skeleton.global_transform * runtime.skeleton.get_bone_global_pose(head_index).origin + Vector3(0, 0.08, 0)
			runtime.camera.position = target + Vector3(0, 0, 0.60)
			runtime.camera.look_at(target, Vector3.UP)
		for warmup in range(8):
			await process_frame
		var invariant := _invariants()
		_apply(false)
		var before: Image = await _capture()
		if view.id == "front":
			_apply(true)
			overlay.set_shader_parameter("strength", 0.0)
			var disabled: Image = await _capture()
			_check(_compare(before, disabled).rgb_mean_difference < 0.000001, "zero-strength negative control")
			overlay.set_shader_parameter("strength", 1.0)
		_apply(true)
		var after: Image = await _capture()
		_check(invariant == _invariants(), "all poses/camera/lights unchanged " + view.id)
		_check(mesh_ref == runtime.face_mesh.mesh and skin_ref == runtime.face_mesh.skin, "same mesh and skin " + view.id)
		for i in range(mesh_ref.get_surface_count()):
			if i != face_index:
				_check(untouched[i] == runtime.face_mesh.get_active_material(i), "other material unchanged " + str(i))
		var result := _compare(before, after)
		if view.id == "front":
			_check(result.rgb_mean_difference > 0.00002, "candidate has actual visible pixel changes")
		_check(result.alpha_differences == 0, "alpha unchanged " + view.id)
		_check(before.get_used_rect() == after.get_used_rect(), "same silhouette bounds " + view.id)
		_save(before, "baseline-" + view.id + ".png")
		_save(after, "candidate-" + view.id + ".png")
		await _sheet(before, after, Rect2i(Vector2i.ZERO, before.get_size()), "compare-" + view.id + ".png")
		if revision == "A2":
			overlay.shader = load("res://lookdev/face_a.gdshader")
			overlay.set_shader_parameter("face_atlas", original.albedo_texture)
			var previous: Image = await _capture()
			_save(previous, "previous-a1-" + view.id + ".png")
			sheet_left_label = "FACE A1 / PREVIOUS"
			await _sheet(previous, after, Rect2i(Vector2i.ZERO, before.get_size()), "a1-vs-a2-" + view.id + ".png")
			sheet_left_label = "v1.3 BASELINE"
			overlay.shader = load(shader_path)
			overlay.set_shader_parameter("face_atlas", original.albedo_texture)
		_apply(false)
		var restored: Image = await _capture()
		var rollback_difference: float = _compare(before, restored).rgb_mean_difference
		_check(rollback_difference < 0.000001, "exact visual rollback " + view.id)
		result["rollback_difference"] = rollback_difference
		result["view"] = view.id
		reports.append(result)
		print("FACE_A_VIEW ", view.id, " ", result)
	_check(FileAccess.get_sha256("res://assets/luotianyi_v4.glb") == hash_before, "official model unchanged")
	_check(runtime.skeleton.get_bone_count() == 703 and mesh_ref.get_blend_shape_count() == 48, "rig/expression counts")
	_check(original.next_pass == null, "source material unchanged")
	var report := {"status":"PASS" if failures.is_empty() else "FAIL", "failures":failures,
		"views":reports, "model_sha256":hash_before, "scope":"face-only UV pigment overlay; source atlas, geometry, rig, expressions, eye and hair materials unchanged; offline preview only",
		"revision":revision, "shader_path":shader_path,
		"shader_sha256":FileAccess.get_sha256(shader_path), "output":ProjectSettings.globalize_path(output)}
	var file := FileAccess.open(output + "/report.json", FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t"))
	file.close()
	print("FACE_A_", report.status, " ", report.output)
	quit(0 if failures.is_empty() else 1)

func _apply(candidate: bool) -> void:
	runtime.face_mesh.set_surface_override_material(face_index, face_candidate if candidate else original)

func _sheet(before: Image, after: Image, crop: Rect2i, name: String) -> void:
	var target := SubViewport.new()
	target.size = Vector2i(crop.size.x * 2 + 24, crop.size.y + 72)
	target.disable_3d = true
	target.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(target)
	var sheet := FaceSheet.new()
	sheet.left_label = sheet_left_label
	sheet.right_label = "FACE " + revision + " / PREVIEW ONLY"
	sheet.left = ImageTexture.create_from_image(before.get_region(crop))
	sheet.right = ImageTexture.create_from_image(after.get_region(crop))
	sheet.size = target.size
	target.add_child(sheet)
	await process_frame
	await RenderingServer.frame_post_draw
	_save(target.get_texture().get_image(), name)
	target.queue_free()
