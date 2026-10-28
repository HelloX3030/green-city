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

# 1. senseBox MCU S2 (Base)
sb_largo = 78.0
sb_ancho = 72.0
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
altura_carcasa = z_separacion + df_alto + 6.0
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
# con la abertura a 36 mm de una esquina y 26 mm de la otra, 10 mm de ancho
# (ver 3d-model/measurements). El túnel atraviesa toda la pared izquierda.
usb_ancho = 10.0
usb_alto = 7.0
usb_y0 = -sb_ancho/2 + desfase_y_mcu + 36.0   # 36 mm desde la esquina de la placa
usb_z0 = grosor_base + 4.0    # la placa apoya sobre torretas de 4 mm

tunel_usbc = Part.makeBox(
    35.0, usb_ancho, usb_alto,
    App.Vector(-W/2 - 5.0, usb_y0, usb_z0)
)

cuerpo = cuerpo.cut(tunel_usbc)

# Standoffs base (Fijación M3) para senseBox MCU
puntos_m3_sb = [
    (-sb_largo/2 + 5, desfase_y_mcu - sb_ancho/2 + 5),
    ( sb_largo/2 - 5, desfase_y_mcu - sb_ancho/2 + 5),
    (-sb_largo/2 + 5, desfase_y_mcu + sb_ancho/2 - 5),
    ( sb_largo/2 - 5, desfase_y_mcu + sb_ancho/2 - 5)
]

for px, py in puntos_m3_sb:
    torreta = Part.makeCylinder(3.5, 4.0, App.Vector(px, py, grosor_base))
    agujero = Part.makeCylinder(1.4, 6.0, App.Vector(px, py, grosor_base))
    torreta = torreta.cut(agujero)
    cuerpo = cuerpo.fuse(torreta)

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

# Recorte de la unión para que solo se fusionen con las paredes internas
railes_completos = rail_1.fuse(rail_2).fuse(tope)
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