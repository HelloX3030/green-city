import type { FeatureCollection, LineString } from 'geojson';
import type { IconName } from './icons';

export type ReportType = 'noise' | 'heat' | 'air' | 'no_shade' | 'other';

// one colour and icon per type, used on pins, tiles, badges and chips alike
// same as RADIUS_M in backend/clustering.py: reports this close to a bubble join it
export const CLUSTER_RADIUS_M = 100;

export const TYPES: { id: ReportType; label: string; color: string; icon: IconName }[] = [
	{ id: 'noise', label: 'Zu laut', color: '#6f63b8', icon: 'noise' },
	{ id: 'heat', label: 'Zu heiß', color: '#c4664f', icon: 'heat' },
	{ id: 'air', label: 'Schlechte Luft', color: '#4e7ea6', icon: 'air' },
	{ id: 'no_shade', label: 'Kein Schatten', color: '#a18a4f', icon: 'no_shade' },
	{ id: 'other', label: 'Anderes', color: '#8a8a8e', icon: 'other' }
];

export const typeInfo = (id: string) => TYPES.find((t) => t.id === id) ?? TYPES[4];

export interface Report {
	id: number;
	message: string | null;
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
	people: number; // distinct users
	recent: number; // of the last 7 days
	mine: number; // sent from this device (0 without a token)
	weight: number; // one voice per person and day, halves every 7 days: the bubble size
	types: Record<string, number>; // people per type, the dominant first
	dominant: ReportType; // the type most people name
	latest: string;
	report_ids: number[];
	points: [number, number, string][]; // lat, lon, first type of each report
	status: Status | null;
	reason: string | null;
}

export type Status = 'confirmed' | 'unconfirmed' | 'no_data';

export const STATUS: Record<Status, { label: string; color: string }> = {
	confirmed: { label: 'Bestätigt', color: '#3a7d5c' },
	unconfirmed: { label: 'Nicht bestätigt', color: '#c38b2f' },
	no_data: { label: 'Keine Daten', color: '#8e8e93' }
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

export const SENSOR_KIND: Record<Sensor['kind'], { color: string; icon: IconName; label: string }> = {
	env: { color: '#c4664f', icon: 'heat', label: 'Wetter' },
	air: { color: '#4e7ea6', icon: 'air', label: 'Luft' },
	noise: { color: '#6f63b8', icon: 'noise', label: 'Lärm' }
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

// who this phone is: a random token, kept in localStorage, sent in a header on every request.
// the backend makes a user out of it on first contact. no login in v00.
let memToken = '';
export function deviceToken(): string {
	try {
		let t = localStorage.getItem('device') ?? localStorage.getItem('author'); // 'author' is the old key
		if (!t) {
			t = Array.from(crypto.getRandomValues(new Uint8Array(16)), (b) => b.toString(16).padStart(2, '0')).join('');
		}
		localStorage.setItem('device', t);
		return t;
	} catch {
		return (memToken ||= crypto.randomUUID());
	}
}

const req = (path: string, init: RequestInit = {}) =>
	fetch(`${base}${path}`, { ...init, headers: { ...init.headers, 'x-device': deviceToken() } });

export const getClusters = async (): Promise<Cluster[]> => (await req('/clusters')).json();

export const getReports = async (): Promise<Report[]> => (await req('/reports')).json();

export const getMine = async (): Promise<Report[]> => (await req('/reports/mine')).json();

export interface Me {
	id: number;
	name: string | null; // the account in v00
	devices: number;
}

const json = (body: unknown, method = 'POST'): RequestInit => ({
	method,
	headers: { 'content-type': 'application/json' },
	body: JSON.stringify(body)
});

export const getMe = async (): Promise<Me> => (await req('/me')).json();

export const setName = async (name: string): Promise<Me> => (await req('/me', json({ name }, 'PATCH'))).json();

export const linkCode = async (): Promise<{ code: string; expires_at: string }> =>
	(await req('/me/link', { method: 'POST' })).json();

export async function claim(code: string): Promise<Me> {
	const r = await req('/me/claim', json({ code }));
	if (!r.ok) throw new Error(`${r.status}`);
	return r.json();
}

export async function deleteReport(id: number): Promise<void> {
	const r = await req(`/reports/${id}`, { method: 'DELETE' });
	if (!r.ok) throw new Error(`${r.status}`);
}

export const getSensors = async (): Promise<Sensor[]> =>
	(await req('/sensors')).json();

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
	(await req('/bikes')).json();

export type LayerId = 'noise' | 'trees' | 'bikes' | 'pm';

export const LAYERS: { id: LayerId; label: string; color: string; icon: IconName; hint: string }[] = [
	{ id: 'noise', label: 'Lärmkarte 2022', color: '#b06a5a', icon: 'map', hint: 'Berechneter Straßenlärm, Umweltbundesamt' },
	{ id: 'trees', label: 'Stadtbäume', color: '#7aa874', icon: 'tree', hint: '43 000 Bäume aus dem Baumkataster' },
	{
		id: 'bikes',
		label: 'Messräder, letzte 7 Tage',
		color: '#4e7ea6',
		icon: 'bike',
		hint: 'Räder mit Feinstaubsensor (senseBox:bike). Farbe = PM2,5 der Fahrt'
	},
	{
		id: 'pm',
		label: 'Feinstaub, alle Fahrten',
		color: '#9a8468',
		icon: 'air',
		hint: 'Alle Messrad-Fahrten seit Nov. 2025 auf einem 25-m-Raster. Farbe = PM2,5 im Mittel'
	}
];

export const PM_LEGEND: [string, string][] = [
	['<10', '#5a8f5f'],
	['10', '#c7a24a'],
	['15', '#c4664f'],
	['25', '#a03d3d']
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
	v < 10 ? '#5a8f5f' : v < 15 ? '#c7a24a' : v < 25 ? '#c4664f' : '#a03d3d';

export async function postReport(body: {
	lat: number;
	lon: number;
	types: ReportType[];
	message?: string;
}): Promise<Report> {
	const res = await req('/reports', {
		method: 'POST',
		headers: { 'content-type': 'application/json' },
		body: JSON.stringify(body)
	});
	if (!res.ok) throw new Error(await res.text());
	return res.json();
}

export const dominantType = (c: Cluster): ReportType => c.dominant ?? 'other';

// the reports of one bubble, newest first, no author
export async function clusterReports(id: number): Promise<Report[]> {
	const res = await req(`/clusters/${id}/reports`);
	return res.ok ? res.json() : [];
}
