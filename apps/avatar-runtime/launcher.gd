extends SceneTree


func _init() -> void:
	print("GODOT_LAUNCHER_STARTED")
	var scene := load("res://main.tscn") as PackedScene
	if scene == null:
		push_error("Unable to load res://main.tscn")
		quit(1)
		return

	root.add_child(scene.instantiate())
	print("GODOT_SCENE_INSTANTIATED")
