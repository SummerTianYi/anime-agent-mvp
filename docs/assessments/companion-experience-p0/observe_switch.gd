extends SceneTree

func _initialize() -> void:
	call_deferred("observe")

func observe() -> void:
	if OS.get_environment("AGENT_CORE_WS_URL") != "ws://127.0.0.1:1/ws" or DisplayServer.get_name() != "headless":
		quit(2)
		return
	var role = load("res://main.tscn").instantiate()
	root.add_child(role)
	var ui = role.interaction_ui
	ui.current_conversation_id = 11
	ui._on_new_session_pressed()
	var waiting: int = ui.current_conversation_id
	role._handle_core_event({"type":"chat.response","channel":"task","text":"合成旧任务回执","foreground":false,"conversationId":11})
	var labels: Array[Node] = ui.find_children("*","Label",true,false)
	var delivered := false
	for label in labels:
		if label.text == "合成旧任务回执":
			delivered = true
	print("SWITCH_OBSERVATION ",JSON.stringify({"waiting_id":waiting,"adopted_id":ui.current_conversation_id,"old_label_present":delivered}))
	quit()
