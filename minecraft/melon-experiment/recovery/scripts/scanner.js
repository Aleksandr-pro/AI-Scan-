// Work is bounded per interval. The nearest blocks are visited first; a change
// of player block/dimension restarts that player's scan around the new centre.
const R = 7, H = 3;
const PER_PLAYER = 80, GLOBAL_BUDGET = 160;
const offsets = [];
for (let y = -H; y <= H; y++) for (let z = -R; z <= R; z++) for (let x = -R; x <= R; x++) offsets.push({x,y,z});
offsets.sort((a,b) => (a.x*a.x+a.y*a.y+a.z*a.z)-(b.x*b.x+b.y*b.y+b.z*b.z) || a.y-b.y || a.z-b.z || a.x-b.x);

export function createScanner(from, to, resolve, notify, options = {}) {
  const cursors = new Map();
  let start = 0;
  return {
    tick(players) {
      const active = new Set(players.map(p => p.id));
      for (const id of cursors.keys()) if (!active.has(id)) cursors.delete(id);
      if (!players.length) return;
      let budget = GLOBAL_BUDGET;
      for (let n = 0; n < players.length && budget > 0; n++) {
        const p = players[(start+n)%players.length];
        let dim, base, key;
        try {
          dim = p.dimension;
          const loc = p.location;
          base = {x:Math.floor(loc.x),y:Math.floor(loc.y),z:Math.floor(loc.z)};
          key = `${dim.id}:${base.x},${base.y},${base.z}`;
          notify(p,'running');
        } catch (_) { continue; }
        let state = cursors.get(p.id);
        if (!state || state.key !== key) state = {key,cursor:0};
        const count = Math.min(PER_PLAYER,budget);
        for (let i = 0; i < count; i++) {
          const offset = offsets[state.cursor++ % offsets.length];
          const at = {x:base.x+offset.x,y:base.y+offset.y,z:base.z+offset.z};
          let block, id;
          // Unloaded or out-of-world positions are normal at the edge of a scan.
          try { block = dim.getBlock(at); id = block?.typeId; } catch (_) { continue; }
          if (options.reportExisting && id === to) { notify(p,'existing',{at}); continue; }
          if (id !== from) continue;
          try {
            block.setPermutation(resolve(to));
          } catch (error) { notify(p,'error',{at,error}); continue; }
          // A successful API call does not by itself establish what was stored.
          // Read the position again; this still cannot verify client rendering.
          try {
            const actual = dim.getBlock(at)?.typeId;
            if (actual === to) notify(p,'changed',{at});
            else notify(p,'unconfirmed',{at,actual:actual || 'недоступен'});
          } catch (error) { notify(p,'unconfirmed',{at,actual:String(error)}); }
        }
        state.cursor %= offsets.length;
        cursors.set(p.id,state);
        budget -= count;
      }
      start = (start+1)%players.length;
    }
  };
}
