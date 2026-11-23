import { states } from './field.js';

// This system replaces real world blocks. Journal first, restore only our own
// block ID; fail closed on corrupt/unavailable journal, unloaded chunks, or errors.
export const JOURNAL = 'grassflow:auto_journal_v1';
export const CONTROL = 'grassflow_auto';
export const CUSTOM = 'grassflow:auto_terrain';
export const LIMIT = 256;
const RADIUS = 8, RETAIN = 12, SCANS = 40, MUTATIONS = 4, RESTORE = 12;
const OFFSETS = [];
for (let z = -RADIUS; z <= RADIUS; z++) for (let x = -RADIUS; x <= RADIUS; x++)
  if (x*x + z*z <= RADIUS*RADIUS) OFFSETS.push([x,z]);
OFFSETS.sort((a,b) => a[0]*a[0] + a[1]*a[1] - b[0]*b[0] - b[1]*b[1]);

function validStates(s) {
  return !!s && typeof s === 'object' && !Array.isArray(s) && Object.keys(s).length <= 8 &&
    Object.entries(s).every(([k,v]) => k.length <= 80 && /^[\x20-\x7E]*$/.test(k) &&
      (typeof v === 'boolean' || (typeof v === 'number' && Number.isFinite(v)) ||
       (typeof v === 'string' && v.length <= 80 && /^[\x20-\x7E]*$/.test(v))));
}
export function load(world) {
  const raw = world.getDynamicProperty(JOURNAL);
  if (raw === undefined) return [];
  if (typeof raw !== 'string' || raw.length > 31000) throw Error('invalid journal');
  const records = JSON.parse(raw), seen = new Set();
  if (!Array.isArray(records) || records.length > LIMIT) throw Error('invalid journal size');
  for (const r of records) {
    if (!r || !Number.isInteger(r.x) || !Number.isInteger(r.y) || !Number.isInteger(r.z) ||
        Math.abs(r.x) > 30000000 || Math.abs(r.z) > 30000000 || Math.abs(r.y) > 2048 || !validStates(r.s)) throw Error('invalid journal entry');
    const key = `${r.x},${r.y},${r.z}`;
    if (seen.has(key)) throw Error('duplicate journal entry');
    seen.add(key);
  }
  return records;
}
function save(world, records) {
  const raw = JSON.stringify(records);
  if (records.length > LIMIT || raw.length > 31000) throw Error('journal capacity exceeded');
  try { world.setDynamicProperty(JOURNAL, raw); }
  catch (e) { throw Error(`journal write failed: ${e}`); }
}
function closeToPlayers(record, players) {
  return players.some(p => {
    const pos = p.location;
    return Math.abs(pos.y - record.y) <= 12 && Math.abs(pos.x-record.x) <= RETAIN && Math.abs(pos.z-record.z) <= RETAIN;
  });
}
function available(block) { return !!block && block.typeId === 'minecraft:air' && !block.isWaterlogged; }

export function createController(world, resolve) {
  let restorationCursor = 0, playerIndex = 0;
  const cursors = new Map(), cache = new Map();
  function isRecovering() {
    const board = world.scoreboard.getObjective(CONTROL);
    if (!board) throw Error('control scoreboard missing');
    return board.getScore('pause') === 1;
  }
  function restore(dim, records, players, restoring) {
    if (!records.length) return records;
    const start = restorationCursor % records.length;
    const targets = new Set();
    for (let i = 0; i < Math.min(RESTORE, records.length); i++) targets.add((start + i) % records.length);
    restorationCursor = (start + targets.size) % records.length;
    const kept = [];
    for (let i = 0; i < records.length; i++) {
      const r = records[i];
      if (!targets.has(i)) { kept.push(r); continue; }
      try {
        const block = dim.getBlock(r);
        if (!block) { kept.push(r); continue; }
        // Player/game changed or removed it: forget it without overwriting.
        if (block.typeId !== CUSTOM) continue;
        const above = dim.getBlock({x:r.x, y:r.y+1, z:r.z});
        if (!above || block.isWaterlogged) { kept.push(r); continue; }
        if (restoring || !closeToPlayers(r, players) || !available(above)) {
          block.setPermutation(resolve('minecraft:grass_block', r.s));
          continue;
        }
      } catch (_) { /* Unloaded, out of bounds, or write failed: retain record. */ }
      kept.push(r);
    }
    // If this write fails, the old journal survives; a restored block is
    // detected as no longer custom on the next pass. Never lose records first.
    if (kept.length !== records.length) save(world, kept);
    return kept;
  }
  function tick(now) {
    try {
      const board = world.scoreboard.getObjective(CONTROL);
      if (!board) throw Error('control scoreboard missing');
      board.setScore('status_session', 0);
      let records = load(world);
      const dim = world.getDimension('overworld');
      const players = dim.getPlayers();
      const ids = new Set(players.map(p => p.id));
      for (const id of cursors.keys()) if (!ids.has(id)) cursors.delete(id);
      const recovering = isRecovering(now);
      records = restore(dim, records, players, recovering);
      if (recovering || !players.length || records.length >= LIMIT) {
        board.setScore('count', records.length);
        board.setScore('status_session', board.getScore('session'));
        return;
      }
      const player = players[playerIndex++ % players.length], p = player.location;
      const cx = Math.floor(p.x), cz = Math.floor(p.z);
      const center = `${cx},${cz}`;
      let scan = cursors.get(player.id);
      if (!scan || scan.center !== center) { scan = {center, cursor: 0}; cursors.set(player.id, scan); }
      let made = 0;
      for (let n = 0; n < SCANS && made < MUTATIONS && records.length < LIMIT; n++) {
        const [dx,dz] = OFFSETS[scan.cursor++ % OFFSETS.length];
        const x = cx + dx, z = cz + dz;
        try {
          const block = dim.getTopmostBlock({x,z});
          if (!block || block.typeId !== 'minecraft:grass_block' || block.isWaterlogged) continue;
          const y = block.location.y;
          if (Math.abs(y - p.y) > 6 || !available(dim.getBlock({x,y:y+1,z}))) continue;
          if (records.some(r => r.x === x && r.y === y && r.z === z)) continue;
          const r = {x,y,z,s:block.permutation.getAllStates()};
          if (!validStates(r.s)) continue;
          const props = states(x,z), key = Object.values(props).join('');
          if (!cache.has(key)) cache.set(key, resolve(CUSTOM, props));
          // Persist the complete original state BEFORE replacing the block.
          save(world, [...records, r]);
          records.push(r);
          if (block.typeId !== 'minecraft:grass_block') continue;
          block.setPermutation(cache.get(key));
          made++;
        } catch (error) {
          // Failed reads leave the candidate untouched; a failed post-journal
          // swap stays journaled and will be reconciled later. Journal errors
          // escape so no further candidates can be modified in this tick.
          if (String(error).includes('journal') || String(error).includes('property')) throw error;
        }
      }
      board.setScore('count', records.length);
      board.setScore('status_session', board.getScore('session'));
    } catch (error) { console.warn(`[GrassFlow] Paused safely: ${error}`); }
  }
  return {tick};
}
