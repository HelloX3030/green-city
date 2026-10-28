<script lang="ts">
	import Icon from './Icon.svelte';
	import { typeInfo, timeAgo, STATUS, type Cluster, type Report } from './api';

	let {
		reports,
		clusters,
		onopen,
		onwithdraw,
		onclose
	}: {
		reports: Report[];
		clusters: Cluster[];
		onopen: (r: Report) => void;
		onwithdraw: (r: Report) => void;
		onclose: () => void;
	} = $props();

	const bubble = (r: Report) => clusters.find((c) => c.report_ids.includes(r.id));
	// the second tap withdraws, the first one only asks
	let asking = $state<number | null>(null);
	let askTimer: ReturnType<typeof setTimeout>;
	function withdraw(r: Report) {
		clearTimeout(askTimer);
		if (asking === r.id) {
			asking = null;
			return onwithdraw(r);
		}
		asking = r.id;
		askTimer = setTimeout(() => (asking = null), 4000);
	}
</script>

<div class="head">
	<h2>Meine Meldungen</h2>
	<button class="x" onclick={onclose} aria-label="Schließen"><Icon name="x" size={16} /></button>
</div>
{#if reports.length === 0}
	<p class="empty">Noch nichts gemeldet.</p>
{/if}
<div class="list">
	{#each reports as r (r.id)}
		{@const c = bubble(r)}
		{@const t = typeInfo(r.types[0])}
		<div class="row">
			<button class="open" onclick={() => onopen(r)}>
				<i style="background: {t.color}"><Icon name={t.icon} size={13} /></i>
				<span class="text">
					<b>{r.types.map((x) => typeInfo(x).label).join(', ')}</b>
					<small>
						{timeAgo(r.created_at)}
						{#if c}
							· {c.count === 1 ? 'nur du' : `${c.count} hier`}
							{#if c.status}· <span style="color: {STATUS[c.status].color}">{STATUS[c.status].label}</span>{/if}
						{:else}
							· nicht mehr auf der Karte
						{/if}
					</small>
				</span>
			</button>
			<button class="undo" class:ask={asking === r.id} onclick={() => withdraw(r)}>
				{asking === r.id ? 'Wirklich?' : 'Zurückziehen'}
			</button>
		</div>
	{/each}
</div>

<style>
	.head {
		display: flex;
		align-items: center;
		margin-bottom: 2px;
	}
	h2 {
		margin: 0;
		font-size: 17px;
		font-weight: 700;
		letter-spacing: -0.01em;
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
	}
	.empty {
		margin: 10px 0 4px;
		font-size: 13.5px;
		color: var(--ink2);
	}
	.list {
		max-height: 40vh;
		overflow-y: auto;
	}
	.row {
		display: flex;
		align-items: center;
		gap: 8px;
		border-top: 1px solid var(--line);
	}
	.row:first-child {
		border-top: 0;
	}
	.open {
		flex: 1;
		min-width: 0;
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 10px 0;
		text-align: left;
	}
	.open i {
		flex: none;
		width: 28px;
		height: 28px;
		border-radius: 50%;
		display: grid;
		place-items: center;
		color: #fff;
	}
	.text {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}
	.text b {
		font-size: 14px;
		font-weight: 600;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.text small {
		font-size: 12px;
		color: var(--ink2);
	}
	.undo {
		flex: none;
		padding: 6px 10px;
		border-radius: 999px;
		background: var(--fill);
		font-size: 12px;
		font-weight: 500;
		color: var(--ink2);
	}
	.undo.ask {
		background: #a03d3d;
		color: #fff;
	}
</style>
