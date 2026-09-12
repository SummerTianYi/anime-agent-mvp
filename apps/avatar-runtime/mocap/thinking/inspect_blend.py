"""Codex: read-only source-rig evidence. Never save or modify the blend."""
import bpy
import json
import sys
from pathlib import Path

output = Path(sys.argv[sys.argv.index('--') + 1])
if output.exists():
    raise FileExistsError(output)
report = {'blend': bpy.data.filepath, 'armatures': [], 'meshes': []}
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        report['armatures'].append({'name': obj.name, 'count': len(obj.data.bones), 'bones': [
            {'name': bone.name, 'parent': bone.parent.name if bone.parent else None,
             'head': list(bone.head_local), 'tail': list(bone.tail_local),
             'matrix': [list(row) for row in bone.matrix_local]}
            for bone in obj.data.bones
        ]})
    if obj.type == 'MESH':
        report['meshes'].append({'name': obj.name, 'vertices': len(obj.data.vertices),
                                'bounds': [list(corner) for corner in obj.bound_box],
                                'shape_keys': len(obj.data.shape_keys.key_blocks) if obj.data.shape_keys else 0})
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('THINKING_SOURCE_INSPECTED', output)
