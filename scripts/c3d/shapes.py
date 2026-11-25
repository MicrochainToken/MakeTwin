"""Primitives with clean topology for product parts.

Every function returns a new mesh object linked to the scene, positioned in world space.
Register it with core.part(...) afterwards. Sizes in metres.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

from . import core

AXES = {"X": Vector((1, 0, 0)), "Y": Vector((0, 1, 0)), "Z": Vector((0, 0, 1)),
        "-X": Vector((-1, 0, 0)), "-Y": Vector((0, -1, 0)), "-Z": Vector((0, 0, -1))}


def _vec(v):
    return AXES[v].copy() if isinstance(v, str) else Vector(v).normalized()


def _to_obj(name, bm):
    mesh = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    return core.link(obj)


def _orient(bm, axis, center):
    """Rotate geometry built along +Z to point along `axis`, then move it to `center`."""
    rot = Vector((0, 0, 1)).rotation_difference(_vec(axis)).to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(center)) @ rot, verts=bm.verts)


# ---------------------------------------------------------------- boxes

def box(name, size, center=(0, 0, 0)):
    """Sharp box. Prefer rounded_box for anything visible."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    return _to_obj(name, bm)


def rounded_box(name, size, radius, center=(0, 0, 0), segments=4, top_radius=None):
    """Box with all edges rounded by `radius` (clamped to fit).

    top_radius: optional different radius for the top edges only (e.g. a soft moulded lid).
    """
    w, d, h = size
    r = min(radius, 0.49 * min(w, d, h))
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    if top_radius is None:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=r, offset_type="OFFSET", segments=segments,
                        profile=0.5, affect="EDGES", clamp_overlap=True)
    else:
        rt = min(top_radius, 0.49 * min(w, d, h))
        top = [e for e in bm.edges if all(v.co.z > 0 for v in e.verts)]
        rest = [e for e in bm.edges if e not in top]
        bmesh.ops.bevel(bm, geom=top, offset=rt, offset_type="OFFSET", segments=segments,
                        profile=0.5, affect="EDGES", clamp_overlap=True)
        rest = [e for e in rest if e.is_valid]
        bmesh.ops.bevel(bm, geom=rest, offset=r, offset_type="OFFSET", segments=segments,
                        profile=0.5, affect="EDGES", clamp_overlap=True)
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    return _to_obj(name, bm)


def rounded_slab(name, width, height, depth, radius, center=(0, 0, 0), axis="Y", n_corner=8):
    """Rounded rectangle (width x height, corner radius) extruded `depth` along `axis`.

    Straight walls, sharp front/back edges. Use for panels, glass, displays, buttons and as a
    boolean cutter for recesses: unlike rounded_box it does not curve the recess floor.
    """
    w, h = width, height
    a = section_rounded_rect(w, h, radius, z=-depth / 2, n_corner=n_corner)
    b = section_rounded_rect(w, h, radius, z=depth / 2, n_corner=n_corner)
    obj = loft(name, [a, b])
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    # Build a right-handed frame with height as close to world Z as possible.
    # A 180-degree rotation_difference has an ambiguous spin axis; using it here
    # swapped width/height for +Y panels.
    ax = _vec(axis)
    up = Vector((0, 1, 0)) if abs(ax.z) > 0.9 else Vector((0, 0, 1))
    up = (up - ax * up.dot(ax)).normalized()
    right = up.cross(ax).normalized()
    rot = Matrix((right, up, ax)).transposed().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(center)) @ rot, verts=bm.verts)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return obj


# ---------------------------------------------------------------- round shapes

def cylinder(name, radius, height, center=(0, 0, 0), axis="Z", segments=64, bevel=0.0):
    """Cylinder centred on `center`, its length along `axis`. bevel rounds both rims."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments,
                          radius1=radius, radius2=radius, depth=height)
    if bevel > 0:
        rims = [e for e in bm.edges if all(abs(abs(v.co.z) - height / 2) < 1e-9 for v in e.verts)]
        bmesh.ops.bevel(bm, geom=rims, offset=min(bevel, 0.49 * radius, 0.49 * height),
                        offset_type="OFFSET", segments=3, profile=0.5, affect="EDGES", clamp_overlap=True)
    _orient(bm, axis, center)
    return _to_obj(name, bm)


def lathe(name, profile, center=(0, 0, 0), axis="Z", segments=96):
    """Revolve a 2D profile [(radius, height), ...] around `axis`.

    Order the profile along the outside surface. Start and end at radius 0 for a closed
    solid (knobs, bottles, plates); otherwise the ends are left open. Repeat a point to
    keep a crisp crease there.
    """
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r <= 1e-9:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(a), r * math.sin(a), z))
                          for a in (2 * math.pi * i / segments for i in range(segments))])
    for a, b in zip(rings[:-1], rings[1:]):
        if len(a) == 1 and len(b) == 1:
            continue
        for i in range(segments):
            j = (i + 1) % segments
            if len(a) == 1:
                bm.faces.new((a[0], b[i], b[j]))
            elif len(b) == 1:
                bm.faces.new((a[i], b[0], a[j]))
            else:
                bm.faces.new((a[i], b[i], b[j], a[j]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-9)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    _orient(bm, axis, center)
    return _to_obj(name, bm)


def sweep(name, path, radius, segments=24, cap=True, smooth_path=True):
    """Sweep a round tube of `radius` along a 3D `path` [(x,y,z), ...].

    For handles, cables, tubular frames, chair legs. smooth_path=True turns the points into a
    smooth Bezier curve; False keeps straight segments with sharp corners.
    """
    cu = bpy.data.curves.new(name + "_path", "CURVE")
    cu.dimensions = "3D"
    cu.resolution_u = 24
    cu.bevel_depth = radius
    cu.bevel_resolution = max(2, segments // 4 - 1)
    cu.use_fill_caps = cap
    if smooth_path:
        sp = cu.splines.new("BEZIER")
        sp.bezier_points.add(len(path) - 1)
        for bp, p in zip(sp.bezier_points, path):
            bp.co = p
            bp.handle_left_type = bp.handle_right_type = "AUTO"
    else:
        sp = cu.splines.new("POLY")
        sp.points.add(len(path) - 1)
        for pt, p in zip(sp.points, path):
            pt.co = (*p, 1.0)
    tmp = core.link(bpy.data.objects.new(name + "_curve", cu))
    dg = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    mesh.name = name
    bpy.data.objects.remove(tmp)
    bpy.data.curves.remove(cu)
    obj = core.link(bpy.data.objects.new(name, mesh))
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bm.to_mesh(mesh)
    bm.free()
    return obj


# ---------------------------------------------------------------- sections and lofts

def section_rounded_rect(w, d, r, z=0.0, n_corner=8, center=(0, 0)):
    """Closed loop for a rounded rectangle in the XY plane at height z."""
    r = min(r, 0.499 * min(w, d))
    pts = []
    for cx, cy, a0 in ((w / 2 - r, d / 2 - r, 0), (-w / 2 + r, d / 2 - r, 90),
                       (-w / 2 + r, -d / 2 + r, 180), (w / 2 - r, -d / 2 + r, 270)):
        for i in range(n_corner + 1):
            a = math.radians(a0 + 90 * i / n_corner)
            pts.append((center[0] + cx + r * math.cos(a), center[1] + cy + r * math.sin(a), z))
    return pts


def section_superellipse(w, d, z=0.0, exponent=2.5, n=64, center=(0, 0)):
    """Closed loop between an ellipse (exponent 2) and a rounded rectangle (exponent 4+)."""
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        x = w / 2 * math.copysign(abs(c) ** (2 / exponent), c)
        y = d / 2 * math.copysign(abs(s) ** (2 / exponent), s)
        pts.append((center[0] + x, center[1] + y, z))
    return pts


def loft(name, sections, cap_start=True, cap_end=True):
    """Skin closed loops (same point count, same winding) into one surface.

    Use for bodies whose cross-section changes smoothly: kettles, mice, seat shells.
    More sections = more control; keep them evenly spaced along the length.
    """
    n = len(sections[0])
    if any(len(s) != n for s in sections):
        raise ValueError("loft: every section needs the same number of points")
    bm = bmesh.new()
    loops = [[bm.verts.new(p) for p in s] for s in sections]
    for a, b in zip(loops[:-1], loops[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    for loop, use in ((loops[0], cap_start), (loops[-1], cap_end)):
        if use:
            c = bm.verts.new(sum((v.co for v in loop), Vector()) / n)
            for i in range(n):
                bm.faces.new((c, loop[(i + 1) % n], loop[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _to_obj(name, bm)


def subdivided(name, verts, faces, levels=2, creases=None):
    """Subdivision surface from a coarse cage (verts, faces).

    The cage controls the shape like a sculptor's armature: few points, smooth result.
    creases: {(i, j): 0..1} edge sharpness by vertex index pair (1 = fully sharp).
    """
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    mesh.update()
    if creases:
        attr = mesh.attributes.get("crease_edge") or mesh.attributes.new("crease_edge", "FLOAT", "EDGE")
        lookup = {frozenset(e.vertices): e.index for e in mesh.edges}
        for (i, j), value in creases.items():
            idx = lookup.get(frozenset((i, j)))
            if idx is not None:
                attr.data[idx].value = value
    obj = core.link(bpy.data.objects.new(name, mesh))
    mod = obj.modifiers.new("subsurf", "SUBSURF")
    mod.levels = mod.render_levels = levels
    core.apply_modifiers(obj)
    return obj


def extrude_outline(name, outline, depth, plane="XZ", offset=0.0, bevel=0.0):
    """Extrude a flat 2D outline [(u, v), ...] by `depth`.

    plane "XZ": outline drawn as seen from the front, extruded towards +Y starting at y=offset.
    plane "XY": drawn from above, extruded up from z=offset. plane "YZ": seen from the side.
    """
    bm = bmesh.new()
    if plane == "XZ":
        pts = [(u, offset, v) for u, v in outline]
        direction = Vector((0, depth, 0))
    elif plane == "XY":
        pts = [(u, v, offset) for u, v in outline]
        direction = Vector((0, 0, depth))
    else:
        pts = [(offset, u, v) for u, v in outline]
        direction = Vector((depth, 0, 0))
    face = bm.faces.new([bm.verts.new(p) for p in pts])
    res = bmesh.ops.extrude_face_region(bm, geom=[face])
    moved = [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=direction, verts=moved)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, offset_type="OFFSET", segments=3,
                        profile=0.5, affect="EDGES", clamp_overlap=True)
    return _to_obj(name, bm)


# ---------------------------------------------------------------- editing

def _is_manifold(obj):
    """True for a clean closed solid: watertight (every edge shared by exactly two faces) and,
    when it holds several separate shells (e.g. joined pieces), none of their bounds overlap.
    Overlapping or nested shells self-intersect, which only the EXACT solver handles."""
    me = obj.data
    if not me.polygons:
        return False
    bm = bmesh.new()
    bm.from_mesh(me)
    ok = all(e.is_manifold for e in bm.edges) and not any(v.is_wire for v in bm.verts)
    if ok:
        bm.verts.ensure_lookup_table()
        seen, boxes = set(), []
        for start in bm.verts:
            if start.index in seen:
                continue
            seen.add(start.index)
            stack, lo, hi = [start], list(start.co), list(start.co)
            while stack:
                v = stack.pop()
                for i in range(3):
                    lo[i] = min(lo[i], v.co[i]); hi[i] = max(hi[i], v.co[i])
                for e in v.link_edges:
                    w = e.other_vert(v)
                    if w.index not in seen:
                        seen.add(w.index)
                        stack.append(w)
            boxes.append((lo, hi))
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                (alo, ahi), (blo, bhi) = boxes[i], boxes[j]
                if all(alo[k] < bhi[k] and blo[k] < ahi[k] for k in range(3)):
                    ok = False
                    break
            if not ok:
                break
    bm.free()
    return ok


def _bbox_overlap(a, b):
    (alo, ahi), (blo, bhi) = core.bbox_world(a), core.bbox_world(b)
    return all(alo[i] <= bhi[i] and blo[i] <= ahi[i] for i in range(3))


def _manifold_solver_available():
    """MANIFOLD arrived in Blender 4.5; older Blender (the Skill supports 4.2+) has only EXACT/FLOAT."""
    items = bpy.types.BooleanModifier.bl_rna.properties["solver"].enum_items
    return "MANIFOLD" in {e.identifier for e in items}


def _fast_eligible(obj):
    """Only a plain mesh whose stored data is exactly what Blender evaluates: any unapplied modifier
    (mirror, array, solidify...) would make the watertightness test look at the wrong geometry."""
    return obj.type == "MESH" and len(obj.modifiers) == 0 and _is_manifold(obj)


def _apply_boolean(target, cutter, operation, solver):
    mod = target.modifiers.new("bool", "BOOLEAN")
    mod.operation = operation
    mod.solver = solver
    if solver == "EXACT":
        mod.use_self = True        # joined cutters may overlap each other
        mod.use_hole_tolerant = True
    mod.object = cutter
    core.apply_modifiers(target)


def boolean(target, cutter, operation="DIFFERENCE", keep_cutter=False):
    """Cut/join `cutter` into `target` and apply. Use for recesses, holes, slots.

    Watertight operands without unapplied modifiers use Blender's fast MANIFOLD solver (Blender
    4.5+, typically 50x faster than EXACT, which matters on slow server CPUs); anything else, or
    a MANIFOLD result that did not change an overlapping target, uses the EXACT solver.
    Make cutters overshoot the surface they pass through by at least core.gap() so no
    coincident faces remain.
    """
    solver = "EXACT"
    if _manifold_solver_available() and _fast_eligible(target) and _fast_eligible(cutter):
        before = target.data.copy()
        n_before = (len(before.vertices), len(before.polygons))
        _apply_boolean(target, cutter, operation, "MANIFOLD")
        me = target.data
        unchanged = (len(me.vertices), len(me.polygons)) == n_before
        if me.polygons and not (unchanged and _bbox_overlap(target, cutter)):
            solver = "MANIFOLD"
            bpy.data.meshes.remove(before)
        else:                       # failed or no-op on an overlapping cutter: redo exactly
            failed = target.data
            target.data = before
            before.name = failed.name
            bpy.data.meshes.remove(failed)
    if solver == "EXACT":
        _apply_boolean(target, cutter, operation, "EXACT")
    if not keep_cutter:
        cutter_mesh = cutter.data
        bpy.data.objects.remove(cutter)
        if cutter_mesh is not None and cutter_mesh.users == 0:
            bpy.data.meshes.remove(cutter_mesh)
    return target


def cut_many(target, cutters):
    """Subtract cutters sequentially (MANIFOLD solver when watertight, else EXACT).

    Joining intersecting cutters concatenates surfaces rather than unioning them.
    Sequential cuts avoid handing that self-intersecting operand to the solver.
    Check the resulting topology; this does not guarantee every boolean succeeds.
    """
    for cutter in cutters:
        boolean(target, cutter)
    return target


def bevel(obj, width, segments=3, angle_deg=30.0):
    """Round the edges sharper than angle_deg (for meshes made by booleans or extrusion)."""
    mod = obj.modifiers.new("bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(angle_deg)
    mod.harden_normals = False
    core.apply_modifiers(obj)
    return obj


def shell(obj, thickness, inward=True):
    """Give an open surface a real wall thickness (sheet metal, moulded shells, fabric)."""
    mod = obj.modifiers.new("shell", "SOLIDIFY")
    mod.thickness = thickness
    mod.offset = -1.0 if inward else 1.0
    mod.use_even_offset = True
    core.apply_modifiers(obj)
    return obj


def move(obj, offset):
    obj.location = Vector(obj.location) + Vector(offset)
    return obj


def rotate(obj, degrees, axis="Z", pivot=(0, 0, 0)):
    """Rotate mesh data about a world pivot (applied to vertices)."""
    m = (Matrix.Translation(Vector(pivot)) @ Matrix.Rotation(math.radians(degrees), 4, _vec(axis))
         @ Matrix.Translation(-Vector(pivot)))
    obj.data.transform(obj.matrix_world.inverted() @ m @ obj.matrix_world)
    obj.data.update()
    return obj
