// Renders renders/*.png from the viewer: serves 3d-model/ on a port, drives headless Chrome over CDP
// and waits for the viewer's data-ready flag (chrome --screenshot aborts the 4 MB model fetch).
// usage: node render.mjs
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const HERE = path.dirname(new URL(import.meta.url).pathname);
const PORT = process.env.PORT ?? 8765;
const OUT = path.join(HERE, 'renders');
const VIEWS = [['01-front', 'view=front'], ['02-top', 'view=top'], ['03-side-usb', 'view=side'], ['04-exploded', 'view=explode'], ['05-lid-off', 'view=open'], ['06-sled', 'view=sled']];
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
fs.mkdirSync(OUT, { recursive: true });

const http = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1'], { cwd: HERE, stdio: 'ignore' });
for (let i = 0; i < 50; i++) { if (await fetch(`http://127.0.0.1:${PORT}/export/case.glb`, { method: 'HEAD' }).then((r) => r.ok).catch(() => false)) break; await wait(200); }
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'nn-render-'));
const chrome = spawn(process.env.CHROME ?? 'google-chrome', ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--hide-scrollbars', '--window-size=1600,1000', 'about:blank'], { stdio: 'ignore' });
let targets;
for (let i = 0; i < 100 && !targets; i++) {
	const port = fs.existsSync(`${profile}/DevToolsActivePort`) && fs.readFileSync(`${profile}/DevToolsActivePort`, 'utf8').split('\n')[0];
	if (port) targets = await fetch(`http://127.0.0.1:${port}/json`).then((r) => r.json()).catch(() => null);
	if (!targets) await wait(100);
}
const ws = new WebSocket(targets.find((t) => t.type === 'page').webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let id = 0;
const pending = new Map();
ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) pending.get(m.id)(m); };
const send = (method, params = {}) => new Promise((r) => (pending.set(++id, r), ws.send(JSON.stringify({ id, method, params }))));
await send('Page.enable');
await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 1600, height: 1000, deviceScaleFactor: 1, mobile: false });
const evalJs = async (expr) => (await send('Runtime.evaluate', { expression: expr, returnByValue: true })).result?.result?.value;

let failed = 0;
for (const [name, query] of VIEWS) {
	let ready = false;
	// the first load after a cold start sometimes loses the model fetch: one retry
	for (let attempt = 0; attempt < 2 && !ready; attempt++) {
		await send('Page.navigate', { url: `http://127.0.0.1:${PORT}/viewer/?ui=0&${query}` });
		for (let t = 0; t < 90000 && !ready; t += 500) {
			await wait(500);
			ready = (await evalJs(`document.documentElement.dataset.ready === '1'`)) === true;
			if ((await evalJs(`document.getElementById('status')?.textContent ?? ''`)).startsWith('Could not')) break;
		}
	}
	if (!ready) { console.log(`render ${name} failed: ` + (await evalJs(`document.getElementById('status')?.textContent`))); failed++; continue; }
	await wait(1500); // shadows and tone mapping settle, the second frame is the final one
	const r = await send('Page.captureScreenshot', { format: 'png' });
	fs.writeFileSync(path.join(OUT, `${name}.png`), Buffer.from(r.result.data, 'base64'));
	console.log(`  renders/${name}.png`);
}
ws.close();
chrome.kill();
http.kill();
await wait(500);
try { fs.rmSync(profile, { recursive: true, force: true, maxRetries: 5 }); } catch {}
process.exit(failed ? 1 : 0);
