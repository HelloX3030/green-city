<script lang="ts">
	import Icon from './Icon.svelte';
	import { STATUS } from './api';

	let { onclose }: { onclose: () => void } = $props();

	const steps = [
		['plus', 'Melden', 'Zu laut, zu heiß, schlechte Luft, kein Schatten. Ein Tipp auf die Karte reicht.'],
		['map', 'Bündeln', 'Meldungen im Umkreis von 100 m werden zu einer Stelle, die Zahl sind die Meldungen. Pro Person und Tag wächst eine Stelle nur einmal, alte verblassen nach ein paar Tagen. Weit rausgezoomt fassen sich nahe Stellen zusammen.'],
		['radio', 'Prüfen', 'Jede Stelle wird mit den Sensoren der Stadt verglichen. Wo Daten fehlen, stellen wir unseren NoiseNode auf.']
	] as const;
</script>

<div class="head">
	<h2>Sag's Heilbronn</h2>
	<button class="x" onclick={onclose} aria-label="Schließen"><Icon name="x" size={16} /></button>
</div>
<p class="lead">Wo stört Lärm, Hitze oder schlechte Luft? Du meldest, die Sensoren bestätigen.</p>
<ol>
	{#each steps as [icon, title, text]}
		<li>
			<i><Icon name={icon} size={16} /></i>
			<span><b>{title}</b>{text}</span>
		</li>
	{/each}
</ol>
<div class="status">
	{#each Object.values(STATUS) as s}
		<span><i style="background: {s.color}"></i>{s.label}</span>
	{/each}
</div>
<p class="foot">Green City Hackathon Heilbronn 2026. Daten: openSenseMap, Umweltbundesamt, Stadt Heilbronn.</p>

<style>
	.head {
		display: flex;
		align-items: center;
		margin-bottom: 4px;
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
	.lead {
		margin: 0 0 12px;
		color: var(--ink2);
		font-size: 13px;
	}
	ol {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 10px;
	}
	li {
		display: flex;
		gap: 12px;
		align-items: flex-start;
	}
	li i {
		flex: none;
		width: 30px;
		height: 30px;
		border-radius: 10px;
		background: var(--accent);
		color: var(--on-accent);
		display: grid;
		place-items: center;
	}
	li b {
		display: block;
		font-size: 14px;
		font-weight: 600;
	}
	li span {
		font-size: 13px;
		color: var(--ink2);
	}
	.status {
		display: flex;
		gap: 14px;
		margin-top: 14px;
		font-size: 12px;
		color: var(--ink2);
	}
	.status span {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.status i {
		width: 10px;
		height: 10px;
		border-radius: 50%;
	}
	.foot {
		margin: 12px 0 0;
		font-size: 11px;
		color: var(--ink2);
	}
</style>
