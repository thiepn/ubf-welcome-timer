import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn, spawnSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
test('Windows CMD launcher rejects unsupported Node.js 18 before serving any page', {
  skip:process.platform !== 'win32' || Number(process.versions.node.split('.')[0]) !== 18,
  timeout:15000,
}, async () => {
  const child=spawn('cmd.exe',['/d','/c','Start-Timer.cmd'], {
    cwd:root,env:{...process.env,UBF_TIMER_NO_BROWSER:'1'},
    windowsHide:true,stdio:['pipe','pipe','pipe'],
  });
  let output='';
  child.stdout.on('data',chunk=>{output+=chunk.toString();});
  child.stderr.on('data',chunk=>{output+=chunk.toString();});
  try {
    child.stdin.write('\r\n');
    child.stdin.end();
    const code=await Promise.race([
      new Promise((resolve,reject)=>{
        child.once('exit',resolve);
        child.once('error',reject);
      }),
      new Promise((_,reject)=>setTimeout(()=>reject(new Error('Launcher did not reject Node 18')),4500)),
    ]);
    assert.notEqual(code,0,'Unsupported Node must fail');
    assert.match(output,/Node\.js 20|Node 20|requires Node/i);
    await assert.rejects(fetch('http://127.0.0.1:8765/control.html',{signal:AbortSignal.timeout(300)}));
  } finally {
    if (child.pid && child.exitCode===null) {
      spawnSync('taskkill.exe',['/PID',String(child.pid),'/T','/F'],{
        windowsHide:true,stdio:'ignore',
      });
    }
  }
});
