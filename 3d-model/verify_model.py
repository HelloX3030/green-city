"""Verificación headless de la carcasa hoja (CreateLeafMacro.py).

Uso (necesita FreeCAD sin GUI; p. ej. el env conda "freecad"):

    cd 3d-model
    conda run -n freecad freecadcmd verify_model.py

Ejecuta el macro, comprueba las condiciones geométricas (colisiones con las
placas, encaje y cierre de la tapa, carro de raíles suelto y sus ranuras,
tapón USB, capucha del mic, alero, nervaduras, QR, refuerzos, insertos) y
exporta los STL más el FCStd reconstruido a ./build/ (carpeta no versionada).

Variables opcionales: LEAF_MACRO (ruta al macro), LEAF_OUT (carpeta salida).
Código de salida 0 si todo pasa, 1 si algo falla.
"""
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
MACRO = os.environ.get("LEAF_MACRO", os.path.join(AQUI, "CreateLeafMacro.py"))
OUT = os.environ.get("LEAF_OUT", os.path.join(AQUI, "build"))
os.makedirs(OUT, exist_ok=True)

# El macro guarda sus líneas de GUI tras "if App.GuiUp:", así que se puede
# ejecutar tal cual en freecadcmd.
g = {}
with open(MACRO) as f:
    exec(compile(f.read(), MACRO, "exec"), g)

import FreeCAD as App
import Part

doc = App.ActiveDocument
objs = {o.Name: o for o in doc.Objects}
print("Objects:", list(objs))

body = objs["Caja_Base_Ampliada"].Shape
lid = objs["Tapa_Hoja_Ampliada"].Shape
mcu = objs["REF_senseBox_MCU"].Shape
sensor = objs["REF_DFRobot_SoundMeter"].Shape
plug = objs["Tapon_USB"].Shape
carro = objs["Carro_Railes"].Shape

failures = []
def check(name, ok, detail=""):
    print(("PASS" if ok else "FAIL"), name, detail)
    if not ok:
        failures.append(name)

# --- validity ---
check("body valid solid", body.isValid() and len(body.Solids) >= 1,
      f"solids={len(body.Solids)}")
check("lid valid solid", lid.isValid() and len(lid.Solids) >= 1,
      f"solids={len(lid.Solids)}")
check("rail sled valid single solid", carro.isValid() and len(carro.Solids) == 1,
      f"solids={len(carro.Solids)}")

def overlap(a, b):
    return a.common(b).Volume

# --- component envelope collisions with enclosure body ---
check("MCU does not intersect body", overlap(body, mcu) < 1e-6,
      f"overlap={overlap(body, mcu):.1f} mm^3")
check("sensor does not intersect body", overlap(body, sensor) < 1e-6,
      f"overlap={overlap(body, sensor):.1f} mm^3")
check("MCU does not intersect lid", overlap(lid, mcu) < 1e-6,
      f"overlap={overlap(lid, mcu):.1f} mm^3")
check("sensor does not intersect lid", overlap(lid, sensor) < 1e-6,
      f"overlap={overlap(lid, sensor):.1f} mm^3")
check("MCU and sensor don't collide", overlap(mcu, sensor) < 1e-6)

# --- components inside the enclosure footprint ---
bb_body = body.BoundBox
for nm, s in (("MCU", mcu), ("sensor", sensor)):
    bb = s.BoundBox
    inside = (bb.XMin > bb_body.XMin and bb.XMax < bb_body.XMax and
              bb.YMin > bb_body.YMin and bb.YMax < bb_body.YMax)
    check(f"{nm} inside body footprint", inside,
          f"{nm} bb=({bb.XMin:.1f},{bb.YMin:.1f},{bb.ZMin:.1f})-({bb.XMax:.1f},{bb.YMax:.1f},{bb.ZMax:.1f})")

# --- sensor support: does the sensor actually rest on the sled's rails? ---
sensor_drop = sensor.copy()
sensor_drop.translate(App.Vector(0, 0, -0.5))
support = overlap(carro, sensor_drop)
check("sensor is supported by sled rails (drop test)", support > 1.0,
      f"contact volume when lowered 0.5mm = {support:.2f} mm^3")

# --- sensor is captive on the sled: stops fore and aft, free drop-in from above ---
for dx, nm in ((2.0, "+x"), (-2.0, "-x")):
    s = sensor.copy(); s.translate(App.Vector(dx, 0, 0))
    check(f"sled stop blocks sensor sliding {nm}", overlap(carro, s) > 1.0,
          f"contact when slid {nm} 2mm = {overlap(carro, s):.1f} mm^3")
s_up = sensor.copy(); s_up.translate(App.Vector(0, 0, 5.0))
check("sensor drop-in path from above is clear",
      overlap(body, s_up) < 1e-6 and overlap(carro, s_up) < 1e-6,
      f"overlap when raised 5mm = body {overlap(body, s_up):.3f} + sled {overlap(carro, s_up):.3f} mm^3")

# --- rail sled: seats with no interference, locked in XY by the wall divots,
# --- supported by the divot floors, and slides out freely upward ---
check("sled seats without interference", overlap(body, carro) < 1e-3,
      f"body/sled overlap = {overlap(body, carro):.4f} mm^3")
check("sled clears the lid", overlap(lid, carro) < 1e-3,
      f"lid/sled overlap = {overlap(lid, carro):.4f} mm^3")
check("sled clears the MCU", overlap(carro, mcu) < 1e-6,
      f"sled/MCU overlap = {overlap(carro, mcu):.2f} mm^3")
for dv, nm in ((App.Vector(2, 0, 0), "+x"), (App.Vector(-2, 0, 0), "-x"),
               (App.Vector(0, 1, 0), "+y"), (App.Vector(0, -1, 0), "-y")):
    c = carro.copy(); c.translate(dv)
    check(f"divots lock sled {nm}", overlap(body, c) > 0.5,
          f"contact when shifted {nm} = {overlap(body, c):.1f} mm^3")
c_dn = carro.copy(); c_dn.translate(App.Vector(0, 0, -0.5))
check("divot floors support sled (drop test)", overlap(body, c_dn) > 0.5,
      f"contact when lowered 0.5mm = {overlap(body, c_dn):.1f} mm^3")
c_up = carro.copy(); c_up.translate(App.Vector(0, 0, 5.0))
check("sled slides out freely upward", overlap(body, c_up) < 1e-3,
      f"contact when raised 5mm = {overlap(body, c_up):.4f} mm^3")
check("headroom between sensor and lid underside >= 0.3mm",
      g["altura_carcasa"] - sensor.BoundBox.ZMax >= 0.3 - 1e-9,
      f"gap = {g['altura_carcasa'] - sensor.BoundBox.ZMax:.2f} mm")

# --- USB-C opening: spec = shorter (72mm) side, 36mm from one corner, 10mm wide ---
probe_at_wall = Part.makeBox(30.0, 9.0, 6.0,
                             App.Vector(-g["W"]/2 - 3.0, g["usb_y0"] + 0.5, g["grosor_base"] + 4.5))
check("USB-C opening pierces wall (spec position)", overlap(body, probe_at_wall) < 1.0,
      f"material in opening = {overlap(body, probe_at_wall):.1f} mm^3")
mcu_cy = (mcu.BoundBox.YMin + mcu.BoundBox.YMax) / 2.0
check("USB-C opening centered on connector (board file: center +5mm)",
      abs(g["usb_centro_y"] - (mcu_cy + 5.0)) < 1e-6,
      f"center={g['usb_centro_y']:.2f} board center+5={mcu_cy + 5.0:.1f}")
probe_plug = Part.makeBox(30.0, 12.5, 7.0,
                          App.Vector(-g["W"]/2 - 3.0, g["usb_centro_y"] - 6.25, g["usb_cz"] - 3.5))
check("opening admits USB-C plug overmold (12.5 x 7)", overlap(body, probe_plug) < 1.0,
      f"material in plug path = {overlap(body, probe_plug):.1f} mm^3")

# --- MCU standoffs: screw posts at the board's real M3 holes, board supported ---
for px, py in g["puntos_m3_sb"]:
    ok = (abs(abs(px) - 24.5) < 1e-6 and
          abs(py - (mcu.BoundBox.YMax - 5.0)) < 1e-6 and
          mcu.BoundBox.XMin < px < mcu.BoundBox.XMax and
          mcu.BoundBox.YMin < py < mcu.BoundBox.YMax)
    check(f"M3 post at board drill position ({px:.1f},{py:.1f})", ok,
          f"board file: x=+-24.5, y=top edge-5 ({mcu.BoundBox.YMax - 5.0:.1f})")
mcu_drop = mcu.copy(); mcu_drop.translate(App.Vector(0, 0, -0.5))
check("MCU is supported by posts (drop test)", overlap(body, mcu_drop) > 1.0,
      f"contact when lowered 0.5mm = {overlap(body, mcu_drop):.1f} mm^3")

# --- rails clear the MCU component envelope ---
z_rail = g["grosor_base"] + g["z_separacion"]
check("rails start above MCU envelope", z_rail >= mcu.BoundBox.ZMax,
      f"rail bottom={z_rail:.1f} MCU top={mcu.BoundBox.ZMax:.1f}")

# --- mic hole pierces the lid above the sensor edge (probe stops inside the hood) ---
mic_x = -g["df_largo"]/2 + 2.0
probe_mic = Part.makeCylinder(2.5, 8.5, App.Vector(mic_x, 0, sensor.BoundBox.ZMax - 0.1))
check("mic hole pierces lid", overlap(lid, probe_mic) < 1.0,
      f"material above mic = {overlap(lid, probe_mic):.1f} mm^3")

# --- mic rain hood: cap blocks vertical rain, side mouth stays open ---
h = g["altura_carcasa"]
probe_rain = Part.makeCylinder(2.0, 12.0, App.Vector(mic_x, 0, h + 9.2))
check("mic hood cap blocks vertical rain", overlap(lid, probe_rain) > 10.0,
      f"cap material over mic = {overlap(lid, probe_rain):.1f} mm^3")
probe_boca = Part.makeBox(5.0, 4.0, 1.7, App.Vector(mic_x - 7.9, -2.0, h + 6.1))
check("mic hood side mouth is open", overlap(lid, probe_boca) < 0.5,
      f"material in mouth = {overlap(lid, probe_boca):.2f} mm^3")

# --- drip edge: lid rim overhangs the body wall (probe just outside the wall) ---
p_x = Part.makeBox(1.3, 3.0, 0.4, App.Vector(g["W"]/2 + 0.2, 13.0, h + 0.1))
check("drip edge overhangs wall at +x", overlap(lid, p_x) > 0.1 and overlap(body, p_x) < 1e-6,
      f"alero material outside wall = {overlap(lid, p_x):.2f} mm^3")
p_y = Part.makeBox(3.0, 1.3, 0.4, App.Vector(-1.5, -g["L"]/2 - 1.5, h + 0.1))
check("drip edge overhangs wall at tip", overlap(lid, p_y) > 0.1 and overlap(body, p_y) < 1e-6,
      f"alero material outside wall = {overlap(lid, p_y):.2f} mm^3")

# --- leaf aesthetics: smooth spline outline, veins, QR recess ---
check("outline is a smooth B-spline",
      any(isinstance(e.Curve, Part.BSplineCurve) for e in body.Edges))
p_stem = Part.makeBox(4.0, 2.0, 3.0, App.Vector(-2.0, -87.0, 3.0))
check("no stem beyond leaf tip (removed in v2)", overlap(body, p_stem) < 1e-6,
      f"material at y=-87..-85 = {overlap(body, p_stem):.1f} mm^3")
p_rib = Part.makeCylinder(0.35, 0.45, App.Vector(0, -40.0, 34.85))
check("midrib groove engraved (0.8mm)", overlap(lid, p_rib) < 0.05,
      f"material in groove = {overlap(lid, p_rib):.3f} mm^3")
p_vein = Part.makeCylinder(0.35, 0.45, App.Vector(8.19, 43.74, 34.85))
check("side vein groove engraved", overlap(lid, p_vein) < 0.05,
      f"material in groove = {overlap(lid, p_vein):.3f} mm^3")
p_qr_air = Part.makeBox(23.0, 23.0, 0.4, App.Vector(-11.5, 8.5, 35.0))
check("QR recess is open (0.6mm pocket)", overlap(lid, p_qr_air) < 0.5,
      f"material in pocket = {overlap(lid, p_qr_air):.2f} mm^3")
p_qr_floor = Part.makeBox(23.0, 23.0, 0.3, App.Vector(-11.5, 8.5, 34.4))
check("QR recess floor is solid", overlap(lid, p_qr_floor) > 140.0,
      f"floor material = {overlap(lid, p_qr_floor):.1f} mm^3 (full 158.7)")

# --- strength details: wall-base fillet, bottom chamfer, insert bores ---
fi = g["factor_interior"]
wx_, wy_ = 65.0 * fi, 14.5 * fi
ux_, uy_ = 65.0 / 66.6, 14.5 / 66.6
p_fil = Part.makeBox(0.7, 0.7, 0.7,
                     App.Vector(wx_ - ux_ * 0.7 - 0.35, wy_ - uy_ * 0.7 - 0.35, 2.6))
check("wall-base fillet present", overlap(body, p_fil) > 0.2,
      f"fillet material in corner = {overlap(body, p_fil):.2f} mm^3")
p_cham = Part.makeBox(0.45, 3.0, 0.18, App.Vector(64.8, 13.0, 0.0))
check("bottom edge chamfered", overlap(body, p_cham) < 0.05,
      f"material at bottom rim corner = {overlap(body, p_cham):.3f} mm^3")
for px, py in g["puntos_m3_sb"]:
    p_bore = Part.makeCylinder(1.8, 3.6, App.Vector(px, py, 2.6))
    check(f"heat-set insert bore open at ({px:.1f},{py:.1f})", overlap(body, p_bore) < 0.05,
          f"material in bore = {overlap(body, p_bore):.2f} mm^3")
    p_floor = Part.makeCylinder(1.0, 0.6, App.Vector(px, py, 0.2))
    check(f"pilot floor solid under post ({px:.1f},{py:.1f})", overlap(body, p_floor) > 1.5,
          f"floor material = {overlap(body, p_floor):.2f} mm^3 (full 1.88)")

# --- base is blind (v2): the old keyhole / zip-tie / weep hole positions are solid ---
for hx, hy in [(-20.0, -35.0), (20.0, -35.0), (0.0, 52.0),
               (-12.0, -45.0), (12.0, -45.0), (-12.0, 48.0), (12.0, 48.0),
               (-6.0, -52.0), (6.0, -52.0)]:
    p = Part.makeCylinder(0.8, g["grosor_base"] - 0.4, App.Vector(hx, hy, 0.2))
    check(f"base solid at old hole ({hx:.0f},{hy:.0f})", overlap(body, p) > 3.0,
          f"material = {overlap(body, p):.2f} mm^3 (full {3.14159*0.64*(g['grosor_base']-0.4):.2f})")

# --- printed USB plug: seats with clearance, stops on the flare, pulls out ---
check("USB plug seats without interference", overlap(body, plug) < 1e-3,
      f"body/plug overlap = {overlap(body, plug):.4f} mm^3")
check("USB plug clears MCU", overlap(plug, mcu) < 1e-6,
      f"plug/MCU overlap = {overlap(plug, mcu):.2f} mm^3")
plug_in = plug.copy(); plug_in.translate(App.Vector(2.0, 0, 0))
check("USB plug stops against flare (push-in 2mm collides)", overlap(body, plug_in) > 1.0,
      f"contact when pushed 2mm = {overlap(body, plug_in):.1f} mm^3")
plug_out = plug.copy(); plug_out.translate(App.Vector(-3.0, 0, 0))
check("USB plug pulls out freely", overlap(body, plug_out) < 1e-3,
      f"contact when pulled 3mm = {overlap(body, plug_out):.4f} mm^3")

# --- interior height: sensor must fit under the lid rim (skirt hangs lower at the walls) ---
check("sensor top <= body rim", sensor.BoundBox.ZMax <= g["altura_carcasa"] + 1e-6,
      f"sensor top={sensor.BoundBox.ZMax:.2f} rim={g['altura_carcasa']:.2f}")

# --- lid closure: seated lid must not interfere, but must register and snap ---
check("lid seats without interference", overlap(body, lid) < 1e-3,
      f"body/lid overlap={overlap(body, lid):.4f} mm^3")
lid_shift = lid.copy(); lid_shift.translate(App.Vector(2.0, 0, 0))
check("skirt registers lid in XY (2mm shift collides)", overlap(body, lid_shift) > 1.0,
      f"contact when shifted 2mm = {overlap(body, lid_shift):.2f} mm^3")
lid_lift = lid.copy(); lid_lift.translate(App.Vector(0, 0, 1.0))
check("snap bumps retain lid (1mm lift collides)", overlap(body, lid_lift) > 0.01,
      f"contact when lifted 1mm = {overlap(body, lid_lift):.3f} mm^3")

# --- spec dimension echoes ---
# (Ojo: el BoundBox de OCC es laxo tras booleanas con splines; para cotas
# reales, muestrear el STL exportado con Mesh.Mesh().)
print(f"INFO MCU envelope: {mcu.BoundBox.XLength:.2f} x {mcu.BoundBox.YLength:.2f} x {mcu.BoundBox.ZLength:.2f} (board file 74 x 68, alto 11)")
print(f"INFO sensor envelope: {sensor.BoundBox.XLength:.2f} x {sensor.BoundBox.YLength:.2f} x {sensor.BoundBox.ZLength:.2f} (spec 60.25 x 42.5 x 7.5)")
print(f"INFO enclosure: {bb_body.XLength:.1f} x {bb_body.YLength:.1f}, body h={bb_body.ZLength:.1f}, with lid top={lid.BoundBox.ZMax:.1f}")
print(f"INFO material volume: body={body.Volume/1000:.1f} cm^3, lid={lid.Volume/1000:.1f} cm^3")

# --- export for visual inspection / printing ---
import Mesh
for nm, s in (("body", body), ("lid", lid), ("rails", carro),
              ("mcu", mcu), ("sensor", sensor), ("plug", plug)):
    m = doc.addObject("Mesh::Feature", "M_" + nm)
    m.Mesh = Mesh.Mesh(s.tessellate(0.3))
    Mesh.export([m], os.path.join(OUT, nm + ".stl"))

doc.saveAs(os.path.join(OUT, "LeafModel_rebuilt.FCStd"))

print("RESULT:", "ALL PASS" if not failures else f"{len(failures)} FAILURES: {failures}")
# freecadcmd termina sin vaciar el buffer de stdout cuando se lanza
# SystemExit: hay que hacer flush antes para no perder el informe.
sys.stdout.flush()
sys.exit(0 if not failures else 1)
