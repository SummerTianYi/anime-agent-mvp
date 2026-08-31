extends SceneTree


const OFFICIAL_MODEL_PATH := "res://assets/luotianyi_v4.glb"
const OFFICIAL_MODEL_SHA256 := "df55806d343d149b41c20d0ef074373cafca2379212fd8691e998ea6cddc6e4a"
const EXPECTED_SURFACES := 23
const EXPECTED_BLEND_SHAPES := 48
## The Blender source rig has 751 bones; the exported runtime GLB intentionally
## carries the 703 skinned/deform bones used by Godot.
const EXPECTED_BONES := 703
const PREVIEW_DIR := "user://model-look-1.2-preview"
const MIN_PREVIEW_LUMINANCE := 0.52
const MAX_PREVIEW_LUMINANCE := 0.62
const MAX_CLIPPED_RATIO := 0.08
const MAX_FRAME_TIME_MS := 18.5
const MAX_FRAME_TIME_REGRESSION := 1.12


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	if DisplayServer.get_name() == "headless":
		_fail("This verification requires a rendering display driver")
		return
	var scene := load("res://main.tscn") as PackedScene
	if scene == null:
		_fail("Unable to load main scene")
		return
	var runtime: Node = scene.instantiate()
	root.add_child(runtime)
	await process_frame
	await process_frame
	runtime._cancel_authored_motion()
	runtime.set_process(false)
	if not _verify_structure(runtime):
		return
	var invariant_model_transform: Transform3D = runtime.model.transform
	var invariant_camera_transform: Transform3D = runtime.camera.transform
	var invariant_camera_fov: float = runtime.camera.fov
	var invariant_mesh_aabb: AABB = runtime.face_mesh.get_aabb()

	runtime.set_model_look_preview(false)
	await process_frame
	await process_frame
	var baseline: Image = runtime.avatar_render_viewport.get_texture().get_image()
	runtime.set_model_look_preview(true)
	await process_frame
	await process_frame
	var preview: Image = runtime.avatar_render_viewport.get_texture().get_image()
	if baseline.is_empty() or preview.is_empty() or baseline.get_size() != preview.get_size():
		_fail("A/B render capture failed")
		return

	var baseline_metrics := _image_metrics(baseline)
	var preview_metrics := _image_metrics(preview)
	var alpha_difference := _alpha_difference_ratio(baseline, preview)
	if alpha_difference > 0.0001:
		_fail("The look profile changed avatar geometry/alpha: %.6f" % alpha_difference)
		return
	if float(preview_metrics["clipped_ratio"]) >= float(baseline_metrics["clipped_ratio"]):
		_fail("Preview did not reduce clipped highlights")
		return
	var preview_luminance := float(preview_metrics["average_luminance"])
	if preview_luminance < MIN_PREVIEW_LUMINANCE or preview_luminance > MAX_PREVIEW_LUMINANCE:
		_fail("Preview luminance is outside the review range: %.4f" % preview_luminance)
		return
	if float(preview_metrics["clipped_ratio"]) > MAX_CLIPPED_RATIO:
		_fail("Preview still clips too many highlights")
		return

	var output_dir := ProjectSettings.globalize_path(PREVIEW_DIR)
	DirAccess.make_dir_recursive_absolute(output_dir)
	baseline.save_png(PREVIEW_DIR + "/1.1-baseline-front.png")
	preview.save_png(PREVIEW_DIR + "/1.2-preview-front.png")
	var contact := _make_contact_sheet(baseline, preview)
	contact.save_png(PREVIEW_DIR + "/ab-front.png")
	var projection_parity: Dictionary = await _verify_projection_parity(runtime)
	if projection_parity.is_empty():
		return
	var review_views: Dictionary = await _save_review_views(runtime)
	if review_views.is_empty():
		return
	var baseline_frame_ms: float = await _benchmark_frame_time(runtime, false)
	var preview_frame_ms: float = await _benchmark_frame_time(runtime, true)
	if preview_frame_ms > MAX_FRAME_TIME_MS:
		_fail("Preview frame time exceeds the MVP target: %.3f ms" % preview_frame_ms)
		return
	if preview_frame_ms > baseline_frame_ms * MAX_FRAME_TIME_REGRESSION:
		_fail("Preview frame time regressed too far: %.3f -> %.3f ms" % [baseline_frame_ms, preview_frame_ms])
		return

	runtime.set_model_look_preview(false)
	await process_frame
	await process_frame
	var rollback: Image = runtime.avatar_render_viewport.get_texture().get_image()
	var rollback_difference := _rgba_difference_ratio(baseline, rollback)
	if rollback_difference > 0.0:
		_fail("Disabling the preview did not restore the exact 1.1 render")
		return
	runtime.set_model_look_preview(true)
	if not runtime.model.transform.is_equal_approx(invariant_model_transform):
		_fail("The look profile changed the model transform")
		return
	if not runtime.camera.transform.is_equal_approx(invariant_camera_transform) \
			or not is_equal_approx(runtime.camera.fov, invariant_camera_fov):
		_fail("The look profile changed the camera projection")
		return
	var final_aabb: AABB = runtime.face_mesh.get_aabb()
	if not final_aabb.position.is_equal_approx(invariant_mesh_aabb.position) \
			or not final_aabb.size.is_equal_approx(invariant_mesh_aabb.size):
		_fail("The look profile changed the mesh bounds")
		return

	print("GODOT_MODEL_LOOK_PREVIEW_OK", {
		"official_model_sha256": FileAccess.get_sha256(OFFICIAL_MODEL_PATH),
		"surface_count": runtime.face_mesh.mesh.get_surface_count(),
		"blend_shapes": runtime.face_mesh.mesh.get_blend_shape_count(),
		"bones": runtime.skeleton.get_bone_count(),
		"target_surfaces": runtime.model_look_preview_materials.size(),
		"baseline": baseline_metrics,
		"preview": preview_metrics,
		"alpha_difference_ratio": alpha_difference,
		"projection_parity": projection_parity,
		"mesh_aabb": invariant_mesh_aabb,
		"model_transform": invariant_model_transform,
		"camera_transform": invariant_camera_transform,
		"camera_fov": invariant_camera_fov,
		"rollback_difference_ratio": rollback_difference,
		"baseline_frame_ms": baseline_frame_ms,
		"preview_frame_ms": preview_frame_ms,
		"review_views": review_views,
		"contact_sheet": ProjectSettings.globalize_path(PREVIEW_DIR + "/ab-front.png"),
	})
	quit(0)


func _verify_structure(runtime: Node) -> bool:
	var actual_hash := FileAccess.get_sha256(OFFICIAL_MODEL_PATH).to_lower()
	if actual_hash != OFFICIAL_MODEL_SHA256:
		_fail("Official model hash changed: %s" % actual_hash)
		return false
	if runtime.face_mesh == null or runtime.face_mesh.mesh == null or runtime.skeleton == null:
		_fail("Runtime mesh or skeleton is unavailable")
		return false
	if runtime.face_mesh.mesh.get_surface_count() != EXPECTED_SURFACES:
		_fail("Official material slot count changed")
		return false
	if runtime.face_mesh.mesh.get_blend_shape_count() != EXPECTED_BLEND_SHAPES:
		_fail("Official expression count changed")
		return false
	if runtime.skeleton.get_bone_count() != EXPECTED_BONES:
		_fail("Official skeleton count changed: %d" % runtime.skeleton.get_bone_count())
		return false
	return true


func _image_metrics(source: Image) -> Dictionary:
	var image := source.duplicate()
	image.resize(480, 580, Image.INTERPOLATE_BILINEAR)
	var opaque_pixels := 0
	var clipped_pixels := 0
	var luminance_sum := 0.0
	for y in range(image.get_height()):
		for x in range(image.get_width()):
			var pixel: Color = image.get_pixel(x, y)
			if pixel.a < 0.08:
				continue
			opaque_pixels += 1
			var luminance: float = pixel.r * 0.2126 + pixel.g * 0.7152 + pixel.b * 0.0722
			luminance_sum += luminance
			if maxf(pixel.r, maxf(pixel.g, pixel.b)) >= 0.96:
				clipped_pixels += 1
	return {
		"opaque_pixels": opaque_pixels,
		"average_luminance": luminance_sum / maxf(float(opaque_pixels), 1.0),
		"clipped_ratio": float(clipped_pixels) / maxf(float(opaque_pixels), 1.0),
		"used_rect": image.get_used_rect(),
	}


func _alpha_difference_ratio(left_source: Image, right_source: Image) -> float:
	var left := left_source.duplicate()
	var right := right_source.duplicate()
	left.resize(480, 580, Image.INTERPOLATE_BILINEAR)
	right.resize(480, 580, Image.INTERPOLATE_BILINEAR)
	var differing := 0
	var considered := 0
	for y in range(left.get_height()):
		for x in range(left.get_width()):
			var left_alpha: float = left.get_pixel(x, y).a
			var right_alpha: float = right.get_pixel(x, y).a
			if maxf(left_alpha, right_alpha) < 0.02:
				continue
			considered += 1
			if absf(left_alpha - right_alpha) > 0.02:
				differing += 1
	return float(differing) / maxf(float(considered), 1.0)


func _rgba_difference_ratio(left_source: Image, right_source: Image) -> float:
	var left := left_source.duplicate()
	var right := right_source.duplicate()
	left.resize(480, 580, Image.INTERPOLATE_BILINEAR)
	right.resize(480, 580, Image.INTERPOLATE_BILINEAR)
	var differing := 0
	for y in range(left.get_height()):
		for x in range(left.get_width()):
			var left_pixel: Color = left.get_pixel(x, y)
			var right_pixel: Color = right.get_pixel(x, y)
			if not left_pixel.is_equal_approx(right_pixel):
				differing += 1
	return float(differing) / float(left.get_width() * left.get_height())


func _verify_projection_parity(runtime: Node) -> Dictionary:
	var base_rotation: Vector3 = runtime.base_model_rotation
	var base_distance: float = runtime.BASE_CAMERA_DISTANCE
	var cases := [
		{"id": "front", "yaw": 0.0},
		{"id": "left", "yaw": PI * 0.5},
		{"id": "right", "yaw": -PI * 0.5},
		{"id": "back", "yaw": PI},
	]
	var output := {}
	for view_case in cases:
		runtime.model.rotation = base_rotation + Vector3(0.0, float(view_case["yaw"]), 0.0)
		runtime.camera.position = Vector3(0.0, runtime.CAMERA_FOCUS.y, base_distance)
		runtime.camera.look_at(runtime.CAMERA_FOCUS, Vector3.UP)
		runtime.set_model_look_preview(false)
		await process_frame
		await process_frame
		var baseline: Image = runtime.avatar_render_viewport.get_texture().get_image()
		runtime.set_model_look_preview(true)
		await process_frame
		await process_frame
		var preview: Image = runtime.avatar_render_viewport.get_texture().get_image()
		if baseline.is_empty() or preview.is_empty() or baseline.get_size() != preview.get_size():
			_fail("Projection parity capture failed: %s" % view_case["id"])
			return {}
		var alpha_difference := _alpha_difference_ratio(baseline, preview)
		var baseline_rect := baseline.get_used_rect()
		var preview_rect := preview.get_used_rect()
		if alpha_difference > 0.0001 or baseline_rect != preview_rect:
			_fail(
				"Look profile changed the %s silhouette: alpha %.6f, %s -> %s"
				% [view_case["id"], alpha_difference, baseline_rect, preview_rect]
			)
			return {}
		var relative_path := PREVIEW_DIR + "/ab-%s.png" % view_case["id"]
		_make_contact_sheet(baseline, preview).save_png(relative_path)
		output[str(view_case["id"])] = {
			"alpha_difference_ratio": alpha_difference,
			"used_rect": baseline_rect,
			"contact_sheet": ProjectSettings.globalize_path(relative_path),
		}
	runtime.model.rotation = base_rotation
	runtime.camera.position = Vector3(0.0, runtime.CAMERA_FOCUS.y, base_distance)
	runtime.camera.look_at(runtime.CAMERA_FOCUS, Vector3.UP)
	runtime.set_model_look_preview(true)
	await process_frame
	await process_frame
	return output


func _save_review_views(runtime: Node) -> Dictionary:
	var base_rotation: Vector3 = runtime.base_model_rotation
	var base_distance: float = runtime.BASE_CAMERA_DISTANCE
	var cases := [
		{"id": "left", "yaw": PI * 0.5, "distance": base_distance},
		{"id": "right", "yaw": -PI * 0.5, "distance": base_distance},
		{"id": "back", "yaw": PI, "distance": base_distance},
		{"id": "max-zoom", "yaw": 0.0, "distance": runtime.MIN_CAMERA_DISTANCE},
		{"id": "neutral-face", "yaw": 0.0, "distance": runtime.MIN_CAMERA_DISTANCE},
		{"id": "expression-extremes", "yaw": 0.0, "distance": runtime.MIN_CAMERA_DISTANCE, "expression": true},
	]
	var output := {}
	for view_case in cases:
		_reset_expression_blend_shapes(runtime)
		runtime.model.rotation = base_rotation + Vector3(0.0, float(view_case["yaw"]), 0.0)
		runtime.camera.position = Vector3(0.0, runtime.CAMERA_FOCUS.y, float(view_case["distance"]))
		runtime.camera.look_at(runtime.CAMERA_FOCUS, Vector3.UP)
		if bool(view_case.get("expression", false)):
			_set_expression_blend_shape(runtime, "笑い", 0.88)
			_set_expression_blend_shape(runtime, "ウィンク右", 0.95)
		await process_frame
		await process_frame
		var image: Image = runtime.avatar_render_viewport.get_texture().get_image()
		var used_rect := image.get_used_rect()
		if used_rect.position.x <= 8 or used_rect.position.y <= 8 \
				or used_rect.end.x >= image.get_width() - 8 \
				or used_rect.end.y >= image.get_height() - 8:
			_fail("Review view reaches the render boundary: %s" % view_case["id"])
			return {}
		var relative_path := PREVIEW_DIR + "/1.2-preview-%s.png" % view_case["id"]
		image.save_png(relative_path)
		output[str(view_case["id"])] = {
			"path": ProjectSettings.globalize_path(relative_path),
			"used_rect": used_rect,
		}
	_reset_expression_blend_shapes(runtime)
	runtime.model.rotation = base_rotation
	runtime.camera.position = Vector3(0.0, runtime.CAMERA_FOCUS.y, base_distance)
	runtime.camera.look_at(runtime.CAMERA_FOCUS, Vector3.UP)
	await process_frame
	await process_frame
	return output


func _reset_expression_blend_shapes(runtime: Node) -> void:
	for blend_index in range(runtime.face_mesh.mesh.get_blend_shape_count()):
		runtime.face_mesh.set_blend_shape_value(blend_index, 0.0)


func _set_expression_blend_shape(runtime: Node, expression_name: String, value: float) -> void:
	if runtime.expression_ids.has(expression_name):
		runtime.face_mesh.set_blend_shape_value(int(runtime.expression_ids[expression_name]), value)


func _benchmark_frame_time(runtime: Node, preview_enabled: bool) -> float:
	runtime.set_model_look_preview(preview_enabled)
	for _warmup in range(8):
		await process_frame
	var started_at := Time.get_ticks_usec()
	for _sample in range(60):
		await process_frame
	return float(Time.get_ticks_usec() - started_at) / 60000.0


func _make_contact_sheet(baseline_source: Image, preview_source: Image) -> Image:
	var used_rect := baseline_source.get_used_rect().merge(preview_source.get_used_rect())
	var full_rect := Rect2i(Vector2i.ZERO, baseline_source.get_size())
	var crop_rect := used_rect.grow(96).intersection(full_rect)
	var baseline := baseline_source.get_region(crop_rect)
	var preview := preview_source.get_region(crop_rect)
	var contact := Image.create(crop_rect.size.x * 2, crop_rect.size.y, false, Image.FORMAT_RGBA8)
	contact.fill(Color(0.055, 0.06, 0.07, 1.0))
	contact.blend_rect(baseline, Rect2i(Vector2i.ZERO, baseline.get_size()), Vector2i.ZERO)
	contact.blend_rect(preview, Rect2i(Vector2i.ZERO, preview.get_size()), Vector2i(crop_rect.size.x, 0))
	return contact


func _fail(message: String) -> void:
	push_error(message)
	quit(1)
