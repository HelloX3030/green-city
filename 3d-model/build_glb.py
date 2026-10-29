"""Build export/case.glb (binary glTF of the whole assembly) from the STLs.

    conda run -n freecad python build_glb.py        # needs trimesh (pip install trimesh)

Input: export/{body,lid,rails,plug}.stl and build/glb-src/{mcu,sensor}.stl as
written by export_model.py. One node per part, named like the STL. Printed
parts share a neutral material, the two reference boards a second, slightly
transparent one. Vertices are split along edges sharper than 30 deg so the
viewer shades curved faces smoothly and box edges crisply. Verifies the file
by loading it again and prints the part list.
"""
import os
import sys
import numpy as np
import trimesh
from trimesh.visual.material import PBRMaterial

AQUI = os.path.dirname(os.path.abspath(__file__))
EXPORT = os.path.join(AQUI, "export")
GLB_SRC = os.path.join(AQUI, "build", "glb-src")
OUT = os.path.join(EXPORT, "case.glb")

PRINTED = (0.86, 0.85, 0.82, 1.0)   # neutral light grey, like unpainted PETG
BOARD = (0.23, 0.49, 0.36, 0.62)    # app accent green, slightly transparent

PARTS = [  # (name, folder, material)
    ("body", EXPORT, "printed"),
    ("lid", EXPORT, "printed"),
    ("rails", EXPORT, "printed"),
    ("plug", EXPORT, "printed"),
    ("mcu", GLB_SRC, "board"),
    ("sensor", GLB_SRC, "board"),
]

materials = {
    "printed": PBRMaterial(name="printed", baseColorFactor=PRINTED,
                           metallicFactor=0.0, roughnessFactor=0.6),
    "board": PBRMaterial(name="board", baseColorFactor=BOARD,
                         metallicFactor=0.0, roughnessFactor=0.45,
                         alphaMode="BLEND", doubleSided=True),
}

scene = trimesh.Scene()
for name, folder, mat in PARTS:
    path = os.path.join(folder, name + ".stl")
    m = trimesh.load(path, force="mesh")           # merges coincident vertices
    m = trimesh.graph.smooth_shade(m, angle=np.radians(30))  # split sharp edges
    m.visual = trimesh.visual.TextureVisuals(material=materials[mat])
    m.metadata["name"] = name
    scene.add_geometry(m, node_name=name, geom_name=name)
    print(f"  {name}: {len(m.faces)} tris, {len(m.vertices)} verts")

scene.export(OUT, include_normals=True)
size = os.path.getsize(OUT)
print(f"wrote {os.path.relpath(OUT, AQUI)}: {size/1e6:.2f} MB")

# verify: load it back
check = trimesh.load(OUT, force="scene")
names = sorted(check.geometry)
print("glb parts:", names)
b = check.bounds
print(f"glb bounds: {b[0].round(1)} .. {b[1].round(1)} (mm, Z up)")
missing = [n for n, _, _ in PARTS if n not in names]
if missing or size > 5_000_000:
    print("FAIL", "missing parts" if missing else "too big", missing)
    sys.exit(1)
