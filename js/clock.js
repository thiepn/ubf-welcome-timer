import {remainingMs} from './timer-core.js';

/** A monotonic anchor per snapshot, avoiding setInterval drift and wall-clock jumps. */
export class TimerClock {
  constructor() { this.identity = null; this.endMono = null; }

  useState(state) {
    this.identity = `${state.sessionId}:${state.revision}`;
    this.endMono = state.phase === 'running'
      ? performance.now() + remainingMs(state, Date.now())
      : null;
  }

  remaining(state) {
    if (state.phase !== 'running') return remainingMs(state);
    if (this.identity !== `${state.sessionId}:${state.revision}` || this.endMono === null) this.useState(state);
    return Math.max(0, Math.min(state.durationMs, this.endMono - performance.now()));
  }

  drift(state) {
    if (state.phase !== 'running') return 0;
    const estimatedDeadline = Date.now() + this.remaining(state);
    return estimatedDeadline - state.deadlineEpochMs;
  }
}
