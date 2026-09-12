extends SceneTree
## Codex: structural/trajectory gates for this preview, not universal physics.
const Review = preload("res://lookdev/render_candidate.gd")
const Pose = preload("res://mocap/thinking/pose.gd")
var failures: Array[String] = []
var checks := 0
func _init() -> void:
	call_deferred("_run")
func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok and not failures.has(message):
		failures.append(message)
func hand_shape_errors(pose: RefCounted, rig: Skeleton3D) -> Array[String]:
	var errors: Array[String] = []
	for finger in ["人指", "中指", "薬指", "小指"]:
		for digit in ["１", "２", "３"]:
			var i := rig.find_bone(finger + digit + ".L")
			var before: Transform3D = pose.baseline[i]
			var angle := rad_to_deg(before.basis.get_rotation_quaternion().angle_to(rig.get_bone_pose_rotation(i)))
			if (finger == "人指" and angle > 3.0) or (finger != "人指" and angle < 25.0):
				errors.append(finger + digit)
	return errors
func _run() -> void:
	var runtime = load("res://main.tscn").instantiate()
	runtime.set_script(Review.OfflineRuntime)
	root.add_child(runtime)
	var pose = Pose.new()
	pose.setup(runtime)
	var rig: Skeleton3D = runtime.skeleton
	pose.apply(3.7)
	check(hand_shape_errors(pose, rig).is_empty(), "index open and three fingers curled")
	var middle := rig.find_bone("中指１.L")
	rig.set_bone_pose(middle, pose.baseline[middle])
	check(not hand_shape_errors(pose, rig).is_empty(), "negative control rejects old open-hand shape")
	var hash_before := FileAccess.get_sha256("res://assets/luotianyi_v4.glb")
	var previous := {}
	var maximum_step := 0.0
	var maximum_elbow := 0.0
	var maximum_wrist := 0.0
	var maximum_off_axis := 0.0
	var maximum_support_gap := 0.0
	var max_step_bone := ""
	var max_wrist_at := ""
	var samples := []
	for frame in range(1141):
		var t := float(frame) / 120.0
		pose.apply(t)
		for i in rig.get_bone_count():
			var original: Transform3D = pose.baseline[i]
			var current := rig.get_bone_pose(i)
			check(current.origin.distance_to(original.origin) < 0.00001, "bone translations preserved")
			check(current.basis.get_scale().distance_to(original.basis.get_scale()) < 0.00001, "bone scales preserved")
			check(current.is_finite(), "finite pose")
			if not pose.controlled.has(i):
				check(current.is_equal_approx(original), "noncontrolled pose preserved")
			if frame in [0, 1140]:
				check(current.is_equal_approx(original), "exact A-pose endpoints")
		for i in pose.controlled:
			var q := rig.get_bone_pose_rotation(i)
			if previous.has(i):
				var angle: float = previous[i].angle_to(q)
				if angle > maximum_step:
					maximum_step = angle
					max_step_bone = "%s at %.3fs" % [rig.get_bone_name(i), t]
			previous[i] = q
		for side in ["L", "R"]:
			var shoulder: Vector3 = pose.point("腕." + side)
			var elbow: Vector3 = pose.point("ひじ." + side)
			var wrist: Vector3 = pose.point("手首." + side)
			var fingers: Vector3 = (pose.point("人指１." + side) + pose.point("小指１." + side)) * 0.5
			maximum_elbow = maxf(maximum_elbow, (elbow - shoulder).angle_to(wrist - elbow))
			var bend := (wrist - elbow).angle_to(fingers - wrist)
			if bend > maximum_wrist:
				maximum_wrist = bend
				max_wrist_at = "%s at %.3f" % [side, t]
			var e := rig.find_bone("ひじ." + side)
			var original: Transform3D = pose.baseline[e]
			var q := original.basis.get_rotation_quaternion().inverse() * rig.get_bone_pose_rotation(e)
			var v := Vector3(q.x, q.y, q.z)
			var axis: Vector3 = pose.hinges[side]
			maximum_off_axis = maxf(maximum_off_axis, (v - axis * v.dot(axis)).length())
		if t >= 1.65 and t <= 7.0:
			maximum_support_gap = maxf(maximum_support_gap, pose.contacts().support_elbow_m)
			check(pose.point("手首.L").distance_to(pose.point("頭")) < 0.19, "chin hand stays near face")
			check(hand_shape_errors(pose, rig).is_empty(), "fixed hand shape throughout looking motion")
		if frame % 120 == 0:
			samples.append({"time": t, "contacts": pose.contacts()})
	check(maximum_step < deg_to_rad(2.5), "no sudden >2.5 degree jumps at 120Hz")
	check(maximum_elbow < deg_to_rad(146), "elbow flex <=146 degrees")
	check(maximum_wrist < deg_to_rad(60), "wrist bend <=60 degrees")
	check(maximum_off_axis < 0.001, "elbows are hinges, not axial twist joints")
	check(maximum_support_gap < 0.045, "support palm stays at elbow surface allowance")
	check(hash_before == Review.SHA and hash_before == FileAccess.get_sha256("res://assets/luotianyi_v4.glb"), "immutable official asset")
	check(rig.get_bone_count() == 703 and runtime.face_mesh.mesh.get_blend_shape_count() == 48, "703 bones and 48 morphs")
	var report := {"agent": "Codex", "frames_120hz": 1141, "checks": checks, "failures": failures,
		"max_step_deg": rad_to_deg(maximum_step), "max_step_at": max_step_bone,
		"max_elbow_deg": rad_to_deg(maximum_elbow), "max_wrist_deg": rad_to_deg(maximum_wrist), "max_wrist_at": max_wrist_at,
		"max_elbow_off_axis": maximum_off_axis, "max_support_palm_elbow_m": maximum_support_gap, "samples": samples}
	var output := OS.get_environment("THINKING_REPORT")
	if not output.is_empty() and not FileAccess.file_exists(output):
		FileAccess.open(output, FileAccess.WRITE).store_string(JSON.stringify(report, "\t"))
	print("THINKING_VERIFY ", JSON.stringify(report))
	quit(0 if failures.is_empty() else 1)
