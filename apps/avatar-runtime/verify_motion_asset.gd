extends SceneTree


const REGISTRY_PATH := "res://motion_registry.json"
const EXPECTED_BONE_COUNT := 751
# Codex: validate each installed format; thinking and farewell are not listening clips.
const EXPECTED_IDS := ["idle", "pirouette", "listen", "think", "farewell"]
const NATIVE_CONTRACTS := {
	"listen": {"tracks": 74, "rotations": 74, "shapes": 0, "keys": 61},
	"think": {"tracks": 108, "rotations": 108, "shapes": 0, "sha256": "7637d1210c52fd4fcaff4d40f517eab578a9cfc4c9dec46b1e75c370a56e9f09"},
	"farewell": {"tracks": 39, "rotations": 37, "shapes": 2, "sha256": "aa9684cdf8e8927a601bbed3c47bf6abc38fc7dc4b85b8432f0239889542bea7"},
}


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var registry_data: Variant = JSON.parse_string(FileAccess.get_file_as_string(REGISTRY_PATH))
	if registry_data is not Dictionary or registry_data.get("clips", null) is not Array:
		_fail("Motion registry is invalid")
		return
	var results: Array[Dictionary] = []
	var seen: Array[String] = []
	for clip_data in registry_data.get("clips", []):
		if clip_data is not Dictionary:
			_fail("Motion registry contains a non-dictionary clip")
			return
		var clip_id := str(clip_data.get("id", ""))
		if clip_id not in EXPECTED_IDS or clip_id in seen:
			_fail("Unknown or duplicate motion id: " + clip_id)
			return
		seen.append(clip_id)
		var result := _verify_clip(clip_data)
		if result.is_empty():
			return
		results.append(result)
	if results.size() != EXPECTED_IDS.size():
		_fail("Expected five installed motion clips, found %d" % results.size())
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
	var resource: Resource = load(motion_path)
	if resource is Animation:
		var native := resource as Animation
		var contract: Dictionary = NATIVE_CONTRACTS.get(clip_id, {})
		if contract.is_empty() or native.length < float(clip_data.get("minimum_duration", 0.1)) or native.get_track_count() != int(contract.tracks):
			_fail("Native clip has invalid duration or track count: " + clip_id)
			return {}
		if contract.has("sha256") and FileAccess.get_sha256(motion_path) != contract.sha256:
			_fail("Approved native clip hash mismatch: " + clip_id)
			return {}
		var rotations := 0
		var shapes := 0
		for i in range(native.get_track_count()):
			if native.track_get_type(i) == Animation.TYPE_ROTATION_3D:
				rotations += 1
			elif native.track_get_type(i) == Animation.TYPE_BLEND_SHAPE:
				shapes += 1
			else:
				_fail("Unexpected translation/scale/value track: " + clip_id)
				return {}
			if native.track_get_key_count(i) < 2 or (contract.has("keys") and native.track_get_key_count(i) != int(contract.keys)):
				_fail("Invalid native key count: " + clip_id)
				return {}
		if rotations != int(contract.rotations) or shapes != int(contract.shapes):
			_fail("Native rotation/expression track contract mismatch: " + clip_id)
			return {}
		return {"id": clip_id, "path": motion_path, "duration": native.length, "tracks": native.get_track_count(), "format": "runtime-native; per-motion playback guards required"}
	if NATIVE_CONTRACTS.has(clip_id):
		_fail("Native motion was replaced with a non-Animation resource: " + clip_id)
		return {}
	var packed_scene := resource as PackedScene
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
