import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {readFileSync, readdirSync, statSync, existsSync} from 'node:fs';
import {resolve, join} from 'node:path';
import {createHash} from 'node:crypto';

const root = resolve(import.meta.dirname, '..');
const file = (path) => readFileSync(join(root, path), 'utf8');
const hash = (path) => createHash('sha256').update(readFileSync(path)).digest('hex');

test('native staging is reproducible and preserves both supplied Canva images byte for byte', () => {
  execFileSync(process.execPath, ['scripts/build-desktop.mjs'], {cwd:root});
  const output = join(root, 'dist', 'desktop');
  for (const name of ['welcome.png', 'background-clean.png']) {
    assert.equal(hash(join(root, 'assets', name)), hash(join(output, 'assets', name)));
  }
  for (const name of ['control.html', 'display.html', 'index.html', 'js/timer-core.js',
    'js/sync.js', 'js/native-projector.js', 'css/native-projector.css']) {
    assert.equal(hash(join(root, name)), hash(join(output, name)), name);
  }
  assert.equal(existsSync(join(output, 'server.mjs')), false);
  assert.equal(existsSync(join(output, 'reference')), false);
  assert.equal(existsSync(join(output, 'tests')), false);
  assert.equal(readdirSync(output).sort().join(','), 'assets,control.html,css,display.html,index.html,js');
});

test('native enhancement does not replace the browser popup workflow', () => {
  assert.match(file('js/control.js'), /window\.open\(new URL\('\.\/display\.html'/);
  assert.match(file('js/control.js'), /globalThis\.__TAURI__\?\.core\?\.invoke/);
  assert.match(file('control.html'), /js\/native-projector\.js/);
  assert.match(file('control.html'), /css\/native-projector\.css/);
  assert.match(file('js/native-projector.js'), /if \(native\?\.invoke\)/);
});

test('native actions are restricted to the controller and display is read-only', () => {
  const config = JSON.parse(file('src-tauri/tauri.conf.json'));
  const capability = JSON.parse(file('src-tauri/capabilities/default.json'));
  assert.equal(config.app.withGlobalTauri, true);
  assert.equal(config.app.windows[0].label, 'controller');
  assert.deepEqual(capability.windows, ['controller']);
  assert.equal(config.bundle.active, false);
  const main = file('src-tauri/src/main.rs');
  for (const name of ['list_projector_targets','open_projector','release_projector','projector_status']) {
    assert.match(main, new RegExp('fn ' + name + '\\('));
  }
  assert.match(main, /window\.label\(\) != "controller"/);
  assert.match(main, /set_fullscreen_on_monitor/);
  assert.match(main, /choose_target_key/);
  assert.match(main, /is_fullscreen\(\)/);
  assert.match(main, /current_monitor\(\)/);
  assert.match(main, /validate_projector/);
  assert.match(main, /physical_bounds_match/);
  assert.match(main, /inner_position/);
  assert.match(main, /inner_size/);
  assert.match(main, /wait_for_fullscreen_placement/);
  assert.match(main, /WindowEvent::Moved/);
  assert.match(main, /WindowEvent::ScaleFactorChanged/);
  assert.match(file('js/native-projector.js'), /monitorKey/);
  assert.doesNotMatch(file('js/native-projector.js'), /Number\(selector\.value\)/);
  assert.match(main, /WebviewUrl::App\("display\.html"\.into\(\)\)/);
  assert.match(main, /\.focused\(false\)/);
  assert.match(main, /\.focusable\(false\)/);
  assert.match(main, /operator_had_focus/);
  assert.match(main, /window\.set_focus\(\)/);
  const nativeSmoke = file('src-tauri/src/bin/webview2_smoke.rs');
  assert.match(nativeSmoke, /WEBVIEW2_FOCUS_PASS/);
  assert.match(nativeSmoke, /WEBVIEW2_FOCUS_RELEASE_PASS/);
  assert.doesNotMatch(file('js/display.js'), /__TAURI__|open_projector|release_projector/);
});

test('Tauri frontend paths resolve within staged distribution without a local server', () => {
  const config = JSON.parse(file('src-tauri/tauri.conf.json'));
  const stagedPath = resolve(root, 'src-tauri', config.build.frontendDist);
  assert.equal(stagedPath, join(root, 'dist', 'desktop'));
  assert.equal(statSync(join(stagedPath, 'control.html')).isFile(), true);
  assert.equal(statSync(join(stagedPath, 'display.html')).isFile(), true);
});
