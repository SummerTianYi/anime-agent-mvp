// Codex: A-only facial definition study, UV-attached and non-geometric.
// Uses the existing face atlas read-only. No displacement or normal edits.
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled;
uniform sampler2D face_atlas : source_color, filter_linear_mipmap, repeat_enable;
uniform float strength : hint_range(0.0, 1.0) = 1.0;

float soft_region(vec2 p, vec2 center, vec2 radius) {
	vec2 d = (p - center) / radius;
	return exp(-dot(d, d) * 2.0);
}

void fragment() {
	vec3 tex = texture(face_atlas, UV).rgb;
	// Delicate under-tip shading, not a black line down the nose bridge.
	float nose = soft_region(UV, vec2(0.500, 0.490), vec2(0.0075, 0.0040));
	float nose_side = soft_region(UV, vec2(0.504, 0.483), vec2(0.0035, 0.010));
	// Follow existing lip pigment so open-mouth shape keys remain compatible.
	float mouth = soft_region(UV, vec2(0.500, 0.564), vec2(0.031, 0.010));
	float pigment = smoothstep(0.10, 0.32, tex.r - tex.g);
	// Ear contrast only inside the existing atlas island, not through hair.
	float ear = soft_region(UV, vec2(0.078, 0.080), vec2(0.060, 0.087));
	float ear_detail = smoothstep(0.065, 0.16, tex.r - tex.g);
	float opacity = nose * 0.19 + nose_side * 0.055 + mouth * pigment * 0.25 + ear * ear_detail * 0.12;
	ALBEDO = vec3(0.40, 0.21, 0.15);
	ALPHA = clamp(opacity * strength, 0.0, 0.24);
}
