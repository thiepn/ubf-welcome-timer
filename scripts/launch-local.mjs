/** Launch the existing localhost-only server and open the controller when ready. */
import {spawn} from 'node:child_process';
import {createConnection} from 'node:net';
import {setTimeout as delay} from 'node:timers/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const port = 8765;
const controllerUrl = `http://127.0.0.1:${port}/control.html`;
const noBrowser = process.argv.includes('--no-open') || process.env.UBF_TIMER_NO_BROWSER === '1';

async function portInUse() {
  return new Promise(resolve => {
    const client = createConnection({host: '127.0.0.1', port});
    let finished = false;
    const done = occupied => {
      if (finished) return;
      finished = true;
      client.destroy();
      resolve(occupied);
    };
    client.once('connect', () => done(true));
    client.once('error', () => done(false));
    client.setTimeout(500, () => done(true)); // Fail closed on an ambiguous probe.
  });
}

if (await portInUse()) {
  console.error(`Port ${port} is already in use. Close any previous timer window/server before relaunching.`);
  process.exitCode = 1;
} else {
  const server = spawn(process.execPath, ['server.mjs'], {
    cwd: root,
    env: {...process.env, PORT: String(port)},
    stdio: 'inherit',
  });
  let childError = null;
  let stopping = false;
  server.on('error', error => {childError = error;});
  const shutdown = () => { stopping = true; if (!server.killed) server.kill(); };
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
  let ready = false;
  for (let i = 0; i < 40; i += 1) {
    if (childError || server.exitCode !== null) break;
    try {
      const response = await fetch(controllerUrl, {signal: AbortSignal.timeout(500)});
      if (response.ok && (await response.text()).includes('id="panel-title"')) {
        ready = true;
        break;
      }
    } catch { /* Server is starting. */ }
    await delay(100);
  }
  if (!ready) {
    console.error('The local timer server did not become ready. Check the error above.');
    if (!server.killed) server.kill();
    process.exitCode = 1;
  } else {
    console.log(`Controller: ${controllerUrl}`);
    console.log('Projector:  http://127.0.0.1:8765/display.html');
    console.log('No internet connection or npm install is needed during operation.');
    if (process.platform === 'win32' && !noBrowser) {
      const opener = spawn('cmd.exe', ['/d', '/c', `start "" "${controllerUrl}"`], {
        windowsHide: true,
        stdio: 'ignore',
      });
      opener.once('error', error => console.error(`Could not open browser automatically: ${error.message}. Open ${controllerUrl} manually.`));
      opener.unref();
    }
  }
  const childExit = await new Promise(resolve => {
    if (server.exitCode !== null) resolve(server.exitCode);
    else server.once('exit', code => resolve(code));
  });
  if (!stopping && (childError || childExit !== 0 || !ready)) process.exitCode = 1;
}
