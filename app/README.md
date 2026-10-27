# app

SvelteKit + MapLibre. One page: map, report sheet, cluster card.

```
npm install
npm run dev -- --host     # phone on the same wifi: http://<laptop-ip>:5173
npm run build             # static files in build/
```

Backend defaults to `http://<same host>:8000`. Override with `VITE_API_URL` in `.env`.
