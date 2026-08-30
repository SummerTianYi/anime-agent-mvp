from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import blender_arguments  # noqa: E402


DEFAULT_BONE_MAP = {
    "hip": "センター",
    "abdomen": "上半身",
    "chest": "上半身2",
    "neck": "首",
    "head": "頭",
    "rCollar": "肩.R",
    "rShldr": "腕.R",
    "rForeArm": "ひじ.R",
    "rHand": "手首.R",
    "lCollar": "肩.L",
    "lShldr": "腕.L",
    "lForeArm": "ひじ.L",
    "lHand": "手首.L",
    "rThigh": "足.R",
    "rShin": "ひざ.R",
    "rFoot": "足首.R",
    "lThigh": "足.L",
    "lShin": "ひざ.L",
    "lFoot": "足首.L",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Retarget a humanoid BVH clip onto the prepared Luo Tianyi armature"
    )
    parser.add_argument("--target", required=True, help="Prepared Luo Tianyi .blend")
    parser.add_argument("--motion", required=True, help="Source .bvh motion")
    parser.add_argument("--output-blend", required=True)
    parser.add_argument("--output-glb", required=True)
    parser.add_argument("--action-name", default="cmu_pirouette")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument(
        "--keep-horizontal-root-motion",
        action="store_true",
        help="Keep root X/Y displacement; desktop clips are in-place by default",
    )
    parser.add_argument(
        "--allow-airborne",
        action="store_true",
        help="Preserve airborne motion; desktop clips keep the lowest foot grounded by default",
    )
    return parser.parse_args(blender_arguments())


def one_armature(objects: list[bpy.types.Object], label: str) -> bpy.types.Object:
    armatures = [obj for obj in objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"Expected one {label} armature, found {len(armatures)}")
    return armatures[0]


def validate_mapping(
    source: bpy.types.Object,
    target: bpy.types.Object,
    mapping: dict[str, str],
) -> None:
    missing_source = [name for name in mapping if name not in source.data.bones]
    missing_target = [name for name in mapping.values() if name not in target.data.bones]
    if missing_source or missing_target:
        raise RuntimeError(
            f"Invalid bone map: missing source={missing_source}, missing target={missing_target}"
        )


def hierarchy_depth(pose_bone: bpy.types.PoseBone) -> int:
    depth = 0
    parent = pose_bone.parent
    while parent is not None:
        depth += 1
        parent = parent.parent
    return depth


def reset_pose(armature: bpy.types.Object) -> None:
    for pose_bone in armature.pose.bones:
        pose_bone.matrix_basis.identity()


def desired_head_position(pose_bone: bpy.types.PoseBone) -> Vector:
    if pose_bone.parent is None:
        return pose_bone.bone.matrix_local.translation.copy()
    rest_from_parent = pose_bone.parent.bone.matrix_local.inverted() @ pose_bone.bone.matrix_local
    return pose_bone.parent.matrix @ rest_from_parent.translation


def source_height(armature: bpy.types.Object) -> float:
    points = [point for bone in armature.data.bones for point in (bone.head_local, bone.tail_local)]
    return max(point.z for point in points) - min(point.z for point in points)


def target_height(target: bpy.types.Object) -> float:
    mesh = next(
        (
            obj
            for obj in bpy.context.scene.objects
            if obj.type == "MESH"
            and any(
                modifier.type == "ARMATURE" and modifier.object == target
                for modifier in obj.modifiers
            )
        ),
        None,
    )
    if mesh is None:
        raise RuntimeError("Could not find the skinned target mesh")
    corners = [mesh.matrix_world @ Vector(corner) for corner in mesh.bound_box]
    return max(point.z for point in corners) - min(point.z for point in corners)


def lowest_foot_height(target: bpy.types.Object) -> float:
    return min(target.pose.bones[name].tail.z for name in ("足首.L", "足首.R"))


def create_retargeted_action(
    source: bpy.types.Object,
    target: bpy.types.Object,
    mapping: dict[str, str],
    action_name: str,
    output_fps: int,
    keep_horizontal_root_motion: bool,
    allow_airborne: bool,
) -> tuple[bpy.types.Action, dict[str, object]]:
    source_action = source.animation_data.action if source.animation_data else None
    if source_action is None:
        raise RuntimeError("Imported BVH has no active action")

    source_fps = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base
    source_start = int(round(source_action.frame_range[0]))
    source_end = int(round(source_action.frame_range[1]))
    duration_seconds = (source_end - source_start) / source_fps
    output_frames = max(2, int(round(duration_seconds * output_fps)) + 1)
    motion_scale = target_height(target) / source_height(source)

    if target.animation_data is None:
        target.animation_data_create()
    if target.animation_data.action is not None:
        target.animation_data.action = None
    old_action = bpy.data.actions.get(action_name)
    if old_action is not None:
        bpy.data.actions.remove(old_action)
    action = bpy.data.actions.new(action_name)
    target.animation_data.action = action

    for pose_bone in target.pose.bones:
        for constraint in pose_bone.constraints:
            constraint.mute = True

    ordered_mapping = sorted(
        mapping.items(), key=lambda item: hierarchy_depth(target.pose.bones[item[1]])
    )
    bpy.context.scene.frame_set(source_start)
    bpy.context.view_layer.update()
    reset_pose(target)
    bpy.context.view_layer.update()
    ground_height = lowest_foot_height(target)
    root_source = source.pose.bones["hip"]
    baseline_root_location = root_source.location.copy()
    maximum_ground_correction = 0.0

    for output_index in range(output_frames):
        output_frame = output_index + 1
        source_time = output_index / output_fps
        source_frame = min(source_end, source_start + source_time * source_fps)
        bpy.context.scene.frame_set(int(round(source_frame)))
        bpy.context.view_layer.update()
        reset_pose(target)
        bpy.context.view_layer.update()

        for source_name, target_name in ordered_mapping:
            source_bone = source.data.bones[source_name]
            source_pose = source.pose.bones[source_name]
            target_bone = target.data.bones[target_name]
            target_pose = target.pose.bones[target_name]

            source_rest_rotation = source_bone.matrix_local.to_quaternion()
            source_pose_rotation = source_pose.matrix.to_quaternion()
            world_delta = source_pose_rotation @ source_rest_rotation.inverted()
            desired_rotation = world_delta @ target_bone.matrix_local.to_quaternion()
            desired_matrix = Matrix.LocRotScale(
                desired_head_position(target_pose),
                desired_rotation,
                Vector((1.0, 1.0, 1.0)),
            )
            target_pose.rotation_mode = "QUATERNION"
            target_pose.matrix = desired_matrix
            bpy.context.view_layer.update()
            target_pose.keyframe_insert(
                data_path="rotation_quaternion", frame=output_frame, group=target_name
            )

        target_root = target.pose.bones[mapping["hip"]]
        root_delta = (root_source.location - baseline_root_location) * motion_scale
        if not keep_horizontal_root_motion:
            root_delta.x = 0.0
            root_delta.y = 0.0
        target_root.location += root_delta
        bpy.context.view_layer.update()
        if not allow_airborne:
            ground_correction = ground_height - lowest_foot_height(target)
            root_matrix = target_root.matrix.copy()
            root_matrix.translation.z += ground_correction
            target_root.matrix = root_matrix
            bpy.context.view_layer.update()
            maximum_ground_correction = max(maximum_ground_correction, abs(ground_correction))
        target_root.keyframe_insert(data_path="location", frame=output_frame, group=target_root.name)

    bpy.context.scene.render.fps = output_fps
    bpy.context.scene.render.fps_base = 1.0
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = output_frames
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    action.use_frame_range = True
    action.frame_start = 1
    action.frame_end = output_frames

    return action, {
        "source_fps": source_fps,
        "source_frames": source_end - source_start + 1,
        "duration_seconds": duration_seconds,
        "output_fps": output_fps,
        "output_frames": output_frames,
        "motion_scale": motion_scale,
        "mapped_bones": len(mapping),
        "feet_grounded": not allow_airborne,
        "ground_height": ground_height,
        "maximum_ground_correction": maximum_ground_correction,
    }


def export_animated_glb(
    target: bpy.types.Object,
    output_path: Path,
) -> bpy.types.Object:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mesh = next(
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH"
        and any(
            modifier.type == "ARMATURE" and modifier.object == target
            for modifier in obj.modifiers
        )
    )
    bpy.ops.object.select_all(action="DESELECT")
    target.hide_set(False)
    mesh.hide_set(False)
    target.select_set(True)
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = target
    result = bpy.ops.export_scene.gltf(
        filepath=str(output_path),
        export_format="GLB",
        use_selection=True,
        export_animations=True,
        export_animation_mode="ACTIVE_ACTIONS",
        export_frame_range=True,
        export_nla_strips=False,
        export_morph=True,
        export_skins=True,
        export_all_influences=True,
        export_lights=False,
        export_cameras=False,
        export_extras=True,
    )
    if not output_path.is_file():
        raise RuntimeError(f"glTF exporter did not create {output_path}")
    print("GLB_EXPORT", result, "BYTES", output_path.stat().st_size)
    return mesh


def main() -> None:
    args = parse_args()
    target_path = Path(args.target).expanduser().resolve()
    motion_path = Path(args.motion).expanduser().resolve()
    output_blend = Path(args.output_blend).expanduser().resolve()
    output_glb = Path(args.output_glb).expanduser().resolve()
    for path in (target_path, motion_path):
        if not path.is_file():
            raise FileNotFoundError(path)

    bpy.ops.wm.open_mainfile(filepath=str(target_path))
    existing_objects = set(bpy.context.scene.objects)
    target = one_armature(list(existing_objects), "target")
    bpy.ops.import_anim.bvh(
        filepath=str(motion_path),
        frame_start=1,
        use_fps_scale=False,
        update_scene_fps=True,
    )
    imported_objects = [obj for obj in bpy.context.scene.objects if obj not in existing_objects]
    source = one_armature(imported_objects, "source")
    validate_mapping(source, target, DEFAULT_BONE_MAP)

    action, report = create_retargeted_action(
        source,
        target,
        DEFAULT_BONE_MAP,
        args.action_name,
        args.fps,
        args.keep_horizontal_root_motion,
        args.allow_airborne,
    )
    source.hide_set(True)
    source.hide_render = True
    output_blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_blend))
    mesh = export_animated_glb(target, output_glb)
    report.update(
        {
            "action": action.name,
            "target_armature": target.name,
            "target_bones": len(target.data.bones),
            "target_mesh": mesh.name,
            "shape_keys": len(mesh.data.shape_keys.key_blocks) if mesh.data.shape_keys else 0,
            "output_blend": str(output_blend),
            "output_glb": str(output_glb),
        }
    )
    print("RETARGET_REPORT", json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
