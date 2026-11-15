// Execute actual WebView2 controller/display on a Windows CI runner, with a
// hard timeout so a headless runner limitation cannot stall the workflow.
// There is no projector and NO physical-display certification here.
import {spawn, spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {dirname, resolve} from 'node:path';

if (process.platform !== 'win32') {
  console.error('This smoke requires Windows with installed WebView2.');
  process.exit(2);
}
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const args = ['run','--quiet','--manifest-path','src-tauri/Cargo.toml',
  '--bin','webview2_smoke'];
const child = spawn('cargo', args, {
  cwd: root, windowsHide: true, stdio:['ignore','pipe','pipe'],
});
let output='';
child.stdout.on('data', chunk => {output+=chunk.toString();});
child.stderr.on('data', chunk => {output+=chunk.toString();});
let exited=false;
const stop = setTimeout(() => {
  if (exited) return;
  console.error('WEBVIEW2_SMOKE_TIMEOUT: Real native WebView2 signal not received in time.');
  console.error(output.slice(-8000));
  if (child.pid) spawnSync('taskkill.exe',['/PID',String(child.pid),'/T','/F'],
    {windowsHide:true,stdio:'ignore'});
  process.exitCode=1;
}, 90000);
child.on('error', error => {
  clearTimeout(stop);
  console.error('WEBVIEW2_SMOKE_START_ERROR:',error.message);
  process.exitCode=1;
});
child.on('exit', code => {
  exited=true;
  clearTimeout(stop);
  console.log(output.slice(-8000));
  if (code !== 0 || !output.includes('WEBVIEW2_SMOKE_PASS:') ||
      !output.includes('WEBVIEW2_FOCUS_PASS:') ||
      !output.includes('WEBVIEW2_FOCUS_RELEASE_PASS:') ||
      !output.includes('WEBVIEW2_FOCUS_RACE_PASS:') ||
      !output.includes('WEBVIEW2_FULLSCREEN_PASS:') ||
      !output.includes('WEBVIEW2_SAME_LABEL_REOPEN_PASS:')) {
    console.error('WEBVIEW2_SMOKE_FAIL: native process did not prove same-profile timer propagation.');
    process.exitCode=1;
  } else {
    console.log('WEBVIEW2_SMOKE_PASS: two real Windows WebViews, no projector.');
  }
});
