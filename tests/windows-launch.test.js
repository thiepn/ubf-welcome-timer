import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn, spawnSync} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

// Runs on the Windows Server CI runner, not on a physical Windows 11 projector.
test('Windows double-click CMD launcher serves local controller, display and Canva asset', {
  skip: process.platform !== 'win32',
  timeout: 30000,
}, async () => {
  const child = spawn('cmd.exe', ['/d', '/c', 'Start-Timer.cmd'], {
    cwd: root,
    env: {...process.env, UBF_TIMER_NO_BROWSER: '1'},
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let output = '';
  child.stdout.on('data', chunk => { output += chunk.toString(); });
  child.stderr.on('data', chunk => { output += chunk.toString(); });
  try {
    let ready = false;
    for (let i = 0; i < 160; i += 1) {
      if (child.exitCode !== null) throw new Error(`Launcher exited early: ${output}`);
      try {
        const page = await fetch('http://127.0.0.1:8765/control.html', {signal: AbortSignal.timeout(600)});
        if (page.ok && (await page.text()).includes('id="panel-title"')) {
          ready = true;
          break;
        }
      } catch { /* Probe again while server starts. */ }
      await delay(100);
    }
    assert.equal(ready, true, `CMD launcher never became ready: ${output}`);
    const display = await fetch('http://127.0.0.1:8765/display.html');
    assert.equal(display.status, 200);
    assert.match(await display.text(), /id="stage"/);
    const image = await fetch('http://127.0.0.1:8765/assets/welcome.png');
    assert.equal(image.status, 200);
    const png = Buffer.from(await image.arrayBuffer());
    assert.equal(png.subarray(0, 8).toString('hex'), '89504e470d0a1a0a');
    assert.ok(output.includes('127.0.0.1:8765'), output);
  } finally {
    if (child.pid && child.exitCode === null) {
      // Clean up cmd.exe and its Node.js child process tree, even on test failure.
      spawnSync('taskkill.exe', ['/PID', String(child.pid), '/T', '/F'], {windowsHide: true, stdio: 'ignore'});
    }
  }
});
