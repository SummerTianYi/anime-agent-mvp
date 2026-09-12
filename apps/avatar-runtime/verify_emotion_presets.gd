extends "res://lookdev/render_candidate.gd"

## Codex: behavioral acceptance tests independent of production preset data.
const EXPECTED := {
	"surprised":{"びっくり":1.0,"上":0.65,"瞳小":0.32,"お":0.85},
	"angry":{"怒り":1.0,"怒り２":0.55,"下":0.15,"じと目":0.52,"口角下げ":0.5,"∧":0.62},
	"tears":{"眼泪":1.0,"困る":1.0,"まばたき":0.12,"下瞼上げ":0.24,"口角下げ":0.75,"∧":0.3,"あ":0.14}
}
var assertions := 0
var sampled_frames := 0

func _run() -> void:
	runtime = load("res://main.tscn").instantiate()
	runtime.set_script(OfflineRuntime)
	root.add_child(runtime)
	for event in EXPECTED:
		_reset()
		runtime.handle_agent_event("avatar." + event)
		_step(0.6)
		_expect_mix(EXPECTED[event], "approved " + event)
		_step(3.0)
		_expect_mix({}, "timeout neutral " + event)
	# Switching presets must release keys that belong only to the earlier face.
	for previous in EXPECTED:
		for next in EXPECTED:
			_reset()
			runtime.handle_agent_event("avatar." + previous)
			_step(0.4)
			runtime.handle_agent_event("avatar." + next)
			_step(0.6)
			_expect_mix(EXPECTED[next], "switch " + previous + " to " + next)
	# Preserve explicit emotion through agent state transitions; mouth belongs
	# to speech while speaking, and to the expression again after speech ends.
	for event in EXPECTED:
		_reset()
		runtime.handle_agent_event("avatar." + event)
		runtime._set_agent_state("thinking")
		_step(0.45)
		_expect_mix(EXPECTED[event], "thinking keeps " + event)
		runtime._set_agent_state("speaking")
		_step(0.35)
		_assert(_value("∧") < 0.002 and _value("口角下げ") < 0.002,"no speech jaw conflict " + event)
		var open_mouth := 0.0
		for name in runtime.SPEAKING_MOUTHS:
			open_mouth += _value(name)
		_assert(open_mouth > 0.1,"speech mouth moves " + event)
		_assert(_value("笑い") < 0.002,"no automatic happy face over " + event)
		runtime._set_agent_state("idle")
		_step(0.45)
		_expect_mix(EXPECTED[event],"speech return " + event)
	# States already active before a preset must also return after its timeout.
	for state in ["thinking","working","error","speaking"]:
		_reset()
		runtime._set_agent_state(state)
		_step(0.5)
		var speech_clock: float = runtime.speaking_mouth_elapsed
		runtime.handle_agent_event("avatar.tears")
		_assert(runtime.speaking_mouth_elapsed == speech_clock,"emotion preserves speech clock")
		_step(3.0)
		var state_shape: String = {"thinking":"じと目","working":"じと目","error":"困る","speaking":"笑い"}[state]
		var state_weight: float = {"thinking":0.28,"working":0.18,"error":0.72,"speaking":0.18}[state]
		_assert(absf(_value(state_shape)-state_weight) < 0.003,"underlying state restored " + state)
	# Automatic/manual blinking temporarily overrides eye closure but leaves
	# the cry squint intact afterwards, without losing the expression label.
	_reset()
	runtime.handle_agent_event("avatar.tears")
	_step(0.5)
	runtime.blink_timer = 0.0
	_step(0.1)
	_assert(_value("まばたき") > 0.75,"blink closes eyes")
	_assert(runtime.expression_name != "眨眼","blink preserves emotion label")
	_step(0.6)
	_expect_mix(EXPECTED.tears,"cry restored after blink")
	_reset()
	runtime.handle_agent_event("avatar.angry")
	_step(0.5)
	runtime.handle_agent_event("avatar.smile")
	_step(0.5)
	_expect_mix({"笑い":0.85},"legacy smile clears new emotion")
	runtime.handle_agent_event("avatar.tears")
	_step(0.3)
	runtime.handle_agent_event("avatar.reset")
	_step(0.6)
	_expect_mix({},"reset clears all preset keys")
	# Explicit raw morph and diagnostic mouth commands retain their old meaning.
	runtime.handle_agent_event("avatar.angry")
	runtime.handle_agent_event("avatar.expression",{"name":"あ","value":0.5,"duration":1.0})
	_step(0.5)
	_expect_mix({"あ":0.5},"raw expression override")
	runtime.handle_agent_event("avatar.tears")
	runtime.handle_agent_event("avatar.mouth_o")
	_step(0.5)
	_expect_mix({"お":0.9},"manual mouth override")
	for event in EXPECTED:
		for intensity in [-1.0,0.0,0.41,1.0,99.0,NAN,INF]:
			_reset()
			runtime.handle_agent_event("avatar." + event,{"intensity":intensity})
			_step(0.5)
			if intensity <= 0 or not is_finite(intensity):
				_expect_mix({},"invalid/zero intensity " + event)
	# Real frame deltas including a stall must release the pose, not strand it.
	for delta in [1.0/144.0,1.0/60.0,1.0/30.0,0.2,4.0]:
		_reset()
		runtime.handle_agent_event("avatar.tears")
		for frame in range(ceili(4.5/delta)):
			runtime._process_expressions(delta)
			_check_finite()
		_expect_mix({},"expired after variable delta " + str(delta))
	print("GODOT_EMOTION_PRESETS_", "PASS" if failures.is_empty() else "FAIL", {"assertions":assertions,"frames":sampled_frames,"failures":failures})
	quit(0 if failures.is_empty() else 1)

func _reset() -> void:
	runtime.handle_agent_event("avatar.reset")
	runtime._set_agent_state("idle")
	runtime.blink_timer = 1000.0
	for name in runtime.expression_ids:
		runtime._set_expression(name,0.0)
		runtime.expression_values[name] = 0.0
		runtime.face_mesh.set_blend_shape_value(runtime.expression_ids[name],0.0)

func _step(seconds: float) -> void:
	for frame in range(roundi(seconds*60)):
		runtime._process_speaking_mouth(1.0/60.0)
		runtime._process_expressions(1.0/60.0)
		_check_finite()

func _value(name: String) -> float:
	return runtime.face_mesh.get_blend_shape_value(runtime.expression_ids[name])

func _expect_mix(expected: Dictionary,label: String) -> void:
	for name in runtime.expression_ids:
		_assert(absf(_value(name) - float(expected.get(name,0.0))) < 0.003,label + ": " + name)

func _check_finite() -> void:
	sampled_frames += 1
	for name in runtime.expression_ids:
		var value := _value(name)
		_assert(is_finite(value) and value >= 0.0 and value <= 1.0,"finite/bounded " + name)

func _assert(condition: bool,label: String) -> void:
	assertions += 1
	if not condition and label not in failures:
		_check(false,label)
