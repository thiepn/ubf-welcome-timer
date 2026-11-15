import test from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {browserOpenInvocation, openDefaultBrowser} from '../scripts/browser-open.mjs';

const controller='http://127.0.0.1:8765/control.html';

test('Windows default-browser command opens exactly the loopback controller URL', () => {
  assert.deepEqual(browserOpenInvocation(controller),{
    executable:'cmd.exe',
    args:['/d','/c','start "" "' + controller + '"'],
    options:{windowsHide:true,stdio:'ignore'},
  });
  assert.throws(()=>browserOpenInvocation('https://example.org/'),/unexpected controller URL/);
});

test('browser opener invokes the Windows command and detaches without hiding failures', () => {
  const calls=[];
  const warnings=[];
  const child=new EventEmitter();
  child.unref=()=>calls.push({unref:true});
  const result=openDefaultBrowser(controller,(executable,args,options)=>{
    calls.push({executable,args,options});
    return child;
  }, message=>warnings.push(message));
  assert.equal(result,child);
  assert.equal(calls.length,2);
  assert.equal(calls[0].executable,'cmd.exe');
  assert.deepEqual(calls[0].args,['/d','/c','start "" "' + controller + '"']);
  assert.deepEqual(calls[0].options,{windowsHide:true,stdio:'ignore'});
  assert.deepEqual(calls[1],{unref:true});
  child.emit('error',new Error('blocked by Windows policy'));
  assert.match(warnings[0],/blocked by Windows policy/);
  assert.match(warnings[0],/Open http:\/\/127\.0\.0\.1:8765\/control\.html manually/);
});
