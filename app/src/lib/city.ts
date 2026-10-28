import boundary from './boundary.json';

// city limit from opendata.heilbronn.de, see `make boundary`
export const RING = boundary.ring as [number, number][];
export const CITY_BBOX: [number, number, number, number] = [
	Math.min(...RING.map((p) => p[0])),
	Math.min(...RING.map((p) => p[1])),
	Math.max(...RING.map((p) => p[0])),
	Math.max(...RING.map((p) => p[1]))
];
export const inCity = (lat: number, lon: number) =>
	lon > CITY_BBOX[0] && lon < CITY_BBOX[2] && lat > CITY_BBOX[1] && lat < CITY_BBOX[3];
