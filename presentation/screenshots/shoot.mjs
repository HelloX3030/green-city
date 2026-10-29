// Screenshots of the app for the slides, phone size at 3x, into this folder.
// Needs the dev server and the backend running: APP=http://localhost:5173 API=http://localhost:8000 node presentation/screenshots/shoot.mjs
// The Chrome helpers are the ones of app/e2e/run.mjs, cut down.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const APP = process.env.APP ?? 'http://localhost:5173';
const API = process.env.API ?? 'http://localhost:8000';
const OUT = new URL('./', import.meta.url).pathname;
const CITY = { latitude: 49.1427, longitude: 9.2109, accuracy: 10 }; // Kiliansplatz
const PHONE = { width: 390, height: 844, dpr: 3, mobile: true };
const WIDE = { width: 1600, height: 900, dpr: 2, mobile: false };
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const only = process.argv[2] ?? '';

async function browser() {
	const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'hn-shots-'));
	const chrome = spawn('google-chrome', ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--window-size=1600,1024', '--hide-scrollbars', 'about:blank'], { stdio: 'ignore' });
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
	ws.onmessage = (e) => {
		const m = JSON.parse(e.data);
		if (m.id && pending.has(m.id)) pending.get(m.id)(m), pending.delete(m.id);
	};
	const send = (method, params = {}) => new Promise((r) => (pending.set(++id, r), ws.send(JSON.stringify({ id, method, params }))));
	let size = PHONE;
	const page = {
		eval: async (expr) => {
			const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
			if (r.result?.exceptionDetails) throw new Error('eval: ' + (r.result.exceptionDetails.exception?.description ?? r.result.exceptionDetails.text).split('\n')[0]);
			return r.result?.result?.value;
		},
		size: async (s) => {
			size = s;
			await send('Emulation.setDeviceMetricsOverride', { width: s.width, height: s.height, deviceScaleFactor: s.dpr, mobile: s.mobile });
		},
		goto: async () => {
			await send('Emulation.setGeolocationOverride', CITY);
			await send('Page.navigate', { url: APP + '/' });
			for (let t = 0; t < 30000; t += 250) {
				await wait(250);
				if (await page.eval(`!!(window.__map && window.__map.loaded())`).catch(() => false)) break;
			}
			await wait(800);
		},
		shot: async (name) => {
			await page.idle();
			await wait(400);
			const r = await send('Page.captureScreenshot', { format: 'png', clip: { x: 0, y: 0, width: size.width, height: size.height, scale: size.dpr } });
			fs.writeFileSync(`${OUT}${name}.png`, Buffer.from(r.result.data, 'base64'));
			console.log('  ' + name + '.png');
		},
		tap: async (x, y) => {
			await send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
			await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
		},
		click: (sel) => page.eval(`(() => { const el = document.querySelector(${JSON.stringify(sel)}); if (!el) throw new Error('no ' + ${JSON.stringify(sel)}); el.click(); })(); 0`),
		clickText: (text) => page.eval(`(() => { const el = [...document.querySelectorAll('button')].find(b => b.textContent.trim().startsWith(${JSON.stringify(text)})); if (!el) throw new Error('no button ' + ${JSON.stringify(text)}); el.click(); })(); 0`),
		type: (sel, text) => page.eval(`(() => { const i = document.querySelector(${JSON.stringify(sel)}); i.value = ${JSON.stringify(text)}; i.dispatchEvent(new Event('input', { bubbles: true })); })(); 0`),
		sheet: () => page.eval(`document.querySelector('.sheet')?.innerText ?? ''`),
		until: async (sel, ms = 6000) => {
			for (let t = 0; t < ms; t += 250) {
				if (await page.eval(`!!document.querySelector(${JSON.stringify(sel)})`)) return true;
				await wait(250);
			}
			return false;
		},
		idle: () => page.eval(`Promise.race([new Promise((r) => window.__map.once('idle', r)), new Promise((r) => setTimeout(r, 3000))]).then(() => 0)`),
		settled: () => page.eval(`new Promise((r) => { const t0 = Date.now(); const f = () => (window.__map.isMoving() && Date.now() - t0 < 6000 ? setTimeout(f, 100) : r(0)); setTimeout(f, 300); })`),
		setView: async (lon, lat, zoom) => {
			await page.eval(`window.__map.jumpTo({center: [${lon}, ${lat}], zoom: ${zoom}}); 0`);
			await wait(600);
			await page.idle();
		},
		// tap the bubble nearest to a point, like run.mjs does
		tapBubble: async (lon, lat) => {
			const at = await page.eval(`(() => { const p = window.__map.project([${lon}, ${lat}]); const box = document.querySelector('.map').getBoundingClientRect(); let best, bd = 1e9; for (const el of document.querySelectorAll('.pin.cluster:not(.group)')) { const r = el.getBoundingClientRect(); const d = Math.hypot(r.left + r.width / 2 - box.left - p.x, r.top + r.height / 2 - box.top - p.y); if (d < bd) (best = el), (bd = d); } if (!best) return null; const r = best.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()`);
			if (!at) throw new Error('no bubble near ' + lon + ',' + lat);
			await page.tap(...at);
		},
		close: () => page.click('[aria-label="Schließen"]')
	};
	await send('Page.enable');
	await send('Runtime.enable');
	await send('Browser.grantPermissions', { origin: APP, permissions: ['geolocation'] });
	await page.size(PHONE);
	const close = async () => {
		ws.close();
		const gone = new Promise((r) => chrome.on('exit', r));
		chrome.kill();
		await gone;
		fs.rmSync(profile, { recursive: true, force: true });
	};
	return { page, send, close };
}

const clusters = await (await fetch(`${API}/clusters`)).json();
const byCount = [...clusters].sort((a, b) => b.count - a.count);
const biggest = byCount[0];
const gap = byCount.find((c) => c.status === 'no_data');
const confirmed = byCount.find((c) => c.status === 'confirmed');
const { page, send, close } = await browser();
const shots = {};
const shot = (name, fn) => (shots[name] = fn);

shot('01-home', async () => {
	await page.goto();
	await page.setView(9.2185, 49.1425, 13.6);
	await page.shot('01-home');
});
shot('02-report-sheet', async () => {
	await page.goto();
	await page.clickText('Melden');
	await page.settled();
	await wait(500);
	await page.shot('02-report-sheet');
	await page.clickText('Zu laut');
	await page.type('.sheet .msg', 'Nachts Poser und Rennen, jedes Wochenende');
	await wait(200);
	await page.shot('02b-report-sheet-filled');
	await page.clickText('Melden');
	await page.until('.sheet .badge');
	await page.until('.sheet .voices li.me');
	await wait(600);
	await page.shot('03-sent-card');
	await page.close();
});
shot('04-sent-trash', async () => {
	// the Mängelmelder hint: a Müll report, only once the type exists
	await page.goto();
	await page.setView(9.2255, 49.1465, 16);
	await page.clickText('Melden');
	await page.settled();
	await wait(500);
	await page.clickText('Müll');
	await page.type('.sheet .msg', 'Sperrmüll liegt seit Tagen hier');
	await page.clickText('Melden');
	await page.until('.sheet .badge');
	await wait(800);
	await page.shot('04-sent-trash-hint');
	await page.close();
});
shot('05-cluster-card', async () => {
	await page.goto();
	await page.setView(biggest.lon, biggest.lat, 15.5);
	await page.tapBubble(biggest.lon, biggest.lat);
	await page.until('.sheet .status');
	await wait(600);
	await page.shot('05-cluster-card');
	await page.close();
});
shot('06-no-sensor', async () => {
	if (!gap) return console.log('  no bubble without a sensor');
	await page.goto();
	await page.setView(gap.lon, gap.lat, 15.5);
	await page.tapBubble(gap.lon, gap.lat);
	await page.until('.sheet .status');
	await wait(600);
	await page.shot('06-no-sensor-card');
	await page.close();
});
shot('06b-confirmed', async () => {
	if (!confirmed) return console.log('  no confirmed bubble');
	await page.goto();
	await page.setView(confirmed.lon, confirmed.lat, 15.5);
	await page.tapBubble(confirmed.lon, confirmed.lat);
	await page.until('.sheet .status');
	await wait(600);
	await page.shot('06b-confirmed-card');
	await page.close();
});
shot('07-filter', async () => {
	await page.goto();
	await page.setView(9.2185, 49.1425, 13.6);
	await page.click('[aria-label="Ebenen"]');
	await wait(400);
	try {
		await page.clickText('Ohne Sensor');
	} catch {
		await page.clickText('Nur Bestätigte');
		console.log('  (no Ohne Sensor filter yet, used Nur Bestätigte)');
	}
	await wait(600);
	await page.shot('07-filter-sheet');
	await page.close();
	await wait(600);
	await page.shot('07b-filter-map');
	if (gap) {
		await page.setView(gap.lon, gap.lat, 15.5);
		await page.tapBubble(gap.lon, gap.lat);
		await page.until('.sheet .status');
		await wait(600);
		await page.shot('07c-filter-no-sensor-card');
		await page.close();
	}
	await page.eval(`localStorage.removeItem('filter'); 0`);
});
shot('08-layer-noise', async () => {
	await page.goto();
	await page.click('[aria-label="Ebenen"]');
	await wait(400);
	await page.clickText('Lärmkarte');
	await wait(400);
	await page.close();
	await page.setView(9.2185, 49.1425, 13.6);
	await wait(1500);
	await page.shot('08-layer-noise');
	await page.click('[aria-label="Ebenen"]');
	await wait(300);
	await page.clickText('Lärmkarte');
	await page.close();
});
shot('09-noisenode', async () => {
	await page.goto();
	const at = await page.eval(`(() => { const el = document.querySelector('.pin.sensor.ours'); if (!el) return null; const r = el.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()`);
	if (!at) {
		const sensors = await (await fetch(`${API}/sensors`)).json();
		const ours = sensors.find((s) => s.team) ?? sensors.find((s) => /noisenode/i.test(s.name));
		if (!ours) return console.log('  no NoiseNode');
		await page.setView(ours.lon, ours.lat, 16);
	}
	const at2 = at ?? (await page.eval(`(() => { const el = document.querySelector('.pin.sensor.ours'); const r = el.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()`));
	await page.tap(...at2);
	await page.until('.history svg', 8000);
	await wait(800);
	await page.shot('09-noisenode-7d');
	await page.eval(`[...document.querySelectorAll('.history .seg button')].find((b) => b.textContent.trim() === 'Alles').click(); 0`);
	await wait(600);
	await page.shot('09b-noisenode-all');
	await page.eval(`[...document.querySelectorAll('.history .seg button')].find((b) => b.textContent.trim() === '24 h').click(); 0`);
	await wait(600);
	await page.shot('09c-noisenode-24h');
	await page.close();
});
shot('10-about', async () => {
	await page.goto();
	await page.click('.title');
	await wait(500);
	await page.shot('10-about');
	await page.close();
});
shot('11-map-wide', async () => {
	await page.size(WIDE);
	await page.goto();
	await page.setView(9.2185, 49.1445, 13.3);
	await wait(1500);
	await page.shot('11-map-wide');
	await page.size(PHONE);
});
shot('12-logo', async () => {
	// the leaf as a transparent PNG for the slides
	const svg = fs.readFileSync(new URL('../../app/static/favicon.svg', import.meta.url), 'utf8');
	await send('Emulation.setDeviceMetricsOverride', { width: 512, height: 512, deviceScaleFactor: 2, mobile: false });
	await send('Emulation.setDefaultBackgroundColorOverride', { color: { r: 0, g: 0, b: 0, a: 0 } });
	await send('Page.navigate', { url: 'data:text/html;charset=utf-8,' + encodeURIComponent(`<body style="margin:0;background:transparent">${svg.replace('width="64" height="64"', 'width="512" height="512"')}</body>`) });
	await wait(800);
	const r = await send('Page.captureScreenshot', { format: 'png', clip: { x: 0, y: 0, width: 512, height: 512, scale: 2 } });
	fs.writeFileSync(`${OUT}12-logo-leaf.png`, Buffer.from(r.result.data, 'base64'));
	console.log('  12-logo-leaf.png');
	await send('Emulation.clearDeviceMetricsOverride');
	await send('Emulation.setDefaultBackgroundColorOverride', {});
	await page.size(PHONE);
});

for (const [name, fn] of Object.entries(shots)) {
	if (!name.includes(only)) continue;
	console.log(name);
	try {
		await fn();
	} catch (e) {
		console.log('  failed: ' + e.message);
	}
}
await close();
