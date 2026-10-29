"""Export the newest case model to ./export/ (versioned).

Run headless from inside 3d-model/ after verify_model.py has rebuilt
./build/LeafModel_rebuilt.FCStd (make_exports.sh does both):

    conda run -n freecad freecadcmd export_model.py

Writes export/body.stl, lid.stl, rails.stl, plug.stl (printable parts,
0.1 mm mesh tolerance), export/case.step (the whole assembly incl. the two
reference boards) and build/glb-src/mcu.stl + sensor.stl (the reference
boards, input for build_glb.py together with the printed STLs). Falls back to running CreateLeafMacro.py when the FCStd
is missing. LEAF_OUT / LEAF_BUILD override the folders.
"""
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
BUILD = os.environ.get("LEAF_BUILD", os.path.join(AQUI, "build"))
OUT = os.environ.get("LEAF_OUT", os.path.join(AQUI, "export"))
GLB_SRC = os.path.join(BUILD, "glb-src")
os.makedirs(OUT, exist_ok=True)
os.makedirs(GLB_SRC, exist_ok=True)

import FreeCAD as App
import Part
import Mesh
import Import

fcstd = os.path.join(BUILD, "LeafModel_rebuilt.FCStd")
if os.path.exists(fcstd):
    doc = App.openDocument(fcstd)
    print("Loaded", fcstd)
else:
    macro = os.path.join(AQUI, "CreateLeafMacro.py")
    g = {}
    with open(macro) as f:
        exec(compile(f.read(), macro, "exec"), g)
    doc = App.ActiveDocument
    print("Rebuilt from", macro)

# FreeCAD name -> export name. The first four are the printed parts.
PARTS = [
    ("Caja_Base_Ampliada", "body"),
    ("Tapa_Hoja_Ampliada", "lid"),
    ("Carro_Railes", "rails"),
    ("Tapon_USB", "plug"),
    ("REF_senseBox_MCU", "mcu"),
    ("REF_DFRobot_SoundMeter", "sensor"),
]
PRINTED = {"body", "lid", "rails", "plug"}
objs = {o.Name: o for o in doc.Objects}

def write_stl(shape, path, tol):
    m = Mesh.Mesh(shape.tessellate(tol))
    m.write(path)
    print(f"  {os.path.relpath(path, AQUI)}: {m.CountFacets} facets, {os.path.getsize(path)/1e6:.2f} MB")

step_objs = []
for fc_name, name in PARTS:
    obj = objs[fc_name]
    obj.Label = name  # product names inside the STEP
    step_objs.append(obj)
    # printed parts go to export/, the reference boards only to build/glb-src/
    folder = OUT if name in PRINTED else GLB_SRC
    write_stl(obj.Shape, os.path.join(folder, name + ".stl"), 0.1)

step = os.path.join(OUT, "case.step")
Import.export(step_objs, step)
print(f"  {os.path.relpath(step, AQUI)}: {os.path.getsize(step)/1e6:.2f} MB")

# real outer dimensions from the mesh (OCC's BoundBox is lax after spline booleans)
bb = Mesh.Mesh(objs["Caja_Base_Ampliada"].Shape.tessellate(0.1)).BoundBox
bl = Mesh.Mesh(objs["Tapa_Hoja_Ampliada"].Shape.tessellate(0.1)).BoundBox
print(f"INFO outer: body {bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.1f} mm, "
      f"lid {bl.XLength:.1f} x {bl.YLength:.1f}, assembled height {bl.ZMax - bb.ZMin:.1f} mm")
sys.stdout.flush()
