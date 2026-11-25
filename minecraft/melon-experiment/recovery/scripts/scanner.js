// Deliberately bounded, resumable per-player scan; no loading of chunks or commands.
const R = 7, H = 3;
const SIDE = 2 * R + 1, HEIGHT = 2 * H + 1, TOTAL = SIDE * SIDE * HEIGHT;
const PER_PLAYER = 80, GLOBAL_BUDGET = 160;

export function createScanner(from, to, resolve, notify) {
  const cursors = new Map();
  let start = 0;
  return {
    tick(players) {
      const active = new Set(players.map(p => p.id));
      for (const id of cursors.keys()) if (!active.has(id)) cursors.delete(id);
      if (!players.length) return;
      let budget = GLOBAL_BUDGET;
      for (let n = 0; n < players.length && budget > 0; n++) {
        const p = players[(start + n) % players.length];
        let cursor = cursors.get(p.id) || 0;
        let dim, base;
        try {
          dim = p.dimension;
          const loc = p.location;
          base = {x: Math.floor(loc.x), y: Math.floor(loc.y), z: Math.floor(loc.z)};
          notify(p, 'running');
        } catch (_) { continue; }
        const count = Math.min(PER_PLAYER, budget);
        for (let i = 0; i < count; i++) {
          const index = cursor++ % TOTAL;
          const x = index % SIDE - R;
          const z = Math.floor(index / SIDE) % SIDE - R;
          const y = Math.floor(index / (SIDE * SIDE)) - H;
          try {
            const block = dim.getBlock({x:base.x+x,y:base.y+y,z:base.z+z});
            if (block && block.typeId === from) {
              block.setPermutation(resolve(to));
              notify(p, 'changed');
            }
          } catch (e) { notify(p, 'error', e); }
        }
        cursors.set(p.id, cursor % TOTAL);
        budget -= count;
      }
      start = (start + 1) % players.length;
    }
  };
}
