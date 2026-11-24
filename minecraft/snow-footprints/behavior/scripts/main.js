import {system, world, MolangVariableMap} from '@minecraft/server';
import {createFootprints} from './footsteps.js';

const prints = createFootprints((dimension, at, angle) => {
  const variables = new MolangVariableMap();
  variables.setFloat('variable.aegis_angle', angle);
  dimension.spawnParticle('aegis:snow_footprint', at, variables);
});

// Sampling twice per tenth of a second avoids a per-tick world scan.
system.runInterval(() => prints.tick(world.getAllPlayers(), system.currentTick), 2);
