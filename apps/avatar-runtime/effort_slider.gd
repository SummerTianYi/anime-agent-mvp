extends Control

## Codex/ChatGPT 式思考强度滑杆：一条很粗的圆角轨道，已选段为天依蓝
## #66CCFF，三个档位旋钮是天依表情（当前档大而亮带白圈，其余小而淡）。
## 点按/拖动轨道任意位置换档。

signal value_changed(index: int)

const TRACK_HEIGHT := 14.0
const KNOB_SIZE := 44.0
const IDLE_SIZE := 30.0
const FILL_COLOR := Color("66ccff")
const TRACK_COLOR := Color(0.16, 0.19, 0.25, 1.0)

var stickers: Array = []
var value = 2:
	set(next):
		var clamped := clampi(int(next), 0, maxi(stickers.size() - 1, 0))
		if clamped == value:
			return
		value = clamped
		queue_redraw()
		value_changed.emit(value)
var _dragging := false


func _ready() -> void:
	custom_minimum_size = Vector2(280.0, 56.0)
	size_flags_horizontal = Control.SIZE_EXPAND_FILL
	mouse_filter = Control.MOUSE_FILTER_STOP


func _stop_x(index: int) -> float:
	var count := maxi(stickers.size(), 1)
	var margin := KNOB_SIZE / 2.0
	return margin + (size.x - KNOB_SIZE) * (float(index) / float(count - 1))


func _draw() -> void:
	var track_rect := Rect2(0.0, (size.y - TRACK_HEIGHT) / 2.0, size.x, TRACK_HEIGHT)
	var track := StyleBoxFlat.new()
	track.bg_color = TRACK_COLOR
	track.set_corner_radius_all(TRACK_HEIGHT / 2.0)
	draw_style_box(track, track_rect)
	var fill := StyleBoxFlat.new()
	fill.bg_color = FILL_COLOR
	fill.set_corner_radius_all(TRACK_HEIGHT / 2.0)
	draw_style_box(fill, Rect2(track_rect.position, Vector2(_stop_x(value), TRACK_HEIGHT)))
	for i in stickers.size():
		var tex: Texture2D = stickers[i]
		if tex == null:
			continue
		var active: bool = i == value
		var side := KNOB_SIZE if active else IDLE_SIZE
		var center := Vector2(_stop_x(i), size.y / 2.0)
		if active:
			draw_circle(center, KNOB_SIZE / 2.0 + 2.0, Color(1.0, 1.0, 1.0, 0.92))
		draw_texture_rect(
			tex,
			Rect2(center - Vector2(side, side) / 2.0, Vector2(side, side)),
			false,
			Color(1.0, 1.0, 1.0, 1.0 if active else 0.55)
		)


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		_dragging = event.pressed
		if event.pressed:
			_seek_to(event.position.x)
	elif event is InputEventMouseMotion and _dragging:
		_seek_to(event.position.x)


func _seek_to(x: float) -> void:
	var count := maxi(stickers.size(), 1)
	var margin := KNOB_SIZE / 2.0
	var ratio := (x - margin) / maxf(size.x - KNOB_SIZE, 1.0)
	var index := clampi(int(round(ratio * (count - 1))), 0, count - 1)
	if index != value:
		value = index
