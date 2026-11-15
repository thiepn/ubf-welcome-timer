//! Only repair focus when the timer's own projector actually activated.
//! An old "controller was focused" snapshot cannot justify taking focus
//! back from a presentation selected while a fullscreen operation was pending.

use tauri::WebviewWindow;

fn should_restore(
    operator_focused_at_start: bool,
    operator_focused_before_fullscreen: bool,
    operator_focused_now: bool,
    projector_focused_now: bool,
) -> bool {
    operator_focused_at_start
        && operator_focused_before_fullscreen
        && !operator_focused_now
        && projector_focused_now
}

pub fn restore_if_projector_activated(
    controller: &WebviewWindow,
    projector: &WebviewWindow,
    operator_focused_at_start: bool,
    operator_focused_before_fullscreen: bool,
) -> Result<bool, String> {
    let operator_focused_now = controller.is_focused().map_err(|e| e.to_string())?;
    let projector_focused_now = projector.is_focused().map_err(|e| e.to_string())?;
    let should = should_restore(
        operator_focused_at_start,
        operator_focused_before_fullscreen,
        operator_focused_now,
        projector_focused_now,
    );
    if should {
        controller.set_focus().map_err(|e| e.to_string())?;
    }
    Ok(should)
}

#[cfg(test)]
mod tests {
    use super::should_restore;

    #[test]
    fn restores_when_our_projector_is_the_window_that_stole_focus() {
        assert!(should_restore(true, true, false, true));
    }

    #[test]
    fn refuses_to_reclaim_from_a_new_presentation_window() {
        assert!(!should_restore(true, true, false, false));
    }

    #[test]
    fn refuses_if_operator_switched_before_fullscreen_transition() {
        assert!(!should_restore(true, false, false, true));
    }

    #[test]
    fn no_focus_change_when_controller_is_still_active() {
        assert!(!should_restore(true, true, true, false));
    }

    #[test]
    fn never_activates_a_controller_that_was_not_the_operator_target() {
        assert!(!should_restore(false, false, false, true));
    }
}
