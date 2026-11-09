extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var scene := load("res://main.tscn") as PackedScene
	var runtime = scene.instantiate()
	root.add_child(runtime)
	var ui = runtime.interaction_ui
	ui.chat_panel.show()
	var body := "周遥，368分。"
	runtime._handle_core_event({"type":"chat.response","text":body,"channel":"task","emotion":"happy","emotion_intensity":0.73,"gesture":"nod"})
	var visible_answer := false
	for label in ui.bubbles_box.find_children("*","Label",true,false):
		if label.text == body and label.is_visible_in_tree():
			visible_answer = true
	runtime._handle_core_event({"type":"agent.state","state":"idle"})
	runtime._handle_core_event({"type":"avatar.command","event":"avatar.smile","payload":{"intensity":0.73}})
	runtime._handle_core_event({"type":"avatar.command","event":"avatar.nod","payload":{}})
	if not visible_answer or runtime.expression_name != "微笑" or runtime.action_name != "nod":
		push_error("Query response, smile or nod missing")
		quit(1)
		return
	runtime._handle_core_event({"type":"agent.state","state":"speaking"})
	if not is_equal_approx(float(runtime.expression_targets["笑い"]),0.73):
		push_error("Speech transition discarded the reply expression")
		quit(1)
		return
	runtime._process_expressions(0.12)
	if runtime.face_mesh.get_blend_shape_value(runtime.expression_ids["笑い"]) <= 0.0:
		push_error("No weight reached the visible mesh")
		quit(1)
		return
	runtime._handle_core_event({"type":"agent.state","state":"thinking"})
	if is_equal_approx(float(runtime.expression_targets["笑い"]),0.73):
		push_error("Old smile carried into the next thinking turn")
		quit(1)
		return
	print("QUERY_EXPRESSION_OK bubble=true intensity=0.73 nod=true speaking_mesh=true old_turn_cleared=true")
	quit()
