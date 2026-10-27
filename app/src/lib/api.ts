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
	types: Record<string, number>;
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

export const dominantType = (c: Cluster): ReportType =>
	(Object.entries(c.types).sort((a, b) => b[1] - a[1])[0]?.[0] as ReportType) ?? 'other';
