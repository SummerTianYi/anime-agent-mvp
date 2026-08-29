extends SceneTree


const EXPECTED_TEXT := "inputcheckready"


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var scene := load("res://main.tscn") as PackedScene
	if scene == null:
		_fail("Unable to load main scene")
		return

	var runtime := scene.instantiate()
	root.add_child(runtime)
	var interaction_ui: Node = runtime.interaction_ui
	if interaction_ui == null or interaction_ui.chat_input == null:
		_fail("Chat input was not created")
		return

	interaction_ui._open_chat()
	if not interaction_ui.chat_input.has_focus():
		_fail("Chat input did not acquire focus")
		return

	if DisplayServer.get_name() != "headless":
		DisplayServer.window_set_title("Anime Agent Text Input E2E")
		DisplayServer.window_set_position(Vector2i(100, 100))
		DisplayServer.window_move_to_foreground()
		print("GODOT_CHAT_TEXT_INPUT_WAITING", EXPECTED_TEXT)
		_wait_for_visible_text(interaction_ui)
		return

	var yaw_before: float = runtime.target_yaw
	var press := InputEventKey.new()
	press.pressed = true
	press.keycode = KEY_A
	press.physical_keycode = KEY_A
	press.unicode = 97
	runtime._input(press)
	if not is_equal_approx(runtime.target_yaw, yaw_before):
		_fail("Typing 'a' triggered the avatar turn shortcut")
		return

	print("GODOT_CHAT_SHORTCUT_GUARD_OK", {
		"focus": interaction_ui.chat_input.has_focus(),
		"avatar_shortcut_blocked": true,
	})
	quit(0)


func _wait_for_visible_text(interaction_ui: Node) -> void:
	var started_at := Time.get_ticks_msec()
	while Time.get_ticks_msec() - started_at < 30000:
		await process_frame
		if interaction_ui.chat_input.text == EXPECTED_TEXT:
			print("GODOT_CHAT_TEXT_INPUT_OK", {
				"text": interaction_ui.chat_input.text,
				"os_keyboard_input": true,
			})
			interaction_ui._send_current_message()
			await process_frame
			quit(0)
			return
	_fail("Timed out waiting for exact OS keyboard input")


func _fail(message: String) -> void:
	push_error(message)
	quit(1)
