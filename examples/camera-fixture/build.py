"""Deterministic, generic service enclosure. No external/product inputs."""
from pathlib import Path
import sys
SKILL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILL / 'scripts'))
from c3d import core, shapes, materials, joints, anim

core.reset_scene(product_size=(.34,.32,.35), fps=30)
metal=materials.get('painted_metal', color='#d5e1dd')
blue=materials.get('abs_satin', color='#287c9f')
orange=materials.get('abs_matte', color='#e47a32')
rubber=materials.get('rubber')
body=shapes.rounded_box('housing',(.34,.30,.30),radius=.008,center=(0,0,.18))
shapes.cut_many(body,[shapes.rounded_box('interior',(.29,.26,.31),radius=.004,center=(0,0,.215)),
    shapes.box('rear_port',(.27,.05,.215),center=(0,.145,.185)),
    shapes.box('button_pocket',(.036,.036,.06),center=(.10,-.08,.035))])
core.part(body,'housing',material=metal);core.smooth(body)
for x in [-.13,.13]:
    for y in [-.11,.11]:
        core.part(shapes.rounded_box('foot',(.035,.035,.026),radius=.003,center=(x,y,.013)),
            f'foot_{"l" if x<0 else "r"}_{"f" if y<0 else "b"}',material=rubber)
hatch=core.part(shapes.rounded_box('rear_hatch',(.265,.008,.21),radius=.003,center=(0,.156,.185)),
    'rear_hatch',material=blue)
hinge=joints.hinge(hatch,pivot=(-.1325,.156,.185),axis='Z',limits_deg=(0,105),name='rear_hinge')
cover=core.part(shapes.rounded_box('top_cover',(.29,.26,.012),radius=.004,center=(0,0,.339)),
    'top_cover',material=blue)
lift=joints.slider(cover,'Z',limits=(0,.12),name='top_lift_joint')
button=core.part(shapes.rounded_box('underside_button',(.024,.024,.008),radius=.002,center=(.10,-.08,.027)),
    'underside_button',material=orange)
press=joints.button(button,'Z',travel=.006,name='underside_press_joint')
# A fixed internal feature gives the top/rear openings useful visual context.
core.part(shapes.rounded_box('insert',(.10,.10,.07),radius=.006,center=(0,0,.11)),
    'insert',material=orange)
rear=dict(view='rear',parts=['rear_hatch','housing'],padding=1.25,transitionSeconds=.8)
top=dict(view='top',azimuth=150,elevation=15,parts=['top_cover','housing','insert'],padding=1.2,transitionSeconds=.7)
under=dict(view='underside',azimuth=25,elevation=-65,parts=['underside_button','housing'],padding=1.2,transitionSeconds=.9)
anim.open_close(hinge,clip='rear_open',seconds=1.2)
anim.camera_clip('rear_open',rear)
anim.open_close(lift,clip='top_inspect',seconds=1)
anim.camera_clip('top_inspect',top)
anim.press(press,clip='underside_press',seconds=.6)
anim.camera_clip('underside_press',under)
evidence=[dict(source='generic fixture specification',locator='build.py; synthetic demonstration, no manual')]
g=anim.guide(title='Service enclosure demonstration')
g.step('rear','Open the rear hatch.',{hinge:105},seconds=1.2,hold=.4,evidence=evidence,camera=rear)
g.step('top','Lift the top cover and inspect the orange insert.',{lift:.12},seconds=1,hold=.4,evidence=evidence,camera=top,pause_after=True)
g.step('under','Press the underside control.',{press:.006},seconds=.4,hold=.3,evidence=evidence,camera=under)
g.step('release','Release the underside control.',{press:0},seconds=.3,hold=.3,evidence=evidence,camera={**under,'transitionSeconds':0})
g.finish()
# Nonzero initial-state regression: unrelated joints and default rest must stay isolated.
h=anim.guide('close_from_open','Close from open',initial_state='rear open; top raised',initial={hinge:105,lift:.12})
h.step('close','Close the rear hatch while the cover stays raised.',{hinge:0},seconds=.8,hold=.2,evidence=evidence,camera=rear)
h.finish()
for obj in core.parts():
    core.smooth(obj)
core.finish(core.args().get('out','model.blend'))
