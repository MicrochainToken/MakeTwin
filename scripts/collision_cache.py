"""Conservative acceleration of rigid mesh collision checks.

No sampling, distance thresholds or collision exemptions are changed. Cache only
unmodified rigid mesh geometry at an exactly identical world transform. Sweep
world AABBs before the original BVH intersection test.
"""


def install(namespace):
    cache = {}
    world_bm = namespace['world_bm']
    core = namespace['core']
    BVHTree = namespace['BVHTree']
    boxes_touch = namespace['boxes_touch']

    def cached_trees(objs):
        out = {}
        for o in objs:
            rigid = not o.modifiers and not o.data.shape_keys and not o.data.animation_data
            key = (o.data.as_pointer(), tuple(v for row in o.matrix_world for v in row),
                   len(o.data.vertices), len(o.data.polygons))
            old = cache.get(o.name)
            if rigid and old is not None and old[0] == key:
                value = old[1]
            else:
                bm = world_bm(o)
                value = BVHTree.FromBMesh(bm), core.bbox_world(o)
                bm.free()
                if rigid:
                    cache[o.name] = key, value
                else:
                    cache.pop(o.name, None)
            out[o.name] = value
        return out

    def overlap_pairs(objs, pad, include=None, exclude=None):
        data = cached_trees(objs)
        ordered = sorted(data, key=lambda n: data[n][1][0].x)
        active = []
        hits = {}
        for b in ordered:
            low = data[b][1][0].x
            active = [a for a in active if data[a][1][1].x + pad >= low]
            for a in active:
                pair = frozenset((a, b))
                if include is not None and not (pair & include):
                    continue
                if exclude is not None and pair in exclude:
                    continue
                if not boxes_touch(data[a][1], data[b][1], pad):
                    continue
                overlaps = data[a][0].overlap(data[b][0])
                if overlaps:
                    hits[pair] = len(overlaps)
            active.append(b)
        return hits

    namespace['trees'] = cached_trees
    namespace['overlap_pairs'] = overlap_pairs
    return cache
