// what the map shows of the reports: which types, how many reports at least, how far back, only confirmed.
// Nothing set means everything, the defaults; the choice is kept in localStorage.
import { TYPES, type Cluster, type ReportType } from './api';

export interface Filter {
	types: ReportType[]; // empty means all
	min: 1 | 3 | 10; // reports at least
	days: 7 | 14 | 30;
	confirmed: boolean;
}

export const MINS = [1, 3, 10] as const;
export const DAYS = [7, 14, 30] as const;
export const DEFAULT: Filter = { types: [], min: 1, days: 14, confirmed: false };

export const isDefault = (f: Filter) => !f.types.length && f.min === 1 && f.days === 14 && !f.confirmed;

const KEY = 'filter';
export function loadFilter(): Filter {
	try {
		const f = { ...DEFAULT, ...JSON.parse(localStorage.getItem(KEY) ?? '{}') };
		f.types = f.types.filter((t: string) => TYPES.some((x) => x.id === t));
		if (!MINS.includes(f.min)) f.min = 1;
		if (!DAYS.includes(f.days)) f.days = 14;
		return f;
	} catch {
		return DEFAULT;
	}
}
export function saveFilter(f: Filter) {
	try {
		isDefault(f) ? localStorage.removeItem(KEY) : localStorage.setItem(KEY, JSON.stringify(f));
	} catch {}
}

// the bubbles that pass, each counted and coloured by the chosen types only
export function applyFilter(clusters: Cluster[], f: Filter): Cluster[] {
	const out: Cluster[] = [];
	for (const c of clusters) {
		if (f.confirmed && c.status !== 'confirmed') continue;
		let v = c;
		if (f.types.length) {
			const types = Object.fromEntries(Object.entries(c.types).filter(([t]) => f.types.includes(t as ReportType)));
			const keys = Object.keys(types) as ReportType[];
			if (!keys.length) continue;
			// reports per chosen type summed, as on the chips; a report naming two of them is still one report
			const count = Math.min(c.count, Object.values(types).reduce((a, b) => a + b, 0));
			v = { ...c, types, dominant: keys[0], count };
		}
		if (v.count < f.min) continue;
		out.push(v);
	}
	return out;
}
