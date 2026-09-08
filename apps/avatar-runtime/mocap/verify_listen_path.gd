extends SceneTree

## Codex: a smooth wrong detour is still wrong. Check the entire local rotation
## path, not just adjacent keys and legal final joint angles.
func _init() -> void:
	var path := OS.get_environment("LISTEN_REVIEW_PATH")
	if path.is_empty():
		var registry: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://motion_registry.json"))
		for entry in registry.clips:
			if entry.id == "listen":
				path = entry.path
	var clip := load(path) as Animation
	if clip == null:
		quit(1)
		return
	var failed := false
	var reference := load("res://assets/motions/listen_reference_fk_v1.tres") as Animation
	if reference == null or clip.get_track_count() != reference.get_track_count():
		push_error("LISTEN_PATH_FAIL missing/changed endpoint reference")
		quit(1)
		return
	for track in range(clip.get_track_count()):
		if clip.track_get_type(track) != Animation.TYPE_ROTATION_3D or clip.track_get_path(track) != reference.track_get_path(track):
			push_error("LISTEN_PATH_FAIL changed track contract")
			quit(1)
			return
		for t in [0.0, 2.0]:
			# The owner requested only these two endpoint changes for FK v2.
			var changed := String(clip.track_get_path(track).get_subname(0))
			if t == 2.0 and changed in ["上半身", "腕.R"]:
				if clip.rotation_track_interpolate(track, t).angle_to(reference.rotation_track_interpolate(track, t)) > deg_to_rad(8.0):
					push_error("LISTEN_PATH_FAIL endpoint adjustment exceeds small-change budget")
					failed = true
				continue
			if clip.rotation_track_interpolate(track, t).angle_to(reference.rotation_track_interpolate(track, t)) > 0.002:
				push_error("LISTEN_PATH_FAIL changed reviewed endpoint")
				failed = true
		var name := String(clip.track_get_path(track).get_subname(0))
		if name not in ["腕.R", "ひじ.R", "手首.R", "腕.L", "ひじ.L", "手首.L"]:
			continue
		var first: Quaternion = clip.track_get_key_value(track, 0)
		var last: Quaternion = clip.track_get_key_value(track, clip.track_get_key_count(track) - 1)
		var direct := first.angle_to(last)
		var distance := 0.0
		var maximum_step := 0.0
		var previous := first
		for sample in range(1, 481):
			var q := clip.rotation_track_interpolate(track, clip.length * sample / 480.0)
			# atan2 is numerically stable for very small subdivided rotations.
			var delta := previous.inverse() * q
			var step := 2.0 * atan2(Vector3(delta.x, delta.y, delta.z).length(), absf(delta.w))
			distance += step
			maximum_step = maxf(maximum_step, step)
			previous = q
		var excess := distance - direct
		print("LISTEN_PATH ", name, " direct=", rad_to_deg(direct), " travelled=", rad_to_deg(distance), " excess=", rad_to_deg(excess), " delta=", first.inverse() * last)
		# This simple, single-direction raise/tuck must not roll out and back.
		if excess > deg_to_rad(2.0) or maximum_step > deg_to_rad(1.0):
			push_error("LISTEN_PATH_FAIL unnecessary rotation detour or velocity: " + name)
			failed = true
	print("LISTEN_PATH_FAIL" if failed else "LISTEN_PATH_OK")
	quit(1 if failed else 0)
