import { BlockPermutation, system, world } from '@minecraft/server';
import { createController } from './wetness.js';

const controller = createController(world, (id, states) => BlockPermutation.resolve(id, states));
world.afterEvents.weatherChange.subscribe(controller.weatherChanged);
system.runInterval(controller.tick, 40);

system.afterEvents.scriptEventReceive.subscribe(event => {
  if (!['rainwet:restore', 'rainwet:resume', 'rainwet:status'].includes(event.id)) return;
  const reply = message => { if (event.sourceEntity) event.sourceEntity.sendMessage(message); };
  try {
    if (event.id === 'rainwet:restore') {
      controller.pause();
      reply('RainWet: восстановление включено. Не отключайте пакет, пока status не покажет 0. Посетите все изменённые области.');
    } else if (event.id === 'rainwet:resume') {
      controller.resume();
      reply('RainWet: намокание разрешено после события дождя.');
    } else {
      const s = controller.status();
      reply(`RainWet: записей ${s.remaining}; пауза ${s.paused ? 'да' : 'нет'}; дождь ${s.raining ? 'да' : 'нет/неизвестно'}.`);
    }
  } catch (e) { reply(`RainWet: ошибка; не отключайте пакет: ${e}`); }
});
