<script lang="ts">
	import Icon from './Icon.svelte';
	import { onDestroy } from 'svelte';
	import { typeInfo, timeAgo, STATUS, setName, linkCode, claim, getMe, type Cluster, type Me, type Report } from './api';

	let {
		reports,
		clusters,
		me,
		onopen,
		onwithdraw,
		onchanged,
		onsay,
		onclose
	}: {
		reports: Report[];
		clusters: Cluster[];
		me: Me | null;
		onopen: (r: Report) => void;
		onwithdraw: (r: Report) => void;
		onchanged: () => void; // name set or devices linked: the page refetches me, mine, clusters
		onsay: (msg: string) => void;
		onclose: () => void;
	} = $props();

	// the account in v00: a name if you want one, and a code to make another phone this user
	let mode = $state<'list' | 'name' | 'link'>('list');
	let name = $state('');
	let myCode = $state('');
	let theirs = $state('');
	function openName() {
		name = me?.name ?? '';
		mode = 'name';
	}
	async function saveName() {
		try {
			await setName(name);
		} catch {
			return onsay('Speichern fehlgeschlagen');
		}
		mode = 'list';
		onchanged();
	}
	// while the code is on screen, watch for the other device claiming it
	let watch: ReturnType<typeof setInterval> | undefined;
	async function openLink() {
		mode = 'link';
		myCode = theirs = '';
		try {
			myCode = (await linkCode()).code;
		} catch {
			return onsay('Server nicht erreichbar');
		}
		const devices = me?.devices ?? 1;
		watch = setInterval(async () => {
			try {
				if ((await getMe()).devices <= devices) return;
			} catch {
				return;
			}
			back();
			onsay('Geräte verknüpft');
			onchanged();
		}, 2000);
	}
	function back() {
		clearInterval(watch);
		mode = 'list';
	}
	onDestroy(() => clearInterval(watch));
	async function link() {
		try {
			await claim(theirs.trim());
		} catch {
			return onsay('Code unbekannt oder abgelaufen');
		}
		back();
		onsay('Geräte verknüpft');
		onchanged();
	}

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
	<h2>{mode === 'name' ? 'Dein Name' : mode === 'link' ? 'Anderes Gerät verknüpfen' : 'Meine Meldungen'}</h2>
	<button class="x" onclick={mode === 'list' ? onclose : back} aria-label={mode === 'list' ? 'Schließen' : 'Zurück'}><Icon name="x" size={16} /></button>
</div>
{#if mode === 'name'}
	<p class="hint">Freiwillig, steht nirgends öffentlich.</p>
	<input bind:value={name} maxlength="40" placeholder="Name" autocomplete="off" />
	<button class="primary" onclick={saveName}>Speichern</button>
{:else if mode === 'link'}
	<p class="hint">Auf dem anderen Gerät: Meine Meldungen → Anderes Gerät verknüpfen → diesen Code eingeben. Gilt 10 Minuten.</p>
	<div class="code">{myCode || '······'}</div>
	<p class="hint">Oder hier den Code des anderen Geräts eingeben, dann gehören dessen Meldungen zu diesem.</p>
	<div class="claim">
		<input bind:value={theirs} maxlength="6" placeholder="Code" autocomplete="off" autocapitalize="characters" />
		<button class="primary" onclick={link} disabled={theirs.trim().length !== 6}>Verknüpfen</button>
	</div>
{:else}
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
						<span>{timeAgo(r.created_at)}</span>
						{#if c}
							· <span>{c.count === 1 ? 'nur du' : `${c.count} hier`}</span>
							{#if c.status}· <span style="color: {STATUS[c.status].color}">{STATUS[c.status].label}</span>{/if}
						{:else}
							· <span>nicht mehr auf der Karte</span>
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
<div class="account">
	<button onclick={openName}>{me?.name || 'Name angeben'}</button>
	<span>·</span>
	<button onclick={openLink}>Anderes Gerät verknüpfen{me && me.devices > 1 ? ` (${me.devices})` : ''}</button>
</div>
{/if}

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
	/* each piece of the line wraps as a whole, never "Sensor / fehlt" */
	.text small span {
		white-space: nowrap;
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
	.account {
		display: flex;
		justify-content: center;
		gap: 8px;
		margin-top: 10px;
		font-size: 13px;
		color: var(--ink2);
	}
	.account button {
		color: var(--ink2);
		font-weight: 500;
	}
	.hint {
		margin: 8px 0 10px;
		font-size: 13px;
		color: var(--ink2);
	}
	input {
		width: 100%;
		height: 44px;
		padding: 0 12px;
		border-radius: 12px;
		border: 1px solid var(--line);
		background: var(--fill);
	}
	.primary {
		display: block;
		width: 100%;
		height: 44px;
		margin-top: 10px;
		border-radius: 12px;
		background: var(--accent);
		color: var(--on-accent);
		font-weight: 600;
	}
	.primary:disabled {
		opacity: 0.45;
	}
	.code {
		text-align: center;
		font-size: 34px;
		font-weight: 700;
		letter-spacing: 0.25em;
		padding: 6px 0 10px;
	}
	.claim {
		display: flex;
		gap: 8px;
	}
	.claim input {
		text-transform: uppercase;
		letter-spacing: 0.15em;
	}
	.claim .primary {
		width: auto;
		margin: 0;
		padding: 0 16px;
		flex: none;
	}
</style>
