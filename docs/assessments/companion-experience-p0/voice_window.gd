extends SceneTree
# Observe the normal role scene. Leave the renderer, bridge, audio player and animation running.
var role
var folder := OS.get_environment("COMPANION_AUDITION_STATE")
var peak_mouth := 0.0
var audible_frames := 0

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	if folder.is_empty() or not FileAccess.file_exists(folder + "/synthetic-only"):
		quit(2)
		return
	if DisplayServer.get_name() == "headless" or AudioServer.get_driver_name() != "WASAPI":
		quit(3)
		return
	role = load("res://main.tscn").instantiate()
	root.add_child(role)
	await process_frame
	await process_frame
	root.title = "天依陪伴试听（隔离窗口）"
	root.position = Vector2i(40, 56)
	role.interaction_ui._open_chat()
	var start := Time.get_ticks_msec()
	while not FileAccess.file_exists(folder + "/finished") and Time.get_ticks_msec() - start < 175000:
		await process_frame
		if role.speech_player != null and role.speech_player.playing:
			audible_frames += 1
			peak_mouth = maxf(peak_mouth, role.speech_open)
	var result := {"visible":root.visible, "display":DisplayServer.get_name(), "audio":AudioServer.get_driver_name(),
		"bones":role.skeleton.get_bone_count(), "face_shapes":role.face_mesh.mesh.get_blend_shape_count(),
		"playing_frames":audible_frames, "peak_mouth":peak_mouth}
	var f := FileAccess.open(folder + "/window.json", FileAccess.WRITE)
	f.store_line(JSON.stringify(result))
	f.close()
	quit(0 if audible_frames > 0 else 4)
