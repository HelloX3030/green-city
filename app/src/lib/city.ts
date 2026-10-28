import boundary from './boundary.json';

// city limit from opendata.heilbronn.de, see `make boundary`
export const RING = boundary.ring as [number, number][];
export const CITY_BBOX: [number, number, number, number] = [
	Math.min(...RING.map((p) => p[0])),
	Math.min(...RING.map((p) => p[1])),
	Math.max(...RING.map((p) => p[0])),
	Math.max(...RING.map((p) => p[1]))
];

// flat coordinates for distances: x = lon * cos(lat), y = lat
const K = Math.cos((((CITY_BBOX[1] + CITY_BBOX[3]) / 2) * Math.PI) / 180);
const FLAT = RING.map(([lon, lat]) => [lon * K, lat]);

export function inCity(lat: number, lon: number) {
	const x = lon * K;
	let inside = false;
	for (let i = 0, j = FLAT.length - 1; i < FLAT.length; j = i++) {
		const [xi, yi] = FLAT[i];
		const [xj, yj] = FLAT[j];
		if (yi > lat !== yj > lat && x < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside;
	}
	return inside;
}

const CX = FLAT.reduce((a, p) => a + p[0], 0) / FLAT.length;
const CY = FLAT.reduce((a, p) => a + p[1], 0) / FLAT.length;
const EPS = 1e-5; // ~1 m

// the point itself when inside the city, else the nearest point on the city limit, a metre inward
export function clampToCity(lat: number, lon: number): [number, number] {
	if (inCity(lat, lon)) return [lat, lon];
	const px = lon * K;
	let best = Infinity;
	let q = [px, lat];
	let n = [0, 0];
	for (let i = 0; i < FLAT.length - 1; i++) {
		const [ax, ay] = FLAT[i];
		const [bx, by] = FLAT[i + 1];
		const dx = bx - ax;
		const dy = by - ay;
		const l2 = dx * dx + dy * dy;
		const t = l2 ? Math.min(1, Math.max(0, ((px - ax) * dx + (lat - ay) * dy) / l2)) : 0;
		const qx = ax + t * dx;
		const qy = ay + t * dy;
		const d = (px - qx) ** 2 + (lat - qy) ** 2;
		if (d < best) {
			best = d;
			q = [qx, qy];
			const l = Math.sqrt(l2) || 1;
			n = [-dy / l, dx / l];
		}
	}
	// nudge inside: across the segment one way or the other, or towards the middle of the city at a tip
	const cl = Math.hypot(CX - q[0], CY - q[1]) || 1;
	for (const [ox, oy] of [n, [-n[0], -n[1]], [(CX - q[0]) / cl, (CY - q[1]) / cl]]) {
		const x = q[0] + ox * EPS;
		const y = q[1] + oy * EPS;
		if (inCity(y, x / K)) return [y, x / K];
	}
	return [q[1], q[0] / K];
}
