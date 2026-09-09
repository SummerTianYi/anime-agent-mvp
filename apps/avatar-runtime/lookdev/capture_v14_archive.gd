extends "res://lookdev/render_candidate.gd"

## Codex: seven immutable-version views, rendered through production 1.4.
func _run() -> void:
	if DisplayServer.get_name() == "headless":
		quit(1)
		return
	output = "user://model-1.4-freeze/" + Time.get_datetime_string_from_system().replace(":", "-") + "-" + str(OS.get_process_id())
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(output))
	root.size = Vector2i(16,16)
	root.position = Vector2i(-100,-100)
	root.always_on_top = false
	viewport = SubViewport.new()
	viewport.size = Vector2i(1920,2320)
	viewport.own_world_3d = true
	viewport.transparent_bg = true
	viewport.msaa_3d = Viewport.MSAA_4X
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(viewport)
	runtime = load("res://main.tscn").instantiate()
	runtime.set_script(OfflineRuntime)
	viewport.add_child(runtime)
	runtime.set_model_look_version("1.4")
	_check(runtime.model_look_version == "1.4", "production look")
	_check(FileAccess.get_sha256("res://assets/luotianyi_v4.glb") == SHA, "official hash")
	var views := [{"id":"front","yaw":0},{"id":"left","yaw":90},{"id":"right","yaw":-90},{"id":"back","yaw":180},{"id":"max-zoom","yaw":0},{"id":"neutral-face","yaw":0},{"id":"expression-extremes","yaw":0}]
	for view in views:
		_pose(float(view.yaw),2.0)
		var target: Vector3 = runtime.CAMERA_FOCUS
		var distance: float = 3.8
		if view.id == "max-zoom":
			distance = runtime.MIN_CAMERA_DISTANCE
		if view.id in ["neutral-face","expression-extremes"]:
			target = runtime.skeleton.global_transform * runtime.skeleton.get_bone_global_pose(runtime.skeleton.find_bone("頭")).origin + Vector3(0,0.08,0)
			distance = 0.60
		if view.id == "expression-extremes":
			runtime.face_mesh.set_blend_shape_value(runtime.expression_ids["笑い"],1.0)
			runtime.face_mesh.set_blend_shape_value(runtime.expression_ids["あ"],1.0)
		runtime.camera.position = target + Vector3(0,0,distance)
		runtime.camera.look_at(target,Vector3.UP)
		var invariant := _invariants()
		var pixels: Image = await _capture()
		_check(pixels.get_used_rect().size.y > 300, "nonempty " + str(view.id))
		_check(_invariants() == invariant, "capture does not alter pose " + str(view.id))
		_save(pixels,str(view.id)+".png")
	print("MODEL_14_ARCHIVE_VIEWS ",ProjectSettings.globalize_path(output)," failures=",failures)
	quit(0 if failures.is_empty() else 1)
