import { BlockPermutation, system } from '@minecraft/server';
import { createController } from './controller.js';

const controller = createController((id, properties) => BlockPermutation.resolve(id, properties));
system.afterEvents.scriptEventReceive.subscribe(event => {
  if (event.id === 'grassflow:preview') controller.begin(event.sourceEntity, 'preview');
  if (event.id === 'grassflow:clear') controller.begin(event.sourceEntity, 'clear');
});
system.runInterval(() => controller.tick(), 1);
