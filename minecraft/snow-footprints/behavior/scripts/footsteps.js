// Visual-only snow footprints. No blocks, player inventory or world properties are modified.
export const STEP_DISTANCE = 0.82;
// The rendered plane is 0.34 × 0.52: 0.64 exceeds its diagonal, so
// equal-height footprints cannot geometrically intersect at any angle.
export const MIN_PRINT_DISTANCE = 0.64;
export const LIFE_TICKS = 1200;
export const MAX_TOTAL = 720;
export const MAX_PER_PLAYER = 360;
const MAX_JUMP = 1.5; // horizontal distance per sample: reject teleportation
const HEIGHT_TOLERANCE = 0.20;
const MARGIN_Y = 0.025; // reduce surface z-fighting; still not a physical dent

// The snow surface at one XZ sample, close to the player's feet.
export function snowSurface(dimension, x, footY, z) {
  const bx = Math.floor(x), bz = Math.floor(z), y = Math.floor(footY);
  for (const by of [y, y - 1, y - 2]) {
    const block = dimension.getBlock({x: bx, y: by, z: bz});
    if (!block) continue;
    if (block.typeId === 'minecraft:snow') {
      const top = by + 1;
      if (Math.abs(top - footY) <= HEIGHT_TOLERANCE) return top;
    } else if (block.typeId === 'minecraft:snow_layer') {
      const height = block.permutation.getState('height');
      if (!Number.isInteger(height) || height < 0 || height > 7) continue;
      const top = by + (height + 1) / 8;
      // Some layer states have reduced or no collision. The player may stand
      // on the support at layer base rather than at the visual snow surface.
      if (footY >= by - 0.075 && footY <= top + HEIGHT_TOLERANCE) return top;
    }
  }
  return undefined;
}

// Require the center and at least two corners on the same snow surface.
// This is less aggressive on natural, uneven snow; borders can still overhang.
export function printPosition(dimension, center, dx, dz, side) {
  const rightX = dz, rightZ = -dx;
  const x = center.x + rightX * side * 0.17;
  const z = center.z + rightZ * side * 0.17;
  const y = snowSurface(dimension, x, center.y, z);
  if (y === undefined) return undefined;
  let matching = 0;
  for (const [along, across] of [[0.25,0.16],[0.25,-0.16],[-0.25,0.16],[-0.25,-0.16]]) {
    const sx = x + dx * along + rightX * across;
    const sz = z + dz * along + rightZ * across;
    const other = snowSurface(dimension, sx, center.y, sz);
    if (other !== undefined && Math.abs(other - y) <= 0.01) matching++;
  }
  if (matching < 2) return undefined;
  return {x, y: y + MARGIN_Y, z};
}

export function createFootprints(spawn, report = () => {}) {
  const players = new Map();
  function signal(player, type, detail) {
    try { report(player, type, detail); } catch (_) { /* diagnostics must not stop effects */ }
  }
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
        const eligible = !player.isInWater && !player.isSwimming && !player.isGliding &&
          !player.isFlying && !player.isSleeping && !player.getComponent('minecraft:riding');
        if (!eligible) { players.delete(player.id); continue; }
        if (!previous || previous.dimension !== dim.id) {
          players.set(player.id, {pos: {...p}, dimension: dim.id, carry: 0, side: -1});
          continue;
        }
        // isOnGround is documented to be unreliable in some situations. Only
        // allow a fallback when feet are near snow, height is stable, and no
        // jump/fall is reported. This remains an approximation, not animation.
        if (!player.isOnGround) {
          const stable = !player.isJumping && !player.isFalling &&
            Math.abs(p.y - previous.pos.y) < 0.025 && snowSurface(dim, p.x, p.y, p.z) !== undefined;
          if (!stable) {
            previous.pos = {...p}; previous.carry = 0;
            continue;
          }
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
          const overlaps = at && active.some(entry => entry.dimension === dim.id &&
            Math.abs(entry.y - at.y) < 0.12 &&
            Math.hypot(entry.x - at.x, entry.z - at.z) < MIN_PRINT_DISTANCE);
          if (at && !overlaps && active.length < MAX_TOTAL && active.filter(e => e.player === player.id).length < MAX_PER_PLAYER) {
            const angle = Math.atan2(dx, dz) * 180 / Math.PI;
            spawn(dim, at, angle);
            signal(player, 'emitted'); // API accepted request; rendering is client-side.
            active.push({player: player.id, expires: now + LIFE_TICKS,
              dimension: dim.id, x: at.x, y: at.y, z: at.z});
            previous.side *= -1;
          }
          distance += STEP_DISTANCE;
        }
        previous.carry = (previous.carry + length) % STEP_DISTANCE;
        previous.pos = {...p};
      } catch (error) {
        // Surface/runtime failures must not be silently swallowed. Report is
        // rate-limited in main.js, then retry from a fresh sample next tick.
        signal(player, 'error', String(error));
        players.delete(player.id);
      }
    }
    for (const id of players.keys()) if (!current.has(id)) players.delete(id);
  }
  return {tick};
}
