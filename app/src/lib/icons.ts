// Lucide-style 24x24 stroke icons, one path list each.
const c = (cx: number, cy: number, r: number) =>
	`M${cx - r} ${cy}a${r} ${r} 0 1 0 ${2 * r} 0a${r} ${r} 0 1 0 ${-2 * r} 0`;

export const ICONS = {
	leaf: ['M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.5 19 2c1 2 2 4.2 2 8 0 5.5-4.8 10-10 10Z', 'M2 21c0-3 1.9-5.5 5-6.5'],
	locate: [c(12, 12, 3), 'M12 2v3M12 19v3M2 12h3M19 12h3', c(12, 12, 8)],
	layers: ['m12 2 10 5-10 5L2 7z', 'm2 12 10 5 10-5', 'm2 17 10 5 10-5'],
	noise: ['M11 5 6 9H2v6h4l5 4z', 'M15.5 8.5a5 5 0 0 1 0 7', 'M19 5a10 10 0 0 1 0 14'],
	heat: ['M14 4v10.5a4 4 0 1 1-4 0V4a2 2 0 1 1 4 0z'],
	air: ['M17.7 7.7A2.5 2.5 0 1 1 19.5 12H2', 'M9.6 4.6A2 2 0 1 1 11 8H2', 'M12.6 19.4A2 2 0 1 0 14 16H2'],
	no_shade: [c(12, 12, 4), 'M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4'],
	other: [c(5, 12, 1), c(12, 12, 1), c(19, 12, 1)],
	radio: [c(12, 12, 2), 'M16.2 7.8a6 6 0 0 1 0 8.4M7.8 16.2a6 6 0 0 1 0-8.4M19.1 4.9a10 10 0 0 1 0 14.2M4.9 19.1a10 10 0 0 1 0-14.2'],
	tree: ['m17 14 3 3.3a1 1 0 0 1-.7 1.7H4.7a1 1 0 0 1-.7-1.7L7 14h-.3a1 1 0 0 1-.8-1.6L9 9h-.2A1 1 0 0 1 8 7.4L12 3l4 4.4a1 1 0 0 1-.8 1.6H15l3 3.4a1 1 0 0 1-.8 1.6z', 'M12 22v-3'],
	bike: [c(18.5, 17.5, 3.5), c(5.5, 17.5, 3.5), c(15, 5, 1), 'M12 17.5V14l-3-3 4-3 2 3h2'],
	map: ['M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3z', 'M9 3v15M15 6v15'],
	x: ['M18 6 6 18M6 6l12 12'],
	check: ['M20 6 9 17l-5-5'],
	plus: ['M12 5v14M5 12h14'],
	minus: ['M5 12h14']
} as const;

export type IconName = keyof typeof ICONS;

export const iconSvg = (name: IconName, cls = 'i') =>
	`<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name].map((d) => `<path d="${d}"/>`).join('')}</svg>`;
