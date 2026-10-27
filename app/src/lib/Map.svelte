<script lang="ts">
	import {
		Map as MLMap,
		NavigationControl,
		GeolocateControl,
		setWorkerUrl,
		type GeoJSONSource,
		type MapMouseEvent
	} from 'maplibre-gl';
	import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
	import type { FeatureCollection } from 'geojson';
	import 'maplibre-gl/dist/maplibre-gl.css';

	// Vite bundles MapLibre so its default worker path is wrong; point it at a bundled worker.
	setWorkerUrl(workerUrl);
	import { onMount } from 'svelte';
	import { TYPES, dominantType, type Cluster } from './api';

	let {
		clusters = [],
		picking = false,
		onpick,
		onselect
	}: {
		clusters?: Cluster[];
		picking?: boolean;
		onpick?: (c: { lat: number; lon: number }) => void;
		onselect?: (c: Cluster | null) => void;
	} = $props();

	let el: HTMLDivElement;
	let map: MLMap;
	let ready = $state(false);

	const HEILBRONN: [number, number] = [9.2185, 49.1427];

	onMount(() => {
		map = new MLMap({
			container: el,
			style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
			center: HEILBRONN,
			zoom: 13,
			attributionControl: { compact: true }
		});
		map.addControl(new NavigationControl({ showCompass: false }), 'top-right');
		map.addControl(
			new GeolocateControl({ positionOptions: { enableHighAccuracy: true } }),
			'top-right'
		);

		map.on('load', () => {
			map.addSource('clusters', { type: 'geojson', data: toGeoJSON(clusters) });
			map.addLayer({
				id: 'cluster-glow',
				type: 'circle',
				source: 'clusters',
				paint: {
					'circle-color': ['get', 'color'],
					'circle-opacity': 0.25,
					'circle-radius': ['+', 18, ['*', 6, ['sqrt', ['get', 'count']]]],
					'circle-blur': 0.6
				}
			});
			map.addLayer({
				id: 'cluster-dot',
				type: 'circle',
				source: 'clusters',
				paint: {
					'circle-color': ['get', 'color'],
					'circle-opacity': 0.85,
					'circle-radius': ['+', 8, ['*', 3, ['sqrt', ['get', 'count']]]],
					'circle-stroke-color': '#fff',
					'circle-stroke-width': 1.5
				}
			});
			map.addLayer({
				id: 'cluster-count',
				type: 'symbol',
				source: 'clusters',
				layout: {
					'text-field': ['to-string', ['get', 'count']],
					'text-size': 12,
					'text-font': ['Open Sans Bold'],
					'text-allow-overlap': true
				},
				paint: { 'text-color': '#111' }
			});
			map.on('click', 'cluster-dot', (e: MapMouseEvent & { features?: any[] }) => {
				const id = e.features?.[0]?.properties?.id;
				onselect?.(clusters.find((c) => c.id === id) ?? null);
			});
			map.on('click', (e: MapMouseEvent) => {
				if (!map.queryRenderedFeatures(e.point, { layers: ['cluster-dot'] }).length) onselect?.(null);
			});
			map.on('mouseenter', 'cluster-dot', () => (map.getCanvas().style.cursor = 'pointer'));
			map.on('mouseleave', 'cluster-dot', () => (map.getCanvas().style.cursor = ''));
			map.on('moveend', () => {
				if (picking) {
					const c = map.getCenter();
					onpick?.({ lat: c.lat, lon: c.lng });
				}
			});
			ready = true;
		});
		return () => map.remove();
	});

	$effect(() => {
		if (!ready) return;
		(map.getSource('clusters') as GeoJSONSource).setData(toGeoJSON(clusters));
	});

	$effect(() => {
		if (ready && picking) {
			const c = map.getCenter();
			onpick?.({ lat: c.lat, lon: c.lng });
		}
	});

	function toGeoJSON(cs: Cluster[]): FeatureCollection {
		return {
			type: 'FeatureCollection',
			features: cs.map((c) => ({
				type: 'Feature',
				geometry: { type: 'Point', coordinates: [c.lon, c.lat] },
				properties: {
					id: c.id,
					count: c.count,
					color: TYPES.find((t) => t.id === dominantType(c))?.color
				}
			}))
		};
	}

	export function flyTo(lat: number, lon: number) {
		map?.flyTo({ center: [lon, lat], zoom: Math.max(map.getZoom(), 15) });
	}
</script>

<div class="map" bind:this={el}></div>
{#if picking}
	<div class="crosshair" aria-hidden="true"></div>
{/if}

<style>
	.map {
		position: absolute;
		inset: 0;
	}
	.crosshair {
		position: absolute;
		left: 50%;
		top: 50%;
		width: 22px;
		height: 22px;
		margin: -11px 0 0 -11px;
		border: 3px solid #fff;
		border-radius: 50%;
		box-shadow: 0 0 0 2px #0008;
		pointer-events: none;
	}
	.crosshair::after {
		content: '';
		position: absolute;
		left: 50%;
		top: 50%;
		width: 4px;
		height: 4px;
		margin: -2px 0 0 -2px;
		background: #fff;
		border-radius: 50%;
	}
</style>
