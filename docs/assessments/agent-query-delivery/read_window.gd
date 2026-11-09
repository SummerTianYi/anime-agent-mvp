extends SceneTree
# An actual isolated window. Only the probe owns its WebSocket and never plays audio.
var socket := WebSocketPeer.new()
var runtime
var ui
var log_file: FileAccess
var greeted := false

func _initialize() -> void:
	call_deferred("start")

func start() -> void:
	root.title = "天依 · 隔离查询验收"
	root.always_on_top = false
	root.borderless = false
	root.size = Vector2i(560, 720)
	runtime = load("res://runtime.gd").new()
	ui = load("res://interaction_ui.gd").new(runtime)
	root.add_child(ui)
	runtime.interaction_ui = ui
	ui.chat_panel.show()
	log_file = FileAccess.open(OS.get_environment("QUERY_WINDOW_LOG"), FileAccess.WRITE)
	var url := OS.get_environment("AGENT_CORE_WS_URL")
	if not url.begins_with("ws://127.0.0.1:") or socket.connect_to_url(url) != OK:
		quit(2)

func _process(_delta: float) -> bool:
	if log_file == null:
		return false
	socket.poll()
	if socket.get_ready_state() == WebSocketPeer.STATE_CLOSED:
		quit()
		return false
	if socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
		return false
	if not greeted:
		socket.send_text(JSON.stringify({"type":"client.hello","role":"avatar"}))
		greeted = true
	while socket.get_available_packet_count() > 0:
		var packet = JSON.parse_string(socket.get_packet().get_string_from_utf8())
		if not packet is Dictionary:
			continue
		var kind: String = packet.get("type","")
		if kind == "client.ready":
			log_file.store_line(JSON.stringify({"ready":true}))
			log_file.flush()
		if kind in ["session.switched","permission.pending","agent.tool","chat.response","core.error"]:
			runtime._handle_core_event(packet)
		if kind in ["agent.tool","chat.response","core.error"]:
			var values: Array = []
			for label in ui.bubbles_box.find_children("*","Label",true,false):
				values.append(label.text)
			log_file.store_line(JSON.stringify({"request":packet.get("request_id",""),"type":kind,
				"labels":values,"status":ui.chat_status.text,"session":ui.current_conversation_id}))
			log_file.flush()
	return false

func _finalize() -> void:
	if runtime != null:
		runtime.free()
