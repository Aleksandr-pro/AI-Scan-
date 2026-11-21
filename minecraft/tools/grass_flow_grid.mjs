// Use exactly the same field module as the Bedrock addon for the desktop preview.
import { readFile } from 'node:fs/promises';
const path = new URL('../grass-flow-experiment/behavior/scripts/field.js', import.meta.url);
const text = await readFile(path, 'utf8');
const { corners, detailVariant } = await import(`data:text/javascript;base64,${Buffer.from(text).toString('base64')}`);
const start = Number(process.argv[2] ?? -16), size = Number(process.argv[3] ?? 32);
const rows = [];
for (let z = start; z < start + size; z++) {
  const row = [];
  for (let x = start; x < start + size; x++) row.push([...corners(x, z), detailVariant(x, z)]);
  rows.push(row);
}
console.log(JSON.stringify(rows));
