import { system, world } from '@minecraft/server';
import { createDirector } from './ambience.js';

const director = createDirector();
system.runInterval(() => {
  director.tick(world.getAllPlayers(), system.currentTick, world.getTimeOfDay());
}, 200);
