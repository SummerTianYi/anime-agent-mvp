extends SceneTree

## Codex: reference-guided FK, not new capture. Refine the accepted v1 endpoint
## only at upper torso/right shoulder; preserve its smooth joint-space paths.
## Each joint follows one fixed local rotation arc: no changing elbow pole,
## repeated wrist aiming or frame-by-frame shoulder-frame reconstruction.
const SOURCE := "res://assets/motions/listen_reference_fk_v1.tres"
const SOURCE_SHA := "38e8e82cccb596d929b1fd764f581d36afc96c54c3404c10ba319431bd30a7e4"
const Review = preload("res://lookdev/render_candidate.gd")

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	var output := OS.get_environment("LISTEN_OUTPUT")
	if output.is_empty():
		output = "res://assets/motions/listen_reference_fk_v2.tres"
	if FileAccess.file_exists(output) or FileAccess.file_exists(output + ".json"):
		push_error("Refusing to overwrite a motion or provenance file")
		quit(1)
		return
	if FileAccess.get_sha256(SOURCE) != SOURCE_SHA:
		push_error("Reviewed endpoint asset missing or changed; do not guess endpoints")
		quit(1)
		return
	var original := load(SOURCE) as Animation
	if original == null or original.get_track_count() != 74:
		quit(1)
		return
	# Solve only the requested endpoint adjustment on the actual runtime rig.
	# The middle is still a single FK arc per joint, never a moving IK pole.
	var runtime: Node = load("res://main.tscn").instantiate()
	runtime.set_script(Review.OfflineRuntime)
	root.add_child(runtime)
	var rig: Skeleton3D = runtime.skeleton
	for track in range(original.get_track_count()):
		var bone := rig.find_bone(String(original.track_get_path(track).get_subname(0)))
		rig.set_bone_pose_rotation(bone, original.rotation_track_interpolate(track, 2.0))
	rig.force_update_all_bone_transforms()
	var chest := rig.find_bone("上半身")
	var chest_pose := rig.get_bone_global_pose(chest)
	chest_pose.basis = Basis(Vector3.RIGHT, deg_to_rad(4.0)) * chest_pose.basis
	rig.set_bone_global_pose(chest, chest_pose)
	rig.force_update_all_bone_transforms()
	var arm := rig.find_bone("腕.R")
	var arm_pose := rig.get_bone_global_pose(arm)
	var hand := rig.get_bone_global_pose(rig.find_bone("手首.R")).origin
	var head := rig.get_bone_global_pose(rig.find_bone("頭")).origin
	var wrist_target := hand.lerp(head, 0.15)
	arm_pose.basis = Basis(Quaternion((hand - arm_pose.origin).normalized(), (wrist_target - arm_pose.origin).normalized())) * arm_pose.basis
	rig.set_bone_global_pose(arm, arm_pose)
	rig.force_update_all_bone_transforms()
	var closer := rig.get_bone_global_pose(rig.find_bone("手首.R")).origin
	var tuned := { "上半身": rig.get_bone_pose_rotation(chest), "腕.R": rig.get_bone_pose_rotation(arm) }
	print("LISTEN_DETAIL ", { "extra_lean_degrees": 4.0, "wrist_head_before": hand.distance_to(head), "wrist_head_after": closer.distance_to(head), "wrist_shift": hand.distance_to(closer) })
	var result := Animation.new()
	result.resource_name = "listen_reference_fk_v2"
	result.length = 2.0
	for track in range(original.get_track_count()):
		if original.track_get_type(track) != Animation.TYPE_ROTATION_3D:
			push_error("Endpoint source must contain rotations only")
			quit(1)
			return
		var start: Quaternion = original.track_get_key_value(track, 0)
		var end: Quaternion = original.track_get_key_value(track, original.track_get_key_count(track) - 1)
		var name := String(original.track_get_path(track).get_subname(0))
		if tuned.has(name):
			end = tuned[name]
		var target := result.add_track(Animation.TYPE_ROTATION_3D)
		result.track_set_path(target, original.track_get_path(track))
		result.track_set_interpolation_type(target, Animation.INTERPOLATION_LINEAR)
		for frame in range(61):
			var t := float(frame) / 30.0
			# Arm raise and elbow flex are coordinated. The left elbow follows
			# the shoulder, so the tuck starts outside the skirt, not through it.
			var progress := smoothstep(0.0, 1.0, clampf(t / 1.65, 0.0, 1.0))
			if name == "ひじ.L":
				progress = smoothstep(0.0, 1.0, clampf((t - 0.3) / 1.4, 0.0, 1.0))
			elif name in ["上半身", "上半身2", "首", "頭"]:
				progress = smoothstep(0.0, 1.0, clampf((t - 0.25) / 1.45, 0.0, 1.0))
			result.rotation_track_insert_key(target, t, start.slerp(end, progress).normalized())
	if ResourceSaver.save(result, output) != OK:
		quit(1)
		return
	var report := {
		"agent": "Codex", "method": "reference-guided fixed-local-axis FK, endpoint-preserving",
		"source": SOURCE, "source_sha256": SOURCE_SHA,
		"reference_video": "9d7f8fb2da073cbff079bae38d39da1d.mp4 (visual reference, not landmark input)",
		"clip_sha256": FileAccess.get_sha256(output), "duration": 2.0,
		"frames": 61, "rotation_tracks": 74,
		"preserved": "exact start and all end rotations except upper torso/right upper arm; official mesh/rest/skin/proportions/materials",
		"authored": "extra 4-degree forward lean and small right shoulder swing toward head; no extra wrist or elbow change",
		"wrist_head_before": hand.distance_to(head), "wrist_head_after": closer.distance_to(head),
	}
	var file := FileAccess.open(output + ".json", FileAccess.WRITE)
	if file == null:
		quit(1)
		return
	file.store_string(JSON.stringify(report, "\t") + "\n")
	print("LISTEN_FK_BAKE_OK ", output, " ", report.clip_sha256)
	quit()
