// Smoke-test the real entrypoint with a mocked Script API, not the game client.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

let callback, interval, shouldThrow=false;
const system={currentTick:0,runInterval(fn,rate){callback=fn;interval=rate;}};
const messages=[],spawned=[];
const dim={id:'minecraft:overworld',getBlock({y}){
  return {typeId:y===0?'minecraft:snow':'minecraft:air',permutation:{getState(){return undefined;}}};
},spawnParticle(id,at,vars){
  if(shouldThrow)throw new Error('test render API failure');
  spawned.push({id,at,angle:vars.values['variable.aegis_angle']});
}};
class MolangVariableMap {constructor(){this.values={};}setFloat(k,v){this.values[k]=v;}}
const p={id:'player',location:{x:.5,y:1,z:.5},dimension:dim,isOnGround:true,
  getComponent(){return undefined;},sendMessage(text){messages.push(text);}};
const world={getAllPlayers(){return [p];}};
globalThis.__snowMock={system,world,MolangVariableMap};
globalThis.__snowLogic=new URL('../snow-footprints/behavior/scripts/footsteps.js',import.meta.url).href;
const filename=new URL('../snow-footprints/behavior/scripts/main.js',import.meta.url);
let source=await readFile(filename,'utf8');
source=source.replace("import {system, world, MolangVariableMap} from '@minecraft/server';",'const {system, world, MolangVariableMap} = globalThis.__snowMock;');
source=source.replace("import {createFootprints} from './footsteps.js';",'const {createFootprints} = await import(globalThis.__snowLogic);');
assert.ok(!source.includes("from '@minecraft/server'"),'mock import must replace API');
await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
assert.equal(interval,2);
function tick(x,t) {p.location.x=x;system.currentTick=t;callback();}
tick(.5,0);assert.equal(messages.length,1);assert.match(messages[0],/Скрипт запущен/);
tick(1.4,2);assert.equal(spawned.length,1);assert.equal(spawned[0].id,'aegis:snow_footprint');assert.equal(spawned[0].angle,90);
assert.match(messages[1],/след запрошен/);
tick(2.3,4);assert.equal(spawned.length,2);assert.equal(messages.length,2,'status is once per session');
shouldThrow=true;tick(3.2,6);assert.equal(messages.length,3);assert.match(messages[2],/Ошибка скрипта/);
tick(4.1,8);tick(5.0,10);assert.equal(messages.length,3,'error is rate limited');
console.log('Snow footprint entrypoint smoke test passed');
