extends SceneTree


const REQUIRED_PIROUETTE_BONES := [
	"センター", "上半身", "上半身2", "首", "頭",
	"肩.L", "腕.L", "ひじ.L", "手首.L",
	"肩.R", "腕.R", "ひじ.R", "手首.R",
	"足.L", "ひざ.L", "足首.L",
	"足.R", "ひざ.R", "足首.R",
]


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var scene := load("res://main.tscn") as PackedScene
	if scene == null:
		_fail("Unable to load main scene")
		return
	var runtime: Node = scene.instantiate()
	root.add_child(runtime)
	if runtime.authored_motion_player == null or runtime.skeleton == null:
		_fail("Runtime motion registry was not prepared")
		return
	if not runtime.authored_motion_clips.has("idle") or not runtime.authored_motion_clips.has("pirouette"):
		_fail("Runtime motion registry is missing idle or pirouette")
		return
	var runtime_skeleton := runtime.skeleton as Skeleton3D
	var motion_player := runtime.authored_motion_player as AnimationPlayer
	var chest_index: int = runtime_skeleton.find_bone("上半身2")

	runtime._play_authored_motion(&"idle")
	motion_player.seek(0.0, true)
	var idle_start: Quaternion = runtime_skeleton.get_bone_pose_rotation(chest_index)
	motion_player.seek(2.0, true)
	var idle_sample: Quaternion = runtime_skeleton.get_bone_pose_rotation(chest_index)
	var idle_delta := idle_start.angle_to(idle_sample)
	var idle_animation := motion_player.get_animation(&"idle") as Animation
	if idle_delta < 0.01 or idle_animation.loop_mode != Animation.LOOP_LINEAR:
		_fail("Idle motion is not visibly sampled or configured to loop")
		return
	motion_player.advance(idle_animation.length + 0.1)
	if not runtime.authored_motion_active or runtime.authored_motion_name != &"idle":
		_fail("Idle motion did not remain active across a full loop")
		return

	runtime.handle_agent_event("avatar.pirouette")
	motion_player.seek(0.0, true)
	var pirouette_start: Quaternion = runtime_skeleton.get_bone_pose_rotation(chest_index)
	motion_player.seek(1.0, true)
	var pirouette_sample: Quaternion = runtime_skeleton.get_bone_pose_rotation(chest_index)
	var pirouette_delta := pirouette_start.angle_to(pirouette_sample)
	if runtime.authored_motion_name != &"pirouette" or pirouette_delta < 0.01:
		_fail("Pirouette did not interrupt idle and drive the static avatar skeleton")
		return
	var pirouette_animation := motion_player.get_animation(&"pirouette") as Animation
	var animated_bones: Dictionary = {}
	for track_index in range(pirouette_animation.get_track_count()):
		var track_path := pirouette_animation.track_get_path(track_index)
		if track_path.get_subname_count() > 0:
			animated_bones[str(track_path.get_subname(track_path.get_subname_count() - 1))] = true
	for bone_name in REQUIRED_PIROUETTE_BONES:
		if not animated_bones.has(bone_name):
			_fail("Pirouette runtime animation is missing core bone: %s" % bone_name)
			return

	runtime._cancel_authored_motion(true)
	if not runtime.authored_motion_active or runtime.authored_motion_name != &"idle":
		_fail("Runtime did not return to authored idle after interaction motion")
		return
	print("GODOT_MOTION_RUNTIME_OK", {
		"clips": runtime.authored_motion_clips.keys(),
		"static_model_preserved": runtime.model.name == "LuoTianyi",
		"idle_duration": idle_animation.length,
		"idle_tracks": idle_animation.get_track_count(),
		"idle_delta_radians": idle_delta,
		"pirouette_duration": pirouette_animation.length,
		"pirouette_tracks": pirouette_animation.get_track_count(),
		"pirouette_delta_radians": pirouette_delta,
		"returned_to_idle": true,
	})
	quit(0)


func _fail(message: String) -> void:
	push_error(message)
	quit(1)
