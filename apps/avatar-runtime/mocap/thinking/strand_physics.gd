extends RefCounted
## Codex: offline position-based strands, metre/second units; optional idle return.
## Distance links, compliant bending, spatial segment contact and damping.
const DT := 1.0 / 240.0
const RADIUS := 0.014
const ITERATIONS := 64
const BEND_COMPLIANCE := 0.00008
const LAST_PIN := 2
var rig: Skeleton3D
var chains := []
var shapes := []
var contact_count := 0

func seed_from_rig() -> void:
	# Animated grooming before contact only. Preserve its incoming velocity.
	for chain in chains:
		chain.old = chain.p.duplicate()
		for j in range(17):
			chain.p[j] = rig.get_bone_global_pose(chain.ids[j]).origin

func diagnostics() -> Dictionary:
	var result := {"mapping_error_m": 0.0, "link_error_m": 0.0, "solver_gap_m": 10.0, "rig_gap_m": 10.0, "worst_link": "", "worst_solver_contact": "", "worst_rig_contact": ""}
	for chain in chains:
		for j in range(17):
			var actual := rig.get_bone_global_pose(chain.ids[j]).origin
			result.mapping_error_m = maxf(result.mapping_error_m, actual.distance_to(chain.p[j]))
			if j >= 16:
				continue
			var length_error: float = absf(chain.p[j].distance_to(chain.p[j + 1]) - chain.lengths[j])
			if length_error > result.link_error_m:
				result.link_error_m = length_error
				result.worst_link = rig.get_bone_name(chain.ids[j])
			for s in range(shapes.size()):
				var shape: Array = shapes[s]
				var sim := Geometry3D.get_closest_points_between_segments(chain.p[j], chain.p[j+1], shape[0], shape[1])
				var real := Geometry3D.get_closest_points_between_segments(actual, rig.get_bone_global_pose(chain.ids[j+1]).origin, shape[0], shape[1])
				var sim_gap: float = sim[0].distance_to(sim[1]) - shape[2] - RADIUS
				var real_gap: float = real[0].distance_to(real[1]) - shape[2] - RADIUS
				if sim_gap < result.solver_gap_m:
					result.solver_gap_m = sim_gap
					result.worst_solver_contact = "%s / %d" % [rig.get_bone_name(chain.ids[j]), s]
				if real_gap < result.rig_gap_m:
					result.rig_gap_m = real_gap
					result.worst_rig_contact = "%s / %d" % [rig.get_bone_name(chain.ids[j]), s]
	return result

func setup(runtime: Node) -> void:
	rig = runtime.skeleton
	for side in ["R", "L"]:
		var ids := []
		var points := []
		for j in range(17):
			var id := rig.find_bone("MaWei_%s_%d_1" % [side, j])
			ids.append(id)
			points.append(rig.get_bone_global_pose(id).origin)
		var lengths := []
		var bends := []
		for j in range(16):
			lengths.append(points[j].distance_to(points[j + 1]))
		for j in range(15):
			bends.append(points[j].distance_to(points[j + 2]))
		chains.append({"ids": ids, "p": points, "old": points.duplicate(), "lengths": lengths, "bends": bends})

func point(name: String) -> Vector3:
	return rig.get_bone_global_pose(rig.find_bone(name)).origin

func update_shapes() -> void:
	shapes.clear()
	for side in ["L", "R"]:
		shapes.append([point("腕." + side), point("ひじ." + side), 0.035])
		shapes.append([point("ひじ." + side), point("手首." + side), 0.032])
		shapes.append([point("手首." + side), point("中指１." + side), 0.022])
		shapes.append([point("手首." + side), point("手首." + side), 0.041])
	# Rest fitted torso spheres, transformed by the animated upper body delta.
	var chest := rig.get_bone_global_pose(rig.find_bone("上半身2"))
	var rest := rig.get_bone_global_rest(rig.find_bone("上半身2"))
	var delta := chest * rest.affine_inverse()
	for p in [Vector3(-0.04, 1.195, 0.025), Vector3(0.04, 1.195, 0.025), Vector3(0, 1.045, 0.005)]:
		var center: Vector3 = delta * p
		shapes.append([center, center, 0.078])

func inv_mass(i: int) -> float:
	return 0.0 if i <= LAST_PIN else 1.0

func distance_constraint(points: Array, a: int, b: int, length: float, alpha: float, lambda_before: float) -> float:
	var offset: Vector3 = points[b] - points[a]
	var distance := offset.length()
	var wa := inv_mass(a)
	var wb := inv_mass(b)
	if distance < 0.000001 or wa + wb == 0:
		return 0.0
	var dl := (-(distance - length) - alpha * lambda_before) / (wa + wb + alpha)
	var correction := offset / distance * dl
	points[a] -= correction * wa
	points[b] += correction * wb
	return lambda_before + dl

func project_segment(points: Array, a: int, b: int, shape: Array, margin: float = 0.0) -> void:
	var closest := Geometry3D.get_closest_points_between_segments(points[a], points[b], shape[0], shape[1])
	var normal := closest[0] - closest[1]
	var depth: float = float(shape[2]) + RADIUS + margin - normal.length()
	if depth <= 0.0:
		return
	var edge: Vector3 = points[b] - points[a]
	var u := clampf((closest[0] - points[a]).dot(edge) / maxf(edge.length_squared(), 0.000001), 0.0, 1.0)
	var wa := inv_mass(a)
	var wb := inv_mass(b)
	var denominator := wa * (1.0 - u) * (1.0 - u) + wb * u * u
	if denominator < 0.0001:
		return
	if normal.length_squared() < 0.000000001:
		normal = Vector3(0, 0, 1)
	else:
		normal = normal.normalized()
	# Bound a single projection; distance/contact iterate together afterward.
	var correction := normal * minf(depth / denominator, 0.03)
	points[a] += correction * wa * (1.0 - u)
	points[b] += correction * wb * u
	contact_count += 1

func step(collisions: bool = true, return_strength: float = 0.0, margin: float = 0.0) -> void:
	update_shapes()
	for chain in chains:
		var points: Array = chain.p
		var old: Array = chain.old
		var current := points.duplicate()
		for j in range(17):
			if j <= LAST_PIN:
				points[j] = rig.get_bone_global_pose(chain.ids[j]).origin
			else:
				# Optional exit-only restoring force; default simulation is unchanged.
				var target := rig.get_bone_global_pose(chain.ids[j]).origin
				var force: Vector3 = Vector3.DOWN * 9.81 * (1.0 - return_strength) + (target - points[j]) * 400.0 * return_strength
				points[j] += (points[j] - old[j]) * exp(-(8.0 + 32.0 * return_strength) * DT) + force * DT * DT
		var lambdas := []
		lambdas.resize(15)
		lambdas.fill(0.0)
		for iteration in range(ITERATIONS):
			for j in range(LAST_PIN - 1, 15):
				lambdas[j] = distance_constraint(points, j, j + 2, chain.bends[j], BEND_COMPLIANCE / (DT * DT), lambdas[j])
			for n in range(LAST_PIN, 16):
				var j := n if iteration % 2 == 0 else 15 + LAST_PIN - n
				distance_constraint(points, j, j + 1, chain.lengths[j], 0.0, 0.0)
			if collisions:
				for j in range(LAST_PIN, 16):
					for s in range(shapes.size()):
						var k := s if iteration % 2 == 0 else shapes.size() - 1 - s
						project_segment(points, j, j + 1, shapes[k], margin)
		chain.old = current

func apply_to_rig() -> void:
	for chain in chains:
		for j in range(LAST_PIN, 16):
			var id: int = chain.ids[j]
			var current := rig.get_bone_global_pose(id)
			var child := rig.get_bone_global_pose(chain.ids[j + 1]).origin
			var direction: Vector3 = chain.p[j + 1] - current.origin
			var rotation := Quaternion((child - current.origin).normalized(), direction.normalized())
			current.basis = Basis(rotation) * current.basis
			rig.set_bone_global_pose(id, current)
			rig.force_update_all_bone_transforms()
		# Preserve the terminal's local frame: the existing flyaway geometry
		# follows the last solved segment rather than receiving an extra flip.
