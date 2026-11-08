extends SceneTree

# Replay only recorded text delivery events. The runtime stays outside the tree,
# so its connection, microphone and avatar startup never run.
func _initialize() -> void:
	call_deferred("_read")

func _read() -> void:
	var directory := OS.get_environment("COMPANION_EVAL_DIR")
	var input := FileAccess.open(directory.path_join("dialogues.jsonl"), FileAccess.READ)
	var runtime = load("res://runtime.gd").new()
	var ui = load("res://interaction_ui.gd").new(runtime)
	root.add_child(ui)
	runtime.interaction_ui = ui
	var rows: Array = []
	while input.get_position() < input.get_length():
		var line := input.get_line()
		if line.is_empty():
			continue
		var turn: Dictionary = JSON.parse_string(line)
		var bubbles: Array = []
		for event in turn.delivery_events:
			var kind := str(event.type)
			if kind not in ["core.error", "chat.response"]:
				continue
			ui._remove_empty_hint()
			var previous := int(ui.bubbles_box.get_child_count())
			runtime._handle_core_event(event)
			if ui.bubbles_box.get_child_count() != previous + 1:
				push_error("Missing added row: " + str(turn.id))
				quit(1)
				return
			var row: Node = ui.bubbles_box.get_child(-1)
			var content: Label = row.get_child(1).get_child(0).get_child(0)
			var expected := str(event.get("text", event.get("message", ""))).strip_edges()
			if content.text != expected:
				push_error("Text mismatch: " + str(turn.id))
				quit(1)
				return
			bubbles.append({"type":kind, "text":content.text})
		rows.append({"id":turn.id, "bubbles":bubbles})
	await process_frame
	var out := FileAccess.open(directory.path_join("ui_text.json"), FileAccess.WRITE)
	out.store_line(JSON.stringify(rows, "\t", false))
	out.close()
	print("CHAT_WIDGET_ROWS_READ ", rows.size())
	runtime.free()
	quit(0)
