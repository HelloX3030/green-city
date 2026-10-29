<script lang="ts">
	// the time graph of one sensor: a line per phenomenon, 24 h and 7 Tage from the hourly series,
	// Alles from the daily one. A finger or the mouse on it reads the value under it, else the latest.
	import { getSensorHistory, SENSOR_KIND, type Sensor, type Series } from './api';

	// key and tabs bound so the card's value tiles can switch the chart too
	let { sensor, key = $bindable(''), tabs = $bindable([]) }: { sensor: Sensor; key?: string; tabs?: string[] } = $props();

	const LABELS: Record<string, string> = { temp: 'Temperatur', pm25: 'PM2,5', noise: 'Lärm' };
	const UNITS: Record<string, string> = { temp: '°C', pm25: 'µg/m³', noise: 'dB' };
	const RANGES = [
		['24h', '24 h'],
		['7d', '7 Tage'],
		['all', 'Alles']
	] as const;
	type Range = (typeof RANGES)[number][0];
	const WD = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'];
	const H = 150; // svg height
	const PAD = { t: 8, r: 46, b: 18 }; // the tick labels sit right, the dates below

	let history = $state<Record<string, Series> | null>(null);
	let range = $state<Range>('7d');
	let w = $state(0);
	let hover = $state<number | null>(null);

	// the phenomena in the order of the live values, then what only the history has
	const keys = $derived.by(() => {
		if (!history) return [];
		const live = sensor.values.map((v) => v.key).filter((k) => k in history!);
		return [...live, ...Object.keys(history).filter((k) => !live.includes(k))];
	});
	$effect(() => {
		tabs = keys;
	});
	const label = (k: string) => sensor.values.find((v) => v.key === k)?.label ?? LABELS[k] ?? k;
	const unit = $derived(sensor.values.find((v) => v.key === key)?.unit ?? UNITS[key] ?? '');
	const color = $derived(sensor.team ? 'var(--accent)' : SENSOR_KIND[sensor.kind].color);

	$effect(() => {
		const id = sensor.id;
		history = null;
		hover = null;
		getSensorHistory(id).then((h) => {
			if (id !== sensor.id) return; // another sensor by now
			history = h;
			const ks = keys;
			if (!ks.includes(key)) key = ks[0] ?? '';
		});
	});

	const points = $derived.by(() => {
		const s = history?.[key];
		if (!s) return [];
		const since = range === '24h' ? Date.now() - 24 * 3600e3 : 0;
		return (range === 'all' ? s.daily : s.hourly).map(([t, v]) => ({ t: Date.parse(t), v })).filter((p) => p.t >= since);
	});
	const any = $derived(keys.some((k) => history![k].daily.length > 0 || history![k].hourly.length > 0));

	const fmt = (v: number) => (Math.abs(v) >= 100 || Number.isInteger(v) ? Math.round(v).toString() : v.toFixed(1)).replace('.', ',');
	const day = (t: number) => {
		const d = new Date(t);
		return `${WD[d.getDay()]} ${d.getDate()}.${d.getMonth() + 1}.`;
	};
	const when = (t: number) => (range === 'all' ? day(t) : `${day(t)}, ${String(new Date(t).getHours()).padStart(2, '0')}:00`);
	// hours when the data spans less than two days (a sensor that just went live), else days
	const axis = (t: number, span: number) => {
		const d = new Date(t);
		if (span < 2 * 86400e3) return `${String(d.getHours()).padStart(2, '0')}:00`;
		if (range === '7d') return `${WD[d.getDay()]} ${d.getDate()}.`;
		return `${d.getDate()}.${d.getMonth() + 1}.`;
	};

	const geo = $derived.by(() => {
		if (points.length < 2 || !w) return null;
		const vs = points.map((p) => p.v);
		let lo = Math.min(...vs);
		let hi = Math.max(...vs);
		if (hi === lo) (hi += 1), (lo -= 1);
		const pad = (hi - lo) * 0.08;
		(lo -= pad), (hi += pad);
		// fine dust and noise are never below zero, so the pad must not draw a negative tick
		if (key !== 'temp' && Math.min(...vs) >= 0) lo = Math.max(lo, 0);
		const t0 = points[0].t;
		const t1 = points[points.length - 1].t;
		const x = (t: number) => ((t - t0) / (t1 - t0)) * (w - PAD.r);
		const y = (v: number) => PAD.t + (1 - (v - lo) / (hi - lo)) * (H - PAD.t - PAD.b);
		const xy = points.map((p) => [x(p.t), y(p.v)]);
		// a gap in the data breaks the line, no stroke across hours or days with nothing
		const step = (range === 'all' ? 24 : 1) * 3600e3;
		const runs: number[][][] = [];
		points.forEach((p, i) => {
			if (!i || p.t - points[i - 1].t > 2.5 * step) runs.push([]);
			runs[runs.length - 1].push(xy[i]);
		});
		const path = (run: number[][]) => run.map(([a, b], i) => `${i ? 'L' : 'M'}${a.toFixed(1)} ${b.toFixed(1)}`).join('');
		const line = runs.map(path).join('');
		const base = H - PAD.b;
		const area = runs.map((r) => `${path(r)}L${r[r.length - 1][0].toFixed(1)} ${base}L${r[0][0].toFixed(1)} ${base}Z`).join('');
		const ticks = [hi, (hi + lo) / 2, lo].map((v) => ({ v, y: y(v) }));
		const labels = [0, 1, 2, 3].map((j) => {
			const t = t0 + ((t1 - t0) * j) / 3;
			return { x: x(t), text: axis(t, t1 - t0), anchor: j === 0 ? 'start' : j === 3 ? 'end' : 'middle' };
		});
		return { xy, line, area, ticks, labels };
	});

	const at = $derived(points.length ? (hover ?? points.length - 1) : null);

	function pick(e: PointerEvent) {
		if (!geo) return;
		const px = e.clientX - (e.currentTarget as Element).getBoundingClientRect().left;
		let best = 0;
		for (let i = 1; i < geo.xy.length; i++) if (Math.abs(geo.xy[i][0] - px) < Math.abs(geo.xy[best][0] - px)) best = i;
		hover = best;
	}
</script>

<div class="history" bind:clientWidth={w}>
	{#if history && !any}
		<p class="none">Noch keine Verlaufsdaten</p>
	{:else if history}
		{#if keys.length > 1}
			<div class="seg tabs">
				{#each keys as k}
					<button class:on={k === key} onclick={() => ((key = k), (hover = null))}>{label(k)}</button>
				{/each}
			</div>
		{/if}
		<div class="row">
			<div class="read">
				{#if at !== null}
					<b>{fmt(points[at].v)} <small>{unit}</small></b>
					<span>{when(points[at].t)}</span>
				{:else}
					<span>Zu wenig Daten für diesen Zeitraum</span>
				{/if}
			</div>
			<div class="seg">
				{#each RANGES as [id, text]}
					<button class:on={id === range} onclick={() => ((range = id), (hover = null))}>{text}</button>
				{/each}
			</div>
		</div>
		<svg
			width={w}
			height={H}
			style="--c: {color}"
			role="img"
			aria-label="Verlauf {label(key)}"
			onpointerdown={pick}
			onpointermove={pick}
			onpointerleave={() => (hover = null)}
		>
			{#if geo}
				{#each geo.ticks as t}
					<line x1="0" x2={w - PAD.r + 4} y1={t.y} y2={t.y} class="grid" />
					<text x={w} y={t.y + 4} text-anchor="end">{fmt(t.v)}</text>
				{/each}
				{#each geo.labels as l}
					<text x={l.x} y={H - 4} text-anchor={l.anchor}>{l.text}</text>
				{/each}
				<path d={geo.area} class="area" />
				<path d={geo.line} class="line" />
				{#if at !== null}
					{#if hover !== null}
						<line x1={geo.xy[at][0]} x2={geo.xy[at][0]} y1={PAD.t} y2={H - PAD.b} class="cursor" />
					{/if}
					<circle cx={geo.xy[at][0]} cy={geo.xy[at][1]} r="4" class="dot" />
				{/if}
			{/if}
		</svg>
	{:else}
		<div style="height: {H + 48}px"></div>
	{/if}
</div>

<style>
	.history {
		margin-top: 14px;
	}
	.none {
		margin: 0;
		font-size: 13px;
		color: var(--ink2);
	}
	.row {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 8px;
		margin: 8px 0 2px;
	}
	.read {
		display: flex;
		flex-direction: column;
		min-height: 36px;
	}
	.read b {
		font-size: 20px;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
		letter-spacing: -0.01em;
	}
	.read small {
		font-size: 12px;
		font-weight: 500;
		color: var(--ink2);
	}
	.read span {
		font-size: 12px;
		color: var(--ink2);
	}
	.seg {
		display: inline-flex;
		flex: none;
		background: var(--fill);
		border-radius: 999px;
		padding: 2px;
	}
	.seg button {
		height: 26px;
		padding: 0 9px;
		border-radius: 999px;
		font-size: 12px;
		font-weight: 600;
		color: var(--ink2);
		white-space: nowrap;
	}
	.seg button.on {
		background: #fff;
		color: var(--ink);
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
	}
	svg {
		display: block;
		touch-action: none;
		cursor: crosshair;
		user-select: none;
	}
	svg text {
		font-size: 11px;
		fill: var(--ink2);
	}
	.grid {
		stroke: var(--line);
		stroke-dasharray: 2 3;
	}
	.area {
		fill: var(--c);
		opacity: 0.12;
	}
	.line {
		fill: none;
		stroke: var(--c);
		stroke-width: 2;
		stroke-linejoin: round;
	}
	.cursor {
		stroke: var(--ink2);
		stroke-width: 1;
	}
	.dot {
		fill: var(--c);
		stroke: #fff;
		stroke-width: 2;
	}
</style>
