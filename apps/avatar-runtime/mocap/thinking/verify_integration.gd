extends SceneTree
## Codex: production handlers/player/strand ownership, with no Core or user DB.
const Review = preload("res://lookdev/render_candidate.gd")
const Freeze = preload("res://mocap/thinking/freeze.gd")
var failures: Array[String] = []
var checks := 0
func _init() -> void:
	call_deferred("_run")
func check(ok: bool, message: String) -> void:
	checks += 1
	if not ok and not failures.has(message):
		failures.append(message)
func _run() -> void:
	var runtime = load("res://main.tscn").instantiate()
	runtime.set_script(Review.OfflineRuntime)
	root.add_child(runtime)
	check(runtime.authored_motion_clips.has("think"), "thinking registered and available")
	if not failures.is_empty():
		finish(runtime)
		return
	var rig: Skeleton3D = runtime.skeleton
	var player: AnimationPlayer = runtime.authored_motion_player
	var merged := player.get_animation(&"think")
	check(merged.get_track_count() == 108 and is_equal_approx(merged.length, 9.5), "108 tracks / 9.5 seconds")
	check(merged.loop_mode == Animation.LOOP_NONE, "one shot, not repeated task jitter")
	var expected := {}
	for source in Freeze.SOURCES:
		var path: String = OS.get_environment("THINKING_APPROVED_ROOT").path_join(source[0])
		check(FileAccess.get_sha256(path) == source[1], "approved source hash " + source[0])
		var clip := load(path) as Animation
		for track in clip.get_track_count():
			expected[String(clip.track_get_path(track).get_subname(0))] = [clip, track]
	runtime.handle_agent_event("avatar.think")
	# Complete the player's entry blend before deterministic random seeks.
	player.advance(0.3)
	var baseline := {}
	for bone in rig.get_bone_count():
		baseline[bone] = rig.get_bone_pose(bone)
	for frame in range(1141):
		var t := float(frame) / 120.0
		player.seek(t, true)
		runtime.elapsed = 123.4 + t
		runtime._apply_pigtail_pose()
		for track in merged.get_track_count():
			var bone_name := String(merged.track_get_path(track).get_subname(0))
			var bone := rig.find_bone(bone_name)
			check(merged.track_get_type(track) == Animation.TYPE_ROTATION_3D, "no translation/scale tracks")
			var source: Array = expected[bone_name]
			var reference: Quaternion = source[0].rotation_track_interpolate(source[1], t)
			check(merged.rotation_track_interpolate(track, t).is_equal_approx(reference), "source parity " + bone_name)
			if not bone_name.begins_with("MaWei_") or (t >= 0.2 and t <= 9.3):
				check(rotation_equal(rig.get_bone_pose_rotation(bone), reference), "production playback parity " + bone_name)
		for bone in rig.get_bone_count():
			check(rig.get_bone_pose_position(bone).is_equal_approx(baseline[bone].origin), "bone positions unchanged")
			check(rig.get_bone_pose_scale(bone).is_equal_approx(baseline[bone].basis.get_scale()), "bone scales unchanged")
			if not expected.has(String(rig.get_bone_name(bone))):
				check(rig.get_bone_pose(bone).is_equal_approx(baseline[bone]), "unowned bones unchanged")
	# Last 0.2s must land on the live idle clock, not the preview's zero clock.
	var end_hair := hair_snapshot(runtime)
	check(not rotation_equal(Quaternion.IDENTITY, Quaternion(Vector3.RIGHT, 0.01)), "negative control rejects changed rotation")
	runtime._on_authored_motion_finished(&"think")
	player.advance(0.0)
	runtime._apply_pigtail_pose()
	check(hair_equal(end_hair, hair_snapshot(runtime)), "all 34 strands hand off to current idle phase")
	check(runtime.authored_motion_name == &"idle", "completed action returns to idle")
	runtime._set_agent_state("thinking")
	check(runtime.authored_motion_name == &"think", "automatic thinking entry")
	player.seek(3.7, true)
	runtime._set_agent_state("thinking")
	check(is_equal_approx(player.current_animation_position, 3.7), "duplicate states do not restart")
	runtime.handle_agent_event("avatar.think")
	check(is_equal_approx(player.current_animation_position, 3.7), "duplicate menu click does not restart")
	runtime._set_agent_state("speaking")
	check(runtime.agent_state == "speaking" and runtime.authored_motion_name == &"think", "reply state is immediate; body finishes naturally")
	runtime._set_voice_motion_state("recording")
	check(runtime.authored_motion_name == &"listen", "recording preempts thinking")
	runtime._set_agent_state("thinking")
	check(runtime.authored_motion_name == &"listen", "automatic thinking does not steal recording")
	runtime._set_voice_motion_state("idle")
	for t in [0.01, 1.3, 3.7, 7.8, 9.49]:
		runtime.handle_agent_event("avatar.think")
		player.seek(t, true)
		runtime._apply_pigtail_pose()
		runtime.handle_agent_event("avatar.reset")
		player.advance(0.0)
		runtime._apply_pigtail_pose()
		check(runtime.authored_motion_name == &"idle" and hair_equal(hair_snapshot(runtime), end_hair), "reset releases hair at " + str(t))
	var info: Dictionary = runtime.authored_motion_clips["think"]
	runtime._set_agent_state("idle")
	runtime.handle_agent_event("avatar.nod")
	runtime._set_agent_state("thinking")
	check(runtime.action_name == "nod", "automatic thinking does not steal manual procedural action")
	runtime.handle_agent_event("avatar.reset")
	runtime.authored_motion_clips.erase("think")
	runtime._set_agent_state("idle")
	runtime._set_agent_state("thinking")
	check(runtime.authored_motion_name == &"idle", "missing optional local asset is safe")
	runtime.authored_motion_clips["think"] = info
	check(rig.get_bone_count() == 703 and runtime.face_mesh.mesh.get_blend_shape_count() == 48, "model structure unchanged")
	check(FileAccess.get_sha256("res://assets/luotianyi_v4.glb") == Review.SHA, "official asset unchanged")
	finish(runtime)
func hair_snapshot(runtime: Node) -> Array:
	var result := []
	for chain in runtime.pigtail_chains:
		for bone in chain:
			result.append(runtime.skeleton.get_bone_pose_rotation(bone))
	return result
func hair_equal(a: Array, b: Array) -> bool:
	for i in a.size():
		if not a[i].is_equal_approx(b[i]):
			return false
	return true
static func rotation_equal(actual: Quaternion, wanted: Quaternion) -> bool:
	actual = actual.normalized()
	wanted = wanted.normalized()
	if actual.dot(wanted) < 0.0:
		actual = -actual # q/-q represent the same rotation, as in preview.gd.
	return Vector4(actual.x - wanted.x, actual.y - wanted.y, actual.z - wanted.z, actual.w - wanted.w).length() < 0.00002
func finish(runtime: Node) -> void:
	var report := {"owner": "Codex", "checks": checks, "frames_120hz": 1141, "failures": failures}
	print("THINKING_INTEGRATION ", JSON.stringify(report))
	var path := OS.get_environment("THINKING_REPORT")
	if not path.is_empty() and not FileAccess.file_exists(path):
		var file := FileAccess.open(path, FileAccess.WRITE)
		file.store_string(JSON.stringify(report, "  "))
	runtime.free()
	quit(0 if failures.is_empty() else 1)
