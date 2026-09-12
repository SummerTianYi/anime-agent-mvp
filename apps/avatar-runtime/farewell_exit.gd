extends RefCounted
## Codex: exit-only playback of the owner's immutable 39-track approved take.
## Registry role=exit is excluded from interaction loading; no Core/menu exit.
const PATH := "res://assets/motions/farewell_reference_v1.tres"
const SHA256 := "aa9684cdf8e8927a601bbed3c47bf6abc38fc7dc4b85b8432f0239889542bea7"
const BLEND_SECONDS := 0.45
const DEADLINE_SECONDS := 8.0
var closing := false
var finished := false
var time := 0.0
var clip: Animation
var runtime: Node3D
var start_pose: Array[Transform3D] = []
var idle_pose: Array[Transform3D] = []
var start_face := PackedFloat32Array()
var bone_tracks := {}
var face_tracks := {}

func begin(owner_runtime: Node3D) -> bool:
	if closing:
		return false
	closing = true
	runtime = owner_runtime
	if runtime.skeleton == null or runtime.face_mesh == null or not FileAccess.file_exists(PATH):
		return false
	if FileAccess.get_sha256(PATH) != SHA256:
		return false
	clip = load(PATH) as Animation
	if clip == null or clip.get_track_count() != 39 or not is_equal_approx(clip.length, 4.1):
		return false
	for track in clip.get_track_count():
		var path := clip.track_get_path(track)
		if path.get_subname_count() != 1:
			return false
		var target := str(path.get_subname(0))
		if clip.track_get_type(track) == Animation.TYPE_ROTATION_3D:
			var bone: int = runtime.skeleton.find_bone(target)
			if bone < 0 or bone_tracks.has(bone):
				return false
			bone_tracks[bone] = track
		elif clip.track_get_type(track) == Animation.TYPE_BLEND_SHAPE:
			if not runtime.expression_ids.has(target) or face_tracks.has(target):
				return false
			face_tracks[target] = track
		else:
			return false
	if bone_tracks.size() != 37 or face_tracks.size() != 2:
		return false
	for bone in runtime.skeleton.get_bone_count():
		start_pose.append(runtime.skeleton.get_bone_pose(bone))
	for shape in runtime.face_mesh.get_blend_shape_count():
		start_face.append(runtime.face_mesh.get_blend_shape_value(shape))
	# Capture the same idle t=0 base used in the accepted preview. All old
	# animation writers stop before this controller becomes the sole writer.
	runtime._cancel_authored_motion()
	runtime._restore_bone_poses()
	var player: AnimationPlayer = runtime.authored_motion_player
	if player != null and player.has_animation(runtime.default_idle_motion):
		player.play(runtime.default_idle_motion, 0.0)
		player.seek(0.0, true)
		player.pause()
	for bone in runtime.skeleton.get_bone_count():
		idle_pose.append(runtime.skeleton.get_bone_pose(bone))
	runtime.authored_motion_active = false
	runtime.action_name = "idle"
	runtime._clear_emotions()
	runtime.expression_timers.clear()
	apply_pose()
	return true

func advance(delta: float) -> void:
	if finished or clip == null:
		return
	time = minf(time + maxf(delta, 0.0), clip.length)
	apply_pose()
	if time >= clip.length:
		finished = true
		runtime._finish_exit("animation_finished")

func apply_pose() -> void:
	var mix := smoothstep(0.0, BLEND_SECONDS, time)
	for bone in idle_pose.size():
		var target: Transform3D = idle_pose[bone]
		if bone_tracks.has(bone):
			target.basis = Basis(clip.rotation_track_interpolate(bone_tracks[bone], time)).scaled(target.basis.get_scale())
		runtime.skeleton.set_bone_pose(bone, target)
	# Preserve the existing two complete pigtail chains, with a smooth handoff
	# from any baked thinking pose rather than snapping a strand behind her.
	runtime._apply_pigtail_pose()
	if mix < 1.0:
		for bone in idle_pose.size():
			var target: Transform3D = runtime.skeleton.get_bone_pose(bone)
			runtime.skeleton.set_bone_pose(bone, start_pose[bone].interpolate_with(target, mix))
	runtime._sync_deform_bone_mirrors()
	for name in runtime.expression_ids:
		var index: int = runtime.expression_ids[name]
		var value := clip.blend_shape_track_interpolate(face_tracks[name], time) if face_tracks.has(name) else 0.0
		runtime.face_mesh.set_blend_shape_value(index, lerpf(start_face[index], value, mix))
