<script lang="ts">
	import { onMount } from 'svelte';
	import Map from '#lib/Map.svelte';
	import Icon from '#lib/Icon.svelte';
	import ReportSheet from '#lib/ReportSheet.svelte';
	import ClusterCard from '#lib/ClusterCard.svelte';
	import SensorCard from '#lib/SensorCard.svelte';
	import LayerSheet from '#lib/LayerSheet.svelte';
	import AboutSheet from '#lib/AboutSheet.svelte';
	import {
		getBikes,
		getClusters,
		getSensors,
		type Cluster,
		type LayerId,
		type Report,
		type Sensor
	} from '#lib/api.ts';

	let clusters = $state<Cluster[]>([]);
	let sensors = $state<Sensor[]>([]);
	let selected = $state<Cluster | null>(null);
	let sensor = $state<Sensor | null>(null);
	let layers = $state(new Set<LayerId>());
	let layersOpen = $state(false);
	let aboutOpen = $state(false);
	let bikes = $state<Awaited<ReturnType<typeof getBikes>> | null>(null);
	let mine = $state(false);
	let reporting = $state(false);
	let pick = $state<{ lat: number; lon: number } | null>(null);
	let offline = $state(false);
	let sheetHeight = $state(0);
	let map: Map;

	async function refresh() {
		try {
			clusters = await getClusters();
			if (selected) selected = clusters.find((c) => c.id === selected!.id) ?? null;
			offline = false;
		} catch {
			offline = true;
		}
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

	function toggle(id: LayerId) {
		const next = new Set(layers);
		next.has(id) ? next.delete(id) : next.add(id);
		layers = next;
		if (id === 'bikes' && !bikes) refreshBikes();
	}

	onMount(() => {
		refresh();
		refreshSensors();
		const t = setInterval(refresh, 5000);
		const u = setInterval(refreshSensors, 30000);
		const v = setInterval(refreshBikes, 300000);
		return () => {
			clearInterval(t);
			clearInterval(u);
			clearInterval(v);
		};
	});

	function locate(then?: (lat: number, lon: number) => void) {
		navigator.geolocation?.getCurrentPosition(
			(p) => {
				map.showMe(p.coords.latitude, p.coords.longitude);
				(then ?? map.flyTo)(p.coords.latitude, p.coords.longitude);
			},
			() => {},
			{ enableHighAccuracy: true, timeout: 5000 }
		);
	}

	function startReport(at?: { lat: number; lon: number }) {
		selected = null;
		sensor = null;
		layersOpen = false;
		aboutOpen = false;
		reporting = true;
		if (at) map.flyTo(at.lat, at.lon, 16);
		else locate();
	}

	async function sent(r: Report) {
		reporting = false;
		await refresh();
		selected = clusters.find((c) => c.report_ids.includes(r.id)) ?? null;
		mine = true;
	}

	function select(c: Cluster | null) {
		selected = c;
		sensor = null;
		mine = false;
		if (c) layersOpen = aboutOpen = false;
	}

	function openAbout() {
		aboutOpen = !aboutOpen;
		if (aboutOpen) {
			selected = sensor = null;
			layersOpen = reporting = false;
		}
	}
</script>

<svelte:head><title>Heilbronn meldet</title></svelte:head>

<Map
	bind:this={map}
	{clusters}
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
		layersOpen = aboutOpen = false;
	}}
/>

<button class="title glass" class:on={aboutOpen} onclick={openAbout}><Icon name="leaf" size={17} />Heilbronn meldet</button>
{#if offline}<div class="off">Server nicht erreichbar</div>{/if}

{#if !reporting}
	<div class="stack">
		<button class="rb glass" onclick={() => locate()} aria-label="Mein Standort"><Icon name="locate" /></button>
		<button
			class="rb glass"
			class:on={layersOpen}
			onclick={() => ((layersOpen = !layersOpen), (aboutOpen = false))}
			aria-label="Ebenen"><Icon name="layers" /></button
		>
		<button class="rb glass zoom" onclick={() => map.zoomBy(1)} aria-label="Vergrößern"><Icon name="plus" /></button>
		<button class="rb glass zoom" onclick={() => map.zoomBy(-1)} aria-label="Verkleinern"><Icon name="minus" /></button>
	</div>
{/if}

<div class="sheet glass" bind:clientHeight={sheetHeight}>
	<div class="grab"></div>
	{#if reporting}
		<ReportSheet location={pick} onclose={() => (reporting = false)} onsent={sent} />
	{:else if selected}
		<ClusterCard cluster={selected} {mine} onclose={() => (selected = null)} onreport={() => startReport(selected!)} />
	{:else if sensor}
		<SensorCard {sensor} onclose={() => (sensor = null)} />
	{:else if layersOpen}
		<LayerSheet {layers} ontoggle={toggle} onclose={() => (layersOpen = false)} />
	{:else if aboutOpen}
		<AboutSheet onclose={() => (aboutOpen = false)} />
	{:else}
		<button class="primary" onclick={() => startReport()}><Icon name="plus" />Melden</button>
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
	.off {
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
		box-shadow: 0 -1px 0 rgba(0, 0, 0, 0.05), 0 -10px 30px rgba(0, 0, 0, 0.08);
	}
	@media (min-width: 600px) {
		.sheet {
			right: auto;
			left: 14px;
			bottom: 14px;
			width: 400px;
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
	.legend {
		display: flex;
		gap: 16px;
		justify-content: center;
		margin-top: 12px;
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
