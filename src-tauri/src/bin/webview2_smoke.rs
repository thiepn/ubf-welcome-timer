//! CI-only real Windows WebView2 integration smoke. Not part of production.
//! Uses two real Tauri WebViews on ONE monitor to validate same-app storage and
//! controller -> display timer propagation. Never claims projector acceptance.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Manager, WebviewUrl, WebviewWindow, WebviewWindowBuilder};

#[tauri::command]
fn smoke_report(
    app: tauri::AppHandle,
    window: WebviewWindow,
    phase: String,
    storage_present: bool,
) -> Result<(), String> {
    if window.label() != "ci-display" {
        return Err("Only CI display can report test completion".into());
    }
    if phase == "running" && storage_present {
        println!("WEBVIEW2_SMOKE_PASS: separate native WebViews shared timer state");
        app.exit(0);
    } else {
        eprintln!("WEBVIEW2_SMOKE_FAIL: {phase}, storage_present={storage_present}");
        app.exit(1);
    }
    Ok(())
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

const OBSERVE_DISPLAY: &str = r#"
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

fn main() {
    tauri::Builder::default()
        .on_page_load(|webview, payload| {
            if !matches!(payload.event(), tauri::webview::PageLoadEvent::Finished) {
                return;
            }
            let result = match webview.label() {
                "controller" => webview.eval(START_COUNTDOWN),
                "ci-display" => webview.eval(OBSERVE_DISPLAY),
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
            // This is a CI fixture window on the primary display, NOT a
            // projector. It deliberately loads the actual display.html page.
            WebviewWindowBuilder::new(
                app,
                "ci-display",
                WebviewUrl::App("display.html".into()),
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
