// Codex: A2 preview, wider soft nose definition and clearer existing lip pigment.
// A1 is retained in face_a.gdshader. No geometry, normal, atlas or rig edits.
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
	// Spread the under-tip cue into a shallow arc; reduce its peak darkness.
	float nx = clamp((UV.x - 0.500) / 0.017, -1.0, 1.0);
	vec2 arc_uv = vec2(UV.x, UV.y + 0.002 * nx * nx);
	float nose = soft_region(arc_uv, vec2(0.500, 0.490), vec2(0.014, 0.005));
	float nose_side = soft_region(UV, vec2(0.508, 0.480), vec2(0.005, 0.017));
	float nose_light = soft_region(UV, vec2(0.498, 0.477), vec2(0.005, 0.014));
	float mouth = soft_region(UV, vec2(0.500, 0.564), vec2(0.035, 0.013));
	float pigment = smoothstep(0.10, 0.32, tex.r - tex.g);
	float lip = mouth * pigment * 0.43;
	// Identical ear contribution to A1; do not move hair to expose it.
	float ear = soft_region(UV, vec2(0.078, 0.080), vec2(0.060, 0.087));
	float ear_detail = smoothstep(0.065, 0.16, tex.r - tex.g);
	float shade = nose * 0.13 + nose_side * 0.06 + lip + ear * ear_detail * 0.12;
	float highlight = nose_light * 0.035;
	vec3 shade_color = mix(vec3(0.40, 0.21, 0.15), vec3(0.49, 0.21, 0.18), clamp(lip / 0.3, 0.0, 1.0));
	ALBEDO = (shade_color * shade + vec3(0.96, 0.88, 0.78) * highlight) / max(shade + highlight, 0.00001);
	ALPHA = clamp((shade + highlight) * strength, 0.0, 0.34);
}
