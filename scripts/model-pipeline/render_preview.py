from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import blender_arguments  # noqa: E402


def look_at(obj: object, target: Vector) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a neutral model inspection preview")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(blender_arguments())
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.open_mainfile(filepath=str(input_path))
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 700
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.008, 0.008, 0.015)
    for obj in list(scene.objects):
        if obj.type in {"CAMERA", "LIGHT"}:
            bpy.data.objects.remove(obj, do_unlink=True)

    points = [obj.matrix_world @ Vector(corner) for obj in scene.objects if obj.type == "MESH" for corner in obj.bound_box]
    if not points:
        raise RuntimeError("No mesh objects found")
    minimum = Vector((min(v.x for v in points), min(v.y for v in points), min(v.z for v in points)))
    maximum = Vector((max(v.x for v in points), max(v.y for v in points), max(v.z for v in points)))
    center = (minimum + maximum) / 2
    height = maximum.z - minimum.z
    target = Vector((center.x, center.y, minimum.z + height * 0.56))

    camera_data = bpy.data.cameras.new("PreviewCamera")
    camera = bpy.data.objects.new("PreviewCamera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = Vector((center.x, minimum.y - height * 1.8, target.z))
    camera_data.lens = 58
    look_at(camera, target)
    scene.camera = camera

    def add_area(name: str, location: tuple[float, float, float], energy: float, size: float, color: tuple[float, float, float]) -> None:
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = color
        light = bpy.data.objects.new(name, data)
        scene.collection.objects.link(light)
        light.location = location
        look_at(light, target)

    add_area("Key", (center.x + height * 0.7, minimum.y - height, maximum.z + height * 0.7), 900, height * 0.7, (0.72, 0.84, 1.0))
    add_area("Fill", (center.x - height * 0.8, minimum.y - height * 0.8, target.z + height * 0.2), 650, height * 0.8, (1.0, 0.78, 0.72))
    add_area("Rim", (center.x, maximum.y + height * 0.6, maximum.z + height * 0.2), 850, height * 0.5, (0.55, 0.7, 1.0))
    scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)
    print("BOUNDS", tuple(round(x, 4) for x in minimum), tuple(round(x, 4) for x in maximum))
    print("RENDERED", output_path, output_path.stat().st_size)


if __name__ == "__main__":
    main()
