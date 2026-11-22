import { system, world } from '@minecraft/server';
system.runTimeout(() => {
  try {
    const board = world.scoreboard.getObjective('grassflow_auto');
    if (!board) throw Error('основной набор не запущен');
    const session = board.getScore('session');
    if (!session || board.getScore('status_session') !== session) throw Error('основной набор ещё не подтвердил состояние');
    if (board.getScore('restore_session') === session) throw Error('набор восстановления ещё включён');
    if (board.getScore('count') !== 0) throw Error('ещё не все блоки восстановлены');
    board.setScore('pause', 0);
    world.sendMessage('Живая почва: автоматический режим снова включён. Можно отключить набор возобновления.');
  } catch (e) { world.sendMessage(`Живая почва: возобновление запрещено: ${e}.`); }
}, 100);
