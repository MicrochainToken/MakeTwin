"""Blender regression: rigid pose bake, rest preservation and real NLA evaluation."""
import math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import bpy
from mathutils import Quaternion
from c3d import core,mechanism,shapes,materials
core.reset_scene(product_size=(.2,.2,.2))
handle=bpy.data.objects.new('mechanism_attachment',None);bpy.context.scene.collection.objects.link(handle)
handle.location=(.02,.01,.03);handle.rotation_euler=(.1,.2,.3)
rest=handle.matrix_basis.copy();bpy.context.view_layer.update();rest=handle.matrix_world.copy()
poses=[(0,(.02,.01,.03),tuple(handle.rotation_euler.to_quaternion())),(12,(.06,.04,.03),tuple(Quaternion((0,0,1),math.pi/2))),(24,(.1,.07,.03),tuple(Quaternion((0,0,1),math.pi)))]
action=mechanism.bake_transform(handle,'run_cycle',poses)
bpy.context.view_layer.update()
assert max(abs(handle.matrix_world[i][j]-rest[i][j]) for i in range(4) for j in range(4))<1e-6
handle.animation_data.nla_tracks[0].mute=False
for frame,pos,q in poses:
 bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
 assert (handle.location-__import__('mathutils').Vector(pos)).length<1e-6, (frame,tuple(handle.location),pos,[(x.frame_start,x.frame_end,x.action_frame_start,x.action_frame_end,x.influence) for x in handle.animation_data.nla_tracks[0].strips])
 assert abs(handle.rotation_quaternion.dot(Quaternion(q)))>1-1e-6
assert handle.animation_data.nla_tracks[0].name=='run_cycle'
try:mechanism.bake_transform(handle,'run_cycle',poses);raise AssertionError('Duplicate accepted')
except ValueError:pass
# Save a visible, registered part so the full suite verifies actual GLB channels too.
rod=core.part(shapes.rounded_box('fixture',(.02,.004,.004),.001),'link_fixture',materials.get('aluminum_brushed'),parent=handle)
handle.animation_data.nla_tracks[0].mute=True
core.finish(core.args().get('out','mechanism-baked.blend'))
print('ok mechanism rigid-transform bake and NLA poses')
