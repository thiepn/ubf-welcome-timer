import {
  parseDuration, formatTime, progress, startTimer, pauseTimer, resumeTimer,
  resetTimer, returnToWelcome, completeTimer, rebaseDeadline,
} from './timer-core.js';
import {TimerClock} from './clock.js';
import {TimerSync} from './sync.js';

const $ = (selector) => document.querySelector(selector);
const time = $('#current-time');
const caption = $('#time-caption');
const phaseBadge = $('#status-badge');
const track = $('#track-progress');
const preview = $('#mini-preview');
const previewTime = $('#preview-time');
const previewRing = $('#preview-ring-fill');
const inputMinutes = $('#minutes');
const inputSeconds = $('#seconds');
const inputError = $('#input-error');
const durationControls = $('#duration-controls');
const startButton = $('#start');
const pauseButton = $('#pause');
const resumeButton = $('#resume');
const resetButton = $('#reset');
const welcomeButton = $('#welcome');
const connection = $('#connection-status');
const connectionDot = $('#connection-dot');
const message = $('#system-message');
const presets = [...document.querySelectorAll('[data-duration]')];
const clock = new TimerClock();
let state;
let lockedByOtherController = false;
// The Web Locks API prevents commands during the BroadcastChannel startup race.
// In older browsers, retain the existing presence-based fallback.
const exclusiveControlSupported = Boolean(globalThis.navigator?.locks?.request);
let controlsLeaseHeld = !exclusiveControlSupported;
let acquiringControl = false;
let releaseControls = null;
let controlClosed = false;
let selectedDuration = 300000;
let lastWarning = '';
let lastClockReview = 0;

const statusLabels = {welcome:'Willkommen',running:'Läuft',paused:'Pausiert',completed:'Beendet'};
const descriptionLabels = {welcome:'Bereit',running:'Countdown läuft',paused:'Countdown pausiert',completed:'Countdown beendet'};

function setWarning(text) {
  if (!text) return;
  lastWarning = text;
  message.textContent = text;
  message.hidden = false;
}

function clearInputError() { inputError.hidden = true; }
function durationFromFields() {
  const result = parseDuration(inputMinutes.value, inputSeconds.value);
  inputError.hidden = result !== null;
  return result;
}
function selectDuration(duration) {
  selectedDuration = duration;
  inputMinutes.value = Math.floor(duration / 60000);
  inputSeconds.value = Math.floor((duration % 60000) / 1000);
  clearInputError();
  updatePresetButtons();
  render();
}
function updatePresetButtons() {
  const candidate = parseDuration(inputMinutes.value, inputSeconds.value);
  for (const button of presets) {
    const selected = candidate === Number(button.dataset.duration);
    button.classList.toggle('active', selected);
    button.setAttribute('aria-pressed', String(selected));
  }
}

function render() {
  if (!state) return;
  const remaining = clock.remaining(state);
  const displayRemaining = state.phase === 'welcome' ? selectedDuration : remaining;
  time.textContent = formatTime(displayRemaining);
  previewTime.textContent = formatTime(displayRemaining);
  phaseBadge.textContent = statusLabels[state.phase];
  phaseBadge.dataset.phase = state.phase;
  caption.textContent = descriptionLabels[state.phase];
  const percent = state.phase === 'welcome' ? 0 : progress(state, remaining);
  track.style.width = `${100 * percent}%`;
  previewRing.style.strokeDashoffset = String(100 * (1 - percent));
  preview.classList.toggle('active', state.phase !== 'welcome');

  const active = state.phase === 'running';
  const paused = state.phase === 'paused';
  const welcome = state.phase === 'welcome';
  const complete = state.phase === 'completed';
  const editable = welcome || complete;
  for (const input of [inputMinutes, inputSeconds, ...presets]) input.disabled = !editable || lockedByOtherController;
  startButton.hidden = !editable;
  startButton.disabled = lockedByOtherController;
  pauseButton.hidden = !active;
  pauseButton.disabled = lockedByOtherController;
  resumeButton.hidden = !paused;
  resumeButton.disabled = lockedByOtherController;
  resetButton.disabled = welcome || lockedByOtherController;
  welcomeButton.disabled = welcome || lockedByOtherController;
  durationControls.classList.toggle('locked', !editable);
}

function onState(next, {initial = false} = {}) {
  state = next;
  clock.useState(next);
  if (initial) selectDuration(next.durationMs);
  render();
}

function onPresence(peers, channelAvailable) {
  const now = Date.now();
  const others = [...peers.values()].filter(p => now - p.seenAt <= 4500);
  const displays = others.filter(p => p.role === 'display');
  const controllers = others.filter(p => p.role === 'control');
  const awaitingLease = exclusiveControlSupported && !controlsLeaseHeld;
  lockedByOtherController = controllers.length > 0 || awaitingLease;
  if (!channelAvailable) {
    connection.textContent = 'Verbindungsstatus nicht nachweisbar; lokale Synchronisierung kann weiterhin funktionieren.';
    connectionDot.classList.remove('connected');
  } else {
    connection.textContent = displays.length > 0
      ? `${displays.length} Projektionsfenster verbunden`
      : 'Kein Projektionsfenster erkannt';
    connectionDot.classList.toggle('connected', displays.length > 0);
  }
  if (controllers.length > 0) {
    setWarning('Mehrere Steuerfenster erkannt. Bitte alle bis auf eines schließen; Timeraktionen sind vorübergehend gesperrt.');
  } else if (awaitingLease) {
    connection.textContent = 'Warte auf exklusiven Steuerzugriff.';
    connectionDot.classList.remove('connected');
  } else if (lastWarning.includes('Mehrere Steuerfenster')) {
    lastWarning = '';
    message.hidden = true;
  }
  render();
}

const sync = new TimerSync('control', {onState, onPresence, onIssue:setWarning});
sync.start();

function tryAcquireControlLease() {
  if (!exclusiveControlSupported || controlsLeaseHeld || acquiringControl || controlClosed) return;
  acquiringControl = true;
  void navigator.locks.request('ubf-koeln-projector-timer:single-controller:v1',
    {mode:'exclusive', ifAvailable:true}, async (lock) => {
      acquiringControl = false;
      if (!lock || controlClosed) return;
      controlsLeaseHeld = true;
      onPresence(sync.peerLastSeen, Boolean(sync.channel));
      await new Promise(resolve => { releaseControls = resolve; });
      controlsLeaseHeld = false;
      releaseControls = null;
      if (!controlClosed) onPresence(sync.peerLastSeen, Boolean(sync.channel));
    }).catch(() => {
      acquiringControl = false;
      onPresence(sync.peerLastSeen, Boolean(sync.channel));
      setWarning('Exklusiver Steuerzugriff ist derzeit nicht verfügbar.');
    });
}
tryAcquireControlLease();
let ownershipInterval = setInterval(tryAcquireControlLease, 1500);

function command(operation) {
  if (lockedByOtherController) return;
  // Check persisted state first in case a storage event has not been processed.
  sync.requestSnapshot();
  try {
    const now = Date.now();
    const next = operation(now);
    if (next) sync.write(next);
  } catch (error) { setWarning(`Aktion nicht möglich: ${error.message}`); }
}

for (const button of presets) {
  button.addEventListener('click', () => {
    if (button.disabled) return;
    selectDuration(Number(button.dataset.duration));
  });
}
for (const input of [inputMinutes, inputSeconds]) {
  input.addEventListener('input', () => {
    selectedDuration = parseDuration(inputMinutes.value, inputSeconds.value) ?? selectedDuration;
    clearInputError();
    updatePresetButtons();
    render();
  });
}

startButton.addEventListener('click', () => {
  const duration = durationFromFields();
  if (duration === null) return;
  selectedDuration = duration;
  command((now) => startTimer(state, duration, now, crypto.randomUUID?.() || String(now)));
});
pauseButton.addEventListener('click', () => command((now) => pauseTimer(state, now, clock.remaining(state))));
resumeButton.addEventListener('click', () => command((now) => resumeTimer(state, now)));
resetButton.addEventListener('click', () => command((now) => resetTimer(state, now)));
welcomeButton.addEventListener('click', () => command((now) => returnToWelcome(state, now)));

$('#open-display').addEventListener('click', () => {
  if (globalThis.__TAURI__?.core?.invoke) return; // Native projector is owned by Rust.
  const popup = window.open(new URL('./display.html', location.href), 'ubf-koeln-projector');
  if (!popup) setWarning('Pop-up blockiert. Projektionsfenster über display.html direkt öffnen.');
  else popup.focus();
});

function tick() {
  if (!state) return;
  if (state.phase === 'running') {
    const remaining = clock.remaining(state);
    if (remaining <= 0 && !lockedByOtherController) {
      command((now) => completeTimer(state, now));
    } else if (performance.now() - lastClockReview > 2000) {
      lastClockReview = performance.now();
      if (Math.abs(clock.drift(state)) >= 1500 && remaining > 0 && !lockedByOtherController) {
        command((now) => rebaseDeadline(state, now, remaining));
        setWarning('Die Systemuhr wurde geändert. Der laufende Countdown wurde auf die monotone Zeit abgestimmt.');
      }
    }
  }
  render();
}
setInterval(tick, 100);
tick();
addEventListener('pagehide', () => {
  controlClosed = true;
  // A suspended page must never retain an enabled operator UI without its lock.
  lockedByOtherController = true;
  controlsLeaseHeld = false;
  clearInterval(ownershipInterval);
  releaseControls?.();
  sync.close();
  render();
});
addEventListener('pageshow', (event) => {
  if (!event.persisted || !controlClosed) return;
  controlClosed = false;
  controlsLeaseHeld = !exclusiveControlSupported;
  sync.resume();
  tryAcquireControlLease();
  ownershipInterval = setInterval(tryAcquireControlLease, 1500);
});
