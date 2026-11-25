"""Worked example: countertop microwave oven, 0.48 x 0.36 x 0.28 m.

Run:  scripts/blender.sh -b --python examples/mini-oven/build.py -- --out mini-oven.blend
Shows: rounded body with a boolean cavity, side-hinged door with a glass window and a
swept handle, lathe-turned knob and turntable, a push button in a clearance hole, an LED
with a power glow, rubber feet, side vent slots, and five animation clips.
"""
import os
import sys

SKILL_DIR = os.environ.get("MAKETWIN_SKILL_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
from c3d import anim, core, joints, materials, shapes  # noqa: E402

A = core.args()
OUT = os.path.abspath(A.get("out", "mini-oven.blend"))

W, D, H = 0.48, 0.36, 0.28          # overall size (PLAN.md: from a typical 20 L microwave)
FOOT = 0.010                        # rubber foot height
core.reset_scene(product_size=(W, D, H))
G = core.gap()                      # flicker-free gap for this product size (~0.4 mm)

# ---- materials (colours would come from the photos)
body_mat = materials.get("painted_metal", color="#d9dad7")
panel_mat = materials.get("abs_satin", color="#2a2c2f")
door_mat = materials.get("abs_satin", color="#2a2c2f")
glass_mat = materials.get("glass_tinted")
handle_mat = materials.get("aluminum_brushed")
knob_mat = materials.get("abs_satin", color="#c9cbcc")
button_mat = materials.get("abs_matte", color="#3a3c40")
led_mat = materials.get("led_lens")
glow_mat = materials.get("emissive", color="#ff4a2a", name="glow_red")
plate_mat = materials.get("glass_clear", color="#eef3f2")
foot_mat = materials.get("rubber")
cavity_mat = materials.get("painted_metal", color="#bfc2c3", name="cavity_paint")

# ---- body: rounded box sitting on its feet, front face at y = -D/2
body_h = H - FOOT
body = shapes.rounded_box("body", (W, D, body_h), radius=0.012, center=(0, 0, FOOT + body_h / 2),
                          segments=4)
front_y = -D / 2

# cooking cavity (left), cut from the front; cutter overshoots the front face by 1 cm
door_w = 0.335                       # door covers the cavity area; control strip on the right
cav = dict(x0=-W / 2 + 0.03, x1=-W / 2 + door_w - 0.03, z0=FOOT + 0.03, z1=H - 0.035, depth=0.29)
cutter = shapes.rounded_box("cav_cut", (cav["x1"] - cav["x0"], cav["depth"] + 0.01, cav["z1"] - cav["z0"]),
                            radius=0.01, center=((cav["x0"] + cav["x1"]) / 2, front_y + cav["depth"] / 2 - 0.005,
                                                 (cav["z0"] + cav["z1"]) / 2))
# power-button pocket and side vents
btn = dict(x=W / 2 - 0.072, z=FOOT + 0.07, w=0.044, h=0.018)
pocket = shapes.box("btn_pocket", (btn["w"] + 2 * G * 3, 0.02, btn["h"] + 2 * G * 3),
                    center=(btn["x"], front_y, btn["z"]))
vents = [shapes.rounded_box(f"vent{i}", (0.02, 0.09, 0.006), radius=0.0029,
                            center=(W / 2, 0.02, FOOT + 0.09 + i * 0.014)) for i in range(8)]
shapes.cut_many(body, [cutter, pocket] + vents)
body.data.materials.append(body_mat)
core.part(body, "body", label="Housing")
core.smooth(body)

# control strip: a separate dark front panel on the right, inset gap from the body face
strip_w = W - door_w - 2 * G
strip = shapes.rounded_box("control_panel", (strip_w - 0.012, 0.004, body_h - 0.03), radius=0.0018,
                           center=(W / 2 - strip_w / 2 - 0.004, front_y - 0.002 - G, FOOT + body_h / 2))
# the strip needs the same button hole as the body
pocket2 = shapes.box("btn_pocket2", (btn["w"] + 2 * G * 3, 0.03, btn["h"] + 2 * G * 3),
                     center=(btn["x"], front_y, btn["z"]))
shapes.boolean(strip, pocket2)
core.part(strip, "control_panel", material=panel_mat, label="Control panel")
core.smooth(strip)
panel_front = front_y - 0.004 - G

# ---- door (left, hinged on its left edge, swings towards the viewer)
door_t = 0.028
door_y = front_y - G - door_t / 2
door = shapes.rounded_box("door", (door_w - 2 * G, door_t, body_h - 0.006), radius=0.006,
                          center=(-W / 2 + door_w / 2, door_y, FOOT + body_h / 2))
# window opening through the door (you see the cavity through it); glass sits in a 6 mm deep rebate
win = dict(w=0.215, h=0.165, cx=-W / 2 + 0.03 + 0.215 / 2 + 0.012, cz=FOOT + body_h / 2)
opening = shapes.rounded_slab("win_cut", win["w"] - 0.016, win["h"] - 0.016, door_t + 0.01, radius=0.006,
                              center=(win["cx"], door_y, win["cz"]))
rebate = shapes.rounded_slab("win_rebate", win["w"], win["h"], 0.012, radius=0.008,
                             center=(win["cx"], door_y - door_t / 2, win["cz"]))
shapes.cut_many(door, [opening, rebate])
core.part(door, "door", material=door_mat, label="Door")
core.smooth(door)
rebate_back = door_y - door_t / 2 + 0.006
# glass corner radius = rebate radius minus the gap, so the corners keep the same clearance
glass = shapes.rounded_slab("door_glass", win["w"] - 2 * G, win["h"] - 2 * G, 0.004, radius=0.008 - G,
                            center=(win["cx"], rebate_back - G - 0.002, win["cz"]))
core.part(glass, "door_glass", material=glass_mat, parent=door, label="Door window")
core.smooth(glass)

# handle: vertical bar on the door's right edge, swept along a smooth path
hx = -W / 2 + door_w - 0.035
door_front = door_y - door_t / 2
hz0, hz1 = FOOT + 0.06, H - 0.06
path = [(hx, door_front + 0.004, hz0), (hx, door_front - 0.022, hz0 + 0.02),
        (hx, door_front - 0.026, (hz0 + hz1) / 2),
        (hx, door_front - 0.022, hz1 - 0.02), (hx, door_front + 0.004, hz1)]
handle = shapes.sweep("handle", path, radius=0.0065, segments=24)
core.part(handle, "door_handle", material=handle_mat, parent=door, label="Door handle")
core.smooth(handle)
core.allow_contact(handle, door, "handle ends are screwed into the door")

door_hinge = joints.hinge(door, pivot=(-W / 2 + G, door_y + door_t / 2, FOOT + body_h / 2),
                          axis="-Z", limits_deg=(0, 105), name="door_hinge")

# ---- controls on the strip
knob_z = FOOT + 0.175
knob_x = W / 2 - strip_w / 2 - 0.004
knob = shapes.lathe("knob", [(0, 0), (0.021, 0), (0.0215, 0.002), (0.0205, 0.018), (0.019, 0.022),
                             (0.0, 0.0225)],
                    center=(knob_x, panel_front - G, knob_z), axis="-Y", segments=96)
grip = shapes.rounded_box("grip", (0.007, 0.012, 0.03), radius=0.0025,
                          center=(knob_x, panel_front - G - 0.026, knob_z))
shapes.boolean(knob, grip, operation="UNION")
core.part(knob, "timer_knob", material=knob_mat, label="Timer knob")
core.smooth(knob)
knob_joint = joints.knob(knob, axis="-Y", center=(knob_x, panel_front, knob_z), limits_deg=(0, 270),
                         name="knob_turn")

button = shapes.rounded_box("power_button", (btn["w"], 0.012, btn["h"]), radius=0.004,
                            center=(btn["x"], front_y - 0.004 - G - 0.003 + 0.006, btn["z"]))
core.part(button, "power_button", material=button_mat, label="Start button")
core.smooth(button)
button_joint = joints.button(button, press_axis="Y", travel=0.003)

led = shapes.cylinder("power_led", 0.0035, 0.004, center=(btn["x"], panel_front - G - 0.002, btn["z"] + 0.035),
                      axis="Y", segments=32, bevel=0.0012)
core.part(led, "power_led", material=led_mat, label="Power light")
core.smooth(led)
led_glow = anim.glow_part("power_led_glow", led, glow_mat)

# ---- turntable inside the cavity
tt_c = ((cav["x0"] + cav["x1"]) / 2, front_y + cav["depth"] / 2, cav["z0"] + G)
plate = shapes.lathe("turntable", [(0, 0), (0.118, 0), (0.125, 0.004), (0.127, 0.012), (0.124, 0.013),
                                   (0.115, 0.006), (0, 0.005)], center=tt_c, axis="Z", segments=128)
core.part(plate, "turntable", material=plate_mat, label="Glass turntable")
core.smooth(plate)
plate_joint = joints.knob(plate, axis="Z", center=tt_c, limits_deg=(0, 360), name="turntable_spin")

# ---- feet
for i, (x, y) in enumerate([(-1, -1), (1, -1), (-1, 1), (1, 1)]):
    f = shapes.cylinder(f"foot_{i}", 0.014, FOOT - G, center=(x * (W / 2 - 0.04), y * (D / 2 - 0.04), (FOOT - G) / 2),
                        segments=48, bevel=0.003)
    core.part(f, f"foot_{i + 1}", material=foot_mat, label="Rubber foot")
    core.smooth(f)

# ---- cavity liner colour: the body's cavity faces get the lighter paint
body.data.materials.append(cavity_mat)
for poly in body.data.polygons:
    c = body.matrix_world @ poly.center
    if cav["x0"] - 1e-4 < c.x < cav["x1"] + 1e-4 and cav["z0"] - 1e-4 < c.z < cav["z1"] + 1e-4 \
            and c.y > front_y + 0.002:
        poly.material_index = 1

# ---- animations (all start from closed/off)
anim.open_close(door_hinge, clip="open_door", seconds=1.2)
anim.turn(knob_joint, clip="set_timer", degrees=180, seconds=1.0)
anim.power([led_glow], clip="power_on", buttons=[button_joint])
anim.turn(plate_joint, clip="turntable_spin", degrees=360, seconds=4.0)
# Extraction must follow the cavity opening, rather than a radial path through its wall.
tray_extract = joints.slider(plate_joint.parent, axis="-Y", origin=tt_c, limits=(0, 0.45),
                             name="turntable_extract")
anim.sequence("explode", [(door_hinge, [(0, 0), (1.2, 105)]),
                          (tray_extract, [(0, 0), (1.2, 0), (3.0, 0.45)])])

# Continuous instructional fixture: the door remains open during inspection.
g=anim.guide()
evidence=[{"source":"PLAN.md","locator":"Illustrative oven fixture; not a product manual"}]
g.step("open", "Open the door", {door_hinge:105}, evidence=evidence)
g.step("inspect", "Inspect the turntable; keep the door open", seconds=.5, hold=1, evidence=evidence, pause_after=True)
g.step("close", "Close the door", {door_hinge:0}, evidence=evidence)
g.step("power", "Press Start", {button_joint:.003, led_glow:1}, seconds=.2, hold=.1, evidence=evidence)
g.step("release", "Release Start; the indicator stays lit", {button_joint:0}, seconds=.2, evidence=evidence)
g.finish()
g2=anim.guide(clip="inspect_from_open", title="Inspect from open", initial_state="door_open", initial={door_hinge:105})
g2.step("look", "Inspect the open cavity", seconds=.5, evidence=evidence)
g2.step("close", "Close the door", {door_hinge:0}, evidence=evidence)
g2.finish()
core.finish(OUT)
