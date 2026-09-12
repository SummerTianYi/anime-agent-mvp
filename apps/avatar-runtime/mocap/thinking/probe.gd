extends SceneTree
## Codex: offline rig probe and contact negative control. No production _ready.
const Review = preload("res://lookdev/render_candidate.gd")
func _init() -> void:
	call_deferred("_run")
func _run() -> void:
	var output := OS.get_environment("THINKING_OUTPUT")
	if output.is_empty() or FileAccess.file_exists(output + "/rig.json"):
		push_error("Use a fresh THINKING_OUTPUT directory")
		quit(1)
		return
	DirAccess.make_dir_recursive_absolute(output)
	var runtime = load("res://main.tscn").instantiate()
	runtime.set_script(Review.OfflineRuntime)
	root.add_child(runtime)
	runtime._play_authored_motion(&"idle")
	runtime.authored_motion_player.seek(0.0, true)
	runtime.authored_motion_player.pause()
	var rig: Skeleton3D = runtime.skeleton
	var bones := []
	for i in rig.get_bone_count():
		var pose := rig.get_bone_global_pose(i)
		bones.append({"name": rig.get_bone_name(i), "parent": rig.get_bone_parent(i),
			"point": [pose.origin.x, pose.origin.y, pose.origin.z], "basis": str(pose.basis), "rest": str(rig.get_bone_rest(i))})
	var report := {"bones": bones, "model_transform": str(runtime.model.transform), "rig_transform": str(rig.global_transform),
		"face_aabb": str(runtime.face_mesh.get_aabb()), "camera": str(runtime.camera.transform)}
	var surfaces := []
	for s in runtime.face_mesh.mesh.get_surface_count():
		var vertices: PackedVector3Array = runtime.face_mesh.mesh.surface_get_arrays(s)[Mesh.ARRAY_VERTEX]
		var bounds := AABB(vertices[0], Vector3.ZERO)
		var middle := []
		for vertex in vertices:
			bounds = bounds.expand(vertex)
			if absf(vertex.x) < 0.003 and vertex.y > 1.27 and vertex.y < 1.40 and vertex.z > 0.04:
				middle.append([vertex.x, vertex.y, vertex.z])
		surfaces.append({"name": runtime.face_mesh.mesh.surface_get_name(s), "bounds": str(bounds), "face_center": middle})
	report["surfaces"] = surfaces
	FileAccess.open(output + "/rig.json", FileAccess.WRITE).store_string(JSON.stringify(report, "\t"))
	# Intended RED: the untouched A-pose must NOT pass a chin-contact check.
	var wrist := rig.get_bone_global_pose(rig.find_bone("手首.L")).origin
	var head := rig.get_bone_global_pose(rig.find_bone("頭")).origin
	print("BASELINE_CHIN_CONTACT distance=", wrist.distance_to(head), " required<0.19m; expected FAIL")
	quit(1 if wrist.distance_to(head) >= 0.19 else 0)
