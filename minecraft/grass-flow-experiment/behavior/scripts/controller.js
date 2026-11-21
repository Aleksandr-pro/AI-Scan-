import { states } from './field.js';

const SIZE = 32;
const BATCH = 16;
const BLOCK = 'grassflow:sample';
const AIR = 'minecraft:air';

// No action on load: only explicit /scriptevent requests can modify blocks.
export function createController(resolve) {
  let job = null;
  const cache = new Map();
  const say = (p, text) => { try { p.sendMessage(`GrassFlow: ${text}`); } catch (_) {} };
  const cell = (j, i) => ({x: j.x0 + (i % SIZE), y: j.y, z: j.z0 + Math.floor(i / SIZE)});
  function begin(player, kind) {
    if (!player || player.typeId !== 'minecraft:player') return;
    if (job) return say(player, 'Дождитесь завершения текущей операции.');
    const p = player.location;
    job = { player, dim: player.dimension, x0: Math.floor(p.x) - SIZE / 2,
      z0: Math.floor(p.z) - SIZE / 2, y: Math.floor(p.y) - 1,
      kind, stage: kind === 'preview' ? 'check' : 'clear', index: 0, changed: 0 };
    say(player, `${kind === 'preview' ? 'Проверяю пустое пространство' : 'Убираю только блоки grassflow:sample'}: x ${job.x0}..${job.x0+SIZE-1}, y ${job.y}, z ${job.z0}..${job.z0+SIZE-1}.`);
  }
  function tick() {
    if (!job) return;
    const j = job;
    try {
      let count = 0;
      while (j.index < SIZE * SIZE && count++ < BATCH) {
        const pos = cell(j, j.index);
        const block = j.dim.getBlock(pos);
        if (!block) throw new Error('чанк не загружен или позиция вне мира');
        if (j.stage === 'check') {
          if (block.typeId !== AIR) throw new Error(`место занято: ${pos.x} ${pos.y} ${pos.z}; ничего не построено`);
        } else if (j.stage === 'build') {
          if (block.typeId !== AIR) throw new Error(`место занято во время строительства: ${pos.x} ${pos.y} ${pos.z}; часть площадки могла остаться`);
          const s = states(pos.x, pos.z);
          const key = Object.values(s).join('');
          if (!cache.has(key)) cache.set(key, resolve(BLOCK, s));
          block.setPermutation(cache.get(key));
          j.changed++;
        } else if (block.typeId === BLOCK) {
          block.setPermutation(resolve(AIR));
          j.changed++;
        }
        j.index++;
      }
      if (j.index === SIZE * SIZE) {
        if (j.stage === 'check') {
          j.stage = 'build'; j.index = 0;
          say(j.player, 'Место пустое; строю отдельную площадку по 16 блоков за тик.');
        } else {
          say(j.player, `Готово. Изменено блоков: ${j.changed}.`);
          job = null;
        }
      }
    } catch (e) {
      say(j.player, `Остановлено: ${String(e)}. Изменено блоков: ${j.changed}. Для удаления частичной площадки используйте clear с тех же координат.`);
      job = null;
    }
  }
  return { begin, tick };
}
