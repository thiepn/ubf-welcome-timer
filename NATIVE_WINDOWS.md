# UBF Köln Timer — native Windows projector candidate

Status: **Draft development only.** No installer, deployment, release or physical projector acceptance is claimed. The browser website and Start-Timer.cmd remain usable without the desktop wrapper.

## Purpose

The native Tauri 2 shell packages the existing control.html and display.html locally. It does **not** start an HTTP server, change the Canva PNG files, or rewrite the timer, persistence, recovery or synchronization modules.

On Windows 11 with an extended external display:

1. Configure **Win + P → Erweitern**, with the laptop's own panel set as the **main** Windows display.
2. Run the Tauri app. Its controller opens on the Windows primary display.
3. Click **Auf Beamer projizieren**. Exactly one secondary monitor is selected automatically. If multiple external monitors exist, explicitly choose the target.
4. The original display.html opens directly as a separate borderless fullscreen window on that monitor; the controller remains on the primary screen.
5. When PowerPoint/Canva or other Sunday-service presentation needs the projector, click **Beamer freigeben**. This closes only the projector window; it does **not** close the controller, stop the timer or launch the next presentation.

No F11, dragging a window or browser popup should be necessary. A native fullscreen placement must still be physically verified on the church's actual Windows/projector setup.

## Build / development

Prerequisites: Windows 11, Rust stable MSVC toolchain and Microsoft C++ Build Tools; Tauri 2 uses installed Edge WebView2. Node.js 20+ is needed to **build**, not to run the compiled app.

From the repository root:

1. Run: npm run build:desktop
2. Run: cargo run --manifest-path src-tauri/Cargo.toml
3. Run: npm test
4. Run: cargo test --manifest-path src-tauri/Cargo.toml

Tauri configuration is in src-tauri/tauri.conf.json. The staged frontend is dist/desktop/ (ignored); only index.html, control.html, display.html, css/, js/, and assets/ are bundled. The original PNG bytes are checked by tests. The bundle flag is intentionally disabled until installation/release is separately approved.

## Projection safety

- If no secondary monitor is detected, native projection refuses to start. Duplicate/mirrored monitor geometry is rejected. Never silently put the projector display on the primary screen.
- Multiple external monitors require an explicit choice. The selected display is passed as a snapshot-bound identity (name and physical rectangle), not a list index. If Windows reorders, removes or resizes the chosen screen before projection, the command refuses instead of redirecting to another display.
- After showing the native window, its actual fullscreen state and current monitor are rechecked against the selected target. Each status poll fails closed if Windows moved it elsewhere; the presence of a WebView2 window alone does not certify projection.
- Native projection commands reject calls from any window except controller. The projector has no declared Tauri capabilities and the existing JS display remains read-only.
- When Windows migrates the projection window onto the primary monitor after disconnection, the native status poll closes it.
- Controller and projector are packaged in the same Tauri app origin/profile; the existing BroadcastChannel and localStorage code is reused, not replaced. Cross-window synchronization, pause/resume and reopening **passed on Windows Server 2022 CI**. The actual church Windows 11/projector setup remains **NOT TESTED**.
- The Windows **primary** display is assumed to be the laptop. There is no reliable built-in-panel inference in this initial version: changing primary display to the projector would put the controller there.
- Closing the projector window frees that monitor for the next application. The operating system and the next presentation program decide what becomes visible next. The Tauri app does not automatically start Canva or PowerPoint.
- The existing browser-only offline launcher remains the rollback path (Start-Timer.cmd and RUNBOOK_WINDOWS.md).

## Outstanding acceptance (not automatically certified)

- Actual Windows 11 extended-screen window placement (including projector to the left/negative coordinates).
- Pixel-accurate 16:9 Canva welcome and ring geometry at physical projector resolution.
- Same-origin WebView2 controller/display state propagation on the **actual church Windows 11 laptop** (the Windows Server 2022 two-window CI smoke passed, but the physical device has not been tested).
- Monitor unplug/replug, emergency Beamer freigeben, and no laptop takeover.
- PowerPoint/Canva live takeover without a desktop flash at the worship handoff.
- Full Sunday rehearsal with sleep/notification/network handling.

Do not distribute or use for a live Sunday service until these checks pass.

## Additional native CI acceptance fixture

The draft PR includes a **Windows Server 2022 real WebView2** two-window smoke
(`src-tauri/src/bin/webview2_smoke.rs`). It starts the actual controller and
display HTML pages in two Tauri WebViews on a single monitor, starts a 3-minute
timer through the controller, then requires the display WebView to observe the
running countdown, shared localStorage state and loaded Canva image. The test
process must report a positive result within 90 seconds or CI fails.

This is an isolated **test-only binary**, not the desktop app, not an installer,
and does not attempt to detect or occupy any physical projector. Even a passing
result proves only WebView2 propagation in the CI environment. Fullscreen
placement, hotplug, and PowerPoint handoff on the actual Windows 11 church
equipment remain **NOT TESTED**.

## Fullscreen coverage / unplug containment candidate

The native projector now requires the actual WebView content rectangle to match
the selected external monitor's *physical* pixel rectangle (within 2px),
in addition to fullscreen state and monitor identity. This rejects taskbar-sized
maximized windows and DPI/logical-pixel mistakes. Placement is rechecked for
up to 1.2 seconds because Windows may asynchronously position fullscreen
windows. The initially invisible window is moved to the chosen monitor before
showing it.

Monitor-move, resize and DPI-change events also trigger a fail-closed native
check; an invalid projection is hidden and closed rather than waiting for
the controller's three-second status poll. **Actual unplug on the church
projector is not automatically certified by CI.**

The isolated Windows Server 2022 WebView2 smoke now has an additional
**single-monitor fullscreen experiment**: it opens a test-only fullscreen
WebView and requires its actual inner physical bounds to match the CI runner's
primary screen. The runner is not a projector and does not certify placement
on an external display or mixed-DPI dual-monitor behavior.

### Presentation handoff limitation

`Beamer freigeben` closes only the timer display; the controller and countdown
remain available. The Windows desktop may be briefly visible before a separate
PowerPoint/Canva presentation covers the external monitor. This application
**does not launch, activate, or automatically transfer control to PowerPoint
or Canva**. A seamless handoff is **NOT TESTED** and must not be claimed.

## Physical Windows 11 handoff acceptance

Use [PHYSICAL_ACCEPTANCE_WINDOWS11.md](./PHYSICAL_ACCEPTANCE_WINDOWS11.md)
for the church laptop/projector rehearsal. All real-device results initially
remain **NOT_TESTED**. Do not treat a Windows Server CI pass as an actual
PowerPoint, Canva, HDMI hotplug or external-monitor test.

The documented handoff is deliberately conservative: `Beamer freigeben`
only closes the timer window. It cannot certify that PowerPoint or Canva has
already put the audience slide on the correct monitor, and it cannot prevent
a temporary view of the desktop if another presentation is not ready.
