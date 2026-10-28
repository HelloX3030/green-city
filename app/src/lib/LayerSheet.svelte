<script lang="ts">
	import Icon from './Icon.svelte';
	import { LAYERS, TYPES, typeInfo, type LayerId, type ReportType } from './api';
	import { DAYS, DEFAULT, MINS, isDefault, type Filter } from './filter';

	let {
		layers,
		filter,
		ontoggle,
		onfilter,
		onclose
	}: {
		layers: Set<LayerId>;
		filter: Filter;
		ontoggle: (id: LayerId) => void;
		onfilter: (f: Filter) => void;
		onclose: () => void;
	} = $props();

	const set = (part: Partial<Filter>) => onfilter({ ...filter, ...part });
	function toggleType(t: ReportType) {
		set({ types: filter.types.includes(t) ? filter.types.filter((x) => x !== t) : [...filter.types, t] });
	}
	const which = $derived(filter.types.length ? `nur ${filter.types.map((t) => typeInfo(t).label).join(', ')}` : 'alle Arten');
</script>

<div class="head">
	<h2>Ebenen</h2>
	<button class="x" onclick={onclose} aria-label="Schließen"><Icon name="x" size={16} /></button>
</div>
<!-- what the map shows of the reports; nothing set is everything -->
<h3>Meldungen <small>{which}</small></h3>
<div class="chips">
	{#each TYPES as t}
		<button
			class="type"
			class:on={filter.types.includes(t.id)}
			style="--c: {t.color}"
			aria-pressed={filter.types.includes(t.id)}
			onclick={() => toggleType(t.id)}><Icon name={t.icon} size={16} />{t.label}</button
		>
	{/each}
</div>
<div class="row">
	<span>mindestens</span>
	<span class="seg">
		{#each MINS as m}
			<button class:on={filter.min === m} aria-pressed={filter.min === m} onclick={() => set({ min: m })}>{m}</button>
		{/each}
	</span>
	<span>{filter.min === 1 ? 'Meldung' : 'Meldungen'}</span>
</div>
<div class="row">
	<span>die letzten</span>
	<span class="seg">
		{#each DAYS as d}
			<button class:on={filter.days === d} aria-pressed={filter.days === d} onclick={() => set({ days: d })}>{d}</button>
		{/each}
	</span>
	<span>Tage</span>
</div>
<button class="opt" onclick={() => set({ confirmed: !filter.confirmed })} aria-pressed={filter.confirmed}>
	<span class="text"><b>Nur Bestätigte</b><small>Stellen, die ein Sensor bestätigt</small></span>
	<span class="tog" class:on={filter.confirmed}></span>
</button>
{#if !isDefault(filter)}
	<button class="reset" onclick={() => onfilter(DEFAULT)}>Zurücksetzen</button>
{/if}
<h3>Hintergrund</h3>
{#each LAYERS as l}
	<button class="layer" onclick={() => ontoggle(l.id)} aria-pressed={layers.has(l.id)}>
		<span class="thumb">
			<img src="/thumbs/{l.id}.png" alt="" width="60" height="60" />
			<i style="background: {l.color}"><Icon name={l.icon} size={13} /></i>
		</span>
		<span class="text"><b>{l.label}</b><small>{l.hint}</small></span>
		<span class="tog" class:on={layers.has(l.id)}></span>
	</button>
{/each}

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
	.layer {
		display: flex;
		align-items: center;
		gap: 12px;
		width: 100%;
		padding: 9px 0;
		border-top: 1px solid var(--line);
		text-align: left;
	}
	.opt {
		display: flex;
		align-items: center;
		gap: 12px;
		width: 100%;
		padding: 6px 0 2px;
		text-align: left;
	}
	h3 {
		margin: 12px 0 6px;
		font-size: 13px;
		font-weight: 700;
		color: var(--ink2);
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}
	h3 small {
		font-weight: 500;
		text-transform: none;
		letter-spacing: 0;
		margin-left: 6px;
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.type {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		height: 30px;
		padding: 0 10px 0 8px;
		border-radius: 999px;
		background: var(--fill);
		color: var(--c);
		font-size: 13px;
		font-weight: 600;
	}
	.type.on {
		background: var(--c);
		color: #fff;
	}
	.row {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-top: 8px;
		font-size: 13px;
		color: var(--ink2);
	}
	.seg {
		display: inline-flex;
		background: var(--fill);
		border-radius: 999px;
		padding: 2px;
	}
	.seg button {
		min-width: 36px;
		height: 26px;
		border-radius: 999px;
		font-size: 13px;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
		color: var(--ink2);
	}
	.seg button.on {
		background: var(--accent);
		color: var(--on-accent);
	}
	.reset {
		display: block;
		margin-top: 6px;
		font-size: 13px;
		font-weight: 600;
		color: var(--accent);
	}
	.thumb {
		position: relative;
		flex: none;
		width: 60px;
		height: 60px;
	}
	.thumb img {
		display: block;
		width: 60px;
		height: 60px;
		border-radius: 12px;
		box-shadow: inset 0 0 0 1px var(--line);
	}
	.thumb i {
		position: absolute;
		right: -5px;
		bottom: -5px;
		width: 22px;
		height: 22px;
		border-radius: 50%;
		border: 2px solid #fff;
		display: grid;
		place-items: center;
		color: #fff;
	}
	.text {
		min-width: 0;
	}
	.text b {
		display: block;
		font-size: 14px;
		font-weight: 600;
	}
	.text small {
		color: var(--ink2);
		font-size: 12px;
	}
	.tog {
		margin-left: auto;
		width: 42px;
		height: 26px;
		border-radius: 13px;
		background: rgba(0, 0, 0, 0.14);
		position: relative;
		flex: none;
		transition: background 0.15s;
	}
	.tog::after {
		content: '';
		position: absolute;
		top: 2px;
		left: 2px;
		width: 22px;
		height: 22px;
		border-radius: 50%;
		background: #fff;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
		transition: left 0.15s;
	}
	.tog.on {
		background: var(--accent);
	}
	.tog.on::after {
		left: 18px;
	}
</style>
