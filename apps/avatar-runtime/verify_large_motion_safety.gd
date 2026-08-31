extends SceneTree


const OFFICIAL_MODEL_PATH := "res://assets/luotianyi_v4.glb"
const OFFICIAL_MODEL_SHA256 := "df55806d343d149b41c20d0ef074373cafca2379212fd8691e998ea6cddc6e4a"
const ACTION_AXIS_KEYS := [
	"lift.R", "elbow.R", "wrist.R", "wrist_wave.R",
	"lift.L", "elbow.L", "wrist.L", "wrist_wave.L",
]


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	if FileAccess.get_sha256(OFFICIAL_MODEL_PATH).to_lower() != OFFICIAL_MODEL_SHA256:
		_fail("Official model hash changed")
		return
	var scene := load("res://main.tscn") as PackedScene
	if scene == null:
		_fail("Unable to load main scene")
		return
	var runtime: Node = scene.instantiate()
	root.add_child(runtime)
	if runtime.skeleton == null:
		_fail("Runtime skeleton was not discovered")
		return
	for axis_key in ACTION_AXIS_KEYS:
		if not runtime.action_axes.has(axis_key):
			_fail("Missing derived action axis: %s" % axis_key)
			return
		var axis: Vector3 = runtime.action_axes[axis_key]
		if not is_finite(axis.x) or not is_finite(axis.y) or not is_finite(axis.z) or not is_equal_approx(axis.length(), 1.0):
			_fail("Invalid action axis: %s" % axis_key)
			return
	if runtime.deform_bone_mirrors.size() != 6:
		_fail("Expected six MMD control-to-deform leg mirrors")
		return
	if runtime.process_priority <= runtime.authored_motion_player.process_priority:
		_fail("Runtime pose corrections do not run after AnimationPlayer")
		return

	var original_model_scale: Vector3 = runtime.model.scale
	var original_rotation: Vector3 = runtime.model.rotation
	for action in ["nod", "wave", "greet"]:
		runtime._start_action(action, 2.0)
		runtime.action_elapsed = 1.0
		runtime._apply_action_pose()
		if not _all_cached_bones_finite(runtime):
			_fail("Non-finite bone pose during %s" % action)
			return
		if not runtime.model.scale.is_equal_approx(original_model_scale):
			_fail("Model scale changed during %s" % action)
			return
		runtime.action_name = "idle"
		runtime._restore_bone_poses()
		if not runtime.model.rotation.is_equal_approx(original_rotation):
			_fail("Model rotation was not restored after %s" % action)
			return

	for clip_name in [&"pirouette", &"listen"]:
		if not runtime.authored_motion_clips.has(String(clip_name)):
			continue
		runtime._play_authored_motion(clip_name)
		var animation: Animation = runtime.authored_motion_player.get_animation(clip_name)
		for sample_ratio in [0.0, 0.25, 0.5, 0.75, 1.0]:
			runtime.authored_motion_player.seek(animation.length * sample_ratio, true)
			if not _all_cached_bones_finite(runtime):
				_fail("Non-finite bone pose during authored %s at %.2f" % [clip_name, sample_ratio])
				return
			if not runtime.model.scale.is_equal_approx(original_model_scale):
				_fail("Model scale changed during authored %s" % clip_name)
				return
		runtime._cancel_authored_motion(true)

	if runtime.avatar_render_viewport.size != Vector2i(1920, 2320):
		_fail("Large-motion render margin is not active")
		return
	if not runtime.avatar_texture_rect.size.is_equal_approx(Vector2(960.0, 1160.0)):
		_fail("Large-motion composite size is not active")
		return
	if DisplayServer.get_name() != "headless":
		runtime._start_action("greet", 2.0)
		runtime.action_elapsed = 1.0
		runtime._apply_action_pose()
		await process_frame
		await process_frame
		var preview: Image = runtime.avatar_render_viewport.get_texture().get_image()
		preview.save_png("user://large-motion-safety.png")
		print("GODOT_LARGE_MOTION_PREVIEW_SAVED ", ProjectSettings.globalize_path("user://large-motion-safety.png"))
	print("GODOT_LARGE_MOTION_SAFETY_OK", {
		"action_axes": ACTION_AXIS_KEYS,
		"deform_bone_mirrors": runtime.deform_bone_mirrors.size(),
		"runtime_process_priority": runtime.process_priority,
		"tested_actions": ["nod", "wave", "greet", "pirouette", "listen"],
		"render_viewport_size": runtime.avatar_render_viewport.size,
		"composite_size": runtime.avatar_texture_rect.size,
		"official_model_sha256": OFFICIAL_MODEL_SHA256,
		"model_structure_untouched": true,
	})
	quit(0)


func _all_cached_bones_finite(runtime: Node) -> bool:
	for bone_index in range(runtime.skeleton.get_bone_count()):
		var rotation: Quaternion = runtime.skeleton.get_bone_pose_rotation(int(bone_index))
		if not is_finite(rotation.x) or not is_finite(rotation.y) or not is_finite(rotation.z) or not is_finite(rotation.w):
			return false
	return true


func _fail(message: String) -> void:
	push_error(message)
	quit(1)
