.PHONY: setup dev backend app build check test e2e trees boundary pm

setup:            ## install everything (uv + npm)
	cd backend && uv sync
	cd app && npm install

dev:              ## backend :8000 + app :5173, ctrl-c stops both
	@trap 'kill 0' INT TERM; \
	$(MAKE) -s backend & $(MAKE) -s app & wait

backend:
	cd backend && uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

app:
	cd app && npm run dev -- --host

build:            ## static app into app/build
	cd app && npm run build

check:            ## type-check the app
	cd app && npm run check

test:             ## backend unit tests
	cd backend && uv run python -m unittest

e2e:              ## drive app/scenarios.md through headless Chrome (needs make dev running)
	cd app && node e2e/run.mjs

trees:            ## rebuild app/static/trees.json from the city tree register
	python3 research/trees.py

boundary:         ## rebuild app/src/lib/boundary.json from the city limit
	python3 research/boundary.py

pm:               ## rebuild app/static/pm.json, all-time bike PM2.5 grid (~5 min)
	python3 research/pm.py
