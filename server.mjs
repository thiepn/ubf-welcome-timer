/** Local-only static file server. No backend state or external dependencies. */
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.dirname(fileURLToPath(import.meta.url));
const port = Number(process.env.PORT || 8765);
const mime = {
  '.html':'text/html; charset=utf-8',
  '.css':'text/css; charset=utf-8',
  '.js':'text/javascript; charset=utf-8',
  '.png':'image/png',
  '.svg':'image/svg+xml',
  '.json':'application/json; charset=utf-8',
};
const server = createServer(async (req, res) => {
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.writeHead(405, {'Allow':'GET, HEAD'}); res.end(); return;
  }
  let relative;
  try { relative = decodeURIComponent(new URL(req.url, `http://127.0.0.1:${port}`).pathname); }
  catch { res.writeHead(400); res.end(); return; }
  if (relative === '/') relative = '/index.html';
  const target = path.resolve(root, '.' + relative);
  if (!target.startsWith(root + path.sep)) { res.writeHead(403); res.end(); return; }
  if (!(path.extname(target) in mime)) { res.writeHead(404); res.end(); return; }
  try {
    const body = await readFile(target);
    res.writeHead(200, {'Content-Type':mime[path.extname(target)], 'Content-Length':body.length, 'Cache-Control':'no-cache'});
    if (req.method === 'HEAD') res.end(); else res.end(body);
  } catch {res.writeHead(404);res.end('Not found');}
});
server.listen(port, '127.0.0.1', () => {
  console.log(`UBF Köln Timer: http://127.0.0.1:${port}/control.html`);
  console.log(`Projektion:      http://127.0.0.1:${port}/display.html`);
});
