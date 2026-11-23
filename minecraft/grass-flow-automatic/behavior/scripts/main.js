import { BlockPermutation, system, world } from '@minecraft/server';
import { createController } from './automatic.js';

const controller = createController(world, (id, values) => BlockPermutation.resolve(id, values));
// Give each game session a fresh ID so stale recovery heartbeats cannot be
// confused with a live helper after a restart. Fail closed if this write fails.
system.run(() => {
  try {
    const board = world.scoreboard.getObjective('grassflow_auto') ?? world.scoreboard.addObjective('grassflow_auto', 'GrassFlow control');
    board.setScore('session', Math.floor(Math.random() * 2000000000) + 1);
    board.setScore('status_session', 0);
    board.setScore('restore_session', 0);
    // Let the optional recovery pack set its persistent pause first.
    system.runTimeout(() => {
      system.runInterval(() => controller.tick(system.currentTick), 10);
    }, 100);
  } catch (e) { console.warn(`[GrassFlow] Cannot initialize safely: ${e}`); }
});
