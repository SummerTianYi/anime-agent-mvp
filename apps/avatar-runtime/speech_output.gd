extends RefCounted
## Voice-only gain before a look-ahead limiter. Original WAVs stay untouched.

const BUS_NAME := &"TianyiSpeech"
const GAIN_ENV := "ANIME_AGENT_SPEECH_GAIN_DB"
const DEFAULT_GAIN_DB := 3.0
const CEILING_DB := -1.0


static func parse_gain(text: String) -> float:
	var value := text.strip_edges()
	if value.is_empty():
		return DEFAULT_GAIN_DB
	if not value.is_valid_float() or not is_finite(value.to_float()):
		push_warning("Invalid speech gain; using default 3 dB")
		return DEFAULT_GAIN_DB
	return clampf(value.to_float(), -12.0, 6.0)


static func configure(gain_db: float) -> StringName:
	var index := AudioServer.get_bus_index(BUS_NAME)
	if index < 0:
		AudioServer.add_bus()
		index = AudioServer.bus_count - 1
		AudioServer.set_bus_name(index, BUS_NAME)
		AudioServer.set_bus_send(index, &"Master")
		AudioServer.add_bus_effect(index, AudioEffectHardLimiter.new())
	var limiter := AudioServer.get_bus_effect(index, 0) as AudioEffectHardLimiter
	limiter.pre_gain_db = maxf(gain_db, 0.0)
	limiter.ceiling_db = CEILING_DB
	limiter.release = 0.1
	AudioServer.set_bus_volume_db(index, minf(gain_db, 0.0))
	# At zero the original signal passes through, including its original peaks.
	AudioServer.set_bus_effect_enabled(index, 0, gain_db > 0.0)
	return BUS_NAME


static func configure_from_environment() -> StringName:
	var gain_db := parse_gain(OS.get_environment(GAIN_ENV))
	var bus := configure(gain_db)
	print("GODOT_SPEECH_OUTPUT_READY ", JSON.stringify({
		"gainDb": gain_db, "ceilingDb": CEILING_DB,
		"limiterEnabled": gain_db > 0.0, "bus": bus,
	}))
	return bus
