# NoiseNode case viewer

`index.html` is a self-contained three.js (0.160.0, jsDelivr CDN) viewer that loads `../export/case.glb`, so `viewer/` and `export/` must sit next to each other.
Serve locally with `python3 -m http.server 8000` run inside `3d-model/`, then open <http://localhost:8000/viewer/>; or copy both folders onto any static host (the app's static folder works too).
`export/` holds the printable STLs (body, lid, rails, plug), `case.step` (the whole assembly for CAD) and `case.glb` for the viewer.
URL parameters script the view: `?view=front|top|open|sled|side|explode`, `&explode=1`, `&lid=0`, `&boards=0`, `&ui=0` (used by `make_exports.sh` to render `renders/`).
