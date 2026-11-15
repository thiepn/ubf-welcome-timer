# UBF Köln — Projector Countdown Timer v1.0

A small static website for Sunday-service welcome projection. The public display remains open on the projector while an operator privately starts, pauses, resumes, resets, or cancels a countdown on the same computer.

**Status (15 November 2026):** Public GitHub source on `main`, but **GitHub Pages remains disabled and no release is published**. The merged baseline `d15cb451b5f65528a7e88541d417cb9d49ddbcb2` passed **23 Node and 14 Chromium automated tests** (Actions `43689422924`). **Windows 11 and physical projector acceptance are still NOT TESTED.** This branch also prepares a local offline-first Windows launcher; its separate CI results must be checked on the exact PR HEAD.

## Start on Windows 11 (offline-first)

1. Install **Node.js 20+** before the service, then completely extract the project ZIP to a local folder (including `assets/` and `scripts/`).
2. Double-click **`Start-Timer.cmd`** in the extracted root. Keep its black terminal window open: it starts the server only on `127.0.0.1:8765` and opens the controller in the default browser.
3. If no browser opens automatically, go to **http://127.0.0.1:8765/control.html**.
4. Connect the projector, select **Win + P → Erweitern**, then select **Projektionsfenster öffnen**. Move that separate window to the projector and press **F11**.
5. Keep the controller window on the laptop, and run the 10-second rehearsal before real use.

**For complete operator instructions, errors, fallback and real-projector signoff, read [`RUNBOOK_WINDOWS.md`](./RUNBOOK_WINDOWS.md) (German).** No `npm install` or internet access is required during local operation; Node.js must already be installed. Do not use `file://` to open the HTML directly or mix `localhost` and `127.0.0.1`: the two windows must share the exact origin and browser profile. The connected-window indicator is **not** a physical-projector detector.

The original terminal workflow still works: `npm run serve`, then open both local URLs. The offline-first launcher does not change any runtime timer behavior or make a GitHub Pages deployment.

## Controls

| Control | Behavior |
|---|---|
| Presets | 1, 3, 5, 10 minutes; selection only, does not start the timer |
| Custom | `00:10` through `99:59` |
| Countdown starten | Starts from the selected duration; welcome text crossfades to timer |
| Pausieren | Freezes the digital time and blue progress ring |
| Fortsetzen | Continues from the frozen remaining duration |
| Zurücksetzen | Restores the full duration but remains paused on the timer view |
| Willkommensfolie anzeigen | Returns to the unmodified original welcome slide |
| Completion | Stops at `00:00` and a fully blue ring until the operator changes the state |

The blue ring begins at 12 o'clock, fills clockwise, and is based on elapsed time / selected duration.

## Original Canva assets (provided, installed)

The two actual Canva exports supplied on 14 November 2026 are included, replacing both provisional assets:

- `assets/welcome.png`: complete **2048 × 1152** welcome slide. Idle projection uses this image directly.
- `assets/background-clean.png`: matching **2048 × 1152** slide with the main title and subtitle removed, leaving the circle, street photo, logo, and corner illustrations intact.
- `reference/ubf-logo-source.png`: additional UBF-logo reference supplied separately. **Not rendered**: the logo is already embedded in both slides, and adding it again would duplicate the branding.

The image pair was visually inspected and compared pixel by pixel. Differences above 1 RGB channel value are confined to the headline/subtitle region; faint 1-value differences elsewhere are consistent with export rounding. Both images have matching dimensions and geometry. See `ASSET_VERIFICATION.md`.

The timer ring uses the original Canva headline blue: **`#0F5EAB`**. Its SVG position was calibrated against the existing slide layout; the actual extended-display/projector appearance still needs manual acceptance.

If Canva assets are revised later, export both images at the **same 16:9 dimensions**, preserving all non-text elements and their positions. The standalone logo is optional source material, not a replacement for the embedded branding.

## Internals

- No frontend framework, external CDN, database, WebSocket, or hosted backend.
- `display.html`: fullscreen public presentation; **never writes authoritative timer state**.
- `control.html`: controller; only window that may write timer state.
- `BroadcastChannel`: same-origin/same-profile tab synchronization.
- `localStorage`: state persistence, with `storage` event fallback across tabs.
- `performance.now()`: monotonic timer updates during an uninterrupted page session.
- Persisted wall-clock deadline: countdown reconstruction after refresh or browser restart.
- A snapshot older than **12 hours since its last update** is discarded and replaced with the welcome slide.
- Duplicate controller windows detect each other and temporarily disable timer actions until only one remains (where BroadcastChannel is available).

**Limitations:** Both windows must share the same site origin and browser storage partition. Browsers in private/incognito windows, different profiles, or different physical devices do **not** automatically synchronize. System clock changes during a *closed* browser can affect reconstructed time. Storage restrictions can disable refresh recovery, and the controller displays a warning. Full offline *reopening* is not supported in v1; an already loaded timer continues without a network connection.

## Tests

### Unit and same-origin simulation

```powershell
npm test
```

Uses Node.js built-in test runner. No dependency install is needed. Covers timing, transitions, validation, refresh persistence, stale state, revision ordering, and simulated BroadcastChannel synchronization.

### Real Chromium browser tests (requires Playwright for Python)

```powershell
python -m pip install -r requirements-test.txt
python -m playwright install chromium
npm run test:browser
```

The test suite starts its own local test server on `127.0.0.1:18765` and checks browser behavior, including open-window synchronization, pause/resume, reset, refresh recovery, a full 10-second countdown, custom validation, and offline-after-load behavior.

**Current GitHub CI baseline:** 23 Node checks and 14 Chromium browser checks passed on `main` at `d15cb451` (Actions `43689422924`). Earlier local environment restrictions in `TEST_REPORT.md` remain historical evidence, not the current CI result. Physical-projector tests have not been performed.

### Before Sunday use — manual acceptance

- [x] Replace reconstructed `background-clean.png` with the supplied Canva export.
- [x] Preserve the supplied complete Canva image byte-for-byte as the idle slide (projector visual acceptance outstanding).
- [ ] Verify ring and `MM:SS` text align within the white circle.
- [ ] Test at the actual projector resolution and brightness.
- [ ] Verify `Win + P → Erweitern` and `F11` fullscreen on the projector.
- [ ] Start the countdown while the welcome slide is already projected; confirm no window-switch flash.
- [ ] Pause, resume, reset, return; confirm only laptop displays controls.
- [ ] Refresh *both* browser pages during an active countdown.
- [ ] Disconnect internet after both pages have loaded; confirm continued countdown.
- [ ] Leave the display on `00:00`, then return explicitly to the welcome slide.

## Development scope

Only the six requested v1 features are implemented: welcome slide, presets, custom countdown, pause/resume/reset, start transition, and refresh recovery. Phone remote, automatic schedules, custom announcements, accounts, and cloud synchronization are not included. Nothing has been deployed.


## Repository and release policy

- Source is committed publicly at [`thiepn/ubf-welcome-timer`](https://github.com/thiepn/ubf-welcome-timer); the repository is **not** empty. The previous `REPOSITORY_PREP.md` and initial test report record **historical pre-upload evidence**, not the current repository state.
- `.github/workflows/tests.yml` performs tests only; no deployment steps or Pages permissions. GitHub Pages remains disabled; publishing requires separate authorization and independent acceptance.
- The user attested permission to publish the original Canva-derived PNGs; no independent third-party license audit or downstream reuse license is claimed (see `ASSET_RIGHTS.md`).
- Full local Windows launcher acceptance requires a Windows runner smoke test; actual Windows 11 dual-screen, projector image fidelity and service rehearsal remain **NOT TESTED** until performed on the real equipment.
