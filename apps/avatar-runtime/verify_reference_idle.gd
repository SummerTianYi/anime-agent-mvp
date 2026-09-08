extends SceneTree

## Codex 2026-09-08: regression for the conservative A-pose idle, not a
## general collision/cloth-physics acceptance test.
const MODEL_SHA := "df55806d343d149b41c20d0ef074373cafca2379212fd8691e998ea6cddc6e4a"
const IDLE_SHA := "5cf15a1d3e657cf76e5f58e33c9d3593a14494b89817ad2a910d57cabf9d433a"
var failure := ""


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	OS.set_environment("AGENT_CORE_WS_URL", "ws://127.0.0.1:1/ws")
	var runtime: Node = load("res://main.tscn").instantiate()
	root.add_child(runtime)
	runtime.set_process(false)
	var rig: Skeleton3D = runtime.skeleton
	var player: AnimationPlayer = runtime.authored_motion_player
	player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	var arms: Array[int] = []
	for side in ["L", "R"]:
		var shoulder := rig.find_bone("肩." + side)
		if shoulder < 0:
			_fail("Missing shoulder chain")
			return
		arms.append(shoulder)
	var cursor := 0
	while cursor < arms.size():
		arms.append_array(rig.get_bone_children(arms[cursor]))
		cursor += 1
	if FileAccess.get_sha256("res://assets/luotianyi_v4.glb") != MODEL_SHA \
			or FileAccess.get_sha256("res://assets/motions/luotianyi_idle.glb") != IDLE_SHA:
		_fail("Official model or original mocap asset changed")
		return
	runtime._play_authored_motion(&"idle")
	var animation := player.get_animation(&"idle")
	# Sequential sampling includes two full loops; do not just inspect one pose.
	for frame in range(750):
		player.advance(1.0 / 30.0)
		if not _check_arms(rig, arms):
			_fail("Idle frame %d: %s" % [frame, failure])
			return
	for event in ["avatar.pirouette", "avatar.listen", "avatar.wave", "avatar.greet"]:
		runtime.handle_agent_event(event)
		var expected_action: String = event.trim_prefix("avatar.")
		if runtime.action_name != expected_action:
			_fail("Interaction was not entered: " + event)
			return
		if runtime.authored_motion_active:
			if not _verify_original_interaction(runtime, expected_action):
				_fail("Non-idle clip was modified: " + expected_action)
				return
			player.advance(1.1)
		else:
			runtime.action_elapsed = 0.6
			runtime._apply_action_pose()
		if _check_arms(rig, arms):
			_fail("Interaction did not move either arm: " + event)
			return
		runtime.handle_agent_event("avatar.reset")
		player.advance(0.5)
		if runtime.authored_motion_name != &"idle" or not _check_arms(rig, arms):
			_fail("Return from %s: %s" % [event, failure])
			return
		# Also exercise natural completion, not just the explicit reset shortcut.
		runtime.handle_agent_event(event)
		for step in range(285):
			player.advance(1.0 / 30.0)
			runtime._process(1.0 / 30.0)
		if runtime.authored_motion_name != &"idle" or not _check_arms(rig, arms):
			_fail("Natural completion from %s: %s" % [event, failure])
			return
	print("GODOT_REFERENCE_IDLE_OK", {
		"arm_chain_bones": arms.size(), "sampled_frames": 750,
		"duration": animation.length, "original_assets_unchanged": true,
		"scope": "reference arms only; no universal collision guarantee",
	})
	if DisplayServer.get_name() != "headless":
		await _render_review(runtime)
	quit(0)


func _verify_original_interaction(runtime: Node, clip_id: String) -> bool:
	var config: Dictionary = runtime.authored_motion_clips[clip_id].duplicate(true)
	if bool(config.get("relaxed_arms", false)):
		return false
	var original := AnimationLibrary.new()
	runtime._load_authored_motion_clip(StringName(clip_id), str(config["path"]), config, original)
	var before := original.get_animation(StringName(clip_id))
	var after: Animation = runtime.authored_motion_player.get_animation(StringName(clip_id))
	if before == null or before.get_track_count() != after.get_track_count():
		return false
	for track in range(before.get_track_count()):
		if before.track_get_path(track) != after.track_get_path(track) \
				or before.track_get_type(track) != after.track_get_type(track) \
				or before.track_get_key_count(track) != after.track_get_key_count(track):
			return false
		for key in range(before.track_get_key_count(track)):
			if before.track_get_key_time(track, key) != after.track_get_key_time(track, key) \
					or before.track_get_key_value(track, key) != after.track_get_key_value(track, key):
				return false
	return true


func _render_review(runtime: Node) -> void:
	var output_dir := "user://reference-idle-2026-09-08"
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(output_dir))
	var player: AnimationPlayer = runtime.authored_motion_player
	# Use the actual visible runtime viewport, same camera/look for every view.
	var sheet := Image.create(384 * 5, 464, false, Image.FORMAT_RGBA8)
	var reference_front: Image
	var yaw_angles := [0.0, -45.0, 45.0, 90.0, 180.0]
	for view in range(yaw_angles.size()):
		runtime.model.rotation = runtime.base_model_rotation + Vector3(0.0, deg_to_rad(yaw_angles[view]), 0.0)
		player.seek(2.0, true)
		runtime.elapsed = 2.0
		runtime._apply_pigtail_pose()
		await process_frame
		await RenderingServer.frame_post_draw
		var shot: Image = runtime.avatar_render_viewport.get_texture().get_image()
		if view == 0:
			reference_front = shot.duplicate()
		shot.save_png(output_dir + "/reference-%d.png" % view)
		shot.resize(384, 464, Image.INTERPOLATE_LANCZOS)
		sheet.blit_rect(shot, Rect2i(0, 0, 384, 464), Vector2i(view * 384, 0))
	sheet.save_png(output_dir + "/reference-five-views.png")
	# Re-load the untouched clip without the registry fallback, in memory only.
	var library := AnimationLibrary.new()
	runtime._load_authored_motion_clip(&"original", "res://assets/motions/luotianyi_idle.glb", {
		"bone_layer": "upper_body", "loop": true,
	}, library)
	player.add_animation_library(&"review", library)
	runtime.model.rotation = runtime.base_model_rotation
	runtime.skeleton.reset_bone_poses()
	player.play(&"review/original", 0.0)
	player.seek(2.0, true)
	runtime._apply_pigtail_pose()
	await process_frame
	await RenderingServer.frame_post_draw
	var original: Image = runtime.avatar_render_viewport.get_texture().get_image()
	original.save_png(output_dir + "/original-front.png")
	var crop := reference_front.get_used_rect().merge(original.get_used_rect()).grow(24)
	crop = crop.intersection(Rect2i(Vector2i.ZERO, original.get_size()))
	var comparison := Image.create(crop.size.x * 2, crop.size.y, false, Image.FORMAT_RGBA8)
	comparison.blit_rect(original, crop, Vector2i.ZERO)
	comparison.blit_rect(reference_front, crop, Vector2i(crop.size.x, 0))
	comparison.save_png(output_dir + "/before-after.png")
	print("REFERENCE_IDLE_REVIEW_DIR ", ProjectSettings.globalize_path(output_dir))


func _check_arms(rig: Skeleton3D, arms: Array[int]) -> bool:
	for index in arms:
		var expected := rig.get_bone_rest(index)
		var name := rig.get_bone_name(index)
		if name == "腕.L" or name == "腕.R":
			var angle := 48.0 if name == "腕.L" else -48.0
			expected.basis = expected.basis * Basis(Quaternion(Vector3.RIGHT, deg_to_rad(angle)))
		if not rig.get_bone_pose(index).is_equal_approx(expected):
			failure = "Arm bone did not retain reference pose: " + rig.get_bone_name(index)
			return false
	return true


func _fail(message: String) -> void:
	push_error(message)
	quit(1)
