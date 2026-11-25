import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const source = await readFile(new URL('../melon-experiment/behavior/scripts/scanner.js', import.meta.url), 'utf8');
const recovery = await readFile(new URL('../melon-experiment/recovery/scripts/scanner.js', import.meta.url), 'utf8');
assert.equal(source, recovery);
const {createScanner} = await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const blocks = new Map([['0,64,0','minecraft:melon_block'],['1,64,0','minecraft:stone'],['2,64,0','minecraft:melon_block']]);
let gets=0, writes=0;
const dimension = {getBlock({x,y,z}) { gets++; const key = [x,y,z].join(','); return {
  get typeId() {return blocks.get(key) || 'minecraft:air';},
  setPermutation(value) {writes++; blocks.set(key,value);}
}; }};
const player = {id:'a', dimension, location:{x:.5,y:64,z:.5}};
const notices=[];
const scan = createScanner('minecraft:melon_block','aimelon:fruit', x=>x, (_,type)=>notices.push(type));
for (let i=0; i<20; i++) { const before=gets; scan.tick([player]); assert.equal(gets-before,80); }
assert.equal(blocks.get('0,64,0'),'aimelon:fruit');
assert.equal(blocks.get('2,64,0'),'aimelon:fruit');
assert.equal(blocks.get('1,64,0'),'minecraft:stone');
assert.equal(writes,2);
assert.ok(notices.includes('changed'));
const restore = createScanner('aimelon:fruit','minecraft:melon_block', x=>x, ()=>{});
for (let i=0; i<20; i++) restore.tick([player]);
assert.equal(blocks.get('0,64,0'),'minecraft:melon_block');
assert.equal(blocks.get('2,64,0'),'minecraft:melon_block');
assert.equal(blocks.get('1,64,0'),'minecraft:stone');
const players = Array.from({length:10}, (_,i)=>({...player,id:String(i)}));
const before=gets; scan.tick(players); assert.equal(gets-before,160);
let errorSeen=false;
const bad=createScanner('minecraft:melon_block','aimelon:fruit',x=>x,(_,t)=>{if(t==='error') errorSeen=true});
bad.tick([{...player,dimension:{getBlock(){throw new Error('unloaded')}}}]);
assert.equal(errorSeen,true);
console.log('Melon scanner bounds, replacement, restoration, and failure tests passed');
