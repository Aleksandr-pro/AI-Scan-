import assert from 'node:assert/strict';
import { createController, findSurface, REGISTRY, PAUSED, LIMIT } from '../rain-wetness/behavior/scripts/wetness.js';

const k = p => `${p.x},${p.y},${p.z}`;
const dry = { 'rainwet:dirt': 'minecraft:dirt', 'rainwet:grass': 'minecraft:grass_block', 'rainwet:stone': 'minecraft:stone' };
function fixture() {
  const blocks = new Map();
  const props = new Map();
  const unloaded = new Set();
  let writes = 0, failSave = false, biome = 'minecraft:plains';
  function put(p, id, states = {}) { blocks.set(k(p), { id, states }); }
  const dim = {
    getPlayers: () => [{ location: { x: 0, y: 64, z: 0 } }],
    getBiome: () => ({ id: biome }),
    getBlock: p => {
      if (unloaded.has(k(p))) return undefined;
      const v = blocks.get(k(p)) || { id: 'minecraft:air', states: {} };
      return { typeId: v.id, isAir: v.id === 'minecraft:air', isWaterlogged: false,
        location: { x: p.x, y: p.y, z: p.z }, permutation: { getAllStates: () => v.states },
        setType(id) { writes++; put(p, id); }, setPermutation(perm) { writes++; put(p, perm.id, perm.states); } };
    },
    getTopmostBlock: ({ x, z }) => dim.getBlock({ x, y: 63, z }),
  };
  const world = {
    getDimension: () => dim,
    getDynamicProperty: id => props.get(id),
    setDynamicProperty: (id, value) => { if (failSave) throw Error('storage failed'); props.set(id, value); },
  };
  const resolve = (id, states) => ({ id, states });
  const create = () => createController(world, resolve, () => .5);
  put({ x: 0, y: 63, z: 0 }, 'minecraft:dirt', { dirt_type: 'normal' });
  return { put, blocks, props, unloaded, dim, world, create, get writes() { return writes; },
    set biome(v) { biome = v; }, set failSave(v) { failSave = v; } };
}

const a = fixture();
let c = a.create();
c.tick();
assert.equal(a.writes, 0, 'unknown weather is conservative');
c.weatherChanged({ dimension: 'minecraft:nether', newWeather: 'Rain' }); c.tick();
assert.equal(a.writes, 0);
c.weatherChanged({ dimension: 'minecraft:overworld', newWeather: 'Rain' }); c.tick();
assert.equal(a.blocks.get('0,63,0').id, 'rainwet:dirt');
assert.deepEqual(JSON.parse(a.props.get(REGISTRY))[0].states, { dirt_type: 'normal' });
c.tick(); assert.equal(a.writes, 1, 'no double-wetting');
c.weatherChanged({ dimension: 'overworld', newWeather: 'Clear' }); c.tick();
assert.deepEqual(a.blocks.get('0,63,0'), { id: 'minecraft:dirt', states: { dirt_type: 'normal' } });
assert.equal(c.status().remaining, 0);

// Restart during rain: unknown state causes restoration rather than rewetting.
c.weatherChanged({ dimension: 'overworld', newWeather: 'Rain' }); c.tick();
c = a.create(); c.tick();
assert.equal(a.blocks.get('0,63,0').id, 'minecraft:dirt');
// Pause persists and restores even while raining.
c.weatherChanged({ dimension: 'overworld', newWeather: 'Rain' }); c.tick();
c.pause(); c.tick();
assert.equal(a.props.get(PAUSED), true);
assert.equal(a.blocks.get('0,63,0').id, 'minecraft:dirt');
c = a.create(); c.weatherChanged({ dimension: 'overworld', newWeather: 'Rain' }); c.tick();
assert.equal(a.blocks.get('0,63,0').id, 'minecraft:dirt');
c.resume(); c.tick(); assert.equal(a.blocks.get('0,63,0').id, 'rainwet:dirt');
// Player changes the location; restoration must never replace their block.
a.put({ x: 0, y: 63, z: 0 }, 'minecraft:diamond_block'); c.pause(); c.tick();
assert.equal(a.blocks.get('0,63,0').id, 'minecraft:diamond_block');
assert.equal(c.status().remaining, 0);

for (const v of ['covered', 'biome', 'unloaded', 'storage', 'corrupt']) {
  const t = fixture(), ctrl = t.create();
  if (v === 'covered') t.put({ x: 0, y: 64, z: 0 }, 'minecraft:oak_leaves');
  if (v === 'biome') t.biome = 'minecraft:desert';
  if (v === 'unloaded') t.unloaded.add('0,63,0');
  if (v === 'storage') t.failSave = true;
  if (v === 'corrupt') t.props.set(REGISTRY, '{');
  ctrl.weatherChanged({ dimension: 'overworld', newWeather: 'Rain' }); ctrl.tick();
  assert.equal(t.writes, 0, v);
}
const capped = fixture();
const capRecords = Array.from({ length: LIMIT }, (_, x) => ({ x: x + 100, y: 63, z: 0, original: 'minecraft:dirt', wet: 'rainwet:dirt', states: {} }));
capped.props.set(REGISTRY, JSON.stringify(capRecords));
const capController = capped.create();
capController.weatherChanged({ dimension: 'overworld', newWeather: 'Rain' }); capController.tick();
assert.equal(capped.writes, 0, 'world-wide wet block cap is enforced');

const grass = fixture(); grass.put({ x: 0, y: 63, z: 0 }, 'minecraft:grass_block');
assert.equal(findSurface(grass.dim, 0, 0, 64).wet, 'rainwet:grass');
grass.put({ x: 0, y: 63, z: 0 }, 'minecraft:stone');
assert.equal(findSurface(grass.dim, 0, 0, 64).wet, 'rainwet:stone');
grass.put({ x: 0, y: 63, z: 0 }, 'minecraft:chest');
assert.equal(findSurface(grass.dim, 0, 0, 64), undefined);

// Restore must not starve loaded positions behind four unloaded ones.
const t = fixture();
const records = Array.from({ length: LIMIT }, (_, x) => ({ x, y: 63, z: 0, original: 'minecraft:dirt', wet: 'rainwet:dirt', states: {} }));
t.props.set(REGISTRY, JSON.stringify(records));
for (const r of records) t.put(r, r.wet);
for (let i = 0; i < 4; i++) t.unloaded.add(`${i},63,0`);
const ctrl = t.create();
for (let i = 0; i < 40; i++) ctrl.tick();
assert.equal(ctrl.status().remaining, 4, 'unloaded tracked positions are preserved; other positions restore');
t.unloaded.clear();
for (let i = 0; i < 4; i++) ctrl.tick();
assert.equal(ctrl.status().remaining, 0);
for (const entry of t.blocks.values()) assert.ok(!dry[entry.id], 'restored all custom blocks');
console.log('Wetness logic passed mock safety, persistence, weather and restoration tests.');
