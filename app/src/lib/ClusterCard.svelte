<script lang="ts">
	import { typeInfo, timeAgo, STATUS, type Cluster } from './api';

	let {
		cluster,
		mine = false,
		onclose
	}: { cluster: Cluster; mine?: boolean; onclose: () => void } = $props();

	const others = $derived(mine ? cluster.count - 1 : cluster.count);
	const ago = $derived(timeAgo(cluster.latest));
</script>

<div class="card">
	<button class="x" onclick={onclose} aria-label="Schließen">×</button>
	{#if mine}
		<h2>Gemeldet.</h2>
		<p class="big">
			{others === 0 ? 'Du bist hier der Erste.' : `Du und ${others} ${others === 1 ? 'andere Person' : 'andere'} in der Nähe.`}
		</p>
	{:else}
		<h2>{cluster.count} {cluster.count === 1 ? 'Meldung' : 'Meldungen'}</h2>
	{/if}
	<div class="types">
		{#each Object.entries(cluster.types) as [t, n]}
			<span class="tag" style="--c: {typeInfo(t).color}">{typeInfo(t).label} · {n}</span>
		{/each}
	</div>
	<p class="meta">Letzte Meldung {ago}</p>
	{#if cluster.status}
		<p class="status">
			<span class="badge" style="--c: {STATUS[cluster.status].color}">{STATUS[cluster.status].label}</span>
			{cluster.reason}
		</p>
	{/if}
</div>

<style>
	.card {
		z-index: 3;
		position: absolute;
		left: 12px;
		right: 12px;
		bottom: calc(12px + env(safe-area-inset-bottom));
		background: var(--bg);
		color: var(--fg);
		border-radius: 16px;
		padding: 14px 16px;
		box-shadow: 0 8px 30px #0008;
	}
	.x {
		position: absolute;
		top: 8px;
		right: 10px;
		background: none;
		border: 0;
		color: #888;
		font-size: 22px;
	}
	h2 {
		margin: 0 0 6px;
		font-size: 18px;
	}
	.big {
		font-size: 16px;
		margin: 0 0 10px;
	}
	.types {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		margin-bottom: 8px;
	}
	.tag {
		border: 1.5px solid var(--c);
		color: var(--c);
		border-radius: 999px;
		padding: 3px 10px;
		font-size: 13px;
	}
	.meta {
		color: #999;
		font-size: 13px;
		margin: 0 0 4px;
	}
	.status {
		color: #ddd;
		font-size: 14px;
		margin: 0;
		line-height: 1.4;
	}
	.badge {
		background: var(--c);
		color: #111;
		border-radius: 6px;
		padding: 1px 7px;
		font-size: 12px;
		font-weight: 700;
		margin-right: 4px;
	}
</style>
