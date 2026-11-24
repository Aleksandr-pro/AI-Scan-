// Visual-only snow footprints. No blocks, player inventory or world properties are modified.
export const STEP_DISTANCE = 0.75;
export const LIFE_TICKS = 1200;
export const MAX_TOTAL = 720;
export const MAX_PER_PLAYER = 360;
const MAX_JUMP = 1.5; // horizontal distance per sample: reject teleportation
const HEIGHT_TOLERANCE = 0.20; // snow layer collision and visual surface can differ
const MARGIN_Y = 0.015;

// The snow surface at one XZ sample, close to the player's feet.
export function snowSurface(dimension, x, footY, z) {
  const bx = Math.floor(x), bz = Math.floor(z), y = Math.floor(footY);
  for (const by of [y, y - 1, y - 2]) {
    const block = dimension.getBlock({x: bx, y: by, z: bz});
    if (!block) continue;
    let top;
    if (block.typeId === 'minecraft:snow') top = by + 1;
    else if (block.typeId === 'minecraft:snow_layer') {
      const height = block.permutation.getState('height');
      if (!Number.isInteger(height) || height < 0 || height > 7) continue;
      top = by + (height + 1) / 8;
    } else continue;
    if (Math.abs(top - footY) <= HEIGHT_TOLERANCE) return top;
  }
  return undefined;
}

// Suppress a footprint if its bounding rectangle would bridge a ledge or two
// different heights. Some legitimate prints near borders will be skipped.
export function printPosition(dimension, center, dx, dz, side) {
  const rightX = dz, rightZ = -dx;
  const x = center.x + rightX * side * 0.15;
  const z = center.z + rightZ * side * 0.15;
  const y = snowSurface(dimension, x, center.y, z);
  if (y === undefined) return undefined;
  for (const [along, across] of [[0.25,0.13],[0.25,-0.13],[-0.25,0.13],[-0.25,-0.13]]) {
    const sx = x + dx * along + rightX * across;
    const sz = z + dz * along + rightZ * across;
    const other = snowSurface(dimension, sx, center.y, sz);
    if (other === undefined || Math.abs(other - y) > 0.01) return undefined;
  }
  return {x, y: y + MARGIN_Y, z};
}

export function createFootprints(spawn) {
  const players = new Map();
  let active = [];
  function tick(list, now) {
    active = active.filter(entry => entry.expires > now);
    const current = new Set();
    for (const player of list) {
      try {
        current.add(player.id);
        const p = player.location;
        const dim = player.dimension;
        const previous = players.get(player.id);
        const eligible = player.isOnGround && !player.isInWater && !player.isSwimming &&
          !player.isGliding && !player.isFlying && !player.isSleeping &&
          !player.getComponent('minecraft:riding');
        if (!eligible) { players.delete(player.id); continue; }
        if (!previous || previous.dimension !== dim.id) {
          players.set(player.id, {pos: {...p}, dimension: dim.id, carry: 0, side: -1});
          continue;
        }
        const vx = p.x - previous.pos.x, vz = p.z - previous.pos.z;
        const length = Math.hypot(vx, vz);
        if (length > MAX_JUMP || Math.abs(p.y - previous.pos.y) > 0.7) {
          players.set(player.id, {pos: {...p}, dimension: dim.id, carry: 0, side: -1});
          continue;
        }
        if (length < 0.002) { previous.pos = {...p}; continue; }
        const dx = vx / length, dz = vz / length;
        let distance = STEP_DISTANCE - previous.carry;
        while (distance <= length) {
          const ratio = distance / length;
          const center = {x: previous.pos.x + vx * ratio, y: previous.pos.y + (p.y - previous.pos.y) * ratio,
            z: previous.pos.z + vz * ratio};
          const at = printPosition(dim, center, dx, dz, previous.side);
          if (at && active.length < MAX_TOTAL && active.filter(e => e.player === player.id).length < MAX_PER_PLAYER) {
            const angle = Math.atan2(dx, dz) * 180 / Math.PI;
            spawn(dim, at, angle);
            active.push({player: player.id, expires: now + LIFE_TICKS});
            previous.side *= -1;
          }
          distance += STEP_DISTANCE;
        }
        previous.carry = (previous.carry + length) % STEP_DISTANCE;
        previous.pos = {...p};
      } catch (_) {
        // Unloaded chunks / invalid entity / failed particle: retry from a fresh sample.
        players.delete(player.id);
      }
    }
    for (const id of players.keys()) if (!current.has(id)) players.delete(id);
  }
  return {tick};
}
