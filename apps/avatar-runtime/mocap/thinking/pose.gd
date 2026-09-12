extends RefCounted
## Codex: video-reference authored candidate, NOT automatically recovered mocap.
## Solve contact key poses once, then interpolate local rotations on fixed arcs.
var rig: Skeleton3D
var baseline := {}
var controlled: Array[int] = []
var hinges := {}
var keyposes: Array[Dictionary] = []
var keytimes := [0.0, 0.3, 1.65, 2.5, 3.7, 5.2, 6.5, 7.0, 8.6, 9.5]

func setup(runtime: Node) -> void:
	rig = runtime.skeleton
	runtime._cancel_authored_motion()
	runtime._restore_bone_poses()
	runtime._play_authored_motion(&"idle")
	runtime.authored_motion_player.seek(0.0, true)
	runtime.authored_motion_player.pause()
	for i in rig.get_bone_count():
		baseline[i] = rig.get_bone_pose(i)
	var arms := {}
	for side in ["L", "R"]:
		runtime._collect_bone_descendants("肩." + side, arms)
		var hand := point("手首." + side)
		var normal := (point("人指１." + side) - hand).cross(point("小指１." + side) - hand).normalized()
		if normal.z < 0.0:
			normal = -normal
		var hinge := (hand - point("ひじ." + side)).normalized().cross(normal).normalized()
		hinges[side] = rig.get_bone_global_pose(rig.find_bone("ひじ." + side)).basis.inverse() * hinge
	for i in arms:
		controlled.append(i)
	for name in ["上半身", "上半身2", "首", "頭"]:
		controlled.append(rig.find_bone(name))
	keyposes = [snapshot(), snapshot()]
	for angles in [Vector2(0, -3), Vector2(0, -7), Vector2(12, -5), Vector2(-13, -4), Vector2(0, -3), Vector2(0, -3)]:
		reset()
		contact_pose(angles.x, angles.y)
		keyposes.append(snapshot())
	reset()
	keyposes.append(snapshot())
	keyposes.append(snapshot())

func point(name: String) -> Vector3:
	return rig.get_bone_global_pose(rig.find_bone(name)).origin

func reset() -> void:
	for i in baseline:
		rig.set_bone_pose(i, baseline[i])
	rig.force_update_all_bone_transforms()

func snapshot() -> Dictionary:
	var rotations := {}
	for i in controlled:
		rotations[i] = rig.get_bone_pose_rotation(i)
	return rotations

func apply(t: float) -> void:
	reset()
	var segment := 0
	while segment < keytimes.size() - 2 and t > keytimes[segment + 1]:
		segment += 1
	var u := smoothstep(0.0, 1.0, clampf((t - keytimes[segment]) / (keytimes[segment + 1] - keytimes[segment]), 0.0, 1.0))
	for i in controlled:
		var a: Quaternion = keyposes[segment][i]
		var b: Quaternion = keyposes[segment + 1][i]
		rig.set_bone_pose_rotation(i, a.slerp(b, u))
	rig.force_update_all_bone_transforms()

func rotate_global(name: String, rotation: Basis) -> void:
	var i := rig.find_bone(name)
	var transform := rig.get_bone_global_pose(i)
	transform.basis = rotation * transform.basis
	rig.set_bone_global_pose(i, transform)
	rig.force_update_all_bone_transforms()

func aim(name: String, child: String, direction: Vector3) -> void:
	rotate_global(name, Basis(Quaternion((point(child) - point(name)).normalized(), direction.normalized())))

func solve_arm(side: String, wrist: Vector3, pole: Vector3) -> void:
	var shoulder := point("腕." + side)
	var elbow := point("ひじ." + side)
	var hand := point("手首." + side)
	var a := shoulder.distance_to(elbow)
	var b := elbow.distance_to(hand)
	var offset := wrist - shoulder
	var d := clampf(offset.length(), sqrt(a * a + b * b + 2 * a * b * cos(deg_to_rad(145))), a + b - 0.001)
	var axis := offset.normalized()
	wrist = shoulder + axis * d
	var x := (a * a - b * b + d * d) / (2 * d)
	var h := sqrt(maxf(0, a * a - x * x))
	var joint := shoulder + axis * x + (pole - axis * pole.dot(axis)).normalized() * h
	var before := (elbow - shoulder).normalized()
	var hinge_before: Vector3 = rig.get_bone_global_pose(rig.find_bone("ひじ." + side)).basis * hinges[side]
	hinge_before = (hinge_before - before * hinge_before.dot(before)).normalized()
	var after := (joint - shoulder).normalized()
	var hinge_after := after.cross((wrist - joint).normalized()).normalized()
	rotate_global("腕." + side, Basis(after, hinge_after, after.cross(hinge_after)) * Basis(before, hinge_before, before.cross(hinge_before)).transposed())
	aim("ひじ." + side, "手首." + side, wrist - point("ひじ." + side))

func orient_palm(side: String, fingers: Vector3, normal: Vector3) -> void:
	var wrist := point("手首." + side)
	var index := point("人指１." + side) - wrist
	var little := point("小指１." + side) - wrist
	var y := ((index + little) * 0.5).normalized()
	var z := index.cross(little).normalized()
	# Index/little ordering differs between hands; use actual palm-facing normals.
	if side == "L":
		z = -z
	var x := y.cross(z).normalized()
	z = x.cross(y).normalized()
	var target_y := fingers.normalized()
	var target_x := target_y.cross(normal).normalized()
	var target_z := target_x.cross(target_y).normalized()
	var delta := Basis(target_x, target_y, target_z) * Basis(x, y, z).transposed()
	var hand_index := rig.find_bone("手首." + side)
	var target_basis := delta * rig.get_bone_global_pose(hand_index).basis
	# Anatomical forearm roll belongs in the official twist chain, not a kink
	# at the wrist. Apply a fixed per-key-pose roll, then keep only hand swing.
	var axis := (wrist - point("ひじ." + side)).normalized()
	var q := delta.get_rotation_quaternion()
	var projection := Vector3(q.x, q.y, q.z).dot(axis)
	var twist := Quaternion(axis.x * projection, axis.y * projection, axis.z * projection, q.w).normalized()
	var angle := 2.0 * atan2(Vector3(twist.x, twist.y, twist.z).dot(axis), twist.w)
	angle = wrapf(angle, -PI, PI)
	for n in range(1, 4):
		rotate_global("手捩%d.%s" % [n, side], Basis(axis, angle * float(n) / 4.0))
	rotate_global("手捩." + side, Basis(axis, angle))
	var hand_pose := rig.get_bone_global_pose(hand_index)
	hand_pose.basis = target_basis
	rig.set_bone_global_pose(hand_index, hand_pose)
	rig.force_update_all_bone_transforms()

func contact_pose(yaw: float, pitch: float) -> void:
	rotate_global("上半身2", Basis(Vector3.RIGHT, deg_to_rad(2)))
	rotate_global("首", Basis(Vector3.UP, deg_to_rad(yaw * 0.3)))
	rotate_global("頭", Basis(Vector3.UP, deg_to_rad(yaw * 0.7)) * Basis(Vector3.RIGHT, deg_to_rad(pitch)))
	var head := rig.get_bone_global_pose(rig.find_bone("頭"))
	# Approximate jaw reference in head space; GPU multi-view review is required.
	var wrist := head * Vector3(0.048, -0.085, 0.134)
	solve_arm("L", wrist, Vector3(0.5, -1.0, 1.2))
	orient_palm("L", head.basis * Vector3(-0.85, 0.50, -0.15), head.basis * Vector3(0.0, 0.0, -1.0))
	# Owner's close-up revision: index + thumb open; remaining three curl into
	# the palm. The shape stays fixed through the whole thinking hold.
	for finger in ["人指", "中指", "薬指", "小指"]:
		for digit in ["１", "２", "３"]:
			var name: String = finger + digit + ".L"
			var i := rig.find_bone(name)
			if i >= 0:
				var curl: float = 0.0 if finger == "人指" else {"１": 65.0, "２": 80.0, "３": 35.0}[digit]
				rig.set_bone_pose_rotation(i, rig.get_bone_pose_rotation(i) * Quaternion(Vector3.RIGHT, deg_to_rad(curl)))
	rig.force_update_all_bone_transforms()
	var elbow := point("ひじ.L")
	solve_arm("R", elbow + Vector3(-0.080, -0.037, 0.008), Vector3(-0.6, -0.7, 1.8))
	orient_palm("R", Vector3(0.96, 0.13, -0.07), Vector3.DOWN)
	for finger in ["人指", "中指", "薬指", "小指"]:
		for digit in ["１", "２", "３"]:
			var i := rig.find_bone(finger + digit + ".R")
			if i >= 0:
				rig.set_bone_pose_rotation(i, rig.get_bone_pose_rotation(i) * Quaternion(Vector3.RIGHT, deg_to_rad(8 if digit == "１" else 23)))
	rig.force_update_all_bone_transforms()

func contacts() -> Dictionary:
	var head := rig.get_bone_global_pose(rig.find_bone("頭"))
	return {"chin_wrist_m": point("手首.L").distance_to(head.origin),
		"support_elbow_m": ((point("人指１.R") + point("小指１.R")) * 0.5).distance_to(point("ひじ.L")),
		"chin_wrist": str(point("手首.L")), "chin_elbow": str(point("ひじ.L")), "support_wrist": str(point("手首.R"))}
