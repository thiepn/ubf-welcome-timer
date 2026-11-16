"""Real-browser end-to-end acceptance for Chromium (requires Playwright).

Run from the project directory:
  python -m pip install playwright
  python -m playwright install chromium
  npm run test:browser

This test suite starts its own local server. It does not publish the website.
"""
import os
import re
import socket
import subprocess
import time
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
PORT = 18765
BASE = f'http://127.0.0.1:{PORT}'

# This mock exercises the real controller DOM bridge in Chromium; it is NOT
# a WebView2 test and deliberately cannot certify physical projector behavior.
NATIVE_BRIDGE_MOCK = r"""(() => {
  window.__nativeCalls = [];
  window.__nativeActive = false;
  window.__nativeTargets = [
    {id: 'PROJECTOR-A|1920|0|1920|1080', name: 'Projektor A', width: 1920, height: 1080}
  ];
  window.__nativePopupWasCalled = false;
  window.__nativeDelayNextStatus = false;
  window.__nativePendingStatus = [];
  window.__nativeHoldOpen = false;
  window.__nativeHoldRelease = false;
  window.__nativePendingActions = [];
  window.__nativeForcedOpenError = '';
  window.__nativeForcedReleaseError = '';
  window.__nativeForcedStatusError = '';
  window.open = () => { window.__nativePopupWasCalled = true; throw Error('native popup regression'); };
  window.__TAURI__ = {core: {invoke: async (command, args = {}) => {
    window.__nativeCalls.push({command, args});
    if (command === 'list_projector_targets') return window.__nativeTargets;
    if (command === 'projector_status') {
      if (window.__nativeForcedStatusError) throw Error(window.__nativeForcedStatusError);
      if (window.__nativeDelayNextStatus) {
        window.__nativeDelayNextStatus = false;
        const captured = window.__nativeActive;
        return new Promise(resolve => {
          window.__nativePendingStatus.push(() => resolve(captured));
        });
      }
      return window.__nativeActive;
    }
    if (command === 'open_projector') {
      if (window.__nativeForcedOpenError) throw Error(window.__nativeForcedOpenError);
      if (!window.__nativeTargets.some(target => target.id === args.monitorKey)) {
        throw Error('Die Beameranordnung hat sich geändert.');
      }
      if (window.__nativeHoldOpen) {
        await new Promise(resolve => { window.__nativePendingActions.push(resolve); });
      }
      window.__nativeActive = true;
      return;
    }
    if (command === 'release_projector') {
      if (window.__nativeForcedReleaseError) throw Error(window.__nativeForcedReleaseError);
      if (window.__nativeHoldRelease) {
        await new Promise(resolve => { window.__nativePendingActions.push(resolve); });
      }
      window.__nativeActive = false;
      return;
    }
    throw Error('Unexpected command: ' + command);
  }}};
})();"""


class ProjectorTimerBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = dict(os.environ, PORT=str(PORT))
        cls.server = subprocess.Popen(
            ['node', 'server.mjs'], cwd=str(ROOT), env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        for _ in range(70):
            try:
                with socket.create_connection(('127.0.0.1', PORT), timeout=0.1):
                    break
            except OSError:
                time.sleep(0.1)
        else:
            cls.server.terminate()
            raise RuntimeError('Local static server failed to start.')
        cls.playwright = sync_playwright().start()
        browser_opts = {'headless': True}
        if os.environ.get('PLAYWRIGHT_CHROMIUM_PATH'):
            browser_opts['executable_path'] = os.environ['PLAYWRIGHT_CHROMIUM_PATH']
        cls.browser = cls.playwright.chromium.launch(**browser_opts)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'browser'):
            cls.browser.close()
        if hasattr(cls, 'playwright'):
            cls.playwright.stop()
        if hasattr(cls, 'server'):
            cls.server.terminate()
            try:
                cls.server.wait(timeout=3)
            except subprocess.TimeoutExpired:
                cls.server.kill()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width':1536,'height':864})
        self.control = self.context.new_page()
        self.display = self.context.new_page()
        self.errors = []
        self.control.on('pageerror', lambda e: self.errors.append(f'controller: {e}'))
        self.display.on('pageerror', lambda e: self.errors.append(f'display: {e}'))
        self.display.goto(BASE + '/display.html')
        self.control.goto(BASE + '/control.html')

    def tearDown(self):
        self.assertEqual(self.errors, [], 'JavaScript errors occurred')
        self.context.close()

    def test_01_original_welcome_and_no_projector_controls(self):
        stage = self.display.locator('#stage')
        self.assertNotIn('is-timer', stage.get_attribute('class'))
        self.assertEqual(self.display.locator('img.slide-image--welcome').get_attribute('src'), './assets/welcome.png')
        self.assertTrue(self.display.locator('img.slide-image--welcome').evaluate('(el) => el.complete && el.naturalWidth > 0'))
        self.assertTrue(self.display.locator('img.slide-image--clean').evaluate('(el) => el.complete && el.naturalWidth > 0'))
        self.assertTrue(self.display.locator('img.slide-image--welcome').evaluate('el => { const clean = document.querySelector(\".slide-image--clean\"); return el.naturalWidth === clean.naturalWidth && el.naturalHeight === clean.naturalHeight; }'))
        self.assertEqual(self.display.locator('button,input,nav').count(), 0)
        self.assertTrue(self.display.locator('body').evaluate('(el) => getComputedStyle(el).cursor === "none"'))

    def test_01b_browser_fallback_retains_connection_status(self):
        # Native-only UI simplification must not hide browser presence.
        self.assertFalse(self.control.locator('#connection-status').is_hidden())
        self.assertFalse(self.control.locator('#connection-dot').is_hidden())
        expect(self.control.locator('.side-heading h2')).to_have_text('Publikumsansicht')

    def test_02_start_pause_resume_reset_return_and_sync(self):
        self.control.get_by_role('button',name='3 Min.').click()
        self.control.get_by_role('button',name='Countdown starten').click()
        expect(self.display.locator('#stage')).to_have_class(re.compile(r'is-timer'))
        self.assertEqual(self.control.locator('#status-badge').get_attribute('data-phase'),'running')
        self.display.wait_for_timeout(1300)
        self.assertNotEqual(self.display.locator('#timer-numbers').inner_text(), '03:00')
        self.control.get_by_role('button', name='Pausieren').click()
        expect(self.control.locator('#status-badge')).to_have_attribute('data-phase','paused')
        paused = self.display.locator('#timer-numbers').inner_text()
        ring = self.display.locator('#progress-ring').evaluate('(el) => el.style.strokeDashoffset')
        self.display.wait_for_timeout(1200)
        self.assertEqual(self.display.locator('#timer-numbers').inner_text(),paused)
        self.assertEqual(self.display.locator('#progress-ring').evaluate('(el) => el.style.strokeDashoffset'),ring)
        self.control.get_by_role('button', name='Fortsetzen').click()
        expect(self.control.locator('#status-badge')).to_have_attribute('data-phase','running')
        self.control.get_by_role('button', name='Zurücksetzen').click()
        expect(self.control.locator('#status-badge')).to_have_attribute('data-phase','paused')
        expect(self.display.locator('#timer-numbers')).to_have_text('03:00')
        self.control.get_by_role('button', name='Willkommensfolie anzeigen').click()
        expect(self.display.locator('#stage')).not_to_have_class(re.compile(r'is-timer'))
        self.assertEqual(self.display.locator('img.slide-image--welcome').get_attribute('src'),'./assets/welcome.png')

    def test_03_refresh_both_windows_without_restart(self):
        self.control.get_by_role('button',name='5 Min.').click()
        self.control.get_by_role('button',name='Countdown starten').click()
        self.control.wait_for_timeout(1250)
        self.display.reload()
        expect(self.display.locator('#stage')).to_have_class(re.compile(r'is-timer'))
        self.assertNotEqual(self.display.locator('#timer-numbers').inner_text(),'05:00')
        self.control.reload()
        expect(self.control.locator('#status-badge')).to_have_attribute('data-phase','running')
        self.assertNotEqual(self.control.locator('#current-time').inner_text(),'05:00')
        self.assertLessEqual(abs(self._seconds(self.display.locator('#timer-numbers').inner_text()) - self._seconds(self.control.locator('#current-time').inner_text())),1)

    def test_04_custom_duration_and_expiry(self):
        self.control.locator('#minutes').fill('0')
        self.control.locator('#seconds').fill('10')
        self.control.get_by_role('button',name='Countdown starten').click()
        expect(self.display.locator('#stage')).to_have_class(re.compile(r'is-timer'))
        expect(self.control.locator('#status-badge')).to_have_attribute('data-phase','completed',timeout=14000)
        expect(self.display.locator('#timer-numbers')).to_have_text('00:00')
        self.assertAlmostEqual(float(self.display.locator('#progress-ring').evaluate('(el) => el.style.strokeDashoffset')),0,delta=0.01)
        self.assertTrue(self.display.locator('#stage').evaluate('(el) => el.classList.contains("is-timer")'))

    def test_05_offline_after_load_does_not_stop_countdown(self):
        self.control.get_by_role('button',name='1 Min.').click()
        self.control.get_by_role('button',name='Countdown starten').click()
        self.context.set_offline(True)
        before = self._seconds(self.display.locator('#timer-numbers').inner_text())
        self.display.wait_for_timeout(1250)
        after = self._seconds(self.display.locator('#timer-numbers').inner_text())
        self.assertLess(after,before)
        self.context.set_offline(False)

    def test_06_custom_invalid_input_never_starts(self):
        self.control.locator('#minutes').fill('0')
        self.control.locator('#seconds').fill('9')
        self.control.get_by_role('button',name='Countdown starten').click()
        self.assertFalse(self.control.locator('#input-error').is_hidden())
        self.assertEqual(self.control.locator('#status-badge').get_attribute('data-phase'),'welcome')
        self.assertNotIn('is-timer',self.display.locator('#stage').get_attribute('class'))

    def test_07_controller_restart_keeps_display_running(self):
        self.control.get_by_role('button', name='3 Min.').click()
        self.control.get_by_role('button', name='Countdown starten').click()
        expect(self.display.locator('#stage')).to_have_class(re.compile(r'is-timer'))
        self.control.close()
        self.control = self.context.new_page()
        self.control.on('pageerror', lambda e: self.errors.append(f'restarted controller: {e}'))
        self.control.goto(BASE + '/control.html')
        expect(self.control.locator('#status-badge')).to_have_attribute('data-phase', 'running')
        self.assertLessEqual(abs(self._seconds(self.display.locator('#timer-numbers').inner_text()) - self._seconds(self.control.locator('#current-time').inner_text())), 1)
        self.control.get_by_role('button', name='Pausieren').click()
        expect(self.control.locator('#status-badge')).to_have_attribute('data-phase', 'paused')
        frozen = self.display.locator('#timer-numbers').inner_text()
        self.display.wait_for_timeout(1200)
        self.assertEqual(frozen, self.display.locator('#timer-numbers').inner_text())

    def test_08_local_server_cold_launch_without_external_requests(self):
        # Block all non-loopback HTTP requests while keeping localhost available.
        # This does not simulate a fully disabled network adapter.
        self.context.route(re.compile(r'^https?://(?!127\.0\.0\.1:18765(?:/|$))'), lambda route: route.abort())
        self.control.close()
        self.display.close()
        self.display = self.context.new_page()
        self.control = self.context.new_page()
        self.display.on('pageerror', lambda e: self.errors.append(f'offline display: {e}'))
        self.control.on('pageerror', lambda e: self.errors.append(f'offline controller: {e}'))
        self.display.goto(BASE + '/display.html')
        self.control.goto(BASE + '/control.html')
        self.assertTrue(self.display.locator('img.slide-image--welcome').evaluate('(el) => el.complete && el.naturalWidth > 0'))
        self.control.get_by_role('button', name='1 Min.').click()
        self.control.get_by_role('button', name='Countdown starten').click()
        expect(self.display.locator('#stage')).to_have_class(re.compile(r'is-timer'))

    def test_09_storage_write_denied_still_synchronizes_live(self):
        self.control.evaluate("""() => {
          const original = Storage.prototype.setItem;
          Storage.prototype.setItem = function(k, v) {
            if (k === 'ubf-koeln-projector-timer:state:v1') throw new DOMException('blocked', 'QuotaExceededError');
            return original.call(this, k, v);
          };
        }""")
        self.control.get_by_role('button', name='3 Min.').click()
        self.control.get_by_role('button', name='Countdown starten').click()
        expect(self.display.locator('#stage')).to_have_class(re.compile(r'is-timer'))
        expect(self.control.locator('#system-message')).to_be_visible()
        self.assertIn('Speichern nicht möglich', self.control.locator('#system-message').inner_text())

    def test_10_storage_failure_restart_new_session_reaches_display(self):
        self.control.add_init_script("""(() => {
          const original = Storage.prototype.setItem;
          Storage.prototype.setItem = function(k, v) {
            if (k === 'ubf-koeln-projector-timer:state:v1') throw new DOMException('blocked', 'QuotaExceededError');
            return original.call(this, k, v);
          };
        })();""")
        self.control.reload()
        self.control.get_by_role('button', name='3 Min.').click()
        self.control.get_by_role('button', name='Countdown starten').click()
        expect(self.display.locator('#stage')).to_have_class(re.compile(r'is-timer'))
        expect(self.display.locator('#timer-numbers')).to_have_text(re.compile(r'^0[23]:[0-5][0-9]$'))
        self.control.wait_for_timeout(100)
        self.control.reload()
        self.control.get_by_role('button', name='1 Min.').click()
        self.control.get_by_role('button', name='Countdown starten').click()
        expect(self.control.locator('#status-badge')).to_have_attribute('data-phase', 'running')
        expect(self.display.locator('#timer-numbers')).to_have_text(re.compile(r'^(?:01:00|00:[0-5][0-9])$'), timeout=2000)

    def test_11_second_controller_cannot_start_during_startup(self):
        second = self.context.new_page()
        second.on('pageerror', lambda e: self.errors.append(f'second controller: {e}'))
        try:
            second.goto(BASE + '/control.html')
            second.evaluate("() => document.querySelector('#start').click()")
            self.assertEqual(second.locator('#status-badge').get_attribute('data-phase'), 'welcome')
            self.assertNotIn('is-timer', self.display.locator('#stage').get_attribute('class'))
        finally:
            second.close()

    def test_12_restored_controller_must_not_operate_without_its_lease(self):
        # Model persisted pagehide/pageshow. A separate display page holds the
        # exclusive lock, making ownership assertions unambiguous.
        lock_name = 'ubf-koeln-projector-timer:single-controller:v1'
        self.control.wait_for_function("""async (name) => {
          const locks = await navigator.locks.query();
          return locks.held.some(lock => lock.name === name);
        }""", arg=lock_name, timeout=5000)
        self.control.evaluate("""() => window.dispatchEvent(new PageTransitionEvent(
          'pagehide', {persisted: true}))""")
        self.display.evaluate("""(name) => {
          navigator.locks.request(name, {mode: 'exclusive'}, async () => {
            window.__externalLockHeld = true;
            await new Promise(resolve => { window.__externalRelease = resolve; });
          });
        }""", lock_name)
        self.display.wait_for_function("() => window.__externalLockHeld === true", timeout=5000)
        self.control.evaluate("""() => window.dispatchEvent(new PageTransitionEvent(
          'pageshow', {persisted: true}))""")
        # Must fail closed until this controller actually owns the lock.
        expect(self.control.locator('#start')).to_be_disabled(timeout=2000)
        self.display.evaluate("() => window.__externalRelease()")
        expect(self.control.locator('#start')).to_be_enabled(timeout=5000)
        self.control.get_by_role('button', name='3 Min.').click()
        self.control.get_by_role('button', name='Countdown starten').click()
        expect(self.display.locator('#stage')).to_have_class(re.compile(r'is-timer'))

    def test_13_restored_display_resubscribes_to_controller_updates(self):
        # Model persisted pagehide/pageshow, without claiming a real BFCache hit.
        self.display.evaluate("""() => window.dispatchEvent(new PageTransitionEvent(
          'pagehide', {persisted: true}))""")
        self.display.evaluate("""() => window.dispatchEvent(new PageTransitionEvent(
          'pageshow', {persisted: true}))""")
        self.control.get_by_role('button', name='3 Min.').click()
        self.control.get_by_role('button', name='Countdown starten').click()
        expect(self.display.locator('#stage')).to_have_class(re.compile(r'is-timer'), timeout=3000)

    def test_14_no_web_locks_fallback_warns_and_disables_duplicate_controllers(self):
        # Fallback detection is advisory, not an atomic lock; test the actual
        # supported safety behavior after the two tabs have exchanged presence.
        fallback = self.browser.new_context(viewport={'width':1536,'height':864})
        try:
            fallback.add_init_script("""(() => {
              Object.defineProperty(navigator, 'locks', {value: undefined, configurable: true});
            })();""")
            first = fallback.new_page()
            first.goto(BASE + '/control.html')
            self.assertFalse(first.evaluate('() => Boolean(navigator.locks?.request)'))
            second = fallback.new_page()
            second.goto(BASE + '/control.html')
            expect(first.locator('#start')).to_be_disabled(timeout=6000)
            expect(second.locator('#start')).to_be_disabled(timeout=6000)
            expect(first.locator('#system-message')).to_contain_text('Mehrere Steuerfenster')
            second.close()
            expect(first.locator('#start')).to_be_enabled(timeout=8000)
        finally:
            fallback.close()

    def test_15_native_handoff_does_not_reset_running_countdown(self):
        # Real controller code with a mocked Tauri command bridge. The
        # browser display exercises actual BroadcastChannel/localStorage.
        self.control.add_init_script(script=NATIVE_BRIDGE_MOCK)
        self.control.reload()
        project = self.control.get_by_role('button', name='Auf Beamer projizieren')
        expect(project).to_be_enabled(timeout=4000)
        project.click()
        expect(self.control.get_by_role('button', name='Beamer freigeben')).to_be_visible()
        self.assertIn('startet nicht automatisch',
                      self.control.locator('#native-projector-state').inner_text())
        self.assertTrue(self.control.evaluate('window.__nativeActive'))
        self.assertFalse(self.control.evaluate('window.__nativePopupWasCalled'))
        self.control.get_by_role('button', name='3 Min.').click()
        self.control.get_by_role('button', name='Countdown starten').click()
        expect(self.display.locator('#stage')).to_have_class(re.compile('is-timer'))
        self.control.get_by_role('button', name='Beamer freigeben').click()
        expect(self.control.get_by_role('button', name='Beamer freigeben')).to_be_hidden()
        expect(self.control.locator('#status-badge')).to_have_attribute('data-phase', 'running')
        self.assertFalse(self.control.evaluate('window.__nativeActive'))

        # Simulate the native display being closed, then reopened after the
        # PowerPoint handoff: the controller's authoritative timer survives.
        self.display.close()
        self.display = self.context.new_page()
        self.display.on('pageerror', lambda e: self.errors.append(f'reopened display: {e}'))
        self.display.goto(BASE + '/display.html')
        expect(self.display.locator('#stage')).to_have_class(re.compile('is-timer'), timeout=4000)
        project.click()
        expect(self.control.get_by_role('button', name='Beamer freigeben')).to_be_visible()
        calls = self.control.evaluate('window.__nativeCalls')
        self.assertTrue(any(call['command'] == 'open_projector' and
                            call['args']['monitorKey'] == 'PROJECTOR-A|1920|0|1920|1080'
                            for call in calls))
        self.assertLessEqual(abs(self._seconds(self.display.locator('#timer-numbers').inner_text())
                                 - self._seconds(self.control.locator('#current-time').inner_text())), 1)

    def test_16_native_display_rearrangement_refuses_stale_target(self):
        # A layout change between target listing and clicking MUST NOT open a
        # different monitor. The Rust resolver separately tests this invariant.
        self.control.add_init_script(script=NATIVE_BRIDGE_MOCK)
        self.control.reload()
        expect(self.control.get_by_role('button', name='Auf Beamer projizieren')).to_be_enabled()
        self.control.evaluate("""() => {
          window.__nativeTargets = [
            {id:'MONITOR-A|-1920|0|1920|1080', name:'Monitor A', width:1920, height:1080},
            {id:'PROJECTOR-B|1920|0|1280|720', name:'Projektor B', width:1280, height:720}
          ];
          window.dispatchEvent(new Event('focus'));
        }""")
        picker = self.control.locator('#native-monitor')
        expect(picker).to_be_visible(timeout=4000)
        picker.select_option('PROJECTOR-B|1920|0|1280|720')
        self.control.evaluate("""() => {
          window.__nativeTargets = [
            {id:'PROJECTOR-B|-1280|0|1280|720', name:'Projektor B', width:1280, height:720},
            {id:'MONITOR-A|1920|0|1920|1080', name:'Monitor A', width:1920, height:1080}
          ];
        }""")
        self.control.get_by_role('button', name='Auf Beamer projizieren').click()
        expect(self.control.locator('#native-projector-state')).to_contain_text(
            'Die Beameranordnung hat sich geändert.', timeout=2000)
        self.assertFalse(self.control.evaluate('window.__nativeActive'))
        self.assertFalse(self.control.evaluate('window.__nativePopupWasCalled'))

    def test_17_in_flight_status_must_not_erase_a_new_projector_handoff(self):
        # Deterministically reproduce a status request started before the
        # operator clicks 'Auf Beamer projizieren'. Its late "inactive" reply
        # must not hide Beamer freigeben after the actual opening succeeds.
        self.control.add_init_script(script=NATIVE_BRIDGE_MOCK)
        self.control.reload()
        project = self.control.get_by_role('button', name='Auf Beamer projizieren')
        release = self.control.get_by_role('button', name='Beamer freigeben')
        expect(project).to_be_enabled(timeout=4000)
        self.control.evaluate("""() => {
          window.__nativeDelayNextStatus = true;
          window.dispatchEvent(new Event('focus'));
        }""")
        self.control.wait_for_function('window.__nativePendingStatus.length === 1')
        project.click()
        expect(release).to_be_visible(timeout=2000)
        self.control.evaluate('window.__nativePendingStatus.shift()()')
        self.control.wait_for_timeout(100)
        # On the old native-projector.js, the stale poll sets active=false,
        # hiding the release control during an ongoing service.
        self.assertTrue(release.is_visible(),
                        'Stale status concealed Beamer freigeben after successful projection')
        self.assertTrue(self.control.evaluate('window.__nativeActive'))

    def test_18_in_flight_status_must_not_resurrect_a_released_projection(self):
        # Opposite handoff race: the cached "active" answer must not revive
        # release controls after Beamer freigeben has closed the projection.
        self.control.add_init_script(script=NATIVE_BRIDGE_MOCK)
        self.control.reload()
        project = self.control.get_by_role('button', name='Auf Beamer projizieren')
        release = self.control.get_by_role('button', name='Beamer freigeben')
        expect(project).to_be_enabled(timeout=4000)
        project.click()
        expect(release).to_be_visible(timeout=2000)
        self.control.evaluate("""() => {
          window.__nativeDelayNextStatus = true;
          window.dispatchEvent(new Event('focus'));
        }""")
        self.control.wait_for_function('window.__nativePendingStatus.length === 1')
        release.click()
        expect(project).to_be_enabled(timeout=2000)
        expect(release).to_be_hidden(timeout=2000)
        self.control.evaluate('window.__nativePendingStatus.shift()()')
        self.control.wait_for_timeout(100)
        self.assertTrue(project.is_enabled(),
                        'Stale status prevents reprojecting after release')
        self.assertTrue(release.is_hidden(),
                        'Stale active status resurrected release control after handoff')
        self.assertFalse(self.control.evaluate('window.__nativeActive'))

    def test_19_responsive_regie_layout_preserves_real_timer_controls(self):
        # Desktop: real controls remain primary; audience preview is separate.
        left = self.control.locator('.main-panel').bounding_box()
        right = self.control.locator('.side-panel').bounding_box()
        self.assertLess(left['x'] + left['width'], right['x'] + 2)
        self.assertTrue(self.control.locator('#open-display').is_visible())
        self.assertTrue(self.control.locator('#mini-preview img.preview-welcome').evaluate(
            '(img) => img.complete && img.naturalWidth > 0'))
        self.assertTrue(self.control.evaluate(
            'document.documentElement.scrollWidth <= window.innerWidth + 1'))

        # Compact viewport must stack the actual controls, not merely crop
        # the operator panel or show a horizontal scroll bar.
        self.control.set_viewport_size({'width': 390, 'height': 844})
        left = self.control.locator('.main-panel').bounding_box()
        right = self.control.locator('.side-panel').bounding_box()
        self.assertGreaterEqual(right['y'], left['y'] + left['height'] - 2)
        self.assertTrue(self.control.evaluate(
            'document.documentElement.scrollWidth <= window.innerWidth + 1'))
        self.assertTrue(self.control.locator('#reset').is_hidden())
        self.assertTrue(self.control.locator('#welcome').is_hidden())
        self.assertGreaterEqual(self.control.locator('#start').bounding_box()['height'], 40)
        self.assertGreaterEqual(self.control.locator('.preset.active').bounding_box()['height'], 40)
        main_w = self.control.locator('.main-panel').bounding_box()['width']
        self.assertGreater(self.control.locator('#start').bounding_box()['width'], main_w * 0.75)
        self.control.get_by_role('button', name='3 Min.').click()
        self.control.get_by_role('button', name='Countdown starten').click()
        expect(self.control.locator('#status-badge')).to_have_attribute('data-phase', 'running')
        for selector in ('#pause', '#reset', '#welcome'):
            self.assertGreaterEqual(self.control.locator(selector).bounding_box()['height'], 40)
        self.control.get_by_role('button', name='Pausieren').click()
        expect(self.control.locator('#status-badge')).to_have_attribute('data-phase', 'paused')
        self.control.get_by_role('button', name='Willkommensfolie anzeigen').click()
        expect(self.control.locator('#status-badge')).to_have_attribute('data-phase', 'welcome')
        self.assertTrue(self.control.locator('#reset').is_hidden())
        self.assertTrue(self.control.locator('#welcome').is_hidden())

    def test_20_native_projector_actions_are_grouped_next_to_preview(self):
        # Browser-only Tauri mock: verifies DOM order, accessibility and
        # state transitions; does not claim physical native WebView2 behavior.
        self.control.add_init_script(script=NATIVE_BRIDGE_MOCK)
        self.control.reload()
        self.control.set_viewport_size({'width': 390, 'height': 844})
        project = self.control.get_by_role('button', name='Auf Beamer projizieren')
        release = self.control.get_by_role('button', name='Beamer freigeben')
        expect(project).to_be_enabled(timeout=4000)
        self.assertTrue(self.control.evaluate(
            "document.body.classList.contains('native-mode')"))
        self.assertTrue(self.control.locator('.topbar-actions').is_hidden())
        # Browser BroadcastChannel peer presence cannot certify native
        # projector visibility. Never show contradictory connection claims.
        expect(self.control.locator('.side-heading h2')).to_have_text('Folienvorschau')
        expect(self.control.locator('.side-panel')).to_have_attribute('aria-label','Folienvorschau')
        self.assertTrue(self.control.locator('#connection-status').is_hidden())
        self.assertTrue(self.control.locator('#connection-dot').is_hidden())
        expect(self.control.locator('.preview-caption')).to_contain_text(
            'noch nicht auf den Beamer projiziert')
        self.assertTrue(self.control.evaluate("""() => {
          const panel = document.querySelector('.native-projection');
          return panel?.contains(document.querySelector('#open-display')) &&
                 panel.contains(document.querySelector('#native-projector-release')) &&
                 panel.parentElement?.classList.contains('layout') &&
                 document.querySelector('.guide').hidden;
        }"""))
        self.assertTrue(self.control.evaluate(
            'document.documentElement.scrollWidth <= window.innerWidth + 1'))
        # Same native button is on the initial screen, before the timer,
        # not after the entire preview section as in the baseline screenshot.
        self.assertTrue(self.control.evaluate("""() => {
          const b = document.querySelector('#open-display').getBoundingClientRect();
          const timer = document.querySelector('.main-panel').getBoundingClientRect();
          const panel = document.querySelector('.native-projection').getBoundingClientRect();
          return b.top >= 0 && b.bottom <= innerHeight &&
                 panel.bottom < timer.top && b.top < timer.top;
        }"""))
        self.assertTrue(self.control.evaluate("""() => {
          const b = document.querySelector('#start').getBoundingClientRect();
          return b.top >= 0 && b.bottom <= innerHeight;
        }"""))
        # No resize-driven button clone or lost event handler.
        self.control.set_viewport_size({'width':1366,'height':768})
        self.assertTrue(self.control.evaluate("""() => {
          const timer = document.querySelector('.main-panel').getBoundingClientRect();
          const panel = document.querySelector('.native-projection').getBoundingClientRect();
          const preview = document.querySelector('.side-panel').getBoundingClientRect();
          return panel.left > timer.right &&
                 Math.abs(panel.left-preview.left) <= 2 &&
                 panel.bottom < preview.top &&
                 document.querySelectorAll('#open-display').length === 1 &&
                 document.querySelectorAll('#native-projector-release').length === 1;
        }"""))
        self.control.set_viewport_size({'width':390,'height':844})
        project.click()
        expect(release).to_be_visible(timeout=2000)
        expect(self.control.locator('.native-projection')).to_have_attribute('data-status', 'active')
        expect(self.control.locator('.preview-caption')).to_contain_text(
            'am tatsächlichen Beamer prüfen')
        release.click()
        expect(project).to_be_enabled(timeout=2000)
        expect(release).to_be_hidden(timeout=2000)
        expect(self.control.locator('.native-projection')).to_have_attribute('data-status', 'ready')
        expect(self.control.locator('.preview-caption')).to_contain_text(
            'noch nicht auf den Beamer projiziert')
        self.assertTrue(self.control.evaluate(
            'document.documentElement.scrollWidth <= window.innerWidth + 1'))

    @unittest.skipUnless(os.environ.get('UBF_CAPTURE_UI') == '1', 'CI visual evidence only')
    def test_21_capture_operator_console_visual_qa(self):
        """Save actual Chromium screenshots with original Canva assets in CI.

        Screenshots are CI-only transient review evidence, never a deployment
        or a changed user-facing image. Separate browser/native bridge mock.
        """
        out = ROOT / 'artifacts' / 'ui-qa'
        out.mkdir(parents=True, exist_ok=True)
        for label, width, height in [
            ('desktop-1366x768', 1366, 768),
            ('laptop-1120x800', 1120, 800),
            ('compact-390x844', 390, 844),
        ]:
            self.control.set_viewport_size({'width':width, 'height':height})
            self.control.screenshot(path=str(out / (label + '.png')),
                                    full_page=True, animations='disabled')
            metrics = self.control.evaluate("""() => {
              const p = document.querySelector('.main-panel').getBoundingClientRect();
              const s = document.querySelector('.side-panel').getBoundingClientRect();
              const a = document.querySelector('#start').getBoundingClientRect();
              return {width: innerWidth, height: innerHeight,
                      scrollWidth: document.documentElement.scrollWidth,
                      scrollHeight: document.documentElement.scrollHeight,
                      mainBottom: Math.round(p.bottom),
                      sideTop: Math.round(s.top),
                      startY: Math.round(a.top)};
            }""")
            print('UBF_VISUAL_QA', label, metrics, flush=True)

        self.control.add_init_script(script=NATIVE_BRIDGE_MOCK)
        self.control.reload()
        expect(self.control.locator('.native-projection')).to_be_visible()
        for label, width, height in [
            ('native-desktop-1366x768', 1366, 768),
            ('native-compact-390x844', 390, 844),
        ]:
            self.control.set_viewport_size({'width':width, 'height':height})
            expect(self.control.get_by_role('button', name='Auf Beamer projizieren')).to_be_enabled()
            self.control.screenshot(path=str(out / (label + '.png')),
                                    full_page=True, animations='disabled')
            metrics = self.control.evaluate("""() => {
              const panel = document.querySelector('.native-projection').getBoundingClientRect();
              const project = document.querySelector('#open-display').getBoundingClientRect();
              const start = document.querySelector('#start').getBoundingClientRect();
              return {viewport:innerWidth, projectorY:Math.round(panel.y),
                      projectorButtonBottom:Math.round(project.bottom),
                      timerStartBottom:Math.round(start.bottom),
                      horizontalOverflow:document.documentElement.scrollWidth-innerWidth};
            }""")
            print('UBF_NATIVE_ACTION_VISIBILITY', label, metrics, flush=True)
        self.control.set_viewport_size({'width':1120, 'height':800})
        self.control.get_by_role('button', name='3 Min.').click()
        self.control.get_by_role('button', name='Countdown starten').click()
        self.control.screenshot(path=str(out / 'native-running-1120x800.png'),
                                full_page=True, animations='disabled')
        self.control.get_by_role('button', name='Pausieren').click()
        self.control.set_viewport_size({'width':390, 'height':844})
        self.control.screenshot(path=str(out / 'native-paused-390x844.png'),
                                full_page=True, animations='disabled')
        print('UBF_VISUAL_QA captured 7 screenshots; real church hardware NOT_TESTED', flush=True)

    def test_23_native_operator_busy_and_active_actions_are_truthful(self):
        self.control.add_init_script(script=NATIVE_BRIDGE_MOCK)
        self.control.reload()
        self.control.set_viewport_size({'width':390,'height':844})
        panel = self.control.locator('.native-projection')
        project = self.control.locator('#open-display')
        release = self.control.locator('#native-projector-release')
        expect(project).to_be_enabled(timeout=4000)
        self.control.evaluate('window.__nativeHoldOpen = true')
        project.click()
        self.control.wait_for_function('window.__nativePendingActions.length === 1')
        expect(panel).to_have_attribute('data-status','busy')
        expect(panel).to_have_attribute('aria-busy','true')
        expect(project).to_contain_text('wird geöffnet')
        expect(project).to_be_disabled()
        expect(self.control.locator('#native-projector-state')).to_contain_text('wird')
        self.assertTrue(release.is_hidden())
        self.control.evaluate('window.__nativePendingActions.shift()()')
        expect(panel).to_have_attribute('data-status','active')
        expect(panel).to_have_attribute('aria-busy','false')
        expect(release).to_be_visible()
        # The screenshot baseline showed "BEAMER · AKTIV" beside the
        # browser-only "Kein Projektionsfenster erkannt"; this is forbidden.
        self.assertTrue(self.control.locator('#connection-status').is_hidden())
        expect(self.control.locator('.side-heading h2')).to_have_text('Folienvorschau')
        self.assertTrue(project.is_hidden(), 'Inactive disabled opener wastes native action space')
        self.control.evaluate('window.__nativeHoldRelease = true')
        release.click()
        self.control.wait_for_function('window.__nativePendingActions.length === 1')
        expect(panel).to_have_attribute('data-status','busy')
        expect(release).to_contain_text('wird freigegeben')
        expect(release).to_be_disabled()
        self.assertTrue(project.is_hidden())
        self.control.evaluate('window.__nativePendingActions.shift()()')
        expect(panel).to_have_attribute('data-status','ready')
        expect(project).to_be_enabled(timeout=2000)
        expect(release).to_be_hidden()

    def test_24_native_command_error_persists_until_retry(self):
        self.control.add_init_script(script=NATIVE_BRIDGE_MOCK)
        self.control.reload()
        panel = self.control.locator('.native-projection')
        project = self.control.locator('#open-display')
        release = self.control.locator('#native-projector-release')
        expect(project).to_be_enabled(timeout=4000)
        self.control.evaluate("window.__nativeForcedOpenError = 'Die Beameranordnung hat sich geändert.'")
        project.click()
        expect(panel).to_have_attribute('data-status','error')
        expect(self.control.locator('#native-projector-state')).to_contain_text('Beameranordnung')
        self.control.wait_for_timeout(3300)
        expect(panel).to_have_attribute('data-status','error')
        expect(self.control.locator('#native-projector-state')).to_contain_text('Beameranordnung')
        self.control.evaluate("window.__nativeForcedOpenError = ''")
        project.click()
        expect(panel).to_have_attribute('data-status','active')
        expect(release).to_be_visible()
        expect(self.control.locator('#native-projector-state')).not_to_contain_text('Beameranordnung')

    def test_25_native_monitor_poll_failure_recovers_without_wrong_screen(self):
        self.control.add_init_script(script=NATIVE_BRIDGE_MOCK)
        self.control.reload()
        panel = self.control.locator('.native-projection')
        project = self.control.locator('#open-display')
        expect(project).to_be_enabled(timeout=4000)
        self.control.evaluate("""() => {
            window.__nativeForcedStatusError = 'Windows-Status ist nicht verfügbar.';
            window.dispatchEvent(new Event('focus'));
        }""")
        expect(panel).to_have_attribute('data-status','error',timeout=2500)
        expect(project).to_be_disabled()
        expect(self.control.locator('#native-projector-state')).to_contain_text('Windows-Status')
        self.control.evaluate("""() => {
            window.__nativeForcedStatusError = '';
            window.dispatchEvent(new Event('focus'));
        }""")
        expect(project).to_be_enabled(timeout=2500)
        expect(panel).to_have_attribute('data-status','ready')
        self.assertTrue(self.control.evaluate(
            'document.documentElement.scrollWidth <= window.innerWidth + 1'))

    @unittest.skipUnless(os.environ.get('UBF_CAPTURE_UI') == '1', 'CI visual evidence only')
    def test_22_capture_native_projector_operator_states(self):
        # Browser Chromium capture with a controlled native bridge, not a
        # Windows projector or a screenshot of PowerPoint/Canva.
        out = ROOT / 'artifacts' / 'ui-qa'
        out.mkdir(parents=True, exist_ok=True)
        self.control.add_init_script(script=NATIVE_BRIDGE_MOCK)
        self.control.reload()
        self.control.set_viewport_size({'width':390,'height':844})
        panel = self.control.locator('.native-projection')
        project = self.control.locator('#open-display')
        release = self.control.locator('#native-projector-release')
        expect(project).to_be_enabled(timeout=4000)
        self.control.screenshot(path=str(out / 'state-ready-390x844.png'),
                                full_page=True, animations='disabled')

        self.control.evaluate('window.__nativeHoldOpen = true')
        project.click()
        self.control.wait_for_function('window.__nativePendingActions.length === 1')
        expect(panel).to_have_attribute('data-status','busy')
        self.control.screenshot(path=str(out / 'state-opening-390x844.png'),
                                full_page=True, animations='disabled')
        self.control.evaluate('window.__nativePendingActions.shift()()')
        expect(release).to_be_visible(timeout=2000)
        expect(panel).to_have_attribute('data-status','active')
        self.control.screenshot(path=str(out / 'state-active-390x844.png'),
                                full_page=True, animations='disabled')

        self.control.evaluate('window.__nativeHoldRelease = true')
        release.click()
        self.control.wait_for_function('window.__nativePendingActions.length === 1')
        self.control.screenshot(path=str(out / 'state-releasing-390x844.png'),
                                full_page=True, animations='disabled')
        self.control.evaluate('window.__nativePendingActions.shift()()')
        expect(project).to_be_enabled(timeout=2000)

        self.control.evaluate("""() => {
          window.__nativeTargets = [];
          window.dispatchEvent(new Event('focus'));
        }""")
        expect(panel).to_have_attribute('data-status','missing',timeout=3000)
        self.control.screenshot(path=str(out / 'state-disconnected-390x844.png'),
                                full_page=True, animations='disabled')

        self.control.evaluate("""() => {
          window.__nativeTargets = [
            {id:'PROJECTOR-A|1920|0|1920|1080',name:'Projektor A',width:1920,height:1080}
          ];
          window.dispatchEvent(new Event('focus'));
        }""")
        expect(project).to_be_enabled(timeout=3000)
        self.control.evaluate("window.__nativeForcedOpenError = 'Die Beameranordnung hat sich geändert.'")
        project.click()
        expect(panel).to_have_attribute('data-status','error',timeout=2000)
        self.control.screenshot(path=str(out / 'state-error-390x844.png'),
                                full_page=True, animations='disabled')
        self.control.wait_for_timeout(3300)
        expect(panel).to_have_attribute('data-status','error')
        self.control.screenshot(path=str(out / 'state-error-after-poll-390x844.png'),
                                full_page=True, animations='disabled')
        print('UBF_NATIVE_STATES captured ready/opening/active/releasing/disconnected/persistent error',flush=True)

    def test_27_offline_rehearsal_form_records_real_observations_only(self):
        # This is a local file worksheet, not the projector. Verify no
        # fabricated PASS and that save/restore works without a server.
        page = self.context.new_page()
        page.goto((ROOT / 'rehearsal' / 'ACCEPTANCE_OFFLINE.html').as_uri())
        self.assertEqual(page.locator('.probe').count(), 8)
        self.assertEqual(page.locator('.probe-head select').evaluate_all(
            "(items) => items.filter(x => x.value === 'NOT_TESTED').length"), 8)
        self.assertEqual(page.locator('.probe select').count(), 12)
        expect(page.locator('#summary')).to_contain_text('0 von 8 geprüft')
        expect(page.locator('#summary')).to_contain_text('Live: NO_GO')
        self.assertTrue(page.locator('#summary').is_visible())
        page.locator('select[aria-label="W05 Status"]').select_option('FAIL')
        page.locator('.probe').nth(4).locator('textarea').first.fill(
            'PowerPoint zeigte den Desktop für zwei Sekunden')
        page.locator('#tester').fill('Vor-Ort-Test')
        expect(page.locator('#summary')).to_contain_text('1 von 8 geprüft')
        expect(page.locator('#summary')).to_contain_text('1 FAIL')
        with page.expect_download() as d:
            page.locator('#export').click()
        downloaded = d.value
        payload = downloaded.path().read_text(encoding='utf-8')
        import json
        data = json.loads(payload)
        self.assertEqual(data['schema'], 1)
        self.assertEqual(data['live_service'], 'NO_GO')
        self.assertEqual(data['steps']['W05']['status'], 'FAIL')
        self.assertEqual(data['steps']['W01']['status'], 'NOT_TESTED')
        page.locator('select[aria-label="W05 Status"]').select_option('NOT_TESTED')
        page.locator('#tester').fill('')
        page.locator('#import').set_input_files({
            'name':'results.json','mimeType':'application/json','buffer':payload.encode('utf-8')
        })
        expect(page.locator('select[aria-label="W05 Status"]')).to_have_value('FAIL')
        expect(page.locator('#tester')).to_have_value('Vor-Ort-Test')
        # A different build must not inherit approval/status from this file.
        data['source_commit'] = 'f' * 40
        page.locator('#import').set_input_files({
            'name':'wrong.json','mimeType':'application/json',
            'buffer':json.dumps(data).encode('utf-8')
        })
        expect(page.locator('#msg')).to_contain_text('nicht übernommen')
        expect(page.locator('#summary')).to_contain_text('Live: NO_GO')
        # A return visit must clearly identify an earlier rehearsal's results.
        # Reset requires confirmation and cannot carry the old FAIL or notes
        # into a new physical acceptance session.
        saved_at_before_reload = page.evaluate("""() => {
            const key='ubf-physical-rehearsal-v1-'+document.getElementById('build-sha').textContent;
            return JSON.parse(localStorage.getItem(key)).saved_at;
        }""")
        page.reload()
        saved_at_after_reload = page.evaluate("""() => {
            const key='ubf-physical-rehearsal-v1-'+document.getElementById('build-sha').textContent;
            return JSON.parse(localStorage.getItem(key)).saved_at;
        }""")
        self.assertEqual(saved_at_before_reload, saved_at_after_reload,
                         'Simply reopening must not falsify the last-saved timestamp')
        expect(page.locator('#restored-session')).to_be_visible()
        expect(page.locator('#restored-detail')).to_contain_text('früheren Probe')
        expect(page.locator('select[aria-label="W05 Status"]')).to_have_value('FAIL')
        page.once('dialog', lambda dialog: dialog.dismiss())
        page.locator('#new-session').click()
        expect(page.locator('select[aria-label="W05 Status"]')).to_have_value('FAIL')
        page.once('dialog', lambda dialog: dialog.accept())
        page.locator('#new-session').click()
        expect(page.locator('#restored-session')).to_be_hidden()
        expect(page.locator('select[aria-label="W05 Status"]')).to_have_value('NOT_TESTED')
        expect(page.locator('#tester')).to_have_value('')
        expect(page.locator('#summary')).to_contain_text('0 von 8 geprüft')
        page.reload()
        expect(page.locator('#restored-session')).to_be_hidden()
        expect(page.locator('#summary')).to_contain_text('0 von 8 geprüft')
        page.close()

    def test_28_handoff_pass_requires_both_observed_scenarios(self):
        # Current worksheet previously accepted W05/W06 PASS without either
        # handoff scenario being recorded; never treat that as qualified.
        page = self.context.new_page()
        page.goto((ROOT / 'rehearsal' / 'ACCEPTANCE_OFFLINE.html').as_uri())
        for id, index in [('W05', 4), ('W06', 5)]:
            row = page.locator('.probe').nth(index)
            status = page.locator(f'select[aria-label="{id} Status"]')
            status.select_option('PASS')
            expect(status).to_have_value('NOT_TESTED')
            expect(row.locator('.evidence-hint')).to_contain_text('nicht übernommen')
            notes = row.locator('textarea')
            notes.nth(1).fill('Erste Variante tatsächlich beobachtet')
            status.select_option('PASS')
            expect(status).to_have_value('NOT_TESTED')
            notes.nth(2).fill('Zweite Variante tatsächlich beobachtet')
            # Notes alone are not a verdict. Both scenarios must be marked PASS.
            status.select_option('PASS')
            expect(status).to_have_value('NOT_TESTED')
            for field in (['prepared','after'] if id=='W05' else ['full','presenter']):
                row.locator(f'select[aria-label="{id} {field} Ergebnis"]').select_option('PASS')
            status.select_option('PASS')
            expect(status).to_have_value('PASS')
            notes.nth(1).fill('')
            expect(status).to_have_value('NOT_TESTED')

        # Legacy JSON must remain importable without rewriting its raw
        # historical PASS, but the UI/export must flag missing evidence.
        legacy = page.evaluate("""() => ({
            schema:1,source_commit:document.getElementById('build-sha').textContent,
            steps:{W05:{status:'PASS',observation:'Alte Gesamtbewertung',
                        extra:{prepared:'',after:''}}},
            meta:{tester:'Historischer Test'},live_service:'NO_GO'
        })""")
        import json
        page.locator('#import').set_input_files({
            'name':'legacy.json','mimeType':'application/json',
            'buffer':json.dumps(legacy).encode('utf-8')
        })
        expect(page.locator('select[aria-label="W05 Status"]')).to_have_value('PASS')
        expect(page.locator('#summary')).to_contain_text('W05 PASS ohne vollständige Belege')
        expect(page.locator('.probe').nth(4)).to_have_attribute('data-status','unqualified')
        with page.expect_download() as d:
            page.locator('#export').click()
        saved = json.loads(d.value.path().read_text(encoding='utf-8'))
        self.assertIn('W05', saved['evidence_gaps'])
        self.assertEqual(saved['steps']['W05']['status'], 'PASS')
        self.assertEqual(saved['steps']['W05']['observation'], 'Alte Gesamtbewertung')
        self.assertEqual(saved['live_service'], 'NO_GO')
        page.close()

    def test_29_handoff_verdicts_fail_closed_and_legacy_json_remains(self):
        # A nonempty note can describe a failure. Each scenario therefore
        # needs a distinct human-selected verdict before overall PASS.
        import json
        page = self.context.new_page()
        page.goto((ROOT / 'rehearsal' / 'ACCEPTANCE_OFFLINE.html').as_uri())
        w05 = page.locator('.probe').nth(4)
        summary = page.locator('#summary')
        overall = page.locator('select[aria-label="W05 Status"]')
        first = w05.locator('select[aria-label="W05 prepared Ergebnis"]')
        second = w05.locator('select[aria-label="W05 after Ergebnis"]')
        notes = w05.locator('textarea')
        notes.nth(1).fill('Beamer zeigte die richtige Publikumsfolie')
        notes.nth(2).fill('Nach Freigabe zeigte sich kurz der Desktop')
        first.select_option('PASS')
        second.select_option('FAIL')
        expect(overall).to_have_value('FAIL')
        overall.select_option('PASS')
        expect(overall).to_have_value('FAIL')  # A known failed handoff stays FAIL
        expect(summary).to_contain_text('1 FAIL')
        expect(summary).to_contain_text('Live: NO_GO')
        second.select_option('PASS')
        overall.select_option('PASS')
        expect(overall).to_have_value('PASS')
        second.select_option('FAIL')
        expect(overall).to_have_value('FAIL')
        second.select_option('PASS')
        expect(overall).to_have_value('FAIL')  # Never auto-promote a failed test
        overall.select_option('PASS')
        expect(overall).to_have_value('PASS')
        notes.nth(1).fill('')
        expect(overall).to_have_value('NOT_TESTED')
        with page.expect_download() as dl:
            page.locator('#export').click()
        exported = json.loads(dl.value.path().read_text(encoding='utf-8'))
        self.assertEqual(exported['schema'], 1)
        self.assertEqual(exported['steps']['W05']['extra_status'],
                         {'prepared':'PASS','after':'PASS'})
        self.assertEqual(exported['steps']['W05']['status'], 'NOT_TESTED')
        self.assertEqual(exported['live_service'], 'NO_GO')

        # Import old schema-1 data with both narrative notes: no per-scenario
        # verdicts existed then, so preserve the raw historical PASS but flag it.
        legacy = {
            'schema':1,
            'source_commit':page.locator('#build-sha').text_content(),
            'steps':{'W06':{'status':'PASS','observation':'Historische Bewertung',
                            'extra':{'full':'Vollbild beobachtet',
                                     'presenter':'Präsentationsansicht beobachtet'}}},
            'meta':{'tester':'Altdaten'},
            'live_service':'NO_GO'
        }
        page.locator('#import').set_input_files({
            'name':'old.json','mimeType':'application/json',
            'buffer':json.dumps(legacy).encode('utf-8')
        })
        w06 = page.locator('.probe').nth(5)
        expect(page.locator('select[aria-label="W06 Status"]')).to_have_value('PASS')
        expect(w06.locator('select[aria-label="W06 full Ergebnis"]')).to_have_value('NOT_TESTED')
        expect(w06).to_have_attribute('data-status','unqualified')
        expect(summary).to_contain_text('W06 PASS ohne vollständige Belege')
        with page.expect_download() as dl:
            page.locator('#export').click()
        preserved = json.loads(dl.value.path().read_text(encoding='utf-8'))
        self.assertIn('W06', preserved['evidence_gaps'])
        self.assertEqual(preserved['steps']['W06']['status'], 'PASS')
        self.assertEqual(preserved['steps']['W06']['observation'], 'Historische Bewertung')
        self.assertEqual(preserved['steps']['W06']['extra']['full'], 'Vollbild beobachtet')
        self.assertEqual(preserved['steps']['W06']['extra_status'],
                         {'full':'NOT_TESTED','presenter':'NOT_TESTED'})
        page.close()

    def test_30_historical_pass_with_failed_variant_cannot_hide_fail(self):
        # Reproduction on previous HEAD: importing a historical top-level
        # PASS with a failed scenario left the summary at 0 FAIL, and editing
        # the scenario while legacyPass was set did not update overall status.
        import json
        page = self.context.new_page()
        page.goto((ROOT / 'rehearsal' / 'ACCEPTANCE_OFFLINE.html').as_uri())
        source = page.locator('#build-sha').text_content()
        for code, index, fields in [('W05',4,('prepared','after')),
                                    ('W06',5,('full','presenter'))]:
            old = {'schema':1,'source_commit':source,
                   'meta':{'tester':'Historische Probe'},
                   'steps':{code:{'status':'PASS',
                                 'observation':'Früherer Gesamtstatus',
                                 'extra':{fields[0]:'Fehler am Beamer beobachtet',
                                          fields[1]:'Noch nicht beurteilt'},
                                 'extra_status':{fields[0]:'FAIL',fields[1]:'NOT_TESTED'}}},
                   'live_service':'NO_GO'}
            page.locator('#import').set_input_files({
                'name':'historical.json','mimeType':'application/json',
                'buffer':json.dumps(old).encode('utf-8')
            })
            overall = page.locator(f'select[aria-label="{code} Status"]')
            row = page.locator('.probe').nth(index)
            expect(overall).to_have_value('PASS')  # Historical raw value unchanged
            expect(row).to_have_attribute('data-status','FAIL')
            expect(page.locator('#summary')).to_contain_text('1 FAIL')
            expect(page.locator('#summary')).to_contain_text('Live: NO_GO')
            expect(row.locator('.evidence-hint')).to_contain_text('Historischer Gesamtstatus PASS')
            with page.expect_download() as d:
                page.locator('#export').click()
            exported = json.loads(d.value.path().read_text(encoding='utf-8'))
            self.assertEqual(exported['steps'][code]['status'],'PASS')
            self.assertEqual(exported['steps'][code]['extra_status'][fields[0]],'FAIL')
            self.assertIn(code, exported['evidence_gaps'])
            # An actual edit ends historical read-only treatment: fail wins.
            row.locator(f'select[aria-label="{code} {fields[1]} Ergebnis"]').select_option('PASS')
            expect(overall).to_have_value('FAIL')
            overall.select_option('NOT_TESTED')
            expect(overall).to_have_value('FAIL')
            overall.select_option('PASS')
            expect(overall).to_have_value('FAIL')
            # Re-evaluation must be manual after fixing the observed failure.
            row.locator(f'select[aria-label="{code} {fields[0]} Ergebnis"]').select_option('PASS')
            expect(overall).to_have_value('FAIL')
            overall.select_option('PASS')
            expect(overall).to_have_value('PASS')
        page.close()

    @staticmethod
    def _seconds(s):
        mm,ss = map(int,s.split(':'))
        return mm*60+ss


if __name__ == '__main__':
    unittest.main()
