extends SceneTree


const RENDER_SIZE := Vector2i(1920, 2320)
const CONTACT_COLUMNS := 5
const CONTACT_CELL_SIZE := Vector2i(240, 290)
const ACTION_CASES := [
	{"id": "wave", "kind": "procedural", "duration": 2.35, "samples": 25},
	{"id": "greet", "kind": "procedural", "duration": 2.35, "samples": 25},
	{"id": "pirouette", "kind": "authored", "samples": 25},
	{"id": "listen", "kind": "authored", "samples": 25},
]
const ARM_CHAINS := [
	["腕.R", "ひじ.R", "手首.R", "中指先.R"],
	["腕.L", "ひじ.L", "手首.L", "中指先.L"],
]
const DEFORM_LEG_CHAINS := [
	["足D.R", "ひざD.R", "足首D.R", "足先EX.R"],
	["足D.L", "ひざD.L", "足首D.L", "足先EX.L"],
]
const MAX_DEFORM_MIRROR_ORIGIN_ERROR := 0.002
const MAX_DEFORM_MIRROR_ROTATION_ERROR := 0.01


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	if DisplayServer.get_name() == "headless":
		_fail("This verification requires the Windows display driver")
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

	if runtime.avatar_render_viewport == null or runtime.avatar_render_viewport.size != RENDER_SIZE:
		_fail("Large-motion render target is not 1920x2320")
		return
	if not _verify_skin_contract(runtime):
		return

	var action_summaries := {}
	for action_case in ACTION_CASES:
		var summary: Dictionary = await _verify_action(runtime, action_case)
		if summary.is_empty():
			return
		action_summaries[str(action_case["id"])] = summary

	runtime.set_process(false)
	if not await _verify_menu_isolation(runtime):
		return

	print("GODOT_LARGE_MOTION_RENDER_OK", {
		"renderer": RenderingServer.get_video_adapter_api_version(),
		"adapter": RenderingServer.get_video_adapter_name(),
		"render_size": RENDER_SIZE,
		"skin_binds": runtime.face_mesh.skin.get_bind_count(),
		"surfaces": runtime.face_mesh.mesh.get_surface_count(),
		"actions": action_summaries,
		"menu_closed_open_render_identical": true,
		"interaction_panel_clear_of_avatar": true,
	})
	quit(0)


func _verify_skin_contract(runtime: Node) -> bool:
	var mesh_instance: MeshInstance3D = runtime.face_mesh
	if mesh_instance == null or mesh_instance.mesh == null or mesh_instance.skin == null:
		_fail("Runtime skinned mesh was not discovered")
		return false
	if mesh_instance.skin.get_bind_count() != runtime.skeleton.get_bone_count():
		_fail("Skin bind count does not match the runtime skeleton")
		return false
	var mesh: Mesh = mesh_instance.mesh
	for surface_index in range(mesh.get_surface_count()):
		var material := mesh.surface_get_material(surface_index)
		if material is BaseMaterial3D and material.cull_mode != BaseMaterial3D.CULL_DISABLED:
			_fail("Surface %d unexpectedly enables back-face culling" % surface_index)
			return false
	return true


func _verify_action(runtime: Node, action_case: Dictionary) -> Dictionary:
	var action_id := str(action_case["id"])
	var sample_count := int(action_case["samples"])
	var duration := float(action_case.get("duration", 0.0))
	var animation: Animation = null
	if str(action_case["kind"]) == "authored":
		if not runtime.authored_motion_clips.has(action_id):
			_fail("Authored action is unavailable: %s" % action_id)
			return {}
		var clip := StringName(action_id)
		## Exercise the real interaction-menu route. Keyboard shortcuts converge on
		## the same handle_agent_event method, so this covers both user entry paths.
		runtime.interaction_ui._run_action("avatar.%s" % action_id)
		animation = runtime.authored_motion_player.get_animation(clip)
		duration = animation.length

	var contact := Image.create(
		CONTACT_COLUMNS * CONTACT_CELL_SIZE.x,
		ceili(float(sample_count) / CONTACT_COLUMNS) * CONTACT_CELL_SIZE.y,
		false,
		Image.FORMAT_RGBA8
	)
	contact.fill(Color(0.02, 0.02, 0.02, 1.0))
	var minimum_alpha_pixels := 2147483647
	var maximum_alpha_pixels := 0
	var minimum_camera_visibility := 1.0
	var maximum_deform_mirror_origin_error := 0.0
	var maximum_deform_mirror_rotation_error := 0.0
	var union_rect := Rect2i()
	var sample_failures: Array = []
	var verify_deform_mirrors := false
	if animation != null:
		var clip_data: Dictionary = runtime.authored_motion_clips.get(action_id, {})
		verify_deform_mirrors = (
			str(clip_data.get("bone_layer", runtime.MOTION_LAYER_FULL_BODY))
			== runtime.MOTION_LAYER_FULL_BODY
			and bool(clip_data.get("sync_mmd_deform_bones", true))
		)

	for sample_index in range(sample_count):
		var ratio := float(sample_index) / float(sample_count - 1)
		if animation != null:
			runtime.authored_motion_player.seek(duration * ratio, true)
		else:
			runtime.interaction_ui._run_action("avatar.%s" % action_id)
			runtime.action_elapsed = duration * ratio
		await process_frame
		await process_frame

		var image: Image = runtime.avatar_render_viewport.get_texture().get_image()
		if image.is_empty() or image.get_size() != RENDER_SIZE:
			_fail("%s sample %d did not produce the expected render" % [action_id, sample_index])
			return {}
		var used_rect := image.get_used_rect()
		if used_rect.position.x <= 8 or used_rect.position.y <= 8 \
				or used_rect.end.x >= image.get_width() - 8 \
				or used_rect.end.y >= image.get_height() - 8:
			sample_failures.append({"sample": sample_index, "reason": "render_boundary", "rect": used_rect})
		union_rect = used_rect if union_rect.size == Vector2i.ZERO else union_rect.merge(used_rect)

		for chain in ARM_CHAINS:
			for segment_index in range(chain.size() - 1):
				var start_name: String = chain[segment_index]
				var end_name: String = chain[segment_index + 1]
				var start := _project_bone(runtime, start_name)
				var end := _project_bone(runtime, end_name)
				var camera_visibility := _segment_camera_visibility(runtime, start_name, end_name)
				minimum_camera_visibility = minf(minimum_camera_visibility, camera_visibility)
				if camera_visibility < runtime.MIN_LIMB_CAMERA_PLANE_VISIBILITY - 0.02:
					sample_failures.append({
						"sample": sample_index,
						"ratio": ratio,
						"reason": "camera_projection_collapse",
						"segment": "%s>%s" % [start_name, end_name],
						"visibility": camera_visibility,
					})
				var radius := 14.0 if segment_index == chain.size() - 2 else 18.0
				if not _segment_has_continuous_alpha(image, start, end, radius):
					sample_failures.append({
						"sample": sample_index,
						"ratio": ratio,
						"reason": "limb_alpha_gap",
						"segment": "%s>%s" % [start_name, end_name],
					})

		for chain in DEFORM_LEG_CHAINS:
			for segment_index in range(chain.size() - 1):
				var start_name: String = chain[segment_index]
				var end_name: String = chain[segment_index + 1]
				if not _segment_has_continuous_alpha(
					image,
					_project_bone(runtime, start_name),
					_project_bone(runtime, end_name),
					18.0
				):
					sample_failures.append({
						"sample": sample_index,
						"ratio": ratio,
						"reason": "deform_leg_alpha_gap",
						"segment": "%s>%s" % [start_name, end_name],
					})

		if verify_deform_mirrors:
			var mirror_errors := _deform_mirror_errors(runtime)
			maximum_deform_mirror_origin_error = maxf(
				maximum_deform_mirror_origin_error,
				float(mirror_errors["origin"])
			)
			maximum_deform_mirror_rotation_error = maxf(
				maximum_deform_mirror_rotation_error,
				float(mirror_errors["rotation"])
			)
			if float(mirror_errors["origin"]) > MAX_DEFORM_MIRROR_ORIGIN_ERROR \
					or float(mirror_errors["rotation"]) > MAX_DEFORM_MIRROR_ROTATION_ERROR:
				sample_failures.append({
					"sample": sample_index,
					"ratio": ratio,
					"reason": "mmd_deform_chain_desync",
					"origin_error": mirror_errors["origin"],
					"rotation_error": mirror_errors["rotation"],
				})
		var alpha_pixels := _alpha_pixel_count(image)
		minimum_alpha_pixels = mini(minimum_alpha_pixels, alpha_pixels)
		maximum_alpha_pixels = maxi(maximum_alpha_pixels, alpha_pixels)
		var thumb := image.duplicate()
		thumb.resize(CONTACT_CELL_SIZE.x, CONTACT_CELL_SIZE.y, Image.INTERPOLATE_LANCZOS)
		var cell := Vector2i(
			(sample_index % CONTACT_COLUMNS) * CONTACT_CELL_SIZE.x,
			(sample_index / CONTACT_COLUMNS) * CONTACT_CELL_SIZE.y
		)
		contact.blit_rect(thumb, Rect2i(Vector2i.ZERO, CONTACT_CELL_SIZE), cell)

	if animation != null:
		runtime._cancel_authored_motion()
	else:
		runtime.action_name = "idle"
		runtime._restore_bone_poses()
	if not sample_failures.is_empty():
		_fail("%s lost rendered body continuity: %s" % [action_id, sample_failures])
		return {}

	var evidence_path := "user://large-motion-%s-grid.png" % action_id
	contact.save_png(evidence_path)
	return {
		"samples": sample_count,
		"duration": duration,
		"entry_path": "interaction_ui->_run_action->handle_agent_event",
		"minimum_alpha_pixels": minimum_alpha_pixels,
		"maximum_alpha_pixels": maximum_alpha_pixels,
		"minimum_camera_visibility": minimum_camera_visibility,
		"maximum_deform_mirror_origin_error": maximum_deform_mirror_origin_error,
		"maximum_deform_mirror_rotation_error": maximum_deform_mirror_rotation_error,
		"union_rect": union_rect,
		"evidence": ProjectSettings.globalize_path(evidence_path),
	}


func _deform_mirror_errors(runtime: Node) -> Dictionary:
	var maximum_origin_error := 0.0
	var maximum_rotation_error := 0.0
	for mirror in runtime.deform_bone_mirrors:
		var source_index: int = mirror[0]
		var target_index: int = mirror[1]
		var source_base: Transform3D = runtime.deform_mirror_base_global_poses[source_index]
		var target_base: Transform3D = runtime.deform_mirror_base_global_poses[target_index]
		var source_pose: Transform3D = runtime.skeleton.get_bone_global_pose(source_index)
		var target_pose: Transform3D = runtime.skeleton.get_bone_global_pose(target_index)
		maximum_origin_error = maxf(
			maximum_origin_error,
			source_pose.origin.distance_to(target_pose.origin)
		)
		var source_delta := (
			source_pose.basis.orthonormalized()
			* source_base.basis.orthonormalized().inverse()
		).get_rotation_quaternion()
		var target_delta := (
			target_pose.basis.orthonormalized()
			* target_base.basis.orthonormalized().inverse()
		).get_rotation_quaternion()
		maximum_rotation_error = maxf(
			maximum_rotation_error,
			source_delta.angle_to(target_delta)
		)
	return {"origin": maximum_origin_error, "rotation": maximum_rotation_error}


func _verify_menu_isolation(runtime: Node) -> bool:
	runtime._start_action("greet", 2.35)
	runtime.action_elapsed = 1.175
	runtime._apply_action_pose()
	await process_frame
	await process_frame
	var closed: Image = runtime.avatar_render_viewport.get_texture().get_image()
	var closed_alpha_pixels := _alpha_pixel_count(closed)
	var closed_rect := closed.get_used_rect()

	runtime.interaction_ui._open_interaction()
	runtime._sync_interaction_ui_origin()
	await process_frame
	var opened: Image = runtime.avatar_render_viewport.get_texture().get_image()
	var opened_alpha_pixels := _alpha_pixel_count(opened)
	if absf(float(opened_alpha_pixels - closed_alpha_pixels)) / maxf(float(closed_alpha_pixels), 1.0) > 0.005 \
			or opened.get_used_rect() != closed_rect:
		_fail("Opening interaction UI changed the isolated avatar render")
		return false
	var panel_rect: Rect2 = runtime.interaction_ui.get_visible_interaction_rect()
	var avatar_rect := _polygon_rect(runtime._avatar_interaction_polygon())
	if panel_rect.intersects(avatar_rect):
		_fail("Interaction panel covers the avatar: panel=%s avatar=%s" % [panel_rect, avatar_rect])
		return false
	return true


func _project_bone(runtime: Node, bone_name: String) -> Vector2:
	var bone_index: int = runtime.skeleton.find_bone(bone_name)
	if bone_index < 0:
		return Vector2(-1000.0, -1000.0)
	var pose: Transform3D = runtime.skeleton.get_bone_global_pose(bone_index)
	var world_position: Vector3 = runtime.skeleton.global_transform * pose.origin
	return runtime.camera.unproject_position(world_position)


func _segment_camera_visibility(runtime: Node, start_name: String, end_name: String) -> float:
	var start_index: int = runtime.skeleton.find_bone(start_name)
	var end_index: int = runtime.skeleton.find_bone(end_name)
	if start_index < 0 or end_index < 0:
		return 0.0
	var start_pose: Transform3D = runtime.skeleton.get_bone_global_pose(start_index)
	var end_pose: Transform3D = runtime.skeleton.get_bone_global_pose(end_index)
	var direction: Vector3 = runtime.skeleton.global_transform.basis * (end_pose.origin - start_pose.origin)
	if direction.length_squared() < 0.000001:
		return 0.0
	direction = direction.normalized()
	var camera_forward: Vector3 = -runtime.camera.global_transform.basis.z.normalized()
	return sqrt(maxf(0.0, 1.0 - pow(absf(direction.dot(camera_forward)), 2.0)))


func _segment_has_continuous_alpha(image: Image, start: Vector2, end: Vector2, radius: float) -> bool:
	for sample_index in range(17):
		var point := start.lerp(end, float(sample_index) / 16.0)
		var covered := false
		for y in range(floori(point.y - radius), ceili(point.y + radius) + 1):
			if y < 0 or y >= image.get_height():
				continue
			for x in range(floori(point.x - radius), ceili(point.x + radius) + 1):
				if x < 0 or x >= image.get_width():
					continue
				if Vector2(x, y).distance_squared_to(point) <= radius * radius and image.get_pixel(x, y).a > 0.2:
					covered = true
					break
			if covered:
				break
		if not covered:
			return false
	return true


func _polygon_rect(points: PackedVector2Array) -> Rect2:
	if points.is_empty():
		return Rect2()
	var minimum := points[0]
	var maximum := points[0]
	for point in points:
		minimum = minimum.min(point)
		maximum = maximum.max(point)
	return Rect2(minimum, maximum - minimum)


func _alpha_pixel_count(image: Image) -> int:
	var count := 0
	var used_rect := image.get_used_rect()
	for y in range(used_rect.position.y, used_rect.end.y):
		for x in range(used_rect.position.x, used_rect.end.x):
			if image.get_pixel(x, y).a > 0.2:
				count += 1
	return count


func _fail(message: String) -> void:
	push_error(message)
	quit(1)
