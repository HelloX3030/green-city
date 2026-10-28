<script lang="ts">
	import Icon from './Icon.svelte';
	import { typeInfo, timeAgo, STATUS, dominantType, type Cluster } from './api';

	let {
		cluster,
		sent = false,
		onclose,
		onreport
	}: { cluster: Cluster; sent?: boolean; onclose: () => void; onreport: () => void } = $props();

	const mine = $derived(cluster.mine > 0); // one of the reports here is from this device
	const others = $derived(cluster.count - cluster.mine);
	const you = $derived(
		others === 0
			? cluster.mine === 1
				? 'Du bist hier der Erste'
				: 'Alle von dir'
			: `Du und ${others} ${others === 1 ? 'andere Person' : 'andere'} in der Nähe`
	);
	const main = $derived(typeInfo(dominantType(cluster)));
</script>

<div class="head">
	<div class="badge" style="background: {sent ? 'var(--accent)' : main.color}">
		<Icon name={sent ? 'check' : main.icon} size={20} />
	</div>
	<div>
		{#if sent}
			<h2>Gemeldet</h2>
			<p>{you}.</p>
		{:else}
			<h2>{cluster.count} {cluster.count === 1 ? 'Meldung' : 'Meldungen'}</h2>
			<p>
				{#if mine}{you}{:else}{main.label}{/if}
				{#if cluster.recent < cluster.count}· {cluster.recent === 0 ? 'keine' : cluster.recent} davon diese Woche{/if}
				· letzte {timeAgo(cluster.latest)}
			</p>
		{/if}
	</div>
	<button class="x" onclick={onclose} aria-label="Schließen"><Icon name="x" size={16} /></button>
</div>
{#if cluster.status}
	<span class="status" style="background: {STATUS[cluster.status].color}">{STATUS[cluster.status].label}</span>
	<p class="reason">{cluster.reason}</p>
{/if}
<div class="types">
	{#each Object.entries(cluster.types) as [t, n]}
		<span class="chip"><i style="background: {typeInfo(t).color}"></i>{typeInfo(t).label} {n}</span>
	{/each}
</div>
{#if !sent}
	<button class="ghost" onclick={onreport}>Hier auch melden</button>
{/if}

<style>
	.head {
		display: flex;
		align-items: center;
		gap: 12px;
		margin-bottom: 12px;
	}
	.badge {
		width: 40px;
		height: 40px;
		border-radius: 12px;
		display: grid;
		place-items: center;
		color: #fff;
		flex: none;
	}
	h2 {
		margin: 0;
		font-size: 17px;
		font-weight: 700;
		letter-spacing: -0.01em;
	}
	.head p {
		margin: 1px 0 0;
		font-size: 12px;
		color: var(--ink2);
	}
	.x {
		margin-left: auto;
		width: 30px;
		height: 30px;
		border-radius: 50%;
		background: var(--fill);
		display: grid;
		place-items: center;
		color: var(--ink2);
		flex: none;
	}
	.status {
		display: inline-block;
		padding: 5px 10px;
		border-radius: 999px;
		font-weight: 600;
		font-size: 12px;
		color: #fff;
	}
	.reason {
		margin: 10px 0 0;
		font-size: 13.5px;
	}
	.types {
		display: flex;
		gap: 8px;
		margin-top: 12px;
		flex-wrap: wrap;
	}
	.chip {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 5px 10px;
		border-radius: 999px;
		background: var(--fill);
		font-size: 12px;
		font-weight: 500;
	}
	.chip i {
		width: 8px;
		height: 8px;
		border-radius: 50%;
	}
	.ghost {
		display: block;
		width: 100%;
		margin-top: 10px;
		height: 40px;
		color: var(--ink2);
		font-weight: 500;
	}
</style>
