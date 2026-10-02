extends SceneTree
## Codex: real runtime player, isolated project only, no production bridge/data.
const Preview = preload("res://lookdev/render_candidate.gd")
const Exit = preload("res://farewell_exit.gd")
class TestRuntime extends Preview.OfflineRuntime:
	var receipts: Array[Dictionary] = []
	var exits: Array[String] = []
	func _send_speech_receipt(receipt: Dictionary) -> void:
		receipts.append(receipt.duplicate())
	func _process_core_bridge(_delta: float) -> void:
		pass
	func _finish_exit(reason: String) -> void:
		if not exit_committed:
			exit_committed = true
			exits.append(reason)
	func _save_window_position() -> void:
		pass
var checks := 0
var failures: Array[String] = []
func check(value: bool, label: String) -> void:
	checks += 1
	if not value:
		failures.append(label)
func _init() -> void:
	call_deferred("run")
func run() -> void:
	if not FileAccess.file_exists("res://../../.farewell-test-fixture"):
		push_error("Requires disposable fixture")
		quit(1)
		return
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_16_BITS
	wav.mix_rate = 16000
	var pcm := PackedByteArray()
	pcm.resize(3200)
	wav.data = pcm
	var path := ProjectSettings.globalize_path("user://speech-delivery-test.wav")
	check(wav.save_to_wav(path) == OK, "private wav")
	var r = load("res://main.tscn").instantiate()
	r.set_script(TestRuntime)
	root.add_child(r)
	AudioServer.set_bus_mute(0, true)
	var p := {"utteranceId":"utt-test", "playbackId":"part-0", "requestId":"test",
		"partIndex":0,"partCount":1,"audioPath":path}
	r._handle_avatar_speak(p)
	check(r.speech_player.playing, "actual player starts")
	r._handle_avatar_speak(p)
	check(r.receipts.is_empty(), "duplicate active frame does not interrupt")
	r._on_speech_finished()
	check(r.receipts.size() == 1 and not r.receipts[0].interrupted, "natural completion receipt")
	r._handle_avatar_speak(p)
	check(r.receipts.size() == 2, "lost completion can be resent")
	check(r.current_utterance_id.is_empty(), "completed duplicate never replays")
	var bad := p.duplicate()
	bad.playbackId = "missing"
	bad.audioPath = path + ".missing"
	r._handle_avatar_speak(bad)
	check(r.receipts[-1].type == "speech.failed", "ordinary missing file explicit failure")
	bad.playbackId = "bad-wav"
	bad.audioPath = ProjectSettings.globalize_path("user://invalid.wav")
	var f := FileAccess.open(bad.audioPath, FileAccess.WRITE)
	f.store_string("invalid WAV fixture")
	f.close()
	r._handle_avatar_speak(bad)
	check(r.receipts[-1].type == "speech.failed", "corrupt file explicit failure")
	p.playbackId = "interrupt"
	r._handle_avatar_speak(p)
	r._handle_speech_stop({"utteranceId":"utt-test"})
	check(r.receipts[-1].interrupted, "stop is not success")
	r._cache_farewell_voice({"audioPath":path,"text":"再见。"})
	check(r.farewell_voice_cache.size() == 1, "farewell preloaded")
	check(DirAccess.remove_absolute(path) == OK, "remove only own temporary test file")
	r.farewell_exit = Exit.new()
	r.request_exit()
	check(r.speech_player.playing, "farewell plays without Core and without file")
	r._on_speech_finished()
	check(not r.exit_committed, "voice does not truncate farewell motion")
	for frame in 493:
		r._process(1.0 / 120.0)
	check(r.exits == ["animation_finished"], "farewell audio and motion join")
	check(FileAccess.get_sha256(Exit.PATH) == Exit.SHA256, "motion unchanged")
	check(FileAccess.get_sha256("res://assets/luotianyi_v4.glb") == Preview.SHA, "model unchanged")
	print("SPEECH_DELIVERY_REGRESSION ", JSON.stringify({"checks":checks,"failures":failures}))
	r.free()
	quit(0 if failures.is_empty() else 1)
