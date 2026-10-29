// Drives the app through headless Chrome and checks the flows in scenarios.md.
// Needs the dev server (5173) and the backend (8000) running. Screenshots go to e2e/out/.
// Four Chromes run at once, one per screen size and one for the phone-only flows, each with its own profile.
// usage: node e2e/run.mjs [filter]
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const APP = 'http://localhost:5173';
const API = 'http://localhost:8000';
const OUT = new URL('./out/', import.meta.url).pathname;
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
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
// every device token the run sends reports with; at the end their reports are withdrawn.
// They are kept in a file as they come, so a run that dies (or whose backend hangs) leaves them
// for the next run to withdraw, instead of test reports piling up in the bubbles for good
const LEFT = path.join(os.tmpdir(), 'hn-e2e-tokens.json');
const keep = (set) => fs.writeFileSync(LEFT, JSON.stringify([...set]));
const tokens = new (class extends Set {
	add(t) {
		super.add(t);
		keep(this);
		return this;
	}
})((() => {
	try {
		return JSON.parse(fs.readFileSync(LEFT, 'utf8'));
	} catch {
		return [];
	}
})());

// a headless Chrome of its own, the CDP connection and the page helpers
async function browser() {
	const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'hn-e2e-'));
	const chrome = spawn(
		process.env.CHROME ?? 'google-chrome',
		[`--headless=new`, `--remote-debugging-port=0`, `--user-data-dir=${profile}`, '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--window-size=1440,1024', 'about:blank'],
		{ stdio: 'ignore' }
	);
	let targets;
	for (let i = 0; i < 100 && !targets; i++) {
		// Chrome picks a free port and writes it into the profile
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
		if (m.method === 'Runtime.exceptionThrown') page.errors.push(m.params.exceptionDetails.exception?.description ?? m.params.exceptionDetails.text);
		// failed requests ("Failed to load resource: … 404") and console.error, which a phone with devtools shows in red
		if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') page.logs.push(m.params.entry.text + (m.params.entry.url ? ' ' + m.params.entry.url : ''));
		if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') page.logs.push('console.error: ' + m.params.args.map((a) => a.value ?? a.description).join(' '));
	};
	const send = (method, params = {}) => new Promise((r) => (pending.set(++id, r), ws.send(JSON.stringify({ id, method, params }))));
	const page = {
		errors: [],
		logs: [],
		// a console error this scenario provokes on purpose
		allowed: [],
		allowLog: (re) => page.allowed.push(re),
		eval: async (expr) => {
			const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
			if (r.result?.exceptionDetails) throw new Error('eval: ' + (r.result.exceptionDetails.exception?.description ?? r.result.exceptionDetails.text).split('\n')[0]);
			return r.result?.result?.value;
		},
		device: async () => {
			const t = await page.eval(`localStorage.getItem('device')`).catch(() => null);
			if (t) tokens.add(t);
		},
		// a new device: the old token is kept for the cleanup first
		forget: async () => {
			await page.device();
			await page.eval(`localStorage.clear(); 0`);
		},
		goto: async (geo = CITY) => {
			await page.device();
			await send('Emulation.setGeolocationOverride', geo ?? {});
			// under four Chromes vite sometimes fails a module ("Failed to fetch dynamically
			// imported module") and the map never comes: load again, without that load's errors
			const before = page.errors.length;
			const logsBefore = page.logs.length;
			load: for (let attempt = 0; attempt < 3; attempt++) {
				page.errors.length = before;
				page.logs.length = logsBefore;
				await send('Page.navigate', { url: APP + '/' });
				for (let t = 0; t < 30000; t += 250) {
					await wait(250);
					if (await page.eval(`!!(window.__map && window.__map.loaded())`).catch(() => false)) break load;
					if (page.errors.slice(before).some((e) => e.includes('dynamically imported module'))) break;
				}
				console.log(`  map did not load (${page.errors.slice(before)[0]?.split('\n')[0] ?? 'no error, 30 s'}), loading again`);
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
		sheetHas: async (text, ms = 4000) => {
			for (let t = 0; t < ms; t += 200) {
				if ((await page.sheet()).includes(text)) return true;
				await wait(200);
			}
			return false;
		},
		has: (sel) => page.eval(`!!document.querySelector(${JSON.stringify(sel)})`),
		until: async (sel, ms) => {
			for (let t = 0; t < ms; t += 250) {
				if (await page.has(sel)) return true;
				await wait(250);
			}
			return false;
		},
		zoom: () => page.eval(`window.__map.getZoom()`),
		// tiles and sources are rendered, or 3 s passed
		idle: () => page.eval(`Promise.race([new Promise((r) => window.__map.once('idle', r)), new Promise((r) => setTimeout(r, 3000))]).then(() => 0)`),
		center: () => page.eval(`JSON.stringify(window.__map.getCenter())`).then(JSON.parse),
		// a fly animation ended, or 6 s passed
		settled: () => page.eval(`new Promise((r) => { const t0 = Date.now(); const f = () => (window.__map.isMoving() && Date.now() - t0 < 6000 ? setTimeout(f, 100) : r(0)); setTimeout(f, 300); })`),
		setView: (lon, lat, zoom) => page.eval(`window.__map.jumpTo({center: [${lon}, ${lat}], zoom: ${zoom}}); 0`),
		wait
	};
	await send('Page.enable');
	await send('Runtime.enable');
	await send('Log.enable');
	await send('Browser.grantPermissions', { origin: APP, permissions: ['geolocation'] });
	const close = async () => {
		await page.device();
		ws.close();
		const gone = new Promise((r) => chrome.on('exit', r));
		chrome.kill();
		await gone;
		try {
			fs.rmSync(profile, { recursive: true, force: true, maxRetries: 5 });
		} catch {}
	};
	return { page, send, close };
}

// one Chrome running one chain of scenarios; returns their results
async function lane(run) {
	const { page, send, close } = await browser();
	const results = [];
	let current;
	const expect = (cond, msg) => {
		if (!cond) current.fails.push(msg);
	};
	const scenario = async (name, fn) => {
		if (!name.includes(filter)) return;
		current = { name, fails: [] };
		page.errors = [];
		page.logs = [];
		page.allowed = [];
		const t0 = Date.now();
		try {
			await fn();
		} catch (e) {
			current.fails.push(e.message);
		}
		await page.shot(name.replace(/[^a-z0-9]+/gi, '-'));
		for (const e of page.errors) current.fails.push('page error: ' + e.split('\n')[0]);
		// errors from the app and the backend fail the scenario, the basemap's tiles only get a note (their CDN, not us)
		const logs = page.logs.filter((e) => !page.allowed.some((re) => re.test(e)));
		for (const e of logs) {
			if (e.includes(APP) || e.includes(API) || e.startsWith('console.error')) current.fails.push('console: ' + e.split('\n')[0]);
			else console.log(`  note, ${name}: ${e.split('\n')[0]}`);
		}
		results.push(current);
		console.log((current.fails.length ? 'FAIL ' : 'ok   ') + name + ` (${((Date.now() - t0) / 1000).toFixed(1)} s)` + current.fails.map((f) => '\n       ' + f).join(''));
	};
	const melden = () => page.clickText('Melden');
	// set an input's value the way a keyboard would, Svelte sees the input event
	const type = (sel, text) => page.eval(`(() => { const i = document.querySelector(${JSON.stringify(sel)}); i.value = ${JSON.stringify(text)}; i.dispatchEvent(new Event('input', { bubbles: true })); })(); 0`);
	const nearlyZoom = async (z) => expect((await page.zoom()) >= z - 0.01, `zoom ${(await page.zoom()).toFixed(2)} < ${z}`);
	// the other lanes post reports too: a check against the API holds once both agree, within a few seconds
	const same = async (fn, ms = 6000) => {
		for (let t = 0; t < ms; t += 300) {
			if (await fn()) return true;
			await wait(300);
		}
		return fn();
	};
	await run({ page, send, expect, scenario, melden, type, nearlyZoom, same });
	await close();
	return results;
}
// a point on the element where a tap lands on it: the centre, else around it; small pins sit on top of big ones
const FREE = `(el) => { const r = el.getBoundingClientRect(); const c = [r.x + r.width / 2, r.y + r.height / 2]; for (const [dx, dy] of [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1], [0.7, 0.7], [-0.7, 0.7], [0.7, -0.7], [-0.7, -0.7]]) { const x = c[0] + dx * r.width * 0.35, y = c[1] + dy * r.height * 0.35; if (x > 0 && y > 0 && x < innerWidth && y < innerHeight && el.contains(document.elementFromPoint(x, y))) return [x, y]; } return null; }`;

// the flows every screen size runs
const sized = async (size, { page, expect, scenario, melden, type, nearlyZoom, same }) => {
	await page.size(size);

	await scenario(`${size}: first open`, async () => {
		await page.goto();
		expect((await page.sheet()).includes('Melden'), 'no Melden button');
		expect(await page.eval(`document.documentElement.lang === 'de' && document.title === "Sag's Heilbronn"`), 'page not lang="de" or title missing');
		const icon = await page.eval(`(async () => {
			const r = await fetch(document.querySelector('link[rel=icon]').href);
			return r.ok && (await r.text()).includes('#3a7d5c');
		})()`);
		expect(icon, 'tab icon missing or not ours');
		// home screen: iOS takes the apple-touch-icon, Android the manifest's icons; each must load as a PNG of its size
		const home = await page.eval(`(async () => {
			const png = async (href, size) => {
				const r = await fetch(href);
				if (!r.ok || !(r.headers.get('content-type') || '').includes('png')) return false;
				const img = await createImageBitmap(await r.blob());
				return img.width === size && img.height === size;
			};
			const m = document.querySelector('link[rel=manifest]');
			const mr = m && (await fetch(m.href));
			if (!mr || !mr.ok) return 'manifest missing';
			const man = await mr.json();
			if (man.name !== "Sag's Heilbronn" || man.lang !== 'de') return 'manifest name or lang';
			for (const i of man.icons) if (!(await png(new URL(i.src, m.href).href, +i.sizes.split('x')[0]))) return i.src;
			const apple = document.querySelector('link[rel=apple-touch-icon]');
			return apple && (await png(apple.href, 180)) ? 'ok' : 'apple-touch-icon';
		})()`);
		expect(home === 'ok', `home-screen icon broken: ${home}`);
		expect(await page.until('.pin.sensor.ours', 15000), 'NoiseNode pin missing');
		expect(await page.until('.pin.cluster span', 15000), 'no bubbles');
		await wait(300);
		const hidden = await page.eval(`(() => {
			const pins = [...document.querySelectorAll('.pin.sensor')].map((p) => p.getBoundingClientRect());
			return [...document.querySelectorAll('.pin.cluster span')].filter((s) => {
				const r = s.getBoundingClientRect(), x = r.x + r.width / 2, y = r.y + r.height / 2;
				return pins.some((p) => x > p.left && x < p.right && y > p.top && y < p.bottom);
			}).map((s) => s.textContent).join(', ');
		})()`);
		expect(!hidden, `bubble number under a sensor pin: ${hidden}`);
		const attrib = `document.querySelector('.maplibregl-ctrl-attrib')`;
		expect(await page.eval(`!${attrib}.classList.contains('maplibregl-compact-show')`), 'credits open on start');
		await page.eval(`${attrib}.querySelector('.maplibregl-ctrl-attrib-button').click(); 0`);
		await wait(200);
		expect(await page.eval(`${attrib}.classList.contains('maplibregl-compact-show') && ${attrib}.innerText.includes('OpenStreetMap')`), 'the "i" does not open the credits');
		await page.eval(`${attrib}.querySelector('.maplibregl-ctrl-attrib-button').click(); 0`);
	});

	await scenario(`${size}: zoomed out, Melden flies to my position`, async () => {
		await page.goto();
		await page.eval(`window.__map.zoomTo(11, {duration: 0}); 0`);
		await wait(500);
		await melden();
		await page.settled();
		await wait(300);
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
		await page.settled();
		await wait(300);
		await page.clickText('Zu laut');
		await type('.sheet .msg', `Baustelle ab 6 Uhr (${size})`);
		const msgPx = await page.eval(`parseFloat(getComputedStyle(document.querySelector('.sheet .msg')).fontSize)`);
		expect(msgPx >= 16, `message field is ${msgPx}px, iOS Safari zooms in on focus below 16px`);
		expect(await page.eval(`document.querySelector('.sheet .msg').enterKeyHint`) === 'send', 'the keyboard key of the message field does not say send');
		// on the phone the keyboard's send key sends, elsewhere the Melden button
		if (size === 'phone') await page.eval(`document.querySelector('.sheet .msg').dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })); 0`);
		else await page.clickText('Melden');
		await page.until('.sheet .badge', 6000); // post, then the clusters poll with the new report
		await page.until('.sheet .voices li.me', 4000); // the card's own fetch of the texts
		const sheet = await page.sheet();
		expect(sheet.includes('Gemeldet'), `no Gemeldet card, sheet says "${sheet.split('\n')[0]}", Melden ${(await page.eval(`document.querySelector('.sheet .primary')?.disabled`)) ? 'disabled' : 'enabled'}, zoom ${(await page.zoom()).toFixed(3)}`);
		expect(/^Du /m.test(sheet), 'card does not say Du');
		expect(await page.has('.pin.cluster.sel.mine'), 'my bubble has no mine mark');
		expect(await page.sheetHas(`Baustelle ab 6 Uhr (${size})`), 'my text is not on the card');
		const first = await page.eval(`document.querySelector('.sheet .voices li')?.innerText`);
		expect(first && first.includes('Du') && first.includes(`(${size})`), `the first text is not mine with a Du tag: "${first}"`);
		// the chip of the type I named has a ring, also when the bubble has only that type
		const ringed = await page.eval(`[...document.querySelectorAll('.sheet .type.me')].map((b) => b.getAttribute('aria-label'))`);
		expect(ringed.some((l) => l.startsWith('Zu laut') && l.endsWith('von dir')), `my type is not ringed: ${JSON.stringify(ringed)}`);
		const todays = await page.eval(`[...document.querySelectorAll('.sheet .voices li.me')].length`);
		expect(todays < 2 || sheet.includes('Meldung hier heute'), `${todays} of mine, but the card does not count them`);
		expect(sheet.includes('Nochmal melden'), 'the sent card has no Nochmal melden button');
		await page.shot(`${size}-sent`);
		await page.click('[aria-label="Schließen"]');
		await wait(300);
		expect((await page.sheet()).includes('Melden'), 'home sheet not back');
	});

	await scenario(`${size}: tap a bubble, card shows the cluster`, async () => {
		await page.goto();
		await page.setView(CITY.longitude, CITY.latitude, 15);
		await wait(1000);
		// the bubble of the report the previous scenario sent, somewhere near the screen centre
		const pin = await page.eval(`(() => { const free = ${FREE}; for (const p of document.querySelectorAll('.pin.cluster')) { const at = free(p); if (at) return at; } return null; })()`);
		expect(pin, 'no bubble on screen');
		if (!pin) return;
		await page.tap(...pin);
		await page.until('.sheet .voices li.me', 6000); // the card's own fetch of the texts
		const sheet = await page.sheet();
		expect(/^\d+ Meldung/m.test(sheet) && !sheet.includes('Gemeldet'), 'no cluster card');
		expect(/^Du /m.test(sheet), 'card of the bubble with my report does not say Du');
		expect(/letzte (gerade eben|vor \d+ (min|h|Tagen))$/m.test(sheet), `the time in "${sheet.split('\n')[1]}" can break before its unit`);
		let n, api;
		await same(async () => {
			n = await page.eval(`document.querySelector('.pin.cluster.sel')?.textContent`);
			api = (await fetch(`${API}/clusters`).then((r) => r.json())).find((c) => String(c.count) === n && c.people <= +n);
			return api && (api.people < 2 || (await page.sheet()).includes(`Du und ${api.people - 1} andere`));
		});
		expect(api, `bubble says ${n}, no cluster has that many reports`);
		const people = api && `Du und ${api.people - 1} ${api.people === 2 ? 'andere Person' : 'andere Personen'}`;
		if (api && api.people > 1) expect((await page.sheet()).includes(people), `card counts "${(await page.sheet()).split('\n')[0]}", people ${api.people}`);
		expect(await page.has('.sheet .voices li.me'), 'my report is not marked in the list');
		expect(sheet.includes('Nochmal melden') && !sheet.includes('Zählt einmal'), 'reported today, but no Nochmal melden, or the old once-a-day hint');
		// the type chips: icon and reports per type, always here since I reported; mine ringed; a tap filters the texts
		const types = api ? Object.keys(api.types) : [];
		const chips = await page.eval(`[...document.querySelectorAll('.sheet .type')].map((b) => b.textContent.trim())`);
		expect(chips.length === types.length, `${chips.length} chips for ${types.length} types`);
		const ringed = await page.eval(`[...document.querySelectorAll('.sheet .type.me')].map((b) => b.getAttribute('aria-label'))`);
		expect(ringed.length && ringed.every((l) => l.endsWith('von dir')), `ringed chips: ${JSON.stringify(ringed)}`);
		if (chips.length) {
			await page.click('.sheet .type');
			await wait(300);
			const picked = await page.eval(`document.querySelector('.sheet .picked')?.textContent`);
			expect(picked && picked.includes(`${api.types[types[0]]} Meldung`), `filter line says "${picked}"`);
			// the newest five (mine besides), the rest behind "Alle N Texte zeigen"
			let texts, expected, more;
			await same(async () => {
				texts = await page.eval(`[...document.querySelectorAll('.sheet .voices li')].length`);
				more = await page.eval(`document.querySelector('.sheet .more')?.textContent ?? null`);
				expected = (await fetch(`${API}/clusters/${api.id}/reports`).then((r) => r.json())).filter((r) => r.message && r.types.includes(types[0])).length;
				return expected > 5 ? texts < expected && more === `Alle ${expected} Texte zeigen` : texts === expected && more === null;
			});
			expect(expected > 5 ? texts < expected && more === `Alle ${expected} Texte zeigen` : texts === expected && more === null, `${texts} texts for ${types[0]}, api has ${expected}, the button says "${more}"`);
			if (more) {
				await page.click('.sheet .more');
				await wait(200);
				texts = await page.eval(`[...document.querySelectorAll('.sheet .voices li')].length`);
				expect(texts === expected && !(await page.has('.sheet .more')), `unfolded, ${texts} texts for ${types[0]}, api has ${expected}`);
			}
			// the reports without a text are counted under the list, not left out silently
			const rows = (await fetch(`${API}/clusters/${api.id}/reports`).then((r) => r.json())).filter((r) => r.types.includes(types[0]));
			const silent = rows.filter((r) => !r.message).length;
			const line = await page.eval(`document.querySelector('.sheet .silent')?.textContent ?? null`);
			expect(texts && silent ? line === `und ${silent} ${silent === 1 ? 'Meldung' : 'Meldungen'} ohne Text` : line === null, `${silent} without text for ${types[0]}, the card says "${line}"`);
			await page.shot(`${size}-card-filter`);
			await page.click('.sheet .type');
		}
		expect(!sheet.includes('diese Woche'), 'card says "diese Woche" though every report is fresh');
		// a long card scrolls inside the sheet, the button at its end comes into view
		const box = await page.eval(`(() => { const s = document.querySelector('.sheet'); return { h: s.getBoundingClientRect().height, scroll: s.scrollHeight, win: innerHeight, wide: innerWidth >= 600, texts: document.querySelectorAll('.sheet .voices li').length }; })()`);
		expect(box.h <= (box.wide ? box.win - 28 : box.win * 0.72) + 1, `sheet is ${box.h} of ${box.win} px high`);
		if (box.scroll > box.h) {
			await page.eval(`document.querySelector('.sheet').scrollTop = 1e6; 0`);
			await wait(200);
			const btn = await page.eval(`(() => { const r = document.querySelector('.sheet .ghost').getBoundingClientRect(); return r.bottom <= innerHeight && r.top >= 0; })()`);
			expect(btn, 'scrolled down, the button at the end is not in view');
			await page.shot(`${size}-card-scrolled`);
			await page.eval(`document.querySelector('.sheet').scrollTop = 0; 0`);
		} else expect(box.wide || box.texts < 8, `${box.texts} texts and the phone sheet does not scroll`);
		expect(await page.has('.pin.cluster.sel'), 'bubble not highlighted');
		const drawn = (layer) => page.eval(`window.__map.queryRenderedFeatures({layers: ['${layer}']}).length`);
		await page.idle();
		expect((await drawn('disc-sel')) === 1, 'selected disc not drawn');
		expect((await drawn('discs')) > 0, 'faint discs not drawn at zoom 15');
		await page.shot(`${size}-disc`);
		await page.eval(`window.__map.zoomTo(14, {duration: 0}); 0`);
		await page.idle();
		expect((await drawn('disc-sel')) === 1, 'selected disc gone at zoom 14');
		expect((await drawn('discs')) === 0, 'faint discs drawn at zoom 14');
	});

	await scenario(`${size}: Meine Meldungen lists my report, tap flies to its bubble`, async () => {
		await page.goto();
		await page.clickText('Meine Meldungen');
		await wait(500);
		const sheet = await page.sheet();
		expect(sheet.includes('Meine Meldungen') && sheet.includes('Zu laut'), `list: "${sheet.split('\n').slice(0, 3).join(' / ')}"`);
		expect(sheet.includes('Zurückziehen'), 'no Zurückziehen');
		// "gerade eben · 56 hier · Sensor fehlt" may wrap between pieces, never inside one
		const split = await page.eval(
			`[...document.querySelectorAll('.sheet .text small span')].filter((s) => s.getClientRects().length > 1).map((s) => s.textContent)`
		);
		expect(split.length === 0, `row piece broken over two lines: ${JSON.stringify(split)}`);
		await page.eval(`window.__map.jumpTo({zoom: 12}); 0`);
		await page.click('.sheet .open');
		await page.settled();
		await wait(300);
		const card = await page.sheet();
		expect(/^\d+ Meldung/m.test(card) && /^Du /m.test(card), `no card of my bubble: "${card.split('\n')[0]}"`);
		await nearlyZoom(16);
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

	await scenario(`${size}: sensor card shows the history, Alles and 7 Tage switch the chart, a touch reads a value`, async () => {
		// a sensor the server has hourly and daily values for, whose pin is on screen after a jump
		// to it (the map stops at the city limit, a box outside it stays off screen)
		const withHistory = [];
		for (const s of await (await fetch(`${API}/sensors`)).json()) {
			const h = Object.values(await (await fetch(`${API}/sensors/${s.id}/history`)).json());
			if (h.length && h.every((x) => x.hourly.length > 2 && x.daily.length > 2)) withHistory.push(s);
		}
		expect(withHistory.length, 'no sensor with history on the server');
		await page.goto();
		expect(await page.until('.pin.sensor', 10000), 'no sensor pins');
		let sensor, pin;
		for (sensor of withHistory) {
			await page.setView(sensor.lon, sensor.lat, 16);
			// the jump has to be over before the pin is measured, and the pin has to be on top at
			// that point (a neighbour pin or the bubble number can sit on it), else the tap misses
			await page.idle();
			await wait(300);
			pin = await page.eval(`(() => { const p = window.__map.project([${sensor.lon}, ${sensor.lat}]); const box = document.querySelector('.map').getBoundingClientRect(); let best, bd = 1e9; for (const el of document.querySelectorAll('.pin.sensor')) { const r = el.getBoundingClientRect(); const d = Math.hypot(r.left + r.width / 2 - box.left - p.x, r.top + r.height / 2 - box.top - p.y); if (d < bd) (best = [el, r.left + r.width / 2, r.top + r.height / 2]), (bd = d); } if (!best || !best[0].contains(document.elementFromPoint(best[1], best[2]))) return null; return [best[1], best[2]]; })()`);
			if (pin && pin[0] > 0 && pin[0] < page.w && pin[1] > 0 && pin[1] < page.h * 0.7) break; // above the sheet
			pin = null;
		}
		expect(pin, `none of ${withHistory.map((s) => s.name).join(', ')} comes on screen`);
		await page.tap(...pin);
		expect(await page.sheetHas(sensor.name), `the tap did not open ${sensor.name}`);
		// the header says how old the value is ("Messwert vor 1 h"), not "live · vor 1 h"
		const age = await page.eval(`[...document.querySelectorAll('.head p')].map((p) => p.textContent.replace(/[ \\t\\n]+/g, ' ')).find((t) => /openSenseMap|Messstation|Lärmsensor/.test(t))`);
		expect(age && /· (Messwert|offline · letzter Wert) (gerade\seben|vor\s)|· noch kein Messwert/.test(age) && !/live/.test(age), `sensor header reads "${age}"`);
		expect(await page.until('.history .read b', 6000), 'no history readout');
		const read = () => page.eval(`document.querySelector('.history .read').innerText`);
		const line = () => page.eval(`document.querySelector('.history path.line')?.getAttribute('d')`);
		const week = await line();
		expect(week, 'no line for 7 Tage');
		await page.clickText('Alles');
		await wait(200);
		const all = await line();
		expect(all && all !== week, 'Alles draws the same line as 7 Tage');
		await page.clickText('7 Tage');
		await wait(200);
		const latest = await read();
		const svg = await page.eval(`JSON.stringify(document.querySelector('.history svg').getBoundingClientRect())`).then(JSON.parse);
		await page.tap(svg.x + svg.width * 0.3, svg.y + svg.height / 2);
		await wait(200);
		const under = await read();
		expect(under !== latest && (await page.has('.history .cursor')), `the touch reads "${under}", before it "${latest}"`);
		// with more than one charted value its tiles switch the chart too, the charted tile is outlined
		const tiles = await page.eval(`[...document.querySelectorAll('button.tile')].map((b) => b.querySelector('.lbl').textContent)`);
		const tabs = await page.eval(`[...document.querySelectorAll('.history .tabs button')].map((b) => b.textContent)`);
		expect(tiles.every((t) => tabs.includes(t)) && (tabs.length > 1 || !tiles.length), `tappable tiles ${tiles} for chart tabs ${tabs}`);
		if (tiles.length > 1) {
			const other = await page.eval(`(() => { const b = [...document.querySelectorAll('button.tile')].find((b) => !b.classList.contains('on')); b.scrollIntoView({ block: 'center' }); const r = b.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2, b.querySelector('.lbl').textContent]; })()`);
			await page.tap(other[0], other[1]);
			await wait(200);
			const on = await page.eval(`[document.querySelector('.history .tabs button.on')?.textContent, document.querySelector('button.tile.on .lbl')?.textContent, document.querySelector('.history svg').getAttribute('aria-label')]`);
			expect(on[0] === other[2] && on[1] === other[2] && on[2] === `Verlauf ${other[2]}`, `tap on the ${other[2]} tile: tab ${on[0]}, tile ${on[1]}, chart "${on[2]}"`);
		}
		await page.shot(`${size}-sensor-history`);
	});

	await scenario(`${size}: a bubble without a sensor nearby says Sensor fehlt`, async () => {
		// the demo's "no data" beat: the pill names what is missing, the reason says where
		const none = (await (await fetch(`${API}/clusters`)).json()).filter((c) => c.status === 'no_data');
		expect(none.length, 'no bubble without a sensor on the server');
		if (!none.length) return;
		await page.goto();
		let c, pin;
		for (c of none) {
			await page.setView(c.lon, c.lat, 16);
			await wait(600);
			pin = await page.eval(`(() => { const p = window.__map.project([${c.lon}, ${c.lat}]); const box = document.querySelector('.map').getBoundingClientRect(); const free = ${FREE}; let best, bd = 1e9; for (const el of document.querySelectorAll('.pin.cluster:not(.group)')) { const r = el.getBoundingClientRect(); const d = Math.hypot(r.left + r.width / 2 - box.left - p.x, r.top + r.height / 2 - box.top - p.y); if (d < bd) (best = el), (bd = d); } return best && bd < 30 ? free(best) : null; })()`);
			if (pin && pin[1] < page.h * 0.7) break;
			pin = null;
		}
		expect(pin, 'no bubble without a sensor comes on screen');
		if (!pin) return;
		await page.tap(...pin);
		await page.until('.sheet .status', 6000);
		const status = await page.eval(`document.querySelector('.sheet .status')?.textContent`);
		expect(status === 'Sensor fehlt', `the pill says "${status}"`);
		expect(await page.sheetHas('Hier fehlt'), 'no reason under the pill');
		// where the next sensors should go: this spot's place among all spots without one (the other runs may add a spot meanwhile)
		const rank = await page.eval(`document.querySelector('.sheet .rank')?.textContent ?? ''`);
		const m = rank.match(/^Platz (\d+) von (\d+) Stellen ohne Sensor, nach Meldungen\.$/);
		expect(none.length < 2 || (m && +m[1] <= +m[2] && +m[2] >= none.length - 1), `the rank line says "${rank}"`);
		await page.shot(`${size}-no-sensor`);
	});

	await scenario(`${size}: about sheet opens and closes`, async () => {
		await page.goto();
		await page.click('.title');
		await wait(300);
		expect((await page.sheet()).includes('Prüfen'), 'about sheet missing');
		expect((await page.sheet()).includes('Baumkataster'), 'about sheet does not say what shade is checked against');
		await page.shot(`${size}-about`);
		await page.click('.title');
		await wait(300);
		expect((await page.sheet()).includes('Melden'), 'home sheet not back');
	});
};

// the flows the phone alone runs
const phone = async ({ page, send, expect, scenario, melden, type, nearlyZoom, same }) => {
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

	await scenario('phone: the report circle is 100 m on the ground, so it doubles per zoom level', async () => {
		await page.goto();
		await melden();
		await page.settled();
		await wait(300);
		const width = () => page.eval(`document.querySelector('.crosshair').getBoundingClientRect().width`);
		await page.eval(`window.__map.jumpTo({center: [9.2, 49.15], zoom: 15}); 0`);
		await wait(300);
		const w15 = await width();
		await page.eval(`window.__map.jumpTo({center: [9.2, 49.15], zoom: 16}); 0`);
		await wait(300);
		const w16 = await width();
		expect(Math.abs(w15 - 64) < 3, `circle at zoom 15 is ${w15} px, not 64`);
		expect(Math.abs(w16 - 128) < 3, `circle at zoom 16 is ${w16} px, not 128`);
		// the hint hangs below the ring, but at most 90 px under the centre dot
		const hintGap = () =>
			page.eval(
				`(() => { const r = document.querySelector('.crosshair').getBoundingClientRect(); return document.querySelector('.hint').getBoundingClientRect().top - (r.top + r.height / 2); })()`
			);
		const g16 = await hintGap();
		expect(Math.abs(g16 - 76) < 4, `hint sits ${g16} px below the centre at zoom 16, not 76`);
		await page.shot('phone-circle-16');
		await page.eval(`window.__map.jumpTo({center: [9.2, 49.15], zoom: 18}); 0`);
		await wait(300);
		const g18 = await hintGap();
		expect(Math.abs(g18 - 102) < 4, `hint sits ${g18} px below the centre at zoom 18, not 102`);
		await page.shot('phone-circle-18');
	});

	await scenario('phone: centre on a bubble shows which one the report joins', async () => {
		const c = (await fetch(`${API}/clusters`).then((r) => r.json())).find((c) => c.count > 1);
		expect(c, 'no bubble with more than one report');
		await page.goto();
		await melden();
		await page.settled();
		await wait(300);
		await page.setView(c.lon, c.lat, 16);
		await wait(400);
		expect(await page.has('.pin.cluster.join'), 'bubble has no ring');
		let hint, count;
		await same(async () => {
			hint = await page.eval(`document.querySelector('.hint').textContent`);
			count = (await fetch(`${API}/clusters`).then((r) => r.json())).find((x) => x.id === c.id)?.count;
			return hint === `Kommt zu den ${count} Meldungen hier dazu`;
		});
		expect(hint === `Kommt zu den ${count} Meldungen hier dazu`, `hint is "${hint}", the API counts ${count}`);
		// the crosshair's dot (10 px and a 3 px white ring) must not lie on the bubble's number
		const under = await page.eval(`(() => {
			const d = document.querySelector('.crosshair').getBoundingClientRect();
			const x = d.left + d.width / 2, y = d.top + d.height / 2;
			const n = document.querySelector('.pin.cluster.join span').getBoundingClientRect();
			return x + 8 > n.left && x - 8 < n.right && y + 8 > n.top && y - 8 < n.bottom;
		})()`);
		expect(!under, 'the centre dot lies on the bubble number');
		await page.shot('phone-join');
		// 150 m east: outside the radius
		await page.setView(c.lon + 0.00206, c.lat, 16);
		await wait(400);
		expect(!(await page.has('.pin.cluster.join')), 'ring still there 150 m away');
		expect((await page.eval(`document.querySelector('.hint').textContent`)).startsWith('Schieb'), 'hint not back');
	});

	await scenario('phone: zoom out in report mode greys the circle and disables Melden', async () => {
		await page.goto();
		await melden();
		await page.settled();
		await wait(300);
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
		expect(c1.lng > 9.25, `did not reach the east edge: ${c1.lng}`);
		expect(await page.eval(`window.__inCity(${c1.lat}, ${c1.lng})`), `centre left the city: ${c1.lng} ${c1.lat}`);
	});

	await scenario('phone: jump far outside, centre snaps to the city limit, zoom-out stops where the city fills the screen', async () => {
		await page.goto();
		await page.setView(9.5, 49.3, 8);
		await wait(600);
		const c = await page.center();
		expect(await page.eval(`window.__inCity(${c.lat}, ${c.lng})`), `centre left the city: ${c.lng} ${c.lat}`);
		expect(c.lng > 9.25 && c.lat > 49.16, `centre not at the north-east edge of the city: ${c.lng} ${c.lat}`);
		const z = await page.zoom();
		expect(z > 9.5 && z < 12.5 && Math.abs(z - (await page.eval(`window.__map.getMinZoom()`))) < 0.01, `zoom ${z} is not the min zoom`);
		await page.eval(`window.__map.jumpTo({center: [9.1733, 49.1514]}); 0`);
		await wait(300);
		const fits = await page.eval(`(() => { const m = window.__map, b = m.getBounds(); return b.getWest() < 9.0444 && b.getEast() > 9.3021 && b.getSouth() < 49.0929 && b.getNorth() > 49.2099 })()`);
		expect(fits, 'city does not fit the screen at min zoom');
		await page.shot('phone-min-zoom');
	});

	await scenario('phone: zoomed out, touching bubbles merge and a tap on a group zooms in', async () => {
		await page.goto();
		// two people 150 m apart north of the runner's bubble: a group at zoom 12 for sure
		for (const [i, dlon] of [[1, 0], [2, 0.0021]]) {
			const tok = `e2e-group-${i}-`.padEnd(32, '0');
			tokens.add(tok);
			await fetch(`${API}/reports`, { method: 'POST', headers: { 'content-type': 'application/json', 'x-device': tok }, body: JSON.stringify({ lat: CITY.latitude + 0.003, lon: CITY.longitude + dlon, types: ['air'] }) });
		}
		const apiCount = async () => (await fetch(`${API}/clusters`).then((r) => r.json())).reduce((n, c) => n + c.count, 0);
		const onScreen = () => page.eval(`[...document.querySelectorAll('.pin.cluster')].reduce((n, p) => n + +p.textContent, 0)`);
		await page.setView(CITY.longitude, CITY.latitude, 12);
		const agree = async () => (await onScreen()) === (await apiCount());
		expect(await same(agree, 8000), `bubbles say ${await onScreen()} reports, the API ${await apiCount()}`);
		const groups = await page.eval(`document.querySelectorAll('.pin.cluster.group').length`);
		expect(groups > 0, 'no merged bubble at zoom 12');
		await page.shot('phone-groups');
		const group = await page.eval(`(() => { const free = ${FREE}; for (const p of document.querySelectorAll('.pin.cluster.group')) { const at = free(p); if (at) return at; } return null; })()`);
		expect(group, 'no free spot on the group to tap');
		await page.tap(...group);
		await page.settled();
		await wait(500);
		// fitBounds on the members: how far in depends on their spread, at least a level
		expect((await page.zoom()) >= 13 - 1e-6, `tap on the group left the zoom at ${(await page.zoom()).toFixed(2)}`);
		expect(!(await page.has('.sheet .badge')), 'a group opened a card instead of zooming in');
		expect(await same(agree), `after the zoom the bubbles say ${await onScreen()} reports, the API ${await apiCount()}`);
	});

	await scenario('phone: filters narrow the bubbles, the home sheet says so, the × brings all back', async () => {
		await page.goto();
		await page.setView(CITY.longitude, CITY.latitude, 12); // the whole city: every bubble on screen
		await wait(800);
		const sum = (cs) => cs.reduce((n, c) => n + c.count, 0);
		const onScreen = () => page.eval(`[...document.querySelectorAll('.pin.cluster')].reduce((n, p) => n + +p.textContent, 0)`);
		const api = (q = '') => fetch(`${API}/clusters${q}`).then((r) => r.json());
		// counted by the chosen type only, a report naming two types is still one
		const noise = (cs) => cs.filter((c) => c.types.noise).map((c) => ({ ...c, count: Math.min(c.count, c.types.noise) }));
		let want;
		const settle = (expected, q) => same(async () => (want = sum(expected(await api(q)))) === (await onScreen()));
		await page.click('[aria-label="Ebenen"]');
		await wait(300);
		await page.clickText('Zu laut');
		expect(await settle(noise), `only Zu laut: bubbles say ${await onScreen()}, the API ${want}`);
		expect((await page.sheet()).includes('nur Zu laut'), 'the section does not say nur Zu laut');
		await page.eval(`[...document.querySelectorAll('.sheet .seg button')].find((b) => b.textContent === '10').click(); 0`);
		expect(await settle((cs) => noise(cs).filter((c) => c.count >= 10)), `mindestens 10: bubbles say ${await onScreen()}, the API ${want}`);
		await page.shot('phone-filter-sheet');
		await page.eval(`[...document.querySelectorAll('.sheet .seg button')].find((b) => b.textContent === '7').click(); 0`);
		expect(await settle((cs) => noise(cs).filter((c) => c.count >= 10), '?days=7'), `7 Tage: bubbles say ${await onScreen()}, the API ${want}`);
		await page.click('[aria-label="Schließen"]');
		await wait(300);
		expect((await page.sheet()).includes('Zu laut · ab 10 Meldungen · 7 Tage'), `home sheet says "${await page.sheet()}"`);
		expect(await page.has('.rb.dot'), 'no dot on the layers button');
		await page.shot('phone-filter-home');
		// kept over a reload
		await page.goto();
		await page.setView(CITY.longitude, CITY.latitude, 12);
		await wait(800);
		expect((await page.sheet()).includes('ab 10 Meldungen'), 'the filter did not survive a reload');
		await page.click('[aria-label="Filter aufheben"]');
		expect(await settle((cs) => cs), `after the reset bubbles say ${await onScreen()}, the API ${want}`);
		expect(!(await page.has('.rb.dot')) && !(await page.sheetHas('ab 10')), 'the filter line or the dot stayed');
	});

	await scenario('phone: a report the filter hides still says Gemeldet', async () => {
		// only Schlechte Luft from 10 reports: the Zu-laut bubble at my position is filtered out
		await page.goto();
		await page.eval(`localStorage.setItem('filter', JSON.stringify({ types: ['air'], min: 10 })); 0`);
		await page.goto();
		await melden();
		await page.settled();
		await wait(300);
		await page.clickText('Zu laut');
		await page.clickText('Melden');
		let toast = '';
		for (let t = 0; t < 6000 && !toast.startsWith('Gemeldet'); t += 200) {
			await wait(200);
			toast = await page.eval(`document.querySelector('.toast')?.textContent ?? ''`);
		}
		expect(toast.includes('Filter'), `no toast that the filter hides it: "${toast}"`);
		expect((await page.sheet()).includes('Melden'), 'home sheet not back');
		await page.shot('phone-sent-filtered');
		await page.eval(`localStorage.removeItem('filter'); 0`);
	});

	await scenario('phone: a sensor under a big bubble is still tappable', async () => {
		await page.goto();
		// the NoiseNode is 30 m from the runner's bubble: at zoom 15 that is 19 px, inside the bubble
		await page.setView(CITY.longitude, CITY.latitude, 15);
		await wait(500);
		const sensor = await page.eval(`(() => { const r = document.querySelector('.pin.sensor.ours').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()`);
		const bubble = await page.eval(`(() => { const r = [...document.querySelectorAll('.pin.cluster')].map((p) => p.getBoundingClientRect()).find((r) => r.width > 28 + 6); return r ? [r.x + r.width / 2, r.y + r.height / 2, r.width] : null; })()`);
		expect(bubble && Math.hypot(bubble[0] - sensor[0], bubble[1] - sensor[1]) < bubble[2] / 2, 'the sensor is not under a bigger bubble');
		await page.tap(...sensor);
		await wait(500);
		expect((await page.sheet()).includes('NoiseNode'), 'the tap opened the bubble, not the sensor');
		await page.shot('phone-sensor-under-bubble');
	});

	await scenario('phone: withdraw a report, gone from the list and the server', async () => {
		await page.goto();
		const token = await page.eval(`localStorage.getItem('device')`);
		await fetch(`${API}/reports`, { method: 'POST', headers: { 'content-type': 'application/json', 'x-device': token }, body: JSON.stringify({ lat: CITY.latitude, lon: CITY.longitude, types: ['heat'] }) });
		await page.goto();
		const mine = async () => (await fetch(`${API}/reports/mine`, { headers: { 'x-device': token } }).then((r) => r.json())).length;
		const n = await mine();
		expect(n > 0, 'the report of this device is not on the server');
		await page.clickText('Meine Meldungen');
		await wait(500);
		expect((await page.eval(`document.querySelectorAll('.sheet .row').length`)) === n, `list has not ${n} rows`);
		await page.clickText('Zurückziehen');
		await wait(200);
		expect((await page.sheet()).includes('Wirklich?'), 'first tap did not ask');
		await page.clickText('Wirklich?');
		await wait(1000);
		expect((await page.eval(`document.querySelectorAll('.sheet .row').length`)) === n - 1, 'row still in the list');
		expect((await mine()) === n - 1, 'report still on the server');
		expect((await page.eval(`document.querySelector('.toast')?.innerText`)) === 'Meldung zurückgezogen', 'no toast');
	});

	await scenario('phone: a name, and a second device linked by code brings its reports along', async () => {
		await page.goto();
		const token = await page.eval(`localStorage.getItem('device')`);
		const api = (path, init = {}, t = token) => fetch(`${API}${path}`, { ...init, headers: { 'x-device': t, 'content-type': 'application/json', ...init.headers } });
		await page.clickText('Meine Meldungen');
		await wait(500);
		await page.clickText('Name angeben');
		await wait(200);
		await type('.sheet input', 'Kim');
		// the keyboard's key saves, as the Speichern button does
		expect(await page.eval(`document.querySelector('.sheet input').enterKeyHint`) === 'done', 'the keyboard key of the name field does not say done');
		await page.eval(`document.querySelector('.sheet input').dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })); 0`);
		expect(await page.sheetHas('Kim'), 'name not on the sheet');
		expect((await api('/me').then((r) => r.json())).name === 'Kim', 'name not saved');
		// a second device with a report of its own claims this device's code
		const other = 'e2e-other-' + Math.random().toString(16).slice(2).padEnd(24, '0');
		tokens.add(other);
		await api('/reports', { method: 'POST', body: JSON.stringify({ lat: 49.14, lon: 9.2, types: ['heat'] }) }, other);
		const before = (await api('/reports/mine').then((r) => r.json())).length;
		await page.clickText('Anderes Gerät verknüpfen');
		await wait(800);
		const code = await page.eval(`document.querySelector('.sheet .code')?.innerText`);
		expect(/^[A-Z2-9]{6}$/.test(code ?? ''), `code is ${code}`);
		const small = await page.eval(`[...document.querySelectorAll('.sheet input')].map((i) => parseFloat(getComputedStyle(i).fontSize)).filter((px) => px < 16)`);
		expect(!small.length, `inputs at ${small.join(', ')}px, iOS Safari zooms in on focus below 16px`);
		await page.shot('phone-link');
		// a wrong code typed on this device
		await type('.sheet .claim input', 'ZZZZZZ');
		page.allowLog(/400 \(Bad Request\) .*\/me\/claim/);
		// Enter in the field links, as the Verknüpfen button does
		expect(await page.eval(`document.querySelector('.sheet .claim input').enterKeyHint`) === 'go', 'the keyboard key of the code field does not say go');
		await page.eval(`document.querySelector('.sheet .claim input').dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })); 0`);
		await wait(800);
		expect((await page.eval(`document.querySelector('.toast')?.innerText`)) === 'Code unbekannt oder abgelaufen', 'no toast for a bad code');
		// the other device claims the code, this one notices on its own
		const claimed = await api('/me/claim', { method: 'POST', body: JSON.stringify({ code }) }, other).then((r) => r.json());
		expect(claimed.name === 'Kim' && claimed.devices === 2, `claim gave ${JSON.stringify(claimed)}`);
		expect((await api('/reports/mine').then((r) => r.json())).length === before + 1, 'the other device\'s report did not come along');
		expect(await page.sheetHas('Zu heiß', 6000), `sheet did not come back with the linked report: "${(await page.sheet()).split('\n')[0]}"`);
		expect((await page.sheet()).includes('(2)'), 'sheet does not count 2 devices');
		expect((await page.eval(`document.querySelector('.toast')?.innerText`)) === 'Geräte verknüpft', 'no linked toast');
	});

	await scenario('phone: the device token stays over reloads and makes one user, a cleared device is a new one', async () => {
		await page.goto();
		const token = () => page.eval(`localStorage.getItem('device')`);
		// this profile sent the reports above: the server knows which bubbles are mine, and only with the header
		const t0 = await token();
		const mine = async (headers) => (await fetch(`${API}/clusters`, { headers }).then((r) => r.json())).reduce((n, c) => n + c.mine, 0);
		expect((await mine({ 'x-device': t0 })) >= 1, 'no bubble is mine with my token');
		expect((await mine({})) === 0, 'a bubble is mine without a token');
		const list = await fetch(`${API}/reports/mine`, { headers: { 'x-device': t0 } }).then((r) => r.json());
		expect(list.length >= 1 && !('user_id' in list[0]), `/reports/mine: ${JSON.stringify(list[0])}`);
		expect((await fetch(`${API}/reports/mine`)).status === 400, '/reports/mine without a token did not refuse');
		expect(await page.has('.pin.cluster.mine'), 'no bubble on the map is marked as mine');
		await page.forget();
		await page.goto();
		expect(!(await page.has('.pin.cluster.mine')), 'a cleared device still sees its bubbles as mine');
		const me = async () => (await fetch(`${API}/me`, { headers: { 'x-device': await token() } }).then((r) => r.json())).id;
		const t1 = await token();
		expect(t1 && t1.length === 32, `token is ${t1}`);
		const id1 = await me();
		await page.goto();
		expect((await token()) === t1, 'token changed on reload');
		expect((await me()) === id1, 'user changed on reload');
		await page.forget();
		await page.goto();
		expect((await token()) !== t1, 'cleared device kept its token');
		expect((await me()) !== id1, 'cleared device kept its user');
		const noHeader = await fetch(`${API}/reports`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ lat: 49.15, lon: 9.22, types: ['noise'] }) });
		expect(noHeader.status === 400, `report without a device token got ${noHeader.status}`);
	});

	await scenario('phone: a report from another device shows up without waiting for the poll', async () => {
		await page.goto();
		await page.setView(CITY.longitude, CITY.latitude, 15);
		for (let i = 0; i < 20 && !(await page.eval('window.__live')); i++) await wait(250);
		expect(await page.eval('window.__live'), 'event stream not up');
		const count = () => page.eval(`[...document.querySelectorAll('.pin.cluster')].reduce((n, p) => n + +p.textContent, 0)`);
		const before = await count();
		const tok = `e2e-live-${Date.now()}`.padEnd(32, '0');
		tokens.add(tok);
		await fetch(`${API}/reports`, { method: 'POST', headers: { 'content-type': 'application/json', 'x-device': tok }, body: JSON.stringify({ lat: CITY.latitude, lon: CITY.longitude, types: ['heat'] }) });
		let after = before;
		for (let i = 0; i < 10 && after === before; i++) (await wait(250)), (after = await count());
		expect(after > before, `bubbles say ${before} reports before and ${after} after, within 2.5 s`);
	});

	await scenario('phone: basemap down, the bubbles and sensor pins still show on a plain map', async () => {
		await send('Network.enable');
		await send('Network.setBlockedURLs', { urls: ['*basemaps.cartocdn.com*'] });
		await page.goto();
		await wait(1000);
		const bubbles = await page.eval(`document.querySelectorAll('.pin.cluster').length`);
		const pins = await page.eval(`document.querySelectorAll('.pin.sensor').length`);
		const plain = await page.eval(`!!window.__map.getLayer('bg')`);
		await send('Network.setBlockedURLs', { urls: [] });
		await send('Network.disable');
		expect(plain, 'no plain background style');
		expect(bubbles > 0, 'no bubbles without the basemap');
		expect(pins > 0, 'no sensor pins without the basemap');
	});

	await scenario('phone: backend down shows the offline note and recovers', async () => {
		await page.goto();
		await send('Network.enable');
		await send('Network.emulateNetworkConditions', { offline: true, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
		page.allowLog(/ERR_INTERNET_DISCONNECTED/);
		await wait(6500);
		expect(await page.has('.down'), 'no offline note');
		await send('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
		await wait(6500);
		expect(!(await page.has('.down')), 'offline note stays');
		await send('Network.disable');
	});
};


const t0 = Date.now();
const results = (await Promise.all([...Object.keys(SIZES).map((size) => lane((t) => sized(size, t))), lane(phone)])).flat();
const failed = results.filter((r) => r.fails.length);
// the run's own reports go again, so the local map does not fill up with test bubbles
let withdrawn = 0;
const left = new Set();
for (const t of tokens) {
	const headers = { 'x-device': t };
	try {
		const mine = await fetch(`${API}/reports/mine`, { headers }).then((r) => (r.ok ? r.json() : Promise.reject()));
		for (const r of mine) {
			if ((await fetch(`${API}/reports/${r.id}`, { method: 'DELETE', headers })).ok) withdrawn++;
			else left.add(t);
		}
	} catch {
		left.add(t);
	}
}
keep(left);
console.log(`\n${withdrawn} test reports withdrawn${left.size ? `, ${left.size} devices left for the next run` : ''}`);
console.log(`\n${results.length - failed.length}/${results.length} ok in ${((Date.now() - t0) / 1000).toFixed(0)} s, screenshots in e2e/out/`);
process.exit(failed.length ? 1 : 0);
