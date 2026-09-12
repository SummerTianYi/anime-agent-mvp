extends RefCounted
## Codex: offline, action-specific hair guidance, not a general collision solver.
## Run AFTER the baseline sway. Only existing pigtail rotations may change.
var rig: Skeleton3D
var chains: Array = []

func setup(runtime: Node) -> void:
	rig = runtime.skeleton
	for side in ["R", "L"]:
		var chain: Array[int] = []
		for j in range(17):
			chain.append(rig.find_bone("MaWei_%s_%d_1" % [side, j]))
		chains.append(chain)

func weight(t: float) -> float:
	return smoothstep(0.20, 1.40, t) * (1.0 - smoothstep(7.1, 9.3, t))

func apply(t: float) -> void:
	var w := weight(t)
	if w <= 0.0:
		return
	for side in range(2):
		var chain: Array = chains[side]
		var points: Array[Vector3] = []
		for i in chain:
			points.append(rig.get_bone_global_pose(i).origin)
		for j in range(16):
			var p := points[j + 1]
			var root_fade := smoothstep(1.0, 5.0, float(j + 1))
			var offset := Vector3.ZERO
			offset.z = (0.115 if side == 0 else 0.095) * exp(-pow((p.y - 1.14) / 0.17, 2))
			if side == 1:
				offset.x = 0.120 * exp(-pow((p.y - 1.28) / 0.14, 2))
			var target := p + offset * root_fade * w
			var current := rig.get_bone_global_pose(chain[j])
			var child := rig.get_bone_global_pose(chain[j + 1]).origin
			var direction := (target - current.origin).normalized()
			# Below the arm, release the free end toward gravity, rather than
			# pulling it back to its old location and creating an S-shaped loop.
			if j >= 8:
				var free_direction := (points[j + 1] - points[j]).normalized().lerp(Vector3.DOWN, 0.85).normalized()
				direction = direction.lerp(free_direction, smoothstep(7.0, 11.0, float(j)) * w).normalized()
			var turn := Quaternion((child - current.origin).normalized(), direction)
			current.basis = Basis(turn) * current.basis
			rig.set_bone_global_pose(chain[j], current)
			rig.force_update_all_bone_transforms()
