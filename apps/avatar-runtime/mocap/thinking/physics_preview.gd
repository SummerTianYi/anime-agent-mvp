extends "res://mocap/thinking/preview.gd"
## Codex: offline strand experiment, separate from production and body motion.
const Strand = preload("res://mocap/thinking/strand_physics.gd")
const Groom = preload("res://mocap/thinking/hair_pose.gd")
var spring_bones: Array[int] = []
var spring_frames: Array[Dictionary] = []
var observed := {}
var saved_hair: Animation

func observed_pose() -> void:
	observed = {}
	for i in spring_bones:
		observed[i] = runtime.skeleton.get_bone_pose_rotation(i)

func build_springs() -> void:
	var rig: Skeleton3D = runtime.skeleton
	pose.apply(0)
	runtime.elapsed = 0
	runtime._apply_pigtail_pose()
	var solver := Strand.new()
	solver.setup(runtime)
	var groom := Groom.new()
	groom.setup(runtime)
	for chain in solver.chains:
		for i in chain.ids:
			spring_bones.append(i)
	var existing := OS.get_environment("HAIR_CLIP")
	if not existing.is_empty():
		saved_hair = load(existing)
		if not validate_clip(saved_hair):
			quit(1)
			return
		if OS.get_cmdline_user_args().has("--return-idle"):
			restore_idle(groom)
		return
	var no_collisions := OS.get_cmdline_user_args().has("--no-collisions")
	var diagnostics := []
	for step in range(-480, 2281):
		var t := maxf(0, float(step) / 240.0)
		pose.apply(t)
		runtime.elapsed = 0.0
		runtime._apply_pigtail_pose()
		var guided := not OS.get_cmdline_user_args().has("--unguided")
		if guided:
			groom.apply(t)
		if t <= 1.2 and guided:
			solver.seed_from_rig()
			solver.update_shapes()
		else:
			# Keep the groomed attachment frame; restoring its old rotation
			# would rotate every downstream point at the handoff. Free lengths
			# below node 2 are still determined by the simulation, not the guide.
			solver.step(not no_collisions)
		if step >= 0 and step % 2 == 0:
			solver.apply_to_rig()
			observed_pose()
			spring_frames.append(observed.duplicate())
			if step % 24 == 0:
				var row := solver.diagnostics()
				row["time"] = t
				diagnostics.append(row)
		if step % 240 == 0:
			print("STRAND_BAKE_STEP ", step)
			await process_frame
	var clip := Animation.new()
	clip.length = 9.5
	for i in spring_bones:
		var track := clip.add_track(Animation.TYPE_ROTATION_3D)
		clip.track_set_path(track, NodePath("%s:%s" % [runtime.get_path_to(rig), rig.get_bone_name(i)]))
		for f in range(1141):
			clip.rotation_track_insert_key(track, float(f) / 120.0, spring_frames[f][i])
	if ResourceSaver.save(clip, output + "/hair_spring_preview.tres") != OK:
		push_error("Cannot save strand bake")
		quit(1)
		return
	saved_hair = ResourceLoader.load(output + "/hair_spring_preview.tres", "Animation", ResourceLoader.CACHE_MODE_IGNORE)
	if not validate_clip(saved_hair):
		quit(1)
		return
	var replay_error := 0.0
	for f in range(1141):
		for track in range(34):
			var q := saved_hair.rotation_track_interpolate(track, float(f) / 120).normalized()
			var original: Quaternion = spring_frames[f][spring_bones[track]].normalized()
			if q.dot(original) < 0:
				q = -q
			replay_error = maxf(replay_error, Vector4(q.x-original.x, q.y-original.y, q.z-original.z, q.w-original.w).length())
	if replay_error > 0.00002:
		push_error("Saved hair bake differs from simulation")
		quit(1)
		return
	print("STRAND_BAKE_COMPLETE ", spring_frames.size(), " projections=", solver.contact_count)
	FileAccess.open(output + "/solver-diagnostics.json", FileAccess.WRITE).store_string(JSON.stringify(diagnostics, "\t"))
	FileAccess.open(output + "/hair-replay.json", FileAccess.WRITE).store_string(JSON.stringify({"saved_rotation_component_error": replay_error, "samples": 1141, "hair_tracks": 34}))
	if OS.get_cmdline_user_args().has("--return-idle"):
		restore_idle(groom)

func restore_idle(groom: RefCounted) -> void:
	# Codex: explicit exit handoff, not a new equilibrium for production idle.
	# Both complete chains return via the existing front-of-body release path.
	# Keep the original simulation up to 7s; never overwrite its source resource.
	var source := saved_hair
	var clip := Animation.new()
	clip.length = source.length
	clip.resource_name = "thinking_hair_return_preview_Codex"
	for track in source.get_track_count():
		clip.add_track(Animation.TYPE_ROTATION_3D)
		clip.track_set_path(track, source.track_get_path(track))
	pose.apply(0)
	runtime.elapsed = 0
	runtime._apply_pigtail_pose()
	var solver := Strand.new()
	solver.setup(runtime)
	# Seed position AND velocity from the saved source, not from a new idle pose.
	for t in [7.0 - Strand.DT, 7.0]:
		pose.apply(t)
		for track in spring_bones.size():
			runtime.skeleton.set_bone_pose_rotation(spring_bones[track], source.rotation_track_interpolate(track, t))
		solver.seed_from_rig()
	var expected := []
	for f in range(1141):
		var t := float(f) / 120.0
		var u := clampf((t - 8.9) / 0.4, 0.0, 1.0)
		var weight := u * u * u * (u * (u * 6.0 - 15.0) + 10.0)
		if t > 7.0:
			for substep in range(2):
				var st := t - Strand.DT * (1 - substep)
				pose.apply(st)
				runtime.elapsed = st
				runtime._apply_pigtail_pose()
				groom.apply(st)
				solver.step(true, smoothstep(7.0, 8.3, st))
		pose.apply(t)
		runtime.elapsed = t
		runtime._apply_pigtail_pose()
		groom.apply(t)
		var targets := []
		for i in spring_bones:
			targets.append(runtime.skeleton.get_bone_pose_rotation(i).normalized())
		if t > 7.0:
			solver.apply_to_rig()
		var frame := []
		for track in spring_bones.size():
			var q := source.rotation_track_interpolate(track, t).normalized()
			if t > 7.0:
				var solved: Quaternion = runtime.skeleton.get_bone_pose_rotation(spring_bones[track]).normalized()
				q = q.slerp(solved, smoothstep(7.0, 7.15, t)).normalized()
			q = q.slerp(targets[track], weight).normalized()
			clip.rotation_track_insert_key(track, t, q)
			frame.append(q)
		expected.append(frame)
	# Contact projections can introduce short impulses. Filter only the exit
	# window; the held motion and resumed idle remain the original rotations.
	expected = smooth_exit(expected, 12.0)
	# Recheck constraints after temporal filtering: averaging safe poses is
	# not itself collision-safe. Zero incoming velocity avoids a second fall.
	for sigma in [6.0, 5.0]:
		for f in range(841, 1116):
			var t := float(f) / 120.0
			pose.apply(t)
			for track in spring_bones.size():
				runtime.skeleton.set_bone_pose_rotation(spring_bones[track], expected[f][track])
			solver.seed_from_rig()
			solver.seed_from_rig()
			# Small exit-only filter guard band; the independent audit retains
			# the original arm/hair radii. Never enlarge production colliders.
			solver.step(true, 1.0, 0.006 if sigma == 6.0 else 0.002)
			solver.apply_to_rig()
			var correction_weight := smoothstep(7.0, 7.2, t) * (1.0 - smoothstep(8.5, 9.3, t))
			for track in spring_bones.size():
				var before: Quaternion = expected[f][track]
				expected[f][track] = before.slerp(runtime.skeleton.get_bone_pose_rotation(spring_bones[track]).normalized(), correction_weight).normalized()
		expected = smooth_exit(expected, sigma)
	# Measured residual contact is on the outside of the L upper arm (normal
	# predominantly +X). A small smooth release waypoint keeps the whole lower
	# strand on that side until it clears, instead of cutting the corner.
	var release_bone: int = runtime.skeleton.find_bone("MaWei_L_3_1")
	for f in range(841, 960):
		var t := float(f) / 120.0
		pose.apply(t)
		for track in spring_bones.size():
			runtime.skeleton.set_bone_pose_rotation(spring_bones[track], expected[f][track])
		var amount := exp(-pow((t - 7.46) / 0.16, 2)) * smoothstep(7.0, 7.2, t) * (1.0 - smoothstep(7.8, 8.0, t))
		var transform: Transform3D = runtime.skeleton.get_bone_global_pose(release_bone)
		transform.basis = Basis(Vector3.FORWARD * -1.0, deg_to_rad(3.0) * amount) * transform.basis
		runtime.skeleton.set_bone_global_pose(release_bone, transform)
		for track in spring_bones.size():
			expected[f][track] = runtime.skeleton.get_bone_pose_rotation(spring_bones[track]).normalized()
	for f in range(1141):
		for track in spring_bones.size():
			clip.rotation_track_insert_key(track, float(f) / 120.0, expected[f][track])
	var path := output + "/hair_return_preview.tres"
	if ResourceSaver.save(clip, path) != OK:
		push_error("Cannot save return preview")
		quit(1)
		return
	saved_hair = ResourceLoader.load(path, "Animation", ResourceLoader.CACHE_MODE_IGNORE)
	if not validate_clip(saved_hair):
		quit(1)
		return
	var error := 0.0
	for f in range(1141):
		for track in spring_bones.size():
			var q := saved_hair.rotation_track_interpolate(track, float(f) / 120).normalized()
			var wanted: Quaternion = expected[f][track]
			if q.dot(wanted) < 0:
				q = -q
			error = maxf(error, Vector4(q.x-wanted.x, q.y-wanted.y, q.z-wanted.z, q.w-wanted.w).length())
	FileAccess.open(output + "/return-replay.json", FileAccess.WRITE).store_string(JSON.stringify({"samples": 1141, "saved_rotation_component_error": error, "source": source.resource_path, "return_force_ramp_seconds": [7.0, 8.3], "idle_handoff_seconds": [8.9, 9.3], "idle_phase_match_from_seconds": 9.3}))
	if error > 0.00002:
		push_error("Saved return preview differs from authored exit")
		quit(1)
	print("HAIR_RETURN_REPLAY_OK ", error)

func smooth_exit(frames: Array, sigma: float) -> Array:
	var filtered_frames := frames.duplicate(true)
	var radius := ceili(sigma * 3.0)
	for f in range(841, 1116):
		var t := float(f) / 120.0
		var amount := smoothstep(7.0, 7.3, t) * (1.0 - smoothstep(9.0, 9.3, t))
		for track in spring_bones.size():
			var reference: Quaternion = frames[f][track]
			var total := Vector4.ZERO
			for k in range(maxi(840, f - radius), mini(1140, f + radius) + 1):
				var q: Quaternion = frames[k][track]
				if q.dot(reference) < 0:
					q = -q
				total += Vector4(q.x, q.y, q.z, q.w) * exp(-0.5 * pow(float(k - f) / sigma, 2))
			var filtered := Quaternion(total.x, total.y, total.z, total.w).normalized()
			filtered_frames[f][track] = reference.slerp(filtered, amount).normalized()
	return filtered_frames

func validate_clip(clip: Animation) -> bool:
	if clip == null or clip.get_track_count() != 34 or absf(clip.length - 9.5) > 0.00001:
		push_error("Need a 9.5 second, 34-track offline hair bake")
		return false
	for track in range(34):
		if clip.track_get_type(track) != Animation.TYPE_ROTATION_3D or clip.track_get_path(track).get_subname(0) != runtime.skeleton.get_bone_name(spring_bones[track]):
			push_error("Unexpected bone or track type in offline hair bake")
			return false
	return true

func capture(t: float, yaw: int, path: String) -> void:
	if saved_hair == null:
		await build_springs()
	if saved_hair == null or OS.get_cmdline_user_args().has("--audit-only"):
		return
	pose.reset()
	runtime.authored_motion_player.seek(t, true)
	for track in range(34):
		runtime.skeleton.set_bone_pose_rotation(spring_bones[track], saved_hair.rotation_track_interpolate(track, t))
	runtime.model.rotation = runtime.base_model_rotation + Vector3(0, deg_to_rad(yaw), 0)
	var blink := maxf(exp(-pow((t - 2.15) / 0.085, 2)), exp(-pow((t - 6.65) / 0.085, 2)))
	if runtime.expression_ids.has("まばたき"):
		runtime.face_mesh.set_blend_shape_value(runtime.expression_ids["まばたき"], blink * 0.9)
	await process_frame
	await RenderingServer.frame_post_draw
	var pixels := viewport.get_texture().get_image()
	if pixels.is_empty() or pixels.save_png(path) != OK:
		push_error("Physical hair preview image failed")
		quit(1)
