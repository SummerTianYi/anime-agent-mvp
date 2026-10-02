extends "res://mocap/farewell/exit_probe.gd"
## Codex test-only fault controls. Parent rejects non-disposable projects.
var control_seen := ""
var drop_receipts := 0
var disconnect_receipt := false
func _send_speech_receipt(receipt: Dictionary) -> void:
	_record_tts({"event":"receipt", "receipt":receipt})
	if drop_receipts > 0:
		drop_receipts -= 1
		return
	if disconnect_receipt:
		disconnect_receipt = false
		core_socket.close()
		return
	super._send_speech_receipt(receipt)
func _cache_farewell_voice(payload: Dictionary) -> void:
	super._cache_farewell_voice(payload)
	_record_tts({"event":"cache", "count":farewell_voice_cache.size()})
func _process(delta: float) -> void:
	super._process(delta)
	var control := OS.get_environment("FAREWELL_EVIDENCE").path_join("control.json")
	if not FileAccess.file_exists(control):
		return
	var raw := FileAccess.get_file_as_string(control)
	if raw == control_seen:
		return
	var command: Variant = JSON.parse_string(raw)
	if command is not Dictionary:
		return
	control_seen = raw
	drop_receipts = int(command.get("drop", 0))
	disconnect_receipt = command.get("disconnect", false)
	_record_tts({"event":"control", "id":command.get("id", "")})
	if command.get("exit", false):
		request_exit()
