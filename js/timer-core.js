/** Pure, deterministic countdown state transitions. No browser APIs. */
export const SCHEMA_VERSION = 1;
export const STORAGE_KEY = 'ubf-koeln-projector-timer:state:v1';
export const CHANNEL_NAME = 'ubf-koeln-projector-timer:events:v1';
export const MIN_DURATION_MS = 10_000;
export const MAX_DURATION_MS = (99 * 60 + 59) * 1_000;
export const STALE_AFTER_MS = 12 * 60 * 60 * 1_000;
export const PHASES = Object.freeze(['welcome', 'running', 'paused', 'completed']);

export function initialState(now = Date.now(), revision = 0, sessionId = 'welcome') {
  return {
    schemaVersion: SCHEMA_VERSION,
    sessionId,
    revision,
    phase: 'welcome',
    durationMs: 5 * 60_000,
    remainingMs: 5 * 60_000,
    deadlineEpochMs: null,
    updatedAtEpochMs: now,
    createdAtEpochMs: now,
  };
}

export function validDuration(durationMs) {
  return Number.isInteger(durationMs) && durationMs >= MIN_DURATION_MS && durationMs <= MAX_DURATION_MS;
}

export function parseDuration(minutes, seconds) {
  if (!/^\d{1,2}$/.test(String(minutes).trim()) || !/^\d{1,2}$/.test(String(seconds).trim())) {
    return null;
  }
  const mm = Number(minutes);
  const ss = Number(seconds);
  if (ss > 59) return null;
  const duration = (mm * 60 + ss) * 1000;
  return validDuration(duration) ? duration : null;
}

export function isValidState(state) {
  if (!state || typeof state !== 'object' || Array.isArray(state)) return false;
  const int = (value) => Number.isSafeInteger(value);
  if (state.schemaVersion !== SCHEMA_VERSION || typeof state.sessionId !== 'string' || !state.sessionId || state.sessionId.length > 128) return false;
  if (!int(state.revision) || state.revision < 0 || !PHASES.includes(state.phase)) return false;
  if (!validDuration(state.durationMs) || !int(state.remainingMs) || state.remainingMs < 0 || state.remainingMs > state.durationMs) return false;
  if (!int(state.updatedAtEpochMs) || !int(state.createdAtEpochMs)) return false;
  if (state.phase === 'running') {
    if (!int(state.deadlineEpochMs)) return false;
  } else if (state.deadlineEpochMs !== null) return false;
  if (state.phase === 'completed' && state.remainingMs !== 0) return false;
  if (state.phase === 'welcome' && state.remainingMs !== state.durationMs) return false;
  return true;
}

export function isStale(state, now = Date.now()) {
  return now - state.updatedAtEpochMs >= STALE_AFTER_MS;
}

export function recoverState(raw, now = Date.now()) {
  if (!isValidState(raw)) return {state: initialState(now), issue: 'invalid'};
  if (isStale(raw, now)) return {state: initialState(now, raw.revision + 1, 'welcome'), issue: 'stale'};
  return {state: raw, issue: null};
}

export function remainingMs(state, now = Date.now()) {
  if (state.phase === 'completed') return 0;
  if (state.phase !== 'running') return state.remainingMs;
  return Math.max(0, Math.min(state.durationMs, state.deadlineEpochMs - now));
}

export function displayedSeconds(remaining) {
  return Math.ceil(Math.max(0, remaining) / 1000);
}

export function formatTime(remaining) {
  const seconds = displayedSeconds(remaining);
  return `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
}

export function progress(state, remaining = remainingMs(state)) {
  return Math.max(0, Math.min(1, 1 - remaining / state.durationMs));
}

function next(state, now, patch) {
  return {...state, ...patch, revision: state.revision + 1, updatedAtEpochMs: now};
}

export function startTimer(state, durationMs, now, sessionId) {
  if (!validDuration(durationMs)) throw new RangeError('Invalid timer duration.');
  if (state.phase === 'running') throw new Error('Cannot start while a countdown is running.');
  if (!sessionId) throw new Error('Session ID required.');
  return {
    schemaVersion: SCHEMA_VERSION,
    sessionId,
    revision: state.revision + 1,
    phase: 'running',
    durationMs,
    remainingMs: durationMs,
    deadlineEpochMs: now + durationMs,
    createdAtEpochMs: now,
    updatedAtEpochMs: now,
  };
}

export function pauseTimer(state, now, elapsedRemainingMs = remainingMs(state, now)) {
  if (state.phase !== 'running') throw new Error('Only a running countdown can be paused.');
  const frozen = Math.max(0, Math.min(state.durationMs, Math.ceil(elapsedRemainingMs)));
  return frozen === 0 ? completeTimer(state, now) : next(state, now, {phase:'paused', remainingMs:frozen, deadlineEpochMs:null});
}

export function resumeTimer(state, now) {
  if (state.phase !== 'paused') throw new Error('Only a paused countdown can be resumed.');
  return next(state, now, {phase:'running', deadlineEpochMs:now + state.remainingMs});
}

export function resetTimer(state, now) {
  if (state.phase === 'welcome') throw new Error('No countdown to reset.');
  return next(state, now, {phase:'paused', remainingMs:state.durationMs, deadlineEpochMs:null});
}

export function returnToWelcome(state, now) {
  return next(state, now, {phase:'welcome', remainingMs:state.durationMs, deadlineEpochMs:null});
}

export function completeTimer(state, now) {
  if (state.phase !== 'running') throw new Error('Only a running countdown can complete.');
  return next(state, now, {phase:'completed', remainingMs:0, deadlineEpochMs:null});
}

export function rebaseDeadline(state, now, remaining) {
  if (state.phase !== 'running') throw new Error('Only a running countdown can be rebased.');
  return next(state, now, {deadlineEpochMs:now + Math.ceil(Math.max(0, remaining))});
}
