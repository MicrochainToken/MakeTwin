const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../templates/viewer');
const asModule=source=>'data:text/javascript;base64,'+Buffer.from(source).toString('base64');
(async()=>{
const THREE=await import(asModule(fs.readFileSync(path.join(root,'vendor-build-three.module.js'),'utf8')));
globalThis.__testThree=THREE;globalThis.ExplorerState=require(path.join(root,'explorer-state.js'));
const {installExplorer}=await import(asModule(fs.readFileSync(path.join(root,'explorer-controller.js'),'utf8').replace("import * as THREE from 'three';",'const THREE=globalThis.__testThree;')));
const element=()=>({value:'',textContent:'',dataset:{},children:[],attrs:{},append(o){this.children.push(o);},setAttribute(k,v){this.attrs[k]=v;}});
globalThis.document={createElement:element,baseURI:'http://localhost/'};
const elements=Object.fromEntries(['select','input','.explorer-evidence','.explorer-notice','[data-action="apart"]','[data-action="restore"]'].map(k=>[k,element()]));
const buttons=['context','isolate','section'].map(mode=>({...element(),dataset:{mode}}));
const panel={innerHTML:'',querySelector:s=>elements[s],querySelectorAll:()=>buttons,closest:()=>null};
const scene=new THREE.Group(),parent=new THREE.Group();parent.rotation.y=.6;parent.position.set(2,3,1);scene.add(parent);
const material=new THREE.MeshStandardMaterial({color:0x445566}),geometry=new THREE.BoxGeometry(1,1,1);
const a=new THREE.Mesh(geometry,material);a.userData.c3d_part='a';a.position.set(.3,.5,.1);parent.add(a);
const b=new THREE.Mesh(geometry,material);b.userData.c3d_part='b';b.position.set(.2,.4,.3);a.add(b);
scene.updateMatrixWorld(true);
const localA=a.position.clone(),localB=b.position.clone(),worldA=a.getWorldPosition(new THREE.Vector3()),worldB=b.getWorldPosition(new THREE.Vector3());
const data={schemaVersion:1,groups:[{id:'a',label:'A',parts:['a'],offset:[1,0,0],start:0,end:1,evidence:'inferred',note:'test'},{id:'b',label:'B',parts:['b'],offset:[0,1,0],start:0,end:1,evidence:'inferred',note:'test'}]};
globalThis.fetch=async()=>({ok:true,status:200,json:async()=>data});
const controls=new THREE.EventDispatcher();controls.target=new THREE.Vector3();controls.update=()=>{};
const renderer={localClippingEnabled:false};const camera=new THREE.PerspectiveCamera(35,1,.01,100);camera.position.set(3,3,5);
const api=await installExplorer({root:scene,renderer,camera,controls,player:{release(){}},director:{manual(){}}},panel);
const near=(actual,expected)=>assert.ok(actual.distanceTo(expected)<1e-9,`${actual.toArray()} != ${expected.toArray()}`);
for(let i=0;i<30;i++){
 elements.input.value='1';elements.input.oninput();
 near(a.getWorldPosition(new THREE.Vector3()),worldA.clone().add(new THREE.Vector3(1,0,0)));
 near(b.getWorldPosition(new THREE.Vector3()),worldB.clone().add(new THREE.Vector3(0,1,0)));
 elements.input.value='0';elements.input.oninput();
 near(a.getWorldPosition(new THREE.Vector3()),worldA);near(b.getWorldPosition(new THREE.Vector3()),worldB);
}
elements.select.value='a';elements.select.onchange();buttons[1].onclick();
assert.notEqual(a.material,b.material);assert.equal(b.material.opacity,0);assert.equal(material.opacity,1);
buttons[2].onclick();assert.equal(a.material.clippingPlanes.length,1);assert.equal(material.clippingPlanes,null);
api.restore();near(a.position,localA);near(b.position,localB);assert.equal(a.material,material);assert.equal(b.material,material);assert.equal(renderer.localClippingEnabled,false);assert.equal(elements.select.value,'');
const toggle=elements['[data-action="apart"]'];
toggle.onclick();api.update(2.2);
const separated=a.getWorldPosition(new THREE.Vector3());
toggle.onclick();
near(a.getWorldPosition(new THREE.Vector3()),separated); // No snap on click.
api.update(1.1);
near(a.getWorldPosition(new THREE.Vector3()),worldA.clone().add(new THREE.Vector3(.5,0,0)));
assert.equal(api.active,true);
toggle.onclick();api.update(1.1); // Reverse direction again midway.
near(a.getWorldPosition(new THREE.Vector3()),separated);
toggle.onclick();api.update(2.2);
near(a.position,localA);near(b.position,localB);
assert.equal(api.active,false);assert.equal(a.material,material);
assert.equal(toggle.textContent,'Take apart');
api.dispose();delete globalThis.__testThree;
console.log('ok: real Three transforms, nested parts, material isolation, clipping and exact reset');
})().catch(e=>{console.error(e);process.exitCode=1;});
