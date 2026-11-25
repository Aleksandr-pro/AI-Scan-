import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const source = await readFile(new URL('../melon-experiment/behavior/scripts/scanner.js', import.meta.url), 'utf8');
const recovery = await readFile(new URL('../melon-experiment/recovery/scripts/scanner.js', import.meta.url), 'utf8');
assert.equal(source, recovery);
const {createScanner} = await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const blocks = new Map([['0,64,0','minecraft:melon_block'],['1,64,0','minecraft:stone'],['2,64,0','minecraft:melon_block'],['7,61,7','minecraft:melon_block']]);
let gets=0, writes=0;
const dimension = {id:'minecraft:overworld',getBlock({x,y,z}) { gets++; const key = [x,y,z].join(','); return {
  get typeId() {return blocks.get(key) || 'minecraft:air';},
  setPermutation(value) {writes++; blocks.set(key,value);}
}; }};
const player = {id:'a',dimension,location:{x:.5,y:64,z:.5}};
const notices=[];
const scan = createScanner('minecraft:melon_block','aimelon:fruit',x=>x,(_,type,detail)=>notices.push({type,detail}),{reportExisting:true});
scan.tick([player]);
assert.equal(blocks.get('0,64,0'),'aimelon:fruit');
assert.equal(blocks.get('2,64,0'),'aimelon:fruit');
assert.equal(blocks.get('1,64,0'),'minecraft:stone');
assert.ok(notices.some(n=>n.type==='changed' && n.detail.at.x===0 && n.detail.at.y===64 && n.detail.at.z===0));
assert.ok(notices.some(n=>n.type==='changed' && n.detail.at.x===2));
assert.equal(blocks.get('7,61,7'),'minecraft:melon_block'); // full range is incremental
for (let i=0;i<20;i++) scan.tick([player]);
assert.equal(blocks.get('7,61,7'),'aimelon:fruit');
assert.equal(writes,3);
assert.ok(notices.some(n=>n.type==='existing'));
const restore = createScanner('aimelon:fruit','minecraft:melon_block',x=>x,()=>{});
for (let i=0;i<20;i++) restore.tick([player]);
assert.equal(blocks.get('0,64,0'),'minecraft:melon_block');
assert.equal(blocks.get('2,64,0'),'minecraft:melon_block');
assert.equal(blocks.get('7,61,7'),'minecraft:melon_block');
assert.equal(blocks.get('1,64,0'),'minecraft:stone');

// Moving to another block restarts the near-first search rather than using a
// stale cursor that could delay nearby fruit for a full scan.
const moving = createScanner('minecraft:melon_block','aimelon:fruit',x=>x,()=>{});
blocks.set('100,64,100','minecraft:melon_block');
moving.tick([player]);
moving.tick([{...player,location:{x:100.5,y:64,z:100.5}}]);
assert.equal(blocks.get('100,64,100'),'aimelon:fruit');

// A setter can return without actually changing storage: don't claim success.
let failures=[];
const noopDim={id:'test',getBlock(){return {typeId:'minecraft:melon_block',setPermutation(){}}}};
const noop=createScanner('minecraft:melon_block','aimelon:fruit',x=>x,(_,t,d)=>failures.push({t,d}));
noop.tick([{...player,dimension:noopDim}]);
assert.ok(failures.some(n=>n.t==='unconfirmed' && n.d.actual==='minecraft:melon_block'));
assert.equal(failures.some(n=>n.t==='changed'),false);
failures=[];
const throwing=createScanner('minecraft:melon_block','aimelon:fruit',()=>{throw new Error('unknown block')},(_,t,d)=>failures.push({t,d}));
throwing.tick([{...player,dimension:noopDim}]);
assert.ok(failures.some(n=>n.t==='error' && String(n.d.error).includes('unknown block')));
assert.equal(failures.some(n=>n.t==='changed'),false);

// Exceptions while fetching unloaded chunks are expected and skipped.
const unloaded=[];
const bad=createScanner('minecraft:melon_block','aimelon:fruit',x=>x,(_,t)=>unloaded.push(t));
bad.tick([{...player,dimension:{id:'test',getBlock(){throw new Error('unloaded')}}}]);
assert.deepEqual(unloaded,['running']);
// Two players are served per tick and service rotates when there are more.
const served=[];
const empty={id:'empty',getBlock(){return {typeId:'minecraft:air'}}};
const group=Array.from({length:5},(_,i)=>({...player,id:String(i),dimension:empty}));
const bounded=createScanner('minecraft:melon_block','aimelon:fruit',x=>x,(p,t)=>{if(t==='running')served.push(p.id)});
bounded.tick(group); bounded.tick(group); bounded.tick(group); bounded.tick(group);
assert.deepEqual(new Set(served),new Set(['0','1','2','3','4']));
console.log('Melon scanner near-first search, readback, recovery and errors passed');
