extends SceneTree
## Codex: merge the owner's approved, immutable body/hair takes. No live solver.
const SOURCES := [
	["final-detail/thinking_preview.tres", "6b6e4a15c1f531a5a727408adbee77b84306c038b5953708922c57345c3a9eb2", 74],
	["review11/hair_return_preview.tres", "1f77d1eb52b7066d09ea8b711efe72781ecfc50575414bff1f24c6bd45849e51", 34],
]
const DEST := "res://assets/motions/thinking_reference_v1.tres"
func _init() -> void:
	var source_root := OS.get_environment("THINKING_APPROVED_ROOT")
	if source_root.is_empty() or FileAccess.file_exists(DEST):
		push_error("Supply THINKING_APPROVED_ROOT; destination must not exist (immutable release)")
		quit(1)
		return
	var merged := Animation.new()
	merged.length = 9.5
	merged.loop_mode = Animation.LOOP_NONE
	var bones := {}
	for entry in SOURCES:
		var path: String = source_root.path_join(entry[0])
		if FileAccess.get_sha256(path) != entry[1]:
			push_error("Unapproved source: " + path)
			quit(1)
			return
		var clip := load(path) as Animation
		assert(clip != null and clip.get_track_count() == entry[2] and is_equal_approx(clip.length, 9.5))
		for track in clip.get_track_count():
			var bone := String(clip.track_get_path(track).get_subname(0))
			assert(not bones.has(bone) and clip.track_get_type(track) == Animation.TYPE_ROTATION_3D)
			bones[bone] = true
			clip.copy_track(track, merged)
	assert(merged.get_track_count() == 108)
	assert(ResourceSaver.save(merged, DEST) == OK)
	var saved := ResourceLoader.load(DEST, "Animation", ResourceLoader.CACHE_MODE_IGNORE) as Animation
	for track in merged.get_track_count():
		assert(saved.track_get_path(track) == merged.track_get_path(track))
		assert(saved.track_get_key_count(track) == merged.track_get_key_count(track))
		for key in merged.track_get_key_count(track):
			assert(is_equal_approx(saved.track_get_key_time(track, key), merged.track_get_key_time(track, key)))
			var a: Quaternion = saved.track_get_key_value(track, key)
			var c: Quaternion = merged.track_get_key_value(track, key)
			assert(a.is_equal_approx(c))
	print("THINKING_FREEZE_PASS tracks=108 length=9.5 sha256=", FileAccess.get_sha256(DEST))
	quit()
