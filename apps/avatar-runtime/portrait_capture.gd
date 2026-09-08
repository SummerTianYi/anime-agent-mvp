extends RefCounted

## Codex: native-resolution portrait capture, independent of the desktop
## compositor. The temporary camera shares the visible 3D world; neither the
## live viewport nor the official model is resized or modified.
const OUTPUT_DIRECTORY := "user://portraits"
const SCALE := 1.5 # Daily render is already 2x; output is therefore 3x.
var busy := false


func capture(camera: Camera3D, source: Viewport) -> Dictionary:
	if busy:
		return {"ok": false, "error": "A portrait capture is already running"}
	if DisplayServer.get_name() == "headless" or not is_instance_valid(source) \
			or not is_instance_valid(camera) or not source.is_inside_tree():
		return {"ok": false, "error": "Portrait capture needs a visible 3D viewport"}
	# Compact mode includes the UI in its root viewport, but only the world is
	# shared below: chat windows and the surrounding desktop are never captured.
	var output_size := Vector2i(Vector2(source.get_visible_rect().size) * SCALE)
	if output_size.x < 2 or output_size.y < 2 or output_size.x > 8192 or output_size.y > 8192:
		return {"ok": false, "error": "Unsupported portrait dimensions"}
	var directory := ProjectSettings.globalize_path(OUTPUT_DIRECTORY)
	var error := DirAccess.make_dir_recursive_absolute(directory)
	if error != OK:
		return {"ok": false, "error": "Cannot create portrait directory: " + error_string(error)}
	busy = true
	var started := Time.get_ticks_msec()
	var target := SubViewport.new()
	target.name = "PortraitCaptureViewport"
	target.size = output_size
	target.transparent_bg = true
	target.world_3d = source.find_world_3d()
	target.msaa_3d = Viewport.MSAA_4X
	target.render_target_update_mode = SubViewport.UPDATE_ONCE
	var tree := source.get_tree()
	tree.root.add_child(target)
	var capture_camera := camera.duplicate() as Camera3D
	target.add_child(capture_camera)
	capture_camera.global_transform = camera.global_transform
	capture_camera.make_current()
	await RenderingServer.frame_post_draw
	var pixels := target.get_texture().get_image()
	target.queue_free()
	if pixels == null or pixels.is_empty():
		busy = false
		return {"ok": false, "error": "Renderer returned an empty portrait"}
	var stamp := Time.get_datetime_string_from_system().replace(":", "-")
	var path := directory.path_join("tianyi-%s-%d-%d.png" % [stamp, OS.get_process_id(), Time.get_ticks_usec()])
	# Do not overwrite an existing export, including exports from another run.
	if FileAccess.file_exists(path):
		busy = false
		return {"ok": false, "error": "Portrait file already exists"}
	error = pixels.save_png(path)
	busy = false
	if error != OK:
		return {"ok": false, "error": "Cannot save portrait: " + error_string(error)}
	return {"ok": true, "path": path, "size": output_size,
		"elapsed_ms": Time.get_ticks_msec() - started, "transparent": true}
