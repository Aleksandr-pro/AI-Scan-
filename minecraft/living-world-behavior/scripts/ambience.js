// Read-only ambient director. One check per listener every 10s; never edits the world.
const LAND = new Set([
  'plains', 'sunflower_plains', 'forest', 'flower_forest', 'birch_forest',
  'birch_forest_hills', 'birch_forest_mutated', 'birch_forest_hills_mutated',
  'forest_hills', 'roofed_forest', 'roofed_forest_mutated', 'taiga', 'taiga_hills',
  'taiga_mutated', 'mega_taiga', 'mega_taiga_hills', 'meadow', 'cherry_grove',
  'jungle', 'jungle_hills', 'jungle_mutated', 'sparse_jungle', 'bamboo_jungle',
  'swampland', 'swampland_mutated', 'mangrove_swamp', 'river', 'beach',
]);
const WATER_BIOMES = new Set(['ocean', 'deep_ocean', 'cold_ocean', 'deep_cold_ocean',
  'lukewarm_ocean', 'deep_lukewarm_ocean', 'warm_ocean', 'frozen_ocean',
  'deep_frozen_ocean', 'river', 'beach', 'stone_beach']);
const OFFSETS = [[0,0], [2,0], [-2,0], [0,2], [0,-2], [4,0], [-4,0], [0,4], [0,-4],
  [3,3], [-3,3], [3,-3], [-3,-3]];

export function nearWater(dimension, location) {
  const x = Math.floor(location.x), y = Math.floor(location.y), z = Math.floor(location.z);
  let found = 0;
  // Bounded scan, only at player height and immediately below; requires two samples.
  for (const [dx, dz] of OFFSETS) {
    for (const dy of [-1, 0]) {
      const block = dimension.getBlock({ x: x + dx, y: y + dy, z: z + dz });
      if (block && (block.typeId === 'minecraft:water' || block.typeId === 'minecraft:flowing_water')) {
        if (++found >= 2) return true;
      }
    }
  }
  return false;
}

export function environment(player, time) {
  const dim = player.dimension;
  if (dim.id !== 'minecraft:overworld' || player.isInWater) return null;
  const pos = player.location;
  const biome = dim.getBiome(pos).id.replace(/^minecraft:/, '');
  if (!LAND.has(biome) && !WATER_BIOMES.has(biome)) return null;
  const top = dim.getTopmostBlock({x: Math.floor(pos.x), z: Math.floor(pos.z)});
  if (!top) return null;
  // Reject roofs and cave ceilings even if a tree canopy is the topmost block.
  // A leafy first hit is allowed, so this remains an approximation in dense foliage.
  if (top.location.y > Math.floor(pos.y + 1) && !top.typeId.includes('leaves')) return null;
  const obstruction = dim.getBlockFromRay(
    {x: pos.x, y: pos.y + 1.6, z: pos.z}, {x: 0, y: 1, z: 0},
    {maxDistance: 128, includeLiquidBlocks: true});
  if (obstruction && !obstruction.block.typeId.includes('leaves')) return null;
  const near = nearWater(dim, pos);
  const day = time < 12500 || time >= 23500;
  return { biome, near, day, land: LAND.has(biome), shore: WATER_BIOMES.has(biome) && biome !== 'river' };
}

export function pickSound(env, random) {
  if (!env) return null;
  // At most one short recording at a time, leaving room for Minecraft's own sounds.
  const roll = random();
  if (env.near && roll < 0.38) return env.shore ? 'livingworld.shore' : 'livingworld.stream';
  if (!env.land) return null;
  if (roll < 0.82) return env.day ? 'livingworld.birds' : 'livingworld.crickets';
  return 'livingworld.wind';
}

export function createDirector(random = Math.random) {
  const next = new Map();
  return {
    tick(players, now, time) {
      const active = new Set(players.map(p => p.id));
      for (const id of next.keys()) if (!active.has(id)) next.delete(id);
      for (const player of players) {
        if (!next.has(player.id)) {
          next.set(player.id, now + 200 + Math.floor(random() * 400));
          continue;
        }
        if (now < next.get(player.id)) continue;
        // Schedule before reading chunks: errors never result in a tight retry loop.
        next.set(player.id, now + 400 + Math.floor(random() * 401));
        try {
          const sound = pickSound(environment(player, time), random);
          if (sound) player.playSound(sound, {volume: 0.55, pitch: 1});
        } catch (_) {
          // A player can move into an unloaded chunk or leave during this tick.
        }
      }
    },
  };
}
