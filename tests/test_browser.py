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
  window.open = () => { window.__nativePopupWasCalled = true; throw Error('native popup regression'); };
  window.__TAURI__ = {core: {invoke: async (command, args = {}) => {
    window.__nativeCalls.push({command, args});
    if (command === 'list_projector_targets') return window.__nativeTargets;
    if (command === 'projector_status') {
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
      if (!window.__nativeTargets.some(target => target.id === args.monitorKey)) {
        throw Error('Die Beameranordnung hat sich geändert.');
      }
      window.__nativeActive = true;
      return;
    }
    if (command === 'release_projector') {
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

    @staticmethod
    def _seconds(s):
        mm,ss = map(int,s.split(':'))
        return mm*60+ss


if __name__ == '__main__':
    unittest.main()
