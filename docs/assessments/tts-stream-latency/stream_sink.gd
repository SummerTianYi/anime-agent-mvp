extends SceneTree
# Bench-only localhost PCM receiver. Terminal IDs suppress delayed packets.
var ws := WebSocketPeer.new()
var player := AudioStreamPlayer.new()
var ring: AudioStreamGeneratorPlayback
var stream_id := ""
var terminal := {}
var seq := 0
var eof := false
var queued := PackedVector2Array()
var rate := 0
var capacity := 0
var drain_time := -1
var frames := 0
var started := false
var tap := AudioEffectCapture.new()
var heard := false
var begin_usec := 0
var first_bus_ms := -1.0
var skip_start := 0
var last_skips := 0
var deadline := 0

func _initialize() -> void:
	var port := OS.get_environment("TTS_BENCH_PORT").to_int()
	if port < 1024 or port > 65535 or AudioServer.get_driver_name() != "WASAPI":
		quit(2)
		return
	var bus = preload("res://speech_output.gd").configure_from_environment()
	AudioServer.add_bus_effect(AudioServer.get_bus_index(bus),tap)
	player.bus = bus
	root.add_child(player)
	ws.connect_to_url("ws://127.0.0.1:%d" % port)
	deadline = Time.get_ticks_msec()+240000

func send(data: Dictionary) -> void:
	ws.send_text(JSON.stringify(data))

func finish(kind: String) -> void:
	if stream_id.is_empty():
		return
	var receipt := {"type":kind,"id":stream_id,"frames":frames,"heard_on_bus":heard,"first_bus_ms_from_start":first_bus_ms,"underruns_before_eof":last_skips}
	terminal[stream_id] = receipt
	player.stop()
	ring = null
	queued.clear()
	stream_id = ""
	send(receipt)

func packet(m: Dictionary) -> void:
	var id := str(m.get("id",""))
	var action := str(m.get("type",""))
	if action == "quit":
		quit(0)
		return
	if terminal.has(id):
		if action == "start":
			send(terminal[id])
		return
	if action == "start":
		if id == stream_id:
			return
		finish("interrupted")
		stream_id = id
		begin_usec = Time.get_ticks_usec()
		first_bus_ms = -1.0
		rate = int(m.rate)
		if id.is_empty() or rate < 8000 or rate > 96000:
			finish("failed")
			return
		var gen := AudioStreamGenerator.new()
		gen.mix_rate = rate
		gen.buffer_length = 0.30
		player.stream = gen
		player.play()
		player.stream_paused = true
		ring = player.get_stream_playback()
		capacity = ring.get_frames_available()
		skip_start = ring.get_skips()
		tap.clear_buffer()
		last_skips = 0
		frames = 0
		heard = false
		started = false
		seq = 0
		eof = false
		drain_time = -1
		send({"type":"ready","id":id})
	elif id == stream_id and ring != null:
		if action == "cancel":
			finish("interrupted")
		elif action == "chunk" and not eof:
			var raw := Marshalls.base64_to_raw(str(m.pcm))
			if int(m.seq) != seq or raw.is_empty() or raw.size()%2 != 0 or queued.size()+raw.size()/2 > rate*60:
				finish("failed")
				return
			for i in int(raw.size()/2):
				var sample_value := raw.decode_s16(i*2)/32768.0
				queued.append(Vector2(sample_value,sample_value))
			seq += 1
			frames += int(raw.size()/2)
		elif action == "end" and int(m.get("frames",-1)) == frames and frames > 0:
			eof = true
		else:
			finish("failed")

func _process(_dt: float) -> bool:
	ws.poll()
	if ws.get_ready_state() == WebSocketPeer.STATE_OPEN:
		while ws.get_available_packet_count():
			var m = JSON.parse_string(ws.get_packet().get_string_from_utf8())
			if m is Dictionary:
				packet(m)
	elif ws.get_ready_state() == WebSocketPeer.STATE_CLOSED:
		quit(1)
		return false
	if ring != null:
		var n := mini(queued.size(),ring.get_frames_available())
		if n > 0 and ring.push_buffer(queued.slice(0,n)):
			queued = queued.slice(n)
		if not started and (capacity-ring.get_frames_available() >= rate/10 or eof):
			started = true
			player.stream_paused = false
		if started and not eof:
			last_skips = ring.get_skips()-skip_start
		if not heard and tap.can_get_buffer(1):
			for frame in tap.get_buffer(tap.get_frames_available()):
				if maxf(absf(frame.x),absf(frame.y)) > 0.002:
					heard = true
					first_bus_ms = (Time.get_ticks_usec()-begin_usec)/1000.0
					send({"type":"bus_audio","id":stream_id})
					break
		if eof and queued.is_empty() and ring.get_frames_available() == capacity:
			if drain_time < 0:
				drain_time = Time.get_ticks_msec()
			if Time.get_ticks_msec()-drain_time >= 1000*AudioServer.get_output_latency()+20:
				finish("finished" if heard else "failed")
	if Time.get_ticks_msec() > deadline:
		quit(2)
	return false
