//! Native projector ownership and monitor placement.
//! The display window loads the existing read-only display.html and never
//! receives native command permissions. No network server runs in this app.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::Serialize;
use std::time::Duration;
use std::sync::{atomic::{AtomicBool, Ordering}, Mutex};
use tauri::{
    Manager, Monitor, PhysicalPosition, State, WebviewUrl, WebviewWindow, WebviewWindowBuilder,
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

// A list index is unsafe: when the display arrangement changes, the same
// index can refer to another projector. A snapshot-bound token fails closed.
fn monitor_key(monitor: &Monitor) -> String {
    let geometry = DisplayIdentity::from_monitor(monitor);
    format!(
        "{}|{}|{}|{}|{}",
        monitor.name().map(String::as_str).unwrap_or(""),
        geometry.x,
        geometry.y,
        geometry.width,
        geometry.height
    )
}

fn choose_target_key(keys: &[String], selected: &str) -> Result<usize, &'static str> {
    if keys.is_empty() {
        return Err("Kein externer Bildschirm erkannt. Win + P → Erweitern wählen.");
    }
    if selected.is_empty() {
        return Err("Kein Beamer ausgewählt. Bitte die Bildschirme erneut prüfen.");
    }
    keys.iter()
        .position(|key| key == selected)
        .ok_or("Die Beameranordnung hat sich geändert. Bitte erneut auswählen.")
}

// Native state records which exact screen has ownership of the presentation.
// Closing or unplugging the screen clears the registration.
#[derive(Default)]
struct ProjectorRegistry {
    target: Mutex<Option<String>>,
    // A new hidden projector WebView already exists before fullscreen
    // placement finishes. Concurrent status probes must not treat it as an
    // unowned window and close it during presentation startup.
    opening: AtomicBool,
}

// RAII ensures even an early error or cancelled async command releases the
// in-flight guard instead of permanently blocking projection.
struct OpeningPermit<'a>(&'a ProjectorRegistry);
impl Drop for OpeningPermit<'_> {
    fn drop(&mut self) {
        self.0.opening.store(false, Ordering::Release);
    }
}

impl ProjectorRegistry {
    fn begin_open(&self) -> Result<OpeningPermit<'_>, String> {
        self.opening.compare_exchange(
            false, true, Ordering::AcqRel, Ordering::Acquire,
        ).map_err(|_| "Projektionsfenster wird bereits vorbereitet.".to_string())?;
        Ok(OpeningPermit(self))
    }
    fn is_opening(&self) -> bool {
        self.opening.load(Ordering::Acquire)
    }
    fn expected(&self) -> Result<Option<String>, String> {
        Ok(self.target.lock().map_err(|_| "Projektorstatus ist gesperrt.")?.clone())
    }
    fn set(&self, target: Option<String>) -> Result<(), String> {
        *self.target.lock().map_err(|_| "Projektorstatus ist gesperrt.")? = target;
        Ok(())
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
    id: String,
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
            id: monitor_key(monitor),
            name: monitor
                .name()
                .cloned()
                .unwrap_or_else(|| format!("Externer Bildschirm {}", id + 1)),
            width: monitor.size().width,
            height: monitor.size().height,
        })
        .collect())
}

// Use async Tauri commands to avoid blocking the WebView2 event loop on
// Windows when creating and closing windows.
fn verified_target(
    window: &WebviewWindow,
    monitor_key_from_ui: &str,
) -> Result<(Monitor, String), String> {
    let monitors = external_monitors(window)?;
    let keys: Vec<String> = monitors.iter().map(monitor_key).collect();
    let index = choose_target_key(&keys, monitor_key_from_ui).map_err(str::to_owned)?;
    Ok((monitors[index].clone(), keys[index].clone()))
}

fn validate_projector(
    window: &WebviewWindow,
    projector: &WebviewWindow,
    expected_key: &str,
) -> Result<bool, String> {
    // A successful fullscreen API call isn't proof of fullscreen: Tauri
    // explicitly documents that missing target monitors may be ignored.
    if !projector.is_visible().map_err(|e| e.to_string())?
        || !projector.is_fullscreen().map_err(|e| e.to_string())?
    {
        return Ok(false);
    }
    let Some(actual) = projector.current_monitor().map_err(|e| e.to_string())? else {
        return Ok(false);
    };
    let current_key = monitor_key(&actual);
    // A fullscreen flag and a monitor identity do not prove that WebView
    // content actually covers the physical projector pixel area.
    let monitors = external_monitors(window)?;
    let Some(target) = monitors.iter().find(|m| monitor_key(m) == expected_key) else {
        return Ok(false);
    };
    if current_key != expected_key {
        return Ok(false);
    }
    let inner_position = projector.inner_position().map_err(|e| e.to_string())?;
    let inner_size = projector.inner_size().map_err(|e| e.to_string())?;
    let pos = target.position();
    let size = target.size();
    Ok(physical_bounds_match(
        (inner_position.x, inner_position.y, inner_size.width, inner_size.height),
        (pos.x, pos.y, size.width, size.height),
    ))
}

fn physical_bounds_match(actual: (i32, i32, u32, u32), target: (i32, i32, u32, u32)) -> bool {
    const MAX_DIFFERENCE_PX: u32 = 2;
    actual.0.abs_diff(target.0) <= MAX_DIFFERENCE_PX
        && actual.1.abs_diff(target.1) <= MAX_DIFFERENCE_PX
        && actual.2.abs_diff(target.2) <= MAX_DIFFERENCE_PX
        && actual.3.abs_diff(target.3) <= MAX_DIFFERENCE_PX
}

async fn wait_for_fullscreen_placement(
    controller: &WebviewWindow,
    projector: &WebviewWindow,
    expected_key: &str,
) -> Result<bool, String> {
    // Win32 fullscreen placement can be asynchronous; allow up to 1.2s
    // for the actual physical window bounds to settle.
    for _ in 0..16 {
        if validate_projector(controller, projector, expected_key)? {
            return Ok(true);
        }
        tokio::time::sleep(Duration::from_millis(75)).await;
    }
    Ok(false)
}

fn close_failed_projection(
    projector: &WebviewWindow,
    registry: &ProjectorRegistry,
) -> Result<(), String> {
    registry.set(None)?;
    projector.close().map_err(|e| e.to_string())
}

#[tauri::command]
async fn open_projector(
    app: tauri::AppHandle,
    window: WebviewWindow,
    registry: State<'_, ProjectorRegistry>,
    monitor_key: String,
) -> Result<(), String> {
    require_controller(&window)?;
    let _opening_permit = registry.begin_open()?;
    let (target, key) = verified_target(&window, &monitor_key)?;
    let position = target.position();
    let target_position = PhysicalPosition::new(position.x as f64, position.y as f64);

    if let Some(existing) = app.get_webview_window("projector") {
        // The existing window is never assumed to be on the right display.
        existing
            .set_fullscreen_on_monitor(target_position)
            .map_err(|e| format!("Beamer-Vollbild fehlgeschlagen: {e}"))?;
        existing.show().map_err(|e| e.to_string())?;
        if !wait_for_fullscreen_placement(&window, &existing, &key).await? {
            close_failed_projection(&existing, &registry)?;
            return Err("Beamer wurde nicht auf dem gewählten Bildschirm im Vollbild angezeigt.".into());
        }
        registry.set(Some(key))?;
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

    // Position the invisible window on the selected screen before showing it.
    if let Err(e) = projector.set_position(tauri::PhysicalPosition::new(position.x, position.y)) {
        let _ = projector.close();
        return Err(format!("Beamerposition konnte nicht gesetzt werden: {e}"));
    }
    if let Err(e) = projector.set_fullscreen_on_monitor(target_position) {
        let _ = projector.close();
        return Err(format!("Beamer-Vollbild fehlgeschlagen: {e}"));
    }
    if let Err(e) = projector.show() {
        let _ = projector.close();
        return Err(format!("Projektionsfenster konnte nicht angezeigt werden: {e}"));
    }
    // Re-check after the window is shown. If hot-plug changed the topology,
    // reject rather than silently taking over a different monitor.
    if !wait_for_fullscreen_placement(&window, &projector, &key).await? {
        close_failed_projection(&projector, &registry)?;
        return Err("Beamer wurde nicht auf dem gewählten Bildschirm im Vollbild angezeigt.".into());
    }
    registry.set(Some(key))?;
    Ok(())
}

#[tauri::command]
async fn release_projector(
    app: tauri::AppHandle,
    window: WebviewWindow,
    registry: State<'_, ProjectorRegistry>,
) -> Result<(), String> {
    require_controller(&window)?;
    // Do not close an opening projection while its fullscreen placement is
    // still being confirmed by Windows.
    if registry.is_opening() {
        return Err("Beamer wird gerade geöffnet. Bitte erneut versuchen.".into());
    }
    // Release registration before closing the WebView2 window. The controller
    // and its persisted timer state are intentionally not touched.
    registry.set(None)?;
    if let Some(projector) = app.get_webview_window("projector") {
        projector.close().map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[tauri::command]
fn projector_status(
    app: tauri::AppHandle,
    window: WebviewWindow,
    registry: State<'_, ProjectorRegistry>,
) -> Result<bool, String> {
    require_controller(&window)?;
    // Without this guard, a status refresh can observe the newly created
    // window BEFORE registry.set(Some(...)) and close it as "unregistered".
    if registry.is_opening() {
        return Ok(false);
    }
    let Some(projector) = app.get_webview_window("projector") else {
        registry.set(None)?;
        return Ok(false);
    };
    let Some(expected_key) = registry.expected()? else {
        close_failed_projection(&projector, &registry)?;
        return Ok(false);
    };
    // Enforce the exact screen and actual fullscreen status, not merely
    // "some external monitor" or an existing WebviewWindow handle.
    if !validate_projector(&window, &projector, &expected_key)? {
        close_failed_projection(&projector, &registry)?;
        return Ok(false);
    }
    Ok(true)
}

fn main() {
    tauri::Builder::default()
        .manage(ProjectorRegistry::default())
        .on_window_event(|window, event| {
            if window.label() != "projector" {
                return;
            }
            let app = window.app_handle().clone();
            if matches!(event, tauri::WindowEvent::Destroyed) {
                let _ = app.state::<ProjectorRegistry>().set(None);
                return;
            }
            if !matches!(event,
                tauri::WindowEvent::Moved(_)
                | tauri::WindowEvent::Resized(_)
                | tauri::WindowEvent::ScaleFactorChanged { .. }
            ) {
                return;
            }
            // Position/size events are expected while opening fullscreen.
            if app.state::<ProjectorRegistry>().is_opening() {
                return;
            }
            // Windows can relocate a fullscreen presentation onto the laptop
            // when an HDMI projector disconnects. Validate the actual monitor
            // and physical bounds on the native event, rather than waiting
            // for the controller's three-second polling fallback.
            tauri::async_runtime::spawn(async move {
                let registry = app.state::<ProjectorRegistry>();
                if registry.is_opening() { return; }
                let Ok(Some(expected_key)) = registry.expected() else { return; };
                let Some(controller) = app.get_webview_window("controller") else { return; };
                let Some(projector) = app.get_webview_window("projector") else { return; };
                if !matches!(validate_projector(&controller, &projector, &expected_key), Ok(true)) {
                    // Hiding first reduces the chance of an accidental laptop
                    // takeover before the projector window is destroyed.
                    let _ = projector.hide();
                    let _ = close_failed_projection(&projector, &registry);
                }
            });
        })
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

    fn key(label: &str, x: i32, y: i32, w: u32, h: u32) -> String {
        format!("{label}|{x}|{y}|{w}|{h}")
    }

    #[test]
    fn same_screen_selected_by_key() {
        let monitors = vec![
            key("DISPLAY-A", -1920, 0, 1920, 1080),
            key("PROJECTOR-B", 1920, 0, 1280, 720),
        ];
        assert_eq!(choose_target_key(&monitors, &monitors[1]), Ok(1));
    }

    #[test]
    fn changing_display_order_never_redirects_the_projector() {
        let selected = key("PROJECTOR-B", 1920, 0, 1280, 720);
        let rearranged = vec![
            key("PROJECTOR-B", -1280, 0, 1280, 720),
            key("DISPLAY-A", 1920, 0, 1920, 1080),
        ];
        // The historical index 1 would target DISPLAY-A: this must refuse.
        assert!(choose_target_key(&rearranged, &selected).is_err());
    }

    #[test]
    fn detached_or_replaced_display_fails_closed() {
        let selected = key("PROJECTOR-B", 1920, 0, 1280, 720);
        let disconnected = vec![key("DISPLAY-A", -1920, 0, 1920, 1080)];
        assert!(choose_target_key(&disconnected, &selected).is_err());
        assert!(choose_target_key(&[], &selected).is_err());
    }

    #[test]
    fn no_missing_or_arbitrary_target() {
        let monitors = vec![key("PROJECTOR-A", 1920, 0, 1280, 720)];
        assert!(choose_target_key(&monitors, "").is_err());
        assert!(choose_target_key(&monitors, "0").is_err());
    }

    #[test]
    fn clone_mode_is_rejected_by_geometry() {
        let main = DisplayIdentity { x: 0, y: 0, width: 1920, height: 1080 };
        let mirror = main.clone();
        let extended_left = DisplayIdentity { x: -1280, y: 0, width: 1280, height: 720 };
        assert!(!is_external(&mirror, &main));
        assert!(is_external(&extended_left, &main));
    }

    #[test]
    fn physical_fullscreen_bounds_accept_negative_coordinates_and_hidpi_pixels() {
        assert!(physical_bounds_match((-1920, 0, 1920, 1080), (-1920, 0, 1920, 1080)));
        assert!(physical_bounds_match((2560, -150, 3840, 2160), (2560, -150, 3840, 2160)));
        assert!(!physical_bounds_match((2560, -150, 2560, 1440), (2560, -150, 3840, 2160)));
    }

    #[test]
    fn maximized_taskbar_window_and_wrong_screen_are_rejected() {
        assert!(!physical_bounds_match((0, 0, 1920, 1040), (0, 0, 1920, 1080)));
        assert!(!physical_bounds_match((0, 0, 1920, 1080), (1920, 0, 1920, 1080)));
        assert!(physical_bounds_match((1921, -1, 1921, 1079), (1920, 0, 1920, 1080)));
    }

    #[test]
    fn opening_projector_is_not_reclassified_as_unowned_by_status_poll() {
        let state = ProjectorRegistry::default();
        assert!(!state.is_opening());
        {
            let _permit = state.begin_open().expect("first native open should acquire guard");
            assert!(state.is_opening());
            assert!(state.begin_open().is_err(), "a second overlapping open must fail closed");
            assert_eq!(state.expected().unwrap(), None,
                "newly constructed fullscreen window has no registered target until validation");
            state.set(Some("PROJECTOR-A|1920|0|1920|1080".into())).unwrap();
            assert!(state.is_opening(), "status must defer until the command finishes");
        }
        assert!(!state.is_opening());
        assert!(state.expected().unwrap().is_some());
    }

    #[test]
    fn failed_open_releases_the_guard_and_allows_retry() {
        let state = ProjectorRegistry::default();
        { let _permit = state.begin_open().unwrap(); }
        assert!(!state.is_opening());
        { let _retry = state.begin_open().expect("a failed open must be retryable"); }
    }

    #[test]
    fn registry_releases_target_between_services() {
        let state = ProjectorRegistry::default();
        assert_eq!(state.expected().unwrap(), None);
        let target = key("PROJECTOR-A", 1920, 0, 1920, 1080);
        state.set(Some(target.clone())).unwrap();
        assert_eq!(state.expected().unwrap(), Some(target));
        state.set(None).unwrap();
        assert_eq!(state.expected().unwrap(), None);
    }
}
