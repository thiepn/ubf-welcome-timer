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

    @staticmethod
    def _seconds(s):
        mm,ss = map(int,s.split(':'))
        return mm*60+ss


if __name__ == '__main__':
    unittest.main()
