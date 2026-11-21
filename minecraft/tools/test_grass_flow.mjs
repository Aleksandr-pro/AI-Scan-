import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const dir = new URL('../grass-flow-experiment/behavior/scripts/', import.meta.url);
const fieldText = await readFile(new URL('field.js', dir), 'utf8');
const uri = `data:text/javascript;base64,${Buffer.from(fieldText).toString('base64')}`;
const f = await import(uri);
const ctrlText = (await readFile(new URL('controller.js', dir), 'utf8')).replace("'./field.js'", `'${uri}'`);
const {createController} = await import(`data:text/javascript;base64,${Buffer.from(ctrlText).toString('base64')}`);

// Every adjacent block shares the two corner samples exactly, including negative coords.
for (let x = -50; x <= 50; x++) for (let z = -50; z <= 50; z++) {
  const [nw, ne, sw, se] = f.corners(x, z);
  const [rnw, , rsw] = f.corners(x+1, z);
  const [dnw, dne] = f.corners(x, z+1);
  assert.deepEqual([ne, se], [rnw, rsw]);
  assert.deepEqual([sw, se], [dnw, dne]);
  assert.deepEqual(f.states(x, z), f.states(x, z));
  assert.ok([nw,ne,sw,se].every(c => [0,1,2].includes(c)));
}

let cells = new Map(), messages = [], writes = [], unavailable = false;
const key = p => `${p.x},${p.y},${p.z}`;
const dim = {getBlock(p) {
  if (unavailable) return undefined;
  const k = key(p);
  return {get typeId() { return cells.get(k)?.id ?? 'minecraft:air'; },
    setPermutation(perm) { cells.set(k, perm); writes.push([k, perm.id]); }};
}};
const player = {typeId:'minecraft:player', location:{x:0.5,y:100,z:0.5}, dimension:dim, sendMessage:m=>messages.push(m)};
const controller = createController((id, states) => ({id, states}));
const run = () => {for(let i=0;i<140;i++) controller.tick();};
controller.tick(); assert.equal(writes.length, 0); // Never acts spontaneously.
cells.set('-16,99,-16',{id:'minecraft:stone'});
controller.begin(player,'preview'); run();
assert.equal(writes.length, 0); assert.equal(cells.get('-16,99,-16').id,'minecraft:stone');
cells.clear(); messages=[];
controller.begin(player,'preview'); run();
assert.equal(writes.length, 1024);
assert.ok([...cells.values()].every(c=>c.id === 'grassflow:sample'));
assert.deepEqual(cells.get('-16,99,-16').states,f.states(-16,-16));
controller.begin(player,'clear'); run();
assert.equal(writes.length, 2048);
assert.ok([...cells.values()].every(c=>c.id === 'minecraft:air'));
// New terrain during preflight/build is never overwritten.
cells.clear(); writes=[];
controller.begin(player,'preview');
for(let i=0;i<64;i++) controller.tick();
cells.set('-16,99,-16',{id:'minecraft:diamond_block'});
controller.tick();
assert.equal(cells.get('-16,99,-16').id,'minecraft:diamond_block'); assert.equal(writes.length, 0);
// Unavailable chunks abort before writing.
cells.clear(); unavailable=true;
controller.begin(player,'preview'); run(); assert.equal(writes.length,0);
// Clear checks IDs and never touches other block types.
unavailable=false; cells.set('-16,99,-16',{id:'minecraft:stone'});
controller.begin(player,'clear');run();assert.equal(cells.get('-16,99,-16').id,'minecraft:stone');
console.log('Field continuity and safe opt-in controller checks passed.');
