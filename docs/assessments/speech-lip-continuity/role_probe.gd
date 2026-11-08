extends SceneTree
# Isolate only desktop integration. The inherited per-frame animation, expression
# mixer, actual mesh, WAV playback and receipt code run normally.
class LocalRole extends "res://runtime.gd":
	var received := []
	func _ready() -> void:
		process_priority = 100
		base_model_position = model.position
		base_model_rotation = model.rotation
		skeleton = _find_skeleton(model)
		_cache_bones()
		_cache_deform_bone_mirrors()
		_cache_expressions()
		_configure_model_look()
		_restore_bone_poses()
		_cache_action_axes()
		_prepare_authored_motions()
		_play_default_idle_motion()
		current_distance = 2.0
		target_distance = 2.0
		camera.fov = 14
		camera.v_offset = 0.58
	func _process_core_bridge(_delta: float) -> void:
		pass
	func _update_mouse_passthrough(_force: bool = false) -> void:
		pass
	func _send_speech_receipt(receipt: Dictionary) -> void:
		received.append(receipt.duplicate())
	func _save_window_position() -> void:
		pass

var role
var folder := OS.get_environment("LIP_TRACE")
var started := 0
var phase := ""
var rows := []
var tap := AudioEffectCapture.new()
var recording := AudioEffectRecord.new()
var last_shot := -100
var shots := []
var run_id := ""
var wav := OS.get_environment("LIP_WAV")
var peer := StreamPeerTCP.new()
var pending_line := ""

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	if DisplayServer.get_name()=="headless" or AudioServer.get_driver_name()!="WASAPI":
		quit(2)
		return
	root.title = "Tianyi - isolated voice sync"
	root.always_on_top = false
	root.borderless = false
	root.transparent = false
	root.size = Vector2i(420,400)
	root.content_scale_size = Vector2i(420,400)
	root.position = Vector2i(32,64)
	root.transparent_bg = false
	root.msaa_3d = Viewport.MSAA_DISABLED
	role = load("res://main.tscn").instantiate()
	role.set_script(LocalRole)
	root.add_child(role)
	await create_timer(0.7).timeout
	var name = preload("res://speech_output.gd").configure_from_environment()
	var bus := AudioServer.get_bus_index(name)
	tap.buffer_length = 0.25
	AudioServer.add_bus_effect(bus,tap)
	AudioServer.add_bus_effect(bus,recording)
	tap.clear_buffer()
	if OS.has_environment("LIP_BENCH_PORT"):
		await run_bench(int(OS.get_environment("LIP_BENCH_PORT")))
		return
	started = Time.get_ticks_msec()
	recording.set_recording_active(true)
	RenderingServer.frame_post_draw.connect(sample)
	role._set_agent_state("speaking")
	phase="wait"
	await create_timer(0.65).timeout
	play("one")
	phase="file"
	await until_receipt()
	phase="gap"
	await create_timer(0.7).timeout
	play("cancel")
	phase="playing-before-cancel"
	await create_timer(0.48).timeout
	role._handle_speech_stop({"utteranceId":"cancel"})
	phase="cancelled"
	await create_timer(0.45).timeout
	role._handle_avatar_speak({"utteranceId":"failed","playbackId":"bad","audioPath":""})
	phase="failed"
	role._trigger_blink()
	await create_timer(0.45).timeout
	if "retired_utterances" in role:
		play("new")
		phase="replacement"
		await create_timer(0.25).timeout
		role._handle_avatar_speak({"utteranceId":"cancel","playbackId":"late-unseen","audioPath":wav})
		if role.current_utterance_id!="new" or not role.speech_player.playing:
			quit(4)
			return
		role._handle_speech_stop({"utteranceId":"new"})
		phase="replacement-stopped"
		await create_timer(0.2).timeout
	recording.set_recording_active(false)
	var clip := recording.get_recording()
	clip.save_to_wav(folder+"/window-audio.wav")
	RenderingServer.frame_post_draw.disconnect(sample)
	var evidence={"avatar_bones":role.skeleton.get_bone_count(),"shapes":role.face_mesh.mesh.get_blend_shape_count(),
		"driver":AudioServer.get_driver_name(),"receipts":role.received,"samples":rows,"shots":shots}
	var f=FileAccess.open(folder+"/trace.json",FileAccess.WRITE)
	f.store_line(JSON.stringify(evidence))
	f.close()
	print("VISIBLE_ROLE_TRACE ",rows.size()," frames ",shots.size()," images")
	quit()

func play(id: String) -> void:
	role._handle_avatar_speak({"utteranceId":id,"requestId":"fixture","partIndex":0,"playbackId":id,"audioPath":wav})


# The connection only transports the fixture envelopes. The visible role loads
# the actual WAV, runs its animation and returns its own playback receipts.
func run_bench(port: int) -> void:
	role._set_agent_state("speaking")
	if peer.connect_to_host("127.0.0.1",port) != OK:
		quit(2)
		return
	while peer.get_status()==StreamPeerTCP.STATUS_CONNECTING:
		peer.poll()
		await process_frame
	if peer.get_status()!=StreamPeerTCP.STATUS_CONNECTED:
		quit(2)
		return
	send_line({"type":"ready"})
	var playing_id := ""
	var first_sound := 0
	var last_sound := 0
	while true:
		await process_frame
		peer.poll()
		if peer.get_status()!=StreamPeerTCP.STATUS_CONNECTED:
			quit(3)
			return
		var peak := 0.0
		var n := tap.get_frames_available()
		if n>0:
			for frame in tap.get_buffer(n):
				peak=maxf(peak,maxf(absf(frame.x),absf(frame.y)))
		if peak>0.003 and playing_id!="":
			last_sound=roundi(Time.get_unix_time_from_system()*1000.0)
			if first_sound==0:
				first_sound=last_sound
		while not role.received.is_empty():
			var receipt: Dictionary=role.received.pop_front()
			if receipt.playbackId==playing_id:
				receipt["firstSoundMs"]=first_sound
				receipt["lastSoundMs"]=last_sound
				playing_id=""
			send_line(receipt)
		if peer.get_available_bytes():
			pending_line+=peer.get_string(peer.get_available_bytes())
		while pending_line.contains("\n"):
			var end:=pending_line.find("\n")
			var msg=JSON.parse_string(pending_line.left(end))
			pending_line=pending_line.substr(end+1)
			if msg.type=="quit":
				quit()
				return
			if msg.type=="stop":
				role._handle_speech_stop(msg)
			elif msg.type=="speak":
				role._handle_avatar_speak(msg)
				if role.current_speech_payload.get("playbackId","")==msg.playbackId:
					playing_id=msg.playbackId
					first_sound=0
					last_sound=0


func send_line(msg: Dictionary) -> void:
	peer.put_data((JSON.stringify(msg)+"\n").to_utf8_buffer())

func until_receipt() -> void:
	var t := Time.get_ticks_msec()
	while role.received.is_empty() and Time.get_ticks_msec()-t<12000:
		await process_frame

func sample() -> void:
	var ms := Time.get_ticks_msec()-started
	var mouth := 0.0
	for key in role.SPEAKING_MOUTHS:
		if role.expression_ids.has(key):
			mouth=maxf(mouth,role.face_mesh.get_blend_shape_value(role.expression_ids[key]))
	var peak := 0.0
	var n := tap.get_frames_available()
	if n>0:
		for stereo in tap.get_buffer(n):
			peak=maxf(peak,maxf(absf(stereo.x),absf(stereo.y)))
	var pos := -1.0
	if role.speech_player and role.speech_player.playing:
		pos=role.speech_player.get_playback_position()
	rows.append([ms,phase,mouth,peak,pos,role.expression_values.get("まばたき",0),role.expression_values.get("笑い",0)])
	if ms-last_shot>=65:
		root.get_texture().get_image().save_jpg(folder+"/%04d.jpg" % shots.size(),0.84)
		shots.append(ms)
		last_shot=ms
