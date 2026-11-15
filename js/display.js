import {TimerSync} from './sync.js';
import {TimerClock} from './clock.js';
import {formatTime, progress} from './timer-core.js';

const stage = document.querySelector('#stage');
const countdown = document.querySelector('#countdown');
const numbers = document.querySelector('#timer-numbers');
const ring = document.querySelector('#progress-ring');
const accessibleStatus = document.querySelector('#accessible-status');
const clock = new TimerClock();
let state = null;
let lastPhase = null;

function receiveState(next) {
  state = next;
  clock.useState(next);
  const hasTimer = next.phase !== 'welcome';
  stage.classList.toggle('is-timer', hasTimer);
  countdown.setAttribute('aria-hidden', String(!hasTimer));
  if (lastPhase !== next.phase) {
    const statuses = {
      welcome: 'Willkommen zum Gottesdienst.',
      running: 'Countdown läuft.',
      paused: 'Countdown pausiert.',
      completed: 'Countdown beendet.',
    };
    accessibleStatus.textContent = statuses[next.phase];
    lastPhase = next.phase;
  }
  render();
}

function render() {
  if (!state) return;
  const remaining = clock.remaining(state);
  numbers.textContent = formatTime(remaining);
  ring.style.strokeDashoffset = String(100 * (1 - progress(state, remaining)));
  // This is intentional: the display never writes an authoritative completion
  // snapshot, yet it visibly reaches 00:00 even if the controller is hidden.
}

const sync = new TimerSync('display', {onState:receiveState});
sync.start();
document.body.classList.remove('loading');
function frame() { render(); requestAnimationFrame(frame); }
requestAnimationFrame(frame);
addEventListener('pagehide', () => sync.close());
addEventListener('pageshow', (event) => {
  if (event.persisted) sync.resume();
});
