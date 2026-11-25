import {BlockPermutation, system, world} from '@minecraft/server';
import {createScanner} from './scanner.js';

const seen = new Map();
function notice(player, type, error) {
  try {
    let kinds = seen.get(player.id);
    if (!kinds) { kinds = new Set(); seen.set(player.id, kinds); }
    if (kinds.has(type)) return;
    kinds.add(type);
    if (type === 'running') player.sendMessage('§e[3D арбуз: возврат] Восстановление активно. Обойдите все места, где были заменены арбузы.');
    if (type === 'changed') player.sendMessage('§e[3D арбуз: возврат] Экспериментальный арбуз возвращён в обычный.');
    if (type === 'error') console.warn('[3D melon recovery] Scan error: ' + String(error).slice(0,200));
  } catch (_) {}
}
const scanner = createScanner('aimelon:fruit','minecraft:melon_block',id => BlockPermutation.resolve(id),notice);
system.runInterval(() => scanner.tick(world.getAllPlayers()),10);
