//! CI-only real Windows WebView2 integration smoke. Not part of production.
//! Two real Tauri WebViews on ONE monitor exercise start, pause/resume,
//! closing the display and restoring it from the original controller's state.
//! No projector or PowerPoint acceptance is implied.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Manager, WebviewUrl, WebviewWindow, WebviewWindowBuilder};

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
                app.exit(0);
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
        .invoke_handler(tauri::generate_handler![smoke_report])
        .run(tauri::generate_context!())
        .expect("Native WebView2 smoke could not initialize");
}
