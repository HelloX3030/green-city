<script lang="ts">
	import Icon from './Icon.svelte';
	import { TYPES, postReport, type Report, type ReportType } from './api';

	let {
		location,
		onclose,
		onsent
	}: {
		location: { lat: number; lon: number } | null;
		onclose: () => void;
		onsent: (r: Report) => void;
	} = $props();

	let selected = $state<ReportType[]>([]);
	let message = $state('');
	let sending = $state(false);
	let error = $state('');

	const toggle = (id: ReportType) =>
		(selected = selected.includes(id) ? selected.filter((t) => t !== id) : [...selected, id]);

	async function send() {
		if (!location || !selected.length) return;
		sending = true;
		error = '';
		try {
			onsent(await postReport({ ...location, types: selected, message: message || undefined }));
		} catch (e) {
			error = 'Senden fehlgeschlagen. Nochmal?';
		} finally {
			sending = false;
		}
	}
</script>

<div class="head">
	<div>
		<h2>Was stört dich hier?</h2>
		<p>Mehrere möglich</p>
	</div>
	<button class="x" onclick={onclose} aria-label="Abbrechen"><Icon name="x" size={16} /></button>
</div>
<div class="tiles">
	{#each TYPES as t}
		<button
			class="tile"
			class:on={selected.includes(t.id)}
			style="--c: {t.color}"
			onclick={() => toggle(t.id)}
		>
			<Icon name={t.icon} size={22} />
			{t.label}
		</button>
	{/each}
</div>
<input class="msg" placeholder="Ein Satz dazu, optional, öffentlich" maxlength="500" bind:value={message} />
{#if error}<p class="err">{error}</p>{/if}
<div class="row">
	<button class="ghost" onclick={onclose}>Abbrechen</button>
	<button class="primary" disabled={!selected.length || !location || sending} onclick={send}>
		<Icon name="check" size={18} />
		{sending ? 'Sende…' : 'Melden'}
	</button>
</div>

<style>
	.head {
		display: flex;
		align-items: center;
		gap: 12px;
		margin-bottom: 4px;
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
	}
	.tiles {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 8px;
		margin-top: 10px;
	}
	.tile {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 6px;
		padding: 12px 6px 10px;
		border-radius: 14px;
		background: var(--fill);
		font-size: 12px;
		font-weight: 500;
		border: 1.5px solid transparent;
	}
	.tile :global(svg) {
		color: var(--c);
	}
	.tile.on {
		background: #fff;
		border-color: var(--c);
		color: var(--c);
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
	}
	.msg {
		width: 100%;
		box-sizing: border-box;
		margin-top: 10px;
		height: 42px;
		border-radius: 12px;
		background: var(--fill);
		border: 0;
		padding: 0 12px;
		font-size: 14px;
	}
	.msg::placeholder {
		color: var(--ink2);
	}
	.err {
		color: #a03d3d;
		font-size: 13px;
		margin: 8px 0 0;
	}
	.row {
		display: grid;
		grid-template-columns: 1fr 2fr;
		gap: 8px;
		margin-top: 12px;
	}
	.row button {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 8px;
		height: 50px;
		border-radius: 14px;
		font-weight: 600;
		font-size: 16px;
	}
	.primary {
		background: var(--accent);
		color: var(--on-accent);
	}
	.primary:disabled {
		opacity: 0.4;
		cursor: default;
	}
	.ghost {
		background: var(--fill);
		font-weight: 500;
		font-size: 14px;
	}
</style>
