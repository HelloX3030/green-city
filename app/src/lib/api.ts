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
	status: string | null;
}

const base =
	import.meta.env.VITE_API_URL ?? `${location.protocol}//${location.hostname}:8000`;

export const getClusters = async (): Promise<Cluster[]> =>
	(await fetch(`${base}/clusters`)).json();

export const getReports = async (): Promise<Report[]> =>
	(await fetch(`${base}/reports`)).json();

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
