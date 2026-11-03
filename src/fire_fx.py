"""
src/fire_fx.py  ─  Efectos visuales de disparo.

Qué hace este archivo
─────────────────────
Cuando Snake dispara, acá se crean tres cosas al mismo tiempo:

  1. Sprite de fuego animado   → el M16 cambia su sprite normal por uno con llama
                                  mientras Snake está disparando. Si camina, el ciclo
                                  de piernas se sincroniza con el de disparo.

  2. Destello + humo           → flash y nubecita gráficas en la boca del cañón.
                                  Están dibujados con código, sin imágenes extra.

  3. Casquillo                 → el pequeño tubo dorado que sale expulsado hacia un
                                  costado. Tiene física: gravedad, rebote, y queda en
                                  el piso hasta desaparecer.

Cómo se usa desde el resto del código
──────────────────────────────────────
  fx = FireFX()                            # al iniciar el juego (o la misión)

  # Cada vez que Snake dispara:
  fx.on_shot(player, "m16")

  # Cada frame:
  fx.update(dt)
  fx.draw(virtual_surface, camera)

  # Para saber qué sprite de fuego mostrar en lugar del sprite normal de Snake:
  img = fx.get_fire_image("m16", player.facing, player.is_moving, player.frame_index)
  if img:
      surface.blit(img, ...)   # reemplazá el sprite normal de Snake con éste

  # Al reiniciar la misión:
  fx.clear()
"""

import math
import os
import random

import pygame

# Vectores unitarios por dirección: usados para calcular hacia dónde
# apunta el destello en pantalla.
_DIRS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN DE CASQUILLOS
#  ─────────────────────────────────────────────────────────────────────────────
#  Todo lo que controla el comportamiento de los casquillos está acá arriba.
#  El resto del código no hay que tocarlo para ajustar esto.
# ══════════════════════════════════════════════════════════════════════════════

# ── Generales ────────────────────────────────────────────────────────────────
CASINGS_ENABLED = True   # False → ningún arma suelta casquillos
DEBUG_CASINGS   = False  # True  → muestra dónde nació el último casquillo
                          #         (punto magenta) y dónde está el "suelo" de
                          #         cada uno (rayita roja).
                          #         Cambiar a False al terminar de calibrar.

CASING_MAX       = 40    # Cuántos casquillos puede haber en pantalla a la vez.
                          # Si se supera, desaparece el más viejo.
CASING_LIFE      = 3.5   # Segundos que dura cada casquillo (vuelo + tiempo en
                          # el piso).
CASING_FADE_TIME = 1.0   # De esos segundos, los últimos CASING_FADE_TIME se
                          # desvanece gradualmente hasta transparente.
CASING_SIZE      = (4, 2)           # Ancho y alto del casquillo en píxeles
                                     # (del mundo, antes del escalado x2).
CASING_COLOR_AIR    = (218, 165, 32)  # Color mientras vuela (dorado brillante).
CASING_COLOR_GROUND = (184, 134, 11)  # Color cuando ya está en el piso
                                       # (más oscuro y apagado).

# ── Física ───────────────────────────────────────────────────────────────────
CASING_GRAVITY = 300.0   # px/s² hacia abajo. Más alto → cae más rápido.
CASING_SPIN    = (-400.0, 400.0)  # Rango de velocidad de rotación en
                                   # grados/segundo (negativo = gira a la
                                   # izquierda, positivo = a la derecha).
                                   # El valor exacto se sortea al azar en
                                   # ese rango para cada casquillo.

CASING_BOUNCES         = 3     # Cuántas veces rebota antes de quedarse quieto.
                                 # 0 → se clava al tocar el suelo.
CASING_BOUNCE_DAMPING  = 0.35  # Qué fracción de la velocidad vertical conserva
                                 # al rebotar. 0 → no rebota nada; 1 → rebota
                                 # igual de alto que cayó (sin pérdida).
CASING_BOUNCE_FRICTION = 0.50  # Qué fracción de la velocidad horizontal y del
                                 # giro conserva en cada rebote.
CASING_MIN_BOUNCE_SPEED = 25.0 # Si al rebotar la velocidad resultante sería
                                 # menor que esto (px/s), ya no rebota y se
                                 # queda en el suelo.

# ── De dónde sale el casquillo ────────────────────────────────────────────────
# (x, y) en píxeles desde el CENTRO del rect de Snake, según la dirección.
# x positivo → a la derecha de Snake.  y negativo → hacia arriba (el torso).
# Hay una entrada "default" que vale para todas las armas; si querés un
# origen distinto por arma, agregá una entrada con el nombre del sprite_set
# del arma ("m16", "gun", "stinger") copiando el formato de "default".
CASING_ORIGIN = {
    "default": {
        "UP":    ( 0, -4),
        "DOWN":  ( 0, -4),
        "LEFT":  ( 0, -4),
        "RIGHT": ( 0, -4),
    },
    # Ejemplo para el M16 (descomentá y editá):
    "m16": {"UP": (-2, -45), "DOWN": (-4, -35), "LEFT": (-4, -38), "RIGHT": (4, -38)},
}

# ── Con cuánta fuerza y cuánto cae ────────────────────────────────────────────
# Por cada dirección en la que mira Snake.
# Cada valor es (mínimo, máximo): el número exacto se sortea al azar.
#
#   vx   → velocidad horizontal inicial (px/s).
#            Positivo = hacia la derecha.  Negativo = hacia la izquierda.
#   vy   → velocidad vertical inicial (px/s).
#            Negativo = sube.  Más negativo → sube más antes de caer.
#   fall → cuántos píxeles por DEBAJO del punto de origen está el "suelo"
#            (cuánto recorre en vertical antes de chocar con el piso).
#            Mínimo 0.  Más grande → aterriza más lejos en pantalla.
CASING_EJECT = {
    "RIGHT": dict(vx=(-40, -20), vy=(-70, -40), fall=(30, 40)),
    "LEFT":  dict(vx=( 20,  40), vy=(-70, -40), fall=(30, 40)),
    "UP":    dict(vx=( 30,  60), vy=(-40, -10), fall=( 10, 20)),
    "DOWN":  dict(vx=(-60, -30), vy=(-40, -10), fall=( 15, 25)),
}

# ── Por arma ─────────────────────────────────────────────────────────────────
# enabled → False = esa arma no suelta casquillos.
# force   → multiplica vx y vy de CASING_EJECT.
#            1.0 = normal, 2.0 = doble de fuerza, 0.5 = más flojo.
CASING_WEAPONS = {
    "m16":     dict(enabled=True,  force=2.0),
    "beretta": dict(enabled=True,  force=0.8),
    "uzi":     dict(enabled=True,  force=1.0),
    "stinger": dict(enabled=False, force=0.0),  # el Stinger no suelta casquillos
}
# Valor por defecto para cualquier arma que no esté en la lista de arriba.
CASING_WEAPON_DEFAULT = dict(enabled=True, force=1.0)

# Cuántos grados de diferencia se aceptan en el caché de rotaciones.
# Si lo subís, hay menos calidad visual pero más rendimiento.
_CASING_ROT_STEP = 15


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN DE LA BOCA DEL CAÑÓN Y DEL DESTELLO
# ══════════════════════════════════════════════════════════════════════════════

# Posición de la boca del cañón por arma y por dirección,
# x positivo → a la derecha de Snake.  y negativo → hacia arriba (el torso).
# en píxeles desde el CENTRO del rect de Snake.
_MUZZLE = {
    "m16":     {"DOWN": ( 0, -2), "UP": ( 0, -50), "LEFT": (-35, -38), "RIGHT": (35, -38)},
    "gun":     {"DOWN": ( 5,  -9), "UP": (-5, -24), "LEFT": (-16, -14), "RIGHT": (16, -14)},
    "stinger": {"DOWN": ( 0,  -8), "UP": ( 0, -26), "LEFT": (-22, -14), "RIGHT": (22, -14)},
}
_MUZZLE_DEFAULT = {"DOWN": (5, -10), "UP": (-5, -24), "LEFT": (-16, -14), "RIGHT": (16, -14)}

# Tamaño del destello y el humo por arma.
# 0.0 → sin destello (el Stinger, por ejemplo).
_FX_SIZE = {
    "m16":     1.00,
    "beretta": 0.65,
    "uzi":     0.70,
    "gun":     0.70,
    "stinger": 0.00,
}

# Arma → set de sprites de Snake. La Beretta y la UZI usan el mismo
# set "gun"; el M16 tiene el suyo propio.
_SPRITE_SET = {
    "beretta": "gun",
    "uzi":     "gun",
    "m16":     "m16",
    "stinger": "stinger",
}


def _sprite_set_of(weapon_id):
    """Devuelve el nombre del set de sprites para un id de arma dado."""
    return _SPRITE_SET.get(weapon_id, weapon_id)


# ══════════════════════════════════════════════════════════════════════════════
#  ANIMACIÓN DEL SPRITE DE DISPARO (M16)
# ══════════════════════════════════════════════════════════════════════════════
class _FireAnim:
    """
    Maneja los sprites del M16 (u otra arma con el mismo esquema) mientras dispara.

    Dos modos:
      • Quieto disparando → muestra un único sprite de fuego estático por dirección.
      • Caminando disparando → cicla entre cuatro sprites sincronizados con el
                                ciclo de caminata de Snake.

    Esquema de nombres esperado para los archivos PNG
    ──────────────────────────────────────────────────
    Reemplazá "m16_fire" por el prefijo que uses (p.ej. "m16_fire"):

    Quieto disparando   :  m16_fire_down.png       (sin número)
    Caminando disparando:  m16_fire_down2.png  ← posición "de pie"   (= stand)
                           m16_fire_down3.png  ← paso de pierna 1    (= walk1)
                           m16_fire_down4.png  ← paso de pierna 2    (= walk2)

    El ciclo de caminata es: 2 → 3 → 2 → 4   (igual que el ciclo normal de Snake)
    Se repite para up, left y right (con los números 2, 3, 4 iguales).

    GAP (segundos)
    ──────────────
    Es el tiempo que tiene que pasar SIN disparar para que el sprite de fuego
    "se apague" y Snake vuelva a su sprite normal.
    Tiene que ser mayor que el intervalo más largo entre disparos, si no,
    el sprite se apaga entre ráfagas y "parpadea".
    Ejemplo: M16 en auto dispara cada 0,10 s; en ráfaga tiene una pausa de 0,28 s
    → GAP = 0,32 s cubre ambos casos.
    """

    GAP = 0.32   # segundos sin disparar antes de volver al sprite normal

    def __init__(self, folder, prefix, scale=2):
        # _since_last arranca en GAP para que empiece "apagado"
        self._since_last = self.GAP
        self._still: dict = {}   # {facing: Surface}  → sprite quieto
        self._walk:  dict = {}   # {facing: [f2, f3, f2, f4]}  → ciclo caminando
        self._load_all(folder, prefix, scale)

    # ── carga de sprites ──────────────────────────────────────────────────────
    def _load_all(self, folder, prefix, scale):
        def load(path):
            img = pygame.image.load(path).convert_alpha()
            w = int(img.get_width()  * scale)
            h = int(img.get_height() * scale)
            return pygame.transform.scale(img, (w, h))

        for facing in ("DOWN", "UP", "LEFT", "RIGHT"):
            # Los nombres de archivo usan minúsculas (down, up, left, right).
            d = facing.lower()

            # ── Sprite quieto ──────────────────────────────────────────────────
            # Nombre esperado: <prefix>_<dirección>.png
            # Ejemplo:         m16_fire_down.png
            still_path = os.path.join(folder, f"{prefix}_{d}.png")
            if os.path.exists(still_path):
                try:
                    self._still[facing] = load(still_path)
                except Exception as e:
                    print(f"[FireFX] Error cargando {still_path}: {e}")
            else:
                # Aviso sin crashear: el juego sigue funcionando sin ese sprite.
                print(f"[FireFX] Aviso: falta '{prefix}_{d}.png' en '{folder}'")

            # ── Sprites de caminata ────────────────────────────────────────────
            # Nombres esperados: <prefix>_<dirección>2.png  (stand)
            #                    <prefix>_<dirección>3.png  (walk1)
            #                    <prefix>_<dirección>4.png  (walk2)
            walk_paths = [
                os.path.join(folder, f"{prefix}_{d}2.png"),
                os.path.join(folder, f"{prefix}_{d}3.png"),
                os.path.join(folder, f"{prefix}_{d}4.png"),
            ]
            if all(os.path.exists(p) for p in walk_paths):
                try:
                    f2, f3, f4 = [load(p) for p in walk_paths]
                    # Ciclo: stand → walk1 → stand → walk2
                    self._walk[facing] = [f2, f3, f2, f4]
                except Exception as e:
                    print(f"[FireFX] Error cargando sprites de caminata '{prefix}_{d}2/3/4': {e}")
            # Si no existen los tres, _walk[facing] queda vacío y
            # get_image() usará el sprite quieto como fallback.

    # ── API ───────────────────────────────────────────────────────────────────
    def trigger(self):
        """Llamar una vez por cada bala disparada para "activar" el sprite de fuego."""
        self._since_last = 0.0

    def update(self, dt):
        """Avanzar el temporizador de "apagado". Llamar cada frame."""
        self._since_last += dt

    def active(self):
        """Devuelve True si Snake sigue disparando (no pasó GAP desde el último disparo)."""
        return self._since_last < self.GAP

    def get_image(self, facing, is_moving=False, frame_index=0):
        """
        Devuelve el frame del sprite de fuego que corresponde al estado actual,
        o None si el arma no está disparando.

        facing      → player.facing
        is_moving   → player.is_moving
        frame_index → player.frame_index  (sincroniza el ciclo de piernas)
        """
        if not self.active():
            return None   # Snake ya no está disparando → sprite normal

        if is_moving and facing in self._walk:
            # Modo caminando: usar el ciclo [f2, f3, f2, f4] sincronizado
            # con el mismo frame_index que usa el sprite normal de caminata.
            frames = self._walk[facing]
            return frames[frame_index % len(frames)]

        # Modo quieto (o sin sprite de caminata): sprite estático con llama.
        return self._still.get(facing)


# ══════════════════════════════════════════════════════════════════════════════
#  CASQUILLOS CON FÍSICA
# ══════════════════════════════════════════════════════════════════════════════
class _CasingPool:
    """
    Gestiona todos los casquillos en pantalla.

    Ciclo de vida de un casquillo
    ─────────────────────────────
    1. Nace en CASING_ORIGIN con velocidad inicial de CASING_EJECT.
    2. Vuela: la gravedad lo acelera hacia abajo mientras también se mueve
       en horizontal y gira.
    3. Choca con el "suelo" (que está `fall` píxeles por debajo de su
       origen). Rebota CASING_BOUNCES veces y finalmente se queda quieto.
    4. Se queda en el piso hasta que se acaba CASING_LIFE; los últimos
       CASING_FADE_TIME segundos se desvanece gradualmente.
    """

    def __init__(self):
        self.casings     = []         # lista de diccionarios (uno por casquillo)
        self.last_origin = None       # coordenadas del último casquillo (para debug)
        self._img_cache  = {}         # caché de imágenes ya giradas

    def emit(self, x, y, facing, force=1.0):
        """
        Crear un casquillo en la posición (x, y) del mundo.

        x, y   → posición de origen (ya con el offset de CASING_ORIGIN sumado)
        facing → dirección de Snake ("UP", "DOWN", "LEFT", "RIGHT")
        force  → multiplicador de velocidad (de CASING_WEAPONS)
        """
        # Si hay demasiados casquillos, sacar el más viejo.
        if len(self.casings) >= CASING_MAX:
            self.casings.pop(0)

        eject = CASING_EJECT.get(facing, CASING_EJECT["DOWN"])

        # Sortear la distancia de caída al azar dentro del rango configurado.
        fall_min, fall_max = eject["fall"]
        fall = random.uniform(fall_min, fall_max)

        self.last_origin = (x, y)
        self.casings.append({
            "x":         x,
            "y":         y,
            # Velocidad inicial: el rango de CASING_EJECT multiplicado por la
            # fuerza del arma.
            "vx":        random.uniform(*eject["vx"]) * force,
            "vy":        random.uniform(*eject["vy"]) * force,
            # El "suelo": la y en la que va a chocar por primera vez.
            # Es fija para este casquillo (no es el suelo real del mapa).
            "floor_y":   y + max(0.0, fall),
            "rot":       random.uniform(0.0, 360.0),
            "vrot":      random.uniform(*CASING_SPIN),
            "life":      CASING_LIFE,
            "bounces":   CASING_BOUNCES,  # rebotes que le quedan
            "on_ground": False,
        })

    def clear(self):
        """Borrar todos los casquillos (al reiniciar la misión)."""
        self.casings.clear()
        self.last_origin = None

    def update(self, dt):
        """Avanzar la física de todos los casquillos. Llamar cada frame."""
        for c in self.casings:
            c["life"] -= dt   # descontamos tiempo de vida primero

            if c["on_ground"]:
                continue   # ya está quieto, no hay física que aplicar

            # ── Física en el aire ────────────────────────────────────────────
            # La gravedad aumenta la velocidad vertical hacia abajo.
            c["vy"] += CASING_GRAVITY * dt

            # Movemos el casquillo con su velocidad actual.
            c["x"]   += c["vx"]  * dt
            c["y"]   += c["vy"]  * dt
            c["rot"] += c["vrot"] * dt

            # ── Detección del suelo ──────────────────────────────────────────
            # Solo chequeamos si el casquillo va hacia abajo (vy > 0) y
            # ya pasó o llegó a su suelo.
            if c["vy"] > 0 and c["y"] >= c["floor_y"]:
                c["y"] = c["floor_y"]   # ajustamos para que no atraviese el suelo

                # Velocidad que tendría el rebote según el amortiguamiento.
                bounce_speed = abs(c["vy"]) * CASING_BOUNCE_DAMPING

                if c["bounces"] > 0 and bounce_speed >= CASING_MIN_BOUNCE_SPEED:
                    # ── Rebote ───────────────────────────────────────────────
                    c["bounces"] -= 1                      # gastamos un rebote
                    c["vy"]  = -bounce_speed               # invertimos la vertical
                    c["vx"]  *= CASING_BOUNCE_FRICTION     # perdemos velocidad lateral
                    c["vrot"] *= CASING_BOUNCE_FRICTION    # perdemos velocidad de giro
                else:
                    # ── Aterriza definitivamente ──────────────────────────────
                    c["on_ground"] = True
                    c["vx"] = c["vy"] = c["vrot"] = 0.0

        # Sacar los casquillos cuya vida llegó a cero.
        self.casings = [c for c in self.casings if c["life"] > 0]

    def _get_rotated_image(self, color, rot):
        """
        Devuelve la imagen del casquillo girada `rot` grados, desde el caché.
        El caché evita crear una Surface nueva por casquillo por frame.
        """
        # Redondeamos al múltiplo de _CASING_ROT_STEP más cercano para
        # reducir la cantidad de imágenes distintas en el caché.
        bucket = int(rot // _CASING_ROT_STEP) % (360 // _CASING_ROT_STEP)
        angle  = bucket * _CASING_ROT_STEP
        key    = (color, bucket)

        img = self._img_cache.get(key)
        if img is None:
            # Crear la imagen base (un rectángulo del color dado) y girarla.
            base = pygame.Surface(CASING_SIZE, pygame.SRCALPHA)
            base.fill(color)
            img = pygame.transform.rotate(base, angle)
            self._img_cache[key] = img

        return img

    def draw(self, surface, ox, oy):
        """
        Dibujar todos los casquillos.
        ox, oy → desplazamiento de la cámara (camera.camera_rect.topleft).
        """
        fade = max(CASING_FADE_TIME, 1e-3)   # evitar división por cero

        for c in self.casings:
            color = CASING_COLOR_GROUND if c["on_ground"] else CASING_COLOR_AIR
            img   = self._get_rotated_image(color, c["rot"])

            # Alfa para el desvanecimiento final: mientras "life" sea mayor que
            # CASING_FADE_TIME, el alfa es 255 (totalmente visible); cuando
            # life cae por debajo de CASING_FADE_TIME, empieza a desvanecerse.
            img.set_alpha(int(255 * min(1.0, c["life"] / fade)))

            sx = int(c["x"] + ox)
            sy = int(c["y"] + oy)
            surface.blit(img, img.get_rect(center=(sx, sy)))

            if DEBUG_CASINGS:
                # Rayita roja → dónde está el "suelo" de este casquillo.
                fy = int(c["floor_y"] + oy)
                pygame.draw.line(surface, (255, 0, 0), (sx - 5, fy), (sx + 5, fy), 1)

        if DEBUG_CASINGS and self.last_origin:
            # Punto magenta → dónde nació el último casquillo.
            mx, my = self.last_origin
            pygame.draw.circle(surface, (255, 0, 255), (int(mx + ox), int(my + oy)), 2)


# ══════════════════════════════════════════════════════════════════════════════
#  DESTELLO Y HUMO (dibujados con código, sin imágenes)
# ══════════════════════════════════════════════════════════════════════════════
class _FXPool:
    """
    Pool de partículas para el destello de boca y el humo.
    Cada disparo crea un destello (dura ~0,06 s) y, con probabilidad
    SMOKE_CHANCE, una nube de humo que sube y se desvanece.
    """

    FLASH_LIFE   = 0.06    # segundos que dura el destello
    SMOKE_CHANCE = 0.70    # probabilidad de que salga humo por disparo (0-1)
    SMOKE_LIFE   = (0.7, 1.1)     # rango de duración del humo en segundos
    SMOKE_RISE   = (22.0, 38.0)   # rango de velocidad de ascenso (px/s)
    SMOKE_DRIFT  = (-6.0, 6.0)    # rango de deriva horizontal (px/s)
    SMOKE_R0     = 2.0    # radio inicial del puff de humo (px)
    SMOKE_R1     = 6.0    # radio final del puff de humo (px)
    SMOKE_ALPHA  = 110    # alfa máximo del humo (0-255)
    MAX_PUFFS    = 80     # máximo de puffs de humo en pantalla a la vez
    _cache: dict = {}     # caché de imágenes de humo (compartido entre instancias)

    def __init__(self):
        self.flashes = []   # lista de destellos activos
        self.puffs   = []   # lista de puffs de humo activos

    def emit(self, x, y, facing, size=1.0):
        """
        Crear un destello y (posiblemente) un puff de humo en (x, y).
        `facing` define hacia dónde apunta el destello.
        `size`   escala todo el efecto (de _FX_SIZE).
        """
        dx, dy = _DIRS.get(facing, (0, 1))

        # Pequeño ángulo aleatorio para que el destello no apunte siempre
        # exactamente al frente.
        jitter = random.uniform(-0.22, 0.22)   # en radianes
        cs, sn = math.cos(jitter), math.sin(jitter)

        self.flashes.append({
            "x": x, "y": y,
            # Dirección rotada del destello.
            "dx": dx * cs - dy * sn,
            "dy": dx * sn + dy * cs,
            "size": size * random.uniform(0.85, 1.15),
            "life": self.FLASH_LIFE,
        })

        if len(self.puffs) < self.MAX_PUFFS and random.random() < self.SMOKE_CHANCE:
            life = random.uniform(*self.SMOKE_LIFE)
            self.puffs.append({
                "x":  x + random.uniform(-2, 2),
                "y":  y + random.uniform(-2, 1),
                "vx": random.uniform(*self.SMOKE_DRIFT),
                "vy": -random.uniform(*self.SMOKE_RISE),
                "life": life,
                "max":  life,
                "size": size,
            })

    def clear(self):
        """Borrar destellos y humo (al reiniciar la misión)."""
        self.flashes.clear()
        self.puffs.clear()

    def update(self, dt):
        """Avanzar el estado de todos los efectos. Llamar cada frame."""
        for f in self.flashes:
            f["life"] -= dt
        self.flashes = [f for f in self.flashes if f["life"] > 0]

        for p in self.puffs:
            p["life"] -= dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            # El viento horizontal va disminuyendo con el tiempo.
            p["vx"] *= max(0.0, 1.0 - 0.8 * dt)
        self.puffs = [p for p in self.puffs if p["life"] > 0]

    def draw(self, surface, ox, oy):
        # El humo va detrás (se dibuja primero) y el destello encima.
        for p in self.puffs:
            self._draw_puff(surface, ox, oy, p)
        for f in self.flashes:
            self._draw_flash(surface, ox, oy, f)

    @classmethod
    def _draw_puff(cls, surface, ox, oy, p):
        """Dibujar un puff de humo: un círculo semitransparente que crece
        y se desvanece mientras sube."""
        t = p["life"] / p["max"]   # 1.0 = recién nacido, 0.0 = por desaparecer
        s = p["size"]
        # El radio crece desde SMOKE_R0 hasta SMOKE_R1 a medida que pasa el tiempo.
        r     = max(1, int(cls.SMOKE_R0 * s + (cls.SMOKE_R1 * s - cls.SMOKE_R0 * s) * (1.0 - t)))
        alpha = int(cls.SMOKE_ALPHA * t)   # alfa decrece con el tiempo
        if alpha <= 0:
            return

        shade = 215 - int(95 * (1.0 - t))   # se oscurece a medida que desaparece

        # Usamos la caché para no crear la misma Surface miles de veces.
        key = (r, alpha // 12, shade // 22)
        img = cls._cache.get(key)
        if img is None:
            img = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(img, (shade, shade, shade, alpha), (r, r), r)
            cls._cache[key] = img

        surface.blit(img, (int(p["x"] + ox) - r, int(p["y"] + oy) - r))

    @staticmethod
    def _draw_flash(surface, ox, oy, f):
        """
        Dibujar el destello de boca: dos rombos superpuestos (naranja y
        amarillo claro) más un punto central brillante.
        """
        t  = f["life"] / _FXPool.FLASH_LIFE   # 1.0 = recién nacido
        s  = f["size"] * (0.6 + 0.4 * t)       # se encoge con el tiempo
        dx, dy = f["dx"], f["dy"]               # dirección del arma
        px, py = -dy, dx                        # perpendicular a la dirección
        x = f["x"] + ox
        y = f["y"] + oy

        def diamond(length, width, color):
            """Dibuja un rombo elongado apuntando en la dirección del arma."""
            pts = [
                (x - dx * 2 * s,                         y - dy * 2 * s),
                (x + px * width + dx * length * 0.35,    y + py * width + dy * length * 0.35),
                (x + dx * length,                         y + dy * length),
                (x - px * width + dx * length * 0.35,    y - py * width + dy * length * 0.35),
            ]
            pygame.draw.polygon(surface, color, pts)

        diamond(15 * s, 6 * s,   (255, 160,  30))   # naranja, rombo grande
        diamond( 9 * s, 3.5 * s, (255, 245, 160))   # amarillo claro, más pequeño
        pygame.draw.circle(surface, (255, 255, 220), (int(x), int(y)), max(1, int(2.5 * s)))


# ══════════════════════════════════════════════════════════════════════════════
#  CLASE PÚBLICA  ─  FireFX
# ══════════════════════════════════════════════════════════════════════════════
class FireFX:
    """
    Punto de entrada principal para todos los efectos de disparo.

    Cómo se usa
    ───────────
    1. Crear una instancia al principio de la misión:
         fx = FireFX()

    2. Llamar en cada disparo (por ejemplo, dentro del callback shoot() que
       le pasás a WeaponManager.update):
         fx.on_shot(player, "m16")

    3. Llamar en cada frame:
         fx.update(dt)
         fx.draw(virtual_surface, camera)

    4. Para saber si hay que reemplazar el sprite normal de Snake con el de
       fuego (llamar desde Player.draw_with_camera):
         img = fx.get_fire_image("m16", player.facing, player.is_moving, player.frame_index)
         if img:
             surface.blit(img, ...)

    5. Al reiniciar la misión:
         fx.clear()
    """

    # Poner en True para mostrar un punto celeste en la boca del cañón
    # del último disparo (útil para calibrar _MUZZLE).
    DEBUG_MUZZLE = False

    def __init__(self, sprite_folder: str = "assets/sprites/solid_python", scale: int = 2):
        self._pool        = _FXPool()       # destellos y humo
        self._casings     = _CasingPool()   # casquillos
        self._last_muzzle = None            # posición de la última boca de cañón

        # Por ahora solo el M16 tiene sprites propios de disparo.
        # Para agregar otra arma: añadir una entrada con su prefix y sus PNGs.
        self._anims: dict = {
            "m16": _FireAnim(sprite_folder, "m16_fire", scale),
        }

    def on_shot(self, player, weapon_id: str):
        """
        Disparar todos los efectos visuales para un disparo.
        Llamar una vez por cada bala disparada.

        player    → la instancia de Player (para .facing, .rect.center, etc.)
        weapon_id → id del arma ("m16", "beretta", "uzi", "stinger")
        """
        facing     = player.facing
        sprite_set = _sprite_set_of(weapon_id)

        # Activar el sprite de fuego si esta arma tiene animación.
        anim = self._anims.get(sprite_set)
        if anim:
            anim.trigger()

        # Destello y humo: solo si el tamaño del efecto es mayor que cero.
        size = _FX_SIZE.get(weapon_id, 0.75)
        if size > 0:
            offsets = _MUZZLE.get(sprite_set, _MUZZLE_DEFAULT)
            ox, oy = offsets.get(facing, (5, -10))
            mx = player.rect.centerx + ox
            my = player.rect.centery + oy
            self._last_muzzle = (mx, my)
            self._pool.emit(mx, my, facing, size)

        # Casquillo: verificar si esta arma los suelta.
        wcfg = CASING_WEAPONS.get(weapon_id, CASING_WEAPON_DEFAULT)
        if CASINGS_ENABLED and wcfg["enabled"]:
            # Buscar el offset de origen del casquillo (primero por sprite_set,
            # luego por defecto).
            origins = CASING_ORIGIN.get(sprite_set, CASING_ORIGIN["default"])
            cx, cy  = origins.get(facing, CASING_ORIGIN["default"].get(facing, (0, -4)))
            self._casings.emit(
                player.rect.centerx + cx,
                player.rect.centery + cy,
                facing,
                wcfg["force"],
            )

    def muzzle_pos(self, player, weapon_id: str):
        """Boca del cañón en coordenadas del mundo (mismos offsets de _MUZZLE)."""
        offsets = _MUZZLE.get(_sprite_set_of(weapon_id), _MUZZLE_DEFAULT)
        ox, oy = offsets.get(player.facing, (5, -10))
        return (player.rect.centerx + ox, player.rect.centery + oy)

    def clear(self):
        """Borrar todos los efectos en pantalla (llamar al reiniciar la misión)."""
        self._casings.clear()
        self._pool.clear()
        self._last_muzzle = None

    def update(self, dt: float):
        """Avanzar todos los efectos. Llamar una vez por frame."""
        for anim in self._anims.values():
            anim.update(dt)
        self._pool.update(dt)
        self._casings.update(dt)

    def draw(self, surface: pygame.Surface, camera):
        """
        Dibujar todos los efectos sobre `surface`.
        Llamar después de dibujar el mapa y antes de los HUDs.
        `camera` tiene que tener el atributo camera_rect.topleft.
        """
        ox, oy = camera.camera_rect.topleft
        self._casings.draw(surface, ox, oy)  # casquillos van debajo del humo
        self._pool.draw(surface, ox, oy)
        if self.DEBUG_MUZZLE and self._last_muzzle:
            mx, my = self._last_muzzle
            pygame.draw.circle(surface, (0, 255, 255), (int(mx + ox), int(my + oy)), 2)

    def get_fire_image(self, weapon_id: str, facing: str,
                       is_moving: bool = False, frame_index: int = 0):
        """
        Devuelve el sprite de fuego que corresponde al estado actual, o None
        si no hay que reemplazar el sprite normal de Snake.

        weapon_id   → weapons.current_id
        facing      → player.facing
        is_moving   → player.is_moving
        frame_index → player.frame_index  (sincroniza el paso de piernas)
        """
        anim = self._anims.get(_sprite_set_of(weapon_id))
        if anim is None:
            return None
        return anim.get_image(facing, is_moving, frame_index)

    def is_firing(self, weapon_id: str) -> bool:
        """Devuelve True si el arma está en el "estado de disparo" (dentro del GAP)."""
        anim = self._anims.get(_sprite_set_of(weapon_id))
        return anim is not None and anim.active()