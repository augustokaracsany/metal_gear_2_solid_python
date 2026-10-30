"""
src/hind.py  --  Jefe HIND-D

  * HindD: El helicóptero
  * BossHealthBar: Barra de vida del jefe.

Ciclo:
    TAKEOFF: cinemática de despegue, opcional ( Salteable con ESPACIO. )
    ENTER pasa a ORBIT ( La ventana donde se le puede pegar. ) pasa a WARN ( Se frena y marca la franja 
    en la que va a disparar. ) pasa a PASS ( La Pasada en sí, con ráfaga de impactos POR DELANTE del Hind. )
    GAP -> WARN -> PASS ... -> ENTER ( Vuelve a la órbita. ) -> ...
"""
import math
import os
import random

import pygame

from src.hud import draw_text_shadow
from src.settings import (
    COLOR_TEXT, COLOR_HEALTH_SHADOW,
    HEALTH_BAR_X, HEALTH_BAR_Y, HEALTH_BAR_WIDTH, HEALTH_BAR_HEIGHT,
    HEALTH_LABEL_SIZE, HEALTH_NUMBER_SIZE, HEALTH_NUMBER_GAP,
    HEALTH_NUMBER_RESERVED, HEALTH_TICKS,
    COLOR_HEALTH_FILL, COLOR_HEALTH_HIGHLIGHT, COLOR_HEALTH_LOW, COLOR_HEALTH_LINE,
)

# AJUSTES
HIND_DEBUG = False # Dibuja el círculo de órbita y el estado.
HIND_NAME = "HIND-D"
HIND_MAX_HEALTH = 180 # 18 impactos de 10.
HIT_DAMAGE = 10

# Barra de vida del HIND-D.
# PARA TEST Con 1360 px de pantalla, hasta ~580 de largo no pisa el número de la barra de Snake.
BOSS_BAR_ANCHOR = "center" # "center" | "right" | "left".
BOSS_BAR_OFFSET = (0, 0) # Desplazamiento extra ( x, y ) en px.
BOSS_BAR_WIDTH = 560 # Largo de la barra.
BOSS_BAR_HEIGHT = 24 # Grosor.
BOSS_BAR_LABEL_SIZE = 36 # Tamaño del nombre / fase.
BOSS_BAR_SHOW_NUMBER = True # Número grande a la derecha de la barra.
BOSS_BAR_SHOW_PHASE = True # "FASE n" arriba, a la derecha de la barra.
BOSS_BAR_TRAIL = True # Estela clara que baja con retraso al recibir daño.
BOSS_BAR_TRAIL_COLOR = (255, 190, 170)
BOSS_BAR_FILL = (200, 25, 25) # Rojo de la barra.
BOSS_BAR_HIGHLIGHT = (245, 85, 75) # Brillo de la mitad de arriba.
BOSS_BAR_EMPTY = (45, 10, 10) # Fondo de la parte vacía.
BOSS_BAR_FRAME = (150, 25, 25) # Marco rojo oscuro.
BOSS_BAR_LINE = (200, 70, 70) # Línea fina y marcas de abajo.

# DEBUG:
# F3 -> strip_box       
# F4 -> impact_hitbox     
# F5 -> hind_hitbox
# F6 -> HIND_DEBUG (órbita + estado)            
# F7 -> sprite_rect / player_hitbox
DEBUG = dict(
    strip_box=True, # Caja roja de la franja de muerte ( Donde caen los tiros. ) + ruta tenue.
    impact_hitbox=False, # Hitbox real de cada impacto ( Cuadrado amarillo. ).
    hind_hitbox=False, # self.rect del Hind ( Cuadrado verde, 96x96. ).
    sprite_rect=False, # Rectángulo real del sprite que se está dibujando ( Magenta. ).
    player_hitbox=False, # Hitbox de Snake contra la que se chequean los impactos ( Celeste. ).
)

# AUDIO:
# Todo el sonido del jefe se controla desde acá. Las rutas son relativas a AUDIO_DIR.
# file: archivo ( None o "" = silencio / no hace nada. ). Si el archivo no existe, avisa una vez por consola y sigue sin sonido.
# volume: 0.0 a 1.0 ( Se multiplica por SFX_MASTER / MUSIC_MASTER. ).
# loop: True = Suena en bucle mientras dure la acción; False = una sola vez.
# fade_ms: Fundido al empezar / cortar ( Solo para loops de efectos. ).
AUDIO_DIR = "assets/audio/hind-d"
SFX_MASTER = 1.0
MUSIC_MASTER = 1.0
MUSIC_FADE_MS = 800 # Fundido de entrada al cambiar de música.

SFX = {
    # Cinemática: Hélices girando y ascenso ( Fases SPIN y RISE del despegue. ).
    "takeoff": dict(file="helicopter-starting-exterior-01.wav", volume=4, loop=True,  fade_ms=200),
    # VOLAR: Viajando ( ENTER, GAP y mientras hace la pasada. ).
    "fly":     dict(file="helicopter-fly-over-01.wav",     volume=4, loop=True,  fade_ms=300),
    # ORBITAR: Dando vueltitas alrededor de Snake ( Ventana donde se le puede pegar con los Stinger. ).
    "orbit":   dict(file="helicopter-hovering-01.wav",   volume=4, loop=True,  fade_ms=300),
    # DISPARAR: loop=True: Suena continuo mientras caen los tiros:
    #           loop=False: Un sonido por cada tanda de impactos ( FIRE_INTERVAL ).
    "fire":    dict(file="cannon-30mm-hispano-suiza-loop.wav",    volume=1, loop=True,  fade_ms=50),
    # Aviso: Una vez al frenar y marcar la franja.
    "warn":    dict(file="helicopter-fly-over-04.wav",    volume=0.8, loop=False),
    # Cuando Snake le pega al Hind.
    "hit":     dict(file="sfx/hind_hit.mp3",     volume=0.9, loop=False),
    # Cuando cae / explota.
    "down":    dict(file="sfx/hind_explosion.mp3", volume=1.0, loop=False),
}

# Música de la misión del jefe. La maneja game.py según la etapa:
# level: El nivel antes de la cinemática ( Incluye esperar a pisar el trigger. ).
# cutscene: Durante la cinemática de despegue.
# boss: Durante la pelea.
# file=None deja lo que ya estuviera sonando sin tocarlo.
MUSIC = {
    "level":    dict(file="music/mission3_infiltration.mp3", volume=0.6, loop=True),
    "cutscene": dict(file="216-blast-furnace-twin-snakes-version.mp3",         volume=0.7, loop=False),
    "boss":     dict(file="Metal Gear Solid_ Peace Walker Expanded Soundtrack - 30 - CHRYSALIS.mp3", volume=5, loop=True),
}

SPRITE_DIR = "assets/sprites/hind-d"
SPRITE_SCALE = 2 # Igual que todo LO DEMAS.
SHOT_EXTRA_SCALE = 1 # Tamaño extra de los impactos.
PROP_FRAME_MS = 50 # Hélices del sprite de combate ( Frame 1 <-> 2 ).

# Giro del sprite: 
# El sprite solo puede girar de a UNA dirección contigua por paso ( 45° ), nunca saltea:
# right > downright > down > downleft > left ( Aunque sea rápido. ).
TURN_STEP_TIME = 0.10 # Segundos por cada paso de 45°. Menos = Giro más rápido.

# LA CINEMÁTICA DE DESPEGUE 
# Línea de tiempo ( Todo en segundos salvo que diga otra cosa. OJO ):

#   Snake pisa trigger_cutscene:
CINE_START_DELAY = 0.5 # CINE_START_DELAY: espera con la cámara todavía en Snake.
CINE_PAN_IN_TIME = 1.2 # CINE_PAN_IN_TIME: La cámara viaja hasta la pista.
CINE_PAN_OUT_TIME = 1.0 # CINE_PAN_OUT_TIME: La cámara vuelve a Snake y se libera el control
TAKEOFF_HOLD = 5 # TAKEOFF_HOLD: Hind_D1 quieto.
TAKEOFF_SPIN = 10 # TAKEOFF_SPIN: Hélices girando ( D2-D7 ) en el suelo.
TAKEOFF_AFTER = 0.8

# Cámara durante la cinemática: Desplazamiento ( Ejes x, y) en px respecto al centro de la pista.

CINE_CAM_OFFSET = (0, 120)

# Despegue ( CINEMÁTICA. ).
TAKEOFF_PREFIX = "Hind_D" # Hind_D1.png ... Hind_D7.png
TAKEOFF_FRAME_MS = 70 # Velocidad de giro de hélices ( Menos = Más rápido. ).
# Ascenso ( TAKEOFF_ACCEL / TAKEOFF_MAX_SPEED hasta TAKEOFF_RISE_DISTANCE, )
TAKEOFF_ACCEL = 120 # px/s² de aceleración vertical.
TAKEOFF_MAX_SPEED = 260 # px/s máxima de ascenso.
TAKEOFF_RISE_DISTANCE = 520 # px que sube antes de darse por "fuera de pantalla" ( Vista = 384 px de alto. ).
TAKEOFF_SHADOW_DIR = "down" # Sprite de la sombra que aparece al elevarse: hindd-<dir>1/2.png.

# Seguimiento: el centro de la órbita persigue a Snake
FOLLOW_SPEED = 70 # px/s ( Snake camina a 100 ). 0 = órbita fija en el centro del mapa.

# Movimiento.
ENTER_DISTANCE = 450 # Si no hay pista ( Sin boss_spawn. ): desde qué distancia entra.
ENTER_TIME = 3.0 # Mínimo de segundos para llegar a la órbita.
ENTER_AVG_SPEED = 180 # px/s promedio al viajar a la órbita ( Alarga el tiempo si está lejos. ).
GAP_PAUSE_EXTRA = 0.0 # Pausa extra entre pasadas encadenadas.
DOWN_TIME = 3.0 # Duración de la caída/explosión al morir.

# Pasada y FRANJA.
STRIP_WIDTH = 16 # ANCHO de la franja mortal ( px ).
#  ( El LARGO de la franja se ajusta por fase con "strip_length" en PHASES. )
IMPACT_LEAD = 200 # Mínimo de px POR DELANTE del Hind donde caen los tiros.
# Se alarga solo si hace falta: nunca menos que pass_speed*IMPACT_LIFE+20.
PASS_AFTER = 250 # Cuánto sigue de largo después de terminar la franja ( px ).
FIRE_INTERVAL = 0.1 # Segundos entre tandas de impactos.
IMPACTS_PER_TICK = 1 # Impactos por tanda ( Más = ráfaga más densa. ).
IMPACT_LIFE = 0.30 # Cuánto dura cada impacto dibujado.
IMPACT_HITBOX = 0.6 # Tamaño del hitbox respecto al sprite del impacto.
IMPACT_DAMAGE = 12 # Daño a Snake ( 100 de vida, 1 s de invulnerabilidad. ).

# Parámetros por fase:
#  window: Segundos de órbita ( La ventana para pegarle. ).
#  passes: Pasadas seguidas por ataque.
#  warn: Segundos que se frena marcando la franja antes de atacar.
#  strip_length: LARGO de la franja donde caen los tiros ( px ).
#  gap: Pausa entre pasadas encadenadas.
#  radius: Radio de la órbita en px.
#  orbit_speed: Velocidad en la órbita ( px/s ).
#  pass_speed: Velocidad de la pasada ( px/s ).
PHASES = {
    1: dict(window=6.0, passes=5, warn=1.3, strip_length=900, gap=0.0, radius=300, orbit_speed=80,  pass_speed=380),
    2: dict(window=5.0, passes=2, warn=1.1, strip_length=520, gap=0.5, radius=150, orbit_speed=100, pass_speed=440),
    3: dict(window=4.0, passes=3, warn=0.9, strip_length=640, gap=0.4, radius=130, orbit_speed=120, pass_speed=500),
}

# Orden por ángulo en pantalla ( y hacia abajo ): 0° = derecha, 90° = abajo...
# Los índices son contiguos en círculo: 0 y 7 también son vecinos.
DIR_NAMES = ["right", "downright", "down", "downleft",
                "left", "upleft", "up", "upright"]
DOWN_IDX = DIR_NAMES.index("down")


class _HindAudio:
    """Carga los SFX de SFX{} y maneja los loops ( volar / orbitar / disparar / despegue )."""
    def __init__(self):
        self.enabled = pygame.mixer.get_init() is not None
        self.sounds = {}
        self.active = set()
        self._warned = set()
        if not self.enabled:
            return
        for name, cfg in SFX.items():
            snd = self._load(name, cfg)
            if snd:
                self.sounds[name] = snd

    def _load(self, name, cfg):
        f = cfg.get("file")
        if not f:
            return None
        path = os.path.join(AUDIO_DIR, f)
        if not os.path.exists(path):
            if name not in self._warned:
                print(f"Aviso: sonido '{name}' no encontrado: {path}")
                self._warned.add(name)
            return None
        try:
            snd = pygame.mixer.Sound(path)
            snd.set_volume(max(0.0, min(1.0, cfg.get("volume", 1.0) * SFX_MASTER)))
            return snd
        except Exception as e:
            print(f"Aviso: no se pudo cargar sonido '{name}' ({path}): {e}")
            return None

    def is_loop(self, name):
        return bool(SFX.get(name, {}).get("loop", False))

    def play(self, name):
        """One-shot ( También sirve para tandas de disparo con loop=False. )."""
        snd = self.sounds.get(name)
        if snd:
            snd.play()

    def set_loops(self, wanted):
        """Deja sonando exactamente los loops de `wanted` ( Set de nombres. )."""
        if not self.enabled:
            return
        for name in list(self.active - wanted):
            snd = self.sounds.get(name)
            if snd:
                snd.fadeout(int(SFX[name].get("fade_ms", 0)) or 1)
            self.active.discard(name)
        for name in wanted - self.active:
            snd = self.sounds.get(name)
            if snd:
                snd.play(loops=-1, fade_ms=int(SFX[name].get("fade_ms", 0)))
            self.active.add(name)

    def stop_all(self):
        if not self.enabled:
            return
        for snd in self.sounds.values():
            snd.stop()
        self.active.clear()


class _Impact:
    """Marca de impacto de bala en el suelo."""
    def __init__(self, x, y, size):
        self.x, self.y = x, y
        self.life = IMPACT_LIFE
        self.flip = random.random() < 0.5
        self.rect = pygame.Rect(0, 0, size, size)
        self.rect.center = (round(x), round(y))


class HindD:
    def __init__(self, arena_w, arena_h, attacks_enabled=True, pad_pos=None):
        """pad_pos: ( x, y ) CENTRO de la pista ( objeto boss_spawn ). Cuando la haga habrá cinemática de despegue."""
        self.arena_w, self.arena_h = arena_w, arena_h
        self.cx, self.cy = arena_w / 2, arena_h / 2 # Centro de la órbita ( Persigue a Snake ).
        self._centered = False
        self.radius = PHASES[1]["radius"]
        # RADIUS DETERMINA EL RADIO DE LA ORBITA, NO EL RADIO DE LA FRANJA. 
        # La franja se ajusta con strip_length.

        self.max_health = HIND_MAX_HEALTH
        # La vida se mide en "impactos" de 10 de daño ( 18 impactos = 180 de vida ).
        self.health = self.max_health
        self.phase = 1
        self._pending_phase = None
        self.attacks_enabled = attacks_enabled

        self.angle = random.uniform(0, math.tau)
        self.state = "ENTER"
        # La primera vez que se dibuja el sprite, se coloca en la órbita a la altura de Snake ( Si no hay cinemática de despegue. ).
        self.timer = 0.0
        self.x = self.y = 0.0
        self._heading = 0.0
        self._dir_idx = 0 # Dirección que MUESTRA el sprite ( Gira de pasos. ).
        # Me pasé con la explicación borro todo mejor.
        self._turn_timer = 0.0
        self.rect = pygame.Rect(0, 0, 96, 96)

        self.impacts = []
        self.hit_this_window = False # Un impacto por ventana como máximo.
        self.hit_flash = 0.0
        self.dead_done = False

        self.passes_left = 0
        self.pass_dir = (1.0, 0.0)
        self.pass_start = (0.0, 0.0)
        self.pass_len = 0.0
        self.pass_t = 0.0
        self.strip_lo = 0.0
        self.strip_hi = 0.0
        self.lead = IMPACT_LEAD
        self.target = (0.0, 0.0)
        self.fire_timer = 0.0
        self._firing = False
        self._from = (0.0, 0.0)
        self._enter_time = ENTER_TIME

        # Despegue.
        self.takeoff_done = pad_pos is None
        self.cutscene_go = False        # Game lo pone en True cuando termina el paneo de cámara.
        self._skip_takeoff = False
        self.tk_phase = "HOLD"
        self.altitude = 0.0
        self._tk_vel = 0.0

        # Debug / audio.
        self._sprite_rect = None
        self._player_rect = None
        self.audio = _HindAudio()

        self._sprites = self._load_sprites()
        shot = self._sprites["shot"]
        self._impact_size = int(max(shot[0].get_size()) * IMPACT_HITBOX) if shot else 20
        self._dbg_font = pygame.font.Font(None, 16)

        if pad_pos is not None:
            self.state = "TAKEOFF"
            self._heading = -math.pi / 2          # Mirando hacia arriba.
            self._dir_idx = self._target_dir_idx()
            self._place(*pad_pos)
        else:
            self._begin_enter(None)
            self._dir_idx = self._target_dir_idx()

    # ------------------------------------------------------------ utilidades
    @property
    def cfg(self):
        return PHASES[self.phase]

    @property
    def is_defeated(self):
        return self.state == "DOWN"

    def can_be_hit(self):
        return self.state == "ORBIT" and self.attacks_enabled and not self.hit_this_window

    def skip_takeoff(self):
        self._skip_takeoff = True

    def stop_audio(self):
        """Corta todos los sonidos del jefe (muerte de Snake, victoria, reinicio, menú)."""
        self.audio.stop_all()

    def skip_to_orbit(self):
        """Para reintentar sin intro: arranca directo en órbita."""
        self.state = "ORBIT"
        self.takeoff_done = True
        self.timer = 0.0
        self.hit_this_window = False
        self.radius = self.cfg["radius"]
        self._place(*self._orbit_point())

    def consume_phase_change(self):
        """Devuelve el número de fase nueva una sola vez (gancho para la ración del paso 3)."""
        p, self._pending_phase = self._pending_phase, None
        return p

    def _phase_for_health(self):
        r = self.health / self.max_health
        return 1 if r > 2 / 3 else 2 if r > 1 / 3 else 3

    def _orbit_point(self):
        return (self.cx + self.radius * math.cos(self.angle),
                self.cy + self.radius * math.sin(self.angle))

    def _place(self, nx, ny):
        self.x, self.y = nx, ny
        self.rect.center = (round(nx), round(ny))

    def _set_pos(self, nx, ny, dt):
        if dt > 0:
            vx, vy = (nx - self.x) / dt, (ny - self.y) / dt
            if math.hypot(vx, vy) > 5:
                self._heading = math.atan2(vy, vx)
        self._place(nx, ny)

    def _clamp_center(self, x, y):
        m = self.radius
        x = self.arena_w / 2 if self.arena_w < 2 * m else max(m, min(self.arena_w - m, x))
        y = self.arena_h / 2 if self.arena_h < 2 * m else max(m, min(self.arena_h - m, y))
        return x, y

    def _follow(self, dt, player):
        if FOLLOW_SPEED <= 0:
            return
        tx, ty = self._clamp_center(player.rect.centerx, player.rect.centery)
        dx, dy = tx - self.cx, ty - self.cy
        d = math.hypot(dx, dy)
        step = FOLLOW_SPEED * dt
        if d <= step:
            self.cx, self.cy = tx, ty
        elif d > 0:
            self.cx += dx / d * step
            self.cy += dy / d * step

    # ------------------------------------------------------------- giro
    def _target_dir_idx(self):
        """Dirección (0-7) hacia la que quiere mirar según el rumbo real."""
        return round(self._heading / (math.pi / 4)) % 8

    def _update_facing(self, dt):
        """Gira el sprite de a UN paso contiguo (45°) hacia la dirección objetivo.
        Nunca salta de right a left: pasa por downright > down > downleft.
        Si el objetivo está exactamente opuesto (4 pasos) siempre gira en sentido horario
        (right > downright > down > downleft > left)."""
        target = self._target_dir_idx()
        if self._dir_idx == target:
            self._turn_timer = 0.0
            return
        self._turn_timer += dt
        while self._turn_timer >= TURN_STEP_TIME and self._dir_idx != target:
            self._turn_timer -= TURN_STEP_TIME
            diff = (target - self._dir_idx) % 8          # 1..7 en sentido horario
            self._dir_idx = (self._dir_idx + (1 if diff <= 4 else -1)) % 8

    
    def take_hit(self, amount=HIT_DAMAGE, force=False):
        if self.is_defeated or self.state == "TAKEOFF":
            return False
        if not force and not self.can_be_hit():
            return False
        self.hit_this_window = True
        self.health = max(0, self.health - amount)
        self.hit_flash = 0.25
        new_phase = self._phase_for_health()
        if new_phase != self.phase:
            self.phase = new_phase
            self._pending_phase = new_phase
        if self.health <= 0:
            self.state = "DOWN"
            self.timer = 0.0
            self.impacts.clear()
            self._firing = False
            self.audio.set_loops(set())
            self.audio.play("down")
        else:
            self.audio.play("hit")
        return True

    
    def _begin_enter(self, from_pos):
        """from_pos=None -> entra desde lejos; si no, viaja a la órbita desde ahí."""
        if from_pos is None:
            a = random.uniform(0, math.tau)
            from_pos = (self.cx + math.cos(a) * ENTER_DISTANCE,
                        self.cy + math.sin(a) * ENTER_DISTANCE)
        self._from = from_pos
        self.angle = math.atan2(from_pos[1] - self.cy, from_pos[0] - self.cx)
        self._place(*from_pos)
        ox, oy = self._orbit_point()
        dist = math.hypot(ox - from_pos[0], oy - from_pos[1])
        self._enter_time = max(ENTER_TIME, dist / ENTER_AVG_SPEED)
        self.state = "ENTER"
        self.timer = 0.0

    def _update_takeoff(self, dt, player):
        if self._skip_takeoff:
            self._finish_takeoff(player)
            return
        if not self.cutscene_go:
            return                                   # Esperando que la cámara llegue a la pista.
        self.timer += dt
        if self.tk_phase == "HOLD":
            if self.timer >= TAKEOFF_HOLD:
                self.tk_phase, self.timer = "SPIN", 0.0
        elif self.tk_phase == "SPIN":
            if self.timer >= TAKEOFF_SPIN:
                self.tk_phase, self.timer = "RISE", 0.0
        elif self.tk_phase == "RISE":
            self._tk_vel = min(TAKEOFF_MAX_SPEED, self._tk_vel + TAKEOFF_ACCEL * dt)
            self.altitude += self._tk_vel * dt
            if self.altitude >= TAKEOFF_RISE_DISTANCE:
                self.tk_phase, self.timer = "WAIT", 0.0
        elif self.tk_phase == "WAIT":
            if self.timer >= TAKEOFF_AFTER:
                self._finish_takeoff(player)

    def _finish_takeoff(self, player):
        """La sombra queda en la pista (mirando hacia abajo) y desde ahí viaja a la órbita alrededor de Snake."""
        self.altitude = 0.0
        self.takeoff_done = True
        self.radius = self.cfg["radius"]
        self.cx, self.cy = self._clamp_center(*player.rect.center)
        self._centered = True
        self._begin_enter((self.x, self.y))
        # La sombra aparece mirando "down"; a partir de ahí gira de a un paso hacia su rumbo.
        self._dir_idx = DOWN_IDX
        self._turn_timer = 0.0

    def _begin_warn(self, player):
        """Se frena donde está y marca la franja hacia donde está Snake AHORA."""
        cfg = self.cfg
        tx, ty = player.rect.center
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy)
        if d < 40:                                  # Snake justo debajo: usa el rumbo actual.
            dx, dy = math.cos(self._heading), math.sin(self._heading)
            d = 40.0
        else:
            dx, dy = dx / d, dy / d
        self.pass_dir = (dx, dy)
        self.pass_start = (self.x, self.y)
        self.pass_t = 0.0
        self.target = (tx, ty)
        self._heading = math.atan2(dy, dx)

        # Los tiros caen SIEMPRE por delante del Hind: cursor = pass_t + lead.
        self.lead = max(IMPACT_LEAD, cfg["pass_speed"] * IMPACT_LIFE + 20)
        length = cfg["strip_length"]
        self.strip_lo = max(self.lead, d - length / 2)       # La franja se centra sobre Snake.
        self.strip_hi = max(self.strip_lo + 40, d + length / 2)
        self.pass_len = (self.strip_hi - self.lead) + PASS_AFTER

        self.state = "WARN"
        self.timer = 0.0
        self.audio.play("warn")

    def _fire(self, cursor):
        dx, dy = self.pass_dir
        nx, ny = -dy, dx
        sx, sy = self.pass_start
        hw = STRIP_WIDTH / 2
        for _ in range(IMPACTS_PER_TICK):
            along = cursor + random.uniform(-10, 10)
            lat = random.uniform(-hw, hw)
            self.impacts.append(_Impact(sx + dx * along + nx * lat,
                                        sy + dy * along + ny * lat,
                                        self._impact_size))
        if not self.audio.is_loop("fire"):
            self.audio.play("fire")                 # Un sonido por tanda.

    
    def _wanted_loops(self):
        s = self.state
        wanted = set()
        if s == "TAKEOFF":
            if self.cutscene_go and self.tk_phase in ("SPIN", "RISE"):
                wanted.add("takeoff")
        elif s in ("ENTER", "GAP"):
            wanted.add("fly")
        elif s == "PASS":
            wanted.add("fly")
            if self._firing and self.audio.is_loop("fire"):
                wanted.add("fire")
        elif s == "ORBIT":
            wanted.add("orbit")
        return {n for n in wanted if self.audio.is_loop(n)}

    
    def update(self, dt, player, cover_rects=()):
        self._player_rect = player.rect
        self._update_logic(dt, player, cover_rects)
        if self.state not in ("TAKEOFF", "DOWN"):
            self._update_facing(dt)
        self.audio.set_loops(self._wanted_loops())

    def _update_logic(self, dt, player, cover_rects=()):
        cfg = self.cfg
        self.hit_flash = max(0.0, self.hit_flash - dt)
        self._update_impacts(dt, player, cover_rects)
        self._firing = False

        if self.state == "TAKEOFF":
            self._update_takeoff(dt, player)
            return

        if self.state == "DOWN":
            self.timer += dt
            if self.timer >= DOWN_TIME:
                self.dead_done = True
            return

        if not self._centered:                      # Primer frame: centrar en Snake.
            self.cx, self.cy = self._clamp_center(*player.rect.center)
            self._centered = True
            if self.state == "ORBIT":
                self._place(*self._orbit_point())
            else:
                self._begin_enter(None)
        self._follow(dt, player)

        self.timer += dt
        self.radius += (cfg["radius"] - self.radius) * min(1.0, 2.0 * dt)
        omega = cfg["orbit_speed"] / max(1.0, self.radius)

        if self.state == "ENTER":
            self.angle += omega * dt
            ox, oy = self._orbit_point()
            t = min(1.0, self.timer / self._enter_time)
            s = t * t * (3 - 2 * t)
            self._set_pos(self._from[0] + (ox - self._from[0]) * s,
                          self._from[1] + (oy - self._from[1]) * s, dt)
            if t >= 1.0:
                self.state = "ORBIT"
                self.timer = 0.0
                self.hit_this_window = False

        elif self.state == "ORBIT":
            self.angle += omega * dt
            self._set_pos(*self._orbit_point(), dt)
            if not self.attacks_enabled:
                self.timer = 0.0
                return
            if self.timer >= cfg["window"]:
                self.passes_left = cfg["passes"]
                self._begin_warn(player)

        elif self.state == "WARN":                   # Quieto, apuntando.
            if self.timer >= cfg["warn"]:
                self.state = "PASS"
                self.timer = 0.0
                self.pass_t = 0.0
                self.fire_timer = 0.0

        elif self.state == "PASS":
            self.pass_t += cfg["pass_speed"] * dt
            self._place(self.pass_start[0] + self.pass_dir[0] * self.pass_t,
                        self.pass_start[1] + self.pass_dir[1] * self.pass_t)

            cursor = self.pass_t + self.lead         # Los tiros caen por delante del Hind.
            if self.strip_lo <= cursor <= self.strip_hi:
                self._firing = True
                self.fire_timer -= dt
                n = 0
                while self.fire_timer <= 0 and n < 10:
                    self._fire(cursor)
                    self.fire_timer += FIRE_INTERVAL
                    n += 1

            if self.pass_t >= self.pass_len:
                self.passes_left -= 1
                if self.passes_left > 0:
                    self.state = "GAP"
                    self.timer = 0.0
                else:
                    self._begin_enter((self.x, self.y))   # Vuelve a la órbita.

        elif self.state == "GAP":
            if self.timer >= cfg["gap"] + GAP_PAUSE_EXTRA:
                self._begin_warn(player)

    def _update_impacts(self, dt, player, cover_rects):
        covers = list(cover_rects) if cover_rects else []
        in_cover = player.is_hidden or (covers and player.rect.collidelist(covers) != -1)
        for im in self.impacts[:]:
            im.life -= dt
            if im.life <= 0:
                self.impacts.remove(im)
            elif not in_cover and im.rect.colliderect(player.rect):
                player.take_damage(IMPACT_DAMAGE)       # Respeta la invulnerabilidad de Player.

    def _load_img(self, name, scale=SPRITE_SCALE, fallbacks=()):
        for n in (name, *fallbacks):
            path = os.path.join(SPRITE_DIR, n)
            if not os.path.exists(path):
                continue
            try:
                img = pygame.image.load(path).convert_alpha()
                w, h = img.get_size()
                return pygame.transform.scale(img, (max(1, int(w * scale)), max(1, int(h * scale))))
            except Exception as e:
                print(f"Aviso: no se pudo cargar {path}: {e}")
        return None

    def _load_sprites(self):
        sprites = {"hind": {}, "shot": [], "explo": [], "takeoff": []}
        for name in DIR_NAMES:
            frames = [self._load_img(f"hindd-{name}{i}.png") for i in (1, 2)]
            frames = [f for f in frames if f]
            if frames:
                sprites["hind"][name] = frames
        shot_scale = SPRITE_SCALE * SHOT_EXTRA_SCALE
        sprites["shot"] = [f for f in (self._load_img(f"hindd-shot{i}.png", shot_scale) for i in (1, 2)) if f]
        sprites["explo"] = [f for f in (self._load_img(f"explo{i}.png") for i in range(1, 5)) if f]
        sprites["takeoff"] = [self._load_img(f"{TAKEOFF_PREFIX}{i}.png",
                                            fallbacks=(f"hind_d{i}.png", f"Hind_d{i}.png", f"hind_D{i}.png"))
                            for i in range(1, 8)]
        if not all(sprites["takeoff"]):
            sprites["takeoff"] = []
        return sprites

    def _frame(self, ticks):
        return (ticks // PROP_FRAME_MS) % 2

    def _dir_name(self):
        return DIR_NAMES[self._dir_idx]

    def _takeoff_image(self, ticks):
        frames = self._sprites["takeoff"]
        if not frames:
            return None
        if self.tk_phase == "HOLD" or not self.cutscene_go:
            return frames[0]
        return frames[1 + (ticks // TAKEOFF_FRAME_MS) % 6]

    def _blit_center(self, surface, img, sx, sy):
        """Dibuja la imagen centrada y recuerda su rect (para el debug de sprite_rect)."""
        r = img.get_rect(center=(int(sx), int(sy)))
        surface.blit(img, r)
        self._sprite_rect = r

    def draw_ground(self, surface, camera):
        """Nivel de suelo: franja de aviso, impactos, sombra del Hind. Dibujar ANTES de las entidades."""
        ticks = pygame.time.get_ticks()
        self._sprite_rect = None

        # Despegue: en la pista el helicóptero está en el suelo; al elevarse aparece su sombra.
        if self.state == "TAKEOFF":
            sx, sy = camera.apply_pos(self.x, self.y)
            if self.altitude <= 0:
                img = self._takeoff_image(ticks)
                if img:
                    self._blit_center(surface, img, sx, sy)
                else:
                    self._draw_placeholder(surface, sx, sy, ticks, (60, 80, 60))
            else:
                frames = self._sprites["hind"].get(TAKEOFF_SHADOW_DIR)
                if frames:
                    img = frames[self._frame(ticks) % len(frames)]
                    self._blit_center(surface, img, sx, sy)
                else:
                    self._draw_placeholder(surface, sx, sy, ticks, (20, 20, 20))
            return

        # Franja de peligro: rectángulo con el LARGO y ANCHO reales de la ráfaga.
        if DEBUG["strip_box"] and self.state in ("WARN", "PASS"):
            dx, dy = self.pass_dir
            nx, ny = -dy, dx
            sx, sy = self.pass_start
            hw = STRIP_WIDTH / 2

            def pt(along, lat):
                return camera.apply_pos(sx + dx * along + nx * lat, sy + dy * along + ny * lat)

            pygame.draw.line(surface, (120, 35, 30), pt(0, 0), pt(self.strip_lo, 0), 1)   # Ruta (tenue).
            fast = self.state == "PASS" or self.timer > self.cfg["warn"] * 0.6
            if (ticks // (60 if fast else 130)) % 2 == 0:
                corners = [pt(self.strip_lo, -hw), pt(self.strip_hi, -hw),
                        pt(self.strip_hi, hw), pt(self.strip_lo, hw)]
                pygame.draw.lines(surface, (230, 60, 50), True, corners, 2)

        # Impactos de bala en el suelo (sin rotar).
        shots = self._sprites["shot"]
        for im in self.impacts:
            ix, iy = camera.apply_pos(im.x, im.y)
            if shots:
                img = shots[int((IMPACT_LIFE - im.life) / 0.08) % len(shots)]
                if im.flip:
                    img = pygame.transform.flip(img, True, False)
                surface.blit(img, img.get_rect(center=(int(ix), int(iy))))
            else:
                r = 6 + int(6 * im.life / IMPACT_LIFE)
                pygame.draw.circle(surface, (255, 200, 80), (int(ix), int(iy)), r)
                pygame.draw.circle(surface, (255, 255, 255), (int(ix), int(iy)), max(2, r // 3))

        # El Hind (sprite = sombra).
        visible = True
        if self.state == "DOWN":
            if self.timer > DOWN_TIME * 0.8 or (ticks // 90) % 2 == 0:
                visible = False
        elif self.hit_flash > 0 and (ticks // 50) % 2 == 0:
            visible = False

        if visible:
            sx, sy = camera.apply_pos(self.x, self.y)
            if self.state == "DOWN":
                sx += random.randint(-2, 2)
                sy += random.randint(-2, 2)
            frames = self._sprites["hind"].get(self._dir_name())
            if frames:
                img = frames[self._frame(ticks) % len(frames)]
                self._blit_center(surface, img, sx, sy)
            else:
                self._draw_placeholder(surface, sx, sy, ticks, (20, 20, 20))

    def draw_air(self, surface, camera):
        """Capa superior: helicóptero elevándose, explosiones y debug. Dibujar DESPUÉS de los techos."""
        ticks = pygame.time.get_ticks()

        if self.state == "TAKEOFF" and self.altitude > 0:
            sx, sy = camera.apply_pos(self.x, self.y - self.altitude)
            img = self._takeoff_image(ticks)
            if img:
                self._blit_center(surface, img, sx, sy)
            else:
                self._draw_placeholder(surface, sx, sy, ticks, (60, 80, 60))

        if self.state == "DOWN" and self.timer > 0.3:
            sx, sy = camera.apply_pos(self.x, self.y)
            rng = random.Random(ticks // 120)
            explo = self._sprites["explo"]
            for i in range(4):
                ox, oy = rng.randint(-40, 40), rng.randint(-40, 40)
                if explo:
                    img = explo[((ticks // 120) + i) % len(explo)]
                    surface.blit(img, img.get_rect(center=(int(sx + ox), int(sy + oy))))
                else:
                    pygame.draw.circle(surface, (255, 150, 40), (int(sx + ox), int(sy + oy)), rng.randint(8, 18))

        if HIND_DEBUG and self.state != "TAKEOFF":
            self._draw_debug(surface, camera)
        self._draw_debug_boxes(surface, camera)

    def _draw_placeholder(self, surface, sx, sy, ticks, color):
        a = self._heading
        c, s = math.cos(a), math.sin(a)
        nose = (sx + c * 40, sy + s * 40)
        left = (sx - c * 30 - s * 22, sy - s * 30 + c * 22)
        right = (sx - c * 30 + s * 22, sy - s * 30 - c * 22)
        pygame.draw.polygon(surface, color, [nose, left, right])
        ra = ticks * 0.04
        for off in (0, math.pi / 2):
            rx, ry = math.cos(ra + off) * 48, math.sin(ra + off) * 48
            pygame.draw.line(surface, (110, 110, 110), (sx - rx, sy - ry), (sx + rx, sy + ry), 2)

    def _draw_debug_boxes(self, surface, camera):
        """Hitboxes activables desde DEBUG{} (F3-F7 en juego)."""
        if DEBUG["impact_hitbox"]:
            for im in self.impacts:
                x, y = camera.apply_pos(im.rect.x, im.rect.y)
                pygame.draw.rect(surface, (255, 255, 0), (int(x), int(y), im.rect.w, im.rect.h), 1)
        if DEBUG["hind_hitbox"]:
            x, y = camera.apply_pos(self.rect.x, self.rect.y)
            pygame.draw.rect(surface, (0, 255, 0), (int(x), int(y), self.rect.w, self.rect.h), 1)
        if DEBUG["sprite_rect"] and self._sprite_rect is not None:
            pygame.draw.rect(surface, (255, 0, 255), self._sprite_rect, 1)
        if DEBUG["player_hitbox"] and self._player_rect is not None:
            r = self._player_rect
            x, y = camera.apply_pos(r.x, r.y)
            pygame.draw.rect(surface, (0, 200, 255), (int(x), int(y), r.w, r.h), 1)

    def _draw_debug(self, surface, camera):
        ccx, ccy = camera.apply_pos(self.cx, self.cy)
        pygame.draw.circle(surface, (0, 255, 255), (int(ccx), int(ccy)), int(self.radius), 1)
        pygame.draw.circle(surface, (0, 255, 255), (int(ccx), int(ccy)), 3)
        sx, sy = camera.apply_pos(self.x, self.y)
        label = f"{self.state} F{self.phase} HP{self.health} {self._dir_name()}"
        surface.blit(self._dbg_font.render(label, True, (255, 255, 255)), (sx - 40, sy - 50))


class BossHealthBar:
    """Barra de jefe: misma estructura que la de Solid Python, pero centrada, larga y roja."""

    def __init__(self):
        self.label_font = pygame.font.Font(None, BOSS_BAR_LABEL_SIZE)
        self.number_font = pygame.font.Font(None, HEALTH_NUMBER_SIZE)
        self.trail = 1.0
        self.trail_delay = 0.0
        self.last_ratio = 1.0

    def update(self, dt, ratio):
        if ratio < self.last_ratio:
            self.trail_delay = 0.45          # La estela espera un poco antes de bajar.
        self.last_ratio = ratio
        if self.trail_delay > 0:
            self.trail_delay -= dt
        elif self.trail > ratio:
            self.trail = max(ratio, self.trail - 0.25 * dt)
        else:
            self.trail = ratio

    def draw(self, surface, boss):
        W = BOSS_BAR_WIDTH
        H = BOSS_BAR_HEIGHT
        ratio = max(0.0, min(1.0, boss.health / boss.max_health))

        sw = surface.get_width()
        if BOSS_BAR_ANCHOR == "center":
            x = (sw - W) // 2                       # La BARRA queda centrada; el número va afuera, a la derecha.
        elif BOSS_BAR_ANCHOR == "left":
            x = HEALTH_BAR_X
        else:
            group_w = W + (HEALTH_NUMBER_GAP + HEALTH_NUMBER_RESERVED if BOSS_BAR_SHOW_NUMBER else 0)
            x = sw - HEALTH_BAR_X - group_w
        x += BOSS_BAR_OFFSET[0]
        y = HEALTH_BAR_Y + BOSS_BAR_OFFSET[1]

        # 1. Nombre arriba a la izquierda (y la fase a la derecha).
        label_y = y - self.label_font.get_height() - 5
        draw_text_shadow(surface, self.label_font, HIND_NAME, COLOR_TEXT, x, label_y)
        if BOSS_BAR_SHOW_PHASE:
            draw_text_shadow(surface, self.label_font, f"FASE {boss.phase}", BOSS_BAR_LINE,
                             x + W, label_y, align_right=True)

        # 2. Marco + fondo + estela + parte llena + brillo.
        pygame.draw.rect(surface, COLOR_HEALTH_SHADOW, (x - 4, y - 4, W + 8, H + 8))
        pygame.draw.rect(surface, BOSS_BAR_FRAME, (x - 3, y - 3, W + 6, H + 6), 2)
        pygame.draw.rect(surface, BOSS_BAR_EMPTY, (x, y, W, H))
        fill_width = int(W * ratio)
        if BOSS_BAR_TRAIL:
            trail_width = int(W * self.trail)
            if trail_width > fill_width:
                pygame.draw.rect(surface, BOSS_BAR_TRAIL_COLOR, (x, y, trail_width, H))
        if fill_width > 0:
            pygame.draw.rect(surface, BOSS_BAR_FILL, (x, y, fill_width, H))
            pygame.draw.rect(surface, BOSS_BAR_HIGHLIGHT, (x, y, fill_width, H // 2))

        # 3. Línea fina de capacidad máxima con marcas ( Más altas en 1/3 y 2/3 = Cambio de fase. ).
        line_y = y + H + 8
        pygame.draw.line(surface, COLOR_HEALTH_SHADOW, (x, line_y + 1), (x + W, line_y + 1), 2)
        pygame.draw.line(surface, BOSS_BAR_LINE, (x, line_y), (x + W, line_y), 1)
        for i in range(HEALTH_TICKS + 1):
            tick_x = x + int(W * i / HEALTH_TICKS)
            pygame.draw.line(surface, BOSS_BAR_LINE, (tick_x, line_y - 3), (tick_x, line_y), 1)
        for frac in (1 / 3, 2 / 3):
            tick_x = x + int(W * frac)
            pygame.draw.line(surface, COLOR_HEALTH_SHADOW, (tick_x + 1, line_y - 7), (tick_x + 1, line_y + 1), 2)
            pygame.draw.line(surface, BOSS_BAR_LINE, (tick_x, line_y - 7), (tick_x, line_y), 2)

        # 4. Número grande a la derecha de la barra.
        if BOSS_BAR_SHOW_NUMBER:
            number_right = x + W + HEALTH_NUMBER_GAP + HEALTH_NUMBER_RESERVED
            number_h = self.number_font.get_height()
            number_y = y + (H + 8) // 2 - number_h // 2
            draw_text_shadow(surface, self.number_font, str(boss.health), COLOR_TEXT,
                            number_right, number_y, align_right=True)