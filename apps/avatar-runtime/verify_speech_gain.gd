extends SceneTree
## Isolated audio-server regression: no microphone, Core or model calls.
const Output = preload("res://speech_output.gd")
var failures: Array[String] = []
var checks := 0
var results: Array[Dictionary] = []

func check(ok: bool, label: String) -> void:
	checks += 1
	if not ok:
		failures.append(label)

func _init() -> void:
	call_deferred("run")

func run() -> void:
	var directory := OS.get_environment("SPEECH_GAIN_TEST_DIR")
	if directory.is_empty() or not FileAccess.file_exists(directory.path_join(".voice-gain-fixture")):
		push_error("Requires owned voice-gain fixture")
		quit(1)
		return
	var master_db := AudioServer.get_bus_volume_db(0)
	# Mute only this isolated process's final output; capture precedes Master.
	AudioServer.set_bus_mute(0, true)
	check(Output.parse_gain("") == 3.0, "default +3 dB")
	check(Output.parse_gain(" 0 ") == 0.0, "original gain selected")
	check(Output.parse_gain("6") == 6.0, "+6 dB accepted")
	check(Output.parse_gain("99") == 6.0, "upper bound")
	check(Output.parse_gain("-99") == -12.0, "lower bound")
	check(Output.parse_gain("garbage") == 3.0, "invalid falls back")
	check(Output.parse_gain("1e999") == 3.0, "nonfinite rejected")
	var count_before := AudioServer.bus_count
	Output.configure(3.0)
	var index := AudioServer.get_bus_index(Output.BUS_NAME)
	Output.configure(6.0)
	check(AudioServer.bus_count == count_before + 1, "one voice bus only")
	check(AudioServer.get_bus_effect_count(index) == 1, "one limiter only")
	check(AudioServer.get_bus_send(index) == &"Master", "voice routed to Master")
	check(AudioServer.get_bus_volume_db(0) == master_db, "Master volume unchanged")
	Output.configure(0.0)
	check(not AudioServer.is_bus_effect_enabled(index, 0), "zero bypasses limiter")
	var capture := AudioEffectCapture.new()
	capture.buffer_length = 30.0
	AudioServer.add_bus_effect(index, capture)
	for name in ["ack", "short", "long", "peak-probe"]:
		var wav := AudioStreamWAV.load_from_file(directory.path_join(name + ".wav"))
		check(wav != null, name + " fixture loads")
		if wav == null:
			continue
		for gain in [0.0, 3.0, 6.0]:
			Output.configure(gain)
			capture.clear_buffer()
			var player := AudioStreamPlayer.new()
			player.bus = Output.BUS_NAME
			player.stream = wav
			root.add_child(player)
			player.play()
			await create_timer(wav.get_length() + 0.25).timeout
			player.stop()
			var frames := capture.get_buffer(capture.get_frames_available())
			check(frames.size() > 1000, name + " audio actually mixed")
			var peak := 0.0
			var square := 0.0
			var pcm := PackedByteArray()
			pcm.resize(frames.size() * 4)
			for n in frames.size():
				peak = maxf(peak, maxf(absf(frames[n].x), absf(frames[n].y)))
				square += (frames[n].x * frames[n].x + frames[n].y * frames[n].y) * 0.5
				pcm.encode_s16(n * 4, int(clampf(frames[n].x, -1.0, 1.0) * 32767.0))
				pcm.encode_s16(n * 4 + 2, int(clampf(frames[n].y, -1.0, 1.0) * 32767.0))
			var rms := sqrt(square / maxf(frames.size(), 1.0))
			if gain > 0:
				check(peak <= db_to_linear(Output.CEILING_DB) + 0.002, name + " bounded peak " + str(gain))
			results.append({"sample": name, "gainDb": gain, "peakDb": linear_to_db(maxf(peak, 0.000001)),
				"rmsDb": linear_to_db(maxf(rms, 0.000001)), "frames": frames.size()})
			var rendered := AudioStreamWAV.new()
			rendered.format = AudioStreamWAV.FORMAT_16_BITS
			rendered.mix_rate = int(AudioServer.get_mix_rate())
			rendered.stereo = true
			rendered.data = pcm
			check(rendered.save_to_wav(directory.path_join(name + "-gain" + str(int(gain)) + ".wav")) == OK, "render saved")
			player.queue_free()
			await process_frame
	# A quiet signal must actually become louder; clipping prevention alone is insufficient.
	for name in ["ack", "short", "long"]:
		var rows := results.filter(func(row: Dictionary) -> bool: return row.sample == name)
		if rows.size() == 3:
			check(rows[1].rmsDb > rows[0].rmsDb + 1.0, name + " audible gain at +3")
			check(rows[2].rmsDb >= rows[1].rmsDb - 0.1, name + " +6 does not reduce level")
	var report := {"checks": checks, "failures": failures, "renders": results}
	var file := FileAccess.open(directory.path_join("godot-gain-result.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "  "))
	file.close()
	print("SPEECH_GAIN_REGRESSION ", JSON.stringify(report))
	quit(0 if failures.is_empty() else 1)
