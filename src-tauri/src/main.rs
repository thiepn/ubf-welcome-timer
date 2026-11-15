//! Native projector ownership and monitor placement.
//! The display window loads the existing read-only display.html and never
//! receives native command permissions. No network server runs in this app.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::Serialize;
use tauri::{
    Manager, Monitor, PhysicalPosition, WebviewUrl, WebviewWindow, WebviewWindowBuilder,
};

#[derive(Clone, Debug, PartialEq, Eq)]
struct DisplayIdentity {
    x: i32,
    y: i32,
    width: u32,
    height: u32,
}

impl DisplayIdentity {
    fn from_monitor(monitor: &Monitor) -> Self {
        let position = monitor.position();
        let size = monitor.size();
        Self {
            x: position.x,
            y: position.y,
            width: size.width,
            height: size.height,
        }
    }
}

// Matching the desktop geometry also rejects duplicate/mirrored displays.
// A projector in Extend mode must have its own desktop rectangle.
fn is_external(candidate: &DisplayIdentity, primary: &DisplayIdentity) -> bool {
    candidate != primary
}

fn choose_external_index(count: usize, requested: Option<usize>) -> Result<usize, &'static str> {
    match (count, requested) {
        (0, _) => Err("Kein externer Bildschirm erkannt. Win + P → Erweitern wählen."),
        (1, None) => Ok(0),
        (n, Some(index)) if index < n => Ok(index),
        (_, Some(_)) => Err("Bildschirmauswahl ist veraltet. Erneut auswählen."),
        (_, None) => Err("Mehrere externe Bildschirme erkannt. Bitte einen auswählen."),
    }
}

fn require_controller(window: &WebviewWindow) -> Result<(), String> {
    if window.label() != "controller" {
        return Err("Nur die Steuerung darf die Projektion verändern.".into());
    }
    Ok(())
}

fn external_monitors(window: &WebviewWindow) -> Result<Vec<Monitor>, String> {
    let primary = window
        .primary_monitor()
        .map_err(|e| e.to_string())?
        .ok_or("Windows meldet keinen primären Bildschirm.")?;
    let main = DisplayIdentity::from_monitor(&primary);
    let mut monitors: Vec<Monitor> = window
        .available_monitors()
        .map_err(|e| e.to_string())?
        .into_iter()
        .filter(|m| is_external(&DisplayIdentity::from_monitor(m), &main))
        .collect();
    monitors.sort_by_key(|m| {
        let p = m.position();
        (p.x, p.y, m.name().cloned().unwrap_or_default())
    });
    Ok(monitors)
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct ProjectorTarget {
    id: usize,
    name: String,
    width: u32,
    height: u32,
}

#[tauri::command]
fn list_projector_targets(window: WebviewWindow) -> Result<Vec<ProjectorTarget>, String> {
    require_controller(&window)?;
    let monitors = external_monitors(&window)?;
    Ok(monitors
        .iter()
        .enumerate()
        .map(|(id, monitor)| ProjectorTarget {
            id,
            name: monitor
                .name()
                .cloned()
                .unwrap_or_else(|| format!("Externer Bildschirm {}", id + 1)),
            width: monitor.size().width,
            height: monitor.size().height,
        })
        .collect())
}

// Must be async: synchronously creating a WebView2 window inside a Tauri
// command can deadlock on Windows.
#[tauri::command]
async fn open_projector(
    app: tauri::AppHandle,
    window: WebviewWindow,
    monitor_id: Option<usize>,
) -> Result<(), String> {
    require_controller(&window)?;
    let monitors = external_monitors(&window)?;
    let index = choose_external_index(monitors.len(), monitor_id)?;
    let target = &monitors[index];
    let position = target.position();
    let target_position = PhysicalPosition::new(position.x as f64, position.y as f64);

    if let Some(existing) = app.get_webview_window("projector") {
        existing
            .set_fullscreen_on_monitor(target_position)
            .map_err(|e| format!("Beamer-Vollbild fehlgeschlagen: {e}"))?;
        existing.show().map_err(|e| e.to_string())?;
        return Ok(());
    }

    let projector = WebviewWindowBuilder::new(
        &app,
        "projector",
        WebviewUrl::App("display.html".into()),
    )
    .title("UBF Köln — Projektion")
    .visible(false)
    .decorations(false)
    .resizable(false)
    .build()
    .map_err(|e| format!("Projektionsfenster konnte nicht erstellt werden: {e}"))?;

    // Target the physical monitor directly. Do not briefly show a window on
    // the laptop, and do not fall back to presenting on the primary screen.
    if let Err(e) = projector.set_fullscreen_on_monitor(target_position) {
        let _ = projector.close();
        return Err(format!("Beamer-Vollbild fehlgeschlagen: {e}"));
    }
    if let Err(e) = projector.show() {
        let _ = projector.close();
        return Err(format!("Projektionsfenster konnte nicht angezeigt werden: {e}"));
    }
    Ok(())
}

#[tauri::command]
async fn release_projector(
    app: tauri::AppHandle,
    window: WebviewWindow,
) -> Result<(), String> {
    require_controller(&window)?;
    if let Some(projector) = app.get_webview_window("projector") {
        projector.close().map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[tauri::command]
fn projector_status(app: tauri::AppHandle, window: WebviewWindow) -> Result<bool, String> {
    require_controller(&window)?;
    let Some(projector) = app.get_webview_window("projector") else {
        return Ok(false);
    };

    // When a cable is unplugged Windows may relocate a fullscreen window to
    // the laptop. Immediately release it instead of covering the controls.
    let primary = window
        .primary_monitor()
        .map_err(|e| e.to_string())?
        .ok_or("Windows meldet keinen primären Bildschirm.")?;
    if let Some(current) = projector.current_monitor().map_err(|e| e.to_string())? {
        let current_id = DisplayIdentity::from_monitor(&current);
        let primary_id = DisplayIdentity::from_monitor(&primary);
        if !is_external(&current_id, &primary_id) {
            let _ = projector.close();
            return Ok(false);
        }
    }
    Ok(true)
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            // Only the Windows primary display is used for controls. On the
            // church laptop, set the built-in panel as the primary screen.
            if let Some(controller) = app.get_webview_window("controller") {
                if let Some(primary) = controller.primary_monitor()? {
                    let pos = primary.position();
                    controller.set_position(PhysicalPosition::new(pos.x + 48, pos.y + 48))?;
                }
                controller.show()?;
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            list_projector_targets,
            open_projector,
            release_projector,
            projector_status
        ])
        .run(tauri::generate_context!())
        .expect("UBF Timer could not start");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn one_external_monitor_is_automatic() {
        assert_eq!(choose_external_index(1, None), Ok(0));
        assert_eq!(choose_external_index(1, Some(0)), Ok(0));
    }

    #[test]
    fn multiple_external_monitors_require_operator_choice() {
        assert!(choose_external_index(2, None).is_err());
        assert_eq!(choose_external_index(2, Some(1)), Ok(1));
        assert!(choose_external_index(2, Some(2)).is_err());
    }

    #[test]
    fn single_screen_never_becomes_a_projector() {
        assert!(choose_external_index(0, None).is_err());
        assert!(choose_external_index(0, Some(0)).is_err());
    }

    #[test]
    fn clone_mode_is_rejected_by_geometry() {
        let main = DisplayIdentity { x: 0, y: 0, width: 1920, height: 1080 };
        let mirror = main.clone();
        let extended_left = DisplayIdentity { x: -1280, y: 0, width: 1280, height: 720 };
        assert!(!is_external(&mirror, &main));
        assert!(is_external(&extended_left, &main));
    }
}
