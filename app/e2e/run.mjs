// Drives the app through headless Chrome and checks the flows in scenarios.md.
// Needs the dev server (5173) and the backend (8000) running. Screenshots go to e2e/out/.
// usage: node e2e/run.mjs [filter]
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const APP = 'http://localhost:5173';
const API = 'http://localhost:8000';
const OUT = new URL('./out/', import.meta.url).pathname;
const PORT = 9444;
const CITY = { latitude: 49.148, longitude: 9.221, accuracy: 10 };
const AWAY = { latitude: 48.78, longitude: 9.18, accuracy: 10 }; // Stuttgart
const SIZES = { phone: [360, 640, true], tablet: [768, 1024, true], desktop: [1440, 900, false] };
const filter = process.argv[2] ?? '';

for (const [url, what] of [[APP, 'dev server (cd app && npm run dev)'], [`${API}/clusters`, 'backend (cd backend && uv run uvicorn main:app --port 8000)']]) {
	const ok = await fetch(url).then((r) => r.ok).catch(() => false);
	if (!ok) {
		console.error(`${url} not reachable, start the ${what}`);
		process.exit(2);
	}
}

fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'hn-e2e-'));
const chrome = spawn(
	process.env.CHROME ?? 'google-chrome',
	[`--headless=new`, `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--window-size=1440,1024', 'about:blank'],
	{ stdio: 'ignore' }
);
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
let targets;
for (let i = 0; i < 100 && !targets; i++) {
	targets = await fetch(`http://127.0.0.1:${PORT}/json`).then((r) => r.json()).catch(() => null);
	if (!targets) await wait(100);
}
const ws = new WebSocket(targets.find((t) => t.type === 'page').webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let id = 0;
const pending = new Map();
let pageErrors = [];
ws.onmessage = (e) => {
	const m = JSON.parse(e.data);
	if (m.id && pending.has(m.id)) pending.get(m.id)(m), pending.delete(m.id);
	if (m.method === 'Runtime.exceptionThrown') pageErrors.push(m.params.exceptionDetails.exception?.description ?? m.params.exceptionDetails.text);
};
const send = (method, params = {}) => new Promise((r) => (pending.set(++id, r), ws.send(JSON.stringify({ id, method, params }))));
await send('Page.enable');
await send('Runtime.enable');
await send('Browser.grantPermissions', { origin: APP, permissions: ['geolocation'] });

const page = {
	eval: async (expr) => {
		const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
		if (r.result?.exceptionDetails) throw new Error('eval: ' + (r.result.exceptionDetails.exception?.description ?? r.result.exceptionDetails.text).split('\n')[0]);
		return r.result?.result?.value;
	},
	goto: async (geo = CITY) => {
		await send('Emulation.setGeolocationOverride', geo ?? {});
		await send('Page.navigate', { url: APP + '/' });
		for (let t = 0; t < 20000; t += 250) {
			await wait(250);
			if (await page.eval(`!!(window.__map && window.__map.loaded())`).catch(() => false)) break;
		}
		await wait(500);
	},
	size: (name) => {
		const [width, height, mobile] = SIZES[name];
		page.w = width;
		page.h = height;
		return send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile });
	},
	shot: async (name) => {
		const r = await send('Page.captureScreenshot', { format: 'png', clip: { x: 0, y: 0, width: page.w, height: page.h, scale: 1 } });
		fs.writeFileSync(`${OUT}${name}.png`, Buffer.from(r.result.data, 'base64'));
	},
	tap: async (x, y) => {
		await send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
		await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
	},
	drag: async (x0, y0, x1, y1) => {
		await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: x0, y: y0, button: 'left', clickCount: 1 });
		for (let i = 1; i <= 10; i++) {
			await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: x0 + ((x1 - x0) * i) / 10, y: y0 + ((y1 - y0) * i) / 10, button: 'left' });
			await wait(16);
		}
		await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: x1, y: y1, button: 'left', clickCount: 1 });
	},
	click: (sel) => page.eval(`(() => { const el = document.querySelector(${JSON.stringify(sel)}); if (!el) throw new Error('no ' + ${JSON.stringify(sel)}); el.click(); })(); 0`),
	clickText: (text) => page.eval(`(() => { const el = [...document.querySelectorAll('button')].find(b => b.textContent.trim().startsWith(${JSON.stringify(text)})); if (!el) throw new Error('no button ' + ${JSON.stringify(text)}); el.click(); })(); 0`),
	sheet: () => page.eval(`document.querySelector('.sheet')?.innerText ?? ''`),
	has: (sel) => page.eval(`!!document.querySelector(${JSON.stringify(sel)})`),
	until: async (sel, ms) => {
		for (let t = 0; t < ms; t += 250) {
			if (await page.has(sel)) return true;
			await wait(250);
		}
		return false;
	},
	zoom: () => page.eval(`window.__map.getZoom()`),
	center: () => page.eval(`JSON.stringify(window.__map.getCenter())`).then(JSON.parse),
	setView: (lon, lat, zoom) => page.eval(`window.__map.jumpTo({center: [${lon}, ${lat}], zoom: ${zoom}}); 0`),
	wait
};

const results = [];
let current;
const expect = (cond, msg) => {
	if (!cond) current.fails.push(msg);
};
async function scenario(name, fn) {
	if (!name.includes(filter)) return;
	current = { name, fails: [] };
	pageErrors = [];
	try {
		await fn();
	} catch (e) {
		current.fails.push(e.message);
	}
	await page.shot(name.replace(/[^a-z0-9]+/gi, '-'));
	for (const e of pageErrors) current.fails.push('page error: ' + e.split('\n')[0]);
	results.push(current);
	console.log((current.fails.length ? 'FAIL ' : 'ok   ') + name + current.fails.map((f) => '\n       ' + f).join(''));
}

const melden = () => page.clickText('Melden');
const nearlyZoom = async (z) => expect((await page.zoom()) >= z - 0.01, `zoom ${(await page.zoom()).toFixed(2)} < ${z}`);

for (const size of Object.keys(SIZES)) {
	await page.size(size);

	await scenario(`${size}: first open`, async () => {
		await page.goto();
		expect((await page.sheet()).includes('Melden'), 'no Melden button');
		expect(await page.until('.pin.sensor.ours', 10000), 'NoiseNode pin missing');
	});

	await scenario(`${size}: zoomed out, Melden flies to my position`, async () => {
		await page.goto();
		await page.eval(`window.__map.zoomTo(11, {duration: 0}); 0`);
		await wait(500);
		await melden();
		await wait(3500);
		await nearlyZoom(16);
		const c = await page.center();
		expect(Math.abs(c.lat - CITY.latitude) < 0.001 && Math.abs(c.lng - CITY.longitude) < 0.001, `centre ${c.lat.toFixed(4)},${c.lng.toFixed(4)} not at my position`);
		expect(!(await page.has('.crosshair.far')), 'crosshair still grey');
		await page.clickText('Zu laut');
		expect(await page.eval(`!document.querySelector('.sheet .primary').disabled`), 'Melden disabled');
	});

	await scenario(`${size}: send a report, then the card, then close`, async () => {
		await page.goto();
		await melden();
		await wait(3500);
		await page.clickText('Zu laut');
		await page.clickText('Melden');
		await wait(1500);
		expect((await page.sheet()).includes('Gemeldet'), 'no Gemeldet card');
		await page.click('[aria-label="Schließen"]');
		await wait(300);
		expect((await page.sheet()).includes('Melden'), 'home sheet not back');
	});

	await scenario(`${size}: tap a bubble, card shows the cluster`, async () => {
		await page.goto();
		await page.setView(CITY.longitude, CITY.latitude, 15);
		await wait(1000);
		const pin = await page.eval(`(() => { const p = document.querySelector('.pin.cluster'); if (!p) return null; const r = p.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()`);
		expect(pin, 'no bubble on screen');
		if (!pin) return;
		await page.tap(...pin);
		await wait(800);
		expect(/Meldung/.test(await page.sheet()), 'no cluster card');
		expect(await page.has('.pin.cluster.sel'), 'bubble not highlighted');
	});

	await scenario(`${size}: layers on at zoom 11 and 16`, async () => {
		await page.goto();
		await page.eval(`window.__map.zoomTo(11, {duration: 0}); 0`);
		await page.click('[aria-label="Ebenen"]');
		await wait(300);
		for (const i of [0, 2, 3]) await page.eval(`document.querySelectorAll('.layer')[${i}].click(); 0`);
		await wait(2500);
		expect(await page.eval(`document.querySelectorAll('.layer [aria-pressed="true"], .layer[aria-pressed="true"]').length`) === 3, 'not three layers on');
		await page.shot(`${size}-layers-z11`);
		await page.setView(CITY.longitude, CITY.latitude, 16);
		await wait(2500);
		expect(await page.has('.legend'), 'no legend');
	});

	await scenario(`${size}: about sheet opens and closes`, async () => {
		await page.goto();
		await page.click('.title');
		await wait(300);
		expect((await page.sheet()).includes('Prüfen'), 'about sheet missing');
		await page.click('.title');
		await wait(300);
		expect((await page.sheet()).includes('Melden'), 'home sheet not back');
	});
}

await page.size('phone');

await scenario('phone: Melden with position outside Heilbronn', async () => {
	await page.goto(AWAY);
	const before = await page.center();
	await melden();
	await wait(1000);
	expect((await page.eval(`document.querySelector('.toast')?.textContent ?? ''`)).includes('außerhalb'), 'no toast');
	await wait(2000);
	await nearlyZoom(15);
	const c = await page.center();
	expect(Math.abs(c.lat - before.lat) < 0.002, 'centre moved away');
});

await scenario('phone: Melden with position denied', async () => {
	await page.goto(null);
	await page.eval(`navigator.geolocation.getCurrentPosition = (ok, err) => err({ code: 1, message: 'denied' }); 0`);
	await melden();
	await wait(1500);
	expect((await page.eval(`document.querySelector('.toast')?.textContent ?? ''`)).includes('Standort'), 'no toast');
	await nearlyZoom(15);
});

await scenario('phone: zoom out in report mode greys the circle and disables Melden', async () => {
	await page.goto();
	await melden();
	await wait(3500);
	await page.eval(`window.__map.zoomTo(12, {duration: 0}); 0`);
	await wait(800);
	expect(await page.has('.crosshair.far'), 'crosshair not grey');
	expect((await page.eval(`document.querySelector('.hint').textContent`)).includes('Näher'), 'hint not changed');
	await page.clickText('Zu laut');
	expect(await page.eval(`document.querySelector('.sheet .primary').disabled`), 'Melden not disabled');
	await page.eval(`window.__map.zoomTo(15, {duration: 0}); 0`);
	await wait(800);
	expect(await page.eval(`!document.querySelector('.sheet .primary').disabled`), 'Melden still disabled after zooming in');
});

await scenario('phone: drag past the city edge stops without jumping', async () => {
	await page.goto();
	for (let i = 0; i < 6; i++) await page.drag(340, 300, 20, 300);
	await wait(1500);
	const c1 = await page.center();
	await wait(1000);
	const c2 = await page.center();
	expect(c1.lng === c2.lng && c1.lat === c2.lat, 'map still moving after release');
	expect(c1.lng < 9.32, `panned too far east: ${c1.lng}`);
});

await scenario('phone: backend down shows the offline note and recovers', async () => {
	await page.goto();
	await send('Network.enable');
	await send('Network.emulateNetworkConditions', { offline: true, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
	await wait(6500);
	expect(await page.has('.off'), 'no offline note');
	await send('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
	await wait(6500);
	expect(!(await page.has('.off')), 'offline note stays');
	await send('Network.disable');
});

ws.close();
const gone = new Promise((r) => chrome.on('exit', r));
chrome.kill();
await gone;
try {
	fs.rmSync(profile, { recursive: true, force: true, maxRetries: 5 });
} catch {}
const failed = results.filter((r) => r.fails.length);
console.log(`\n${results.length - failed.length}/${results.length} ok, screenshots in e2e/out/`);
process.exit(failed.length ? 1 : 0);
