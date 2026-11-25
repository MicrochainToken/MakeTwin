"""Portable guide metadata validation; no Blender dependency."""
import math
import json
from pathlib import Path

CAMERA_ANGLES = json.loads((Path(__file__).resolve().parents[1] / "templates/viewer/camera-views.json").read_text())

CAMERA_VIEWS = set(CAMERA_ANGLES)


def validate_camera(camera, part_ids=None):
    if not isinstance(camera, dict) or camera.get('view', 'isometric') not in CAMERA_VIEWS:
        raise ValueError('camera needs a supported view')
    unknown = set(camera) - {'view', 'parts', 'padding', 'transitionSeconds', 'azimuth', 'elevation', 'minContext'}
    if unknown:
        raise ValueError('unknown camera fields: ' + ', '.join(sorted(unknown)))
    parts = camera.get('parts', [])
    if not isinstance(parts, list) or any(not isinstance(p, str) or not p.strip() for p in parts):
        raise ValueError('camera parts must be a list of nonempty part IDs')
    if part_ids is not None and set(parts) - set(part_ids):
        raise ValueError('camera references missing part IDs: ' + ', '.join(sorted(set(parts) - set(part_ids))))
    for key, default, lo, hi in [('padding', 1.5, 1.05, 4), ('transitionSeconds', .8, 0, 5), ('azimuth', 0, -180, 180), ('elevation', 25, -85, 85), ('minContext', .15, .05, 1)]:
        value = camera.get(key, default)
        if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value) or not lo <= value <= hi:
            raise ValueError('camera ' + key + ' outside its supported range')


def validate_guides(guides, clips, part_ids=None):
    errors, ids = [], set()
    if not isinstance(guides, list):
        return ['guides must be a list']
    for guide in guides:
        try:
            gid = guide['id']
            if not isinstance(gid, str) or not gid.strip() or gid in ids:
                raise ValueError('guide IDs must be nonempty and unique')
            ids.add(gid)
            if not guide['title'].strip() or not guide['initialState'].strip():
                raise ValueError('guide title and initial state are required')
            duration = clips[guide['clip']]
            if not guide['steps']:
                raise ValueError('guide needs steps')
            previous, steps = 0, set()
            for step in guide['steps']:
                if not step['id'].strip() or step['id'] in steps or not step['instruction'].strip():
                    raise ValueError('step IDs must be unique and captions nonempty')
                steps.add(step['id'])
                a, b, c = [step[k] for k in ('startSeconds','actionEndSeconds','endSeconds')]
                if (any(isinstance(v, bool) or not isinstance(v, (float,int)) or not math.isfinite(v) for v in (a,b,c))
                        or abs(a - previous) > 1e-5 or not a < b <= c or c > duration + 1e-4):
                    raise ValueError('step ranges must be finite, contiguous and inside the clip')
                if not isinstance(step.get('pauseAfter', False), bool):
                    raise ValueError('pauseAfter must be boolean')
                if not step['evidence'] or any(not e['source'].strip() or not e['locator'].strip() for e in step['evidence']):
                    raise ValueError('each step needs a source and evidence locator')
                previous = c
                motion_start = step.get('motionStartSeconds', a)
                if (isinstance(motion_start, bool) or not isinstance(motion_start, (int, float))
                        or not math.isfinite(motion_start) or not a <= motion_start < b):
                    raise ValueError('motion start must be finite and before action end')
                if 'camera' in step:
                    validate_camera(step['camera'], part_ids)
                    motion_start = step.get('motionStartSeconds', a)
                    if not a <= motion_start < b or step['camera'].get('transitionSeconds', .8) > motion_start-a+1e-5:
                        raise ValueError('camera transition must complete before mechanical motion starts')
            if abs(previous - duration) > 1e-4:
                raise ValueError('steps must cover the complete guide clip')
        except (KeyError, TypeError, ValueError, AttributeError) as error:
            errors.append(f'Invalid guide: {error}')
    return errors


def validate_clip_cameras(records, clips, part_ids=None):
    errors = []
    if not isinstance(records, dict):
        return ['clipCameras must be an object keyed by clip name']
    for name, record in records.items():
        try:
            duration = clips[name]
            validate_camera(record['camera'], part_ids)
            a, b, c = (record[k] for k in ('motionStartSeconds', 'actionEndSeconds', 'endSeconds'))
            if (any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (a,b,c))
                    or not 0 <= a < b <= c or abs(c-duration) > 1e-4
                    or record['camera'].get('transitionSeconds', .8) > a + 1e-5):
                raise ValueError('clip camera timing must preserve lead-in and cover clip')
        except (KeyError, TypeError, ValueError) as error:
            errors.append(f'Invalid clip camera {name}: {error}')
    return errors
