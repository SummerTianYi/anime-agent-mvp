extends SceneTree

## Codex: deterministic/offline state, clip and official-asset regression.
const Review = preload("res://lookdev/render_candidate.gd")
var checks := 0
var failures: Array[String] = []

func _init() -> void:
	call_deferred("_run")

func _check(ok: bool, message: String) -> void:
	checks += 1
	if not ok:
		if not failures.has(message):
			failures.append(message)
			push_error("LISTEN_VERIFY_FAIL " + message)

func _run() -> void:
	var runtime: Node = load("res://main.tscn").instantiate()
	runtime.set_script(Review.OfflineRuntime)
	root.add_child(runtime)
	var player: AnimationPlayer = runtime.authored_motion_player
	var rig: Skeleton3D = runtime.skeleton
	var candidate_path := OS.get_environment("LISTEN_REVIEW_PATH")
	if not candidate_path.is_empty():
		var lib := player.get_animation_library(&"")
		lib.remove_animation(&"listen")
		runtime._load_authored_motion_clip(&"listen", candidate_path, runtime.authored_motion_clips["listen"], lib)
	_check(bool(runtime.authored_motion_clips["listen"].get("return_via_reverse", false)), "new listen registry not installed")
	if not failures.is_empty():
		quit(1)
		return
	_check(FileAccess.get_sha256("res://assets/luotianyi_v4.glb") == Review.SHA, "official GLB immutable")
	_check(rig.get_bone_count() == 703, "official skeleton count")
	_check(runtime.face_mesh.mesh.get_blend_shape_count() == 48, "48 expressions")
	var clip := player.get_animation(&"listen")
	_check(clip.get_track_count() == 74, "74 upper-body rotation tracks")
	var maximum_step := 0.0
	var maximum_step_at := ""
	for i in range(clip.get_track_count()):
		_check(clip.track_get_type(i) == Animation.TYPE_ROTATION_3D, "no position/scale/visibility track")
		var bone := rig.find_bone(String(clip.track_get_path(i).get_subname(0)))
		_check(runtime._bone_in_motion_layer(bone, "upper_body"), "upper-body only")
		_check(clip.track_get_key_count(i) == 61, "61 measured/baked frames")
		for k in range(clip.track_get_key_count(i)):
			var q: Quaternion = clip.track_get_key_value(i, k)
			_check(q.is_finite() and absf(q.length() - 1.0) < 0.001, "finite unit quaternion")
			if k > 0:
				var prev: Quaternion = clip.track_get_key_value(i, k - 1)
				var step := absf(prev.angle_to(q))
				if step > maximum_step:
					maximum_step = step
					maximum_step_at = "%s frame %d" % [clip.track_get_path(i), k]
	print("LISTEN_MAXIMUM_STEP ", maximum_step_at, " degrees=", rad_to_deg(maximum_step))
	_check(maximum_step < deg_to_rad(20), "no >20-degree per-frame flip: %s" % maximum_step)
	# Whole trajectory: pose translations/scales never change, lower body stays
	# fixed, intended camera occlusion cannot trigger an extra arm correction.
	runtime._play_authored_motion(&"idle")
	player.advance(0.0)
	player.seek(0.0, true)
	var baseline := {}
	var hinges := {}
	for bone in range(rig.get_bone_count()):
		baseline[bone] = rig.get_bone_pose(bone)
	for side in ["L", "R"]:
		var hand := rig.get_bone_global_pose(rig.find_bone("手首." + side)).origin
		var index := rig.get_bone_global_pose(rig.find_bone("人指１." + side)).origin
		var little := rig.get_bone_global_pose(rig.find_bone("小指１." + side)).origin
		var elbow := rig.get_bone_global_pose(rig.find_bone("ひじ." + side))
		var normal := (index - hand).cross(little - hand).normalized()
		if normal.z < 0.0:
			normal = -normal
		hinges[side] = elbow.basis.inverse() * (hand - elbow.origin).normalized().cross(normal).normalized()
	runtime._play_authored_motion(&"listen")
	player.advance(0.0)
	var maximum_elbow_flex := 0.0
	var maximum_wrist_bend := 0.0
	var maximum_elbow_off_axis := 0.0
	for frame in range(61):
		player.seek(float(frame) / 30.0, true)
		for side in ["L", "R"]:
			var elbow_index := rig.find_bone("ひじ." + side)
			var base_pose: Transform3D = baseline[elbow_index]
			var bend := base_pose.basis.get_rotation_quaternion().inverse() * rig.get_bone_pose_rotation(elbow_index)
			var vector := Vector3(bend.x, bend.y, bend.z)
			var hinge: Vector3 = hinges[side]
			maximum_elbow_off_axis = maxf(maximum_elbow_off_axis, (vector - hinge * vector.dot(hinge)).length())
			var shoulder := rig.get_bone_global_pose(rig.find_bone("腕." + side)).origin
			var joint := rig.get_bone_global_pose(rig.find_bone("ひじ." + side)).origin
			var wrist := rig.get_bone_global_pose(rig.find_bone("手首." + side)).origin
			maximum_elbow_flex = maxf(maximum_elbow_flex, (joint - shoulder).angle_to(wrist - joint))
			var finger := rig.get_bone_global_pose(rig.find_bone("人指１." + side)).origin
			maximum_wrist_bend = maxf(maximum_wrist_bend, (wrist - joint).angle_to(finger - wrist))
		for bone in range(rig.get_bone_count()):
			var before: Transform3D = baseline[bone]
			var after := rig.get_bone_pose(bone)
			_check(before.origin.distance_to(after.origin) < 0.00001, "bone translation unchanged")
			_check(before.basis.get_scale().distance_to(after.basis.get_scale()) < 0.00001, "bone scale unchanged")
			if runtime._bone_in_motion_layer(bone, "lower_body"):
				_check(before.is_equal_approx(after), "lower-body pose unchanged")
		var elbow := rig.get_bone_pose(rig.find_bone("ひじ.L"))
		runtime._preserve_limb_readability()
		_check(elbow.is_equal_approx(rig.get_bone_pose(rig.find_bone("ひじ.L"))), "no camera correction of tucked forearm")
	print("LISTEN_JOINT_LIMITS ", {"elbow_flex_degrees": rad_to_deg(maximum_elbow_flex), "wrist_bend_degrees": rad_to_deg(maximum_wrist_bend), "elbow_off_axis": maximum_elbow_off_axis})
	_check(maximum_elbow_flex < deg_to_rad(135), "elbows must not fold tighter than 135 degrees")
	_check(maximum_wrist_bend < deg_to_rad(40), "wrist bend must remain below 40 degrees")
	_check(maximum_elbow_off_axis < 0.001, "elbow flex must stay on its hinge without axial sleeve twist")
	var hand := rig.get_bone_global_pose(rig.find_bone("手首.L")).origin
	var chest := rig.get_bone_global_pose(rig.find_bone("上半身2")).origin
	_check(hand.z < chest.z - 0.09, "left wrist remains behind torso at hold")
	runtime._cancel_authored_motion(true)
	# Early cancel, completed hold, repeated state, reverse interrupted by recording.
	for stop_time in [0.0, 0.1, 0.5, 1.0, 1.7, 2.1]:
		runtime._set_voice_motion_state("recording")
		player.advance(0.0)
		player.advance(stop_time)
		var before: Quaternion = rig.get_bone_pose_rotation(rig.find_bone("ひじ.L"))
		runtime._set_voice_motion_state("transcribing")
		player.advance(0.0)
		_check(absf(before.angle_to(rig.get_bone_pose_rotation(rig.find_bone("ひじ.L")))) < 0.002, "cancel must not teleport elbow")
		runtime._set_voice_motion_state("transcribing")
		for step in range(75):
			player.advance(1.0 / 30.0)
		_check(runtime.authored_motion_name == &"idle", "cancel returns to A-pose at %s" % stop_time)
	runtime._set_voice_motion_state("recording")
	player.advance(1.2)
	runtime._set_voice_motion_state("idle")
	player.advance(0.3)
	var position := player.current_animation_position
	runtime._set_voice_motion_state("recording")
	player.advance(0.0)
	_check(absf(player.current_animation_position - position) < 0.001, "resume must preserve timeline")
	player.advance(2.1)
	_check(runtime.authored_motion_name == &"listen" and not player.is_playing(), "hold while recording")
	runtime._set_voice_motion_state("idle")
	for step in range(75):
		player.advance(1.0 / 30.0)
	_check(runtime.authored_motion_name == &"idle", "resume then release returns idle")
	runtime._play_authored_motion(&"listen")
	player.advance(0.8)
	runtime._play_authored_motion(&"listen")
	player.advance(0.0)
	_check(absf(player.current_animation_position - 0.8) < 0.001, "repeated G/menu does not restart")
	for step in range(135):
		player.advance(1.0 / 30.0)
	_check(runtime.authored_motion_name == &"idle", "manual listen completes round trip")
	if failures.is_empty():
		print("LISTEN_VERIFY_OK ", {"checks": checks, "maximum_frame_angle_degrees": rad_to_deg(maximum_step), "source": "mocap+authored left arm/palm/lean; no universal collision claim"})
	quit(0 if failures.is_empty() else 1)
