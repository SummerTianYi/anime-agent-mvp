extends SceneTree
## Codex: deterministic, offline exit regression; never operates an OS window.
const Preview = preload("res://lookdev/render_candidate.gd")
const Exit = preload("res://farewell_exit.gd")
class TestRuntime extends Preview.OfflineRuntime:
	var reasons: Array[String] = []
	func _finish_exit(reason: String) -> void:
		if not exit_committed:
			exit_committed = true
			reasons.append(reason)
var failures: Array[String] = []
var checks := 0
var samples := 0
var max_step := 0.0
func check(value: bool, message: String) -> void:
	checks += 1
	if not value and not failures.has(message):
		failures.append(message)
func _init() -> void:
	call_deferred("run")
func run() -> void:
	var r = load("res://main.tscn").instantiate()
	r.set_script(TestRuntime)
	root.add_child(r)
	check(r.has_method("request_exit"), "normal close must use a farewell exit controller")
	if not failures.is_empty():
		print("FAREWELL_RED ", failures)
		quit(1)
		return
	var rig: Skeleton3D = r.skeleton
	check(FileAccess.get_sha256(Exit.PATH) == Exit.SHA256, "exact approved asset")
	check(not r.authored_motion_clips.has("farewell"), "not an ordinary interaction")
	var shape: Mesh = r.face_mesh.mesh
	for scenario in ["idle", "listen", "think", "pirouette", "greet", "speaking", "angry"]:
		r.farewell_exit = Exit.new()
		r.exit_committed = false
		r.reasons.clear()
		r._cancel_authored_motion()
		r._restore_bone_poses()
		r._set_agent_state("idle")
		if scenario in ["idle", "listen", "think", "pirouette"]:
			r._play_authored_motion(StringName(scenario))
			r.authored_motion_player.seek(1.8 if scenario != "think" else 3.7, true)
		elif scenario == "greet":
			r.handle_agent_event("avatar.greet")
			r.action_elapsed = 0.6
			r._apply_action_pose()
		elif scenario == "speaking":
			r._set_agent_state("speaking")
			r._process_speaking_mouth(0.2)
		else:
			r.handle_agent_event("avatar.angry")
		r._process_expressions(0.2)
		r._sync_deform_bone_mirrors()
		r._apply_pigtail_pose()
		var before := []
		for bone in rig.get_bone_count():
			before.append(rig.get_bone_pose_rotation(bone))
		r.request_exit()
		check(r.farewell_exit.closing and not r.exit_committed, "plays before quit " + scenario)
		for bone in rig.get_bone_count():
			check(absf(before[bone].normalized().dot(rig.get_bone_pose_rotation(bone).normalized())) > 0.999999, "no entry snap " + scenario)
		var previous := before.duplicate()
		for frame in 492:
			r._process(1.0 / 120.0)
			var t: float = r.farewell_exit.time
			samples += 1
			if frame % 12 == 0:
				r.request_exit()
				r.handle_agent_event("avatar.reset")
				r._handle_core_event({"type":"voice.state", "state":"recording"})
				r._handle_core_event({"type":"agent.state", "state":"thinking"})
				r._play_authored_motion(&"pirouette")
				r._on_authored_motion_finished(&"think")
				check(is_equal_approx(r.farewell_exit.time, t), "reentrant events do not restart")
			for bone in rig.get_bone_count():
				var q := rig.get_bone_pose_rotation(bone).normalized()
				check(q.is_finite(), "finite all bones")
				var angle := rad_to_deg(2.0 * acos(clampf(absf(previous[bone].normalized().dot(q)), 0.0, 1.0)))
				max_step = maxf(max_step, angle)
				check(angle < 8.0, "bounded entry/motion step " + scenario)
				previous[bone] = q
				if t >= Exit.BLEND_SECONDS and r.farewell_exit.bone_tracks.has(bone):
					var ref: Quaternion = r.farewell_exit.clip.rotation_track_interpolate(r.farewell_exit.bone_tracks[bone], t)
					check(absf(q.dot(ref.normalized())) > 0.999999, "exact accepted bone playback")
			if t >= 1.0 and t <= 3.16:
				check(is_equal_approx(r.face_mesh.get_blend_shape_value(r.expression_ids["笑い"]), 1.0), "closed smile eyes")
				check(is_equal_approx(r.face_mesh.get_blend_shape_value(r.expression_ids["にやり"]), 0.65), "smiling mouth")
			check(r.reasons.is_empty() or t >= 4.1, "no premature quit")
		r._process(0.01)
		check(r.reasons == ["animation_finished"], "finished exactly once " + scenario)
		for i in 10:
			r._process(0.1)
			r.request_exit()
		check(r.reasons.size() == 1, "no duplicate quit")
	check(r.face_mesh.mesh == shape and rig.get_bone_count() == 703, "unchanged model/rig")
	check(FileAccess.get_sha256("res://assets/luotianyi_v4.glb") == Preview.SHA, "official asset hash")
	print("FAREWELL_REGRESSION ", JSON.stringify({"checks":checks,"samples":samples,"max_step_degrees":max_step,"failures":failures}))
	r.free()
	quit(0 if failures.is_empty() else 1)
