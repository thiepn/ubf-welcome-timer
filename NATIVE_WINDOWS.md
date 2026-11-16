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

**Keine verteilbare App steht bereit:** Der Entwurf hat
`bundle.active: false` und wurde weder installiert noch als Release
bereitgestellt. Die folgenden Befehle sind ausschließlich ein **lokaler
Entwicklungs- und Abnahmepfad**, keine bereits durchgeführte Installation.
Für den realen Kirchengerätetest muss zuerst ein autorisierter,
nachweislich lauffähiger Build am konkreten Windows-11-Gerät vorliegen.
Die Browser-Version aus `Start-Timer.cmd` ist kein Test der nativen
Monitor-Automatik.

Vor Ort die kompakte [Bedienkarte](./HANDOFF_OPERATOR_CARD_DE.md)
und die [W01–W08-Abnahmematrix](./PHYSICAL_ACCEPTANCE_WINDOWS11.md)
verwenden. Fehlende echte Geräteergebnisse bleiben `NOT_TESTED`.



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

## Operator-focus handoff verification (Windows CI)

The projector WebView is constructed as **not initially focused** and
**non-focusable**, and the native controller restores its previous focus after
the projection window is shown. Windows CI demonstrated that the builder flags
alone did NOT prevent the read-only WebView2 from stealing focus. The explicit
focus restore ensures the laptop control window remains the keyboard target
when an operator opened the projection from that controller.
This avoids redirecting keyboard operations to a separate audience window.

A Windows Server 2022 real-WebView2 test first reproduced the old behavior:
the controller lost focus and the display gained focus after opening the
projector-style window. The regression now requires the operator controller to
remain focused after opening, after closing the display, and while the
CI-only fullscreen window is visible. The test uses a single monitor: the
real church's separate projector and physical input devices are **NOT TESTED**.

## Operator switches to PowerPoint while projection is opening

GitHub Actions #43748043998 first **reproduced an actual Windows focus
defect** using a focusable, test-only WebView2 presentation stand-in. The
controller was initially focused, another window obtained focus between
fullscreen show and delayed completion, then an unconditional controller
`set_focus()` stole keyboard focus back. This fixture is **not** actual
PowerPoint or Canva acceptance.

The minimal correction shares `src-tauri/src/operator_focus.rs` between
production and Windows smoke. The timer attempts to restore the controller
only if it was focused at opening, remained focused immediately before
fullscreen, and **its own projector window now owns focus**. Otherwise it
leaves the newly selected presentation focused. This avoids a blind
restoration based on a stale initial-focus snapshot.

Remaining limitations: Microsoft Windows controls cross-process focus
permissions and transitions. A test-only second WebView2 process window
inside the same app is **not proof** of a seamless external PowerPoint/Canva
handoff. Real Windows 11 dual-screen behavior and Sunday service remain
**NOT_TESTED / NO_GO**.

## Rapid release/reopen with the production window label

Real Windows Server 2022 WebView2 CI **reproduced** the race in Actions
#43763040871. A test-only projection labeled exactly `projector` was
closed, and immediately rebuilding `projector` failed with
`a webview with label 'projector' already exists`. This shows that
`WebviewWindow::close()` can return before Tauri removes the old label.

The native `release_projector` command now shares the same
`projector_lifecycle::close_and_wait_for_label_release` routine used by
the Windows CI probe. It waits for actual label removal (maximum roughly
two seconds), returning success only when an immediate same-label
reopening is possible. If the old window remains, the operator receives
an explicit error, not a false successful handoff. No timer persistence,
Canva assets, browser fallback, or other presentation programs are changed.

The CI fixture **does not** use a physical projector. It tests same-label
native lifecycle and verifies the new WebView can be shown and subsequently
released. Windows 11 hardware, HDMI disconnect, PowerPoint/Canva audience
handoff, and a desktop-free switch remain **NOT_TESTED**. Live service
remains **NO_GO** pending the physical acceptance matrix.

## Lokales Windows-11-Probepaket (kein Release)

Auf einem vertrauenswürdigen Windows-x64-Buildrechner mit Node.js 20+,
Rust x86_64-pc-windows-msvc und Microsoft C++ Build Tools im **genau
gewünschten PR-Quellstand** aus dem Repository-Stamm ausführen:

    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Build-Windows-Rehearsal.ps1

Nur **lokal** entsteht `dist/UBF-Koeln-Timer-LOKALE-PROBE.zip` mit einer
**unsignierten EXE**, `BUILD_MANIFEST.json` (Quell-SHA und SHA-256),
originalem `welcome.png`-Fallback, Bedienkarte und W01–W08-Protokoll.
Der Build prüft Git-Status, deaktiviertes Installer-Bundling und die
unveränderten Canva-PNG-Hashes. **Kein Upload, Installer, Release, Deployment
oder automatischer Start.** Die lokale ZIP kann erst nach ausdrücklicher
Berechtigung auf den Testrechner übertragen und dort entpackt werden.
Auf dem Zielrechner reicht Windows 11 x64 mit WebView2; dort muss nicht
Rust/Node installiert werden. Vor dem Start SHA-256 kontrollieren;
Sicherheitswarnungen bei unsignierten EXEs nicht blind umgehen.

GitHub Actions baut dieselbe ZIP ausschließlich in PR #4 auf einem
kurzlebigen Windows-Runner aus dem exakten PR-HEAD und **verwirft sie**.
Es wird **keine ausführbare Datei als Artifact hochgeladen**. Ein grüner
CI-Build beweist nur technische Kompilierung, nicht die tatsächliche
Windows-11-/HDMI-/PowerPoint-/Canva-Probe. Alle W01–W08 bleiben NOT_TESTED,
Live-Einsatz bleibt NO_GO.


## Probe-ZIP: Prüfen, starten, Beobachtungen sichern (ohne Veröffentlichung)

Ein vollständig entpacktes **lokales** Probe-ZIP enthält jetzt auch
`Start-Probe.cmd`, `Verify-Windows-Rehearsal.ps1` und das eigenständige
Offline-Formular `ABNAHME_W01-W08.html`.

1. Vom **genehmigten** Quell-Commit aus lokal bauen; ZIP auf den autorisierten
   Testrechner kopieren und vollständig entpacken. `BUILD_MANIFEST.json`
   vergleichen: Die Quell-SHA muss unabhängig mit dem ausdrücklich
   akzeptierten GitHub-Commit übereinstimmen. Hashes aus demselben ZIP
   beweisen nur **interne Konsistenz**, keine digitale Herausgebersignatur.
2. `Start-Probe.cmd` doppelklicken. Das Skript prüft SHA-256 von EXE,
   Original-`welcome.png` und Abnahmeformular, prüft die Probe-Kennzeichen
   und verlangt **PROBE** als ausdrückliche Startbestätigung. Bei Fehler
   nicht starten. Es umgeht keine Windows-SmartScreen-Warnung.
3. `ABNAHME_W01-W08.html` lokal öffnen. Laptop-/Beamer-Metadaten eintragen.
   W01–W08 stehen anfänglich auf **NOT_TESTED**, nicht PASS.
   Das Formular kann nach der echten Beobachtung PASS/FAIL mit Kommentaren
   speichern und als **JSON exportieren** (auch importieren) oder drucken.
   Browser-Zwischenspeicherung alleine ist keine zuverlässige Sicherung.
4. Für W05 PowerPoint **vor** und **nach** Timer-Freigabe getrennt prüfen;
   für W06 Canva **Vollbild** und **Präsentationsansicht** getrennt.
   Die Person am Zuschauerplatz dokumentiert private Referentenansichten,
   Desktop-Flash, Timerverdeckung und Zeitverzug. Eine scheinbar korrekte
   Folie im Nachhinein beweist keinen nahtlosen Handoff.
5. Beim Entfernen des HDMI-Kabels, falscher Anzeige, Eingabefokusverlust
   oder ungewollter Sichtbarkeit privater Inhalte den Test stoppen und FAIL
   festhalten. Statisches `welcome.png` bleibt verfügbar.

Der Prüfer **startet nichts automatisch**; nur eine ausdrücklich bestätigte
lokale Probe öffnet die EXE. Es gibt keine Online-API, keine Uploads und keine
automatische Live-Freigabe. Alle acht echten Gerätetests bleiben hier
**NOT_TESTED**, Sonntagseinsatz **NO_GO**.
