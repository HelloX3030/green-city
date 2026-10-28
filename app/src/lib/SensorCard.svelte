<script lang="ts">
	import Icon from './Icon.svelte';
	import { SENSOR_KIND, isLive, timeAgo, type Sensor } from './api';

	let { sensor, onclose }: { sensor: Sensor; onclose: () => void } = $props();

	const fmt = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(1)).replace('.', ',');
	const kind = $derived(SENSOR_KIND[sensor.kind]);
</script>

<div class="head">
	<div class="badge" style="background: {sensor.team ? 'var(--accent)' : kind.color}">
		<Icon name={kind.icon} size={20} />
	</div>
	<div>
		<h2>{sensor.name}</h2>
		<p>
			{sensor.team ? 'Unser Lärmsensor' : sensor.source === 'uba' ? 'Amtliche Messstation' : 'openSenseMap'}
			· {isLive(sensor) ? 'live' : 'offline'} · {timeAgo(sensor.last)}
		</p>
	</div>
	<button class="x" onclick={onclose} aria-label="Schließen"><Icon name="x" size={16} /></button>
</div>
{#if sensor.values.length}
	<dl>
		{#each sensor.values as v}
			<div><dt>{v.label}</dt><dd>{fmt(v.value)} <small>{v.unit}</small></dd></div>
		{/each}
	</dl>
{:else}
	<p class="empty">Sendet noch keine Daten.</p>
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
	dl {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
		gap: 10px;
		margin: 0;
	}
	dl > div {
		background: var(--fill);
		border-radius: 12px;
		padding: 8px 10px;
	}
	dt {
		color: var(--ink2);
		font-size: 12px;
	}
	dd {
		margin: 0;
		font-size: 18px;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}
	dd small {
		font-size: 12px;
		font-weight: 500;
		color: var(--ink2);
	}
	.empty {
		margin: 0;
		color: var(--ink2);
	}
</style>
