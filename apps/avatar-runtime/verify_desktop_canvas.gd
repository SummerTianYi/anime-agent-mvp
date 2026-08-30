extends SceneTree


const OFFICIAL_MODEL_PATH := "res://assets/luotianyi_v4.glb"
const OFFICIAL_MODEL_SHA256 := "df55806d343d149b41c20d0ef074373cafca2379212fd8691e998ea6cddc6e4a"


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var actual_hash := FileAccess.get_sha256(OFFICIAL_MODEL_PATH)
	if actual_hash.to_lower() != OFFICIAL_MODEL_SHA256:
		_fail("Official model hash changed: %s" % actual_hash)
		return
	var scene := load("res://main.tscn") as PackedScene
	if scene == null:
		_fail("Unable to load main scene")
		return
	var runtime: Node = scene.instantiate()
	root.add_child(runtime)
	if runtime.canvas_mode != "desktop":
		_fail("Desktop canvas is not the default mode")
		return
	var center_polygon: PackedVector2Array = runtime._avatar_interaction_polygon()
	if center_polygon.size() != 14:
		_fail("Avatar click-through hull changed shape")
		return
	if runtime.avatar_render_viewport == null or runtime.avatar_texture_rect == null:
		_fail("Desktop avatar is not rendered through the isolated SubViewport")
		return
	if runtime.avatar_render_viewport.size != Vector2i(1520, 1840):
		_fail("Unexpected supersampled avatar viewport size")
		return
	if not runtime.avatar_texture_rect.size.is_equal_approx(Vector2(760.0, 920.0)):
		_fail("Avatar composite is not downsampled to its intended desktop size")
		return
	if not is_equal_approx(runtime.camera.position.z, runtime.BASE_CAMERA_DISTANCE):
		_fail("Camera distance no longer preserves the original perspective")
		return
	var original_center: Vector2 = runtime.avatar_screen_center
	var original_texture_position: Vector2 = runtime.avatar_texture_rect.position
	runtime.avatar_screen_center += Vector2(120.0, 80.0)
	runtime._sync_avatar_texture_rect()
	var composite_delta: Vector2 = runtime.avatar_texture_rect.position - original_texture_position
	if not composite_delta.is_equal_approx(Vector2(120.0, 80.0)):
		_fail("Desktop drag did not move only the 2D composite")
		return
	runtime.avatar_screen_center = original_center
	runtime._sync_avatar_texture_rect()
	if runtime.interaction_ui == null or not runtime.interaction_ui.has_method("set_canvas_origin"):
		_fail("Interaction UI cannot follow the desktop avatar")
		return
	var model_file := FileAccess.open(OFFICIAL_MODEL_PATH, FileAccess.READ)
	var model_bytes := model_file.get_length() if model_file != null else -1
	print("GODOT_DESKTOP_CANVAS_OK", {
		"canvas_mode": runtime.canvas_mode,
		"official_model_sha256": actual_hash,
		"official_model_bytes": model_bytes,
		"interaction_hull_points": center_polygon.size(),
		"render_viewport_size": runtime.avatar_render_viewport.size,
		"composite_size": runtime.avatar_texture_rect.size,
		"camera_distance": runtime.camera.position.z,
		"camera_fov": runtime.camera.fov,
		"screen_drag_composite_delta": composite_delta,
		"model_remains_on_optical_axis": is_zero_approx(runtime.model.position.x),
		"model_structure_untouched": true,
	})
	quit(0)


func _fail(message: String) -> void:
	push_error(message)
	quit(1)
