import type { FeatureCollection, LineString } from 'geojson';

export type ReportType = 'noise' | 'heat' | 'air' | 'no_shade' | 'other';

export const TYPES: { id: ReportType; label: string; color: string }[] = [
	{ id: 'noise', label: 'Zu laut', color: '#a78bfa' },
	{ id: 'heat', label: 'Zu heiß', color: '#fb923c' },
	{ id: 'air', label: 'Schlechte Luft', color: '#9ca3af' },
	{ id: 'no_shade', label: 'Kein Schatten', color: '#4ade80' },
	{ id: 'other', label: 'Anderes', color: '#60a5fa' }
];

export const typeInfo = (id: string) => TYPES.find((t) => t.id === id) ?? TYPES[4];

export interface Report {
	id: number;
	message: string | null;
	author: string | null;
	lat: number;
	lon: number;
	types: ReportType[];
	created_at: string;
}

export interface Cluster {
	id: number;
	lat: number;
	lon: number;
	count: number;
	weight: number; // count with decay, halves every 7 days
	types: Record<string, number>;
	dominant: ReportType; // by decayed weight
	latest: string;
	report_ids: number[];
	status: Status | null;
	reason: string | null;
}

export type Status = 'confirmed' | 'unconfirmed' | 'no_data';

export const STATUS: Record<Status, { label: string; color: string }> = {
	confirmed: { label: 'Bestätigt', color: '#4ade80' },
	unconfirmed: { label: 'Nicht bestätigt', color: '#facc15' },
	no_data: { label: 'Keine Daten', color: '#f87171' }
};

export interface SensorValue {
	key: string;
	label: string;
	value: number;
	unit: string;
	time: string;
}

export interface Sensor {
	id: string;
	name: string;
	lat: number;
	lon: number;
	source: 'opensensemap' | 'uba';
	kind: 'env' | 'air' | 'noise';
	team: boolean;
	values: SensorValue[];
	last: string | null;
}

export const SENSOR_COLOR: Record<Sensor['kind'], string> = {
	env: '#38bdf8',
	air: '#9ca3af',
	noise: '#facc15'
};

export const isLive = (s: Sensor) => !!s.last && Date.now() - new Date(s.last).getTime() < 2 * 3600e3;

export function timeAgo(iso: string | null) {
	if (!iso) return 'noch nie';
	const m = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
	if (m < 1) return 'gerade eben';
	if (m < 60) return `vor ${m} min`;
	const h = Math.round(m / 60);
	if (h < 48) return `vor ${h} h`;
	return `vor ${Math.round(h / 24)} Tagen`;
}

const base =
	import.meta.env.VITE_API_URL ?? `${location.protocol}//${location.hostname}:8000`;

export const getClusters = async (): Promise<Cluster[]> =>
	(await fetch(`${base}/clusters`)).json();

export const getReports = async (): Promise<Report[]> =>
	(await fetch(`${base}/reports`)).json();

export const getSensors = async (): Promise<Sensor[]> =>
	(await fetch(`${base}/sensors`)).json();

export interface Ride {
	id: string;
	box: string;
	start: string;
	end: string;
	km: number;
	pm25: number;
	pm25_max: number;
	points: number;
}

export const getBikes = async (): Promise<FeatureCollection<LineString, Ride>> =>
	(await fetch(`${base}/bikes`)).json();

export type LayerId = 'noise' | 'trees' | 'bikes';

export const LAYERS: { id: LayerId; label: string; color: string; hint: string }[] = [
	{ id: 'noise', label: 'Lärmkarte 2022', color: '#cd463e', hint: 'Straßenlärm Lden, UBA' },
	{ id: 'trees', label: 'Bäume', color: '#22c55e', hint: 'Baumkataster Stadt Heilbronn' },
	{ id: 'bikes', label: 'Messräder 7 Tage', color: '#f472b6', hint: 'senseBox:bike, PM2,5 je Fahrt' }
];

export const NOISE_LEGEND = [
	['55', '#e2f2bf'],
	['60', '#f3c683'],
	['65', '#cd463e'],
	['70', '#75085c'],
	['>75', '#430a4a']
];

// PM2.5 colour for a ride mean, WHO daily limit is 15
export const pmColor = (v: number) =>
	v < 10 ? '#4ade80' : v < 15 ? '#facc15' : v < 25 ? '#fb923c' : '#f87171';

export async function postReport(body: {
	lat: number;
	lon: number;
	types: ReportType[];
	message?: string;
}): Promise<Report> {
	const res = await fetch(`${base}/reports`, {
		method: 'POST',
		headers: { 'content-type': 'application/json' },
		body: JSON.stringify({ ...body, author: authorId() })
	});
	if (!res.ok) throw new Error(await res.text());
	return res.json();
}

export function authorId(): string {
	try {
		let id = localStorage.getItem('author');
		if (!id) {
			id = crypto.randomUUID();
			localStorage.setItem('author', id);
		}
		return id;
	} catch {
		return 'anon';
	}
}

export const dominantType = (c: Cluster): ReportType => c.dominant ?? 'other';
