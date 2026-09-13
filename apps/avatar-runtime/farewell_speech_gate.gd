extends RefCounted
## Codex: join the immutable animation and this exit's complete audio stream.
var request_id := ""
var animation_done := false
var speech_done := true
var utterance_id := ""
var next_part := 0
var part_count := 0

func expect_speech(id: String) -> void:
	request_id = id
	speech_done = false

func accept_part(payload: Dictionary) -> bool:
	if speech_done or request_id.is_empty() or str(payload.get("requestId", "")) != request_id:
		return false
	var id := str(payload.get("utteranceId", ""))
	var raw_index: Variant = payload.get("partIndex", 0)
	var raw_count: Variant = payload.get("partCount", 1)
	if typeof(raw_index) not in [TYPE_INT, TYPE_FLOAT] or typeof(raw_count) not in [TYPE_INT, TYPE_FLOAT]:
		return false
	var index := int(raw_index)
	var count := int(raw_count)
	if float(index) != float(raw_index) or float(count) != float(raw_count):
		return false
	if id.is_empty() or not utterance_id.is_empty() or index != next_part or count <= index or count > 64:
		return false
	if part_count != 0 and count != part_count:
		return false
	part_count = count
	utterance_id = id
	return true

func finish_part(id: String, interrupted: bool = false) -> void:
	if id.is_empty() or id != utterance_id:
		return
	utterance_id = ""
	next_part += 1
	speech_done = interrupted or next_part == part_count

func unavailable(id: String) -> void:
	# A late failure cannot truncate a part already playing.
	if id == request_id and utterance_id.is_empty():
		speech_done = true

func ready() -> bool:
	return animation_done and speech_done
