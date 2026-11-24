import assert from 'node:assert/strict';
import {createFootprints, printPosition, snowSurface, LIFE_TICKS, STEP_DISTANCE} from '../snow-footprints/behavior/scripts/footsteps.js';

const block = (typeId, height = 0) => ({typeId, permutation: {getState: name => name === 'height' ? height : undefined}});
let mode = 'snow', layers = 0;
const dim = {id: 'minecraft:overworld', getBlock({x,y,z}) {
  if (mode === 'air' || (mode === 'edge' && x >= 2)) return block('minecraft:air');
  if (mode === 'layer') return y === 0 ? block('minecraft:snow_layer', layers) : block('minecraft:air');
  return y === 0 ? block('minecraft:snow') : block('minecraft:air');
}};
const p = {id:'one', dimension:dim, location:{x:0.5,y:1,z:0.5}, isOnGround:true,
  isInWater:false, isSwimming:false, isGliding:false, isFlying:false, isSleeping:false,
  getComponent: () => undefined};
let prints=[];
const system=createFootprints((dimension, pos, angle) => prints.push({dimension,pos,angle}));
function move(x,z,t) {p.location={x,y:1,z};system.tick([p],t);}
assert.equal(snowSurface(dim,.5,1,.5),1);
assert.equal(snowSurface(dim,.5,2,.5),undefined);
mode='layer'; layers=3;
assert.equal(snowSurface(dim,.5,.5,.5), .5);
assert.equal(snowSurface(dim,.5,.375,.5), .5); // thin-layer collision can be lower
layers=8; assert.equal(snowSurface(dim,.5,.5,.5),undefined);
mode='edge'; assert.equal(printPosition(dim,{x:1.9,y:1,z:.5},1,0,1),undefined);
mode='snow';
move(.5,.5,0); move(1,.5,2); assert.equal(prints.length,0);
move(1.5,.5,4); assert.equal(prints.length,1);
assert.equal(prints[0].angle,90); assert.equal(prints[0].pos.y,1.015);
move(2.3,.5,6); assert.equal(prints.length,2);
assert.ok(prints[0].pos.z > .5 && prints[1].pos.z < .5,'alternating left/right');
move(2.3,1.4,8); assert.equal(prints.length,3); assert.equal(prints[2].angle,0);
move(30,1.4,10); assert.equal(prints.length,3,'teleports leave no long trail');
p.isOnGround=false; move(30,2.4,12); assert.equal(prints.length,3);
p.isOnGround=true; move(30,2.4,14); move(30,3.3,16); assert.equal(prints.length,4);
p.getComponent=()=>({});move(30,4.2,18);assert.equal(prints.length,4,'no prints while riding');
p.getComponent=()=>undefined;
mode='air';move(31,4.2,20);move(32,4.2,22);assert.equal(prints.length,4,'no prints on other blocks');
mode='snow';
const limited=[]; const many=createFootprints((d,pos,angle)=>limited.push({pos,angle}));
let t=0;p.location={x:.5,y:1,z:.5};many.tick([p],t);
for(let i=1;i<=400;i++){p.location={x:.5+i*STEP_DISTANCE,y:1,z:.5}; t+=2; many.tick([p],t);}
assert.equal(limited.length,360,'per-player cap');
t=LIFE_TICKS+2;p.location={x:301.25,y:1,z:.5};many.tick([p],t);
assert.equal(limited.length,361,'space freed after expiry');
const all=[]; const global=createFootprints((d,pos,angle)=>all.push({pos,angle}));
const crowd=Array.from({length:4},(_,i)=>({...p,id:`p${i}`,location:{x:.5,y:1,z:i*2+.5}}));
global.tick(crowd,0);
for(let i=1;i<=210;i++){
  for(const q of crowd)q.location.x=.5+i*STEP_DISTANCE;
  global.tick(crowd,i*2);
}
assert.equal(all.length,720,'global particle cap is shared across players');
assert.ok(LIFE_TICKS === 1200,'target lifetime is one minute at 20 ticks/s');
console.log('Snow footprint logic tests passed');
