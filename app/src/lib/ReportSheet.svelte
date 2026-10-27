<script lang="ts">
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

<div class="sheet">
	<div class="handle"></div>
	<h2>Was stört dich hier?</h2>
	<div class="chips">
		{#each TYPES as t}
			<button
				class="chip"
				class:on={selected.includes(t.id)}
				style="--c: {t.color}"
				onclick={() => toggle(t.id)}>{t.label}</button
			>
		{/each}
	</div>
	<input class="msg" placeholder="Optional: ein Satz dazu" maxlength="500" bind:value={message} />
	<p class="hint">Ort: Karte verschieben, bis der Kreis passt.</p>
	{#if error}<p class="err">{error}</p>{/if}
	<div class="row">
		<button class="ghost" onclick={onclose}>Abbrechen</button>
		<button class="primary" disabled={!selected.length || !location || sending} onclick={send}>
			{sending ? 'Sende…' : 'Melden'}
		</button>
	</div>
</div>

<style>
	.sheet {
		z-index: 3;
		position: absolute;
		left: 0;
		right: 0;
		bottom: 0;
		background: var(--bg);
		color: var(--fg);
		border-radius: 18px 18px 0 0;
		padding: 8px 16px calc(16px + env(safe-area-inset-bottom));
		box-shadow: 0 -8px 30px #0008;
	}
	.handle {
		width: 36px;
		height: 4px;
		background: #555;
		border-radius: 2px;
		margin: 0 auto 10px;
	}
	h2 {
		font-size: 18px;
		margin: 0 0 12px;
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		margin-bottom: 12px;
	}
	.chip {
		border: 1.5px solid var(--c);
		color: var(--c);
		background: transparent;
		border-radius: 999px;
		padding: 8px 14px;
		font-size: 15px;
	}
	.chip.on {
		background: var(--c);
		color: #111;
		font-weight: 600;
	}
	.msg {
		width: 100%;
		box-sizing: border-box;
		background: #222;
		color: var(--fg);
		border: 1px solid #333;
		border-radius: 10px;
		padding: 10px 12px;
		font-size: 15px;
	}
	.hint {
		color: #999;
		font-size: 13px;
		margin: 8px 0;
	}
	.err {
		color: #f87171;
		font-size: 14px;
		margin: 4px 0;
	}
	.row {
		display: flex;
		gap: 10px;
	}
	.row button {
		flex: 1;
		padding: 12px;
		border-radius: 12px;
		font-size: 16px;
		border: 0;
	}
	.primary {
		background: var(--accent);
		color: #111;
		font-weight: 600;
	}
	.primary:disabled {
		opacity: 0.4;
	}
	.ghost {
		background: #2a2a2a;
		color: var(--fg);
	}
</style>
