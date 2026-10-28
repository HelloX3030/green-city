import FreeCAD as App
import Part
import math

# ============================================================
# CARCASA HOJA - CARRO DE RAÍLES SUELTO ENCAJADO EN LA PARED
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

# -- Constantes compartidas (varias secciones dependen de ellas) --
dist_min_contorno = 55.0   # distancia mínima del contorno al origen (en los
                           # vértices +-x); convierte holguras radiales en mm a
                           # factores de escala homotéticos: f = 1 +- h / dist
alto_torreta = 4.0         # las placas apoyan a grosor_base + alto_torreta
r_torreta_m3 = 4.0         # torreta M3 con boca para inserto roscado
r_boca_inserto = 2.0       # boca Ø4.0 x 4.5 para inserto M3 (p. ej. Ruthex M3 x 5.7)
prof_boca_inserto = 4.5
r_piloto = 1.4             # piloto Ø2.8: un M3 autorroscante agarra sin inserto
r_media_cana = 3.0         # media caña pared-suelo (refuerzo)
chaflan_inferior = 0.5     # chaflán anti "pata de elefante" en el canto inferior
prof_surco = 0.8           # profundidad de las nervaduras grabadas en el domo

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

# Contorno suave: B-spline periódica que pasa por los 12 puntos del contorno.
# Como la interpolación conmuta con escalados afines, todas las curvas
# escaladas (cavidad, falda, perfiles del domo) siguen siendo homotéticas y
# las holguras calculadas en los vértices se conservan exactamente.
def wire_contorno(puntos, z, fx=1.0, fy=1.0):
    pts = [App.Vector(x * fx, y * fy, z) for x, y in puntos]
    curva = Part.BSplineCurve()
    curva.interpolate(Points=pts, PeriodicFlag=True)
    return Part.Wire([curva.toShape()])

def crear_prisma(puntos, z, altura):
    return Part.Face(wire_contorno(puntos, z)).extrude(App.Vector(0, 0, altura))

def crear_objeto(nombre, forma, color, transparencia=0):
    obj = doc.addObject("Part::Feature", nombre)
    obj.Shape = forma
    if App.GuiUp:  # en freecadcmd (headless) no hay ViewObject
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.Transparency = transparencia
    return obj

def crear_wire_perfil(puntos, factor_x, z):
    return wire_contorno(puntos, z, fx=factor_x)

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
    torreta = Part.makeCylinder(r_torreta_m3, alto_torreta, App.Vector(px, py, grosor_base))
    cuerpo = cuerpo.fuse(torreta)
    # Boca para inserto roscado; debajo sigue el piloto, que deja 1 mm de
    # suelo. Sin insertos, un tornillo M3 autorroscante agarra igualmente.
    boca_inserto = Part.makeCylinder(r_boca_inserto, 6.0,
                                     App.Vector(px, py, grosor_base + alto_torreta - prof_boca_inserto))
    piloto = Part.makeCylinder(r_piloto, 6.0, App.Vector(px, py, 1.0))
    cuerpo = cuerpo.cut(boca_inserto).cut(piloto)

for px, py in puntos_apoyo_sb:
    cuerpo = cuerpo.fuse(Part.makeCylinder(3.5, alto_torreta, App.Vector(px, py, grosor_base)))

# ============================================================
# 2. CARRO DE RAÍLES (pieza suelta que entra desde arriba)
# ============================================================
# Los raíles ya no van fusionados a la caja: son UNA pieza aparte (los dos
# raíles unidos por los topes delantero y trasero, fondo plano: se imprime
# sin soportes) que se desliza en la caja desde arriba. Los extremos de los
# raíles se prolongan 2 mm dentro de la pared, y la pared lleva cuatro
# ranuras verticales (divots) desde el borde superior hasta z_rail que los
# reciben: el fondo de cada ranura soporta el carro a su altura y los
# flancos lo fijan en planta.
rail_ancho = 4.0
rail_alto = 3.5
z_rail = grosor_base + z_separacion
sep_y = df_ancho / 2.0 - 2.0  # la placa del sensor solapa 2 mm sobre cada raíl para apoyarse

prof_divot = 2.0     # prolongación del extremo del raíl dentro de la pared
holgura_divot = 0.3  # holgura por cara raíl-ranura para que deslice

# Factores homotéticos: fin del raíl y fondo de la ranura, medidos desde la
# pared interior (factor_interior) hacia fuera
f_fin_rail = factor_interior + prof_divot / dist_min_contorno
f_divot = factor_interior + (prof_divot + holgura_divot) / dist_min_contorno

largo_barra = W + 20.0  # sobra por ambos lados; el common() lo recorta

rail_1 = Part.makeBox(largo_barra, rail_ancho, rail_alto, App.Vector(-largo_barra/2,  sep_y, z_rail))
rail_2 = Part.makeBox(largo_barra, rail_ancho, rail_alto, App.Vector(-largo_barra/2, -sep_y - rail_ancho, z_rail))

# Topes trasero y delantero: fijan el sensor en x (drop-in con 0.3 mm de
# juego) y a la vez son los travesaños que unen los dos raíles en una pieza
tope_pos_x = df_largo / 2.0
tope = Part.makeBox(3.0, df_ancho + 2*rail_ancho, rail_alto + 4.0, App.Vector(tope_pos_x, -sep_y - rail_ancho, z_rail))
tope_delantero = Part.makeBox(3.0, df_ancho + 2*rail_ancho, rail_alto + 4.0,
                              App.Vector(-df_largo/2.0 - 0.3 - 3.0, -sep_y - rail_ancho, z_rail))

carro = rail_1.fuse(rail_2).fuse(tope).fuse(tope_delantero)
# Recorte en planta: los extremos acaban prof_divot por dentro de la pared
carro = carro.common(crear_prisma([(x * f_fin_rail, y * f_fin_rail) for x, y in contorno],
                                  grosor_base, altura_carcasa))

# Ranuras verticales en la pared, del borde superior al fondo en z_rail. El
# cortador es la barra completa (holgada) limitada a la planta del divot:
# fuera de la pared solo atraviesa el aire de la cavidad. En z no toca nada
# más (la boca USB acaba en z=16.5, los huecos del cierre quedan a >5 mm en
# planta de las bandas de los raíles).
contorno_divot = [(x * f_divot, y * f_divot) for x, y in contorno]
for y0 in (sep_y, -sep_y - rail_ancho):
    barra = Part.makeBox(largo_barra, rail_ancho + 2*holgura_divot,
                         altura_carcasa - z_rail + 2.0,
                         App.Vector(-largo_barra/2, y0 - holgura_divot, z_rail))
    cuerpo = cuerpo.cut(barra.common(crear_prisma(contorno_divot, z_rail,
                                                  altura_carcasa - z_rail + 2.0)))

# ============================================================
# 2a. REFUERZOS (media caña interior y chaflán inferior)
# ============================================================
# Media caña pared-suelo r~3: cuña perimetral cuyo flanco interior es un
# loft de 3 perfiles sobre la cuerda del cuadrante (puntos del arco a 0°,
# 45° y 90°). Refuerza la unión más cargada y evita la grieta de esquina.
# El perfil superior rebasa 0.3 mm dentro de la pared para que el corte y
# la fusión no dejen caras coincidentes.
cunna_molde = crear_prisma(contorno_interior, grosor_base, r_media_cana)
cunna_nucleo = Part.makeLoft(
    [wire_contorno(contorno, grosor_base,
                   factor_interior - r_media_cana/dist_min_contorno,
                   factor_interior - r_media_cana/dist_min_contorno),
     wire_contorno(contorno, grosor_base + 0.88,
                   factor_interior - 0.88/dist_min_contorno,
                   factor_interior - 0.88/dist_min_contorno),
     wire_contorno(contorno, grosor_base + 5.8,
                   factor_interior + 0.3/dist_min_contorno,
                   factor_interior + 0.3/dist_min_contorno)],
    True, False)
cuerpo = cuerpo.fuse(cunna_molde.cut(cunna_nucleo))

# Chaflán de 0.5 mm en el canto inferior exterior: compensa la pata de
# elefante de la primera capa y la caja asienta plana aunque el borde rebose.
f_chaflan = 1.0 - chaflan_inferior / dist_min_contorno
chaflan_molde = crear_prisma(contorno, -chaflan_inferior, 2 * chaflan_inferior)
chaflan_nucleo = Part.makeLoft(
    [wire_contorno(contorno, -chaflan_inferior, f_chaflan, f_chaflan),
     wire_contorno(contorno, 0.0, f_chaflan, f_chaflan),
     wire_contorno(contorno, chaflan_inferior, 1.001, 1.001)], True, False)
cuerpo = cuerpo.cut(chaflan_molde.cut(chaflan_nucleo))

# (v2, feedback del impreso: fuera el peciolo y fuera los agujeros del
# suelo — ojales keyhole, ranuras de brida y drenajes. La base queda ciega.)

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
holgura_falda = 0.4  # holgura radial falda-pared
falda_ext = factor_interior - holgura_falda / dist_min_contorno
falda_int = falda_ext - grosor_falda / dist_min_contorno

# Vaciado del domo: la tapa era un bloque macizo de plástico. Se resta un loft
# interior con los mismos perfiles, escalado en planta al borde interior de la
# falda (falda_int) y comprimido en z para dejar ~2.5 mm de pared en lo alto;
# el borde de apoyo queda macizo y la falda continúa la pared interior del domo.
contorno_falda_int = [(x * falda_int, y * falda_int) for x, y in contorno]
escala_z_vaciado = (altura_domo - 2.5) / altura_domo
wires_vaciado = [crear_wire_perfil(contorno_falda_int, f,
                                   altura_carcasa + (z - altura_carcasa) * escala_z_vaciado)
                 for f, z in perfiles]
vaciado = Part.makeLoft(wires_vaciado, True, False)
tapa = tapa.cut(vaciado)

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

# ---- Capucha del micrófono (intemperie) ----
# Chimenea sobre el orificio del mic con sombrerete cónico: la lluvia
# vertical cae sobre el cono y escurre fuera del tubo; el sonido entra por
# la boca lateral, orientada hacia fuera (-x) y a cubierto bajo el alero del
# sombrerete. El fondo del tubo queda 0.8 mm por debajo de la boca (umbral
# anti-salpicaduras). Recomendado en montaje real: pegar una malla acústica
# hidrófuga (p. ej. Saati Acoustex, Gore) bajo el sombrerete o sobre el
# orificio para sellar contra insectos y agua pulverizada.
tubo_mic = Part.makeCylinder(5.5, 5.0, App.Vector(pos_mic_x, pos_mic_y, altura_carcasa + 4.0))
tubo_mic = tubo_mic.cut(Part.makeCylinder(3.8, 5.0, App.Vector(pos_mic_x, pos_mic_y, altura_carcasa + 4.0)))
sombrerete = Part.makeCone(6.5, 1.5, 4.2, App.Vector(pos_mic_x, pos_mic_y, altura_carcasa + 8.5))
tapa = tapa.fuse(tubo_mic).fuse(sombrerete)
boca_capucha = Part.makeBox(10.2, 6.0, 2.5,
                            App.Vector(pos_mic_x - 12.0, pos_mic_y - 3.0, altura_carcasa + 5.8))
tapa = tapa.cut(boca_capucha)

# ---- Alero perimetral (goterón) ----
# El borde de la tapa vuela ~1.5 mm sobre la pared en todo el perímetro: el
# agua que escurre por el domo gotea fuera de la junta tapa-cuerpo en vez de
# entrar por capilaridad. Banda vertical de 0.6 mm y chaflán que remata
# contra la superficie del domo (el domo solo escala en x, por eso el perfil
# superior usa factores x/y distintos para enterrarse justo bajo él).
def wire_xy(fx, fy, z):
    return wire_contorno(contorno, z, fx=fx, fy=fy)

f_alero = 1.0 + 1.5 / dist_min_contorno  # ~1.5 mm de vuelo radial
alero = Part.makeLoft([wire_xy(f_alero, f_alero, altura_carcasa),
                       wire_xy(f_alero, f_alero, altura_carcasa + 0.6),
                       wire_xy(0.89, 0.995, altura_carcasa + 1.7)], True)
tapa = tapa.fuse(alero)
# el loft del alero es un sólido de sección completa, no un anillo: se vuelve
# a restar el vaciado para que no rellene el domo hueco ni tape el mic
tapa = tapa.cut(vaciado)

# ---- Nervaduras grabadas (surcos de 0.8 mm) ----
# Nervio central partido en dos tramos (deja libre la zona del rebaje QR) y
# cinco pares de nervios laterales a 35° hacia el ápice, como una hoja real.
# Cada lámina fina se recorta a la franja de 0.8 mm bajo la superficie
# (tapa menos tapa desplazada -0.8 en z), de modo que el surco sigue el domo
# con profundidad constante y se desvanece solo al llegar a las paredes
# verticales. Posiciones elegidas para no tocar la capucha del mic.
nervios = [Part.makeBox(1.2, 69.0, 11.0, App.Vector(-0.6, -64.0, 29.0)),
           Part.makeBox(1.2, 29.0, 11.0, App.Vector(-0.6, 35.0, 29.0))]
for y_nervio, largo_nervio in [(-50.0, 38.0), (-30.0, 42.0), (-6.0, 45.0),
                               (38.0, 35.0), (50.0, 18.0)]:
    for ang in (35.0, 145.0):
        lamina = Part.makeBox(largo_nervio, 1.2, 11.0,
                              App.Vector(0, y_nervio - 0.6, 29.0))
        lamina.rotate(App.Vector(0, y_nervio, 0), App.Vector(0, 0, 1), ang)
        nervios.append(lamina)
laminas = nervios[0]
for n in nervios[1:]:
    laminas = laminas.fuse(n)
tapa_bajada = tapa.copy()
tapa_bajada.translate(App.Vector(0, 0, -prof_surco))
surcos = laminas.common(tapa).cut(tapa_bajada)
tapa = tapa.cut(surcos)

# ---- Rebaje QR (flujo de despliegue de la app) ----
# Cajeado de 25 x 25 x 0.6 en la meseta plana del domo para una pegatina QR
# laminada (la que escanea la app al desplegar el sensor): el rebaje la
# protege del roce y la deja enrasada. Para impresión a dos colores: pausa /
# cambio de filamento en z = 34.9 y las nervaduras + el marco del QR quedan
# en color contraste.
rebaje_qr = Part.makeBox(25.0, 25.0, 2.0,
                         App.Vector(-12.5, 7.5, altura_carcasa + altura_domo - 0.6))
tapa = tapa.cut(rebaje_qr)

# ============================================================
# 3b. TAPÓN USB-C IMPRIMIBLE (pieza suelta)
# ============================================================
# Tapón a fricción para la boca USB cuando no hay cable conectado: cono con
# la misma conicidad que la boca abocinada menos 0.3 mm de holgura por lado,
# espiga que sigue el túnel de 13 x 8 y placa-tirador exterior para sacarlo.
# Se imprime aparte; aquí se modela ya asentado en su posición.
tapon = Part.makeLoft([rect_wire_x(-W/2 - 2.5, usb_centro_y, usb_cz, 17.15, 12.15),
                       rect_wire_x(-W/2 + 6.5, usb_centro_y, usb_cz, 12.65, 7.65)], True)
espiga = Part.makeBox(10.0, 12.4, 7.4,
                      App.Vector(-W/2 + 6.0, usb_centro_y - 6.2, usb_cz - 3.7))
tirador = Part.makeBox(1.7, 10.0, 14.0,
                       App.Vector(-W/2 - 4.2, usb_centro_y - 5.0, usb_cz - 7.0))
tapon = tapon.fuse(espiga).fuse(tirador)

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
crear_objeto("Carro_Railes", carro, (0.85, 0.75, 0.30))
crear_objeto("Tapon_USB", tapon, (0.80, 0.60, 0.20))

crear_objeto("REF_senseBox_MCU", ref_sensebox, (0.25, 0.25, 0.25))
crear_objeto("REF_DFRobot_SoundMeter", ref_dfrobot, (0.10, 0.40, 0.80))

doc.recompute()

if App.GuiUp:
    import FreeCADGui as Gui
    Gui.activeDocument().activeView().viewAxonometric()
    Gui.activeDocument().activeView().fitAll()