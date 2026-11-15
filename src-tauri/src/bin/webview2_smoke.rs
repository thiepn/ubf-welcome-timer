//! CI-only real Windows WebView2 integration smoke. Not part of production.
//! Two real Tauri WebViews on ONE monitor exercise start, pause/resume,
//! closing the display and restoring it from the original controller's state.
//! No projector or PowerPoint acceptance is implied.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Manager, PhysicalPosition, WebviewUrl, WebviewWindow, WebviewWindowBuilder};

const KEY: &str = "ubf-koeln-projector-timer:state:v1";

#[tauri::command]
async fn smoke_report(
    app: tauri::AppHandle,
    window: WebviewWindow,
    phase: String,
    storage_present: bool,
) -> Result<(), String> {
    let result: Result<(), String> = (|| {
        if !storage_present {
            return Err(format!("Storage absent during {phase}"));
        }
        match (window.label(), phase.as_str()) {
            ("ci-display", "running") => {
                let controller = app.get_webview_window("controller").ok_or("Controller missing")?;
                window.eval(OBSERVE_PAUSED).map_err(|e| e.to_string())?;
                controller.eval("document.querySelector('#pause')?.click()")
                    .map_err(|e| e.to_string())?;
                println!("WEBVIEW2_SMOKE: running state reached display; requesting pause");
            }
            ("ci-display", "paused") => {
                let controller = app.get_webview_window("controller").ok_or("Controller missing")?;
                window.eval(OBSERVE_RESUMED).map_err(|e| e.to_string())?;
                controller.eval("document.querySelector('#resume')?.click()")
                    .map_err(|e| e.to_string())?;
                println!("WEBVIEW2_SMOKE: paused time remained stable; requesting resume");
            }
            ("ci-display", "resumed") => {
                // Native presentation handoff: close only the read-only display.
                // The original controller, its localStorage and timer remain.
                window.close().map_err(|e| e.to_string())?;
                WebviewWindowBuilder::new(
                    &app, "ci-return-display", WebviewUrl::App("display.html".into()),
                )
                .title("CI WebView2 reopened display")
                .inner_size(640.0, 360.0)
                .build()
                .map_err(|e| e.to_string())?;
                println!("WEBVIEW2_SMOKE: resumed timer; display released and reopened");
            }
            ("ci-return-display", "rehydrated") => {
                println!(
                    "WEBVIEW2_SMOKE_PASS: live start/pause/resume, display release and reopening preserved timer"
                );
                // Reproduce the operator-focus risk using a real Windows
                // WebView2 window, the same builder and show sequence as the
                // production projector. This CI runner has ONE monitor.
                let focus_probe = WebviewWindowBuilder::new(
                    &app, "ci-focus", WebviewUrl::App("display.html".into()),
                )
                .title("CI-only projector focus probe")
                // Exactly mirror the read-only production projector builder.
                .focused(false)
                .focusable(false)
                .visible(false)
                .decorations(false)
                .resizable(false)
                .build()
                .map_err(|e| e.to_string())?;
                let controller = app.get_webview_window("controller").ok_or("Controller missing")?;
                controller.set_focus().map_err(|e| e.to_string())?;
                if !controller.is_focused().map_err(|e| e.to_string())? {
                    return Err("WEBVIEW2_FOCUS_INCONCLUSIVE: controller cannot obtain Windows focus".into());
                }
                focus_probe.show().map_err(|e| e.to_string())?;
                // Production explicitly restores the operator's previous
                // focus after a projector is shown. Test the same behavior.
                controller.set_focus().map_err(|e| e.to_string())?;
            }
            _ => return Err(format!("Unexpected native smoke signal: {} / {phase}", window.label())),
        }
        Ok(())
    })();
    if let Err(error) = &result {
        eprintln!("WEBVIEW2_SMOKE_FAIL: {error}");
        app.exit(1);
    }
    result
}

#[tauri::command]
async fn smoke_focus_check(app: tauri::AppHandle, window: WebviewWindow) -> Result<(), String> {
    if window.label() != "ci-focus" {
        return Err("Focus probe must originate in the CI test display".into());
    }
    let controller = app.get_webview_window("controller").ok_or("Controller missing")?;
    let controller_focused = controller.is_focused().map_err(|e| e.to_string())?;
    let display_focused = window.is_focused().map_err(|e| e.to_string())?;
    if !controller_focused {
        eprintln!("WEBVIEW2_FOCUS_REPRO: projector show stole operator focus; controller={controller_focused} display={display_focused}");
        app.exit(1);
        return Ok(());
    }
    println!("WEBVIEW2_FOCUS_PASS: projector opening preserved Windows controller focus");
    window.close().map_err(|e| e.to_string())?;
    if !controller.is_focused().map_err(|e| e.to_string())? {
        eprintln!("WEBVIEW2_FOCUS_FAIL: releasing read-only display moved focus off controller");
        app.exit(1);
        return Ok(());
    }
    println!("WEBVIEW2_FOCUS_RELEASE_PASS: closing display preserved operator focus");
    // Continue the existing single-monitor physical fullscreen smoke.
    let monitor = controller.primary_monitor().map_err(|e| e.to_string())?
        .ok_or("No Windows CI primary monitor")?;
    let p = monitor.position();
    let fullscreen = WebviewWindowBuilder::new(
        &app, "ci-fullscreen", WebviewUrl::App("display.html".into()),
    )
    .title("CI-only fullscreen physical bounds probe")
    .focused(false)
    .focusable(false)
    .visible(false)
    .decorations(false)
    .resizable(false)
    .build().map_err(|e| e.to_string())?;
    fullscreen.set_position(PhysicalPosition::new(p.x, p.y)).map_err(|e| e.to_string())?;
    fullscreen.set_fullscreen_on_monitor(PhysicalPosition::new(
        f64::from(p.x), f64::from(p.y),
    )).map_err(|e| e.to_string())?;
    fullscreen.show().map_err(|e| e.to_string())?;
    // Reproduction gate: emulate a user switching to a *different*
    // presentation window while fullscreen placement is still settling.
    // This is a second real Windows WebView2 window, NOT PowerPoint/Canva.
    // Production records controller focus BEFORE creating/showing the
    // projector and unconditionally restores it afterward.
    let presentation = WebviewWindowBuilder::new(
        &app, "ci-presentation", WebviewUrl::App("display.html".into()),
    )
    .title("CI-only focusable presentation stand-in (not PowerPoint)")
    .focused(false)
    .inner_size(480.0, 300.0)
    .build().map_err(|e| e.to_string())?;
    presentation.set_focus().map_err(|e| e.to_string())?;
    tokio::time::sleep(std::time::Duration::from_millis(150)).await;
    if !presentation.is_focused().map_err(|e| e.to_string())?
        || controller.is_focused().map_err(|e| e.to_string())? {
        return Err("WEBVIEW2_FOCUS_RACE_INCONCLUSIVE: CI competitor could not obtain Windows focus".into());
    }
    println!("WEBVIEW2_FOCUS_RACE_SETUP: presentation window obtained Windows focus while the projector was opening");
    // OLD production behavior, intentionally duplicated until this proves
    // a failure: operator_had_focus was true at command initiation.
    controller.set_focus().map_err(|e| e.to_string())?;
    tokio::time::sleep(std::time::Duration::from_millis(100)).await;
    if !presentation.is_focused().map_err(|e| e.to_string())? {
        eprintln!("WEBVIEW2_FOCUS_RACE_REPRO: delayed controller restoration stole focus from newly selected presentation window");
        app.exit(1);
        return Ok(());
    }
    println!("WEBVIEW2_FOCUS_RACE_PASS: presentation remained focused after timer opening");
    // A one-monitor CI runner can occlude either WebView2 and suspend its JS
    // timers despite a correct native window state. Check directly from Rust.
    for _ in 0..50 {
        if smoke_fullscreen_check(app.clone(), controller.clone())? {
            return Ok(());
        }
        tokio::time::sleep(std::time::Duration::from_millis(100)).await;
    }
    if let Some(w) = app.get_webview_window("ci-fullscreen") {
        let monitor = w.primary_monitor().ok().flatten();
        eprintln!(
            "WEBVIEW2_FULLSCREEN_DIAG: fullscreen={:?} visible={:?} bounds={:?}/{:?} expected={:?}/{:?} controller_focused={:?} display_focused={:?}",
            w.is_fullscreen(), w.is_visible(), w.inner_position(), w.inner_size(),
            monitor.as_ref().map(|m| m.position().clone()),
            monitor.as_ref().map(|m| m.size().clone()),
            controller.is_focused(), w.is_focused(),
        );
    }
    eprintln!("WEBVIEW2_FULLSCREEN_FAIL: native fullscreen bounds never matched in 5s");
    app.exit(1);
    Ok(())
}

const OBSERVE_FOCUS: &str = r#"
(() => {
  setTimeout(() => {
    window.__TAURI__.core.invoke('smoke_focus_check').catch(error => {
      console.error('WEBVIEW2_FOCUS_CHECK_ERROR: ' + String(error));
    });
  }, 400);
})();
"#;

fn smoke_fullscreen_check(app: tauri::AppHandle, window: WebviewWindow) -> Result<bool, String> {
    if window.label() != "controller" {
        return Err("Only the CI operator controller can inspect fullscreen bounds".into());
    }
    let fullscreen = app.get_webview_window("ci-fullscreen")
        .ok_or("CI fullscreen display window missing")?;
    let monitor = fullscreen.primary_monitor().map_err(|e| e.to_string())?
        .ok_or("No Windows CI primary monitor")?;
    let mpos = monitor.position();
    let msize = monitor.size();
    let p = fullscreen.inner_position().map_err(|e| e.to_string())?;
    let s = fullscreen.inner_size().map_err(|e| e.to_string())?;
    let max_error = 2_u32;
    let controller_focused = window.is_focused().map_err(|e| e.to_string())?;
    let display_focused = fullscreen.is_focused().map_err(|e| e.to_string())?;
    let pass = fullscreen.is_fullscreen().map_err(|e| e.to_string())?
        && controller_focused && !display_focused
        && p.x.abs_diff(mpos.x) <= max_error
        && p.y.abs_diff(mpos.y) <= max_error
        && s.width.abs_diff(msize.width) <= max_error
        && s.height.abs_diff(msize.height) <= max_error;
    if pass {
        println!("WEBVIEW2_FULLSCREEN_PASS: real Windows fullscreen content rectangle matches the CI monitor's physical pixels");
        app.exit(0);
    }
    Ok(pass)
}

const START_COUNTDOWN: &str = r#"
(() => {
  let attempts = 0;
  const ticker = setInterval(() => {
    const button = document.querySelector('#start');
    const preset = document.querySelector('[data-duration="180000"]');
    if (button && preset && !button.disabled) {
      clearInterval(ticker);
      preset.click();
      button.click();
    } else if (++attempts > 100) {
      clearInterval(ticker);
      console.error('WEBVIEW2_SMOKE: controller did not become ready');
    }
  }, 100);
})();
"#;

const OBSERVE_RUNNING: &str = r#"
(() => {
  let attempts = 0;
  const ticker = setInterval(() => {
    const stage = document.querySelector('#stage');
    const clock = document.querySelector('#timer-numbers');
    const welcome = document.querySelector('.slide-image--welcome');
    if (stage?.classList.contains('is-timer') &&
        clock?.textContent?.match(/^(?:02|03):[0-5][0-9]$/) &&
        welcome?.complete && welcome.naturalWidth > 0) {
      clearInterval(ticker);
      const state = localStorage.getItem('ubf-koeln-projector-timer:state:v1');
      const stored = Boolean(state && JSON.parse(state).phase === 'running');
      window.__TAURI__.core.invoke('smoke_report',
        {phase:'running', storagePresent:stored});
    } else if (++attempts > 150) {
      clearInterval(ticker);
      window.__TAURI__.core.invoke('smoke_report',
        {phase:'timeout', storagePresent:false});
    }
  }, 100);
})();
"#;

const OBSERVE_PAUSED: &str = r#"
(() => {
  let attempts = 0, last = null, stableAt = null;
  const ticker = setInterval(() => {
    const raw = localStorage.getItem('ubf-koeln-projector-timer:state:v1');
    const state = raw ? JSON.parse(raw) : null;
    const clock = document.querySelector('#timer-numbers')?.textContent;
    if (state?.phase === 'paused' && clock) {
      if (clock !== last) {
        last = clock; stableAt = Date.now();
      } else if (Date.now() - stableAt > 1250) {
        clearInterval(ticker);
        window.__TAURI__.core.invoke('smoke_report',
          {phase:'paused', storagePresent:true});
      }
    }
    if (++attempts > 100) {
      clearInterval(ticker);
      window.__TAURI__.core.invoke('smoke_report',
        {phase:'timeout-paused', storagePresent:false});
    }
  }, 100);
})();
"#;

const OBSERVE_RESUMED: &str = r#"
(() => {
  let attempts = 0;
  const initial = document.querySelector('#timer-numbers')?.textContent;
  const seconds = time => {
    const parts = time?.split(':').map(Number);
    return parts?.length === 2 ? parts[0] * 60 + parts[1] : Infinity;
  };
  const ticker = setInterval(() => {
    const raw = localStorage.getItem('ubf-koeln-projector-timer:state:v1');
    const state = raw ? JSON.parse(raw) : null;
    const clock = document.querySelector('#timer-numbers')?.textContent;
    if (state?.phase === 'running' && seconds(clock) < seconds(initial)) {
      clearInterval(ticker);
      window.__TAURI__.core.invoke('smoke_report',
        {phase:'resumed', storagePresent:true});
    }
    if (++attempts > 100) {
      clearInterval(ticker);
      window.__TAURI__.core.invoke('smoke_report',
        {phase:'timeout-resumed', storagePresent:false});
    }
  }, 100);
})();
"#;

const OBSERVE_REOPENED: &str = r#"
(() => {
  let attempts = 0;
  const ticker = setInterval(() => {
    const raw = localStorage.getItem('ubf-koeln-projector-timer:state:v1');
    const state = raw ? JSON.parse(raw) : null;
    const stage = document.querySelector('#stage');
    const clock = document.querySelector('#timer-numbers');
    const welcome = document.querySelector('.slide-image--welcome');
    if (state?.phase === 'running' &&
        stage?.classList.contains('is-timer') &&
        clock?.textContent?.match(/^(?:02|03):[0-5][0-9]$/) &&
        welcome?.complete && welcome.naturalWidth > 0) {
      clearInterval(ticker);
      window.__TAURI__.core.invoke('smoke_report',
        {phase:'rehydrated', storagePresent:true});
    }
    if (++attempts > 100) {
      clearInterval(ticker);
      window.__TAURI__.core.invoke('smoke_report',
        {phase:'timeout-reopen', storagePresent:false});
    }
  }, 100);
})();
"#;

fn main() {
    let _ = KEY; // documented single authoritative timer storage key
    tauri::Builder::default()
        .on_page_load(|webview, payload| {
            if !matches!(payload.event(), tauri::webview::PageLoadEvent::Finished) {
                return;
            }
            let result = match webview.label() {
                "controller" => webview.eval(START_COUNTDOWN),
                "ci-display" => webview.eval(OBSERVE_RUNNING),
                "ci-return-display" => webview.eval(OBSERVE_REOPENED),
                "ci-focus" => webview.eval(OBSERVE_FOCUS),
                // Fullscreen verification runs from controller because this
                // intentionally non-focusable audience WebView can be occluded.
                _ => return,
            };
            if let Err(error) = result {
                eprintln!("WEBVIEW2_SMOKE_FAIL: injection failed: {error}");
                webview.app_handle().exit(1);
            }
        })
        .setup(|app| {
            let controller = app
                .get_webview_window("controller")
                .ok_or("Controller window missing from Tauri configuration")?;
            controller.show()?;
            WebviewWindowBuilder::new(
                app, "ci-display", WebviewUrl::App("display.html".into()),
            )
            .title("CI native WebView2 synchronization probe")
            .inner_size(640.0, 360.0)
            .build()?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![smoke_report, smoke_focus_check])
        .run(tauri::generate_context!())
        .expect("Native WebView2 smoke could not initialize");
}
