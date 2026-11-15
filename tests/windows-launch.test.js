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


import {createServer} from 'node:net';
import {mkdtempSync, copyFileSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';

function runCmd(cwd = root) {
  const child = spawn('cmd.exe', ['/d','/c','Start-Timer.cmd'], {
    cwd,
    env: {...process.env, UBF_TIMER_NO_BROWSER: '1'},
    windowsHide: true,
    stdio: ['pipe','pipe','pipe'],
  });
  let output = '';
  child.stdout.on('data', data => { output += data.toString(); });
  child.stderr.on('data', data => { output += data.toString(); });
  return {child, get output(){ return output; }};
}

function hardStop(child) {
  if (child.pid && child.exitCode === null) {
    spawnSync('taskkill.exe', ['/PID', String(child.pid), '/T', '/F'], {
      windowsHide: true, stdio: 'ignore',
    });
  }
}

function waitForExit(child, timeoutMs = 5000) {
  if (child.exitCode !== null) return Promise.resolve(child.exitCode);
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Process did not terminate')), timeoutMs);
    child.once('exit', code => { clearTimeout(timer); resolve(code); });
    child.once('error', error => { clearTimeout(timer); reject(error); });
  });
}

async function waitForController() {
  for (let i=0; i<80; i++) {
    try {
      const response = await fetch('http://127.0.0.1:8765/control.html', {signal: AbortSignal.timeout(500)});
      if (response.ok && (await response.text()).includes('id="panel-title"')) return;
    } catch { /* Server starting. */ }
    await delay(100);
  }
  throw new Error('Local controller failed to start');
}

async function waitForPortClosed() {
  for (let i=0; i<40; i++) {
    try {
      const response = await fetch('http://127.0.0.1:8765/control.html', {signal: AbortSignal.timeout(300)});
      if (!response.ok) return;
    } catch { return; }
    await delay(100);
  }
  throw new Error('Local server remained active after launcher exit');
}

test('missing extracted project files fail closed before starting a server', {
  skip:process.platform !== 'win32', timeout:15000,
}, async () => {
  const work = mkdtempSync(path.join(tmpdir(), 'ubf-missing-assets-'));
  copyFileSync(path.join(root,'Start-Timer.cmd'), path.join(work,'Start-Timer.cmd'));
  const launch = runCmd(work);
  try {
    launch.child.stdin.write('\r\n');
    launch.child.stdin.end();
    const status = await waitForExit(launch.child, 6000);
    assert.notEqual(status, 0);
    assert.match(launch.output, /Required timer files are missing/i);
  } finally { hardStop(launch.child); rmSync(work,{force:true,recursive:true}); }
});

test('a different server occupying 8765 is not reused or terminated', {
  skip:process.platform !== 'win32', timeout:15000,
}, async () => {
  const blocker=createServer((req,res) => {res.writeHead(200);res.end('OTHER PROCESS');});
  await new Promise((resolve,reject) => { blocker.once('error',reject);blocker.listen(8765,'127.0.0.1',resolve); });
  const child=spawn(process.execPath,['scripts/launch-local.mjs','--no-open'], {
    cwd:root,windowsHide:true,stdio:['ignore','pipe','pipe'],
  });
  let output='';
  child.stdout.on('data',data=>{output+=data.toString();});
  child.stderr.on('data',data=>{output+=data.toString();});
  try {
    const status=await waitForExit(child,5000);
    assert.notEqual(status,0);
    assert.match(output,/Port 8765 is already in use/);
    const response=await fetch('http://127.0.0.1:8765/');
    assert.equal(await response.text(),'OTHER PROCESS');
  } finally {
    hardStop(child);
    await new Promise(resolve => blocker.close(resolve));
  }
});

test('operator graceful stop frees port and a subsequent double-click restart works', {
  skip:process.platform !== 'win32', timeout:30000,
}, async () => {
  for (let attempt = 0; attempt < 2; attempt++) {
    const launch=runCmd();
    try {
      await waitForController();
      launch.child.stdin.write('q\r\n');
      launch.child.stdin.end();
      const status=await waitForExit(launch.child,4000);
      assert.equal(status,0,'Shutdown exit status: '+launch.output);
      await waitForPortClosed();
    } finally { hardStop(launch.child); }
  }
});
