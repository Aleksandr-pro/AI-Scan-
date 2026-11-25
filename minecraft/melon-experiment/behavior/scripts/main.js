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
    if (type === 'running') player.sendMessage('§e[3D арбуз 1.0.1] Скрипт запущен. Проверка ближайших блоков; только копия мира.');
    if (type === 'existing') player.sendMessage(`§e[3D арбуз 1.0.1] Найден ранее заменённый блок aimelon:fruit: ${pos}. Это не проверка отрисовки.`);
    if (type === 'changed') player.sendMessage(`§e[3D арбуз 1.0.1] После замены игра сообщает aimelon:fruit: ${pos}. Вид модели нужно проверить глазами.`);
    if (type === 'unconfirmed') player.sendMessage(`§c[3D арбуз 1.0.1] Замена ${pos} не подтверждена: ${safe(detail.actual)}.`);
    if (type === 'error') {
      const error = safe(detail.error);
      console.warn('[3D melon 1.0.1] Replacement failed: '+error);
      player.sendMessage(`§c[3D арбуз 1.0.1] Ошибка замены ${pos}: ${error}`);
    }
  } catch (error) { console.warn('[3D melon] Notice failed: '+String(error)); }
}
const scanner = createScanner('minecraft:melon_block','aimelon:fruit',id => BlockPermutation.resolve(id),notice,{reportExisting:true});
system.runInterval(() => scanner.tick(world.getAllPlayers()),10);
