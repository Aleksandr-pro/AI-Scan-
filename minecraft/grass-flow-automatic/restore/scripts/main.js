import { system, world } from '@minecraft/server';
let tick = 0, errorShown = false;
system.runInterval(() => {
  try {
    // Shared scoreboard coordinates the packs: dynamic properties are scoped
    // to their owning behavior pack and must not be used for cross-pack IPC.
    const board = world.scoreboard.getObjective('grassflow_auto');
    if (!board) throw Error('основной набор не запущен');
    board.setScore('pause', 1);
    const session = board.getScore('session');
    if (typeof session === 'number') board.setScore('restore_session', session);
    if (++tick % 10 === 1) {
      const ready = board.getScore('status_session') === session;
      const count = ready ? board.getScore('count') : undefined;
      const status = Number.isInteger(count) ? `Осталось записей: ${count}.` : 'Ожидание основного набора.';
      for (const p of world.getAllPlayers()) p.sendMessage(`Живая почва: восстановление. ${status} Не отключайте автоматический набор до нуля.`);
    }
  } catch (e) {
    if (!errorShown) { world.sendMessage(`Живая почва: ошибка восстановления; не отключайте наборы, используйте резервную копию. ${e}`); errorShown = true; }
  }
}, 20);
