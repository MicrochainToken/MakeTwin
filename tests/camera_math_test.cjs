const assert=require('node:assert/strict');
const {fitDistance,blendShot,shotAt,positionFor,createShotController,stepIndex}=require('../templates/viewer/camera-director.js');
const views=require('../templates/viewer/camera-views.json');
const overview={min:[-1,-1,-1],max:[1,1,1]};
const steps=[
 {startSeconds:0,motionStartSeconds:1,actionEndSeconds:3,endSeconds:4,camera:{view:'rear',parts:['hatch'],padding:1.2,transitionSeconds:1}},
 {startSeconds:4,motionStartSeconds:5,actionEndSeconds:6,endSeconds:7,camera:{view:'top',parts:['lid'],transitionSeconds:1}},
 {startSeconds:7,motionStartSeconds:8,actionEndSeconds:9,endSeconds:10,camera:{view:'underside',parts:['button'],transitionSeconds:1}}
];
const boundsAt=(t,parts)=>{const x=parts?.includes('hatch')?Math.max(0,Math.min(t-1,2)):.3;
 return {min:[x-.2,-.1,-.1],max:[x+.2,.1,.1]};};
const shot=time=>shotAt({steps,time,boundsAt,overview,views});
const near=(a,b,eps=1e-8)=>assert.ok(Math.abs(a-b)<eps,`${a} != ${b}`);
assert.deepEqual(shot(0).target,[0,0,0]);near(shot(0).yaw,-35);
near(shot(1).yaw,180);near(shot(5).pitch,75);near(shot(8).pitch,-60);
const start=shot(.00001),before=shot(.99999);assert.ok(Math.abs(start.yaw+35)<1e-6);near(Math.abs(before.yaw),180,1e-6);
assert.ok(shot(.5).target[0]<shot(1).target[0]+1e-8); // target blends during lead-in
assert.ok(shot(4.5).target[0]<shot(4).target[0] && shot(4.5).target[0]>shot(5).target[0]);
assert.ok(shot(.5).radius<shot(0).radius && shot(.5).radius>shot(1).radius);
const moving=shot(2),later=shot(2.5);assert.ok(later.target[0]>moving.target[0]);
assert.ok(moving.target[0]<1 && moving.target[0]>.8,'tracking smooths, but follows current motion');
assert.deepEqual(shot(3),shot(3.8),'end reading hold freezes the camera');
assert.deepEqual(shot(9),shot(10),'final sample selects last chapter');
assert.equal(stepIndex(steps,10),2);
for(const t of [0,.2,.8,1,2.1,3,4.4,5,7.5,9,10]){
 const saved=shot(t);for(let n=0;n<100;n++)shot((n*7.137)%10);assert.deepEqual(shot(t),saved,'seek is history independent');
}
const a={target:[0,0,0],radius:1,padding:1.2,yaw:170,pitch:0};
const b={target:[10,4,2],radius:3,padding:1.6,yaw:-170,pitch:60};
const midpoint=blendShot(a,b,.5);near(midpoint.yaw,180);assert.deepEqual(midpoint.target,[5,2,1]);near(midpoint.radius,2);
for(const value of [NaN,Infinity,0,-1])assert.throws(()=>fitDistance(value,35,1));
assert.throws(()=>fitDistance(1,35,Infinity));assert.throws(()=>fitDistance(1,180,1));
assert.ok(fitDistance(1,35,.35)>fitDistance(1,35,2.4));
// Project every moving focus-box corner into the actual perspective frustum.
const sub=(a,b)=>a.map((v,i)=>v-b[i]),dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
const norm=a=>a.map(x=>x/Math.hypot(...a));
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
for(const aspect of [.28,.5,1,2.4,4])for(const t of [1,1.1,2,3,5,6,8,9]){
 const s=shot(t),p=positionFor(s,35,aspect,overview),forward=norm(sub(p.target,p.position)),right=norm(cross(forward,[0,1,0])),up=cross(right,forward);
 const box=boundsAt(t,steps[stepIndex(steps,t)].camera.parts),v=Math.tan(35*Math.PI/360);
 for(const x of [box.min[0],box.max[0]])for(const y of [box.min[1],box.max[1]])for(const z of [box.min[2],box.max[2]]){
   const rel=sub([x,y,z],p.position),depth=dot(rel,forward);assert.ok(depth>0);
   assert.ok(Math.abs(dot(rel,right))/(depth*v*aspect)<=1,'horizontal clipping');
   assert.ok(Math.abs(dot(rel,up))/(depth*v)<=1,'vertical clipping');
 }
}
// Finite-difference smoothness across both ends of lead-in and moving-target tracking.
for(const t of [.999,1.001,1.5,2,2.9,4.999,5.001]){
 const x=shot(t),y=shot(t+.001);assert.ok(Math.hypot(...sub(x.target,y.target))<.005);
 assert.ok(Math.abs(x.radius-y.radius)<.005);assert.ok(Math.abs(((x.yaw-y.yaw+540)%360)-180)<1);
}
let current=a,writes=0;
const controller=createShotController({evaluate:shot,read:()=>current,write:s=>{current=s;writes++;}});
controller.reset();const initial=current;controller.update(0,1);assert.equal(writes,1,'paused timeline freezes');
controller.update(2,.1);const automatic=current;
controller.manual();current=b;controller.update(3,1);assert.equal(current,b,'manual override wins');
controller.auto(3);controller.update(3,0);assert.deepEqual(current,b,'auto resumes from user shot');
controller.update(3,.3);assert.notDeepEqual(current,b);controller.update(3,.3);assert.deepEqual(current,shot(3));
controller.reset();assert.deepEqual(current,initial);assert.equal(controller.enabled,true);
const reduced=shotAt({steps,time:.01,boundsAt,overview,views,reducedMotion:true});near(reduced.yaw,180);
console.log('camera math/controller: lead-in, tracking, easing, holds, aspect/frustum, seek, pause, manual/auto, restart and reduced motion pass');
