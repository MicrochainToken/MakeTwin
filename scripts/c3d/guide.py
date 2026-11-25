"""Stateful, chaptered manual authoring. One continuous NLA clip per guide."""
import json
import math
import bpy
from . import anim
from guide_schema import validate_guides, validate_camera


class Guide:
    def __init__(self, clip='how_to_use', title='How to use', initial_state='assembled_off', initial=None):
        self.clip, self.title, self.initial_state = clip, title, initial_state
        self.time, self.steps, self.channels, self.values, self.eases = 0, [], {}, {}, {}
        self.initial = dict(initial or {})
        for obj, value in self.initial.items():
            if not (obj.get('c3d_joint') or obj.get('c3d_glow')) or not math.isfinite(value):
                raise ValueError('Initial guide values need joints/glows and finite values')
            self.channels[obj] = [(0, value)]
            self.eases[obj] = ['linear']
            self.values[obj] = value
        self.finished = False

    def step(self, sid, instruction, targets=None, seconds=1, hold=.5, evidence=None, pause_after=False, camera=None, lead=None, ease=None):
        if self.finished:
            raise ValueError('Guide already finished')
        targets = dict(targets or {})
        rate = anim.fps()
        if camera is not None:
            validate_camera(camera, {o.get('c3d_part') for o in bpy.context.scene.objects if o.get('c3d_part')})
        lead = (camera.get('transitionSeconds', .8) if camera else 0) if lead is None else lead
        if isinstance(lead, bool) or not isinstance(lead, (int,float)) or not math.isfinite(lead) or lead < 0:
            raise ValueError('camera lead must be finite and nonnegative')
        lead_frames = math.ceil(lead * rate - 1e-8)
        ease = ease or anim.DEFAULT_EASE
        eases = ease if isinstance(ease, dict) else {}
        for e in (list(eases.values()) if eases else [ease]):
            if e not in anim.EASES:
                raise ValueError(f'Unknown ease {e!r}; use one of {sorted(anim.EASES)}')
        if any(isinstance(v, bool) or not isinstance(v, (int,float)) or not math.isfinite(v) for v in (seconds, hold)):
            raise ValueError('Step durations must be finite numbers')
        n, h = round(seconds * rate), round(hold * rate)
        if n < 1 or h < 0 or any(not math.isfinite(v) for v in targets.values()):
            raise ValueError('Step needs a positive duration, nonnegative hold and finite target values')
        start = round(self.time * rate)
        motion_start = start + lead_frames
        stop, end = motion_start + n, motion_start + n + h
        step = dict(id=sid, instruction=instruction, startSeconds=start/rate,
                    actionEndSeconds=stop/rate, endSeconds=end/rate,
                    evidence=evidence or [], pauseAfter=pause_after)
        if camera is not None or lead_frames:
            step['motionStartSeconds'] = motion_start/rate
        if camera is not None:
            step['camera'] = dict(camera)
        doc = dict(id=self.clip, clip=self.clip, title=self.title, initialState=self.initial_state,
                   steps=self.steps + [step])
        errors = validate_guides([doc], {self.clip:end/rate})
        if errors:
            raise ValueError('; '.join(errors))
        for obj, value in targets.items():
            if not obj.get('c3d_joint') and not obj.get('c3d_glow'):
                raise ValueError('Guide targets must be joints or registered glow parts')
            initial = self.initial.get(obj, 0)
            old = self.values.get(obj, initial)
            keys = self.channels.setdefault(obj, [(0, initial)])
            kinds = self.eases.setdefault(obj, ['linear'])
            if keys[-1][0] < motion_start:
                keys.append((motion_start, old)); kinds.append('linear')
            # Glows switch; joints move with the step's easing (per target if a dict was given).
            keys.append((stop, value)); kinds.append('linear' if obj.get('c3d_glow') else eases.get(obj, ease if not eases else anim.DEFAULT_EASE))
            if end > stop:
                keys.append((end, value)); kinds.append('linear')
            self.values[obj] = value
        self.steps.append(step)
        self.time = end/rate
        return self

    def finish(self):
        if self.finished or not self.steps or not self.channels:
            raise ValueError('Guide must have steps and at least one animated target; finish once')
        scene = bpy.context.scene
        existing = json.loads(scene.get('c3d_guides', '[]'))
        if any(g['id'] == self.clip for g in existing):
            raise ValueError('Duplicate guide ID')
        for obj in self.channels:
            if obj.animation_data and any(t.name == self.clip for t in obj.animation_data.nla_tracks):
                raise ValueError('Guide clip already exists on a target')
        for obj, keys in self.channels.items():
            kinds = self.eases.setdefault(obj, ['linear'] * len(keys))
            end = round(self.time * anim.fps())
            if keys[-1][0] < end:
                keys.append((end, keys[-1][1])); kinds.append('linear')
            if obj.get('c3d_joint'):
                anim._joint_keys(obj, self.clip, keys, kinds)
            else:
                full = obj['c3d_rest_scale']
                values = [(f, tuple(max(1e-4, v) * s for s in full)) for f,v in keys]
                anim._clip(obj, self.clip, values, 'scale', eases=kinds)
                obj.scale = (1e-4,)*3
        existing.append(dict(id=self.clip, clip=self.clip, title=self.title,
                             initialState=self.initial_state, steps=self.steps))
        for obj in self.channels:
            for track in obj.animation_data.nla_tracks:
                if track.name == self.clip:
                    track.mute = True
        scene['c3d_guides'] = json.dumps(existing)
        self.finished = True
        return self.clip
