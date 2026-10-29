#!/usr/bin/env bash
# Rebuild everything presentable from the macro: verify + build/, export/ (STL, STEP, glb), renders/.
# Needs the conda env "freecad" (freecadcmd, trimesh, scipy) and google-chrome.
set -euo pipefail
cd "$(dirname "$0")"
conda run -n freecad freecadcmd verify_model.py     # runs the macro, 65 checks, build/*.stl + FCStd (~3.5 min)
conda run -n freecad freecadcmd export_model.py     # export/{body,lid,rails,plug}.stl + case.step
conda run -n freecad python build_glb.py            # export/case.glb (verified by reloading)
node render.mjs                                     # renders/*.png via the viewer + headless Chrome over CDP
