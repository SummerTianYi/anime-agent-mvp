extends SceneTree
## Codex: regression for short audio truncating the wave and vice versa.
const Preview = preload("res://lookdev/render_candidate.gd")
const Exit = preload("res://farewell_exit.gd")
const Gate = preload("res://farewell_speech_gate.gd")
class TestRuntime extends Preview.OfflineRuntime:
	var reasons: Array[String] = []
	func _finish_exit(reason: String) -> void:
		if not exit_committed:
			exit_committed = true
			reasons.append(reason)
	func _process_core_bridge(_delta: float) -> void:
		pass
	func _save_window_position() -> void:
		pass
var failures: Array[String] = []
var checks := 0
func check(value: bool, message: String) -> void:
	checks += 1
	if not value:
		failures.append(message)
func part(id: String = "exit-test", index: int = 0, count: int = 1) -> Dictionary:
	return {"requestId":id,"utteranceId":"utt-test","partIndex":index,"partCount":count,
		"audioPath":ProjectSettings.globalize_path("user://farewell-test.wav")}
func _init() -> void:
	call_deferred("run")
func run() -> void:
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_16_BITS
	wav.mix_rate = 16000
	var pcm := PackedByteArray()
	pcm.resize(3200)
	wav.data = pcm
	check(wav.save_to_wav("user://farewell-test.wav") == OK, "private test WAV")
	var r = load("res://main.tscn").instantiate()
	r.set_script(TestRuntime)
	root.add_child(r)
	AudioServer.set_bus_mute(0, true)
	for mode in ["short", "long", "multipart", "unavailable", "missing", "interrupted", "wrong-id"]:
		r.farewell_exit = Exit.new()
		r.exit_committed = false
		r.reasons.clear()
		r.current_utterance_id = ""
		r.request_exit()
		r.farewell_exit.speech_gate.expect_speech("exit-test")
		var payload := part("exit-test", 0, 2 if mode == "multipart" else 1)
		if mode == "missing":
			payload.audioPath = "user://definitely-missing-farewell.wav"
		r._handle_core_event(part("exit-stale")) # wrong event type cannot alter state
		r._handle_core_event({"type":"avatar.speak","requestId":"exit-stale","utteranceId":"late"})
		check(r.current_utterance_id.is_empty(), "reject unrelated audio " + mode)
		payload.type = "avatar.speak"
		if mode != "unavailable" and mode != "wrong-id":
			r._handle_core_event(payload)
		if mode in ["short", "multipart"]:
			r._on_speech_finished()
		elif mode == "interrupted":
			r._handle_core_event({"type":"avatar.speech.stop","utteranceId":"utt-test"})
		elif mode in ["unavailable", "wrong-id"]:
			r._handle_core_event({"type":"avatar.farewell.status","requestId":"exit-stale" if mode == "wrong-id" else "exit-test","state":"unavailable"})
		check(not r.exit_committed, "voice must not truncate animation " + mode)
		for frame in 493:
			r._process(1.0 / 120.0)
		if mode in ["long", "multipart", "wrong-id"]:
			check(not r.exit_committed, "animation must await own full speech " + mode)
			if mode == "multipart":
				var last := part("exit-test", 1, 2)
				last.type = "avatar.speak"
				r._handle_core_event(last)
			if mode == "wrong-id":
				r._handle_core_event({"type":"avatar.farewell.status","requestId":"exit-test","state":"unavailable"})
			else:
				r._on_speech_finished()
		check(r.reasons == ["animation_finished"], "joined exit exactly once " + mode)
		r._on_speech_finished()
		r.request_exit()
		check(r.reasons.size() == 1, "duplicate completion/close safe " + mode)
	var gate = Gate.new()
	gate.expect_speech("exit-test")
	check(not gate.accept_part(part("exit-stale")), "stale request")
	check(not gate.accept_part(part("exit-test", 1, 2)), "out of order part")
	var malformed := part()
	malformed.partCount = null
	check(not gate.accept_part(malformed), "null count rejected")
	malformed.partCount = 1.5
	check(not gate.accept_part(malformed), "fractional count rejected")
	check(gate.accept_part(part("exit-test", 0, 2)), "first part")
	check(not gate.accept_part(part("exit-test", 0, 2)), "duplicate active part")
	gate.finish_part("wrong-utterance")
	check(not gate.speech_done, "wrong completion")
	gate.finish_part("utt-test")
	check(not gate.accept_part(part("exit-test", 0, 2)), "replayed completed part")
	check(not gate.accept_part(part("exit-test", 1, 3)), "part count cannot change")
	check(gate.accept_part(part("exit-test", 1, 2)), "last part")
	gate.animation_done = true
	gate.unavailable("exit-test")
	check(not gate.ready(), "failure cannot truncate playing audio")
	gate.finish_part("utt-test")
	check(gate.ready(), "complete multipart")
	check(FileAccess.get_sha256(Exit.PATH) == Exit.SHA256, "approved motion unchanged")
	check(FileAccess.get_sha256("res://assets/luotianyi_v4.glb") == Preview.SHA, "official model unchanged")
	print("FAREWELL_SPEECH_REGRESSION ", JSON.stringify({"checks":checks,"failures":failures}))
	r.free()
	quit(0 if failures.is_empty() else 1)
