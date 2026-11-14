# UBF Köln — Projector Countdown Timer v1.0

A small static website for Sunday-service welcome projection. The public display remains open on the projector while an operator privately starts, pauses, resumes, resets, or cancels a countdown on the same computer.

**Status:** Local implementation. **Not deployed**. Automated JavaScript, synchronization and repository path checks are included. See TEST_REPORT.md for the current results. Real-browser/physical-projector acceptance is still required.

## Start on Windows 11

1. Install Node.js 20+ (if not already installed).
2. Open a terminal in this project folder.
3. Run:

   ```powershell
   npm run serve
   ```

4. On the laptop, open **http://127.0.0.1:8765/control.html**.
5. Click **Projektionsfenster öffnen**. If the browser blocks the pop-up, open **http://127.0.0.1:8765/display.html** manually.
6. Connect the projector and set **Win + P → Erweitern** (Extend, not Duplicate).
7. Move the **display** browser window to the projector screen and press **F11** for full-screen mode. Leave that window open.
8. Keep the **control** window on the laptop. Choose 1/3/5/10 minutes or enter a custom duration, then press **Countdown starten**.

**Important:** Do not open the controller window on the projector. The display only shows the welcome slide or timer; the controller is a separate URL.

No `npm install` is needed to run the website. The server binds to `127.0.0.1` and does not publish the site to the internet.

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

**No browser PASS is claimed for this package yet.** In this environment, the bundled Playwright Chromium executable is unavailable. A separate attempt with the system Chromium launched, but its administrator policy blocked navigation to localhost (`ERR_BLOCKED_BY_ADMINISTRATOR`) before tests could exercise application behavior. Run the suite in an unrestricted environment or through the prepared GitHub CI after separate repository authorization.

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


## Prepared for the existing GitHub repository (not uploaded)

The public repository [`thiepn/ubf-welcome-timer`](https://github.com/thiepn/ubf-welcome-timer) **exists but was confirmed empty** during the 15 November 2026 pre-upload audit: no committed files or branches were returned. This package has **not** been uploaded or committed, and GitHub Pages has **not** been enabled or deployed by this project. The connected GitHub interface could not independently read the current Pages setting. See [`REPOSITORY_PREP.md`](./REPOSITORY_PREP.md) for the controlled import procedure and remaining acceptance gates.

- `.github/workflows/tests.yml` runs tests only; it has read-only permissions and **no deployment steps**.
- `.nojekyll` and relative links prepare the site for `/ubf-welcome-timer/` if GitHub Pages is separately authorized in the future.
- `npm test` validates static paths and matching 16:9 image dimensions.
- **Asset publication permission:** the user explicitly confirmed permission to publish the included Canva-derived assets in the public repository. This is a user attestation, not an independent third-party license audit; it does not grant an open-source license to other users. See [`ASSET_RIGHTS.md`](./ASSET_RIGHTS.md).
- Real-browser interaction and physical-projector acceptance remain outstanding; do not enable Pages or deploy without separate authorization.
