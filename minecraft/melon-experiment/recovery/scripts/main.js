import {BlockPermutation, system, world} from '@minecraft/server';
import {createScanner} from './scanner.js';

const seen = new Map();
function notice(player, type, detail = {}) {
  try {
    let kinds = seen.get(player.id);
    if (!kinds) { kinds = new Set(); seen.set(player.id, kinds); }
    if (kinds.has(type)) return;
    kinds.add(type);
    const pos = detail.at ? `${detail.at.x}, ${detail.at.y}, ${detail.at.z}` : '';
    const safe = value => String(value).replace(/[\r\n]/g,' ').slice(0,120);
    if (type === 'running') player.sendMessage('§e[3D арбуз: возврат 1.0.1] Восстановление активно. Обойдите все места замены.');
    if (type === 'changed') player.sendMessage(`§e[3D арбуз: возврат 1.0.1] Игра сообщает обычный арбуз: ${pos}. Остальные места проверьте отдельно.`);
    if (type === 'unconfirmed') player.sendMessage(`§c[3D арбуз: возврат 1.0.1] Возврат ${pos} не подтверждён: ${safe(detail.actual)}.`);
    if (type === 'error') {
      const error = safe(detail.error);
      console.warn('[3D melon recovery 1.0.1] Restore failed: '+error);
      player.sendMessage(`§c[3D арбуз: возврат 1.0.1] Ошибка возврата ${pos}: ${error}`);
    }
  } catch (error) { console.warn('[3D melon recovery] Notice failed: '+String(error)); }
}
const scanner = createScanner('aimelon:fruit','minecraft:melon_block',id => BlockPermutation.resolve(id),notice);
system.runInterval(() => scanner.tick(world.getAllPlayers()),10);
