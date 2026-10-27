<script lang="ts">
	import { onMount } from 'svelte';
	import Map from '#lib/Map.svelte';
	import ReportSheet from '#lib/ReportSheet.svelte';
	import ClusterCard from '#lib/ClusterCard.svelte';
	import { getClusters, type Cluster, type Report } from '#lib/api.ts';

	let clusters = $state<Cluster[]>([]);
	let selected = $state<Cluster | null>(null);
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

	onMount(() => {
		refresh();
		const t = setInterval(refresh, 5000);
		return () => clearInterval(t);
	});

	function startReport() {
		selected = null;
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
	picking={reporting}
	onpick={(p) => (pick = p)}
	onselect={(c) => {
		selected = c;
		mine = false;
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
