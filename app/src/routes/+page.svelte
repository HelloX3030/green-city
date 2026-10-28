<script lang="ts">
	import { onMount } from 'svelte';
	import Map from '#lib/Map.svelte';
	import Icon from '#lib/Icon.svelte';
	import ReportSheet from '#lib/ReportSheet.svelte';
	import ClusterCard from '#lib/ClusterCard.svelte';
	import SensorCard from '#lib/SensorCard.svelte';
	import LayerSheet from '#lib/LayerSheet.svelte';
	import AboutSheet from '#lib/AboutSheet.svelte';
	import MySheet from '#lib/MySheet.svelte';
	import { inCity } from '#lib/city.ts';
	import { DEFAULT, applyFilter, describeFilter, isDefault, loadFilter, saveFilter, type Filter } from '#lib/filter.ts';
	import {
		deleteReport,
		getBikes,
		getClusters,
		getMe,
		getMine,
		getSensors,
		subscribe,
		type Cluster,
		type LayerId,
		type Me,
		type Report,
		type Sensor
	} from '#lib/api.ts';

	let clusters = $state<Cluster[]>([]);
	let sensors = $state<Sensor[]>([]);
	let selected = $state<Cluster | null>(null);
	let sensor = $state<Sensor | null>(null);
	let layers = $state(new Set<LayerId>());
	let filter = $state<Filter>(loadFilter());
	const shown = $derived(applyFilter(clusters, filter)); // the bubbles on the map
	const filtering = $derived(!isDefault(filter)); // a dot on the layers button and a line on the home sheet say so
	let layersOpen = $state(false);
	let aboutOpen = $state(false);
	let mine = $state<Report[]>([]);
	let me = $state<Me | null>(null);
	let mineOpen = $state(false);
	let bikes = $state<Awaited<ReturnType<typeof getBikes>> | null>(null);
	let sent = $state(false); // the card right after sending says Gemeldet
	let reporting = $state(false);
	let pick = $state<{ lat: number; lon: number } | null>(null);
	let offline = $state(false);
	let live = false; // the event stream is up: changes come pushed, the poll is a once-a-minute fallback
	let sheetHeight = $state(0);
	let toast = $state('');
	let toastTimer: ReturnType<typeof setTimeout>;
	let map: Map;

	// a poll that comes back after a newer one is dropped, a late failure must not undo a recovery
	let polls = 0;
	let done = 0;
	async function refresh() {
		const n = ++polls;
		let next: Cluster[] | null = null;
		try {
			next = await getClusters(filter.days);
		} catch {}
		if (n <= done) return;
		done = n;
		if (!next) return (offline = true);
		clusters = next;
		if (selected) selected = shown.find((c) => c.id === selected!.id) ?? null;
		offline = false;
	}

	async function refreshSensors() {
		try {
			sensors = await getSensors();
			if (sensor) sensor = sensors.find((s) => s.id === sensor!.id) ?? sensor;
		} catch {}
	}

	async function refreshBikes() {
		if (!layers.has('bikes')) return;
		try {
			bikes = await getBikes();
		} catch {}
	}

	async function refreshMine() {
		try {
			[mine, me] = await Promise.all([getMine(), getMe()]);
		} catch {}
	}

	function linked() {
		refreshMine();
		refresh();
	}

	function setFilter(f: Filter) {
		const days = f.days !== filter.days;
		filter = f;
		saveFilter(f);
		if (selected) selected = shown.find((c) => c.id === selected!.id) ?? null;
		if (days) refresh();
	}

	function toggle(id: LayerId) {
		const next = new Set(layers);
		next.has(id) ? next.delete(id) : next.add(id);
		layers = next;
		if (id === 'bikes' && !bikes) refreshBikes();
	}

	onMount(() => {
		refresh();
		refreshSensors();
		refreshMine();
		const all = () => {
			refresh();
			refreshMine();
		};
		const stop = subscribe(all, (up) => {
			if (up && !live) all(); // whatever happened while the stream was down
			live = up;
			if (import.meta.env.DEV) Object.assign(window, { __live: up });
		});
		let ticks = 0;
		const t = setInterval(() => {
			ticks++;
			if (!live || ticks % 12 === 0) refresh();
			if (!live && mineOpen) refreshMine();
		}, 5000);
		const u = setInterval(refreshSensors, 30000);
		const v = setInterval(refreshBikes, 300000);
		// back from another tab or a locked phone: everything fresh
		const visible = () => {
			if (document.visibilityState !== 'visible') return;
			all();
			refreshSensors();
		};
		document.addEventListener('visibilitychange', visible);
		return () => {
			stop();
			clearInterval(t);
			clearInterval(u);
			clearInterval(v);
			document.removeEventListener('visibilitychange', visible);
		};
	});

	function say(msg: string) {
		toast = msg;
		clearTimeout(toastTimer);
		toastTimer = setTimeout(() => (toast = ''), 3000);
	}

	// position of the phone: fly there, or say why not
	function locate(then?: (lat: number, lon: number) => void, fail?: () => void) {
		if (!navigator.geolocation) {
			say('Standort nicht verfügbar');
			return fail?.();
		}
		navigator.geolocation.getCurrentPosition(
			(p) => {
				const { latitude: lat, longitude: lon } = p.coords;
				if (!inCity(lat, lon)) {
					say('Du bist außerhalb von Heilbronn');
					return fail?.();
				}
				map.showMe(lat, lon);
				(then ?? map.flyTo)(lat, lon);
			},
			() => {
				say('Standort nicht verfügbar');
				fail?.();
			},
			{ enableHighAccuracy: true, timeout: 5000 }
		);
	}

	function startReport(at?: { lat: number; lon: number }) {
		selected = null;
		sensor = null;
		layersOpen = aboutOpen = mineOpen = false;
		reporting = true;
		if (at) return map.flyTo(at.lat, at.lon, 16);
		// fly to the phone's position if it comes quickly, else zoom in where we are
		let done = false;
		const fallback = () => {
			if (done) return;
			done = true;
			map.ensureZoom(15);
		};
		const timer = setTimeout(fallback, 2000);
		locate(
			(lat, lon) => {
				clearTimeout(timer);
				if (done) return map.flyTo(lat, lon, 16);
				done = true;
				map.flyTo(lat, lon, 16);
			},
			() => {
				clearTimeout(timer);
				fallback();
			}
		);
	}

	async function onsent(r: Report) {
		reporting = false;
		await refresh();
		selected = shown.find((c) => c.report_ids.includes(r.id)) ?? null;
		sent = true;
		refreshMine();
	}

	function openMine() {
		mineOpen = !mineOpen;
		if (mineOpen) {
			selected = sensor = null;
			layersOpen = aboutOpen = reporting = false;
			refreshMine();
		}
	}

	// from the list to the bubble on the map, or to the spot if the report fell out of the 14 days
	function showReport(r: Report) {
		mineOpen = false;
		const c = clusters.find((x) => x.report_ids.includes(r.id));
		if (c) select(c);
		else say('Nicht mehr auf der Karte, älter als 14 Tage');
		map.flyTo(c?.lat ?? r.lat, c?.lon ?? r.lon, 16);
	}

	async function withdraw(r: Report) {
		try {
			await deleteReport(r.id);
		} catch {
			return say('Zurückziehen fehlgeschlagen');
		}
		mine = mine.filter((x) => x.id !== r.id);
		say('Meldung zurückgezogen');
		refresh();
	}

	function select(c: Cluster | null) {
		selected = c;
		sensor = null;
		sent = false;
		if (c) layersOpen = aboutOpen = mineOpen = false;
	}

	function openAbout() {
		aboutOpen = !aboutOpen;
		if (aboutOpen) {
			selected = sensor = null;
			layersOpen = reporting = mineOpen = false;
		}
	}
</script>

<svelte:head><title>Heilbronn meldet</title></svelte:head>

<Map
	bind:this={map}
	clusters={shown}
	{sensors}
	{bikes}
	{layers}
	{sheetHeight}
	selected={selected ?? sensor}
	picking={reporting}
	onpick={(p) => (pick = p)}
	onselect={select}
	onselectsensor={(s) => {
		sensor = s;
		selected = null;
		layersOpen = aboutOpen = mineOpen = false;
	}}
/>

<button class="title glass" class:on={aboutOpen} onclick={openAbout}><Icon name="leaf" size={17} />Heilbronn meldet</button>
{#if offline}<div class="down">Server nicht erreichbar</div>{/if}
{#if toast}<div class="toast glass">{toast}</div>{/if}

<div class="stack">
	<button class="rb glass" onclick={() => locate()} aria-label="Mein Standort"><Icon name="locate" /></button>
	{#if !reporting}
		<button
			class="rb glass"
			class:on={layersOpen}
			class:dot={filtering}
			onclick={() => ((layersOpen = !layersOpen), (aboutOpen = mineOpen = false))}
			aria-label="Ebenen"><Icon name="layers" /></button
		>
	{/if}
	<button class="rb glass zoom" onclick={() => map.zoomBy(1)} aria-label="Vergrößern"><Icon name="plus" /></button>
	<button class="rb glass zoom" onclick={() => map.zoomBy(-1)} aria-label="Verkleinern"><Icon name="minus" /></button>
</div>

<div class="sheet glass" bind:clientHeight={sheetHeight}>
	<div class="grab"></div>
	{#if reporting}
		<ReportSheet location={pick} onclose={() => (reporting = false)} onsent={onsent} />
	{:else if selected}
		<ClusterCard cluster={selected} days={filter.days} {sent} onclose={() => (selected = null)} onreport={() => startReport(selected!)} />
	{:else if sensor}
		<SensorCard {sensor} onclose={() => (sensor = null)} />
	{:else if layersOpen}
		<LayerSheet {layers} {filter} ontoggle={toggle} onfilter={setFilter} onclose={() => (layersOpen = false)} />
	{:else if aboutOpen}
		<AboutSheet onclose={() => (aboutOpen = false)} />
	{:else if mineOpen}
		<MySheet reports={mine} {clusters} {me} onopen={showReport} onwithdraw={withdraw} onchanged={linked} onsay={say} onclose={() => (mineOpen = false)} />
	{:else}
		<button class="primary" onclick={() => startReport()}><Icon name="plus" />Melden</button>
		<button class="ghost" onclick={openMine}>Meine Meldungen{mine.length ? ` · ${mine.length}` : ''}</button>
		{#if filtering}
			<div class="filter">
				<button class="what" onclick={() => (layersOpen = true)}><Icon name="layers" size={13} />{describeFilter(filter)}</button>
				<button class="off" onclick={() => setFilter(DEFAULT)} aria-label="Filter aufheben"><Icon name="x" size={12} /></button>
			</div>
		{/if}
		<div class="legend">
			<span><i class="s"></i>Sensor</span>
			<span><i class="o"></i>Unser NoiseNode</span>
			<span><i class="m"></i>Meldungen</span>
		</div>
	{/if}
</div>

<style>
	.title {
		z-index: 3;
		position: absolute;
		top: calc(14px + env(safe-area-inset-top));
		left: 14px;
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 9px 14px 9px 12px;
		border-radius: 999px;
		font-weight: 700;
		font-size: 15px;
		letter-spacing: -0.01em;
		color: var(--ink);
	}
	.title :global(svg) {
		color: var(--accent);
	}
	.title.on {
		background: var(--accent);
		color: var(--on-accent);
	}
	.title.on :global(svg) {
		color: var(--on-accent);
	}
	.down {
		z-index: 3;
		position: absolute;
		top: calc(60px + env(safe-area-inset-top));
		left: 14px;
		background: #a03d3d;
		color: #fff;
		padding: 5px 10px;
		border-radius: 999px;
		font-size: 12px;
	}
	.toast {
		z-index: 4;
		position: absolute;
		top: calc(70px + env(safe-area-inset-top));
		left: 50%;
		transform: translateX(-50%);
		padding: 8px 14px;
		border-radius: 999px;
		font-size: 13px;
		font-weight: 500;
		white-space: nowrap;
	}
	.stack {
		z-index: 3;
		position: absolute;
		top: calc(14px + env(safe-area-inset-top));
		right: 14px;
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.rb {
		width: 42px;
		height: 42px;
		border-radius: 50%;
		display: grid;
		place-items: center;
		color: var(--ink);
	}
	.rb.on {
		background: var(--accent);
		color: var(--on-accent);
	}
	.rb {
		position: relative;
	}
	.rb.dot::after {
		/* a filter is set */
		content: '';
		position: absolute;
		top: 4px;
		right: 4px;
		width: 9px;
		height: 9px;
		border-radius: 50%;
		background: var(--accent);
		border: 2px solid #fff;
	}
	.rb.on.dot::after {
		background: #fff;
		border-color: var(--accent);
	}
	.filter {
		display: flex;
		justify-content: center;
		align-items: center;
		gap: 4px;
		margin-top: 8px;
		font-size: 12px;
		color: var(--ink2);
	}
	.filter .what {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		height: 24px;
		padding: 0 8px;
		border-radius: 12px;
		background: var(--fill);
		color: var(--ink2);
		font-size: 12px;
		font-weight: 500;
		min-width: 0;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.filter .what :global(svg) {
		flex: none;
		color: var(--accent);
	}
	.filter .off {
		flex: none;
		width: 24px;
		height: 24px;
		border-radius: 50%;
		background: var(--fill);
		display: grid;
		place-items: center;
		color: var(--ink2);
	}
	@media (pointer: coarse) {
		.zoom {
			display: none;
		}
	}
	.sheet {
		z-index: 3;
		position: absolute;
		left: 0;
		right: 0;
		bottom: 0;
		padding: 8px 18px calc(18px + env(safe-area-inset-bottom));
		border-radius: var(--radius) var(--radius) 0 0;
		/* a long card scrolls inside, the map keeps the top */
		max-height: 72%;
		box-sizing: border-box;
		overflow-y: auto;
		overscroll-behavior: contain;
		box-shadow: 0 -1px 0 rgba(0, 0, 0, 0.05), 0 -10px 30px rgba(0, 0, 0, 0.08);
	}
	@media (min-width: 600px) {
		.sheet {
			right: auto;
			left: 14px;
			bottom: 14px;
			width: 400px;
			max-height: calc(100% - 28px);
			padding: 18px;
			border-radius: var(--radius);
			box-shadow: var(--shadow);
		}
		.grab {
			display: none;
		}
	}
	.grab {
		width: 36px;
		height: 5px;
		border-radius: 3px;
		background: rgba(0, 0, 0, 0.18);
		margin: 0 auto 12px;
	}
	.primary {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 8px;
		width: 100%;
		height: 50px;
		border-radius: 14px;
		background: var(--accent);
		color: var(--on-accent);
		font-weight: 600;
		font-size: 16px;
	}
	.ghost {
		display: block;
		width: 100%;
		margin-top: 6px;
		height: 36px;
		color: var(--ink2);
		font-weight: 500;
		font-size: 14px;
	}
	.legend {
		display: flex;
		gap: 16px;
		justify-content: center;
		margin-top: 6px;
		font-size: 12px;
		color: var(--ink2);
	}
	.legend span {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.legend i {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		background: #fff;
		border: 1.5px solid rgba(0, 0, 0, 0.25);
	}
	.legend .o {
		border: 2px solid var(--accent);
	}
	.legend .m {
		background: #6f63b8;
		border: 0;
	}
</style>
