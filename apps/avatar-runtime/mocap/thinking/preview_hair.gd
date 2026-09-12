extends "res://mocap/thinking/preview.gd"
## Codex: independent preview entry point; production runtime is untouched.
const Hair = preload("res://mocap/thinking/hair_pose.gd")
var hair: RefCounted

func capture(t: float, yaw: int, path: String) -> void:
	pose.reset()
	runtime.authored_motion_player.seek(t, true)
	runtime.model.rotation = runtime.base_model_rotation + Vector3(0, deg_to_rad(yaw), 0)
	runtime.elapsed = t
	runtime._apply_pigtail_pose()
	if hair == null:
		hair = Hair.new()
		hair.setup(runtime)
	if not OS.get_cmdline_user_args().has("--baseline"):
		hair.apply(t)
	var blink := maxf(exp(-pow((t - 2.15) / 0.085, 2)), exp(-pow((t - 6.65) / 0.085, 2)))
	if runtime.expression_ids.has("まばたき"):
		runtime.face_mesh.set_blend_shape_value(runtime.expression_ids["まばたき"], blink * 0.9)
	await process_frame
	await RenderingServer.frame_post_draw
	var pixels := viewport.get_texture().get_image()
	if pixels.is_empty() or pixels.save_png(path) != OK:
		push_error("Hair preview render failed: " + path)
		quit(1)
		return
