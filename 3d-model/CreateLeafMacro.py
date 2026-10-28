import FreeCAD as App
import Part
import math

# ============================================================
# CARCASA HOJA - RAÍLES EXTENDIDOS DE PARED A PARED
# ============================================================

if App.ActiveDocument:
    App.closeDocument(App.ActiveDocument.Name)

doc = App.newDocument("Carcasa_Hoja_Railes_Extendidos")

# ---------------- PARAMETROS (mm) ----------------
L = 145.0  # Largo total
W = 130.0  # Ancho total

# 1. senseBox MCU S2 (Base) — del diseño Eagle oficial (repo sensebox/
# senseBox-MCU-S2-ESP32S2, hardware/2.1 y 2.2): placa de 74 x 68 mm con
# 2 taladros M3 (3.2 mm) en (±24.5, +29) y 2 de 2.5 mm en (±11, +32).
# La medida del equipo en `measurements` (78 x 72) sobremedía ~4 mm por eje.
sb_largo = 74.0
sb_ancho = 68.0
sb_alto = 11.0
desfase_y_mcu = 7.0  # desplaza el MCU hacia la parte ancha de la hoja: centrado, sus esquinas inferiores chocan con la pared

# 2. DFRobot Sound Level Meter V2.0 (Nivel Superior)
df_largo = 60.25
df_ancho = 42.50
df_alto = 7.50

grosor_pared = 3.2
grosor_base = 2.5
grosor_tapa = 2.5

z_separacion = 15.5  # los raíles deben quedar por encima de los 11 mm del MCU (torretas 4 + placa 11 + 0.5 de holgura)
altura_carcasa = z_separacion + df_alto + 6.0 + 0.5  # +0.5 de techo: sin él la tapa
# apoyaría exactamente sobre el sensor (cota justa) y cualquier sobre-extrusión
# dejaría la tapa montada sobre la placa en vez de sobre el borde
altura_domo = 6.0

# ---------------- CONTORNO POLIGONAL HOJA ----------------
contorno = [
    (0, -L/2),
    (W*0.22, -L*0.36),
    (W*0.42, -L*0.15),
    (W*0.50,  L*0.10),
    (W*0.38,  L*0.32),
    (W*0.20,  L*0.43),
    (0,       L/2),
    (-W*0.20, L*0.43),
    (-W*0.38, L*0.32),
    (-W*0.50, L*0.10),
    (-W*0.42,-L*0.15),
    (-W*0.22,-L*0.36),
]

def crear_prisma(puntos, z, altura):
    vertices = [App.Vector(x, y, z) for x, y in puntos]
    vertices.append(vertices[0])
    wire = Part.makePolygon(vertices)
    return Part.Face(wire).extrude(App.Vector(0, 0, altura))

def crear_objeto(nombre, forma, color, transparencia=0):
    obj = doc.addObject("Part::Feature", nombre)
    obj.Shape = forma
    obj.ViewObject.ShapeColor = color
    obj.ViewObject.Transparency = transparencia
    return obj

def crear_wire_perfil(puntos, factor_x, z):
    vertices = [App.Vector(x * factor_x, y, z) for x, y in puntos]
    vertices.append(vertices[0])
    return Part.Wire(Part.makePolygon(vertices).Edges)

def altura_superficie(x):
    u = min(abs(x) / (W * 0.5), 1.0)
    return altura_carcasa + grosor_tapa + altura_domo * (1.0 - u)

# ============================================================
# 1. BASE Y CUERPO PRINCIPAL DE LA CAJA
# ============================================================
exterior = crear_prisma(contorno, 0, altura_carcasa)
factor_interior = 0.92  # con 0.88 la cavidad deja solo ~1.6 mm de holgura para los 72 mm de la placa
contorno_interior = [(x * factor_interior, y * factor_interior) for x, y in contorno]
cavidad = crear_prisma(contorno_interior, grosor_base, altura_carcasa)

cuerpo = exterior.cut(cavidad)

# Orificio para puerto USB-C: el puerto está en el lado corto (72 mm) de la placa,
# con la abertura a 36 mm de una esquina y 26 mm de la otra (ver 3d-model/measurements).
# Como la hoja se estrecha ahí, la placa queda ~19 mm por detrás de la pared, así que
# el conector completo (sobremoldeado típico ~12 x 6.5 mm) debe PASAR por la abertura:
# 13 x 8 mm centrados en la posición de la spec (centro a 36 + 10/2 = 41 mm de la
# esquina), con boca abocinada por fuera para guiar el enchufe hasta el puerto.
usb_ancho = 13.0
usb_alto = 8.0
# En el .brd oficial el conector (USB4105) está en el borde de 68 mm, a +5 mm
# del centro de la placa — coincide con el centro que daba la medida del equipo
usb_centro_y = desfase_y_mcu + 5.0
usb_y0 = usb_centro_y - usb_ancho/2
usb_z0 = grosor_base + 3.5    # la placa apoya sobre torretas de 4 mm
usb_cz = usb_z0 + usb_alto/2

tunel_usbc = Part.makeBox(
    35.0, usb_ancho, usb_alto,
    App.Vector(-W/2 - 5.0, usb_y0, usb_z0)
)

cuerpo = cuerpo.cut(tunel_usbc)

# Boca abocinada: tronco de pirámide de 18 x 13 (fuera) a 13 x 8 (dentro)
def rect_wire_x(x, cy, cz, ancho, alto):
    pts = [App.Vector(x, cy - ancho/2, cz - alto/2),
           App.Vector(x, cy + ancho/2, cz - alto/2),
           App.Vector(x, cy + ancho/2, cz + alto/2),
           App.Vector(x, cy - ancho/2, cz + alto/2)]
    pts.append(pts[0])
    return Part.Wire(Part.makePolygon(pts).Edges)

boca_usbc = Part.makeLoft([rect_wire_x(-W/2 - 3.0, usb_centro_y, usb_cz, 18.0, 13.0),
                           rect_wire_x(-W/2 + 7.0, usb_centro_y, usb_cz, usb_ancho, usb_alto)], True)
cuerpo = cuerpo.cut(boca_usbc)

# Torretas para la senseBox MCU: la placa NO tiene taladros en las esquinas.
# Según el .brd oficial lleva 2 taladros M3 en (±24.5, +29): dos torretas
# roscables ahí, y dos torretas lisas de apoyo bajo el borde opuesto (la cara
# inferior de la placa solo tiene serigrafía, se puede apoyar donde haga falta).
# Los taladros de 2.5 mm en (±11, +32) quedan libres (opcional: pines de registro).
puntos_m3_sb = [
    (-24.5, desfase_y_mcu + 29.0),
    ( 24.5, desfase_y_mcu + 29.0),
]
puntos_apoyo_sb = [
    (-24.5, desfase_y_mcu - 29.0),
    ( 24.5, desfase_y_mcu - 29.0),
]

for px, py in puntos_m3_sb:
    torreta = Part.makeCylinder(3.5, 4.0, App.Vector(px, py, grosor_base))
    agujero = Part.makeCylinder(1.4, 6.0, App.Vector(px, py, grosor_base))
    torreta = torreta.cut(agujero)
    cuerpo = cuerpo.fuse(torreta)

for px, py in puntos_apoyo_sb:
    cuerpo = cuerpo.fuse(Part.makeCylinder(3.5, 4.0, App.Vector(px, py, grosor_base)))

# ============================================================
# 2. RAÍLES GUÍA CONTINUOS (DE PARED A PARED)
# ============================================================
rail_ancho = 4.0
rail_largo_total = W * 0.85 # Atraviesa toda la longitud interna en X
rail_alto = 3.5
z_rail = grosor_base + z_separacion
sep_y = df_ancho / 2.0 - 2.0  # la placa del sensor solapa 2 mm sobre cada raíl para apoyarse

# Raíles continuos a todo lo largo
rail_1 = Part.makeBox(rail_largo_total, rail_ancho, rail_alto, App.Vector(-rail_largo_total/2,  sep_y, z_rail))
rail_2 = Part.makeBox(rail_largo_total, rail_ancho, rail_alto, App.Vector(-rail_largo_total/2, -sep_y - rail_ancho, z_rail))

# Tope trasero para que la placa del sensor quede encajada exactamente en su sitio
tope_pos_x = df_largo / 2.0
tope = Part.makeBox(3.0, df_ancho + 2*rail_ancho, rail_alto + 4.0, App.Vector(tope_pos_x, -sep_y - rail_ancho, z_rail))

# Tope delantero espejado: el sensor entra desde arriba (drop-in) y queda
# cautivo entre ambos topes con 0.3 mm de juego; sin él podía deslizarse
# hacia -x y salirse de los raíles
tope_delantero = Part.makeBox(3.0, df_ancho + 2*rail_ancho, rail_alto + 4.0,
                              App.Vector(-df_largo/2.0 - 0.3 - 3.0, -sep_y - rail_ancho, z_rail))

# Recorte de la unión para que solo se fusionen con las paredes internas
railes_completos = rail_1.fuse(rail_2).fuse(tope).fuse(tope_delantero)
railes_limpios = railes_completos.common(cavidad) # Mantiene solo la parte interna

cuerpo = cuerpo.fuse(railes_limpios)

# ============================================================
# 3. TAPA CON REGISTRO DE MICRÓFONO
# ============================================================
perfiles = [
    (1.00, altura_carcasa),
    (0.95, altura_carcasa + 1.0),
    (0.80, altura_carcasa + 3.0),
    (0.55, altura_carcasa + 4.8),
    (0.25, altura_carcasa + altura_domo),
]

wires = [crear_wire_perfil(contorno, factor_x, z) for factor_x, z in perfiles]
tapa = Part.makeLoft(wires, True, False)

pos_mic_x = -df_largo/2 + 2.0 
pos_mic_y = 0.0

agujero_mic = Part.makeCylinder(
    3.0,
    altura_domo + 10.0,
    App.Vector(pos_mic_x, pos_mic_y, altura_carcasa - 1),
    App.Vector(0, 0, 1)
)

tapa = tapa.cut(agujero_mic)

# ---- Falda de registro + cierre a presión ----
# La tapa solo apoyaba sobre el borde: nada la registraba en XY ni impedía
# que se levantara. Una falda interior entra en la cavidad y cuatro resaltes
# semiesféricos encajan en huecos de la pared interior (cierre sin tornillos).
falda_alto = 4.0
grosor_falda = 2.0
holgura_falda = 0.4  # holgura radial falda-pared; la distancia mínima del contorno al origen es ~55 mm
falda_ext = factor_interior - holgura_falda / 55.0
falda_int = falda_ext - grosor_falda / 55.0

falda = crear_prisma([(x * falda_ext, y * falda_ext) for x, y in contorno],
                     altura_carcasa - falda_alto, falda_alto)
falda = falda.cut(crear_prisma([(x * falda_int, y * falda_int) for x, y in contorno],
                               altura_carcasa - falda_alto - 1.0, falda_alto + 2.0))
tapa = tapa.fuse(falda)

z_cierre = altura_carcasa - falda_alto + 1.5
for idx in (1, 3, 9, 11):  # dos resaltes por lado, en vértices del contorno
    vx, vy = contorno[idx]
    r = math.hypot(vx, vy)
    ux, uy = vx / r, vy / r
    # centro sobre la pared interior de la cavidad, retraído 1 mm hacia dentro:
    # el resalte sobresale 0.5 mm de la falda hacia la pared y el hueco (r+0.1)
    # lo recibe con holgura, de modo que montada la tapa no hay interferencia
    cx = vx * factor_interior - ux * 1.0
    cy = vy * factor_interior - uy * 1.0
    resalte = Part.makeSphere(1.5, App.Vector(cx, cy, z_cierre))
    hueco = Part.makeSphere(1.6, App.Vector(cx, cy, z_cierre))
    tapa = tapa.fuse(resalte)
    cuerpo = cuerpo.cut(hueco)

# ============================================================
# 4. COMPONENTES VIRTUALES DE REFERENCIA
# ============================================================
ref_sensebox = Part.makeBox(
    sb_largo, sb_ancho, sb_alto,
    App.Vector(-sb_largo/2, desfase_y_mcu - sb_ancho/2, grosor_base + 4.0)
)

ref_dfrobot = Part.makeBox(
    df_largo, df_ancho, df_alto,
    App.Vector(-df_largo/2, -df_ancho/2, z_rail + rail_alto)
)

# ============================================================
# 5. MOSTRAR EN FREECAD
# ============================================================
crear_objeto("Caja_Base_Ampliada", cuerpo, (0.18, 0.48, 0.20))
crear_objeto("Tapa_Hoja_Ampliada", tapa, (0.28, 0.62, 0.25), transparencia=45)

crear_objeto("REF_senseBox_MCU", ref_sensebox, (0.25, 0.25, 0.25))
crear_objeto("REF_DFRobot_SoundMeter", ref_dfrobot, (0.10, 0.40, 0.80))

doc.recompute()
Gui.activeDocument().activeView().viewAxonometric()
Gui.activeDocument().activeView().fitAll()