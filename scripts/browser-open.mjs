/** Thin, testable wrapper for Windows' default-browser START invocation. */
import {spawn} from 'node:child_process';

export function browserOpenInvocation(url) {
  if (url !== 'http://127.0.0.1:8765/control.html') {
    throw new Error('Refusing to open an unexpected controller URL.');
  }
  return {
    executable: 'cmd.exe',
    args: ['/d', '/c', 'start "" "' + url + '"'],
    options: {windowsHide:true, stdio:'ignore'},
  };
}

export function openDefaultBrowser(url, spawnProcess=spawn, onError=message=>console.error(message)) {
  const spec=browserOpenInvocation(url);
  const child=spawnProcess(spec.executable, spec.args, spec.options);
  child.once('error', error => onError(
    'Could not open browser automatically: ' + error.message + '. Open ' + url + ' manually.'
  ));
  child.unref();
  return child;
}
