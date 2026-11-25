const assert=require('node:assert/strict');
const {validate,offsets}=require('../templates/viewer/explorer-state.js');
const group=(id,parts,start,end,offset)=>({id,label:id,parts,start,end,offset,evidence:'inferred',note:'Approximate test layout'});
const data={schemaVersion:1,groups:[group('cover',['cover'],0,.4,[0,2,0]),group('drive',['shaft','gear'],.4,1,[3,0,0])]};
const groups=validate(data,['cover','shaft','gear']).groups;
assert.deepEqual([...offsets(groups,0).values()],[[0,0,0],[0,0,0],[0,0,0]]);
assert.deepEqual(offsets(groups,.2).get('cover'),[0,1,0]);
assert.deepEqual(offsets(groups,.2).get('shaft'),[0,0,0]);
assert.deepEqual(offsets(groups,.7).get('shaft').map(x=>+x.toFixed(6)),[1.5,0,0]);
assert.deepEqual(offsets(groups,1).get('shaft'),[3,0,0]);
assert.deepEqual(offsets(groups,1).get('shaft'),offsets(groups,1).get('gear'));
// History-free seeking: back/forth does not accumulate displacement.
const expected=[...offsets(groups,.7)];for(let i=0;i<1000;i++){offsets(groups,1);offsets(groups,0);}assert.deepEqual([...offsets(groups,.7)],expected);
for(const bad of [NaN,Infinity,-Infinity])assert.throws(()=>offsets(groups,bad));
const invalid=[{...data,schemaVersion:2},{...data,groups:[group('a',['missing'],0,1,[1,0,0])]},{...data,groups:[group('a',['shaft'],0,1,[1,0,0]),group('b',['shaft'],0,1,[0,1,0])]},{...data,groups:[group('a',['shaft'],.7,.2,[1,0,0])]},{...data,groups:[group('a',['shaft'],0,1,[Infinity,0,0])]},{...data,groups:[{...groups[0],evidence:'verified'}]}];
for(const bad of invalid)assert.throws(()=>validate(bad,['cover','shaft','gear']));
assert.equal(data.groups[0].offset[1],2);groups[0].offset[1]=100;assert.equal(data.groups[0].offset[1],2);
console.log('ok: staged reveal, rigid membership, deterministic seek, metadata validation');
