import test from 'node:test';
import assert from 'node:assert/strict';
import {TimerSync} from '../js/sync.js';
import {startTimer, pauseTimer, STORAGE_KEY} from '../js/timer-core.js';

// Simulates same-origin browser tabs using Node's real BroadcastChannel.
// This is NOT a substitute for real browser acceptance.
const listeners = new EventTarget();
globalThis.addEventListener = (...args) => listeners.addEventListener(...args);
globalThis.removeEventListener = (...args) => listeners.removeEventListener(...args);
const mem = new Map();
globalThis.localStorage = {
  getItem: k => mem.get(k) ?? null,
  setItem: (k,v) => mem.set(k,String(v)),
  removeItem: k => mem.delete(k),
};
const settle = (ms = 40) => new Promise(resolve => setTimeout(resolve,ms));

test('controller writes, displays observe via BroadcastChannel', async () => {
  mem.clear();
  const seen = [];
  const controller = new TimerSync('control');
  const display = new TimerSync('display',{onState: state => seen.push(state.phase)});
  try {
    controller.start(); display.start(); await settle();
    const state = startTimer(controller.state,180000,Date.now(),'integration-1');
    controller.write(state);
    await settle();
    assert.equal(display.state.phase,'running');
    assert.equal(display.state.durationMs,180000);
    assert.equal(JSON.parse(mem.get(STORAGE_KEY)).phase,'running');
    assert.ok(seen.includes('running'));
    assert.throws(() => display.write(state),/Only controller/);
  } finally {controller.close();display.close();}
});

test('delayed earlier snapshot cannot rewind a newer timer revision', async () => {
  mem.clear();
  const controller = new TimerSync('control');
  const display = new TimerSync('display');
  try {
    controller.start(); display.start(); await settle();
    const first = startTimer(controller.state,60000,Date.now(),'integration-2');
    controller.write(first); await settle();
    const second = pauseTimer(first,Date.now()+1000);
    controller.write(second); await settle();
    controller.send({type:'snapshot',state:first}); await settle();
    assert.equal(display.state.phase,'paused');
    assert.equal(display.state.revision,second.revision);
  } finally {controller.close(); display.close();}
});

test('display refresh restores persisted countdown without resetting controller', async () => {
  mem.clear();
  const controller = new TimerSync('control');
  const firstDisplay = new TimerSync('display');
  let refreshed;
  try {
    controller.start(); firstDisplay.start(); await settle();
    controller.write(startTimer(controller.state,300000,Date.now(),'integration-3'));
    await settle(); firstDisplay.close();
    refreshed = new TimerSync('display'); refreshed.start(); await settle();
    assert.equal(refreshed.state.phase,'running');
    assert.equal(refreshed.state.sessionId,'integration-3');
    assert.equal(controller.state.phase,'running');
    assert.equal(refreshed.state.revision,controller.state.revision);
  } finally {controller.close(); firstDisplay.close(); refreshed?.close();}
});

test('duplicate controllers are detectable to both operators', async () => {
  mem.clear();
  let aHasPeer = false, bHasPeer = false;
  const a = new TimerSync('control',{onPresence: peers => aHasPeer = [...peers.values()].some(p=>p.role==='control')});
  const b = new TimerSync('control',{onPresence: peers => bHasPeer = [...peers.values()].some(p=>p.role==='control')});
  try {a.start();b.start();await settle();a.announce();b.announce();await settle();assert.equal(aHasPeer,true);assert.equal(bHasPeer,true);}
  finally {a.close();b.close();}
});


test('new session after a non-persisted controller restart supersedes an old display session', async () => {
  mem.clear();
  const previousSet = globalThis.localStorage.setItem;
  globalThis.localStorage.setItem = () => { throw new Error('storage unavailable'); };
  const display = new TimerSync('display');
  const first = new TimerSync('control');
  let restarted;
  try {
    display.start(); first.start(); await settle();
    first.write(startTimer(first.state, 180000, Date.now(), 'storage-failed-first'));
    await settle();
    assert.equal(display.state.sessionId, 'storage-failed-first');
    first.close();
    await settle(5);
    restarted = new TimerSync('control'); restarted.start();
    await settle();
    restarted.write(startTimer(restarted.state, 60000, Date.now()+100, 'storage-failed-second'));
    await settle();
    assert.equal(display.state.sessionId, 'storage-failed-second');
    assert.equal(display.state.durationMs, 60000);
  } finally {
    first.close(); restarted?.close(); display.close();
    globalThis.localStorage.setItem = previousSet;
  }
});


test('restored display reconnects and catches updates missed during page suspension', async () => {
  mem.clear();
  const controller = new TimerSync('control');
  const display = new TimerSync('display');
  try {
    controller.start(); display.start(); await settle();
    const running = startTimer(controller.state, 180000, Date.now(), 'restore-test');
    controller.write(running);
    await settle();
    assert.equal(display.state.phase, 'running');
    display.close();
    const paused = pauseTimer(running, Date.now() + 1000);
    controller.write(paused);
    await settle();
    assert.equal(display.state.phase, 'running');
    display.resume();
    await settle();
    assert.equal(display.state.phase, 'paused');
    assert.equal(display.state.revision, paused.revision);
    display.close();
    display.resume();
    await settle();
    assert.equal(display.state.phase, 'paused');
  } finally { controller.close(); display.close(); }
});
