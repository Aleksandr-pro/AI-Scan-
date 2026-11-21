import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

// Load the exact Bedrock module without changing its script packaging.
const source = await readFile(new URL('../living-world-behavior/scripts/ambience.js', import.meta.url), 'utf8');
const { nearWater, environment, pickSound, createDirector } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
let biome = 'minecraft:forest', top = { typeId: 'minecraft:oak_leaves', location: { y: 80 } };
let water = false, reads = 0, obstruction;
const dim = {
  id: 'minecraft:overworld',
  getBiome: () => ({id: biome}),
  getTopmostBlock: () => top,
  getBlockFromRay: () => obstruction,
  getBlock: () => { reads++; return {typeId: water ? 'minecraft:water' : 'minecraft:air'}; },
};
const sounds = [];
const player = {id: 'a', dimension: dim, location: {x: 0, y: 64, z: 0}, isInWater: false,
  playSound: (...args) => sounds.push(args)};
assert.equal(environment(player, 6000).day, true);
assert.equal(environment(player, 18000).day, false);
assert.ok(reads <= 52);
assert.equal(pickSound(environment(player, 6000), () => 0.6), 'livingworld.birds');
assert.equal(pickSound(environment(player, 18000), () => 0.6), 'livingworld.crickets');
assert.equal(pickSound(environment(player, 18000), () => 0.95), 'livingworld.wind');
water = true;
assert.equal(nearWater(dim, player.location), true);
assert.equal(pickSound(environment(player, 6000), () => 0.2), 'livingworld.stream');
biome = 'minecraft:ocean';
assert.equal(pickSound(environment(player, 6000), () => 0.2), 'livingworld.shore');
assert.equal(pickSound(environment(player, 6000), () => 0.9), null);
biome = 'minecraft:desert';
assert.equal(environment(player, 6000), null);
biome = 'minecraft:forest';
player.isInWater = true;
assert.equal(environment(player, 6000), null);
player.isInWater = false;
top = {typeId: 'minecraft:stone', location: {y: 80}};
assert.equal(environment(player, 6000), null);
top = {typeId: 'minecraft:oak_leaves', location: {y: 80}};
obstruction = {block: {typeId: 'minecraft:stone'}};
assert.equal(environment(player, 6000), null); // Cave below a tree canopy.
obstruction = {block: {typeId: 'minecraft:oak_leaves'}};
assert.ok(environment(player, 6000));
obstruction = undefined;
dim.id = 'minecraft:nether';
assert.equal(environment(player, 6000), null);
dim.id = 'minecraft:overworld';
water = false;
const director = createDirector(() => 0.5);
director.tick([player], 0, 6000);
director.tick([player], 399, 6000);
assert.equal(sounds.length, 0);
director.tick([player], 400, 6000);
assert.equal(sounds.length, 1);
assert.equal(sounds[0][0], 'livingworld.birds');
director.tick([player], 999, 6000);
assert.equal(sounds.length, 1);
director.tick([player], 1000, 18000);
assert.equal(sounds[1][0], 'livingworld.crickets');
director.tick([], 1100, 6000); // Disconnect resets the player's deadline.
director.tick([player], 1200, 6000);
assert.equal(sounds.length, 2);
// Missing chunks must be safe and not trigger an immediate retry.
dim.getBiome = () => { throw new Error('unloaded'); };
director.tick([player], 1600, 6000);
dim.getBiome = () => ({id: 'minecraft:forest'});
director.tick([player], 1601, 6000);
assert.equal(sounds.length, 2);
console.log('Dynamic ambience director: all checks passed');
