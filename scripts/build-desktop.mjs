// Stage only the existing production web UI and original assets into Tauri.
// The browser site and its offline Node launcher remain untouched.
import {cpSync, existsSync, mkdirSync, rmSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname, join, resolve} from 'node:path';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const output = join(root, 'dist', 'desktop');
const runtimePaths = ['index.html', 'control.html', 'display.html', 'css', 'js', 'assets'];

for (const name of runtimePaths) {
  if (!existsSync(join(root, name))) throw new Error('Required web asset missing: ' + name);
}
rmSync(output, {recursive:true, force:true});
mkdirSync(output, {recursive:true});
for (const name of runtimePaths) {
  cpSync(join(root, name), join(output, name), {recursive:true, force:false});
}
console.log('Staged offline Tauri frontend: ' + runtimePaths.join(', '));
