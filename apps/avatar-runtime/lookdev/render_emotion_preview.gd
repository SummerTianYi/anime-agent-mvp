extends "res://lookdev/render_candidate.gd"

## Codex, 2026-09-12: offline expression study. No production entry point,
## network, asset writes, window persistence, or model-version changes.
const EMOTIONS := [
	{"id":"surprised", "label":"惊讶", "before":{"びっくり":0.9},
		"after":{"びっくり":1.0, "上":0.65, "瞳小":0.32, "お":0.85}},
	{"id":"angry", "label":"生气", "before":{"怒り":0.82},
		"after":{"怒り":1.0, "怒り２":0.55, "下":0.15, "じと目":0.52, "口角下げ":0.50, "∧":0.62}},
	{"id":"tears", "label":"流泪", "before":{"眼泪":0.92},
		"after":{"眼泪":1.0, "困る":1.0, "まばたき":0.24, "下瞼上げ":0.18, "口角下げ":0.65, "∧":0.60, "あ":0.12}}
]

# Preserve both reviewed candidates; this optional study never overwrites them.
const CRY_EARLY := {"眼泪":1.0, "困る":1.0, "下瞼上げ":0.30, "口角下げ":0.85, "あ":0.16}
const CRY_MIDDLE := {"眼泪":1.0, "困る":1.0, "まばたき":0.12, "下瞼上げ":0.24, "口角下げ":0.75, "∧":0.30, "あ":0.14}
const PREVIOUS_REVIEW := "user://emotion-preview/2026-09-12T00-04-29-9888"

class EmotionSheet extends Control:
	var pictures: Array[Image] = []
	var labels: Array[String] = []
	var textures: Array[ImageTexture] = []
	var columns := 2
	var cell := Vector2i(560, 600)
	var title := "表情强化预览｜左：当前版本　右：候选"
	var note := "同一1.4模型 · 同机位/光照/材质 · 仅表情权重变化 · 未实装"
	var font: SystemFont
	func _ready() -> void:
		font = SystemFont.new()
		font.font_names = PackedStringArray(["Microsoft YaHei", "Noto Sans CJK SC"])
		for picture in pictures:
			textures.append(ImageTexture.create_from_image(picture))
	func _draw() -> void:
		draw_rect(Rect2(Vector2.ZERO, size), Color(0.065, 0.075, 0.09))
		draw_string(font, Vector2(24, 38), title, HORIZONTAL_ALIGNMENT_LEFT, -1, 26, Color(0.9,0.94,1))
		draw_string(font, Vector2(24, 69), note, HORIZONTAL_ALIGNMENT_LEFT, -1, 17, Color(0.6,0.7,0.8))
		for i in pictures.size():
			var p := Vector2((i % columns) * cell.x, floori(float(i) / columns) * cell.y + 90)
			draw_rect(Rect2(p + Vector2(8,8), Vector2(cell) - Vector2(16,16)), Color(0.045,0.05,0.06))
			draw_string(font, p + Vector2(22, 36), labels[i], HORIZONTAL_ALIGNMENT_LEFT, cell.x - 36, 22, Color(0.78,0.9,1))
			var available := Vector2(cell.x-16,cell.y-64)
			var ratio := minf(available.x/pictures[i].get_width(), available.y/pictures[i].get_height())
			var picture_size := Vector2(pictures[i].get_size()) * ratio
			draw_texture_rect(textures[i], Rect2(p + Vector2(8,48) + (available-picture_size)*0.5, picture_size), false)

func _run() -> void:
	if DisplayServer.get_name() == "headless":
		push_error("Actual GPU rendering is required for these previews")
		quit(1)
		return
	output = "user://emotion-preview/" + Time.get_datetime_string_from_system().replace(":", "-") + "-" + str(OS.get_process_id())
	_check(DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(output)) == OK, "create unique evidence directory")
	root.always_on_top = false
	root.size = Vector2i(16,16)
	root.position = Vector2i(-100,-100)
	viewport = SubViewport.new()
	viewport.size = Vector2i(640,640)
	viewport.own_world_3d = true
	viewport.transparent_bg = true
	viewport.msaa_3d = Viewport.MSAA_4X
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(viewport)
	runtime = load("res://main.tscn").instantiate()
	runtime.set_script(OfflineRuntime)
	viewport.add_child(runtime)
	runtime.set_model_look_version("1.4")
	_pose(0,2.0)
	_check(FileAccess.get_sha256("res://assets/luotianyi_v4.glb") == SHA, "official GLB hash before")
	_check(runtime.skeleton.get_bone_count() == 703, "703 bones")
	_check(runtime.face_mesh.mesh.get_blend_shape_count() == 48, "48 existing shapes")
	var material_refs: Array = []
	for index in runtime.face_mesh.mesh.get_surface_count():
		material_refs.append(runtime.face_mesh.get_active_material(index))
	var mesh_ref: Mesh = runtime.face_mesh.mesh
	var skin_ref: Skin = runtime.face_mesh.skin
	var target: Vector3 = runtime.skeleton.global_transform * runtime.skeleton.get_bone_global_pose(runtime.skeleton.find_bone("頭")).origin + Vector3(0,0.07,0)
	runtime.camera.position = target + Vector3(0,0,0.46)
	runtime.camera.look_at(target,Vector3.UP)
	var baseline := _invariants()
	var neutral: Image = await _capture()
	_save(neutral, "neutral.png")
	print("EMOTION_SHAPES ", runtime.expression_ids)
	if "--atlas" in OS.get_cmdline_user_args():
		var pictures: Array[Image] = [neutral]
		var labels: Array[String] = ["自然"]
		for name in ["びっくり","瞳小","下瞼上げ","お","あ","あ３","∧","□","口角下げ","困る","怒り","怒り２","上","下","じと目","眼泪"]:
			_mix({name:1.0})
			pictures.append(await _capture())
			labels.append(name)
		await _draw_sheet(pictures,labels,"shape-atlas.png",4,Vector2i(280,324),"现有形变逐项检查｜强度1.0")
	elif "--cry-middle" in OS.get_cmdline_user_args():
		await _cry_middle_review(neutral, baseline, material_refs, mesh_ref, skin_ref)
	else:
		var pictures: Array[Image] = []
		var labels: Array[String] = []
		var reports: Array = []
		for emotion in EMOTIONS:
			_mix(emotion.before)
			var before: Image = await _capture()
			_mix(emotion.after)
			var after: Image = await _capture()
			_check(_invariants() == baseline,"unchanged camera/light/all bone poses " + emotion.id)
			var difference := _compare(before,after)
			_check(difference.rgb_mean_difference > 0.0001,"visible change " + emotion.id)
			_save(before,emotion.id + "-before.png")
			_save(after,emotion.id + "-candidate.png")
			pictures.append(before)
			pictures.append(after)
			labels.append(emotion.label + "｜当前")
			labels.append(emotion.label + "｜强化候选")
			_mix({})
			var restored: Image = await _capture()
			_check(_compare(neutral,restored).rgb_mean_difference < 0.000001,"exact neutral restoration " + emotion.id)
			reports.append({"id":emotion.id,"before":emotion.before,"after":emotion.after,"difference":difference})
		await _draw_sheet(pictures,labels,"comparison-face.png")
		# Same expressions at the normal 560x760 desktop viewport, plus 3/4 angle.
		for view in ["daily","three-quarter"]:
			pictures.clear()
			labels.clear()
			if view == "daily":
				viewport.size = Vector2i(560,760)
				runtime.camera.position = Vector3(0,runtime.CAMERA_FOCUS.y,3.8)
				runtime.camera.look_at(runtime.CAMERA_FOCUS,Vector3.UP)
			else:
				viewport.size = Vector2i(640,640)
				runtime.camera.position = target + Vector3(0,0,0.46)
				runtime.camera.look_at(target,Vector3.UP)
				runtime.model.rotation = runtime.base_model_rotation + Vector3(0,deg_to_rad(30),0)
			for emotion in EMOTIONS:
				for stage in ["before","after"]:
					_mix(emotion[stage])
					var picture: Image = await _capture()
					_save(picture,view + "-" + emotion.id + "-" + stage + ".png")
					pictures.append(picture)
					labels.append(emotion.label + ("｜当前" if stage == "before" else "｜强化候选"))
			await _draw_sheet(pictures,labels,"comparison-" + view + ".png",2,Vector2i(576,824) if view == "daily" else Vector2i(560,600))
		for index in material_refs.size():
			_check(material_refs[index] == runtime.face_mesh.get_active_material(index),"same material " + str(index))
		_check(mesh_ref == runtime.face_mesh.mesh and skin_ref == runtime.face_mesh.skin,"same mesh/skin")
		_check(FileAccess.get_sha256("res://assets/luotianyi_v4.glb") == SHA,"official hash after")
		var report := {"author":"Codex","status":"PASS" if failures.is_empty() else "FAIL","failures":failures,"scope":"OFFLINE STATIC PREVIEW ONLY: existing shape weights, production untouched; temporal/state integration not implemented","cases":reports,"model_sha256":SHA,"output":ProjectSettings.globalize_path(output)}
		var file := FileAccess.open(output + "/report.json",FileAccess.WRITE)
		file.store_string(JSON.stringify(report,"\t"))
		file.close()
	print("EMOTION_PREVIEW_", "PASS" if failures.is_empty() else "FAIL", " ", ProjectSettings.globalize_path(output))
	quit(0 if failures.is_empty() else 1)

func _mix(weights: Dictionary) -> void:
	for index in runtime.face_mesh.mesh.get_blend_shape_count():
		runtime.face_mesh.set_blend_shape_value(index,0.0)
	for name in weights:
		_check(runtime.expression_ids.has(name),"shape available " + name)
		_check(float(weights[name]) >= 0.0 and float(weights[name]) <= 1.0,"bounded weight " + name)
		if runtime.expression_ids.has(name):
			runtime.face_mesh.set_blend_shape_value(runtime.expression_ids[name],weights[name])

func _cry_middle_review(neutral: Image, baseline: Array, material_refs: Array, mesh_ref: Mesh, skin_ref: Skin) -> void:
	var previous: Variant = JSON.parse_string(FileAccess.get_file_as_string(PREVIOUS_REVIEW + "/report.json"))
	_check(previous is Dictionary and previous.get("status") == "PASS", "previous reviewed evidence exists")
	if not failures.is_empty():
		return
	# Preserve weights exactly; allow only measured 8-bit GPU rounding noise.
	var parity: Array = []
	for index in [0,1]:
		var emotion: Dictionary = EMOTIONS[index]
		_check(emotion.after == previous.cases[index].after, "approved weights unchanged " + emotion.id)
		_mix(emotion.after)
		var current: Image = await _capture()
		_save(current,"unchanged-" + emotion.id + ".png")
		var old := Image.load_from_file(PREVIOUS_REVIEW + "/" + emotion.id + "-candidate.png")
		_check(old != null, "previous PNG exists " + emotion.id)
		if old != null:
			var metrics := _pixel_diff(current,old)
			_check(metrics.equivalent, "approved image parity within 8-bit rounding " + emotion.id)
			parity.append({"expression":emotion.id,"pixels":metrics})
			var altered: Image = current.duplicate()
			altered.set_pixel(320,320,Color.MAGENTA)
			_check(not _pixel_diff(altered,old).equivalent,"pixel comparison rejects negative control " + emotion.id)
	# This is exactly halfway in weight space, not a claim of perceptual linearity.
	for name in CRY_MIDDLE:
		var expected := (float(CRY_EARLY.get(name,0.0)) + float(EMOTIONS[2].after.get(name,0.0))) * 0.5
		_check(is_equal_approx(CRY_MIDDLE[name],expected), "halfway weight " + name)
	var pictures: Array[Image] = []
	var labels: Array[String] = []
	var views: Array = []
	for yaw in [0.0,30.0]:
		runtime.model.rotation = runtime.base_model_rotation + Vector3(0,deg_to_rad(yaw),0)
		var view := "front" if yaw == 0 else "three-quarter"
		var view_invariant := _invariants()
		var rendered: Array[Image] = []
		for revision in ["early","middle","last"]:
			var weights: Dictionary = CRY_EARLY if revision == "early" else (CRY_MIDDLE if revision == "middle" else EMOTIONS[2].after)
			_mix(weights)
			var picture: Image = await _capture()
			_save(picture, "cry-" + view + "-" + revision + ".png")
			rendered.append(picture)
			pictures.append(picture)
			var label := "图中版本" if revision == "early" else ("本次折中" if revision == "middle" else "上一轮最终")
			labels.append(("正面｜" if yaw == 0 else "侧面｜") + label)
			_check(_invariants() == view_invariant, "same camera/light/body " + view + revision)
		var from_early := _compare(rendered[0],rendered[1])
		var from_last := _compare(rendered[2],rendered[1])
		_check(from_early.rgb_mean_difference > 0.0001 and from_last.rgb_mean_difference > 0.0001,"distinct from both endpoints " + view)
		views.append({"view":view,"difference_from_early":from_early,"difference_from_last":from_last})
	await _draw_sheet(pictures,labels,"cry-three-way.png",3,Vector2i(480,520),"哭泣表情微调｜左：图中版本　中：本次折中　右：上一轮最终")
	# Restore every expression to the same neutral baseline before finishing.
	runtime.model.rotation = runtime.base_model_rotation
	_mix({})
	var restored: Image = await _capture()
	_save(restored,"neutral-restored.png")
	var rollback := _pixel_diff(neutral,restored)
	_check(rollback.equivalent,"neutral restoration within 8-bit rounding")
	_check(_invariants() == baseline,"all original poses/camera restored")
	for index in material_refs.size():
		_check(material_refs[index] == runtime.face_mesh.get_active_material(index), "same material " + str(index))
	_check(mesh_ref == runtime.face_mesh.mesh and skin_ref == runtime.face_mesh.skin,"same mesh/skin")
	_check(FileAccess.get_sha256("res://assets/luotianyi_v4.glb") == SHA,"official GLB unchanged")
	var report := {"author":"Codex","status":"PASS" if failures.is_empty() else "FAIL","failures":failures,
		"scope":"cry-only offline candidate; surprised/angry weights identical, full RGBA parity within one 8-bit step and mean<1e-6 with identical alpha; no production adoption",
		"early":CRY_EARLY,"middle":CRY_MIDDLE,"last":EMOTIONS[2].after,"views":views,
		"unchanged_expressions":parity,"neutral_rollback":rollback,
		"model_sha256":SHA,"output":ProjectSettings.globalize_path(output)}
	var file := FileAccess.open(output + "/cry-report.json",FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"\t"))
	file.close()

func _pixel_diff(a: Image, b: Image) -> Dictionary:
	if a.get_size() != b.get_size() or a.get_format() != Image.FORMAT_RGBA8 or b.get_format() != Image.FORMAT_RGBA8:
		return {"equivalent":false,"error":"expected equally-sized RGBA8 images"}
	var left := a.get_data()
	var right := b.get_data()
	var maximum := 0
	var alpha_maximum := 0
	var total := 0
	var changed := 0
	for index in left.size():
		var delta := absi(int(left[index])-int(right[index]))
		maximum = maxi(maximum,delta)
		if index % 4 == 3:
			alpha_maximum = maxi(alpha_maximum,delta)
		total += delta
		if delta > 0:
			changed += 1
	var mean_error := float(total) / (left.size()*255.0)
	return {"equivalent":maximum <= 1 and alpha_maximum == 0 and mean_error < 0.000001,
		"max_8bit_error":maximum,"alpha_max":alpha_maximum,"mean_normalized_error":mean_error,"changed_channels":changed}

func _draw_sheet(pictures: Array[Image], labels: Array[String], filename: String, columns: int = 2, cell: Vector2i = Vector2i(560,600), title: String = "表情强化预览｜左：当前版本　右：候选", note: String = "同一1.4模型 · 同机位/光照/材质 · 仅表情权重变化 · 未实装") -> void:
	var target := SubViewport.new()
	target.size = Vector2i(columns * cell.x, ceili(float(pictures.size())/columns)*cell.y+90)
	target.disable_3d = true
	target.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(target)
	var sheet := EmotionSheet.new()
	sheet.pictures = pictures.duplicate()
	sheet.labels = labels.duplicate()
	sheet.columns = columns
	sheet.cell = cell
	sheet.title = title
	sheet.note = note
	sheet.size = target.size
	target.add_child(sheet)
	await process_frame
	await RenderingServer.frame_post_draw
	_save(target.get_texture().get_image(),filename)
	target.queue_free()
