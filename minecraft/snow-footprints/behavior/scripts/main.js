import {system, world, MolangVariableMap} from '@minecraft/server';
import {createFootprints} from './footsteps.js';

// Tiny, local-only diagnostic: at most one message per event per player per
// session. A spawn request does NOT prove the client's renderer drew it.
const notices = new Map();
function notify(player, kind, detail) {
  try {
    let seen = notices.get(player.id);
    if (!seen) { seen = new Set(); notices.set(player.id, seen); }
    if (seen.has(kind)) return;
    seen.add(kind);
    if (kind === 'loaded')
      player.sendMessage('§7[Следы 1.2] Скрипт запущен. Пройдитесь по снегу.');
    else if (kind === 'emitted')
      player.sendMessage('§7[Следы 1.2] Снег найден, след запрошен. Если его не видно, проверьте ресурсы и настройки частиц.');
    else if (kind === 'error') {
      const safe = String(detail).replace(/[\r\n]/g, ' ').slice(0, 160);
      console.warn('[Snow footprints] ' + safe);
      player.sendMessage('§c[Следы 1.2] Ошибка скрипта: ' + safe);
    }
  } catch (error) {
    console.warn('[Snow footprints] Diagnostic message failed: ' + String(error));
  }
}

const prints = createFootprints((dimension, at, angle) => {
  const variables = new MolangVariableMap();
  variables.setFloat('variable.aegis_angle', angle);
  dimension.spawnParticle('aegis:snow_footprint', at, variables);
}, notify);

// One sample every 2 ticks. No changes to blocks, entities, or world properties.
system.runInterval(() => {
  const players = world.getAllPlayers();
  const ids = new Set();
  for (const player of players) { ids.add(player.id); notify(player, 'loaded'); }
  for (const id of notices.keys()) if (!ids.has(id)) notices.delete(id);
  prints.tick(players, system.currentTick);
}, 2);
