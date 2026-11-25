import ast,math,json,sys,os
from pathlib import Path
import bpy
SKILL=Path(os.environ.get('C3D_SKILL_DIR',Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(SKILL/'scripts'))
from collision_cache import install
source=SKILL/'scripts/check_model.py'
tree=ast.parse(source.read_text());assert isinstance(tree.body[-1],ast.Expr);tree.body.pop()
ns={'__file__':str(source),'__name__':'reference_checker'}
exec(compile(tree,str(source),'exec'),ns)
core=ns['core']
core.reset_scene(product_size=(10,10,10))
from c3d import shapes,materials
mat=materials.get('painted_metal')
parts=[]
for i in range(6):
 o=shapes.box('fixture_'+str(i),(.8,.7,.6),center=(i*.65,0,.5))
 core.part(o,o.name,material=mat);parts.append(o)
for i in range(25):
 o=shapes.box('far_'+str(i),(.1,.1,.1),center=(10+i,4,.5));core.part(o,o.name,material=mat);parts.append(o)
bpy.context.view_layer.update()
def reference(objs,pad):
 data={}
 for o in objs:
  bm=ns['world_bm'](o);data[o.name]=(ns['BVHTree'].FromBMesh(bm),core.bbox_world(o));bm.free()
 hits={};names=list(data)
 for i,a in enumerate(names):
  for b in names[i+1:]:
   if not ns['boxes_touch'](data[a][1],data[b][1],pad):continue
   intersections=data[a][0].overlap(data[b][0])
   if intersections:hits[frozenset((a,b))]=len(intersections)
 return hits
fastns=ns.copy();cache=install(fastns);fast=fastns['overlap_pairs']
cases=0
for angle in (0,.35,1.2):
 for dx in (-.4,0,.5):
  parts[1].location.x+=dx;parts[1].rotation_euler.z=angle;bpy.context.view_layer.update()
  expected=reference(parts,.001)
  assert expected==fast(parts,.001),(expected,fast(parts,.001))
  selected={parts[1].name}
  assert {p:n for p,n in expected.items() if p&selected}==fast(parts,.001,include=selected)
  excluded=set(expected)
  assert fast(parts,.001,exclude=excluded)=={}
  cases+=1
# Modifiers and keyed/deformable data must bypass the rigid BVH cache.
mod=parts[2].modifiers.new('changing bevel','BEVEL');mod.segments=2
for width in (.02,.1):
 mod.width=width;bpy.context.view_layer.update()
 assert reference(parts,.001)==fast(parts,.001)
 cases+=1
# A new mesh with the same object name must invalidate its old cached geometry.
parts[3].data=parts[3].data.copy();bpy.context.view_layer.update()
assert reference(parts,.001)==fast(parts,.001)
report={'passed':True,'fixtures':cases+1,'checks':['intersection pairs and triangle-pair counts match original','moving-pair filter preserves eligible pairs','already-reported pairs omitted only after first finding','modifier changes bypass cache','mesh identity invalidates cache'],'samplingReduced':False}
Path('collision-cache-regression.json').write_text(json.dumps(report,indent=2));print('[c3d] collision equivalence tests passed',flush=True)
