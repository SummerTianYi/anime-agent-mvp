extends SceneTree


const REGISTRY_PATH := "res://motion_registry.json"
const EXPECTED_BONE_COUNT := 751


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var registry_data: Variant = JSON.parse_string(FileAccess.get_file_as_string(REGISTRY_PATH))
	if registry_data is not Dictionary or registry_data.get("clips", null) is not Array:
		_fail("Motion registry is invalid")
		return
	var results: Array[Dictionary] = []
	for clip_data in registry_data.get("clips", []):
		if clip_data is not Dictionary:
			_fail("Motion registry contains a non-dictionary clip")
			return
		var result := _verify_clip(clip_data)
		if result.is_empty():
			return
		results.append(result)
	if results.size() != 2:
		_fail("Expected two motion clips, found %d" % results.size())
		return
	print("GODOT_MOTION_ASSETS_OK", {
		"registry": REGISTRY_PATH,
		"clips": results,
	})
	quit(0)


func _verify_clip(clip_data: Dictionary) -> Dictionary:
	var clip_id := str(clip_data.get("id", ""))
	var motion_path := str(clip_data.get("path", ""))
	if not ResourceLoader.exists(motion_path):
		_fail("Motion asset is missing: %s" % motion_path)
		return {}
	var packed_scene := load(motion_path) as PackedScene
	if packed_scene == null:
		_fail("Motion asset did not import as PackedScene: %s" % motion_path)
		return {}
	var motion_root := packed_scene.instantiate()
	root.add_child(motion_root)
	var player := _find_animation_player(motion_root)
	var skeleton := _find_skeleton(motion_root)
	if player == null or skeleton == null:
		_fail("Imported motion is missing AnimationPlayer or Skeleton3D: %s" % clip_id)
		return {}
	if skeleton.get_bone_count() != EXPECTED_BONE_COUNT:
		_fail("Unexpected skeleton bone count for %s: %d" % [clip_id, skeleton.get_bone_count()])
		return {}

	var playable_names: Array[StringName] = []
	for name in player.get_animation_list():
		if name != &"RESET":
			playable_names.append(name)
	if playable_names.size() != 1:
		_fail("Expected one playable animation for %s, found %s" % [clip_id, playable_names])
		return {}
	var animation_name: StringName = playable_names[0]
	var animation := player.get_animation(animation_name)
	if animation == null or animation.length < float(clip_data.get("minimum_duration", 0.1)):
		_fail("Motion duration is too short for %s" % clip_id)
		return {}

	var chest_index := skeleton.find_bone("上半身2")
	player.play(animation_name)
	player.seek(0.0, true)
	var start_rotation := skeleton.get_bone_pose_rotation(chest_index)
	player.seek(float(clip_data.get("sample_seconds", 1.0)), true)
	var sampled_rotation := skeleton.get_bone_pose_rotation(chest_index)
	var rotation_delta := start_rotation.angle_to(sampled_rotation)
	if rotation_delta < 0.01:
		_fail("Animation sampling did not change the chest pose for %s" % clip_id)
		return {}
	var result := {
		"id": clip_id,
		"path": motion_path,
		"duration": animation.length,
		"tracks": animation.get_track_count(),
		"bones": skeleton.get_bone_count(),
		"chest_delta_radians": rotation_delta,
	}
	motion_root.queue_free()
	return result


func _find_animation_player(node: Node) -> AnimationPlayer:
	if node is AnimationPlayer:
		return node as AnimationPlayer
	for child in node.get_children():
		var found := _find_animation_player(child)
		if found != null:
			return found
	return null


func _find_skeleton(node: Node) -> Skeleton3D:
	if node is Skeleton3D:
		return node as Skeleton3D
	for child in node.get_children():
		var found := _find_skeleton(child)
		if found != null:
			return found
	return null


func _fail(message: String) -> void:
	push_error(message)
	quit(1)
