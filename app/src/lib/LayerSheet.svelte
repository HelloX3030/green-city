<script lang="ts">
	import Icon from './Icon.svelte';
	import { LAYERS, type LayerId } from './api';

	let {
		layers,
		ontoggle,
		onclose
	}: { layers: Set<LayerId>; ontoggle: (id: LayerId) => void; onclose: () => void } = $props();
</script>

<div class="head">
	<h2>Ebenen</h2>
	<button class="x" onclick={onclose} aria-label="Schließen"><Icon name="x" size={16} /></button>
</div>
{#each LAYERS as l}
	<button class="layer" onclick={() => ontoggle(l.id)} aria-pressed={layers.has(l.id)}>
		<span class="badge" style="background: {l.color}"><Icon name={l.icon} size={19} /></span>
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
		padding: 10px 0;
		border-top: 1px solid var(--line);
		text-align: left;
	}
	.layer:first-of-type {
		border-top: 0;
	}
	.badge {
		width: 38px;
		height: 38px;
		border-radius: 11px;
		display: grid;
		place-items: center;
		color: #fff;
		flex: none;
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
