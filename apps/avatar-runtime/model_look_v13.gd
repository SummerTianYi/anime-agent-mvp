extends RefCounted

## Codex: v1.3 material profile, identical to the visually accepted candidate A.
## All source textures are shared read-only; only material instances change.
const PROFILES := {
	"face": [0.36, 0.84, 0.92, 0.02],
	"body": [0.36, 0.84, 0.92, 0.02],
	"hand": [0.36, 0.84, 0.92, 0.02],
	"leg": [0.36, 0.84, 0.92, 0.02],
	"fronthair": [0.62, 0.62, 0.66, 0.08],
	"backhair": [0.62, 0.62, 0.66, 0.08],
	"tail": [0.62, 0.62, 0.66, 0.08],
	"clothes1": [0.52, 0.72, 0.92, 0.04],
	"clothes2": [0.52, 0.72, 0.92, 0.04],
	"skirt": [0.52, 0.72, 0.92, 0.04],
}

static func make_material(source: StandardMaterial3D, surface: String) -> StandardMaterial3D:
	var material := source.duplicate() as StandardMaterial3D
	var values: Array = PROFILES[surface]
	material.resource_name = surface + "_1.3"
	material.albedo_color = Color(values[0], values[0], values[0], 1.0)
	material.emission_energy_multiplier = values[1]
	material.roughness = values[2]
	material.rim = values[3]
	material.diffuse_mode = BaseMaterial3D.DIFFUSE_BURLEY
	material.specular_mode = BaseMaterial3D.SPECULAR_SCHLICK_GGX
	material.metallic_specular = 0.12 if surface in ["fronthair", "backhair", "tail"] else 0.06
	return material
