extends SceneTree
## Codex: offline-only structural test, saved Animation replay and GPU evidence.
const Review = preload("res://lookdev/render_candidate.gd")
const Pose = preload("res://mocap/farewell/pose.gd")
var runtime: Node
var pose: RefCounted
var viewport: SubViewport
var failures: Array[String] = []
var output: String
var report := {"agent": "Codex", "preview_only": true, "checks": 0}
const FRAME_COUNT := 124

func _init() -> void:
	call_deferred("_run")

func check(ok: bool, message: String) -> void:
	report.checks += 1
	if not ok and not failures.has(message):
		failures.append(message)

func rotation_error(a: Quaternion, b: Quaternion) -> float:
	a = a.normalized()
	b = b.normalized()
	if a.dot(b) < 0:
		a = -a
	return Vector4(a.x - b.x, a.y - b.y, a.z - b.z, a.w - b.w).length()

func verify() -> void:
	var rig: Skeleton3D = runtime.skeleton
	check(FileAccess.get_sha256("res://assets/luotianyi_v4.glb") == Review.SHA, "official asset hash")
	check(rig.get_bone_count() == 703 and runtime.face_mesh.mesh.get_blend_shape_count() == 48, "703 bones / 48 morphs")
	check(runtime.pigtail_chains.size() == 2 and runtime.pigtail_chains[0].size() == 17 and runtime.pigtail_chains[1].size() == 17, "two complete braids")
	for name in Pose.FACE_PEAK:
		check(runtime.expression_ids.has(name), "official expression exists: " + name)
	pose.apply(0.0)
	var head_index := rig.find_bone("頭")
	var head_start := rig.get_bone_global_pose(head_index).basis.get_rotation_quaternion()
	pose.apply(2.0)
	check(pose.open_fingers_unchanged(), "open five fingers")
	var middle := rig.find_bone("中指１.R")
	rig.set_bone_pose_rotation(middle, rig.get_bone_pose_rotation(middle) * Quaternion(Vector3.RIGHT, 0.5))
	check(not pose.open_fingers_unchanged(), "negative control rejects a curled finger")
	pose.apply(1.0)
	var fixed_pose: Dictionary = pose.snapshot()
	var elbow_anchor: Vector3 = pose.point("ひじ.R")
	check(locked_except_elbow(fixed_pose), "raised arm reference")
	pose.rotate_global("腕.R", Basis(Vector3(0, 0, 1), deg_to_rad(4)))
	check(not locked_except_elbow(fixed_pose), "negative control rejects upper-arm waving")
	pose.apply(1.0)
	pose.rotate_global("手首.R", Basis(Vector3(0, 0, 1), deg_to_rad(4)))
	check(not locked_except_elbow(fixed_pose), "negative control rejects wrist waving")
	var previous := {}
	var max_step := 0.0
	var max_elbow := 0.0
	var max_wrist := 0.0
	var max_off_axis := 0.0
	var min_palm_forward := 1.0
	var max_elbow_drift := 0.0
	var max_locked_error := 0.0
	var wrist_left := INF
	var wrist_right := -INF
	var samples := []
	var max_head_angle := 0.0
	for f in range(493):
		var t := float(f) / 120.0
		pose.apply(t)
		for i in rig.get_bone_count():
			var before: Transform3D = pose.baseline[i]
			var now := rig.get_bone_pose(i)
			check(now.is_finite(), "finite transforms")
			check(now.origin.distance_to(before.origin) < 0.00001, "bone translations unchanged")
			check(now.basis.get_scale().distance_to(before.basis.get_scale()) < 0.00001, "bone scales unchanged")
			if not pose.controlled.has(i):
				check(now.is_equal_approx(before), "left arm / torso / legs / hair local poses unchanged")
			if f in [0, 492]:
				check(now.is_equal_approx(before), "exact A-pose endpoints")
		check(pose.open_fingers_unchanged(), "five fingers never curl")
		var head_now := rig.get_bone_global_pose(head_index).basis.get_rotation_quaternion()
		max_head_angle = maxf(max_head_angle, 4.0 * asin(minf(1.0, rotation_error(head_start, head_now) / 2.0)))
		var face: Dictionary = pose.expression_weights(t)
		for name in face:
			check(is_finite(face[name]) and face[name] >= 0.0 and face[name] <= 1.0, "bounded expression weights")
			if f in [0, 492]:
				check(is_zero_approx(face[name]), "neutral face endpoints")
		if t >= 1.0 and t <= 3.16:
			check(is_equal_approx(face["笑い"], 1.0) and is_equal_approx(face["にやり"], 0.65), "closed smiling eyes and smile throughout waving")
		for i in pose.controlled:
			var q := rig.get_bone_pose_rotation(i)
			if previous.has(i):
				max_step = maxf(max_step, 4.0 * asin(minf(1.0, rotation_error(previous[i], q) / 2.0)))
			previous[i] = q
		var shoulder: Vector3 = pose.point("腕.R")
		var elbow: Vector3 = pose.point("ひじ.R")
		var wrist: Vector3 = pose.point("手首.R")
		var index: Vector3 = pose.point("人指１.R") - wrist
		var little: Vector3 = pose.point("小指１.R") - wrist
		max_elbow = maxf(max_elbow, (elbow - shoulder).angle_to(wrist - elbow))
		max_wrist = maxf(max_wrist, (wrist - elbow).angle_to((index + little) * 0.5))
		var e := rig.find_bone("ひじ.R")
		var original: Transform3D = pose.baseline[e]
		var relative := original.basis.get_rotation_quaternion().inverse() * rig.get_bone_pose_rotation(e)
		var v := Vector3(relative.x, relative.y, relative.z)
		var axis: Vector3 = pose.hinges.R
		max_off_axis = maxf(max_off_axis, (v - axis * v.dot(axis)).length())
		if t >= 1.0 and t <= 3.16:
			min_palm_forward = minf(min_palm_forward, index.cross(little).normalized().z)
			max_elbow_drift = maxf(max_elbow_drift, elbow.distance_to(elbow_anchor))
			max_locked_error = maxf(max_locked_error, locked_error(fixed_pose))
			wrist_left = minf(wrist_left, wrist.x)
			wrist_right = maxf(wrist_right, wrist.x)
		if f % 60 == 0:
			samples.append({"t": t, "shoulder": str(shoulder), "elbow": str(elbow), "wrist": str(wrist)})
	check(max_step < deg_to_rad(3.0), "no sudden rotation jumps at 120 Hz")
	check(max_elbow < deg_to_rad(146), "elbow flex under 146 degrees")
	check(max_wrist < deg_to_rad(45), "wrist bend under 45 degrees")
	check(max_off_axis < 0.001, "elbow fixed anatomical hinge")
	check(min_palm_forward > 0.98, "palm faces forward during all waving")
	check(max_elbow_drift < 0.00001, "upper arm fixed: elbow pivot stationary")
	check(max_locked_error < 0.00001, "only elbow local rotation changes during waving")
	check(wrist_right - wrist_left > 0.12, "visible forearm side-to-side arc greater than 12cm")
	check(max_head_angle > deg_to_rad(2.0) and max_head_angle < deg_to_rad(4.0), "head visibly but subtly moves within four degrees")
	report["max_head_global_angle_deg"] = rad_to_deg(max_head_angle)
	report.merge({"samples_120hz": 493, "controlled_bones": pose.controlled.size(),
		"max_step_deg": rad_to_deg(max_step), "max_elbow_deg": rad_to_deg(max_elbow),
		"max_wrist_deg": rad_to_deg(max_wrist), "max_elbow_off_axis": max_off_axis,
		"min_palm_forward_dot": min_palm_forward, "max_elbow_pivot_drift_m": max_elbow_drift,
		"max_locked_bone_quaternion_error": max_locked_error,
		"wave_wrist_horizontal_span_m": wrist_right - wrist_left, "samples": samples})

func locked_error(reference: Dictionary) -> float:
	var maximum := 0.0
	var elbow: int = runtime.skeleton.find_bone("ひじ.R")
	for i in pose.arm_controlled:
		if i != elbow:
			maximum = maxf(maximum, rotation_error(reference[i], runtime.skeleton.get_bone_pose_rotation(i)))
	return maximum

func locked_except_elbow(reference: Dictionary) -> bool:
	return locked_error(reference) < 0.00001

func bake_and_replay() -> void:
	var clip := Animation.new()
	clip.resource_name = "farewell_right_open_hand_preview_Codex"
	clip.length = Pose.LENGTH
	for i in pose.controlled:
		var track := clip.add_track(Animation.TYPE_ROTATION_3D)
		clip.track_set_path(track, NodePath("%s:%s" % [runtime.get_path_to(runtime.skeleton), runtime.skeleton.get_bone_name(i)]))
	var face_tracks := {}
	for name in Pose.FACE_PEAK:
		var track := clip.add_track(Animation.TYPE_BLEND_SHAPE)
		clip.track_set_path(track, NodePath("%s:%s" % [runtime.get_path_to(runtime.face_mesh), name]))
		face_tracks[name] = track
	for f in range(FRAME_COUNT):
		var t := float(f) / 30.0
		pose.apply(t)
		for track in pose.controlled.size():
			clip.rotation_track_insert_key(track, t, runtime.skeleton.get_bone_pose_rotation(pose.controlled[track]))
		var weights: Dictionary = pose.expression_weights(t)
		for name in face_tracks:
			clip.blend_shape_track_insert_key(face_tracks[name], t, weights[name])
	# Phase boundary is not on the 30 Hz grid. Preserve it explicitly so the
	# lowered-arm interpolation cannot leak backward into the fixed-arm hold.
	for t in [3.16, 3.85]:
		pose.apply(t)
		for track in pose.controlled.size():
			clip.rotation_track_insert_key(track, t, runtime.skeleton.get_bone_pose_rotation(pose.controlled[track]))
		var weights: Dictionary = pose.expression_weights(t)
		for name in face_tracks:
			clip.blend_shape_track_insert_key(face_tracks[name], t, weights[name])
	check(ResourceSaver.save(clip, output + "/farewell_preview.tres") == OK, "save local candidate")
	var replay: Animation = load(output + "/farewell_preview.tres")
	check(replay != null and replay.get_track_count() == pose.controlled.size() + face_tracks.size(), "reload body and expression candidate")
	if replay == null:
		return
	runtime.authored_motion_player.get_animation_library(&"").add_animation(&"_farewell_preview", replay)
	runtime.authored_motion_player.play(&"_farewell_preview")
	runtime.authored_motion_player.advance(0.0)
	runtime.authored_motion_player.pause()
	pose.apply(1.0)
	var locked_reference: Dictionary = pose.snapshot()
	var elbow_anchor: Vector3 = pose.point("ひじ.R")
	var max_error := 0.0
	var max_face_error := 0.0
	for f in range(FRAME_COUNT):
		var t := float(f) / 30.0
		pose.apply(t)
		var expected: Dictionary = pose.snapshot()
		pose.reset()
		runtime.authored_motion_player.seek(t, true)
		for i in expected:
			max_error = maxf(max_error, rotation_error(expected[i], runtime.skeleton.get_bone_pose_rotation(i)))
		for name in face_tracks:
			max_face_error = maxf(max_face_error, absf(runtime.face_mesh.get_blend_shape_value(runtime.expression_ids[name]) - pose.expression_weights(t)[name]))
	check(max_error < 0.00002, "saved clip replay matches authoring")
	check(max_face_error < 0.00001, "saved expressions replay exactly")
	report["saved_expression_max_weight_error"] = max_face_error
	report["saved_clip_frames"] = FRAME_COUNT
	report["saved_clip_max_quaternion_error"] = max_error
	var max_between_keys := 0.0
	var max_replay_locked := 0.0
	var max_replay_pivot := 0.0
	# Exercise off-keyframe interpolation and non-monotonic seeking as well.
	for f in range(493):
		var t := float((f * 197) % 493) / 120.0
		pose.apply(t)
		var expected: Dictionary = pose.snapshot()
		pose.reset()
		runtime.authored_motion_player.seek(t, true)
		for i in expected:
			max_between_keys = maxf(max_between_keys, rotation_error(expected[i], runtime.skeleton.get_bone_pose_rotation(i)))
		check(pose.open_fingers_unchanged(), "saved clip keeps five fingers open between keys")
		if t >= 1.0 and t <= 3.16:
			max_replay_locked = maxf(max_replay_locked, locked_error(locked_reference))
			max_replay_pivot = maxf(max_replay_pivot, pose.point("ひじ.R").distance_to(elbow_anchor))
			check(locked_except_elbow(locked_reference), "saved clip locks upper arm and wrist between keys")
			check(pose.point("ひじ.R").distance_to(elbow_anchor) < 0.00001, "saved clip fixes elbow pivot")
			for name in face_tracks:
				check(absf(runtime.face_mesh.get_blend_shape_value(runtime.expression_ids[name]) - Pose.FACE_PEAK[name]) < 0.00001, "saved wave holds closed-eye smile")
	check(max_between_keys < 0.01, "saved interpolation / random seek within 1.15 degrees")
	report["off_keyframe_max_quaternion_error"] = max_between_keys
	report["saved_hold_max_locked_quaternion_error"] = max_replay_locked
	report["saved_hold_max_elbow_drift_m"] = max_replay_pivot
	# Read-only comparison against the owner's accepted v2 arm resource.
	var previous_path := OS.get_environment("FAREWELL_ARM_BASELINE")
	if not previous_path.is_empty():
		var previous_clip: Animation = load(previous_path)
		check(previous_clip != null and previous_clip.get_track_count() == 35, "accepted v2 arm baseline")
		if previous_clip != null:
			var max_arm_change := 0.0
			for old_track in previous_clip.get_track_count():
				var new_track := replay.find_track(previous_clip.track_get_path(old_track), Animation.TYPE_ROTATION_3D)
				check(new_track >= 0, "accepted arm track preserved")
				if new_track < 0:
					continue
				for f in range(FRAME_COUNT):
					var t := float(f) / 30.0
					max_arm_change = maxf(max_arm_change, rotation_error(previous_clip.rotation_track_interpolate(old_track, t), replay.rotation_track_interpolate(new_track, t)))
			check(max_arm_change < 0.00002, "accepted v2 arm keys unchanged")
			report["accepted_v2_arm_max_quaternion_error"] = max_arm_change

func finish() -> void:
	report["failures"] = failures
	report["asset_sha256_after"] = FileAccess.get_sha256("res://assets/luotianyi_v4.glb")
	FileAccess.open(output + "/report.json", FileAccess.WRITE).store_string(JSON.stringify(report, "\t"))
	print("FAREWELL_REVIEW ", JSON.stringify(report))
	quit(0 if failures.is_empty() else 1)

func _run() -> void:
	output = OS.get_environment("FAREWELL_OUTPUT")
	if output.is_empty() or DirAccess.dir_exists_absolute(output):
		push_error("FAREWELL_OUTPUT must be a fresh directory")
		quit(1)
		return
	DirAccess.make_dir_recursive_absolute(output)
	root.size = Vector2i(16, 16)
	root.position = Vector2i(-100, -100)
	root.always_on_top = false
	viewport = SubViewport.new()
	viewport.size = Vector2i(960, 1160)
	viewport.own_world_3d = true
	viewport.transparent_bg = true
	viewport.msaa_3d = Viewport.MSAA_4X
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(viewport)
	runtime = load("res://main.tscn").instantiate()
	runtime.set_script(Review.OfflineRuntime)
	viewport.add_child(runtime)
	runtime.set_model_look_version("1.4")
	pose = Pose.new()
	pose.setup(runtime)
	verify()
	bake_and_replay()
	if not failures.is_empty() or OS.get_cmdline_user_args().has("--verify-only"):
		finish()
		return
	if DisplayServer.get_name() == "headless":
		check(false, "real GPU required for rendering")
		finish()
		return
	if OS.get_cmdline_user_args().has("--near"):
		runtime.camera.position = Vector3(-0.12, 1.34, 1.38)
		runtime.camera.look_at(Vector3(-0.12, 1.34, 0))
	for t in [0.0, 0.5, 0.75, 1.0, 1.3, 1.55, 3.5, 3.8, 4.1]:
		for yaw in [0, 55, -55, 180]:
			await capture(t, yaw, output + "/t%.2f-y%d.png" % [t, yaw])
	if OS.get_cmdline_user_args().has("--animate"):
		DirAccess.make_dir_recursive_absolute(output + "/frames")
		for f in range(FRAME_COUNT):
			await capture(float(f) / 30.0, 0, output + "/frames/%04d.png" % f)
			if f % 30 == 0:
				print("FAREWELL_RENDER_FRAME ", f)
	check(FileAccess.get_sha256("res://assets/luotianyi_v4.glb") == Review.SHA, "asset unchanged after render")
	finish()

func capture(t: float, yaw: int, path: String) -> void:
	pose.reset()
	runtime.authored_motion_player.seek(t, true)
	runtime.model.rotation = runtime.base_model_rotation + Vector3(0, deg_to_rad(yaw), 0)
	runtime.elapsed = t
	runtime._apply_pigtail_pose()
	# Head and facial expression are replayed from the saved candidate itself.
	await process_frame
	await RenderingServer.frame_post_draw
	var pixels := viewport.get_texture().get_image()
	check(not pixels.is_empty(), "nonempty GPU frame")
	if not pixels.is_empty():
		check(pixels.save_png(path) == OK, "save GPU frame")
