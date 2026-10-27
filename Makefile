.PHONY: setup dev backend app build check trees

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

trees:            ## rebuild app/static/trees.json from the city tree register
	python3 research/trees.py
