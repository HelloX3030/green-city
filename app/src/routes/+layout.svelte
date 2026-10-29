<script lang="ts">
	import '../app.css';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();
</script>

<svelte:head>
	<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
</svelte:head>

{@render children()}
