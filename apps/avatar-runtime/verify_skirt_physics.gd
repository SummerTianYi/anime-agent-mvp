extends SceneTree


const OFFICIAL_MODEL_PATH := "res://assets/luotianyi_v4.glb"
const OFFICIAL_MODEL_SHA256 := "df55806d343d149b41c20d0ef074373cafca2379212fd8691e998ea6cddc6e4a"
const DEFAULT_TEST_FPS := 60
const EVIDENCE_COLUMNS := 5
const EVIDENCE_CELL_SIZE := Vector2i(384, 464)
const CONTACT_CELL_SIZE := Vector2i(384, 384)
## Bone origins sit inside the cloth volume, so this is only an explosion/
## inversion guard. Actual visible cloth contact uses skinned vertices below.
const CONTACT_TOLERANCE := 0.13
const GEOMETRY_CONTACT_TOLERANCE := 0.003
const MAX_SKIRT_SEGMENT_LENGTH_RATIO := 1.08
const CASES := [
	{"id": "idle", "sample_count": 49},
	{"id": "pirouette", "sample_count": 49},
]

var monitored_runtime: Node
var monitored_rest_lengths: Dictionary = {}
var latest_clearance := {}
var latest_terminal_clearance := {}
var latest_segment_ratio := 0.0
var modifier_samples := 0
var skirt_vertices: Array = []
var geometry_probe_requested := false
var latest_geometry_contact := {}
var test_fps := DEFAULT_TEST_FPS


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var requested_fps := OS.get_environment("ANIME_AGENT_SKIRT_TEST_FPS").to_int()
	if requested_fps > 0:
		test_fps = requested_fps
	if DisplayServer.get_name() == "headless":
		_fail("Skirt verification requires a rendering display driver")
		return
	if FileAccess.get_sha256(OFFICIAL_MODEL_PATH).to_lower() != OFFICIAL_MODEL_SHA256:
		_fail("Official model hash changed")
		return
	var scene := load("res://main.tscn") as PackedScene
	if scene == null:
		_fail("Unable to load main scene")
		return
	var runtime: Node = scene.instantiate()
	root.add_child(runtime)
	await process_frame
	await process_frame
	if not _verify_runtime_contract(runtime):
		return
	_apply_tuning_overrides(runtime)
	skirt_vertices = _cache_skirt_vertices(runtime)
	if skirt_vertices.size() < 100:
		_fail("Unable to recover enough weighted skirt vertices for geometry checks: %d" % skirt_vertices.size())
		return

	var rest_lengths := _skirt_rest_segment_lengths(runtime)
	monitored_runtime = runtime
	monitored_rest_lengths = rest_lengths
	runtime.skirt_simulator.modification_processed.connect(_on_skirt_modified)
	var summaries := {}
	var requested_case := OS.get_environment("ANIME_AGENT_SKIRT_TEST_CASE").strip_edges()
	for case_data in CASES:
		if not requested_case.is_empty() and str(case_data["id"]) != requested_case:
			continue
		var summary: Dictionary = await _verify_case(runtime, case_data, rest_lengths)
		if summary.is_empty():
			return
		summaries[str(case_data["id"])] = summary
		print("GODOT_SKIRT_CASE_OK", case_data["id"], summary)

	print("GODOT_SKIRT_PHYSICS_OK", {
		"fixed_fps": test_fps,
		"official_model_sha256": OFFICIAL_MODEL_SHA256,
		"model_structure_untouched": true,
		"runtime": runtime._skirt_physics_summary(),
		"cases": summaries,
	})
	quit(0)


func _verify_runtime_contract(runtime: Node) -> bool:
	if not runtime.skirt_physics_enabled or runtime.skirt_simulator == null:
		_fail("Runtime skirt physics is not enabled")
		return false
	if runtime.skirt_chains.size() != runtime.SKIRT_CHAIN_COUNT:
		_fail("Expected %d skirt chains, found %d" % [runtime.SKIRT_CHAIN_COUNT, runtime.skirt_chains.size()])
		return false
	if runtime.skirt_simulator.get_setting_count() != runtime.SKIRT_CHAIN_COUNT:
		_fail("Spring setting count does not match skirt chain count")
		return false
	if runtime.skirt_colliders.size() < 20:
		_fail("Skirt collider rig is incomplete")
		return false
	for chain in runtime.skirt_chains:
		if chain.size() != runtime.SKIRT_CHAIN_LENGTH:
			_fail("Skirt chain is incomplete: %s" % [chain])
			return false
	for setting_index in range(runtime.SKIRT_CHAIN_COUNT):
		if runtime.skirt_simulator.get_collision_count(setting_index) != runtime.skirt_colliders.size():
			_fail(
				"Skirt setting %d registered %d/%d colliders"
				% [
					setting_index,
					runtime.skirt_simulator.get_collision_count(setting_index),
					runtime.skirt_colliders.size(),
				]
			)
			return false
	return true


func _apply_tuning_overrides(runtime: Node) -> void:
	var stiffness := OS.get_environment("ANIME_AGENT_SKIRT_TEST_STIFFNESS").to_float()
	var drag := OS.get_environment("ANIME_AGENT_SKIRT_TEST_DRAG").to_float()
	var gravity := OS.get_environment("ANIME_AGENT_SKIRT_TEST_GRAVITY").to_float()
	var radius := OS.get_environment("ANIME_AGENT_SKIRT_TEST_RADIUS").to_float()
	for setting_index in range(runtime.SKIRT_CHAIN_COUNT):
		if stiffness > 0.0:
			runtime.skirt_simulator.set_stiffness(setting_index, stiffness)
		if drag > 0.0:
			runtime.skirt_simulator.set_drag(setting_index, drag)
		if gravity > 0.0:
			runtime.skirt_simulator.set_gravity(setting_index, gravity)
		if radius > 0.0:
			runtime.skirt_simulator.set_radius(setting_index, radius)
	if stiffness > 0.0 or drag > 0.0 or gravity > 0.0 or radius > 0.0:
		runtime.skirt_simulator.reset()
		print("GODOT_SKIRT_TEST_TUNING", {
			"stiffness": stiffness,
			"drag": drag,
			"gravity": gravity,
			"radius": radius,
		})


func _verify_case(runtime: Node, case_data: Dictionary, rest_lengths: Dictionary) -> Dictionary:
	var case_id := str(case_data["id"])
	if not runtime.authored_motion_clips.has(case_id):
		_fail("Authored skirt test action is unavailable: %s" % case_id)
		return {}
	if runtime.authored_motion_active:
		runtime._cancel_authored_motion(false)
	runtime._play_authored_motion(StringName(case_id))
	var animation: Animation = runtime.authored_motion_player.get_animation(StringName(case_id))
	var total_frames := ceili(animation.length * test_fps) + 2
	var requested_samples := int(case_data["sample_count"])
	var sample_frames: Dictionary = {}
	for sample_index in range(requested_samples):
		var frame := roundi(float(total_frames - 1) * float(sample_index) / float(requested_samples - 1))
		sample_frames[frame] = sample_index

	var evidence := _create_grid(requested_samples, EVIDENCE_CELL_SIZE)
	var contact_evidence := _create_grid(requested_samples, CONTACT_CELL_SIZE)
	var minimum_clearance := INF
	var minimum_contact := {}
	var minimum_terminal_clearance := INF
	var minimum_terminal_contact := {}
	var worst_image: Image
	var geometry_worst_image: Image
	var maximum_segment_ratio := 0.0
	var invalid_pose_count := 0
	var penetration_frames := 0
	var geometry_penetration_samples := 0
	var geometry_failures: Array = []
	var minimum_geometry_clearance := INF
	var minimum_geometry_contact := {}
	var captured_samples := 0
	modifier_samples = 0
	for frame in range(total_frames):
		geometry_probe_requested = sample_frames.has(frame)
		await process_frame
		var contact: Dictionary = latest_clearance.duplicate(true)
		var terminal_contact: Dictionary = latest_terminal_clearance.duplicate(true)
		var clearance := float(contact.get("clearance", INF))
		var terminal_clearance := float(terminal_contact.get("clearance", INF))
		if clearance < minimum_clearance:
			minimum_clearance = clearance
			minimum_contact = contact.merged({"frame": frame, "second": float(frame) / test_fps}, true)
			worst_image = runtime.avatar_render_viewport.get_texture().get_image()
		if terminal_clearance < minimum_terminal_clearance:
			minimum_terminal_clearance = terminal_clearance
			minimum_terminal_contact = terminal_contact.merged({"frame": frame, "second": float(frame) / test_fps}, true)
		if clearance < -CONTACT_TOLERANCE:
			penetration_frames += 1
		var segment_ratio := latest_segment_ratio
		maximum_segment_ratio = maxf(maximum_segment_ratio, segment_ratio)
		if not is_finite(clearance) or not is_finite(segment_ratio):
			invalid_pose_count += 1
		if sample_frames.has(frame):
			var geometry_contact: Dictionary = latest_geometry_contact.duplicate(true)
			var geometry_clearance := float(geometry_contact.get("clearance", INF))
			var geometry_is_new_worst := geometry_clearance < minimum_geometry_clearance
			if geometry_clearance < minimum_geometry_clearance:
				minimum_geometry_clearance = geometry_clearance
				minimum_geometry_contact = geometry_contact.merged({"frame": frame, "second": float(frame) / test_fps}, true)
			if geometry_clearance < -GEOMETRY_CONTACT_TOLERANCE:
				geometry_penetration_samples += 1
				geometry_failures.append(
					geometry_contact.merged({"frame": frame, "second": float(frame) / test_fps}, true)
				)
			var image: Image = runtime.avatar_render_viewport.get_texture().get_image()
			if image.is_empty():
				_fail("%s frame %d produced an empty render" % [case_id, frame])
				return {}
			if geometry_is_new_worst:
				geometry_worst_image = image.duplicate()
			var sample_index := int(sample_frames[frame])
			_blit_normalized(image, evidence, sample_index, EVIDENCE_CELL_SIZE, false, runtime)
			_blit_normalized(image, contact_evidence, sample_index, CONTACT_CELL_SIZE, true, runtime)
			captured_samples += 1

	var evidence_path := "user://skirt-%s-full-grid.png" % case_id
	var contact_path := "user://skirt-%s-contact-grid.png" % case_id
	var worst_path := "user://skirt-%s-worst.png" % case_id
	var geometry_worst_path := "user://skirt-%s-geometry-worst.png" % case_id
	evidence.save_png(evidence_path)
	contact_evidence.save_png(contact_path)
	if worst_image != null and not worst_image.is_empty():
		worst_image.save_png(worst_path)
	if geometry_worst_image != null and not geometry_worst_image.is_empty():
		geometry_worst_image.save_png(geometry_worst_path)
	runtime._cancel_authored_motion(false)
	if invalid_pose_count > 0:
		_fail("%s generated %d invalid skirt poses" % [case_id, invalid_pose_count])
		return {}
	if modifier_samples < total_frames:
		_fail("%s only observed %d/%d post-modifier samples" % [case_id, modifier_samples, total_frames])
		return {}
	if penetration_frames > 0:
		_fail(
			"%s penetrated runtime colliders on %d frames; worst=%s"
			% [case_id, penetration_frames, minimum_contact]
		)
		return {}
	if geometry_penetration_samples > 0:
		_fail(
			"%s visibly weighted skirt geometry penetrated limb proxies on %d/%d samples; worst=%s"
			% [case_id, geometry_penetration_samples, captured_samples, geometry_failures]
		)
		return {}
	if maximum_segment_ratio > MAX_SKIRT_SEGMENT_LENGTH_RATIO:
		_fail(
			"%s stretched a skirt segment beyond %.2fx rest length: %.5f"
			% [case_id, MAX_SKIRT_SEGMENT_LENGTH_RATIO, maximum_segment_ratio]
		)
		return {}
	return {
		"duration": animation.length,
		"frames": total_frames,
		"captured_samples": captured_samples,
		"minimum_collider_clearance": minimum_clearance,
		"minimum_contact": minimum_contact,
		"minimum_terminal_clearance": minimum_terminal_clearance,
		"minimum_terminal_contact": minimum_terminal_contact,
		"penetration_frames": penetration_frames,
		"minimum_geometry_clearance": minimum_geometry_clearance,
		"minimum_geometry_contact": minimum_geometry_contact,
		"geometry_penetration_samples": geometry_penetration_samples,
		"weighted_skirt_vertices": skirt_vertices.size(),
		"maximum_segment_length_ratio": maximum_segment_ratio,
		"full_evidence": ProjectSettings.globalize_path(evidence_path),
		"contact_evidence": ProjectSettings.globalize_path(contact_path),
		"worst_evidence": ProjectSettings.globalize_path(worst_path),
		"geometry_worst_evidence": ProjectSettings.globalize_path(geometry_worst_path),
	}


func _minimum_skirt_clearance(runtime: Node, terminal_only: bool = false) -> Dictionary:
	var best := {"clearance": INF}
	for chain_index in range(runtime.skirt_chains.size()):
		var chain: Array = runtime.skirt_chains[chain_index]
		## Skirt_0 is fixed at the waist, Skirt_1 carries mesh weights, and
		## Skirt_2 is a zero-weight terminal guide. Keep the two diagnostics
		## separate so an invisible guide cannot create a false visual failure.
		var joint_indices := [chain.size() - 1] if terminal_only else [1]
		for joint_index in joint_indices:
			var skirt_bone: int = chain[joint_index]
			var skirt_origin: Vector3 = runtime.skeleton.get_bone_global_pose(skirt_bone).origin
			for collider: SpringBoneCollisionSphere3D in runtime.skirt_colliders:
				var collider_bone: int = collider.get_bone()
				var collider_pose: Transform3D = runtime.skeleton.get_bone_global_pose(collider_bone)
				var collider_origin: Vector3 = collider_pose.origin + collider_pose.basis.orthonormalized() * collider.position_offset
				var clearance: float = skirt_origin.distance_to(collider_origin) \
					- (runtime.SKIRT_JOINT_RADIUS + collider.radius)
				if clearance < float(best["clearance"]):
					best = {
						"clearance": clearance,
						"chain": chain_index,
						"joint": joint_index,
						"skirt_bone": runtime.skeleton.get_bone_name(skirt_bone),
						"collider": collider.name,
						"collider_bone": runtime.skeleton.get_bone_name(collider_bone),
					}
	return best


func _on_skirt_modified() -> void:
	if monitored_runtime == null:
		return
	latest_clearance = _minimum_skirt_clearance(monitored_runtime)
	latest_terminal_clearance = _minimum_skirt_clearance(monitored_runtime, true)
	if geometry_probe_requested:
		latest_geometry_contact = _minimum_skirt_geometry_clearance(monitored_runtime)
		geometry_probe_requested = false
	latest_segment_ratio = _maximum_skirt_segment_ratio(monitored_runtime, monitored_rest_lengths)
	modifier_samples += 1


func _cache_skirt_vertices(runtime: Node) -> Array:
	var skirt_bones := {}
	for chain in runtime.skirt_chains:
		for bone_index in chain:
			skirt_bones[int(bone_index)] = true
	var cached: Array = []
	var mesh: Mesh = runtime.face_mesh.mesh
	var skin: Skin = runtime.face_mesh.skin
	for surface_index in range(mesh.get_surface_count()):
		var arrays: Array = mesh.surface_get_arrays(surface_index)
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var bones: PackedInt32Array = arrays[Mesh.ARRAY_BONES]
		var weights: PackedFloat32Array = arrays[Mesh.ARRAY_WEIGHTS]
		if vertices.is_empty() or bones.is_empty() or weights.is_empty():
			continue
		var influence_count := 8 if mesh.surface_get_format(surface_index) & Mesh.ARRAY_FLAG_USE_8_BONE_WEIGHTS else 4
		for vertex_index in range(vertices.size()):
			var influences: Array = []
			var skirt_weight := 0.0
			for influence_index in range(influence_count):
				var flat_index := vertex_index * influence_count + influence_index
				var weight := float(weights[flat_index])
				if weight <= 0.00001:
					continue
				var bind_index := int(bones[flat_index])
				var skeleton_bone := _bind_bone_index(runtime, skin, bind_index)
				influences.append([bind_index, weight])
				if skirt_bones.has(skeleton_bone):
					skirt_weight += weight
			if skirt_weight >= 0.5:
				cached.append({
					"vertex": vertices[vertex_index],
					"surface": surface_index,
					"index": vertex_index,
					"influences": influences,
				})
	return cached


func _minimum_skirt_geometry_clearance(runtime: Node) -> Dictionary:
	var best := {"clearance": INF}
	var skin: Skin = runtime.face_mesh.skin
	for record: Dictionary in skirt_vertices:
		var source: Vector3 = record["vertex"]
		var deformed := Vector3.ZERO
		var total_weight := 0.0
		for influence: Array in record["influences"]:
			var bind_index := int(influence[0])
			var weight := float(influence[1])
			var bone_index := _bind_bone_index(runtime, skin, bind_index)
			if bone_index < 0:
				continue
			var skin_transform: Transform3D = (
				runtime.skeleton.get_bone_global_pose(bone_index)
				* skin.get_bind_pose(bind_index)
			)
			deformed += (skin_transform * source) * weight
			total_weight += weight
		if total_weight <= 0.00001:
			continue
		deformed /= total_weight
		for collider: SpringBoneCollisionSphere3D in runtime.skirt_colliders:
			var collider_bone: int = collider.get_bone()
			var collider_pose: Transform3D = runtime.skeleton.get_bone_global_pose(collider_bone)
			var collider_origin: Vector3 = collider_pose.origin + collider_pose.basis.orthonormalized() * collider.position_offset
			var clearance := deformed.distance_to(collider_origin) - collider.radius
			if clearance < float(best["clearance"]):
				var influence_names: Array[String] = []
				for influence: Array in record["influences"]:
					var influence_bone := _bind_bone_index(runtime, skin, int(influence[0]))
					influence_names.append(
						"%s:%.4f"
						% [runtime.skeleton.get_bone_name(influence_bone), float(influence[1])]
					)
				best = {
					"clearance": clearance,
					"surface": record["surface"],
					"surface_name": runtime.face_mesh.mesh.surface_get_name(int(record["surface"])),
					"vertex": record["index"],
					"source": source,
					"deformed": deformed,
					"collider_origin": collider_origin,
					"collider_radius": collider.radius,
					"influences": influence_names,
					"collider": collider.name,
					"collider_bone": runtime.skeleton.get_bone_name(collider_bone),
				}
	return best


func _bind_bone_index(runtime: Node, skin: Skin, bind_index: int) -> int:
	var bone_index := skin.get_bind_bone(bind_index)
	if bone_index >= 0:
		return bone_index
	var bind_name := skin.get_bind_name(bind_index)
	return runtime.skeleton.find_bone(String(bind_name)) if not bind_name.is_empty() else -1


func _skirt_rest_segment_lengths(runtime: Node) -> Dictionary:
	var lengths := {}
	for chain_index in range(runtime.skirt_chains.size()):
		var chain: Array = runtime.skirt_chains[chain_index]
		for segment_index in range(chain.size() - 1):
			var start: Vector3 = runtime.skeleton.get_bone_global_rest(int(chain[segment_index])).origin
			var finish: Vector3 = runtime.skeleton.get_bone_global_rest(int(chain[segment_index + 1])).origin
			lengths["%d:%d" % [chain_index, segment_index]] = start.distance_to(finish)
	return lengths


func _maximum_skirt_segment_ratio(runtime: Node, rest_lengths: Dictionary) -> float:
	var maximum := 0.0
	for chain_index in range(runtime.skirt_chains.size()):
		var chain: Array = runtime.skirt_chains[chain_index]
		for segment_index in range(chain.size() - 1):
			var start: Vector3 = runtime.skeleton.get_bone_global_pose(int(chain[segment_index])).origin
			var finish: Vector3 = runtime.skeleton.get_bone_global_pose(int(chain[segment_index + 1])).origin
			var rest_length := float(rest_lengths["%d:%d" % [chain_index, segment_index]])
			maximum = maxf(maximum, start.distance_to(finish) / maxf(rest_length, 0.000001))
	return maximum


func _create_grid(sample_count: int, cell_size: Vector2i) -> Image:
	var rows := ceili(float(sample_count) / EVIDENCE_COLUMNS)
	var image := Image.create(EVIDENCE_COLUMNS * cell_size.x, rows * cell_size.y, false, Image.FORMAT_RGBA8)
	image.fill(Color(0.02, 0.02, 0.02, 1.0))
	return image


func _blit_normalized(
	source: Image,
	target: Image,
	sample_index: int,
	cell_size: Vector2i,
	contact_only: bool,
	runtime: Node,
) -> void:
	var crop_rect := _contact_crop_rect(runtime, source.get_size()) if contact_only else source.get_used_rect()
	if crop_rect.size == Vector2i.ZERO:
		return
	var crop := source.get_region(crop_rect)
	crop.resize(cell_size.x, cell_size.y, Image.INTERPOLATE_LANCZOS)
	var cell := Vector2i(
		(sample_index % EVIDENCE_COLUMNS) * cell_size.x,
		(sample_index / EVIDENCE_COLUMNS) * cell_size.y
	)
	target.blit_rect(crop, Rect2i(Vector2i.ZERO, cell_size), cell)


func _contact_crop_rect(runtime: Node, image_size: Vector2i) -> Rect2i:
	var hip := _project_bone(runtime, "下半身")
	var left_knee := _project_bone(runtime, "ひざD.L")
	var right_knee := _project_bone(runtime, "ひざD.R")
	var minimum := hip.min(left_knee).min(right_knee) - Vector2(260.0, 180.0)
	var maximum := hip.max(left_knee).max(right_knee) + Vector2(260.0, 180.0)
	var rect := Rect2i(Vector2i(floori(minimum.x), floori(minimum.y)), Vector2i(ceili(maximum.x - minimum.x), ceili(maximum.y - minimum.y)))
	return rect.intersection(Rect2i(Vector2i.ZERO, image_size))


func _project_bone(runtime: Node, bone_name: String) -> Vector2:
	var bone_index: int = runtime.skeleton.find_bone(bone_name)
	if bone_index < 0:
		return Vector2.ZERO
	var pose: Transform3D = runtime.skeleton.get_bone_global_pose(bone_index)
	return runtime.camera.unproject_position(runtime.skeleton.global_transform * pose.origin)


func _fail(message: String) -> void:
	push_error(message)
	quit(1)
