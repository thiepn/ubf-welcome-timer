import {CHANNEL_NAME, STORAGE_KEY, initialState, isValidState, recoverState} from './timer-core.js';

/** Controller writes timer state; displays are read-only timer consumers. */
export class TimerSync {
  constructor(role, {onState = () => {}, onPresence = () => {}, onIssue = () => {}} = {}) {
    this.role = role;
    this.onState = onState;
    this.onPresence = onPresence;
    this.onIssue = onIssue;
    this.windowId = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`;
    this.state = initialState();
    this.channel = null;
    this.storageAvailable = true;
    this.peerLastSeen = new Map();
    this.heartbeat = null;
    this.storageListener = this.handleStorage.bind(this);
    this.channelListener = this.handleMessage.bind(this);
    this.visibilityListener = () => this.requestSnapshot();
  }

  readStorage() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw === null) return {state: initialState(), issue: null, empty: true};
      const result = recoverState(JSON.parse(raw), Date.now());
      return {...result, empty: false};
    } catch (error) {
      if (error instanceof SyntaxError) return {state: initialState(), issue: 'invalid', empty: false};
      this.storageAvailable = false;
      this.onIssue('Der Browser blockiert die Speicherung. Wiederherstellung nach Neuladen ist nicht garantiert.');
      return {state: initialState(), issue: 'blocked', empty: true};
    }
  }

  start() {
    const {state, issue, empty} = this.readStorage();
    this.state = state;
    if (issue === 'invalid') this.onIssue('Ungültige gespeicherte Daten; die Willkommensansicht wurde wiederhergestellt.');
    if (issue === 'stale') this.onIssue('Alter Timer verworfen; Willkommensansicht wiederhergestellt.');
    if (this.role === 'control' && this.storageAvailable && (issue === 'stale' || issue === 'invalid')) {
      this.write(state);
    }
    // An empty store intentionally stays empty until an operator starts a timer.
    if (typeof BroadcastChannel !== 'undefined') {
      try {
        this.channel = new BroadcastChannel(CHANNEL_NAME);
        this.channel.addEventListener('message', this.channelListener);
      } catch { this.channel = null; }
    }
    addEventListener('storage', this.storageListener);
    addEventListener('pageshow', this.visibilityListener);
    addEventListener('visibilitychange', this.visibilityListener);
    this.heartbeat = setInterval(() => this.announce(), 1500);
    this.announce();
    this.requestSnapshot();
    this.onState(this.state, {initial:true, empty});
    this.onPresence(this.peerLastSeen, Boolean(this.channel));
  }

  announce() {
    this.send({type:'presence', role:this.role});
    this.clearExpiredPresence();
  }

  clearExpiredPresence() {
    const now = Date.now();
    for (const [id, peer] of this.peerLastSeen) if (now - peer.seenAt > 4500) this.peerLastSeen.delete(id);
    this.onPresence(this.peerLastSeen, Boolean(this.channel));
  }

  send(data) {
    try { this.channel?.postMessage({...data, sender:this.windowId}); } catch { /* localStorage remains fallback */ }
  }

  requestSnapshot() {
    this.send({type:'request-state'});
    const stored = this.readStorage();
    // Do not overwrite a newer, in-memory snapshot with missing or older storage.
    if (!stored.empty && stored.issue === null) this.accept(stored.state);
  }

  handleStorage(event) {
    if (event.key !== STORAGE_KEY) return;
    if (event.newValue === null) {
      // Ignore deletion; controller will decide how to repair persistence.
      this.onIssue('Gespeicherter Zustand wurde extern entfernt.');
      return;
    }
    try { this.accept(JSON.parse(event.newValue)); } catch { this.onIssue('Unlesbare Synchronisierungsdaten wurden ignoriert.'); }
  }

  handleMessage(event) {
    const msg = event.data;
    if (!msg || typeof msg !== 'object' || msg.sender === this.windowId) return;
    if (msg.type === 'presence') {
      if (msg.role !== 'display' && msg.role !== 'control') return;
      this.peerLastSeen.set(msg.sender, {role: msg.role, seenAt: Date.now()});
      this.onPresence(this.peerLastSeen, true);
    } else if (msg.type === 'request-state' && this.role === 'control') {
      this.send({type:'snapshot', state:this.state});
    } else if (msg.type === 'snapshot' && this.role === 'display') {
      this.accept(msg.state);
    }
  }

  accept(incoming) {
    if (!isValidState(incoming)) return;
    if (incoming.revision <= this.state.revision) return;
    const recovered = recoverState(incoming, Date.now());
    // A stale state cannot resurrect a timer on display refresh.
    if (recovered.issue !== null) {
      if (recovered.issue === 'stale' && this.role === 'display') {
        this.state = recovered.state;
        this.onState(this.state, {stale:true});
      }
      return;
    }
    this.state = incoming;
    this.onState(this.state, {initial:false});
  }

  write(state) {
    if (this.role !== 'control') throw new Error('Only controller can issue timer commands.');
    if (!isValidState(state)) throw new Error('Refusing invalid timer state.');
    this.state = state;
    if (this.storageAvailable) {
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }
      catch {
        this.storageAvailable = false;
        this.onIssue('Speichern nicht möglich. Der Timer läuft, aber Neuladen kann den Zustand verlieren.');
      }
    }
    this.send({type:'snapshot', state});
    this.onState(this.state, {initial:false});
  }

  close() {
    if (this.heartbeat) clearInterval(this.heartbeat);
    removeEventListener('storage', this.storageListener);
    removeEventListener('pageshow', this.visibilityListener);
    removeEventListener('visibilitychange', this.visibilityListener);
    this.channel?.close();
  }
}
