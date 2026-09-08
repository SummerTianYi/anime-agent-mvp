extends SceneTree

## Historical Codex v2 builder, retained for endpoint/archive reproduction.
## Its IK transition was rejected; use build_listen_transition.gd for current FK.
## Bake measured right-arm motion on the ACTUAL runtime rest skeleton.
## The occluded left arm is authored; no mesh, rest, scale, or skin writes.
const Review = preload("res://lookdev/render_candidate.gd")
var runtime: Node
var rig: Skeleton3D
var frames: Array
var controlled: Array[int] = []
var start_pose: Dictionary = {}
var elbow_hinges: Dictionary = {}
var result: Animation
var output := "res://assets/motions/listen_mocap_v2_corrected_candidate.tres"

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	var requested_output := OS.get_environment("LISTEN_OUTPUT")
	if not requested_output.is_empty():
		output = requested_output
	if FileAccess.file_exists(output):
		push_error("Refusing to overwrite an existing motion; choose a new LISTEN_OUTPUT")
		quit(1)
		return
	var input := OS.get_environment("LISTEN_LANDMARKS")
	if input.is_empty() or not FileAccess.file_exists(input):
		push_error("LISTEN_LANDMARKS must identify the reviewed local pose JSON")
		quit(1)
		return
	var payload: Variant = JSON.parse_string(FileAccess.get_file_as_string(input))
	if payload is not Dictionary or payload.get("frames") is not Array:
		push_error("Invalid landmark JSON")
		quit(1)
		return
	frames = payload.frames
	if frames.size() < 103:
		push_error("The reviewed source segment requires at least 103 frames at 30fps")
		quit(1)
		return
	runtime = load("res://main.tscn").instantiate()
	runtime.set_script(Review.OfflineRuntime)
	root.add_child(runtime)
	rig = runtime.skeleton
	runtime._cancel_authored_motion()
	runtime._restore_bone_poses()
	# Reproduce conservative idle exactly, including non-controlled helper bones.
	runtime._play_authored_motion(&"idle")
	runtime.authored_motion_player.seek(0.0, true)
	runtime.authored_motion_player.pause()
	var arms := {}
	for side in ["L", "R"]:
		runtime._collect_bone_descendants("肩." + side, arms)
	for bone in arms:
		controlled.append(bone)
	for name in ["上半身", "上半身2", "首", "頭"]:
		controlled.append(rig.find_bone(name))
	for bone in controlled:
		start_pose[bone] = rig.get_bone_pose(bone)
	# Derive neutral elbow flexion from the actual open-hand plane, not the
	# old screen-readable gesture axis (which is not an anatomical hinge).
	for side in ["L", "R"]:
		var hand := _point("手首." + side)
		var palm_normal := (_point("人指１." + side) - hand).cross(_point("小指１." + side) - hand).normalized()
		if palm_normal.z < 0.0:
			palm_normal = -palm_normal
		var forearm := (hand - _point("ひじ." + side)).normalized()
		var hinge := forearm.cross(palm_normal).normalized()
		elbow_hinges[side] = rig.get_bone_global_pose(rig.find_bone("ひじ." + side)).basis.inverse() * hinge
		print("LISTEN_ANATOMICAL_HINGE ", side, " ", elbow_hinges[side])
	for name in ["腕.R", "ひじ.R", "手首.R", "腕.L", "ひじ.L", "手首.L", "頭"]:
		print("LISTEN_RIG_BASE ", name, " ", _point(name))
	result = Animation.new()
	result.resource_name = "listen_mocap_v2"
	result.length = 2.0
	for bone in controlled:
		var track := result.add_track(Animation.TYPE_ROTATION_3D)
		result.track_set_path(track, NodePath("%s:%s" % [runtime.get_path_to(rig), rig.get_bone_name(bone)]))
		result.track_set_interpolation_type(track, Animation.INTERPOLATION_LINEAR)
	for f in range(61):
		_pose(float(f) / 30.0)
		for i in range(controlled.size()):
			result.rotation_track_insert_key(i, float(f) / 30.0, rig.get_bone_pose_rotation(controlled[i]))
		if f in [0, 15, 30, 45, 60]:
			print("LISTEN_RIG_SAMPLE ", f, " ", {
				"right_elbow": _point("ひじ.R"), "right_wrist": _point("手首.R"),
				"left_elbow": _point("ひじ.L"), "left_wrist": _point("手首.L")})
	if ResourceSaver.save(result, output) != OK:
		push_error("Unable to save listening clip")
		quit(1)
		return
	var report := {
		"agent": "Codex", "clip": output, "duration": result.length,
		"landmark_sha256": FileAccess.get_sha256(input),
		"model_sha256": FileAccess.get_sha256("res://assets/luotianyi_v4.glb"),
		"clip_sha256": FileAccess.get_sha256(output),
		"frames": 61, "rotation_tracks": controlled.size(),
		"measured": "right wrist-to-ear trajectory, elbow plane, shoulder/head yaw; source 1.7..3.4 seconds",
		"authored": "left arm outside-to-back IK path, right palm orientation, photo-guided torso lean",
		"preserved": "official geometry, textures, rest skeleton, skin, bone lengths and model look 1.3",
	}
	var report_file := FileAccess.open(output + ".json", FileAccess.WRITE)
	if report_file == null:
		quit(1)
		return
	report_file.store_string(JSON.stringify(report, "\t") + "\n")
	print("LISTEN_BAKE_OK ", output, " tracks=", controlled.size())
	quit()

func _point(name: String) -> Vector3:
	return rig.get_bone_global_pose(rig.find_bone(name)).origin

func _smooth(x: float) -> float:
	return smoothstep(0.0, 1.0, clampf(x, 0.0, 1.0))

func _landmark(index: int, second: float) -> Vector3:
	var center := clampi(roundi(second * 30.0), 0, frames.size() - 1)
	var value := Vector3.ZERO
	var count := 0
	for j in range(maxi(0, center - 3), mini(frames.size(), center + 4)):
		var p: Dictionary = frames[j].world[index]
		value += Vector3(float(p.x), -float(p.y), -float(p.z))
		count += 1
	return value / float(count)

func _aim(bone_name: String, child_name: String, direction: Vector3) -> void:
	var bone := rig.find_bone(bone_name)
	var current := rig.get_bone_global_pose(bone)
	var old := (_point(child_name) - current.origin).normalized()
	current.basis = Basis(Quaternion(old, direction.normalized())) * current.basis
	rig.set_bone_global_pose(bone, current)
	rig.force_update_all_bone_transforms()

func _rotate_global(name: String, axis: Vector3, angle: float) -> void:
	var bone := rig.find_bone(name)
	var pose := rig.get_bone_global_pose(bone)
	pose.basis = Basis(Quaternion(axis, angle)) * pose.basis
	rig.set_bone_global_pose(bone, pose)
	rig.force_update_all_bone_transforms()

func _pose(t: float) -> void:
	for bone in start_pose:
		rig.set_bone_pose(bone, start_pose[bone])
	rig.force_update_all_bone_transforms()
	if t <= 0.0:
		return
	var blend := _smooth(t / 1.65)
	# Use source 1.7..3.4s; the source's long pre-roll and final drop are excluded.
	var source_time := 1.7 + minf(t, 1.7)
	var r_sh := _landmark(12, source_time)
	var r_el := _landmark(14, source_time)
	var r_wr := _landmark(16, source_time)
	var shoulders := (_landmark(11, source_time) - r_sh).normalized()
	var base_shoulders := (_landmark(11, 1.7) - _landmark(12, 1.7)).normalized()
	var yaw := clampf(atan2(shoulders.z, shoulders.x) - atan2(base_shoulders.z, base_shoulders.x), -0.5, 0.5)
	# Photo-guided lean plus a small measured head/shoulder offset. Monocular
	# depth is not a trustworthy absolute torso angle; this is authored adaptation.
	var face := _landmark(0, source_time) - (_landmark(11, source_time) + r_sh) * 0.5
	var face0 := _landmark(0, 1.7) - (_landmark(11, 1.7) + _landmark(12, 1.7)) * 0.5
	var lean := (deg_to_rad(8.0) + clampf((face.z - face0.z) * 0.65, -0.03, 0.03)) * blend
	_rotate_global("上半身", Vector3.RIGHT, lean)
	_rotate_global("上半身2", Vector3.UP, -yaw * 0.4 * blend)
	var face_side := (_landmark(7, source_time) - _landmark(8, source_time)).normalized()
	var face_base := (_landmark(7, 1.7) - _landmark(8, 1.7)).normalized()
	var head_yaw := clampf(atan2(face_side.z, face_side.x) - atan2(face_base.z, face_base.x), -0.55, 0.55)
	_rotate_global("頭", Vector3.UP, -head_yaw * 0.65 * blend)
	var upper := (r_el - r_sh).normalized()
	# Human upper-arm/head proportions differ from the avatar. Preserve the
	# measured elbow plane and wrist-to-ear motion, then solve fixed bone lengths.
	var right_start := _point("手首.R")
	var ear_offset := (r_wr - _landmark(8, source_time)) * 0.6
	var right_target := _point("頭") + Vector3(-0.115, 0.035, 0.09) + ear_offset
	_solve_arm("R", right_start.lerp(right_target, blend), upper + Vector3(-0.35, 0.0, 0.1))
	# Authored open palm: index extends upward, not guessed individual finger mocap.
	var palm_axis := (_point("人指１.R") - _point("手首.R")).normalized()
	var forearm_axis := (_point("手首.R") - _point("ひじ.R")).normalized()
	var desired_palm := palm_axis.slerp(Vector3(0.05, 1.0, 0.0).normalized(), blend)
	var wrist_angle := forearm_axis.angle_to(desired_palm)
	if wrist_angle > deg_to_rad(35):
		desired_palm = forearm_axis.slerp(desired_palm, deg_to_rad(35) / wrist_angle)
	_aim("手首.R", "人指１.R", desired_palm)
	# Left wrist follows an explicit outside -> behind path; never a torso chord.
	var l_sh := _point("腕.L")
	var l_wr := _point("手首.L")
	var outward := Vector3(l_sh.x + 0.23, l_sh.y - 0.34, l_sh.z - 0.12)
	var behind := Vector3(l_sh.x - 0.07, l_sh.y - 0.25, l_sh.z - 0.18)
	var wrist: Vector3
	if t < 0.8:
		wrist = l_wr.lerp(outward, _smooth(t / 0.8))
	else:
		wrist = outward.lerp(behind, _smooth((t - 0.8) / 0.9))
	_solve_arm("L", wrist, Vector3(1.0, -0.4, -0.15))
	# Blend the initial near-straight elbow plane without a first-frame pop.
	var entry := _smooth(t / 0.6)
	for name in ["腕.L", "ひじ.L", "手首.L", "腕.R", "ひじ.R", "手首.R"]:
		var i := rig.find_bone(name)
		var q: Quaternion = start_pose[i].basis.get_rotation_quaternion()
		rig.set_bone_pose_rotation(i, q.slerp(rig.get_bone_pose_rotation(i), entry))

func _solve_arm(side: String, wrist: Vector3, pole: Vector3) -> void:
	var shoulder := _point("腕." + side)
	var elbow := _point("ひじ." + side)
	var hand := _point("手首." + side)
	var a := shoulder.distance_to(elbow)
	var b := elbow.distance_to(hand)
	var offset := wrist - shoulder
	var minimum_reach := sqrt(a * a + b * b + 2.0 * a * b * cos(deg_to_rad(125)))
	var d := clampf(offset.length(), minimum_reach, a + b - 0.001)
	var axis := offset.normalized()
	wrist = shoulder + axis * d
	var x := (a * a - b * b + d * d) / (2.0 * d)
	var h := sqrt(maxf(0.0, a * a - x * x))
	var perpendicular := (pole - axis * pole.dot(axis)).normalized()
	var joint := shoulder + axis * x + perpendicular * h
	# Codex: direction-only aiming leaves axial twist undefined. Rotate the
	# shoulder's full frame so the rig's elbow hinge matches the IK bend plane;
	# the elbow then bends about one axis instead of twisting the sleeve.
	var upper_before := (elbow - shoulder).normalized()
	var elbow_basis := rig.get_bone_global_pose(rig.find_bone("ひじ." + side)).basis
	var hinge_before: Vector3 = elbow_basis * elbow_hinges[side]
	hinge_before = (hinge_before - upper_before * hinge_before.dot(upper_before)).normalized()
	var upper_after := (joint - shoulder).normalized()
	var lower_after := (wrist - joint).normalized()
	var hinge_after := upper_after.cross(lower_after).normalized()
	var before_frame := Basis(upper_before, hinge_before, upper_before.cross(hinge_before))
	var after_frame := Basis(upper_after, hinge_after, upper_after.cross(hinge_after))
	var arm_index := rig.find_bone("腕." + side)
	var arm_pose := rig.get_bone_global_pose(arm_index)
	arm_pose.basis = after_frame * before_frame.transposed() * arm_pose.basis
	rig.set_bone_global_pose(arm_index, arm_pose)
	rig.force_update_all_bone_transforms()
	_aim("ひじ." + side, "手首." + side, wrist - _point("ひじ." + side))
