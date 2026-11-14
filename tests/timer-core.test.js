import test from 'node:test';
import assert from 'node:assert/strict';
import {
  initialState, validDuration, parseDuration, isValidState, isStale, recoverState,
  remainingMs, formatTime, progress, startTimer, pauseTimer, resumeTimer,
  resetTimer, returnToWelcome, completeTimer, rebaseDeadline, STALE_AFTER_MS,
} from '../js/timer-core.js';

const baseTime = 1_800_000_000_000;
const initial = () => initialState(baseTime);
const running = (duration = 300000) => startTimer(initial(), duration, baseTime, 'test-1');

test('default state is original welcome with valid schema', () => {
  const state = initial();
  assert.equal(state.phase, 'welcome');
  assert.equal(state.revision, 0);
  assert.equal(state.deadlineEpochMs, null);
  assert.ok(isValidState(state));
});

test('duration boundaries and input validation', () => {
  assert.equal(parseDuration('0','10'), 10000);
  assert.equal(parseDuration('99','59'), 5999000);
  for (const pair of [['0','9'],['100','0'],['1','60'],['a','3'],['1','-1'],['1','1.5'],['','0']]) assert.equal(parseDuration(...pair), null);
  assert.equal(validDuration(60000), true);
  assert.equal(validDuration(1000), false);
  assert.equal(validDuration(Number.NaN), false);
});

test('presets progress proportional to total duration', () => {
  const five = running(300000);
  const ten = running(600000);
  assert.equal(progress(five,remainingMs(five,baseTime + 150000)), .5);
  assert.equal(progress(ten,remainingMs(ten,baseTime + 150000)), .25);
  assert.equal(progress(five,remainingMs(five,baseTime)),0);
  assert.equal(progress(five,remainingMs(five,baseTime + 500000)),1);
});

test('rounds seconds up, never displays prematurely completed', () => {
  assert.equal(formatTime(300000),'05:00');
  assert.equal(formatTime(299999),'05:00');
  assert.equal(formatTime(299000),'04:59');
  assert.equal(formatTime(1),'00:01');
  assert.equal(formatTime(0),'00:00');
  assert.equal(formatTime(-99),'00:00');
});

test('pause freezes time; resume preserves exact remainder', () => {
  const original = running();
  const paused = pauseTimer(original, baseTime+120123);
  assert.equal(paused.phase,'paused');
  assert.equal(paused.remainingMs,179877);
  assert.equal(remainingMs(paused,baseTime+500000),179877);
  const resumed = resumeTimer(paused,baseTime+300000);
  assert.equal(resumed.deadlineEpochMs,baseTime+479877);
  assert.equal(remainingMs(resumed,baseTime+310000),169877);
  assert.ok(isValidState(resumed));
});

test('reset pauses at original duration; return restores welcome', () => {
  const paused = pauseTimer(running(),baseTime+120000);
  const reset = resetTimer(paused,baseTime+140000);
  assert.equal(reset.phase,'paused');
  assert.equal(reset.remainingMs,300000);
  assert.equal(progress(reset),0);
  const welcome = returnToWelcome(reset,baseTime+200000);
  assert.equal(welcome.phase,'welcome');
  assert.equal(welcome.remainingMs,300000);
  assert.ok(isValidState(welcome));
});

test('completion remains full until the controller returns to welcome', () => {
  const completed = completeTimer(running(),baseTime+300000);
  assert.equal(completed.phase,'completed');
  assert.equal(completed.remainingMs,0);
  assert.equal(progress(completed),1);
  assert.equal(formatTime(remainingMs(completed)), '00:00');
  assert.throws(() => resumeTimer(completed, baseTime+301000));
});

test('early invalid commands do not modify existing state', () => {
  const state = running();
  assert.throws(() => startTimer(state,300000,baseTime+1000,'new'));
  assert.throws(() => resumeTimer(state,baseTime+1000));
  assert.throws(() => resetTimer(initial(),baseTime));
  assert.equal(state.phase,'running');
});

test('clock rebase preserves monotonic-derived remaining time', () => {
  const state = running();
  const rebased = rebaseDeadline(state,baseTime+60000,240000);
  assert.equal(rebased.deadlineEpochMs,baseTime+300000);
  assert.equal(rebased.revision, state.revision+1);
  assert.ok(isValidState(rebased));
});

test('refresh recovery preserves running deadline and paused remaining time', () => {
  const state = running();
  const restored = recoverState(JSON.parse(JSON.stringify(state)),baseTime+125000);
  assert.equal(restored.issue,null);
  assert.equal(remainingMs(restored.state,baseTime+125000),175000);
  const paused = pauseTimer(state,baseTime+125000);
  assert.equal(recoverState(paused,baseTime+130000).state.remainingMs,175000);
});

test('12 hour expiry returns welcome and increments revision', () => {
  const state = running();
  assert.equal(isStale(state,baseTime+STALE_AFTER_MS-1),false);
  const result = recoverState(state,baseTime+STALE_AFTER_MS);
  assert.equal(result.issue,'stale');
  assert.equal(result.state.phase,'welcome');
  assert.equal(result.state.revision,state.revision+1);
});

test('corruption and future incompatible versions safely fall back', () => {
  assert.equal(recoverState({foo:'bar'},baseTime).issue,'invalid');
  const future = {...running(),schemaVersion:2};
  assert.equal(recoverState(future,baseTime).state.phase,'welcome');
  const malformed = {...running(),remainingMs:800000};
  assert.equal(isValidState(malformed),false);
});

test('revisions increase for every command', () => {
  const a = running();
  const b = pauseTimer(a,baseTime+10000);
  const c = resumeTimer(b,baseTime+20000);
  const d = resetTimer(c,baseTime+30000);
  const e = returnToWelcome(d,baseTime+40000);
  assert.deepEqual([a,b,c,d,e].map(s=>s.revision),[1,2,3,4,5]);
});


test('system-clock adjustment can move wall-clock deadlines before session creation', () => {
  const original = running();
  const earlierWallClock = baseTime - 180_000;
  const adjusted = rebaseDeadline(original, earlierWallClock, 120_000);
  assert.equal(adjusted.updatedAtEpochMs, earlierWallClock);
  assert.ok(adjusted.deadlineEpochMs < original.createdAtEpochMs);
  assert.ok(isValidState(adjusted));
  assert.equal(remainingMs(adjusted,earlierWallClock),120_000);
});
