<script lang="ts">
	import { SENSOR_COLOR, isLive, timeAgo, type Sensor } from './api';

	let { sensor, onclose }: { sensor: Sensor; onclose: () => void } = $props();

	const fmt = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(1)).replace('.', ',');
</script>

<div class="card">
	<button class="x" onclick={onclose} aria-label="Schließen">×</button>
	<h2><span class="dot" style="--c: {SENSOR_COLOR[sensor.kind]}"></span>{sensor.name}</h2>
	<p class="meta">
		{sensor.team ? 'Unser Lärmsensor' : sensor.source === 'uba' ? 'Amtliche Messstation' : 'openSenseMap'}
		· {isLive(sensor) ? 'live' : 'offline'} · {timeAgo(sensor.last)}
	</p>
	{#if sensor.values.length}
		<dl>
			{#each sensor.values as v}
				<div><dt>{v.label}</dt><dd>{fmt(v.value)} {v.unit}</dd></div>
			{/each}
		</dl>
	{:else}
		<p class="empty">Sendet noch keine Daten.</p>
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
		margin: 0 0 4px;
		font-size: 17px;
		padding-right: 24px;
	}
	.dot {
		display: inline-block;
		width: 10px;
		height: 10px;
		border-radius: 50%;
		background: var(--c);
		margin-right: 8px;
	}
	.meta {
		color: #999;
		font-size: 13px;
		margin: 0 0 10px;
	}
	dl {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
		gap: 8px;
		margin: 0;
	}
	dt {
		color: #999;
		font-size: 12px;
	}
	dd {
		margin: 0;
		font-size: 18px;
		font-weight: 600;
	}
	.empty {
		margin: 0;
		color: #bbb;
	}
</style>
