extends "res://mocap/thinking/verify_hair.gd"
## Codex: audit any saved 34-track hair simulation independently.
func _run() -> void:
	var source := OS.get_environment("SPRING_CLIP")
	var target := OS.get_environment("THINKING_REPORT")
	if source.is_empty() or target.is_empty() or FileAccess.file_exists(target):
		push_error("Need SPRING_CLIP and fresh THINKING_REPORT")
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
	var clip: Animation = load(source)
	if clip == null or clip.get_track_count() != 34:
		push_error("Expected 34 hair-only tracks")
		quit(1)
		return
	var controlled := {}
	for chain in hair.chains:
		for i in chain:
			controlled[i] = true
	for track in clip.get_track_count():
		if clip.track_get_type(track) != Animation.TYPE_ROTATION_3D or not controlled.has(rig.find_bone(clip.track_get_path(track).get_subname(0))):
			push_error("Non-hair rotation track in bake")
			quit(1)
			return
	runtime.authored_motion_player.get_animation_library(&"").add_animation(&"_spring_audit", clip)
	runtime.authored_motion_player.play(&"_spring_audit")
	runtime.authored_motion_player.advance(0)
	runtime.authored_motion_player.pause()
	var max_position := 0.0
	var max_scale := 0.0
	var max_nonhair := 0.0
	var max_step := 0.0
	var worst_step := {}
	var minimum_gap := 1.0
	var penetration_frames := 0
	var previous := {}
	var previous_segments := {}
	var maximum_direction_step := 0.0
	var worst_direction_step := {}
	var frames := []
	var hold_tip := Vector3.ZERO
	var released_tip := Vector3.ZERO
	var return_rotation_error := 0.0
	var return_point_error := 0.0
	var exit_step := 0.0
	var worst_exit := {}
	var preserved_error := 0.0
	var sample_hz := 240 if OS.get_cmdline_user_args().has("--dense") else 120
	var sample_count := int(9.5 * sample_hz) + 1
	var return_samples := 0
	var reference: Animation
	if not OS.get_environment("RETURN_SOURCE_CHECK").is_empty():
		reference = load(OS.get_environment("RETURN_SOURCE_CHECK"))
		if reference == null or reference.get_track_count() != clip.get_track_count():
			push_error("Invalid unchanged-motion reference")
			quit(1)
			return
	for f in range(sample_count):
		var t := float(f) / sample_hz
		pose.apply(t)
		var idle_rotations := {}
		var idle_points := {}
		if t >= 9.3:
			return_samples += 1
			runtime.elapsed = t
			runtime._apply_pigtail_pose()
			for i in controlled:
				idle_rotations[i] = rig.get_bone_pose_rotation(i)
				idle_points[i] = rig.get_bone_global_pose(i).origin
		var baseline := {}
		for i in rig.get_bone_count():
			baseline[i] = rig.get_bone_pose(i)
		runtime.authored_motion_player.seek(t, true)
		if t >= 9.3:
			for i in controlled:
				var delta: Quaternion = idle_rotations[i].inverse() * rig.get_bone_pose_rotation(i)
				return_rotation_error = maxf(return_rotation_error, rad_to_deg(2 * atan2(Vector3(delta.x, delta.y, delta.z).length(), absf(delta.w))))
				return_point_error = maxf(return_point_error, rig.get_bone_global_pose(i).origin.distance_to(idle_points[i]))
		if reference != null and t <= 7.0:
			for track in clip.get_track_count():
				if reference.track_get_path(track) != clip.track_get_path(track):
					push_error("Reference track order differs")
					quit(1)
					return
				var delta: Quaternion = reference.rotation_track_interpolate(track, t).inverse() * clip.rotation_track_interpolate(track, t)
				preserved_error = maxf(preserved_error, rad_to_deg(2 * atan2(Vector3(delta.x, delta.y, delta.z).length(), absf(delta.w))))
		var gap := clearance()
		minimum_gap = minf(minimum_gap, gap.gap)
		if gap.gap < -0.002:
			penetration_frames += 1
		var tips := []
		for chain in hair.chains:
			var tip := rig.get_bone_global_pose(chain[16]).origin
			tips.append([tip.x, tip.y, tip.z])
			for j in range(16):
				var direction := (rig.get_bone_global_pose(chain[j+1]).origin - rig.get_bone_global_pose(chain[j]).origin).normalized()
				if previous_segments.has(chain[j]):
					var before: Vector3 = previous_segments[chain[j]]
					var angle := rad_to_deg(atan2(before.cross(direction).length(), before.dot(direction)))
					if angle > maximum_direction_step:
						maximum_direction_step = angle
						worst_direction_step = {"time": t, "bone": rig.get_bone_name(chain[j])}
				previous_segments[chain[j]] = direction
		if is_equal_approx(t, 7.0):
			hold_tip = rig.get_bone_global_pose(hair.chains[0][16]).origin
		if is_equal_approx(t, 9.5):
			released_tip = rig.get_bone_global_pose(hair.chains[0][16]).origin
		for i in rig.get_bone_count():
			var now := rig.get_bone_pose(i)
			max_position = maxf(max_position, now.origin.distance_to(baseline[i].origin))
			max_scale = maxf(max_scale, now.basis.get_scale().distance_to(baseline[i].basis.get_scale()))
			var q := rig.get_bone_pose_rotation(i).normalized()
			if not controlled.has(i):
				max_nonhair = maxf(max_nonhair, absf(1.0 - absf(q.dot(baseline[i].basis.get_rotation_quaternion().normalized()))))
			elif previous.has(i):
				var d: Quaternion = previous[i].inverse() * q
				var angle := rad_to_deg(2.0 * atan2(Vector3(d.x, d.y, d.z).length(), absf(d.w)))
				if t >= 7.0 and angle > exit_step:
					exit_step = angle
					worst_exit = {"time": t, "bone": rig.get_bone_name(i)}
				if angle > max_step:
					max_step = angle
					worst_step = {"time": t, "bone": rig.get_bone_name(i)}
			previous[i] = q
		frames.append({"time": t, "gap": gap, "tips": tips})
	var integrity := max_position < 0.000005 and max_scale < 0.000005 and max_nonhair < 0.000002
	var return_ok := return_rotation_error < 0.002 and return_point_error < 0.00002 and exit_step * sample_hz / 120.0 < 2.0 and preserved_error < 0.002 and penetration_frames == 0
	var report := {"source": source, "samples": sample_count, "sample_hz": sample_hz, "structure_pass": integrity,
		"return_pass": return_ok, "return_rotation_error_deg": return_rotation_error, "return_point_error_m": return_point_error,
		"exit_max_step_degrees_120hz": exit_step * sample_hz / 120.0, "worst_exit": worst_exit, "return_window_samples": return_samples,
		"unchanged_0_to_7s_error_deg": preserved_error, "unchanged_reference_checked": reference != null,
		"position_error_m": max_position, "scale_error": max_scale, "nonhair_rotation_error": max_nonhair,
		"max_hair_step_degrees": max_step, "worst_step": worst_step,
		"max_centerline_direction_step_degrees": maximum_direction_step, "worst_direction_step": worst_direction_step,
		"proxy_min_gap_m": minimum_gap, "proxy_penetration_frames_over_2mm": penetration_frames,
		"right_tip_drop_after_release_m": hold_tip.y - released_tip.y,
		"limit": "Approximate arm capsules, not actual mesh contacts; naturalness and all collisions remain visual acceptance items.", "frames": frames}
	DirAccess.make_dir_recursive_absolute(target.get_base_dir())
	FileAccess.open(target, FileAccess.WRITE).store_string(JSON.stringify(report, "\t"))
	report.erase("frames")
	print(JSON.stringify(report))
	quit(0 if integrity and (not OS.get_cmdline_user_args().has("--require-return") or return_ok) else 1)
