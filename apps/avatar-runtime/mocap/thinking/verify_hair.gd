extends SceneTree
## Codex: bounded preview verification. Capsule distances are NOT mesh clearance.
const Review = preload("res://lookdev/render_candidate.gd")
const Pose = preload("res://mocap/thinking/pose.gd")
const Hair = preload("res://mocap/thinking/hair_pose.gd")
var runtime: Node
var pose: RefCounted
var hair: RefCounted
var rig: Skeleton3D

func _init() -> void:
	call_deferred("_run")

func point(name: String) -> Vector3:
	return rig.get_bone_global_pose(rig.find_bone(name)).origin

func clearance() -> Dictionary:
	var result := {"gap": 10.0, "pair": ""}
	for chain in hair.chains:
		for j in range(2, 16):
			var p := rig.get_bone_global_pose(chain[j]).origin
			var q := rig.get_bone_global_pose(chain[j + 1]).origin
			for side in ["L", "R"]:
				for names in [["腕.", "ひじ.", 0.035], ["ひじ.", "手首.", 0.032]]:
					var points := Geometry3D.get_closest_points_between_segments(p, q, point(names[0] + side), point(names[1] + side))
					var gap := points[0].distance_to(points[1]) - float(names[2]) - 0.014
					if gap < result.gap:
						var normal: Vector3 = (points[0] - points[1]).normalized()
						result = {"gap": gap, "pair": "%s/%s%s" % [rig.get_bone_name(chain[j]), names[0], side], "outward_normal": [normal.x, normal.y, normal.z]}
	return result

func _run() -> void:
	var report_path := OS.get_environment("THINKING_REPORT")
	if report_path.is_empty() or FileAccess.file_exists(report_path):
		push_error("Use a fresh THINKING_REPORT path")
		quit(1)
		return
	runtime = load("res://main.tscn").instantiate()
	runtime.set_script(Review.OfflineRuntime)
	root.add_child(runtime)
	rig = runtime.skeleton
	pose = Pose.new()
	pose.setup(runtime)
	hair = Hair.new()
	hair.setup(runtime)
	var controlled := {}
	for chain in hair.chains:
		for i in chain:
			controlled[i] = true
	var maximum_position_error := 0.0
	var maximum_scale_error := 0.0
	var maximum_nonhair_rotation_error := 0.0
	var maximum_step := 0.0
	var maximum_segment_error := 0.0
	var maximum_endpoint_error := 0.0
	var previous := {}
	var rows := []
	var minimum_before := 10.0
	var minimum_after := 10.0
	for frame in range(571):
		var t := float(frame) / 60.0
		pose.apply(t)
		runtime.elapsed = t
		runtime._apply_pigtail_pose()
		var before: Dictionary = clearance()
		var local := {}
		for i in rig.get_bone_count():
			local[i] = rig.get_bone_pose(i)
		var lengths := []
		for chain in hair.chains:
			for j in range(16):
				lengths.append(rig.get_bone_global_pose(chain[j]).origin.distance_to(rig.get_bone_global_pose(chain[j + 1]).origin))
		if not OS.get_cmdline_user_args().has("--baseline"):
			hair.apply(t)
		var segment := 0
		for chain in hair.chains:
			for j in range(16):
				var length_now := rig.get_bone_global_pose(chain[j]).origin.distance_to(rig.get_bone_global_pose(chain[j + 1]).origin)
				maximum_segment_error = maxf(maximum_segment_error, absf(length_now - lengths[segment]))
				segment += 1
		var after: Dictionary = clearance()
		minimum_before = minf(minimum_before, before.gap)
		minimum_after = minf(minimum_after, after.gap)
		for i in rig.get_bone_count():
			var now := rig.get_bone_pose(i)
			maximum_position_error = maxf(maximum_position_error, now.origin.distance_to(local[i].origin))
			maximum_scale_error = maxf(maximum_scale_error, now.basis.get_scale().distance_to(local[i].basis.get_scale()))
			var q := rig.get_bone_pose_rotation(i).normalized()
			if frame == 0 or frame == 570:
				maximum_endpoint_error = maxf(maximum_endpoint_error, absf(1.0 - absf(q.dot(local[i].basis.get_rotation_quaternion().normalized()))))
			if not controlled.has(i):
				maximum_nonhair_rotation_error = maxf(maximum_nonhair_rotation_error, absf(1.0 - absf(q.dot(local[i].basis.get_rotation_quaternion().normalized()))))
			elif previous.has(i):
				# Difference quaternion atan2 stays well conditioned near zero.
				var delta: Quaternion = previous[i].inverse() * q
				var angle := rad_to_deg(2.0 * atan2(Vector3(delta.x, delta.y, delta.z).length(), absf(delta.w)))
				maximum_step = maxf(maximum_step, angle)
			previous[i] = q
		rows.append({"time": t, "before": before, "after": after})
	var passed := maximum_position_error < 0.000005 and maximum_scale_error < 0.000005 and maximum_nonhair_rotation_error < 0.000002 and maximum_step < 2.0 and maximum_segment_error < 0.000005 and maximum_endpoint_error < 0.000002
	var proxy_pass := minimum_before < -0.005 and minimum_after > 0.0
	var report := {"agent": "Codex", "integrity_pass": passed, "samples": 571, "sample_hz": 60,
		"arm_capsule_gate_pass": proxy_pass, "bone_segment_length_error_m": maximum_segment_error,
		"endpoint_rotation_error": maximum_endpoint_error,
		"position_error_m": maximum_position_error, "scale_error": maximum_scale_error,
		"nonhair_rotation_error": maximum_nonhair_rotation_error, "max_hair_step_deg": maximum_step,
		"capsule_before_min_m": minimum_before, "capsule_after_min_m": minimum_after,
		"capsule_limit": "diagnostic only: approximate arm radius 32/35mm and hair radius 14mm; not a triangle collision or clothing test",
		"frames": rows}
	DirAccess.make_dir_recursive_absolute(report_path.get_base_dir())
	FileAccess.open(report_path, FileAccess.WRITE).store_string(JSON.stringify(report, "\t"))
	report.erase("frames")
	print(JSON.stringify(report))
	quit(0 if passed and proxy_pass else 1)
