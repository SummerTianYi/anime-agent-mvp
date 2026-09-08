extends SceneTree
const Review = preload("res://lookdev/render_candidate.gd")
var runtime: Node
var output: String

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	if DisplayServer.get_name() == "headless":
		push_error("A real GPU render is required")
		quit(1)
		return
	root.size = Vector2i(16, 16)
	root.position = Vector2i(-100, -100)
	root.always_on_top = false
	var viewport := SubViewport.new()
	viewport.size = Vector2i(960, 1160)
	viewport.own_world_3d = true
	viewport.transparent_bg = true
	viewport.msaa_3d = Viewport.MSAA_4X
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(viewport)
	runtime = load("res://main.tscn").instantiate()
	runtime.set_script(Review.OfflineRuntime)
	viewport.add_child(runtime)
	runtime.set_model_look_version("1.3")
	var candidate_path := OS.get_environment("LISTEN_REVIEW_PATH")
	if not candidate_path.is_empty():
		var lib: AnimationLibrary = runtime.authored_motion_player.get_animation_library(&"")
		lib.remove_animation(&"listen")
		runtime._load_authored_motion_clip(&"listen", candidate_path, runtime.authored_motion_clips["listen"], lib)
	runtime._play_authored_motion(&"listen")
	runtime.authored_motion_player.advance(0.0)
	output = "user://listen-mocap-v2/" + Time.get_datetime_string_from_system().replace(":", "-")
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(output))
	for time in [0.0, 0.5, 1.0, 1.5, 2.0]:
		for yaw in [0, 90, 180, -90]:
			runtime.model.rotation = runtime.base_model_rotation + Vector3(0, deg_to_rad(yaw), 0)
			runtime.authored_motion_player.seek(time, true)
			runtime._preserve_limb_readability()
			runtime.elapsed = time
			runtime._apply_pigtail_pose()
			await process_frame
			await RenderingServer.frame_post_draw
			var pixels := viewport.get_texture().get_image()
			assert(pixels.get_used_rect().size.y > 400, "Blank/truncated render is not evidence")
			pixels.save_png(output + "/t%.1f-y%d.png" % [time, yaw])
	# Actual forward/hold/reverse player execution, not reordered stills.
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(output + "/frames"))
	runtime._cancel_authored_motion(true)
	runtime.model.rotation = runtime.base_model_rotation
	runtime._set_voice_motion_state("recording")
	for frame in range(181):
		if frame == 105:
			runtime._set_voice_motion_state("transcribing")
		runtime.authored_motion_player.advance(1.0 / 30.0)
		runtime._preserve_limb_readability()
		runtime.elapsed = float(frame) / 30.0
		runtime._apply_pigtail_pose()
		await process_frame
		await RenderingServer.frame_post_draw
		viewport.get_texture().get_image().save_png(output + "/frames/%04d.png" % frame)
	print("LISTEN_REVIEW_DIR ", ProjectSettings.globalize_path(output))
	quit()
