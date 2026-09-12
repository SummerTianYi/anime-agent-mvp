extends "res://mocap/thinking/pose.gd"
## Codex: reference-guided farewell candidate. Not automatic motion capture.
## Reuse the inspected rig helpers; never run thinking/contact setup.
const LENGTH := 4.1
const FACE_PEAK := {"笑い": 1.0, "にやり": 0.65}
var arm_controlled: Array[int] = []
var rest_pose := {}
var raised_pose := {}
var wave_left := {}
var wave_right := {}

func setup(runtime: Node) -> void:
	rig = runtime.skeleton
	runtime._cancel_authored_motion()
	runtime._restore_bone_poses()
	runtime._play_authored_motion(&"idle")
	runtime.authored_motion_player.seek(0.0, true)
	runtime.authored_motion_player.pause()
	baseline.clear()
	controlled.clear()
	arm_controlled.clear()
	for i in rig.get_bone_count():
		baseline[i] = rig.get_bone_pose(i)
	var arm := {}
	runtime._collect_bone_descendants("肩.R", arm)
	for i in arm:
		controlled.append(i)
		arm_controlled.append(i)
	for name in ["首", "頭"]:
		controlled.append(rig.find_bone(name))
	var hand := point("手首.R")
	var normal := (point("人指１.R") - hand).cross(point("小指１.R") - hand).normalized()
	if normal.z < 0.0:
		normal = -normal
	var hinge := (hand - point("ひじ.R")).normalized().cross(normal).normalized()
	hinges["R"] = rig.get_bone_global_pose(rig.find_bone("ひじ.R")).basis.inverse() * hinge
	rest_pose = snapshot()
	# Raise the upper arm to shoulder level (+7 degrees), then lock it.
	# Derive the wrist from actual bone lengths; the elbow hinge lies in XY.
	var shoulder := point("腕.R")
	var upper_length := shoulder.distance_to(point("ひじ.R"))
	var lower_length := point("ひじ.R").distance_to(hand)
	var upper_direction := Vector3(-cos(deg_to_rad(7)), sin(deg_to_rad(7)), 0)
	var target_wrist := shoulder + upper_direction * upper_length + Vector3.UP * lower_length
	solve_arm("R", target_wrist, Vector3.LEFT)
	orient_palm("R", Vector3.UP, Vector3(0, 0, 1))
	raised_pose = snapshot()
	# Owner correction: ONLY elbow flex oscillates during the wave. No upper-
	# arm swing, wrist flutter, or forearm axial rotation is added.
	var elbow_index := rig.find_bone("ひじ.R")
	for sign_value in [-1.0, 1.0]:
		set_rotations(raised_pose)
		var elbow_rotation: Quaternion = raised_pose[elbow_index]
		rig.set_bone_pose_rotation(elbow_index, elbow_rotation * Quaternion(hinges.R, deg_to_rad(23.0 * sign_value)))
		rig.force_update_all_bone_transforms()
		if sign_value < 0.0:
			wave_left = snapshot()
		else:
			wave_right = snapshot()
	reset()

func set_rotations(rotations: Dictionary) -> void:
	for i in rotations:
		rig.set_bone_pose_rotation(i, rotations[i])
	rig.force_update_all_bone_transforms()

func blend_rotations(a: Dictionary, b: Dictionary, weight: float) -> void:
	for i in controlled:
		var first: Quaternion = a[i]
		rig.set_bone_pose_rotation(i, first.slerp(b[i], weight))
	rig.force_update_all_bone_transforms()

func apply(t: float) -> void:
	reset()
	t = clampf(t, 0.0, LENGTH)
	if t < 1.0:
		blend_rotations(rest_pose, raised_pose, smoothstep(0.2, 1.0, t))
	elif t <= 3.16:
		var u := (t - 1.0) / 2.16
		var envelope := smoothstep(0.0, 0.12, u) * (1.0 - smoothstep(0.88, 1.0, u))
		var sway := sin(TAU * 3.0 * u) * envelope
		blend_rotations(raised_pose, wave_right if sway >= 0 else wave_left, absf(sway))
	else:
		blend_rotations(raised_pose, rest_pose, smoothstep(3.16, 3.9, t))
	# Independent head/neck layer: the approved arm tracks stay unchanged.
	var u := clampf((t - 0.8) / 2.5, 0.0, 1.0)
	var envelope := smoothstep(0.0, 0.15, u) * (1.0 - smoothstep(0.85, 1.0, u))
	var roll := deg_to_rad(3.0) * sin(TAU * 2.0 * u) * envelope
	var yaw := deg_to_rad(1.5) * sin(TAU * 2.0 * u + PI / 4.0) * envelope
	rotate_global("首", Basis(Vector3(0, 0, 1), roll * 0.4))
	rotate_global("頭", Basis(Vector3.UP, yaw) * Basis(Vector3(0, 0, 1), roll * 0.6))

func expression_weights(t: float) -> Dictionary:
	var weight := smoothstep(0.6, 1.0, t) * (1.0 - smoothstep(3.16, 3.85, t))
	return {"笑い": weight, "にやり": weight * FACE_PEAK["にやり"]}

func open_fingers_unchanged() -> bool:
	for prefix in ["親指", "人指", "中指", "薬指", "小指"]:
		for digit in ["０", "１", "２", "３"]:
			var i := rig.find_bone(prefix + digit + ".R")
			if i >= 0 and not rig.get_bone_pose(i).is_equal_approx(baseline[i]):
				return false
	return true
