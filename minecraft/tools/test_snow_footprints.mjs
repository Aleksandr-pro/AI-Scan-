import assert from 'node:assert/strict';
import {createFootprints, printPosition, snowSurface, LIFE_TICKS, STEP_DISTANCE, MIN_PRINT_DISTANCE} from '../snow-footprints/behavior/scripts/footsteps.js';

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
for (let h=0;h<8;h++) {
  layers=h;
  assert.equal(snowSurface(dim,.5,0,.5),(h+1)/8,`layer ${h} when feet stand on block below`);
  assert.equal(snowSurface(dim,.5,(h+1)/8,.5),(h+1)/8,`layer ${h} when feet stand on top`);
}
assert.equal(snowSurface(dim,.5,1.5,.5),undefined,'no print from a high jump');
layers=8; assert.equal(snowSurface(dim,.5,.5,.5),undefined);
mode='edge';
assert.ok(printPosition(dim,{x:1.9,y:1,z:.5},1,0,1),'partial edge is not rejected');
assert.equal(printPosition(dim,{x:2.1,y:1,z:.5},1,0,1),undefined,'center over air rejected');
mode='snow';
move(.5,.5,0); move(1,.5,2); assert.equal(prints.length,0);
move(1.5,.5,4); assert.equal(prints.length,1);
assert.equal(prints[0].angle,90); assert.equal(prints[0].pos.y,1.025);
move(2.3,.5,6); assert.equal(prints.length,2);
assert.ok(prints[0].pos.z > .5 && prints[1].pos.z < .5,'alternating left/right');
move(2.3,1.4,8); assert.equal(prints.length,3); assert.equal(prints[2].angle,0);
move(30,1.4,10); assert.equal(prints.length,3,'teleports leave no long trail');
p.isOnGround=false; p.isJumping=true; move(30,2.4,12); assert.equal(prints.length,3);
p.isOnGround=true; p.isJumping=false; move(30,2.4,14); move(30,3.3,16); assert.equal(prints.length,4);
p.getComponent=()=>({});move(30,4.2,18);assert.equal(prints.length,4,'no prints while riding');
p.getComponent=()=>undefined;
mode='air';move(31,4.2,20);move(32,4.2,22);assert.equal(prints.length,4,'no prints on other blocks');
// Ground directly below thin snow: including layers with no collision.
mode='layer'; layers=3;
const thin=[]; const layerSystem=createFootprints((d,pos,angle)=>thin.push({pos,angle}));
p.location={x:.5,y:0,z:.5};layerSystem.tick([p],0);
p.location={x:1.4,y:0,z:.5};layerSystem.tick([p],2);
assert.equal(thin.length,1);assert.equal(thin[0].pos.y,.525);
// False negative isOnGround: stable motion at the surface can still work.
const fallback=[]; const fallbackSystem=createFootprints((d,pos)=>fallback.push(pos));
p.isOnGround=false; p.isJumping=false; p.isFalling=false;p.location={x:.5,y:0,z:.5};fallbackSystem.tick([p],0);
p.location={x:1.4,y:0,z:.5};fallbackSystem.tick([p],2);assert.equal(fallback.length,1);
p.isFalling=true;p.location={x:2.1,y:0,z:.5};fallbackSystem.tick([p],4);assert.equal(fallback.length,1);
p.isFalling=false;p.isOnGround=true;mode='snow';
// An API error is reported, instead of being swallowed.
let diagnostics=[];const failing=createFootprints(()=>{throw new Error('mock spawn failed');},(pl,type,detail)=>diagnostics.push({type,detail}));
p.location={x:.5,y:1,z:.5};failing.tick([p],0);p.location={x:1.4,y:1,z:.5};failing.tick([p],2);
assert.equal(diagnostics[0].type,'error');assert.match(diagnostics[0].detail,/mock spawn failed/);
const limited=[]; const many=createFootprints((d,pos,angle)=>limited.push({pos,angle}));
let t=0;p.location={x:.5,y:1,z:.5};many.tick([p],t);
for(let i=1;i<=400;i++){p.location={x:.5+i*STEP_DISTANCE,y:1,z:.5}; t+=2; many.tick([p],t);}
assert.equal(limited.length,360,'per-player cap');
t=LIFE_TICKS+20;p.location={x:.5+400*STEP_DISTANCE+.95,y:1,z:.5};many.tick([p],t);
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
assert.ok(MIN_PRINT_DISTANCE > Math.hypot(.34,.52),'clearance exceeds decal diagonal');
// Two players taking exactly the same step must not stack their decals.
const noOverlap=[];const unique=createFootprints((dimension,pos)=>noOverlap.push({dim:dimension.id,pos}));
const makePlayer=(id,dimension)=>({...p,id,dimension,location:{x:.5,y:1,z:.5}});
const a=makePlayer('a',dim),b=makePlayer('b',dim);
unique.tick([a,b],0);a.location.x=b.location.x=1.4;unique.tick([a,b],2);
assert.equal(noOverlap.length,1,'same-location prints are not stacked');
const otherDim={...dim,id:'minecraft:the_nether'},d=makePlayer('d',otherDim);
unique.tick([a,b,d],4);d.location.x=1.4;unique.tick([a,b,d],6);
assert.equal(noOverlap.length,2,'identical positions in other dimensions are independent');
const c=makePlayer('c',dim);unique.tick([c],LIFE_TICKS+4);c.location.x=1.4;unique.tick([c],LIFE_TICKS+6);
assert.equal(noOverlap.length,3,'old footprints expire and no longer block new ones');
// Simulate a tight turn and walk back over the same trail.
const trail=[];const turns=createFootprints((dimension,pos)=>trail.push(pos));
const tplayer=makePlayer('turning',dim);let clock=0;turns.tick([tplayer],clock);
for (let i=1;i<=15;i++){tplayer.location.x=.5+i*.2;turns.tick([tplayer],clock+=2);}
for (let i=14;i>=0;i--){tplayer.location.x=.5+i*.2;turns.tick([tplayer],clock+=2);}
assert.ok(trail.length>=3,'normal walking still creates a trail');
for(let i=0;i<trail.length;i++)for(let j=i+1;j<trail.length;j++) {
  assert.ok(Math.hypot(trail[i].x-trail[j].x,trail[i].z-trail[j].z)>=MIN_PRINT_DISTANCE-1e-9,
    'tight turns and revisits do not stack live footprints');
}
console.log('Snow footprint logic tests passed');
