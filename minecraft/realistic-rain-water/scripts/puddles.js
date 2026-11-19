// Deliberately conservative: actual source blocks, not a fluid solver.
// We never remove water: a vanilla block has no reliable ownership marker.
export const PROPERTY = 'rainwater:placed_sources_v1';
export const MAX_SOURCES = 16;
export const MAX_ATTEMPTS = 24;
const RADIUS = 12;
const MIN_DISTANCE = 5;
const WALLS = new Set([
  'minecraft:stone', 'minecraft:dirt', 'minecraft:grass_block',
  'minecraft:coarse_dirt', 'minecraft:podzol', 'minecraft:gravel',
  'minecraft:sand', 'minecraft:clay', 'minecraft:andesite',
  'minecraft:diorite', 'minecraft:granite', 'minecraft:tuff',
  'minecraft:deepslate', 'minecraft:moss_block',
]);
const BIOMES = new Set(['minecraft:plains', 'minecraft:forest', 'minecraft:birch_forest']);
const OFFSETS = [[1, 0], [-1, 0], [0, 1], [0, -1]];

function water(block) {
  return block.typeId === 'minecraft:water' || block.typeId === 'minecraft:flowing_water';
}

function loadRecords(world) {
  const value = world.getDynamicProperty(PROPERTY);
  if (value === undefined) return [];
  if (typeof value !== 'string') throw new Error('Invalid water registry; refusing to place water');
  const records = JSON.parse(value);
  if (!Array.isArray(records) || records.length > MAX_SOURCES || !records.every(p =>
    p && Number.isInteger(p.x) && Number.isInteger(p.y) && Number.isInteger(p.z) &&
    Math.abs(p.x) <= 30000000 && Math.abs(p.z) <= 30000000 && p.y >= -2048 && p.y <= 2048)) {
    throw new Error('Invalid water registry; refusing to place water');
  }
  return records;
}

function saveRecords(world, records) {
  world.setDynamicProperty(PROPERTY, JSON.stringify(records));
}

// Only forget a recorded location when a loaded chunk proves it is no longer
// water. Never alter it. Unloaded/failed reads remain conservatively counted.
function pruneRecords(dimension, records) {
  return records.filter(p => {
    try {
      const block = dimension.getBlock(p);
      return !block || water(block);
    } catch (_) {
      return true;
    }
  });
}

export function findBasin(dimension, x, z, playerY) {
  try {
    const floor = dimension.getTopmostBlock({ x, z });
    if (!floor || !WALLS.has(floor.typeId)) return undefined;
    const y = floor.location.y + 1;
    // Avoid placing far above or below the player's current terrain; snow at
    // high elevations is intentionally excluded too.
    if (Math.abs(y - playerY) > 6 || y > 100) return undefined;
    const location = { x, y, z };
    if (!BIOMES.has(dimension.getBiome(location).id)) return undefined;
    const target = dimension.getBlock(location);
    if (!target || !target.isAir) return undefined;
    // Four full natural blocks hold the vanilla source on every horizontal
    // side. No plants, containers, structures or existing water are replaced.
    for (const [dx, dz] of OFFSETS) {
      const wall = dimension.getBlock({ x: x + dx, y, z: z + dz });
      if (!wall || !WALLS.has(wall.typeId)) return undefined;
    }
    return location;
  } catch (_) {
    return undefined; // Unloaded chunks and world-height errors fail closed.
  }
}

export function createController(world, random = Math.random) {
  // Stable API 2.8 has weather-change events but no current-weather query.
  // On every load, wait for a fresh observed event rather than guess.
  let raining = false;
  let playerIndex = 0;

  function weatherChanged(event) {
    if (event.dimension !== 'minecraft:overworld' && event.dimension !== 'overworld') return;
    raining = event.newWeather === 'Rain' || event.newWeather === 'Thunder';
  }

  function tick() {
    if (!raining) return;
    try {
      const dimension = world.getDimension('overworld');
      const players = dimension.getPlayers();
      if (!players.length) return;
      const records = loadRecords(world);
      const kept = pruneRecords(dimension, records);
      if (kept.length !== records.length) saveRecords(world, kept);
      if (kept.length >= MAX_SOURCES) return;
      const player = players[playerIndex++ % players.length];
      const pos = player.location;
      for (let i = 0; i < MAX_ATTEMPTS; i++) {
        const dx = Math.floor(random() * (2 * RADIUS + 1)) - RADIUS;
        const dz = Math.floor(random() * (2 * RADIUS + 1)) - RADIUS;
        const dist2 = dx * dx + dz * dz;
        if (dist2 < MIN_DISTANCE ** 2 || dist2 > RADIUS ** 2) continue;
        const x = Math.floor(pos.x) + dx;
        const z = Math.floor(pos.z) + dz;
        const location = findBasin(dimension, x, z, pos.y);
        if (!location || kept.some(p => p.x === x && p.y === location.y && p.z === z)) continue;
        // Persist the reservation first. If it fails, do not modify the world.
        // If placing then fails, it will be forgotten when observed non-water.
        saveRecords(world, [...kept, location]);
        dimension.getBlock(location).setType('minecraft:water');
        return; // At most one new source per tick invocation across all players.
      }
    } catch (error) {
      console.warn(`[RainWater] No water placed: ${error}`);
    }
  }
  return { weatherChanged, tick };
}
