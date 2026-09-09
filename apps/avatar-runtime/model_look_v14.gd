extends RefCounted

## Codex: accepted A2 face detail; inherit every other v1.3 material unchanged.
const FACE_DETAIL := preload("res://face_detail_v14.gdshader")

static func make_material(source: StandardMaterial3D, surface: String) -> StandardMaterial3D:
	if surface != "face":
		return source
	var material := source.duplicate() as StandardMaterial3D
	material.resource_name = "face_1.4"
	var detail := ShaderMaterial.new()
	detail.shader = FACE_DETAIL
	detail.set_shader_parameter("face_atlas", source.albedo_texture)
	material.next_pass = detail
	return material
