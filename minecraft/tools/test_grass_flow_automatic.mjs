import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const dir = new URL('../grass-flow-automatic/behavior/scripts/', import.meta.url);
const fsrc = await readFile(new URL('field.js', dir),'utf8');
const uri = `data:text/javascript;base64,${Buffer.from(fsrc).toString('base64')}`;
const f = await import(uri);
const src = (await readFile(new URL('automatic.js', dir),'utf8')).replace("'./field.js'", `'${uri}'`);
const {createController,load,JOURNAL,CONTROL,CUSTOM,LIMIT} = await import(`data:text/javascript;base64,${Buffer.from(src).toString('base64')}`);

function setup() {
  const props = new Map(), blocks = new Map(), writes = [], scores = new Map([['session', 123]]);
  const board = {getScore:k=>scores.get(k), setScore:(k,v)=>scores.set(k,v)};
  let failJournal = false, unloaded = false, failSet = false;
  let player = {id:'p', location:{x:0,y:64,z:0}};
  const key = p => `${p.x},${p.y},${p.z}`;
  function value(p) {return blocks.get(key(p)) ?? (p.y === 64 ? {id:'minecraft:grass_block', states:{snowy_bit:false}} : {id:'minecraft:air', states:{}});}
  function block(p) { return {
    location:{...p}, get typeId(){return value(p).id;}, get isWaterlogged(){return false;},
    get permutation(){return {getAllStates:()=>value(p).states};},
    setPermutation(perm){ if(failSet) throw Error('unloaded'); blocks.set(key(p),perm); writes.push([key(p),perm.id]); },
  }; }
  const dim = {getPlayers:()=>player ? [player]:[], getTopmostBlock:({x,z})=>unloaded?undefined:block({x,y:64,z}),
    getBlock:p=>unloaded?undefined:block(p)};
  const world = {scoreboard:{getObjective:k=>k===CONTROL?board:undefined}, getDimension:()=>dim, getDynamicProperty:k=>props.get(k),
    setDynamicProperty(k,v){if(failJournal && k===JOURNAL)throw Error('disk error');props.set(k,v);}};
  const ctl=createController(world,(id,states)=>({id,states:states??{}}));
  return {props,blocks,writes,scores,world,ctl, setPlayer:p=>player=p,
    failJournal:v=>failJournal=v, unload:v=>unloaded=v, failSet:v=>failSet=v};
}
// No call -> no mutations; write-ahead journal records exact vanilla states.
let s=setup(); assert.equal(s.writes.length,0); s.ctl.tick(100);
assert.equal(s.writes.length,4); assert.equal(load(s.world).length,4);
for(const r of load(s.world)) {
  assert.deepEqual(r.s,{snowy_bit:false});
  assert.deepEqual(s.blocks.get(`${r.x},${r.y},${r.z}`).states,f.states(r.x,r.z));
}
// A failed property write cannot replace the block.
s=setup();s.failJournal(true);s.ctl.tick(100);assert.equal(s.writes.length,0);
assert.equal(s.props.has(JOURNAL),false);
// Crashes/failures after journal write retain original data and reconcile later.
s=setup();s.failSet(true);s.ctl.tick(100);assert.equal(s.writes.length,0);assert.ok(load(s.world).length>0);
s.failSet(false);s.scores.set('pause',1);for(let i=0;i<50;i++)s.ctl.tick(200+i*10);
assert.equal(load(s.world).length,0);
// Sticky recovery mode restores loaded blocks and never starts replacements.
s=setup();for(let i=0;i<80;i++)s.ctl.tick(200+i*10);assert.ok(load(s.world).length>0);assert.ok(load(s.world).length<=LIMIT);
s.scores.set('pause',1);for(let i=0;i<50;i++)s.ctl.tick(2000+i*10);
assert.equal(load(s.world).length,0);assert.ok([...s.blocks.values()].every(b=>b.id==='minecraft:grass_block'));
const done=s.writes.length;s.ctl.tick(3000);assert.equal(s.writes.length,done);
// Never resurrect a block the player has replaced.
s=setup();s.ctl.tick(100);let record=load(s.world)[0];let pos=`${record.x},${record.y},${record.z}`;
s.blocks.set(pos,{id:'minecraft:diamond_block',states:{}});s.scores.set('pause',1);
for(let i=0;i<5;i++)s.ctl.tick(200+i*10);assert.equal(s.blocks.get(pos).id,'minecraft:diamond_block');assert.equal(load(s.world).length,0);
// Unloaded chunks are retained for later and cannot be reported restored.
s=setup();s.ctl.tick(100);s.scores.set('pause',1);s.unload(true);
for(let i=0;i<10;i++)s.ctl.tick(200+i*10);assert.equal(load(s.world).length,4);
s.unload(false);for(let i=0;i<5;i++)s.ctl.tick(400+i*10);assert.equal(load(s.world).length,0);
// Corrupt journal fails closed, no replacements.
s=setup();s.props.set(JOURNAL,'not json');s.ctl.tick(100);assert.equal(s.writes.length,0);
// Move away: old loaded custom blocks restore instead of accumulating endlessly.
s=setup();s.ctl.tick(100);const old=load(s.world).map(r=>`${r.x},${r.y},${r.z}`);
s.setPlayer({id:'p',location:{x:100,y:64,z:100}});for(let i=0;i<3;i++)s.ctl.tick(200+i*10);
assert.ok(old.every(k=>s.blocks.get(k)?.id==='minecraft:grass_block'));
console.log('Automatic grass flow: safe mutation, restoration, interruption tests passed.');
