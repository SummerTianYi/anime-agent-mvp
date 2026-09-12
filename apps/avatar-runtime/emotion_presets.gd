extends RefCounted

## Codex, expression revision 1.0: owner-approved GPU previews, 2026-09-12.
## Separate from model look 1.4: no geometry, materials, rig or motion changes.
const REVISION := "1.0"
const PRESETS := {
	"surprised":{"label":"惊讶","intensity":0.90,"duration":1.6,
		"weights":{"びっくり":1.0,"上":0.65,"瞳小":0.32,"お":0.85}},
	"angry":{"label":"生气","intensity":0.82,"duration":1.8,
		"weights":{"怒り":1.0,"怒り２":0.55,"下":0.15,"じと目":0.52,"口角下げ":0.50,"∧":0.62}},
	"tears":{"label":"流泪","intensity":0.92,"duration":2.4,
		"weights":{"眼泪":1.0,"困る":1.0,"まばたき":0.12,"下瞼上げ":0.24,"口角下げ":0.75,"∧":0.30,"あ":0.14}}
}
const LEGACY_EMOTIONS := ["笑い","にやり","じと目","びっくり","困る","怒り","怒り２","眼泪","汗","愛心眼","星星眼","圈圈眼"]
const MOUTH_SHAPES := ["あ","あ２","あ３","い","い２","う","う２","え","え２","お","お２","∧","ん","□","ω","ω2","うへぇ","にやり","てへぺろ","にやりω","口角下げ","ぺろっ"]
const EYE_SHAPES := ["じと目","びっくり","下瞼上げ"]
var weights: Dictionary = {}
var remaining := 0.0
var label := ""

func play(name: String, intensity: float) -> void:
	clear()
	if not PRESETS.has(name) or not is_finite(intensity) or intensity <= 0.0:
		return
	var preset: Dictionary = PRESETS[name]
	# Preserve the public intensity range and match the accepted default exactly.
	var strength := clampf(clampf(intensity,0.0,1.0) / float(preset.intensity),0.0,1.0)
	for key in preset.weights:
		weights[key] = float(preset.weights[key]) * strength
	remaining = float(preset.duration)
	label = preset.label

func clear() -> void:
	weights.clear()
	remaining = 0.0
	label = ""

func active() -> bool:
	return remaining > 0.0 and not weights.is_empty()

func advance(delta: float) -> void:
	if active():
		remaining = maxf(0.0,remaining-delta)
		if remaining == 0.0:
			clear()

func resolve(name: String, base: float, speaking: bool, blink: float) -> float:
	if not active():
		return base
	if name in MOUTH_SHAPES:
		# The mouth is articulated by speech, never stacked with a fixed jaw pose.
		return base if speaking else float(weights.get(name,0.0))
	if name == "まばたき":
		return maxf(base,float(weights.get(name,0.0)))
	if name in EYE_SHAPES:
		return float(weights.get(name,0.0)) * (1.0-clampf(blink,0.0,1.0))
	if weights.has(name):
		return float(weights[name])
	# A working/thinking/speaking state must not silently turn crying into a smile.
	if name in LEGACY_EMOTIONS:
		return 0.0
	return base
