<script lang="ts">
	import Icon from './Icon.svelte';
	import { typeInfo, timeAgo, STATUS, dominantType, clusterReports, type Cluster, type Report, type ReportType } from './api';

	let {
		cluster,
		days = 14,
		sent = false,
		onclose,
		onreport
	}: { cluster: Cluster; days?: number; sent?: boolean; onclose: () => void; onreport: () => void } = $props();

	const mine = $derived(cluster.mine > 0); // one of the reports here is from this device
	const others = $derived(cluster.people - 1); // other people, not other reports
	const persons = (n: number) => `${n} ${n === 1 ? 'Person' : 'Personen'}`;
	const you = $derived(
		others === 0
			? cluster.mine === 1
				? 'Du bist hier der Erste'
				: 'Alle von dir'
			: `Du und ${others} ${others === 1 ? 'andere Person' : 'andere Personen'} in der Nähe`
	);
	const main = $derived(typeInfo(dominantType(cluster)));
	const reports_ = (n: number) => `${n} ${n === 1 ? 'Meldung' : 'Meldungen'}`;
	const sub = $derived(
		[
			mine ? you : `von ${persons(cluster.people)}`,
			main.label,
			cluster.recent < cluster.count ? `${cluster.recent === 0 ? 'keine' : cluster.recent} davon diese Woche` : null,
			`letzte ${timeAgo(cluster.latest)}` // wraps as one piece
		]
			.filter(Boolean)
			.join(' · ')
	);

	// the single reports, for the texts; a tap on a type keeps only that type
	let reports = $state<Report[]>([]);
	let filter = $state<ReportType | null>(null);
	$effect(() => {
		const id = cluster.id;
		void cluster.count; // again when the poll brings a new report
		clusterReports(id, days).then((r) => {
			if (id === cluster?.id) reports = r; // the card may be closed by now
		});
	});
	$effect(() => {
		void cluster.id;
		filter = null;
	});
	// with a type filter on the map the bubble carries only those types, the texts follow
	const voices = $derived(reports.filter((r) => r.message && (filter ? r.types.includes(filter) : r.types.some((t) => t in cluster.types))));
	// mine from today: the button says Nochmal melden, the sent card counts them
	const myToday = $derived(reports.filter((r) => r.mine && r.created_at.slice(0, 10) === new Date().toISOString().slice(0, 10)).length);
	const today = $derived(myToday > 0);
	// the types I named here get a ring on their chip
	const myTypes = $derived(new Set<string>(reports.filter((r) => r.mine).flatMap((r) => r.types)));
	function pick(t: string) {
		filter = filter === t ? null : (t as ReportType);
	}
</script>

<div class="head">
	<div class="badge" style="background: {sent ? 'var(--accent)' : main.color}">
		<Icon name={sent ? 'check' : main.icon} size={20} />
	</div>
	<div>
		{#if sent}
			<h2>Gemeldet</h2>
			<p>{[you, myToday > 1 ? `deine ${myToday}. Meldung hier heute` : null].filter(Boolean).join(' · ')}.</p>
		{:else}
			<h2>{reports_(cluster.count)}</h2>
			<p>{sub}</p>
		{/if}
	</div>
	<button class="x" onclick={onclose} aria-label="Schließen"><Icon name="x" size={16} /></button>
</div>
{#if cluster.status}
	<span class="status" style="background: {STATUS[cluster.status].color}">{STATUS[cluster.status].label}</span>
	<p class="reason">{cluster.reason}</p>
{/if}
{#if Object.keys(cluster.types).length > 1 || myTypes.size}
<div class="types">
	{#each Object.entries(cluster.types) as [t, n]}
		<button
			class="type"
			class:on={filter === t}
			class:me={myTypes.has(t)}
			style="--c: {typeInfo(t).color}"
			aria-label="{typeInfo(t).label}, {reports_(n)}{myTypes.has(t) ? ', von dir' : ''}"
			aria-pressed={filter === t}
			onclick={() => pick(t)}
		>
			<Icon name={typeInfo(t).icon} size={16} />{n}
		</button>
	{/each}
	{#if filter}
		<span class="picked">{typeInfo(filter).label} · {reports_(cluster.types[filter])}</span>
	{/if}
</div>
{/if}
{#if voices.length}
	<ul class="voices">
		{#each voices as r (r.id)}
			<li class:me={r.mine}>
				<i style="background: {typeInfo(filter ?? r.types[0]).color}"></i>
				<span class="when">{timeAgo(r.created_at)}</span>
				{#if r.mine}<span class="tag">Du</span>{/if}
				<span class="text">{r.message}</span>
			</li>
		{/each}
	</ul>
{/if}
<button class="ghost" onclick={onreport}>{today ? 'Nochmal melden' : 'Hier auch melden'}</button>

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
	.tag {
		flex: none;
		font-size: 11px;
		font-weight: 700;
		line-height: 16px;
		padding: 0 6px;
		border-radius: 8px;
		background: var(--accent);
		color: #fff;
		margin-top: 1px;
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
	.status {
		display: inline-block;
		padding: 5px 10px;
		border-radius: 999px;
		font-weight: 600;
		font-size: 12px;
		color: #fff;
	}
	.reason {
		margin: 10px 0 0;
		font-size: 13.5px;
	}
	.types {
		display: flex;
		gap: 6px;
		margin-top: 12px;
		flex-wrap: wrap;
		align-items: center;
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
		font-variant-numeric: tabular-nums;
	}
	.type.me {
		box-shadow: inset 0 0 0 2px var(--c); /* the ones you named */
	}
	.type.on {
		background: var(--c);
		color: #fff;
	}
	.picked {
		font-size: 12px;
		color: var(--ink2);
		margin-left: 2px;
	}
	.voices {
		list-style: none;
		margin: 10px 0 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.voices li {
		display: flex;
		align-items: baseline;
		gap: 8px;
		font-size: 13.5px;
		line-height: 1.35;
	}
	.voices i {
		flex: none;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		align-self: flex-start;
		margin-top: 5px; /* on the first line, also when the text wraps */
	}
	.when {
		flex: none;
		font-size: 12px;
		color: var(--ink2);
		min-width: 70px; /* "gerade eben" and "vor 12 Tagen" fit, the texts start in one line */
	}
	.text {
		overflow-wrap: anywhere;
	}
	.ghost {
		display: block;
		width: 100%;
		margin-top: 10px;
		height: 40px;
		color: var(--ink2);
		font-weight: 500;
	}
</style>
