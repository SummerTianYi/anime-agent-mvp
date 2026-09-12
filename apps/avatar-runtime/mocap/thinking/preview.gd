extends SceneTree
## Codex: isolated offline engine rendering; never installs a clip or opens Core.
const Review = preload("res://lookdev/render_candidate.gd")
const Pose = preload("res://mocap/thinking/pose.gd")
var runtime: Node
var pose: RefCounted
var viewport: SubViewport
var output: String

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	output = OS.get_environment("THINKING_OUTPUT")
	if output.is_empty() or DirAccess.dir_exists_absolute(output):
		push_error("THINKING_OUTPUT must be a fresh directory")
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
	# Candidate-only .tres is saved alongside evidence, never under assets/motions.
	var clip := Animation.new()
	clip.resource_name = "thinking_thumb_index_preview_Codex"
	clip.length = 9.5
	for i in pose.controlled:
		var track := clip.add_track(Animation.TYPE_ROTATION_3D)
		clip.track_set_path(track, NodePath("%s:%s" % [runtime.get_path_to(runtime.skeleton), runtime.skeleton.get_bone_name(i)]))
	for f in range(286):
		var t := float(f) / 30.0
		pose.apply(t)
		for track in pose.controlled.size():
			clip.rotation_track_insert_key(track, t, runtime.skeleton.get_bone_pose_rotation(pose.controlled[track]))
	assert(ResourceSaver.save(clip, output + "/thinking_preview.tres") == OK)
	var replay: Animation = load(output + "/thinking_preview.tres")
	runtime.authored_motion_player.get_animation_library(&"").add_animation(&"_thinking_preview", replay)
	runtime.authored_motion_player.play(&"_thinking_preview")
	runtime.authored_motion_player.advance(0.0)
	runtime.authored_motion_player.pause()
	for f in range(286):
		var t := float(f) / 30.0
		pose.apply(t)
		var expected: Dictionary = pose.snapshot()
		pose.reset()
		runtime.authored_motion_player.seek(t, true)
		for i in expected:
			var actual: Quaternion = runtime.skeleton.get_bone_pose_rotation(i).normalized()
			var wanted: Quaternion = expected[i].normalized()
			if actual.dot(wanted) < 0.0:
				actual = -actual
			# q and -q encode the same rotation; acos(dot) loses precision near 1.
			var error := Vector4(actual.x - wanted.x, actual.y - wanted.y, actual.z - wanted.z, actual.w - wanted.w).length()
			if error >= 0.00002:
				push_error("Saved clip replay differs: frame=%d bone=%s error=%f expected=%s got=%s" % [f, runtime.skeleton.get_bone_name(i), error, expected[i], runtime.skeleton.get_bone_pose_rotation(i)])
				quit(1)
				return
	print("THINKING_SAVED_CLIP_REPLAY_OK 286 frames")
	var near := OS.get_cmdline_user_args().has("--near")
	if near:
		runtime.camera.position = Vector3(0, 1.26, 1.25)
		runtime.camera.look_at(Vector3(0, 1.26, 0))
	for t in [0.0, 0.7, 1.1, 1.65, 3.7, 5.2, 7.7, 9.5]:
		for yaw in [0, 55, -55, 180]:
			await capture(t, yaw, output + "/t%.2f-y%d.png" % [t, yaw])
		pose.apply(t)
		print("THINKING_CONTACT ", t, " ", pose.contacts())
	if OS.get_cmdline_user_args().has("--animate"):
		DirAccess.make_dir_recursive_absolute(output + "/frames")
		for f in range(286):
			await capture(float(f) / 30.0, 0, output + "/frames/%04d.png" % f)
			if f % 60 == 0:
				print("THINKING_RENDER_FRAME ", f)
	print("THINKING_PREVIEW_DIR ", output)
	quit()

func capture(t: float, yaw: int, path: String) -> void:
	pose.reset()
	runtime.authored_motion_player.seek(t, true)
	runtime.model.rotation = runtime.base_model_rotation + Vector3(0, deg_to_rad(yaw), 0)
	runtime.elapsed = t
	runtime._apply_pigtail_pose()
	var blink := maxf(exp(-pow((t - 2.15) / 0.085, 2)), exp(-pow((t - 6.65) / 0.085, 2)))
	if runtime.expression_ids.has("まばたき"):
		runtime.face_mesh.set_blend_shape_value(runtime.expression_ids["まばたき"], blink * 0.9)
	await process_frame
	await RenderingServer.frame_post_draw
	var pixels := viewport.get_texture().get_image()
	if pixels.is_empty():
		push_error("Empty render")
		quit(1)
		return
	assert(pixels.save_png(path) == OK)
