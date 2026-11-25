import {BlockPermutation, system, world} from '@minecraft/server';
import {createScanner} from './scanner.js';

const seen = new Map();
function notice(player, type, error) {
  try {
    let kinds = seen.get(player.id);
    if (!kinds) { kinds = new Set(); seen.set(player.id, kinds); }
    if (kinds.has(type)) return;
    kinds.add(type);
    if (type === 'running') player.sendMessage('§e[3D арбуз] Эксперимент работает: обычные арбузы рядом заменяются. Только копия мира.');
    if (type === 'changed') player.sendMessage('§e[3D арбуз] Арбуз заменён. Внешний вид и механика требуют проверки.');
    if (type === 'error') console.warn('[3D melon] Scan error: ' + String(error).slice(0,200));
  } catch (_) {}
}
const scanner = createScanner('minecraft:melon_block','aimelon:fruit',id => BlockPermutation.resolve(id),notice);
system.runInterval(() => scanner.tick(world.getAllPlayers()),10);
