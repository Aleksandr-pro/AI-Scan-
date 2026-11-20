// Limited experiment: swaps selected full vanilla blocks, never edits water.
export const REGISTRY = 'rainwet:registry_v1';
export const PAUSED = 'rainwet:paused_v1';
export const LIMIT = 64;
export const MAX_SCAN = 20;
export const MAX_WET_PER_TICK = 2;
export const MAX_RESTORE_PER_TICK = 4;
const MAP = { 'minecraft:dirt': 'rainwet:dirt', 'minecraft:grass_block': 'rainwet:grass', 'minecraft:stone': 'rainwet:stone' };
const BIOMES = new Set(['minecraft:plains', 'minecraft:forest', 'minecraft:birch_forest']);
const hasType = id => Object.prototype.hasOwnProperty.call(MAP, id);

function validState(states) {
  return states && typeof states === 'object' && !Array.isArray(states) &&
    Object.keys(states).length <= 16 && Object.entries(states).every(([key, value]) =>
      key.length <= 100 && ['string', 'boolean', 'number'].includes(typeof value) &&
      (typeof value !== 'number' || Number.isFinite(value)) &&
      (typeof value !== 'string' || value.length <= 100));
}
function load(world) {
  const raw = world.getDynamicProperty(REGISTRY);
  if (raw === undefined) return [];
  if (typeof raw !== 'string') throw Error('Invalid registry');
  const list = JSON.parse(raw);
  const seen = new Set();
  if (!Array.isArray(list) || list.length > LIMIT || !list.every(r => {
    if (!r || !Number.isInteger(r.x) || !Number.isInteger(r.y) || !Number.isInteger(r.z) ||
        Math.abs(r.x) > 30000000 || Math.abs(r.z) > 30000000 || r.y < -2048 || r.y > 2048 ||
        !hasType(r.original) || r.wet !== MAP[r.original] || !validState(r.states)) return false;
    const key = `${r.x},${r.y},${r.z}`;
    if (seen.has(key)) return false;
    seen.add(key); return true;
  })) throw Error('Invalid registry');
  return list;
}
function save(world, records) { world.setDynamicProperty(REGISTRY, JSON.stringify(records)); }

export function findSurface(dim, x, z, playerY) {
  try {
    const block = dim.getTopmostBlock({ x, z });
    if (!block || !hasType(block.typeId) || block.isWaterlogged) return undefined;
    const y = block.location.y;
    if (Math.abs(y - playerY) > 6 || y > 100) return undefined;
    const above = dim.getBlock({ x, y: y + 1, z });
    if (!above || !above.isAir || !BIOMES.has(dim.getBiome({ x, y, z }).id)) return undefined;
    const states = block.permutation.getAllStates();
    if (!validState(states)) return undefined;
    return { x, y, z, original: block.typeId, wet: MAP[block.typeId], states };
  } catch (_) { return undefined; }
}

export function createController(world, resolve, random = Math.random) {
  let raining = false; // Unknown after load: restore rather than assume rain.
  let playerIndex = 0;
  let restoreCursor = 0;
  function weatherChanged(event) {
    if (event.dimension !== 'minecraft:overworld' && event.dimension !== 'overworld') return;
    raining = event.newWeather === 'Rain' || event.newWeather === 'Thunder';
  }
  function pause() { world.setDynamicProperty(PAUSED, true); }
  function resume() { world.setDynamicProperty(PAUSED, false); }
  function status() { return { paused: world.getDynamicProperty(PAUSED) === true, raining, remaining: load(world).length }; }

  function restore(dim, records) {
    if (!records.length) return;
    const start = restoreCursor % records.length;
    const selected = new Set();
    for (let n = 0; n < Math.min(MAX_RESTORE_PER_TICK, records.length); n++) {
      selected.add((start + n) % records.length);
    }
    restoreCursor = (start + selected.size) % records.length;
    const kept = [];
    records.forEach((record, index) => {
      if (!selected.has(index)) { kept.push(record); return; }
      try {
        const block = dim.getBlock(record);
        if (!block) { kept.push(record); return; }
        // Don't overwrite a replacement placed by the player or a broken block.
        if (block.typeId !== record.wet) return;
        block.setPermutation(resolve(record.original, record.states));
      } catch (_) { kept.push(record); }
    });
    if (kept.length !== records.length) save(world, kept);
  }

  function tick() {
    try {
      const records = load(world);
      const dim = world.getDimension('overworld');
      if (!raining || world.getDynamicProperty(PAUSED) === true) { restore(dim, records); return; }
      const players = dim.getPlayers();
      if (!players.length || records.length >= LIMIT) return;
      const pos = players[playerIndex++ % players.length].location;
      let made = 0;
      for (let i = 0; i < MAX_SCAN && made < MAX_WET_PER_TICK && records.length < LIMIT; i++) {
        const dx = Math.floor(random() * 21) - 10, dz = Math.floor(random() * 21) - 10;
        if (dx * dx + dz * dz > 100) continue;
        const x = Math.floor(pos.x) + dx, z = Math.floor(pos.z) + dz;
        const record = findSurface(dim, x, z, pos.y);
        if (!record || records.some(r => r.x === x && r.y === record.y && r.z === z)) continue;
        // Write the original permutation before changing anything. A failed
        // write must leave the block untouched; a failed swap keeps a record.
        save(world, [...records, record]);
        records.push(record);
        const block = dim.getBlock(record);
        if (!block || block.typeId !== record.original) continue;
        block.setType(record.wet);
        made++;
      }
    } catch (error) { console.warn(`[RainWet] Changes paused: ${error}`); }
  }
  return { weatherChanged, tick, pause, resume, status };
}
