"""Deterministic review-shot math, matching viewer camera-director.js.
Coordinates are glTF (x, z, -y from Blender); named angles share camera-views.json.
"""
import math
from guide_schema import CAMERA_ANGLES


def lerp(a, b, t):
    return a + (b-a)*t


def vector_lerp(a, b, t):
    return [lerp(x,y,t) for x,y in zip(a,b)]


def distance(a, b):
    return math.dist(a,b)


def fit_distance(radius, fov, aspect, padding=1.5):
    if not all(math.isfinite(v) for v in (radius,fov,aspect,padding)) or not (radius>0 and 0<fov<180 and aspect>0 and padding>=1):
        raise ValueError('Invalid camera fit')
    v=math.radians(fov)/2
    return radius*padding/math.sin(min(v,math.atan(math.tan(v)*aspect)))


def box_shot(box, spec, overview):
    yaw,pitch=CAMERA_ANGLES[spec.get('view','isometric')]
    return dict(target=vector_lerp(box['min'],box['max'],.5),
                radius=max(distance(box['min'],box['max'])/2,
                           distance(overview['min'],overview['max'])/2*spec.get('minContext',.15),1e-5),
                padding=spec.get('padding',1.5),yaw=spec.get('azimuth',yaw),pitch=spec.get('elevation',pitch))


def shot_at(steps, time, bounds_at, overview, reduced_motion=False):
    intro=box_shot(overview,{},overview)
    if time<=0 or not steps:
        return intro
    i=next((i for i,s in enumerate(steps) if time<s['endSeconds']-1e-8),len(steps)-1)
    step=steps[i]; spec=step.get('camera') or {}
    def tracked(s,t):
        camera=s.get('camera') or {};start=s.get('motionStartSeconds',s['startSeconds'])
        t=min(t,s['actionEndSeconds'])
        current=box_shot(bounds_at(t,camera.get('parts')),camera,overview)
        result=dict(current)
        for lag in (.06,.12,.18):
            old=box_shot(bounds_at(max(start,t-lag),camera.get('parts')),camera,overview)
            result['target']=vector_lerp(result['target'],old['target'],.18)
            result['radius']=lerp(result['radius'],old['radius'],.18)
        result['radius']=max(result['radius'],current['radius']+distance(current['target'],result['target']))
        return result
    dest=tracked(step,max(time,step.get('motionStartSeconds',step['startSeconds'])))
    duration=spec.get('transitionSeconds',.8 if spec else 0)
    if reduced_motion or not duration or time>=step['startSeconds']+duration:
        return dest
    previous=tracked(steps[i-1],step['startSeconds']) if i else intro
    k=max(0,min(1,(time-step['startSeconds'])/duration));k=k*k*(3-2*k)
    return dict(target=vector_lerp(previous['target'],dest['target'],k),
                radius=lerp(previous['radius'],dest['radius'],k),padding=lerp(previous['padding'],dest['padding'],k),
                yaw=previous['yaw']+((dest['yaw']-previous['yaw']+540)%360-180)*k,
                pitch=lerp(previous['pitch'],dest['pitch'],k))


def position_for(shot, fov, aspect, overview):
    yaw,pitch=math.radians(shot['yaw']),math.radians(shot['pitch'])
    direction=[math.sin(yaw)*math.cos(pitch),math.sin(pitch),math.cos(yaw)*math.cos(pitch)]
    d=fit_distance(shot['radius'],fov,aspect,shot['padding'])
    center=vector_lerp(overview['min'],overview['max'],.5);r=distance(overview['min'],overview['max'])/2
    offset=[a-b for a,b in zip(shot['target'],center)];dot=sum(a*b for a,b in zip(offset,direction))
    d=max(d,-dot+math.sqrt(max(0,dot*dot+r*r-sum(x*x for x in offset)))+r*.02)
    return dict(target=shot['target'],position=[v+x*d for v,x in zip(shot['target'],direction)],distance=d)
