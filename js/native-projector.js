// Optional native controller integration. The browser build stays unchanged:
 // on web hosts the Tauri global is absent and this module does nothing.
const native = globalThis.__TAURI__?.core;
if (native?.invoke) {
  const invoke = native.invoke;
  const openButton = document.querySelector('#open-display');
  const guide = document.querySelector('.guide');
  const caption = document.querySelector('.preview-caption');
  const panel = document.createElement('section');
  panel.className = 'native-projection';
  panel.setAttribute('aria-label', 'Native Beamersteuerung');
  panel.innerHTML =
    '<div class="native-status-heading"><span class="native-status-dot" aria-hidden="true"></span>' +
    '<span class="native-status-label">NATIVER BEAMER</span></div>' +
    '<p id="native-projector-state" role="status" aria-live="polite">Bildschirme werden geprüft …</p>' +
    '<label id="native-monitor-label" hidden>Beamer auswählen' +
    '<select id="native-monitor"></select></label>' +
    '<div class="native-projector-actions"></div>' +
    '<button type="button" id="native-projector-release" hidden>Beamer freigeben</button>' +
    '<p class="native-projection-note">Bei Windows muss der Laptop als Hauptanzeige eingerichtet sein. ' +
    'Win + P → Erweitern.</p>';
  const preview = document.querySelector('.mini-preview');
  preview.parentNode.insertBefore(panel, preview);
  const actionGroup = panel.querySelector('.native-projector-actions');
  const release = panel.querySelector('#native-projector-release');
  openButton.classList.remove('outline', 'top-action');
  openButton.classList.add('native-open');
  actionGroup.append(openButton, release);
  guide.hidden = true;
  caption.textContent = 'Vorschau · Die echte Projektion läuft auf dem zweiten Windows-Bildschirm.';
  const state = panel.querySelector('#native-projector-state');
  const selectorLabel = panel.querySelector('#native-monitor-label');
  const selector = panel.querySelector('#native-monitor');
  const releaseButton = panel.querySelector('#native-projector-release');
  let busy = false;
  let targets = [];
  let active = false;
  // Discard asynchronous monitor polls started before a newer operator
  // action, or superseded by a later poll. A stale "inactive" result must
  // never hide Beamer freigeben after the projector has opened.
  let statusRevision = 0;

  function explainError(error) {
    return error instanceof Error ? error.message : String(error);
  }

  function render() {
    panel.dataset.status = busy ? 'busy' : active ? 'active' : targets.length ? 'ready' : 'missing';
    selectorLabel.hidden = targets.length <= 1;
    releaseButton.hidden = !active;
    releaseButton.disabled = busy;
    openButton.textContent = active ? 'Projektion läuft' : 'Auf Beamer projizieren';
    openButton.disabled = busy || active || targets.length === 0;
    if (active) {
      state.textContent = 'Projektionsfenster auf externem Bildschirm aktiv. ' +
        'PowerPoint/Canva separat bereithalten: „Beamer freigeben“ schließt nur das Timerbild. ' +
        'Die nächste Präsentation startet nicht automatisch.';
    } else if (!targets.length) {
      state.textContent = 'Kein erweiterter Beamer erkannt. Win + P → Erweitern prüfen.';
    } else if (targets.length > 1) {
      state.textContent = 'Mehrere externe Monitore erkannt. Beamer vor dem Start auswählen.';
    } else {
      state.textContent = 'Externer Bildschirm bereit. Ein Klick startet die Vollbildprojektion.';
    }
  }

  async function refresh() {
    if (busy) return;
    const revision = ++statusRevision;
    try {
      const [newTargets, isActive] = await Promise.all([
        invoke('list_projector_targets'),
        invoke('projector_status'),
      ]);
      // The native result may arrive after open/release or a newer refresh.
      // Ignore it rather than reversing the operator's successful action.
      if (busy || revision !== statusRevision) return;
      const selected = selector.value;
      targets = newTargets;
      active = isActive;
      selector.replaceChildren();
      for (const target of targets) {
        const option = document.createElement('option');
        option.value = String(target.id);
        option.textContent = target.name + ' · ' + target.width + ' × ' + target.height;
        selector.append(option);
      }
      if (targets.some(target => String(target.id) === selected)) selector.value = selected;
      render();
    } catch (error) {
      if (busy || revision !== statusRevision) return;
      panel.dataset.status = 'error';
      openButton.disabled = true;
      releaseButton.disabled = true;
      state.textContent = 'Windows-Beamerprüfung fehlgeschlagen: ' + explainError(error);
    }
  }

  openButton.addEventListener('click', async () => {
    if (busy || active || !targets.length) return;
    ++statusRevision; // Invalidate any in-flight monitor/status refresh.
    busy = true;
    render();
    try {
      // Send the exact screen identity from the last visible list. If the
      // layout changes before Rust opens it, refuse instead of redirecting.
      const monitorKey = targets.length > 1 ? selector.value : targets[0].id;
      await invoke('open_projector', {monitorKey});
      await refreshAfterAction();
    } catch (error) {
      panel.dataset.status = 'error';
      state.textContent = 'Projektion nicht gestartet: ' + explainError(error);
    } finally {
      busy = false;
      // Preserve a useful error instead of immediately overwriting it.
      openButton.disabled = active || !targets.length;
      releaseButton.disabled = false;
    }
  });

  releaseButton.addEventListener('click', async () => {
    if (busy || !active) return;
    ++statusRevision; // Invalidate any in-flight monitor/status refresh.
    busy = true;
    releaseButton.disabled = true;
    try {
      await invoke('release_projector');
      await refreshAfterAction();
    } catch (error) {
      panel.dataset.status = 'error';
      state.textContent = 'Beamer konnte nicht freigegeben werden: ' + explainError(error);
    } finally {
      busy = false;
      releaseButton.disabled = false;
    }
  });

  async function refreshAfterAction() {
    // Do not call refresh() while busy; fetch the actual native state first.
    active = await invoke('projector_status');
    busy = false;
    render();
  }

  void refresh();
  window.addEventListener('focus', () => { void refresh(); });
  setInterval(() => { void refresh(); }, 3000);
}
