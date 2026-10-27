<script lang="ts">
	import {
		Map as MLMap,
		NavigationControl,
		GeolocateControl,
		Popup,
		setWorkerUrl,
		type GeoJSONSource,
		type MapMouseEvent
	} from 'maplibre-gl';
	import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
	import type { FeatureCollection, LineString } from 'geojson';
	import 'maplibre-gl/dist/maplibre-gl.css';

	// Vite bundles MapLibre so its default worker path is wrong; point it at a bundled worker.
	setWorkerUrl(workerUrl);
	import { onMount } from 'svelte';
	import {
		TYPES,
		STATUS,
		SENSOR_COLOR,
		NOISE_LEGEND,
		dominantType,
		isLive,
		pmColor,
		type Cluster,
		type LayerId,
		type Ride,
		type Sensor
	} from './api';

	let {
		clusters = [],
		sensors = [],
		bikes = null,
		layers = new Set<LayerId>(),
		picking = false,
		onpick,
		onselect,
		onselectsensor
	}: {
		clusters?: Cluster[];
		sensors?: Sensor[];
		bikes?: FeatureCollection<LineString, Ride> | null;
		layers?: Set<LayerId>;
		picking?: boolean;
		onpick?: (c: { lat: number; lon: number }) => void;
		onselect?: (c: Cluster | null) => void;
		onselectsensor?: (s: Sensor) => void;
	} = $props();

	let el: HTMLDivElement;
	let map: MLMap;
	let ready = $state(false);

	const HEILBRONN: [number, number] = [9.2185, 49.1427];
	const NOISE_TILES =
		'https://datahub.uba.de/server/rest/services/VeLa/LK/MapServer/export?bbox={bbox-epsg-3857}&bboxSR=3857&imageSR=3857&size=256,256&layers=show:4210&format=png32&transparent=true&f=image';
	const EMPTY: FeatureCollection = { type: 'FeatureCollection', features: [] };
	let treesLoaded = false;
	const popup = new Popup({ closeButton: false, offset: 8, maxWidth: '260px' });

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

		if (import.meta.env.DEV) (window as any).__map = map;

		map.on('load', () => {
			// context layers, all hidden until toggled
			map.addSource('noise', { type: 'raster', tiles: [NOISE_TILES], tileSize: 256, maxzoom: 17 });
			map.addLayer({
				id: 'noise',
				type: 'raster',
				source: 'noise',
				layout: { visibility: 'none' },
				paint: { 'raster-opacity': 0.55 }
			});
			map.addSource('trees', { type: 'geojson', data: EMPTY });
			map.addLayer({
				id: 'trees',
				type: 'circle',
				source: 'trees',
				layout: { visibility: 'none' },
				paint: {
					'circle-color': '#22c55e',
					'circle-opacity': 0.5,
					'circle-radius': [
						'interpolate',
						['exponential', 2],
						['zoom'],
						12,
						0.8,
						19,
						['*', 1.6, ['max', 2, ['get', 'dm']]]
					]
				}
			});
			map.addSource('bikes', { type: 'geojson', data: EMPTY });
			map.addLayer({
				id: 'bikes',
				type: 'line',
				source: 'bikes',
				layout: { visibility: 'none', 'line-cap': 'round', 'line-join': 'round' },
				paint: { 'line-color': ['get', 'color'], 'line-width': 3, 'line-opacity': 0.8 }
			});
			map.addSource('sensors', { type: 'geojson', data: sensorsGeoJSON(sensors) });
			map.addLayer({
				id: 'sensor-dot',
				type: 'circle',
				source: 'sensors',
				paint: {
					'circle-color': ['get', 'color'],
					'circle-opacity': ['case', ['get', 'live'], 0.9, 0.35],
					'circle-radius': ['case', ['get', 'team'], 7, 5],
					'circle-stroke-color': '#111',
					'circle-stroke-width': 1.5
				}
			});
			map.addSource('clusters', { type: 'geojson', data: toGeoJSON(clusters) });
			map.addLayer({
				id: 'cluster-glow',
				type: 'circle',
				source: 'clusters',
				paint: {
					'circle-color': ['get', 'color'],
					'circle-opacity': 0.25,
					'circle-radius': ['+', 18, ['*', 6, ['sqrt', ['get', 'weight']]]],
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
					'circle-radius': ['+', 8, ['*', 3, ['sqrt', ['get', 'weight']]]],
					'circle-stroke-color': ['get', 'stroke'],
					'circle-stroke-width': 2.5
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
			map.on('click', 'sensor-dot', (e: MapMouseEvent & { features?: any[] }) => {
				if (map.queryRenderedFeatures(e.point, { layers: ['cluster-dot'] }).length) return;
				const id = e.features?.[0]?.properties?.id;
				const s = sensors.find((s) => s.id === id);
				if (s) onselectsensor?.(s);
			});
			map.on('click', (e: MapMouseEvent) => {
				popup.remove();
				const hit = map.queryRenderedFeatures(e.point, { layers: ['cluster-dot', 'sensor-dot'] });
				if (hit.length) return;
				onselect?.(null);
				const ride = map.queryRenderedFeatures(e.point, { layers: ['bikes'] })[0]?.properties as Ride;
				if (ride) {
					const d = new Date(ride.start);
					const when = d.toLocaleString('de-DE', { weekday: 'short', hour: '2-digit', minute: '2-digit' });
					popup
						.setLngLat(e.lngLat)
						.setHTML(
							`<b>Messrad ${ride.box}</b><br>${when} · ${fmt(ride.km)} km<br>PM2,5 Ø ${fmt(ride.pm25)} µg/m³, max ${fmt(ride.pm25_max)}`
						)
						.addTo(map);
					return;
				}
				const tree = map.queryRenderedFeatures(e.point, { layers: ['trees'] })[0]?.properties;
				if (tree) {
					popup
						.setLngLat(e.lngLat)
						.setHTML(`<b>${tree.name || 'Baum'}</b><br>Krone ${fmt(tree.dm)} m`)
						.addTo(map);
				}
			});
			for (const l of ['cluster-dot', 'sensor-dot', 'bikes']) {
				map.on('mouseenter', l, () => (map.getCanvas().style.cursor = 'pointer'));
				map.on('mouseleave', l, () => (map.getCanvas().style.cursor = ''));
			}
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
		if (!ready) return;
		(map.getSource('sensors') as GeoJSONSource).setData(sensorsGeoJSON(sensors));
	});

	$effect(() => {
		if (!ready || !bikes) return;
		(map.getSource('bikes') as GeoJSONSource).setData({
			...bikes,
			features: bikes.features.map((f) => ({
				...f,
				properties: { ...f.properties, color: pmColor(f.properties.pm25) }
			}))
		});
	});

	$effect(() => {
		if (!ready) return;
		for (const id of ['noise', 'trees', 'bikes'] as LayerId[]) {
			map.setLayoutProperty(id, 'visibility', layers.has(id) ? 'visible' : 'none');
		}
		if (layers.has('trees') && !treesLoaded) {
			treesLoaded = true;
			fetch('/trees.json')
				.then((r) => r.json())
				.then((rows: [number, number, number, string][]) =>
					(map.getSource('trees') as GeoJSONSource).setData({
						type: 'FeatureCollection',
						features: rows.map(([lon, lat, dm, name]) => ({
							type: 'Feature',
							geometry: { type: 'Point', coordinates: [lon, lat] },
							properties: { dm, name }
						}))
					})
				)
				.catch(() => (treesLoaded = false));
		}
		if (!layers.size) popup.remove();
	});

	const fmt = (v: number) => v.toLocaleString('de-DE', { maximumFractionDigits: 1 });

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
					weight: c.weight,
					color: TYPES.find((t) => t.id === dominantType(c))?.color,
					stroke: c.status ? STATUS[c.status].color : '#fff'
				}
			}))
		};
	}

	function sensorsGeoJSON(ss: Sensor[]): FeatureCollection {
		return {
			type: 'FeatureCollection',
			features: ss.map((s) => ({
				type: 'Feature',
				geometry: { type: 'Point', coordinates: [s.lon, s.lat] },
				properties: { id: s.id, color: SENSOR_COLOR[s.kind], live: isLive(s), team: s.team }
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
{#if layers.has('noise')}
	<div class="legend">
		{#each NOISE_LEGEND as [db, color]}
			<span><i style="background: {color}"></i>{db}</span>
		{/each}
		<span class="unit">dB(A) Lden</span>
	</div>
{/if}

<style>
	.legend {
		position: absolute;
		left: 12px;
		bottom: calc(96px + env(safe-area-inset-bottom));
		display: flex;
		gap: 6px;
		align-items: center;
		background: var(--bg);
		color: var(--fg);
		border-radius: 999px;
		padding: 4px 10px;
		font-size: 11px;
		pointer-events: none;
	}
	.legend i {
		display: inline-block;
		width: 10px;
		height: 10px;
		border-radius: 2px;
		margin-right: 3px;
		vertical-align: -1px;
	}
	.legend .unit {
		color: #999;
	}
	:global(.maplibregl-popup-content) {
		background: var(--bg);
		color: var(--fg);
		border-radius: 10px;
		padding: 8px 12px;
		font-size: 13px;
		line-height: 1.4;
	}
	:global(.maplibregl-popup-tip) {
		border-top-color: var(--bg) !important;
		border-bottom-color: var(--bg) !important;
	}
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
