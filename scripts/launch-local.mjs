/** Launch the existing localhost-only server and open the controller when ready. */
import {spawn} from 'node:child_process';
import {createConnection} from 'node:net';
import {setTimeout as delay} from 'node:timers/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {openDefaultBrowser} from './browser-open.mjs';

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

const nodeMajor = Number(process.versions.node.split('.')[0]);
if (!Number.isSafeInteger(nodeMajor) || nodeMajor < 20) {
  console.error(`Node.js 20 or newer is required; detected ${process.version}. The timer server was not started.`);
  process.exitCode = 1;
} else if (await portInUse()) {
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
  const shutdown = () => {
    if (stopping) return;
    stopping = true;
    if (server.exitCode === null && !server.killed) server.kill();
  };
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
  // Explicit operator shutdown ensures the local server is released before
  // the batch window exits. Also works with piped input in Windows CI.
  let inputBuffer = '';
  const onInput = chunk => {
    inputBuffer += String(chunk);
    const lines = inputBuffer.split(/\r?\n/);
    inputBuffer = lines.pop() || '';
    if (lines.some(line => line.trim().toLowerCase() === 'q')) shutdown();
  };
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', onInput);
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
    console.log('To stop the timer safely, type q and press Enter in this window.');
    if (process.platform === 'win32' && !noBrowser) {
      openDefaultBrowser(controllerUrl);
    }
  }
  const childExit = await new Promise(resolve => {
    if (server.exitCode !== null) resolve(server.exitCode);
    else server.once('exit', code => resolve(code));
  });
  process.stdin.off('data', onInput);
  process.stdin.pause();
  process.off('SIGINT', shutdown);
  process.off('SIGTERM', shutdown);
  if (!stopping && (childError || childExit !== 0 || !ready)) process.exitCode = 1;
}
