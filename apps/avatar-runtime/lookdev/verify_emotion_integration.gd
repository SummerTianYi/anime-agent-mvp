extends "res://lookdev/render_emotion_preview.gd"

## Codex: GPU verification of production event handlers, not an image edit.
const ACCEPTED := {
	"surprised":{"びっくり":1.0,"上":0.65,"瞳小":0.32,"お":0.85},
	"angry":{"怒り":1.0,"怒り２":0.55,"下":0.15,"じと目":0.52,"口角下げ":0.5,"∧":0.62},
	"tears":{"眼泪":1.0,"困る":1.0,"まばたき":0.12,"下瞼上げ":0.24,"口角下げ":0.75,"∧":0.3,"あ":0.14}
}

func _run() -> void:
	if DisplayServer.get_name() == "headless":
		push_error("GPU rendering required")
		quit(1)
		return
	output = "user://emotion-integration/" + Time.get_datetime_string_from_system().replace(":","-") + "-" + str(OS.get_process_id())
	_check(DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(output)) == OK,"create evidence")
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
	var target: Vector3 = runtime.skeleton.global_transform * runtime.skeleton.get_bone_global_pose(runtime.skeleton.find_bone("頭")).origin + Vector3(0,0.07,0)
	runtime.camera.position = target + Vector3(0,0,0.46)
	runtime.camera.look_at(target,Vector3.UP)
	var invariants := _invariants()
	var mesh_ref: Mesh = runtime.face_mesh.mesh
	var skin_ref: Skin = runtime.face_mesh.skin
	var materials: Array = []
	for index in mesh_ref.get_surface_count():
		materials.append(runtime.face_mesh.get_active_material(index))
	var neutral: Image = await _capture()
	var comparisons: Array = []
	var pictures: Array[Image] = []
	var labels: Array[String] = []
	for emotion in EMOTIONS:
		for yaw in [0.0,30.0]:
			_reset_face()
			runtime.model.rotation = runtime.base_model_rotation + Vector3(0,deg_to_rad(yaw),0)
			_mix(emotion.before)
			var before: Image = await _capture()
			_mix(ACCEPTED[emotion.id])
			var expected: Image = await _capture()
			_reset_face()
			runtime.handle_agent_event("avatar." + emotion.id)
			_advance_face(0.8)
			var actual: Image = await _capture()
			var name: String = emotion.id + ("-front" if yaw == 0 else "-three-quarter")
			_save(actual,name + ".png")
			var parity := _pixel_diff(expected,actual)
			_check(parity.equivalent,"accepted weights versus production handler " + name)
			comparisons.append({"case":name,"pixels":parity})
			if yaw == 0:
				pictures.append(before)
				pictures.append(actual)
				labels.append(emotion.label + "｜原版")
				labels.append(emotion.label + "｜正式代码")
			_advance_face(3.0)
			_check(not runtime.emotion_preset.active(),"timeout " + name)
	var target_sheet := SubViewport.new()
	target_sheet.size = Vector2i(1120,1890)
	target_sheet.disable_3d = true
	target_sheet.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(target_sheet)
	var sheet := EmotionSheet.new()
	sheet.pictures = pictures
	sheet.labels = labels
	sheet.title = "正式表情对比｜左：原版　右：已确认方案"
	sheet.note = "同一1.4模型 · 同机位/光照/材质 · 正式事件驱动 · 哭泣采用折中版"
	sheet.size = target_sheet.size
	target_sheet.add_child(sheet)
	await process_frame
	await RenderingServer.frame_post_draw
	_save(target_sheet.get_texture().get_image(),"installed-comparison.png")
	target_sheet.queue_free()
	runtime.model.rotation = runtime.base_model_rotation
	pictures = []
	labels = []
	_reset_face()
	runtime.handle_agent_event("avatar.tears")
	for seconds in [0.05,0.10,0.25]:
		_advance_face(seconds)
		pictures.append(await _capture())
		labels.append("哭泣进入")
	runtime._trigger_blink()
	_advance_face(0.1)
	pictures.append(await _capture())
	labels.append("眨眼")
	_advance_face(0.5)
	runtime.blink_timer = 1000.0 # Compare neutral outside the next automatic blink.
	pictures.append(await _capture())
	labels.append("眨眼恢复")
	runtime._set_agent_state("speaking")
	_advance_face(0.2)
	pictures.append(await _capture())
	labels.append("哭泣中说话")
	runtime._set_agent_state("idle")
	_advance_face(0.4)
	pictures.append(await _capture())
	labels.append("说话结束")
	_advance_face(3.0)
	var restored: Image = await _capture()
	pictures.append(restored)
	labels.append("自动恢复自然")
	await _draw_sheet(pictures,labels,"cry-transition.png",4,Vector2i(320,360),"正式代码时序检查｜进入、眨眼、说话、恢复","正式事件驱动 · 同一1.4模型 · 动态衔接验证")
	_check(_pixel_diff(neutral,restored).equivalent,"neutral restored")
	_check(_invariants() == invariants,"all bone poses, camera, light unchanged")
	_check(runtime.face_mesh.mesh == mesh_ref and runtime.face_mesh.skin == skin_ref,"mesh/skin unchanged")
	for index in materials.size():
		_check(materials[index] == runtime.face_mesh.get_active_material(index),"material unchanged")
	_check(FileAccess.get_sha256("res://assets/luotianyi_v4.glb") == SHA,"official asset unchanged")
	var report := {"author":"Codex","status":"PASS" if failures.is_empty() else "FAIL","failures":failures,"comparisons":comparisons,"model_look":"1.4","expression_revision":runtime.emotion_preset.REVISION,"model_sha256":SHA,"output":ProjectSettings.globalize_path(output)}
	var file := FileAccess.open(output + "/report.json",FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"\t"))
	file.close()
	print("EMOTION_INTEGRATION_",report.status," ",report.output)
	quit(0 if failures.is_empty() else 1)

func _reset_face() -> void:
	runtime._clear_emotions()
	runtime._set_agent_state("idle")
	runtime.blink_timer = 1000.0
	for name in runtime.expression_ids:
		runtime._set_expression(name,0.0)
		runtime.expression_values[name] = 0.0
	_mix({})

func _advance_face(seconds: float) -> void:
	for frame in range(roundi(seconds*60.0)):
		runtime._process_speaking_mouth(1.0/60.0)
		runtime._process_expressions(1.0/60.0)
