<script lang="ts">
	import {
		Map as MLMap,
		LngLat,
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
	import { RING, CITY_BBOX, clampToCity, inCity, distanceM, circle } from './city.ts';
	import {
		TYPES,
		SENSOR_KIND,
		NOISE_LEGEND,
		PM_LEGEND,
		dominantType,
		typeInfo,
		isLive,
		CLUSTER_RADIUS_M,
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
		onpick?: (c: { lat: number; lon: number } | null) => void;
		onselect?: (c: Cluster | null) => void;
		onselectsensor?: (s: Sensor) => void;
	} = $props();

	let el: HTMLDivElement;
	let map: MLMap;
	let ready = $state(false);

	const HEILBRONN: [number, number] = [9.2185, 49.1427];
	// city limit: grey wash outside the ring, the screen centre never leaves the city polygon
	// (replaces MapLibre's own constrain, so min and max zoom are clamped here too)
	function keepCentre(c: LngLat, zoom: number) {
		const [lat, lon] = clampToCity(c.lat, c.lng);
		const z = map ? Math.min(map.getMaxZoom(), Math.max(map.getMinZoom(), zoom)) : zoom;
		return { center: new LngLat(lon, lat), zoom: z };
	}
	// you can zoom out until the city fills the screen, not further
	function fitMinZoom() {
		const cam = map.cameraForBounds(CITY_BBOX);
		if (cam?.zoom) map.setMinZoom(cam.zoom - 0.1);
	}
	const PICK_ZOOM = 15; // a report needs at least this zoom, the circle is 64 px then
	let zoom = $state(13);
	let lat = $state(49.15);
	let lon = $state(9.22);
	const tooFar = $derived(picking && zoom < PICK_ZOOM - 1e-6); // zoomTo(15) can land a hair under 15
	// the bubble a report at the screen centre would join: nearest anchor within the radius, as the backend does it
	const joins = $derived.by(() => {
		if (!picking || tooFar) return null;
		let best: Cluster | null = null;
		let bestD = CLUSTER_RADIUS_M;
		for (const c of clusters) {
			const d = distanceM(lat, lon, c.lat, c.lon);
			if (d < bestD) (best = c), (bestD = d);
		}
		return best;
	});
	const hint = $derived(
		tooFar
			? 'Näher ranzoomen'
			: joins
				? joins.count === 1
					? 'Kommt zur Meldung hier dazu'
					: `Kommt zu den ${joins.count} Meldungen hier dazu`
				: 'Schieb die Karte auf die Stelle'
	);
	// the report circle is the cluster radius on the ground, so it grows with the zoom
	const metresPerPx = $derived((156543.03 * Math.cos((lat * Math.PI) / 180)) / 2 ** zoom);
	const circlePx = $derived(Math.max(24, (2 * CLUSTER_RADIUS_M) / metresPerPx));
	const far = $derived(zoom < 14); // zoomed out the bubbles shrink a bit and the ones that would touch merge
	// the groups depend on the zoom only (pixel distances do), recomputed every quarter level while far
	const zoomStep = $derived(far ? Math.round(zoom * 4) / 4 : 0);
	const bubbleSize = (weight: number) => Math.round(Math.min(64, 30 + 8 * Math.log(1 + weight)) * (far ? 0.8 : 1));
	// what is drawn: one bubble per cluster, or zoomed out one per group of bubbles that overlap on screen,
	// sitting at the heaviest one, reports and voices summed, coloured by the type with most reports in the group
	interface Bubble {
		id: number; // the cluster id, of the heaviest member for a group
		lat: number;
		lon: number;
		count: number;
		weight: number;
		mine: boolean;
		type: string;
		members: Cluster[];
	}
	function bubbles(): Bubble[] {
		let out: Bubble[] = clusters.map((c) => ({ id: c.id, lat: c.lat, lon: c.lon, count: c.count, weight: c.weight, mine: c.mine > 0, type: dominantType(c), members: [c] }));
		// heaviest first, each one joins the first bubble it overlaps; again while merging made bubbles grow
		for (let pass = 0; far && pass < 4; pass++) {
			const next: Bubble[] = [];
			for (const b of out.sort((a, b) => b.weight - a.weight)) {
				const p = map.project([b.lon, b.lat]);
				const into = next.find((n) => {
					const q = map.project([n.lon, n.lat]);
					return Math.hypot(p.x - q.x, p.y - q.y) < (bubbleSize(b.weight) + bubbleSize(n.weight)) / 2 + 6; // 6 px: the rings
				});
				if (into) {
					into.count += b.count;
					into.weight += b.weight;
					into.mine ||= b.mine;
					into.members.push(...b.members);
				} else next.push(b);
			}
			const done = next.length === out.length;
			out = next;
			if (done) break;
		}
		for (const b of out) {
			if (b.members.length === 1) continue;
			const heads: Record<string, number> = {};
			for (const c of b.members) for (const [t, n] of Object.entries(c.types)) heads[t] = (heads[t] ?? 0) + n;
			b.type = Object.entries(heads).sort((x, y) => y[1] - x[1])[0][0];
		}
		return out;
	}
	const NOISE_TILES =
		'https://datahub.uba.de/server/rest/services/VeLa/LK/MapServer/export?bbox={bbox-epsg-3857}&bboxSR=3857&imageSR=3857&size=256,256&layers=show:4210&format=png32&transparent=true&f=image';
	const EMPTY: FeatureCollection = { type: 'FeatureCollection', features: [] };
	let treesLoaded = false;
	let pmLoaded = false;
	const popup = new Popup({ closeButton: false, offset: 8, maxWidth: '260px' });
	const clusterMarkers = new globalThis.Map<number, Marker>();
	const sensorMarkers = new globalThis.Map<string, Marker>();
	// small pins over big ones, bubbles and sensors alike, so nothing hides under a big bubble; the selected one on top
	const SENSOR_PX = 28;
	const layer = (size: number, sel: boolean) => String(sel ? 100 : 100 - Math.round(size));
	let me: Marker | null = null;

	onMount(() => {
		map = new MLMap({
			container: el,
			style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
			center: HEILBRONN,
			zoom: 13,
			maxZoom: 18,
			transformConstrain: keepCentre,
			attributionControl: false
		});
		map.addControl(new AttributionControl({ compact: true }), 'top-left');
		map.scrollZoom.setWheelZoomRate(1 / 900);
		map.touchZoomRotate.disableRotation();

		if (import.meta.env.DEV) Object.assign(window, { __map: map, __inCity: inCity });
		map.on('resize', fitMinZoom);

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
			// the 100 m of every bubble: faint from zoom 15 up, the selected one always, with a line
			map.addSource('discs', { type: 'geojson', data: EMPTY });
			map.addLayer({
				id: 'discs',
				type: 'fill',
				source: 'discs',
				minzoom: 15,
				filter: ['!', ['get', 'sel']],
				paint: { 'fill-color': ['get', 'color'], 'fill-opacity': 0.08 }
			});
			map.addLayer({
				id: 'disc-sel',
				type: 'fill',
				source: 'discs',
				filter: ['get', 'sel'],
				paint: { 'fill-color': ['get', 'color'], 'fill-opacity': 0.16 }
			});
			map.addLayer({
				id: 'disc-sel-line',
				type: 'line',
				source: 'discs',
				filter: ['get', 'sel'],
				paint: { 'line-color': ['get', 'color'], 'line-width': 1.5, 'line-opacity': 0.7 }
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
			map.on('move', () => {
				zoom = map.getZoom();
				({ lat, lng: lon } = map.getCenter());
			});
			fitMinZoom();
			map.on('moveend', () => {
				if (picking) pick();
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
		const pad = { top: 0, left: padLeft, right: 0, bottom: padBottom };
		// setPadding cancels a running animation, so wait for it
		if (map.isMoving()) map.once('moveend', () => map.setPadding(pad));
		else map.setPadding(pad);
		fitMinZoom();
	});

	$effect(() => {
		if (!ready) return;
		const selId = selected !== null && 'report_ids' in selected ? selected.id : null;
		(map.getSource('discs') as GeoJSONSource).setData({
			type: 'FeatureCollection',
			features: clusters.map((c) => ({
				type: 'Feature' as const,
				properties: { color: typeInfo(dominantType(c)).color, sel: c.id === selId },
				geometry: { type: 'Polygon' as const, coordinates: [circle(c.lat, c.lon, CLUSTER_RADIUS_M)] }
			}))
		});
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
		void zoomStep;
		const seen = new Set<number>();
		for (const b of bubbles()) {
			seen.add(b.id);
			let m = clusterMarkers.get(b.id);
			if (!m) {
				const div = document.createElement('div');
				div.className = 'pin cluster';
				div.onclick = (e) => {
					e.stopPropagation();
					popup.remove();
					const cur = bubbles().find((x) => x.id === b.id);
					if (!cur) return;
					// a group opens up when zoomed in; a single bubble shows its card
					if (cur.members.length > 1) {
						const lats = cur.members.map((c) => c.lat);
						const lons = cur.members.map((c) => c.lon);
						map.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]], { padding: 80, maxZoom: 15, duration: 600 });
					} else onselect?.(cur.members[0]);
				};
				m = new Marker({ element: div }).setLngLat([b.lon, b.lat]).addTo(map);
				clusterMarkers.set(b.id, m);
			}
			m.setLngLat([b.lon, b.lat]);
			const div = m.getElement();
			// grows with the log of the voices, 30 px for one, 64 at most
			const size = bubbleSize(b.weight);
			const sel = selId !== null && b.members.some((c) => c.id === selId);
			div.style.setProperty('--c', TYPES.find((t) => t.id === b.type)?.color ?? '#8a8a8e');
			div.style.setProperty('--s', `${size}px`);
			div.style.zIndex = layer(size, sel);
			div.innerHTML = `<span>${b.count}</span>`;
			div.classList.toggle('sel', sel);
			div.classList.toggle('mine', b.mine);
			div.classList.toggle('group', b.members.length > 1);
		}
		for (const [id, m] of clusterMarkers) {
			if (!seen.has(id)) {
				m.remove();
				clusterMarkers.delete(id);
			}
		}
	});

	$effect(() => {
		const id = joins?.id; // read outside the loop, the markers map is empty on the first run
		void clusters; // and again after a refresh, the marker may be new
		for (const [cid, m] of clusterMarkers) m.getElement().classList.toggle('join', cid === id);
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
			const sel = selected !== null && 'kind' in selected && selected.id === s.id;
			div.style.color = s.team ? 'var(--accent)' : SENSOR_KIND[s.kind].color;
			div.style.zIndex = layer(SENSOR_PX, sel);
			div.classList.toggle('ours', s.team);
			div.classList.toggle('off', !isLive(s));
			div.classList.toggle('sel', sel);
		}
		for (const [id, m] of sensorMarkers) {
			if (!seen.has(id)) {
				m.remove();
				sensorMarkers.delete(id);
			}
		}
	});

	// a sensor pin on a bubble's middle hides its number, then the number moves to a badge on the lower edge
	const quarterZoom = $derived(Math.round(zoom * 4) / 4);
	$effect(() => {
		if (!ready) return;
		void quarterZoom; // pixel distances depend on the zoom only
		void clusters;
		void zoomStep; // after the bubbles were redrawn
		void selected; // the selected bubble lies over the pins, nothing covers it
		const pins = sensors.map((s) => map.project([s.lon, s.lat]));
		for (const m of clusterMarkers.values()) {
			const p = map.project(m.getLngLat());
			const covered = !m.getElement().classList.contains('sel') && pins.some((q) => Math.abs(q.x - p.x) < SENSOR_PX / 2 + 12 && Math.abs(q.y - p.y) < SENSOR_PX / 2 + 8);
			m.getElement().classList.toggle('covered', covered);
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

	function pick() {
		if (map.getZoom() < PICK_ZOOM - 1e-6) return onpick?.(null);
		const c = map.getCenter();
		onpick?.({ lat: c.lat, lon: c.lng });
	}

	$effect(() => {
		if (ready && picking) pick();
	});

	export function flyTo(lat: number, lon: number, zoom = 15) {
		map?.flyTo({ center: [lon, lat], zoom: Math.max(map.getZoom(), zoom) });
	}

	export function ensureZoom(zoom: number) {
		if (map && map.getZoom() < zoom) map.zoomTo(zoom, { duration: 500 });
	}

	export function zoomBy(d: number) {
		map?.zoomTo(map.getZoom() + d, { duration: 300 });
	}

	export function showMe(lat: number, lon: number) {
		if (!me) {
			const div = document.createElement('div');
			div.className = 'pin me';
			me = new Marker({ element: div }).setLngLat([lon, lat]).addTo(map);
		}
		me.setLngLat([lon, lat]);
	}
</script>

<div class="map" bind:this={el}></div>
{#if picking}
	<div class="dim" aria-hidden="true"></div>
	<div
		class="crosshair"
		class:far={tooFar}
		style="--bottom: {padBottom}px; --left: {padLeft}px; --d: {circlePx.toFixed(1)}px"
		aria-hidden="true"
	>
		<span class="hint">{hint}</span>
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
		z-index: 0; /* its own stacking context: bubble z-indexes stay under the sheet and the buttons */
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
		box-sizing: border-box;
		width: var(--d);
		height: var(--d);
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
	.crosshair.far {
		border-color: var(--ink2);
		background: rgba(0, 0, 0, 0.06);
	}
	.crosshair.far::after {
		background: var(--ink2);
	}
	.hint {
		position: absolute;
		left: 50%;
		top: calc(50% + min(var(--d) / 2, 90px));
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
		pointer-events: none; /* the ring is 44 px, a tap next to the pin should hit what is there */
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
	:global(.pin.cluster.covered span) {
		position: absolute;
		left: 50%;
		bottom: -10px;
		transform: translateX(-50%);
		padding: 0 6px;
		border-radius: 999px;
		background: var(--c);
		border: 2px solid #fff;
		font-size: 12px;
		line-height: 16px;
	}
	/* several bubbles in one: a second ring */
	:global(.pin.cluster.group) {
		box-shadow: 0 0 0 2px #fff, 0 0 0 3.5px var(--c), 0 2px 6px rgba(0, 0, 0, 0.22);
	}
	:global(.pin.cluster.join) {
		box-shadow: 0 0 0 3px #fff, 0 0 0 5px var(--accent), 0 4px 12px rgba(0, 0, 0, 0.25);
	}
	:global(.pin.cluster.sel) {
		box-shadow: 0 0 0 3px #fff, 0 0 0 5px var(--c), 0 4px 12px rgba(0, 0, 0, 0.25);
	}
	/* a green dot top right: one of the reports here is yours */
	:global(.pin.cluster.mine::after) {
		content: '';
		position: absolute;
		top: -3px;
		right: -3px;
		width: 10px;
		height: 10px;
		border-radius: 50%;
		background: var(--accent);
		border: 2px solid #fff;
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
		z-index: 101; /* the opened credits over the pins, which go up to 100 */
	}
	:global(.maplibregl-ctrl-attrib) {
		background: var(--glass) !important;
		border-radius: 999px;
		box-shadow: var(--shadow);
		font-size: 11px;
	}
	/* MapLibre's own button is a filled black circle, a grey "i" fits the glass buttons */
	:global(.maplibregl-ctrl-attrib-button) {
		background-color: transparent !important;
		background-image: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 20 20' fill='%236e6e73'%3E%3Cpath d='M9 7a1 1 0 1 0 2 0 1 1 0 1 0-2 0m0 3a1 1 0 1 1 2 0v3a1 1 0 1 1-2 0'/%3E%3C/svg%3E") !important;
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
