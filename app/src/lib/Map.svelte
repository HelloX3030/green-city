<script lang="ts">
	import {
		Map as MLMap,
		Marker,
		Popup,
		AttributionControl,
		setWorkerUrl,
		type GeoJSONSource,
		type ExpressionSpecification,
		type MapMouseEvent
	} from 'maplibre-gl';
	import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
	import type { FeatureCollection, LineString, Point, Polygon } from 'geojson';
	import 'maplibre-gl/dist/maplibre-gl.css';

	// Vite bundles MapLibre so its default worker path is wrong; point it at a bundled worker.
	setWorkerUrl(workerUrl);
	import { onMount } from 'svelte';
	import { iconSvg } from './icons';
	import boundary from './boundary.json';
	import {
		TYPES,
		SENSOR_KIND,
		NOISE_LEGEND,
		PM_LEGEND,
		dominantType,
		typeInfo,
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
		selected = null,
		bikes = null,
		layers = new Set<LayerId>(),
		picking = false,
		sheetHeight = 0,
		onpick,
		onselect,
		onselectsensor
	}: {
		clusters?: Cluster[];
		sensors?: Sensor[];
		selected?: Cluster | Sensor | null;
		bikes?: FeatureCollection<LineString, Ride> | null;
		layers?: Set<LayerId>;
		picking?: boolean;
		sheetHeight?: number;
		onpick?: (c: { lat: number; lon: number }) => void;
		onselect?: (c: Cluster | null) => void;
		onselectsensor?: (s: Sensor) => void;
	} = $props();

	let el: HTMLDivElement;
	let map: MLMap;
	let ready = $state(false);

	const HEILBRONN: [number, number] = [9.2185, 49.1427];
	// city limit: grey wash outside the ring, panning stops a little beyond the city bbox
	const RING = boundary.ring as [number, number][];
	const PAD = 0.005; // ~400 m
	const BOUNDS: [number, number, number, number] = [
		Math.min(...RING.map((p) => p[0])) - PAD,
		Math.min(...RING.map((p) => p[1])) - PAD,
		Math.max(...RING.map((p) => p[0])) + PAD,
		Math.max(...RING.map((p) => p[1])) + PAD
	];
	const NOISE_TILES =
		'https://datahub.uba.de/server/rest/services/VeLa/LK/MapServer/export?bbox={bbox-epsg-3857}&bboxSR=3857&imageSR=3857&size=256,256&layers=show:4210&format=png32&transparent=true&f=image';
	const EMPTY: FeatureCollection = { type: 'FeatureCollection', features: [] };
	let treesLoaded = false;
	let pmLoaded = false;
	const popup = new Popup({ closeButton: false, offset: 8, maxWidth: '260px' });
	const clusterMarkers = new globalThis.Map<number, Marker>();
	const sensorMarkers = new globalThis.Map<string, Marker>();
	let me: Marker | null = null;

	onMount(() => {
		map = new MLMap({
			container: el,
			style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
			center: HEILBRONN,
			zoom: 13,
			minZoom: 11,
			maxZoom: 18,
			maxBounds: BOUNDS,
			attributionControl: false
		});
		map.addControl(new AttributionControl({ compact: true }), 'top-left');
		map.scrollZoom.setWheelZoomRate(1 / 900);
		map.touchZoomRotate.disableRotation();

		if (import.meta.env.DEV) (window as any).__map = map;

		map.on('load', () => {
			el.querySelector('.maplibregl-ctrl-attrib')?.classList.remove('maplibregl-compact-show');
			map.addSource('mask', {
				type: 'geojson',
				data: {
					type: 'Feature',
					properties: {},
					geometry: {
						type: 'Polygon',
						coordinates: [
							[[-180, -85], [180, -85], [180, 85], [-180, 85], [-180, -85]],
							RING
						]
					}
				}
			});
			map.addLayer({
				id: 'mask',
				type: 'fill',
				source: 'mask',
				paint: { 'fill-color': '#6e6e73', 'fill-opacity': 0.3 }
			});
			map.addLayer({
				id: 'mask-line',
				type: 'line',
				source: 'mask',
				paint: { 'line-color': '#6e6e73', 'line-width': 1.5, 'line-opacity': 0.7 }
			});
			// context layers, all hidden until toggled
			map.addSource('noise', { type: 'raster', tiles: [NOISE_TILES], tileSize: 256, maxzoom: 17 });
			map.addLayer({
				id: 'noise',
				type: 'raster',
				source: 'noise',
				layout: { visibility: 'none' },
				paint: { 'raster-opacity': 0.45 }
			});
			map.addSource('trees', { type: 'geojson', data: EMPTY });
			map.addLayer({
				id: 'trees',
				type: 'circle',
				source: 'trees',
				layout: { visibility: 'none' },
				paint: {
					'circle-color': '#7aa874',
					'circle-opacity': 0.55,
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
			// all-time PM2.5 grid: dots when zoomed out, the real 25 m cells when zoomed in
			const PM_COLOR: ExpressionSpecification = ['step', ['get', 'pm'], '#5a8f5f', 10, '#c7a24a', 15, '#c4664f', 25, '#a03d3d'];
			map.addSource('pm', { type: 'geojson', data: EMPTY });
			map.addLayer({
				id: 'pm',
				type: 'circle',
				source: 'pm',
				maxzoom: 14.5,
				layout: { visibility: 'none' },
				paint: {
					'circle-color': PM_COLOR,
					'circle-opacity': 0.7,
					'circle-radius': ['interpolate', ['exponential', 2], ['zoom'], 11, 1, 14.5, 4]
				}
			});
			map.addSource('pm-cells', { type: 'geojson', data: EMPTY });
			map.addLayer({
				id: 'pm-cells',
				type: 'fill',
				source: 'pm-cells',
				minzoom: 14.5,
				layout: { visibility: 'none' },
				paint: { 'fill-color': PM_COLOR, 'fill-opacity': 0.6, 'fill-antialias': false }
			});
			map.addSource('bikes', { type: 'geojson', data: EMPTY });
			map.addLayer({
				id: 'bikes',
				type: 'line',
				source: 'bikes',
				layout: { visibility: 'none', 'line-cap': 'round', 'line-join': 'round' },
				paint: { 'line-color': ['get', 'color'], 'line-width': 4, 'line-opacity': 0.85 }
			});
			// the single reports inside a bubble, only when zoomed in close
			map.addSource('members', { type: 'geojson', data: EMPTY });
			map.addLayer({
				id: 'members',
				type: 'circle',
				source: 'members',
				minzoom: 15.5,
				paint: {
					'circle-color': ['get', 'color'],
					'circle-radius': 5,
					'circle-opacity': 0.9,
					'circle-stroke-color': '#fff',
					'circle-stroke-width': 1.5
				}
			});
			map.on('click', (e: MapMouseEvent) => {
				popup.remove();
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
				const cell = map.queryRenderedFeatures(e.point, { layers: ['pm', 'pm-cells'] })[0]?.properties;
				if (cell) {
					popup
						.setLngLat(e.lngLat)
						.setHTML(`<b>PM2,5 Ø ${fmt(cell.pm)} µg/m³</b><br>${cell.n} Messungen hier`)
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
			for (const id of ['bikes', 'pm', 'pm-cells']) {
				map.on('mouseenter', id, () => (map.getCanvas().style.cursor = 'pointer'));
				map.on('mouseleave', id, () => (map.getCanvas().style.cursor = ''));
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

	// the sheet covers the bottom (phone) or the left (wide screens), the map's centre moves away from it
	let wide = $state(false);
	$effect(() => {
		const mq = window.matchMedia('(min-width: 600px)');
		const set = () => (wide = mq.matches);
		set();
		mq.addEventListener('change', set);
		return () => mq.removeEventListener('change', set);
	});
	const padBottom = $derived(wide ? 0 : sheetHeight);
	const padLeft = $derived(wide ? 414 : 0);
	$effect(() => {
		if (!ready) return;
		map.setPadding({ top: 0, left: padLeft, right: 0, bottom: padBottom });
	});

	$effect(() => {
		if (!ready) return;
		(map.getSource('members') as GeoJSONSource).setData({
			type: 'FeatureCollection',
			features: clusters.flatMap((c) =>
				c.points.map(([lat, lon, t]) => ({
					type: 'Feature' as const,
					properties: { color: typeInfo(t).color },
					geometry: { type: 'Point' as const, coordinates: [lon, lat] }
				}))
			)
		});
		const seen = new Set<number>();
		for (const c of clusters) {
			seen.add(c.id);
			let m = clusterMarkers.get(c.id);
			if (!m) {
				const div = document.createElement('div');
				div.className = 'pin cluster';
				div.onclick = (e) => {
					e.stopPropagation();
					popup.remove();
					onselect?.(clusters.find((x) => x.id === c.id) ?? null);
				};
				m = new Marker({ element: div }).setLngLat([c.lon, c.lat]).addTo(map);
				clusterMarkers.set(c.id, m);
			}
			m.setLngLat([c.lon, c.lat]);
			const div = m.getElement();
			const size = Math.round(30 + 6 * Math.sqrt(c.weight));
			div.style.setProperty('--c', TYPES.find((t) => t.id === dominantType(c))?.color ?? '#8a8a8e');
			div.style.setProperty('--s', `${size}px`);
			div.textContent = String(c.count);
			div.classList.toggle('sel', selected !== null && 'report_ids' in selected && selected.id === c.id);
		}
		for (const [id, m] of clusterMarkers) {
			if (!seen.has(id)) {
				m.remove();
				clusterMarkers.delete(id);
			}
		}
	});

	$effect(() => {
		if (!ready) return;
		const seen = new Set<string>();
		for (const s of sensors) {
			seen.add(s.id);
			let m = sensorMarkers.get(s.id);
			if (!m) {
				const div = document.createElement('div');
				div.className = 'pin sensor';
				div.innerHTML = iconSvg(SENSOR_KIND[s.kind].icon);
				div.onclick = (e) => {
					e.stopPropagation();
					popup.remove();
					const cur = sensors.find((x) => x.id === s.id);
					if (cur) onselectsensor?.(cur);
				};
				m = new Marker({ element: div }).setLngLat([s.lon, s.lat]).addTo(map);
				sensorMarkers.set(s.id, m);
			}
			const div = m.getElement();
			div.style.color = s.team ? 'var(--accent)' : SENSOR_KIND[s.kind].color;
			div.classList.toggle('ours', s.team);
			div.classList.toggle('off', !isLive(s));
			div.classList.toggle('sel', selected !== null && 'kind' in selected && selected.id === s.id);
		}
		for (const [id, m] of sensorMarkers) {
			if (!seen.has(id)) {
				m.remove();
				sensorMarkers.delete(id);
			}
		}
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
		for (const id of ['noise', 'trees', 'bikes', 'pm'] as LayerId[]) {
			map.setLayoutProperty(id, 'visibility', layers.has(id) ? 'visible' : 'none');
		}
		map.setLayoutProperty('pm-cells', 'visibility', layers.has('pm') ? 'visible' : 'none');
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
		if (layers.has('pm') && !pmLoaded) {
			pmLoaded = true;
			fetch('/pm.json')
				.then((r) => r.json())
				.then(({ step: [dx, dy], cells }: { step: [number, number]; cells: [number, number, number, number][] }) => {
					const feature = (geometry: Point | Polygon, [, , pm, n]: number[]) => ({ type: 'Feature' as const, geometry, properties: { pm, n } });
					(map.getSource('pm') as GeoJSONSource).setData({
						type: 'FeatureCollection',
						features: cells.map((c) => feature({ type: 'Point', coordinates: [c[0], c[1]] }, c))
					});
					(map.getSource('pm-cells') as GeoJSONSource).setData({
						type: 'FeatureCollection',
						features: cells.map(([x, y, pm, n]) =>
							feature(
								{
									type: 'Polygon',
									coordinates: [[[x - dx / 2, y - dy / 2], [x + dx / 2, y - dy / 2], [x + dx / 2, y + dy / 2], [x - dx / 2, y + dy / 2], [x - dx / 2, y - dy / 2]]]
								},
								[x, y, pm, n]
							)
						)
					});
				})
				.catch(() => (pmLoaded = false));
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

	export function flyTo(lat: number, lon: number, zoom = 15) {
		map?.flyTo({ center: [lon, lat], zoom: Math.max(map.getZoom(), zoom) });
	}

	export function zoomBy(d: number) {
		map?.zoomTo(map.getZoom() + d, { duration: 300 });
	}

	export function showMe(lat: number, lon: number) {
		if (!me) {
			const div = document.createElement('div');
			div.className = 'pin me';
			me = new Marker({ element: div }).addTo(map);
		}
		me.setLngLat([lon, lat]);
	}
</script>

<div class="map" bind:this={el}></div>
{#if picking}
	<div class="dim" aria-hidden="true"></div>
	<div class="crosshair" style="--bottom: {padBottom}px; --left: {padLeft}px" aria-hidden="true">
		<span class="hint">Karte schieben, bis der Kreis passt</span>
	</div>
{/if}
<div class="legends" style="--bottom: {padBottom}px; --left: {padLeft}px">
	{#if layers.has('bikes') || layers.has('pm')}
		<div class="legend glass">
			{#each PM_LEGEND as [v, color]}
				<span><i style="background: {color}"></i>{v}</span>
			{/each}
			<span class="unit">µg/m³ PM2,5</span>
		</div>
	{/if}
	{#if layers.has('noise')}
		<div class="legend glass">
			{#each NOISE_LEGEND as [db, color]}
				<span><i style="background: {color}"></i>{db}</span>
			{/each}
			<span class="unit">dB(A) Lden</span>
		</div>
	{/if}
</div>

<style>
	.map {
		position: absolute;
		inset: 0;
	}
	.dim {
		position: absolute;
		inset: 0;
		background: rgba(0, 0, 0, 0.1);
		pointer-events: none;
	}
	.crosshair {
		position: absolute;
		left: calc((100% + var(--left)) / 2);
		top: calc((100% - var(--bottom)) / 2);
		width: 84px;
		height: 84px;
		transform: translate(-50%, -50%);
		border-radius: 50%;
		border: 2px dashed var(--accent);
		background: rgba(58, 125, 92, 0.1);
		pointer-events: none;
	}
	.crosshair::after {
		content: '';
		position: absolute;
		left: 50%;
		top: 50%;
		width: 10px;
		height: 10px;
		transform: translate(-50%, -50%);
		border-radius: 50%;
		background: var(--accent);
		box-shadow: 0 0 0 3px #fff;
	}
	.hint {
		position: absolute;
		left: 50%;
		top: 100%;
		transform: translate(-50%, 12px);
		white-space: nowrap;
		font-size: 12px;
		background: var(--glass-strong);
		padding: 5px 10px;
		border-radius: 999px;
		box-shadow: var(--shadow);
	}
	.legends {
		position: absolute;
		left: calc(var(--left) + 14px);
		bottom: calc(var(--bottom) + 12px);
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 6px;
		pointer-events: none;
	}
	.legend {
		display: flex;
		gap: 6px;
		align-items: center;
		border-radius: 999px;
		padding: 5px 10px;
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
		color: var(--ink2);
	}

	/* markers live outside the component tree */
	:global(.pin) {
		display: grid;
		place-items: center;
		cursor: pointer;
	}
	:global(.pin .i) {
		width: 15px;
		height: 15px;
	}
	:global(.pin.sensor) {
		width: 28px;
		height: 28px;
		border-radius: 50%;
		background: #fff;
		border: 1.5px solid rgba(0, 0, 0, 0.14);
		box-shadow: 0 2px 6px rgba(0, 0, 0, 0.18);
	}
	:global(.pin.sensor.off) {
		opacity: 0.55;
	}
	:global(.pin.sensor.ours) {
		border: 2px solid var(--accent);
		opacity: 1;
	}
	:global(.pin.sensor.ours::after) {
		content: '';
		position: absolute;
		inset: -8px;
		border-radius: 50%;
		border: 2px solid var(--accent);
		animation: pulse 2.2s ease-out infinite;
	}
	:global(.pin.sensor.sel) {
		box-shadow: 0 0 0 3px #fff, 0 0 0 5px currentColor;
	}
	@keyframes pulse {
		0% {
			transform: scale(0.7);
			opacity: 0.6;
		}
		100% {
			transform: scale(1.5);
			opacity: 0;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		:global(.pin.sensor.ours::after) {
			animation: none;
			opacity: 0.4;
		}
	}
	:global(.pin.cluster) {
		width: var(--s);
		height: var(--s);
		border-radius: 50%;
		background: var(--c);
		color: #fff;
		font-weight: 700;
		font-size: 14px;
		border: 2px solid #fff;
		box-shadow: 0 2px 6px rgba(0, 0, 0, 0.22);
	}
	:global(.pin.cluster::before) {
		content: '';
		position: absolute;
		inset: -11px;
		border-radius: 50%;
		background: var(--c);
		opacity: 0.22;
		z-index: -1;
	}
	:global(.pin.cluster.sel) {
		box-shadow: 0 0 0 3px #fff, 0 0 0 5px var(--c), 0 4px 12px rgba(0, 0, 0, 0.25);
	}
	:global(.pin.me) {
		width: 16px;
		height: 16px;
		border-radius: 50%;
		background: #3b82f6;
		border: 3px solid #fff;
		box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.15), 0 2px 6px rgba(0, 0, 0, 0.3);
		cursor: default;
	}
	:global(.maplibregl-ctrl-top-left) {
		top: 56px;
	}
	:global(.maplibregl-ctrl-attrib) {
		background: var(--glass) !important;
		border-radius: 999px;
		font-size: 11px;
	}
	:global(.maplibregl-popup-content) {
		background: var(--glass-strong);
		color: var(--ink);
		border-radius: 12px;
		padding: 8px 12px;
		font-size: 13px;
		line-height: 1.4;
		box-shadow: var(--shadow);
	}
	:global(.maplibregl-popup-tip) {
		border-top-color: var(--glass-strong) !important;
		border-bottom-color: var(--glass-strong) !important;
	}
</style>
