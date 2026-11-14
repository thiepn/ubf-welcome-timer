import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, existsSync, readdirSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const files = ['index.html', 'control.html', 'display.html'];
const prefix = '/ubf-welcome-timer/';
const source = (name) => readFileSync(path.join(root, name), 'utf8');

test('Pages-ready root entry, Jekyll bypass, and no publishing workflow', () => {
  assert.ok(existsSync(path.join(root, '.nojekyll')));
  assert.ok(existsSync(path.join(root, 'index.html')));
  const workflows = readdirSync(path.join(root, '.github', 'workflows'));
  assert.deepEqual(workflows, ['tests.yml']);
  const workflow = source('.github/workflows/tests.yml');
  assert.match(workflow, /contents: read/);
  assert.doesNotMatch(workflow, /(?:pages:\s*write|id-token:\s*write|deploy-pages|upload-pages-artifact|deploy from)/i);
});

test('HTML entrypoints and module imports resolve within a project Pages subpath', () => {
  for (const file of files) {
    const html = source(file);
    const links = [...html.matchAll(/(?:href|src)="([^"]+)"/g)].map(match => match[1]);
    for (const link of links) {
      if (link.startsWith('data:')) continue;
      assert.ok(link.startsWith('./'), `${file}: non-relative link ${link}`);
      const resolved = new URL(link, `https://example.github.io${prefix}${file}`);
      assert.ok(resolved.pathname.startsWith(prefix), `${file}: escapes repository prefix: ${link}`);
      assert.ok(existsSync(path.join(root, resolved.pathname.slice(prefix.length))), `${file}: missing ${link}`);
    }
  }
  assert.match(source('index.html'), /url=\.\/control\.html/);
  for (const file of readdirSync(path.join(root, 'js')).filter(x => x.endsWith('.js'))) {
    const code = source(`js/${file}`);
    for (const match of code.matchAll(/\bfrom\s+['"](\.[^'"]+)['"]/g)) {
      const imported = path.resolve(root, 'js', match[1]);
      assert.ok(existsSync(imported), `js/${file}: unresolved ${match[1]}`);
    }
  }
});

test('Original and clean Canva assets exist with identical 16:9 dimensions', () => {
  function pngDimensions(file) {
    const bytes = readFileSync(path.join(root, 'assets', file));
    assert.equal(bytes.subarray(0,8).toString('hex'),'89504e470d0a1a0a');
    return [bytes.readUInt32BE(16), bytes.readUInt32BE(20)];
  }
  const original = pngDimensions('welcome.png');
  const clean = pngDimensions('background-clean.png');
  assert.deepEqual(clean, original);
  assert.ok(original[0] > 0 && original[1] > 0);
  assert.equal(original[0] * 9, original[1] * 16);
});
