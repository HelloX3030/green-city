# 3d-model

`CreateLeafMacro.py` builds the NoiseNode leaf case in FreeCAD; `verify_model.py` runs it headless with 65 geometry checks (`conda run -n freecad freecadcmd verify_model.py`, writes the gitignored `build/`).

- `export/` — newest printable STLs (body, lid, rails, plug), `case.step` (assembly) and `case.glb` (viewer model).
- `viewer/` — self-contained three.js viewer of `export/case.glb` (serve `3d-model/` with `python3 -m http.server`, open `/viewer/`).
- `renders/` — PNG renders (1600 px) of the case for slides and the handout, made from the viewer.

Regenerate all three in one go: `./make_exports.sh`
