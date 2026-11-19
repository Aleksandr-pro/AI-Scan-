import assert from 'node:assert/strict';
import { createController, findBasin, MAX_SOURCES, PROPERTY } from '../realistic-rain-water/scripts/puddles.js';

const key = ({ x, y, z }) => `${x},${y},${z}`;
function fixture() {
  const blocks = new Map();
  const at = (x, y, z, typeId) => blocks.set(key({ x, y, z }), typeId);
  at(5, 63, 0, 'minecraft:dirt');
  for (const [dx, dz] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) at(5 + dx, 64, dz, 'minecraft:dirt');
  let biome = 'minecraft:plains';
  let ceiling = false;
  let unloaded = false;
  let failSave = false;
  let prop;
  let writes = 0;
  const dimension = {
    getPlayers: () => [{ location: { x: 0, y: 64, z: 0 } }],
    getBiome: () => ({ id: biome }),
    getTopmostBlock: ({ x, z }) => ceiling ? { typeId: 'minecraft:stone', location: { x, y: 90, z } } :
      ({ typeId: blocks.get(key({ x, y: 63, z })) || 'minecraft:air', location: { x, y: 63, z } }),
    getBlock: p => {
      if (unloaded) return undefined;
      const typeId = blocks.get(key(p)) || 'minecraft:air';
      return { typeId, isAir: typeId === 'minecraft:air', setType(value) { writes++; blocks.set(key(p), value); } };
    },
  };
  const world = {
    getDimension: () => dimension,
    getDynamicProperty: () => prop,
    setDynamicProperty: (_, value) => { if (failSave) throw Error('storage failed'); prop = value; },
  };
  // dx=5, dz=0, repeatedly.
  let n = 0;
  const controller = createController(world, () => (++n % 2 ? 0.7 : 0.5));
  return { controller, dimension, at, blocks, world, get writes() { return writes; },
    set biome(v) { biome = v; }, set ceiling(v) { ceiling = v; },
    set unloaded(v) { unloaded = v; }, set failSave(v) { failSave = v; },
    set prop(v) { prop = v; }, get prop() { return prop; } };
}

const f = fixture();
assert.deepEqual(findBasin(f.dimension, 5, 0, 64), { x: 5, y: 64, z: 0 });
f.controller.tick();
assert.equal(f.writes, 0, 'weather is unknown on load');
f.controller.weatherChanged({ dimension: 'minecraft:nether', newWeather: 'Rain' });
f.controller.tick();
assert.equal(f.writes, 0, 'ignore another dimension');
f.controller.weatherChanged({ dimension: 'minecraft:overworld', newWeather: 'Rain' });
f.controller.tick();
assert.equal(f.blocks.get('5,64,0'), 'minecraft:water');
assert.equal(f.writes, 1);
assert.equal(JSON.parse(f.prop).length, 1);
f.controller.tick();
assert.equal(f.writes, 1, 'do not replace existing water');
f.controller.weatherChanged({ dimension: 'minecraft:overworld', newWeather: 'Clear' });
f.controller.tick();
assert.equal(f.blocks.get('5,64,0'), 'minecraft:water', 'never remove anyone’s water');

for (const variant of ['biome', 'ceiling', 'wall', 'occupied', 'unloaded', 'storage', 'corrupt', 'limit']) {
  const t = fixture();
  if (variant === 'biome') t.biome = 'minecraft:desert';
  if (variant === 'ceiling') t.ceiling = true;
  if (variant === 'wall') t.at(6, 64, 0, 'minecraft:air');
  if (variant === 'occupied') t.at(5, 64, 0, 'minecraft:chest');
  if (variant === 'unloaded') t.unloaded = true;
  if (variant === 'storage') t.failSave = true;
  if (variant === 'corrupt') t.prop = '{';
  if (variant === 'limit') {
    t.prop = JSON.stringify(Array.from({ length: MAX_SOURCES }, (_, x) => ({ x: x + 100, y: 64, z: 0 })));
    for (let x = 100; x < 100 + MAX_SOURCES; x++) t.at(x, 64, 0, 'minecraft:water');
  }
  t.controller.weatherChanged({ dimension: 'overworld', newWeather: 'Thunder' });
  t.controller.tick();
  assert.equal(t.writes, 0, variant);
}
const unloaded = fixture();
unloaded.prop = JSON.stringify([{ x: 100, y: 64, z: 0 }]);
unloaded.unloaded = true;
unloaded.controller.weatherChanged({ dimension: 'overworld', newWeather: 'Rain' });
unloaded.controller.tick();
assert.equal(JSON.parse(unloaded.prop).length, 1, 'unloaded records stay reserved');
console.log('Rain-water safety and weather tests passed (mocked engine).');
