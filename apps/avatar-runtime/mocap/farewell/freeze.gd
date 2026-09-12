extends SceneTree
## Codex: preserve the accepted animation byte-for-byte; never overwrite a version.
const Exit = preload("res://farewell_exit.gd")
func _init() -> void:
	var source := OS.get_environment("FAREWELL_APPROVED_TRES")
	if source.is_empty() or FileAccess.get_sha256(source) != Exit.SHA256:
		push_error("FAREWELL_APPROVED_TRES must point to the exact accepted v3 TRES")
		quit(1)
		return
	if FileAccess.file_exists(Exit.PATH):
		if FileAccess.get_sha256(Exit.PATH) == Exit.SHA256:
			print("FAREWELL_FREEZE_PASS already installed: ", Exit.SHA256)
			quit()
		else:
			push_error("Refusing to overwrite existing farewell release")
			quit(1)
		return
	var dest := ProjectSettings.globalize_path(Exit.PATH)
	if DirAccess.make_dir_recursive_absolute(dest.get_base_dir()) != OK or DirAccess.copy_absolute(source, dest) != OK:
		push_error("Could not install farewell asset")
		quit(1)
		return
	if FileAccess.get_sha256(dest) != Exit.SHA256:
		push_error("Farewell copy verification failed")
		quit(1)
		return
	print("FAREWELL_FREEZE_PASS ", Exit.SHA256)
	quit()
