//! Wait for real Tauri window destruction before reusing the fixed projector
//! label. WebviewWindow::close() posts a close request and may return while
//! Windows/Tauri still own that label. Controller state must not be reset.

use std::time::Duration;
use tauri::{AppHandle, Manager, WebviewWindow};

pub async fn close_and_wait_for_label_release(
    app: &AppHandle,
    projector: &WebviewWindow,
) -> Result<(), String> {
    let label = projector.label().to_owned();
    projector
        .close()
        .map_err(|e| format!("Projektionsfenster konnte nicht geschlossen werden: {e}"))?;
    // A native close is asynchronous. Do not say "released" until a subsequent
    // open can safely create a fresh WebView with the *same* label.
    for _ in 0..40 {
        if app.get_webview_window(&label).is_none() {
            return Ok(());
        }
        tokio::time::sleep(Duration::from_millis(50)).await;
    }
    Err(format!(
        "Projektionsfenster {label} ist noch nicht vollständig geschlossen. Bitte erneut versuchen."
    ))
}
