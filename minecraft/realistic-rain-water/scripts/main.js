import { system, world } from '@minecraft/server';
import { createController } from './puddles.js';

const controller = createController(world);
world.afterEvents.weatherChange.subscribe(controller.weatherChanged);
// One scan every five seconds, globally, rather than one per player.
system.runInterval(controller.tick, 100);
