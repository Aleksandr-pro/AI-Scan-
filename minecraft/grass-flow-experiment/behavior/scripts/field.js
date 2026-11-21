// Deterministic, coordinate-based density. Corner values are shared between tiles.
// Pure functions: no world access and no random/seed state.
export function hash2(x, z, seed) {
  let h = Math.imul(x | 0, 0x1f123bb5) ^ Math.imul(z | 0, 0x5f356495) ^ seed;
  h ^= h >>> 16; h = Math.imul(h, 0x7feb352d); h ^= h >>> 15;
  h = Math.imul(h, 0x846ca68b); h ^= h >>> 16;
  return (h >>> 0) / 4294967295;
}
function smooth(x) { return x * x * (3 - 2 * x); }
function noise(x, z, scale, seed) {
  const xx = x / scale, zz = z / scale;
  const x0 = Math.floor(xx), z0 = Math.floor(zz);
  const tx = smooth(xx - x0), tz = smooth(zz - z0);
  const lerp = (a, b, t) => a + (b - a) * t;
  return lerp(lerp(hash2(x0, z0, seed), hash2(x0 + 1, z0, seed), tx),
              lerp(hash2(x0, z0 + 1, seed), hash2(x0 + 1, z0 + 1, seed), tx), tz);
}
export function density(x, z) {
  // A small, spatially smooth detail field breaks up broad borders without
  // turning density back into independent block-by-block randomness.
  return 0.65 * noise(x, z, 24, 0x51a72) + 0.23 * noise(x, z, 9, 0x3f18b)
    + 0.12 * noise(x, z, 3, 0x7d31c);
}
export function level(x, z) {
  const v = density(x, z);
  return v < 0.40 ? 0 : v < 0.60 ? 1 : 2;
}
// Order: north-west, north-east, south-west, south-east.
export function corners(x, z) {
  return [level(x,z), level(x+1,z), level(x,z+1), level(x+1,z+1)];
}
export function detailVariant(x, z) {
  // Four fixed phases make the photographic surface repeat every 2x2 blocks.
  // They vary detail only; density still comes from shared world-space corners.
  return (x & 1) + 2 * (z & 1);
}
export function states(x, z) {
  const [nw, ne, sw, se] = corners(x, z);
  return {'grassflow:nw': nw, 'grassflow:ne': ne, 'grassflow:sw': sw, 'grassflow:se': se,
          'grassflow:detail': detailVariant(x, z)};
}
