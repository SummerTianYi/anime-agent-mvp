extends SceneTree


const REQUIRED_PIROUETTE_BONES := [
	"センター", "上半身", "上半身2", "首", "頭",
	"肩.L", "腕.L", "ひじ.L", "手首.L",
	"肩.R", "腕.R", "ひじ.R", "手首.R",
	"足.L", "ひざ.L", "足首.L",
	"足.R", "ひざ.R", "足首.R",
]
const LOWER_BODY_BONES := [
	"センター", "下半身", "足.L", "ひざ.L", "足首.L", "足.R", "ひざ.R", "足首.R",
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
	if not runtime.authored_motion_clips.has("idle") or not runtime.authored_motion_clips.has("pirouette") or not runtime.authored_motion_clips.has("listen"):
		_fail("Runtime motion registry is missing idle, pirouette or listen")
		return
	var runtime_skeleton := runtime.skeleton as Skeleton3D
	var motion_player := runtime.authored_motion_player as AnimationPlayer
	var chest_index: int = runtime_skeleton.find_bone("上半身2")
	if runtime.pigtail_chains.size() != 2:
		_fail("Expected two complete pigtail chains")
		return
	for chain in runtime.pigtail_chains:
		if chain.size() != 17:
			_fail("Expected 17 bones in each pigtail chain, found %d" % chain.size())
			return
		for bone_index in chain:
			if not runtime._bone_in_motion_layer(bone_index, "upper_body"):
				_fail("Pigtail bone was not classified as upper body: %s" % runtime_skeleton.get_bone_name(bone_index))
				return
			if runtime._bone_in_motion_layer(bone_index, "lower_body"):
				_fail("Pigtail bone leaked into the lower-body layer: %s" % runtime_skeleton.get_bone_name(bone_index))
				return

	runtime._cancel_authored_motion()
	runtime._restore_bone_poses()
	var pigtail_root: int = runtime.pigtail_chains[0][0]
	var pigtail_tip: int = runtime.pigtail_chains[0][-1]
	runtime.elapsed = 0.0
	runtime._apply_pigtail_pose()
	var pigtail_root_start := runtime_skeleton.get_bone_pose_rotation(pigtail_root)
	var pigtail_tip_start := runtime_skeleton.get_bone_pose_rotation(pigtail_tip)
	runtime.elapsed = 1.3
	runtime._apply_pigtail_pose()
	var pigtail_root_delta: float = pigtail_root_start.angle_to(runtime_skeleton.get_bone_pose_rotation(pigtail_root))
	var pigtail_tip_delta: float = pigtail_tip_start.angle_to(runtime_skeleton.get_bone_pose_rotation(pigtail_tip))
	if pigtail_root_delta < 0.001 or pigtail_tip_delta < 0.0001:
		_fail("Pigtail secondary motion did not reach both root and tip")
		return

	runtime._play_authored_motion(&"idle")
	motion_player.seek(0.0, true)
	var idle_start: Quaternion = runtime_skeleton.get_bone_pose_rotation(chest_index)
	motion_player.seek(2.0, true)
	var idle_sample: Quaternion = runtime_skeleton.get_bone_pose_rotation(chest_index)
	var idle_delta := idle_start.angle_to(idle_sample)
	var idle_animation := motion_player.get_animation(&"idle") as Animation
	var idle_bones := _animated_bones(idle_animation)
	for bone_name in LOWER_BODY_BONES:
		if idle_bones.has(bone_name):
			_fail("Upper-body idle leaked onto lower-body bone: %s" % bone_name)
			return
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
	var animated_bones := _animated_bones(pirouette_animation)
	for bone_name in REQUIRED_PIROUETTE_BONES:
		if not animated_bones.has(bone_name):
			_fail("Pirouette runtime animation is missing core bone: %s" % bone_name)
			return

	runtime._handle_core_event({"type": "voice.state", "state": "recording"})
	if not runtime.voice_recording_active or runtime.authored_motion_name != &"listen":
		_fail("Voice recording did not start the listen motion")
		return
	var listen_animation := motion_player.get_animation(&"listen") as Animation
	motion_player.seek(1.0, true)
	runtime._on_authored_motion_finished(&"listen")
	if not runtime.authored_motion_active or runtime.authored_motion_name != &"listen":
		_fail("Listen motion did not hold its final pose while recording")
		return
	runtime._handle_core_event({"type": "voice.state", "state": "transcribing"})
	if not runtime.authored_motion_returning or runtime.authored_motion_name != &"listen":
		_fail("Listen must reverse its safe entry path after recording")
		return
	motion_player.advance(listen_animation.length + 0.1)
	if runtime.voice_recording_active or runtime.authored_motion_name != &"idle":
		_fail("Listen motion did not return to idle after recording")
		return

	if not runtime.authored_motion_active or runtime.authored_motion_name != &"idle":
		_fail("Runtime did not return to authored idle after interaction motion")
		return
	print("GODOT_MOTION_RUNTIME_OK", {
		"clips": runtime.authored_motion_clips.keys(),
		"static_model_preserved": runtime.model.name == "LuoTianyi",
		"idle_duration": idle_animation.length,
		"idle_tracks": idle_animation.get_track_count(),
		"idle_lower_body_tracks": 0,
		"idle_delta_radians": idle_delta,
		"pirouette_duration": pirouette_animation.length,
		"pirouette_tracks": pirouette_animation.get_track_count(),
		"pirouette_delta_radians": pirouette_delta,
		"listen_duration": listen_animation.length,
		"listen_voice_hold": true,
		"pigtail_chain_lengths": runtime.pigtail_chains.map(func(chain: Array) -> int: return chain.size()),
		"pigtail_root_delta_radians": pigtail_root_delta,
		"pigtail_tip_delta_radians": pigtail_tip_delta,
		"returned_to_idle": true,
	})
	quit(0)


func _animated_bones(animation: Animation) -> Dictionary:
	var animated_bones: Dictionary = {}
	for track_index in range(animation.get_track_count()):
		var track_path := animation.track_get_path(track_index)
		if track_path.get_subname_count() > 0:
			animated_bones[str(track_path.get_subname(track_path.get_subname_count() - 1))] = true
	return animated_bones


func _fail(message: String) -> void:
	push_error(message)
	quit(1)
