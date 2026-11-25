"""A held pose that differs from rest must remain an animation channel."""
import os,sys,json,struct
from pathlib import Path
import bpy
SKILL=Path(os.environ.get('C3D_SKILL_DIR',Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(SKILL/'scripts'))
from c3d import core,shapes,materials,anim
from fast_animation_export import export_flattened
core.reset_scene(product_size=(1,1,1),fps=30)
o=core.part(shapes.box('part',(.1,.1,.1),center=(0,0,.1)),'part',material=materials.get('abs_satin'))
base=tuple(o.location)
anim._clip(o,'how_to_use',[(0,base),(30,(.1,base[1],base[2]))],'location')
anim._clip(o,'held',[(0,(.2,base[1],base[2])),(30,(.2,base[1],base[2]))],'location')
for t in o.animation_data.nla_tracks:t.mute=True
o.location=base;bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
p=Path('fast-export-regression.glb');export_flattened(p)
b=p.read_bytes();length=struct.unpack_from('<I',b,12)[0];d=json.loads(b[20:20+length]);data=b[28+length:]
node=next(i for i,n in enumerate(d['nodes']) if n.get('name')=='part')
assert abs(d['nodes'][node].get('translation',[0,0,0])[0])<1e-6,'Exported rest contaminated by a clip'
a=next(a for a in d['animations'] if a['name']=='held')
c=next((c for c in a['channels'] if c['target']=={'node':node,'path':'translation'}),None)
assert c is not None,'Held pose differing from rest was dropped'
acc=d['accessors'][a['samplers'][c['sampler']]['output']];view=d['bufferViews'][acc['bufferView']]
for i in range(acc['count']):
 x,y,z=struct.unpack_from('<fff',data,view.get('byteOffset',0)+acc.get('byteOffset',0)+i*12)
 assert abs(x-.2)<1e-6 and abs(y-.1)<1e-6 and abs(z)<1e-6,(x,y,z)
print('[c3d] fast held-pose export regression passed',flush=True)
