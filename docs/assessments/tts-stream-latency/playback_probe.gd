extends SceneTree
# Isolated audio-only Godot project. No 3D scene, network, microphone or desktop state.
class VoiceHost extends "res://runtime.gd":
	var receipts: Array = []
	func _ready() -> void:
		set_process(false)
		set_physics_process(false)
	func _exit_tree() -> void:
		pass
	func _send_speech_receipt(receipt: Dictionary) -> void:
		receipts.append(receipt.duplicate())

var host: VoiceHost
var tap: AudioEffectCapture
var results: Array = []
var failures: Array = []
var path := OS.get_environment("PROBE_WAV")
var output := OS.get_environment("PROBE_RESULT")

func _initialize() -> void:
	call_deferred("_run")

func elapsed(start: int) -> float:
	return (Time.get_ticks_usec() - start) / 1000.0

func nonzero() -> bool:
	var n := tap.get_frames_available()
	if n == 0:
		return false
	for v in tap.get_buffer(n):
		if maxf(absf(v.x), absf(v.y)) > 0.002:
			return true
	return false

func verify(ok: bool, label: String) -> void:
	if not ok:
		failures.append(label)

func payload(id: String, file: String) -> Dictionary:
	return {"utteranceId":id, "playbackId":id+"-0", "audioPath":file, "partIndex":0}

func wave(id: String, interrupt: bool) -> void:
	tap.clear_buffer()
	var begin := Time.get_ticks_usec()
	var idx := host.receipts.size()
	var message := payload(id,path)
	host._handle_avatar_speak(message)
	var load_ms := elapsed(begin)
	host._handle_avatar_speak(message)
	var first := -1.0
	var cancelled := false
	while host.receipts.size() == idx and elapsed(begin) < 15000:
		if nonzero() and first < 0:
			first = elapsed(begin)
		if interrupt and first > 0 and elapsed(begin) >= first + 130 and not cancelled:
			host._handle_speech_stop({"utteranceId":id})
			cancelled = true
		await process_frame
	var receipt: Dictionary = host.receipts.back() if host.receipts.size() > idx else {}
	verify(first >= 0 and receipt.get("type") == "speech.finished" and receipt.get("interrupted") == interrupt, id)
	results.append({"case":id,"call_ms":load_ms,"bus_first_ms":first,"receipt_ms":elapsed(begin),"receipt":receipt})
	await create_timer(0.14).timeout

# Replay the identical PCM progressively at real-time cadence. This measures the
# ring buffer and device only. Input is pre-synthesized; no inference speed claim.
func chunks(id: String, abort: bool) -> void:
	var wav := AudioStreamWAV.load_from_file(path)
	verify(wav.format == AudioStreamWAV.FORMAT_16_BITS and not wav.stereo, "fixture format")
	var data := wav.data
	var frames := int(data.size()/2)
	var gen := AudioStreamGenerator.new()
	gen.mix_rate = wav.mix_rate
	gen.buffer_length = 0.30
	var player := AudioStreamPlayer.new()
	player.bus = host.speech_player.bus
	player.stream = gen
	root.add_child(player)
	tap.clear_buffer()
	var begin := Time.get_ticks_usec()
	player.play()
	var ring = player.get_stream_playback()
	var written := 0
	var first := -1.0
	var released := 0
	var skips_in_audio := 0
	var last_feed_ms := -1.0
	while elapsed(begin) < wav.get_length()*1000+1500:
		var t := elapsed(begin)
		# 100 ms initial buffer followed by 20 ms packets. Generator is in
		#-process so this does not include network or sidecar synthesis time.
		released = mini(frames, int((100+floor(t/20.0)*20)*wav.mix_rate/1000.0))
		var count := mini(int(ring.get_frames_available()), released-written)
		if count > 0:
			var packet := PackedVector2Array()
			packet.resize(count)
			for j in count:
				var sample_value := data.decode_s16(2*(written+j))/32768.0
				packet[j] = Vector2(sample_value,sample_value)
			if ring.push_buffer(packet):
				written += count
				last_feed_ms = t
		if nonzero() and first < 0:
			first = elapsed(begin)
		if written < frames:
			skips_in_audio = ring.get_skips()
		if abort and first > 0 and t > first + 130:
			player.stop()
			break
		if written == frames and t > wav.get_length()*1000 + AudioServer.get_output_latency()*1000 + 80:
			break
		await process_frame
	verify(first >= 0 and (written < frames if abort else written == frames),id)
	results.append({"case":id,"bus_first_ms":first,"stop_ms":elapsed(begin),"last_feed_ms":last_feed_ms,
		"frames_written":written,"frames_in_fixture":frames,"skips_before_last_feed":skips_in_audio,"cancelled":abort})
	player.stop()
	player.queue_free()
	await create_timer(0.14).timeout

func _run() -> void:
	host = VoiceHost.new()
	for pair in [["LuoTianyi",Node3D.new()],["Camera3D",Camera3D.new()],["Environment",WorldEnvironment.new()],["KeyLight",DirectionalLight3D.new()],["FillLight",DirectionalLight3D.new()]]:
		pair[1].name = pair[0]
		host.add_child(pair[1])
	root.add_child(host)
	var bus_name = preload("res://speech_output.gd").configure_from_environment()
	var index := AudioServer.get_bus_index(bus_name)
	tap = AudioEffectCapture.new()
	tap.buffer_length = 0.25
	AudioServer.add_bus_effect(index,tap)
	var driver := AudioServer.get_driver_name()
	if driver != "WASAPI":
		verify(false,"physical playback requires WASAPI")
	elif OS.get_environment("PROBE_GAPS") == "1":
		for length in [2,4]:
			for repeat in 2:
				await continuous(length,repeat)
	else:
		await wave("wav-1",false)
		await chunks("pcm-1",false)
		await wave("wav-2",false)
		await chunks("pcm-2",false)
		await wave("wav-cancel",true)
		await chunks("pcm-cancel",true)
		host._handle_avatar_speak(payload("bad",""))
		verify(host.receipts.back().get("type")=="speech.failed","failed receipt")
		await wave("recovery",false)
	var report := {"driver":driver,"output_latency_ms":AudioServer.get_output_latency()*1000,"gain_db":OS.get_environment("ANIME_AGENT_SPEECH_GAIN_DB"),
		"measurements":results,"failures":failures,"all_runtime_receipts":host.receipts}
	var f := FileAccess.open(output,FileAccess.WRITE)
	f.store_line(JSON.stringify(report,"  "))
	f.close()
	print("AUDIO_PROBE ",driver," rows=",results.size()," failures=",failures)
	quit(0 if failures.is_empty() else 1)

# Ready WAV parts delivered immediately on receipt. No deliberate inter-part delay.
func continuous(length: int, repeat: int) -> void:
	var begin := Time.get_ticks_usec()
	var previous_loud := -1.0
	var gaps: Array = []
	var first := -1.0
	for part in length:
		var id := "con-%d-%d-%d" % [length,repeat,part]
		var before := host.receipts.size()
		var seen := false
		host._handle_avatar_speak(payload(id,path))
		while host.receipts.size() == before and elapsed(begin) < 60000:
			if nonzero():
				var t := elapsed(begin)
				if not seen:
					if first < 0:
						first = t
					elif previous_loud >= 0:
						gaps.append(t-previous_loud)
					seen = true
				previous_loud = t
			await process_frame
		verify(seen and host.receipts.size()==before+1,id)
	results.append({"case":"consecutive-ready-WAV","parts":length,"repeat":repeat,"bus_first_ms":first,
		"elapsed_ms":elapsed(begin),"interpart_last_to_first_nonzero_ms":gaps})
	await create_timer(0.15).timeout
