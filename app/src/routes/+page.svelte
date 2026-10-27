<script lang="ts">
	import { onMount } from 'svelte';
	import Map from '#lib/Map.svelte';
	import ReportSheet from '#lib/ReportSheet.svelte';
	import ClusterCard from '#lib/ClusterCard.svelte';
	import SensorCard from '#lib/SensorCard.svelte';
	import { getClusters, getSensors, type Cluster, type Report, type Sensor } from '#lib/api.ts';

	let clusters = $state<Cluster[]>([]);
	let sensors = $state<Sensor[]>([]);
	let selected = $state<Cluster | null>(null);
	let sensor = $state<Sensor | null>(null);
	let mine = $state(false);
	let reporting = $state(false);
	let pick = $state<{ lat: number; lon: number } | null>(null);
	let offline = $state(false);
	let map: Map;

	async function refresh() {
		try {
			clusters = await getClusters();
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

	onMount(() => {
		refresh();
		refreshSensors();
		const t = setInterval(refresh, 5000);
		const u = setInterval(refreshSensors, 30000);
		return () => {
			clearInterval(t);
			clearInterval(u);
		};
	});

	function startReport() {
		selected = null;
		sensor = null;
		reporting = true;
		navigator.geolocation?.getCurrentPosition(
			(p) => map.flyTo(p.coords.latitude, p.coords.longitude),
			() => {},
			{ enableHighAccuracy: true, timeout: 5000 }
		);
	}

	async function sent(r: Report) {
		reporting = false;
		await refresh();
		selected = clusters.find((c) => c.report_ids.includes(r.id)) ?? null;
		mine = true;
	}
</script>

<svelte:head><title>Heilbronn meldet</title></svelte:head>

<Map
	bind:this={map}
	{clusters}
	{sensors}
	picking={reporting}
	onpick={(p) => (pick = p)}
	onselect={(c) => {
		selected = c;
		sensor = null;
		mine = false;
	}}
	onselectsensor={(s) => {
		sensor = s;
		selected = null;
	}}
/>

<header>
	<span class="logo">Heilbronn meldet</span>
	{#if offline}<span class="off">Backend nicht erreichbar</span>{/if}
</header>

{#if reporting}
	<ReportSheet location={pick} onclose={() => (reporting = false)} onsent={sent} />
{:else if selected}
	<ClusterCard cluster={selected} {mine} onclose={() => (selected = null)} />
{:else if sensor}
	<SensorCard {sensor} onclose={() => (sensor = null)} />
{:else}
	<button class="fab" onclick={startReport}>Melden</button>
{/if}

<style>
	header {
		z-index: 3;
		position: absolute;
		top: 10px;
		left: 12px;
		display: flex;
		gap: 8px;
		align-items: center;
		pointer-events: none;
	}
	.logo {
		background: var(--bg);
		color: var(--fg);
		padding: 6px 12px;
		border-radius: 999px;
		font-weight: 600;
		font-size: 14px;
	}
	.off {
		background: #7f1d1d;
		color: #fff;
		padding: 6px 10px;
		border-radius: 999px;
		font-size: 12px;
	}
	.fab {
		z-index: 3;
		position: absolute;
		left: 50%;
		bottom: calc(24px + env(safe-area-inset-bottom));
		transform: translateX(-50%);
		background: var(--accent);
		color: #111;
		border: 0;
		border-radius: 999px;
		padding: 16px 36px;
		font-size: 18px;
		font-weight: 700;
		box-shadow: 0 6px 24px #0008;
	}
</style>
