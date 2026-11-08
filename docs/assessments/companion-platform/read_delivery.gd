extends SceneTree

# Use the existing Godot event handler and actual message labels without a network client.
func _initialize() -> void:
	call_deferred("read_deliveries")


func read_deliveries() -> void:
	var path := OS.get_environment("COMPANION_DIALOGUES")
	var phase := OS.get_environment("COMPANION_PHASE")
	var source := FileAccess.open(path,FileAccess.READ)
	var output := FileAccess.open(OS.get_environment("COMPANION_RENDERED"),FileAccess.WRITE)
	if source == null or output == null:
		quit(2)
		return
	var runtime = load("res://runtime.gd").new()
	var ui = load("res://interaction_ui.gd").new(runtime)
	root.add_child(ui)
	runtime.interaction_ui = ui
	var count := 0
	while source.get_position() < source.get_length():
		var row = JSON.parse_string(source.get_line())
		if not row is Dictionary:
			continue
		var id := str(row["id"])
		if (phase == "before") != (id.begins_with("archive-") or id.begins_with("before-") or id.begins_with("fixture-")):
			continue
		var displayed := []
		for e in row["bubbles"]:
			ui.current_conversation_id = int(e["conversationId"])
			ui._remove_empty_hint()
			var old_count: int = ui.bubbles_box.get_child_count()
			runtime._handle_core_event(e)
			if ui.bubbles_box.get_child_count() != old_count + 1:
				push_error(id + ": missing message")
				quit(3)
				return
			var observed := ""
			var marker := ""
			for label in ui.bubbles_box.get_child(-1).find_children("*","Label",true,false):
				if label.text == e["text"]:
					observed = label.text
				if label.text in ["操作回执","记忆回执"]:
					marker = label.text
			var expected_marker: String = {"task":"操作回执","memory":"记忆回执"}.get(e.get("channel",""),"")
			if observed.is_empty() or marker != expected_marker:
				push_error(id + ": text or receipt label differs")
				quit(4)
				return
			displayed.append({"text":observed,"label":marker})
			count += 1
		output.store_line(JSON.stringify({"id":id,"display":displayed}))
	output.close()
	print("GODOT_DELIVERY_LABELS_OK ",count)
	runtime.free()
	quit(0)
