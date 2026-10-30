"""
src/hind.py  --  Jefe HIND-D

Ciclo base (fase 1):
    TAKEOFF → ENTER → ORBIT → WARN → PASS → GAP → WARN → ... → ENTER → ...

Fase 2 agrega STILL_WARN → STILL_FIRE (spray en cono, bullet-hell ligero)
Fase 3 agrega además MPASS_WARN → MPASS (barrage de misiles que caen cerca de Snake)

Sonido de aviso antes de cada tipo de ataque:
  - "warn"        → antes de PASS normal
  - "warn_still"  → antes de STILL_FIRE
  - "warn_missile"→ antes de MPASS
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

# ─── AJUSTES GENERALES ────────────────────────────────────────────────────────
HIND_DEBUG      = False
HIND_NAME       = "HIND-D"
HIND_MAX_HEALTH = 180
HIT_DAMAGE      = 10

BOSS_BAR_ANCHOR      = "center"
BOSS_BAR_OFFSET      = (0, 0)
BOSS_BAR_WIDTH       = 560
BOSS_BAR_HEIGHT      = 24
BOSS_BAR_LABEL_SIZE  = 36
BOSS_BAR_SHOW_NUMBER = True
BOSS_BAR_SHOW_PHASE  = True
BOSS_BAR_TRAIL       = True
BOSS_BAR_TRAIL_COLOR = (255, 190, 170)
BOSS_BAR_FILL        = (200, 25, 25)
BOSS_BAR_HIGHLIGHT   = (245, 85, 75)
BOSS_BAR_EMPTY       = (45, 10, 10)
BOSS_BAR_FRAME       = (150, 25, 25)
BOSS_BAR_LINE        = (200, 70, 70)

DEBUG = dict(
    strip_box=True,
    impact_hitbox=False,
    hind_hitbox=False,
    sprite_rect=False,
    player_hitbox=False,
)

# ─── AUDIO ────────────────────────────────────────────────────────────────────
AUDIO_DIR     = "assets/audio/hind-d"
SFX_MASTER    = 1.0
MUSIC_MASTER  = 1.0
MUSIC_FADE_MS = 800

SFX = {
    "takeoff":      dict(file="helicopter-starting-exterior-01.wav", volume=4,   loop=True,  fade_ms=200),
    "fly":          dict(file="helicopter-fly-over-01.wav",           volume=4,   loop=True,  fade_ms=300),
    "orbit":        dict(file="helicopter-hovering-01.wav",           volume=4,   loop=True,  fade_ms=300),
    "fire":         dict(file="cannon-30mm-hispano-suiza-loop.wav",   volume=1,   loop=True,  fade_ms=50),
    "warn":         dict(file="helicopter-fly-over-04.wav",           volume=0.8, loop=False),
    "warn_still":   dict(file="helicopter-fly-over-04.wav",           volume=0.9, loop=False),
    "warn_missile": dict(file="helicopter-fly-over-04.wav",           volume=1.0, loop=False),
    "hit":          dict(file="sfx/hind_hit.mp3",                     volume=0.9, loop=False),
    "down":         dict(file="sfx/hind_explosion.mp3",               volume=1.0, loop=False),
}

MUSIC = {
    "level":    dict(file="music/mission3_infiltration.mp3",
                     volume=0.6, loop=True),
    "cutscene": dict(file="216-blast-furnace-twin-snakes-version.mp3",
                     volume=0.7, loop=False),
    "boss":     dict(file="Metal Gear Solid_ Peace Walker Expanded Soundtrack - 30 - CHRYSALIS.mp3",
                     volume=5, loop=True),
}

# ─── SPRITES ──────────────────────────────────────────────────────────────────
SPRITE_DIR       = "assets/sprites/hind-d"
SPRITE_SCALE     = 2
SHOT_EXTRA_SCALE = 1
PROP_FRAME_MS    = 50
TURN_STEP_TIME   = 0.10

TAKEOFF_PREFIX        = "Hind_D"
TAKEOFF_FRAME_MS      = 70
TAKEOFF_ACCEL         = 120
TAKEOFF_MAX_SPEED     = 260
TAKEOFF_RISE_DISTANCE = 520
TAKEOFF_SHADOW_DIR    = "down"

# ─── CINEMÁTICA ───────────────────────────────────────────────────────────────
CINE_START_DELAY  = 0.5
CINE_PAN_IN_TIME  = 1.2
CINE_PAN_OUT_TIME = 1.0
TAKEOFF_HOLD      = 5
TAKEOFF_SPIN      = 10
TAKEOFF_AFTER     = 0.8
CINE_CAM_OFFSET   = (0, 120)

# ─── MOVIMIENTO ───────────────────────────────────────────────────────────────
FOLLOW_SPEED    = 70
ENTER_DISTANCE  = 450
ENTER_TIME      = 3.0
ENTER_AVG_SPEED = 180
GAP_PAUSE_EXTRA = 0.0
DOWN_TIME       = 3.0

# ─── PASADA / FRANJA (cañón) ──────────────────────────────────────────────────
STRIP_WIDTH      = 16
IMPACT_LEAD      = 200
PASS_AFTER       = 250
FIRE_INTERVAL    = 0.1
IMPACTS_PER_TICK = 1
IMPACT_LIFE      = 0.30
IMPACT_HITBOX    = 0.6
IMPACT_DAMAGE    = 12

# ─── STILL_FIRE (spray en cono, fases 2 y 3) ─────────────────────────────────
STILL_WARN_TIME   = 1.2
STILL_DURATION    = 4.0
STILL_BURST_GAP   = 0.18
STILL_BURST_SIZE  = 4
STILL_CONE_HALF   = 55
STILL_RANGE       = 260
STILL_RANGE_MIN   = 60
STILL_DAMAGE      = IMPACT_DAMAGE
STILL_FOLLOW      = True
STILL_SPREAD_RAND = 0.0

# ─── MPASS — barrage de misiles (fase 3) ─────────────────────────────────────
# Ajustado para que el ataque sea frontal, inesquivable sin cobertura y bien anunciado.
MPASS_WARN_TIME     = 1.2    # Tiempo de advertencia visual en el suelo
MPASS_INTERVAL      = 0.12   # Frecuencia de lanzamiento de misiles en la pasada
MPASS_SPEED         = 300    # Velocidad de avance del Hind durante el ataque
MPASS_MISSILE_SPEED = 580    # Velocidad de vuelo de cada cohete
MPASS_MISSILE_LIFE  = 4.0
MPASS_DAMAGE        = 40     # Daño masivo si impacta fuera de cobertura ("te comes mucho daño")
MPASS_EXPLODE_R     = 55     # Radio de explosión amplio
MPASS_STRIP_WIDTH   = 140    # Franja rectangular ancha de muerte
MPASS_LEAD          = 200
MPASS_AFTER         = 300
MPASS_TRAIL_LEN     = 22
MPASS_TRAIL_LIFE    = 0.28
HIND_ALTITUDE       = 400

# ─── FASES ────────────────────────────────────────────────────────────────────
PHASES = {
    1: dict(
        window=6.0, warn=1.3, strip_length=900, gap=0.0,
        radius=300, orbit_speed=80, pass_speed=380,
        attack_sequence=["pass", "pass", "pass"],
    ),
    2: dict(
        window=5.0, warn=1.1, strip_length=520, gap=0.5,
        radius=200, orbit_speed=100, pass_speed=440,
        attack_sequence=["pass", "still", "pass", "still"],
    ),
    3: dict(
        window=4.0, warn=0.9, strip_length=640, gap=0.4,
        radius=160, orbit_speed=120, pass_speed=500,
        attack_sequence=["pass", "still", "mpass", "pass", "still", "mpass"],
    ),
}

DIR_NAMES = ["right", "downright", "down", "downleft", "left", "upleft", "up", "upright"]
DOWN_IDX  = DIR_NAMES.index("down")

_MDIR_ANGLES = [0, math.pi/4, math.pi/2, 3*math.pi/4,
                math.pi, -3*math.pi/4, -math.pi/2, -math.pi/4]


def _dir_for_angle(angle_rad):
    best, best_diff = DIR_NAMES[0], float("inf")
    for name, a in zip(DIR_NAMES, _MDIR_ANGLES):
        diff = abs(math.atan2(math.sin(angle_rad - a), math.cos(angle_rad - a)))
        if diff < best_diff:
            best, best_diff = name, diff
    return best


# ─── AUDIO ────────────────────────────────────────────────────────────────────
class _HindAudio:
    def __init__(self):
        self.enabled = pygame.mixer.get_init() is not None
        self.sounds  = {}
        self.active  = set()
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
        snd = self.sounds.get(name)
        if snd:
            snd.play()

    def set_loops(self, wanted):
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


# ─── IMPACTO (cañón) ──────────────────────────────────────────────────────────
class _Impact:
    def __init__(self, x, y, size):
        self.x, self.y = x, y
        self.life = IMPACT_LIFE
        self.flip = random.random() < 0.5
        self.rect = pygame.Rect(0, 0, size, size)
        self.rect.center = (round(x), round(y))


# ─── MISIL DE BARRAGE ─────────────────────────────────────────────────────────
class _BarrageMissile:
    def __init__(self, start_x, start_y, target_x, target_y, missile_sprites):
        self.start_x    = float(start_x)
        self.start_y    = float(start_y)
        self.target_x   = float(target_x)
        self.target_y   = float(target_y)
        self.x          = self.start_x
        self.y          = self.start_y
        dx              = target_x - start_x
        dy              = target_y - start_y
        dist            = math.hypot(dx, dy)
        if dist > 0:
            self.vx = dx / dist * MPASS_MISSILE_SPEED
            self.vy = dy / dist * MPASS_MISSILE_SPEED
        else:
            self.vx, self.vy = 0.0, MPASS_MISSILE_SPEED
        self.angle          = math.atan2(self.vy, self.vx)
        self.travel_time    = dist / MPASS_MISSILE_SPEED if MPASS_MISSILE_SPEED > 0 else 0.01
        self.elapsed        = 0.0
        self.life           = MPASS_MISSILE_LIFE
        self.active         = True
        self.exploded       = False
        self._sprites       = missile_sprites
        self._trail: list[tuple[float, float, float]] = []
        self.rect           = pygame.Rect(0, 0, 12, 12)
        self.rect.center    = (round(self.x), round(self.y))

    def update(self, dt):
        if not self.active:
            return
        self.elapsed += dt
        self.life    -= dt
        self.x       += self.vx * dt
        self.y       += self.vy * dt
        self.rect.center = (round(self.x), round(self.y))
        
        self._trail.append((self.x, self.y, 0.0))
        aged = []
        for tx, ty, age in self._trail:
            age += dt
            if age < MPASS_TRAIL_LIFE:
                aged.append((tx, ty, age))
        self._trail = aged[-MPASS_TRAIL_LEN:]

        if self.elapsed >= self.travel_time or self.life <= 0:
            self.active   = False
            self.exploded = True

    def draw(self, surface, camera):
        if not self.active:
            return
        for tx, ty, age in self._trail:
            t     = age / MPASS_TRAIL_LIFE
            alpha = int(200 * (1.0 - t))
            shade = int(160 + 90 * t)
            r     = max(1, int(4 * (1.0 - t * 0.6)))
            sx, sy = camera.apply_pos(tx, ty)
            s = pygame.Surface((r * 2 + 1, r * 2 + 1), pygame.SRCALPHA)
            pygame.draw.circle(s, (shade, shade, shade, alpha), (r, r), r)
            surface.blit(s, (int(sx) - r, int(sy) - r))

        sx, sy   = camera.apply_pos(self.x, self.y)
        dir_name = _dir_for_angle(self.angle)
        img      = self._sprites.get(dir_name) if self._sprites else None
        if img:
            surface.blit(img, img.get_rect(center=(int(sx), int(sy))))
        else:
            dx = math.cos(self.angle)
            dy = math.sin(self.angle)
            tip_x  = int(sx + dx * 9)
            tip_y  = int(sy + dy * 9)
            tail_x = int(sx - dx * 5)
            tail_y = int(sy - dy * 5)
            pygame.draw.line(surface, (220, 210, 190), (tail_x, tail_y), (tip_x, tip_y), 3)
            pygame.draw.circle(surface, (255, 200, 80), (tip_x,  tip_y),  3)
            pygame.draw.circle(surface, (255, 100, 20), (tail_x, tail_y), 4)


# ─── EXPLOSIÓN DE MISIL ───────────────────────────────────────────────────────
class _MissileExplosion:
    DURATION = 0.55

    def __init__(self, x, y, explo_sprites):
        self.x, self.y = float(x), float(y)
        self.life      = self.DURATION
        self._sprites  = explo_sprites

    def update(self, dt):
        self.life -= dt

    @property
    def done(self):
        return self.life <= 0

    def draw(self, surface, camera):
        t  = max(0.0, self.life / self.DURATION)
        sx, sy = camera.apply_pos(self.x, self.y)
        if self._sprites:
            idx = min(int((1.0 - t) * len(self._sprites)), len(self._sprites) - 1)
            img = self._sprites[idx].copy()
            img.set_alpha(int(245 * t))
            surface.blit(img, img.get_rect(center=(int(sx), int(sy))))
        else:
            r_out = int(MPASS_EXPLODE_R * (1.3 - t * 0.5))
            r_in  = max(2, int(r_out * 0.4))
            s     = pygame.Surface((r_out * 2 + 2, r_out * 2 + 2), pygame.SRCALPHA)
            cx, cy = r_out + 1, r_out + 1
            pygame.draw.circle(s, (255, 120, 20,  int(210 * t)), (cx, cy), r_out)
            pygame.draw.circle(s, (255, 240, 80,  int(255 * t)), (cx, cy), r_in)
            surface.blit(s, (int(sx) - r_out - 1, int(sy) - r_out - 1))


# ─── HIND-D ───────────────────────────────────────────────────────────────────
class HindD:
    def __init__(self, arena_w, arena_h, attacks_enabled=True, pad_pos=None):
        self.arena_w, self.arena_h = arena_w, arena_h
        self.cx, self.cy  = arena_w / 2, arena_h / 2
        self._centered    = False
        self.radius       = PHASES[1]["radius"]

        self.max_health   = HIND_MAX_HEALTH
        self.health       = self.max_health
        self.phase        = 1
        self._pending_phase = None
        self.attacks_enabled = attacks_enabled

        self.angle        = random.uniform(0, math.tau)
        self.state        = "ENTER"
        self.timer        = 0.0
        self.x = self.y   = 0.0
        self._heading     = 0.0
        self._dir_idx     = 0
        self._turn_timer  = 0.0
        self.rect         = pygame.Rect(0, 0, 96, 96)

        self.impacts         = []
        self.hit_this_window = False
        self.hit_flash       = 0.0
        self.dead_done       = False

        self.pass_dir     = (1.0, 0.0)
        self.pass_start   = (0.0, 0.0)
        self.pass_len     = 0.0
        self.pass_t       = 0.0
        self.strip_lo     = 0.0
        self.strip_hi     = 0.0
        self.lead         = IMPACT_LEAD
        self.target       = (0.0, 0.0)
        self.fire_timer   = 0.0
        self._firing      = False
        self._from        = (0.0, 0.0)
        self._enter_time  = ENTER_TIME

        self._attack_seq  = []
        self._attack_idx  = 0

        self._still_player_pos  = (0.0, 0.0)
        self._still_burst_timer = 0.0

        # MPASS (barrage)
        self._mpass_dir              = (1.0, 0.0)
        self._mpass_start            = (0.0, 0.0)
        self._mpass_t                = 0.0
        self._mpass_len              = 0.0
        self._mpass_timer            = 0.0
        self._mpass_strip_lo         = 0.0
        self._mpass_strip_hi         = 0.0
        self._barrage_missiles: list[_BarrageMissile]     = []
        self._missile_explosions: list[_MissileExplosion] = []

        self.takeoff_done  = pad_pos is None
        self.cutscene_go   = False
        self._skip_takeoff = False
        self.tk_phase      = "HOLD"
        self.altitude      = 0.0
        self._tk_vel       = 0.0

        self._sprite_rect  = None
        self._player_rect  = None
        self.audio         = _HindAudio()

        self._sprites      = self._load_sprites()
        shot               = self._sprites["shot"]
        self._impact_size  = int(max(shot[0].get_size()) * IMPACT_HITBOX) if shot else 20
        self._dbg_font     = pygame.font.Font(None, 16)

        if pad_pos is not None:
            self.state    = "TAKEOFF"
            self._heading = -math.pi / 2
            self._dir_idx = self._target_dir_idx()
            self._place(*pad_pos)
        else:
            self._begin_enter(None)
            self._dir_idx = self._target_dir_idx()

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
        sprites = {"hind": {}, "shot": [], "explo": [], "takeoff": [], "missile": {}}
        for name in DIR_NAMES:
            frames = [self._load_img(f"hindd-{name}{i}.png") for i in (1, 2)]
            frames = [f for f in frames if f]
            if frames:
                sprites["hind"][name] = frames
        shot_scale = SPRITE_SCALE * SHOT_EXTRA_SCALE
        sprites["shot"]  = [f for f in (self._load_img(f"hindd-shot{i}.png", shot_scale) for i in (1, 2)) if f]
        sprites["explo"] = [f for f in (self._load_img(f"explo{i}.png") for i in range(1, 5)) if f]
        sprites["takeoff"] = [self._load_img(f"{TAKEOFF_PREFIX}{i}.png",
                                              fallbacks=(f"hind_d{i}.png", f"Hind_d{i}.png", f"hind_D{i}.png"))
                               for i in range(1, 8)]
        if not all(sprites["takeoff"]):
            sprites["takeoff"] = []
        for name in DIR_NAMES:
            img = self._load_img(f"missile-{name}.png")
            if img:
                sprites["missile"][name] = img
        return sprites

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
        self.audio.stop_all()

    def skip_to_orbit(self):
        self.state = "ORBIT"
        self.takeoff_done = True
        self.timer = 0.0
        self.hit_this_window = False
        self.radius = self.cfg["radius"]
        self._place(*self._orbit_point())

    def consume_phase_change(self):
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
        d      = math.hypot(dx, dy)
        step   = FOLLOW_SPEED * dt
        if d <= step:
            self.cx, self.cy = tx, ty
        elif d > 0:
            self.cx += dx / d * step
            self.cy += dy / d * step

    def _air_pos(self):
        return self.x, self.y - HIND_ALTITUDE

    def _target_dir_idx(self):
        return round(self._heading / (math.pi / 4)) % 8

    def _update_facing(self, dt):
        target = self._target_dir_idx()
        if self._dir_idx == target:
            self._turn_timer = 0.0
            return
        self._turn_timer += dt
        while self._turn_timer >= TURN_STEP_TIME and self._dir_idx != target:
            self._turn_timer -= TURN_STEP_TIME
            diff = (target - self._dir_idx) % 8
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
            self._barrage_missiles.clear()
            self._missile_explosions.clear()
            self._firing = False
            self.audio.set_loops(set())
            self.audio.play("down")
        else:
            self.audio.play("hit")
        return True

    def take_damage(self, amount):
        return self.take_hit(amount)

    def _begin_enter(self, from_pos):
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

    def _begin_attack_sequence(self, player):
        self._attack_seq = list(self.cfg.get("attack_sequence", ["pass"]))
        self._attack_idx = 0
        self._launch_next_attack(player)

    def _launch_next_attack(self, player):
        if self._attack_idx >= len(self._attack_seq):
            self._begin_enter((self.x, self.y))
            return
        attack = self._attack_seq[self._attack_idx]
        self._attack_idx += 1
        if attack == "pass":
            self._begin_warn(player)
        elif attack == "still":
            self._begin_still_warn(player)
        elif attack == "mpass":
            self._begin_mpass_warn(player)
        else:
            self._begin_enter((self.x, self.y))

    def _begin_warn(self, player):
        cfg = self.cfg
        tx, ty = player.rect.center
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy)
        if d < 40:
            dx, dy = math.cos(self._heading), math.sin(self._heading)
            d = 40.0
        else:
            dx, dy = dx / d, dy / d
        self.pass_dir   = (dx, dy)
        self.pass_start = (self.x, self.y)
        self.pass_t     = 0.0
        self.target     = (tx, ty)
        self._heading   = math.atan2(dy, dx)
        self.lead       = max(IMPACT_LEAD, cfg["pass_speed"] * IMPACT_LIFE + 20)
        length          = cfg["strip_length"]
        self.strip_lo   = max(self.lead, d - length / 2)
        self.strip_hi   = max(self.strip_lo + 40, d + length / 2)
        self.pass_len   = (self.strip_hi - self.lead) + PASS_AFTER
        self.state      = "WARN"
        self.timer      = 0.0
        self.audio.play("warn")

    def _begin_still_warn(self, player):
        self._still_player_pos = player.rect.center
        tx, ty = self._still_player_pos
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy)
        if d > 0:
            self._heading = math.atan2(dy / d, dx / d)
        self.state = "STILL_WARN"
        self.timer = 0.0
        self.audio.play("warn_still")

    def _begin_mpass_warn(self, player):
        """
        Configura la pasada de misiles frontal garantizando que el helicóptero
        apunte exactamente hacia adelante en dirección al movimiento.
        """
        tx, ty = player.rect.center
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy)
        if d < 40:
            dx, dy = math.cos(self._heading), math.sin(self._heading)
            d = 40.0
        else:
            dx, dy = dx / d, dy / d
            
        # Forzamos que el ángulo de avance sea estrictamente frontal hacia donde mira
        self._mpass_dir   = (dx, dy)
        self._mpass_start = (self.x, self.y)
        self._mpass_t     = 0.0
        self._heading     = math.atan2(dy, dx)
        
        # Franja de misiles orientada hacia adelante
        self._mpass_strip_lo = max(MPASS_LEAD, d - self.cfg["strip_length"] / 2)
        self._mpass_strip_hi = max(self._mpass_strip_lo + 60, d + self.cfg["strip_length"] / 2)
        self._mpass_len      = (self._mpass_strip_hi - MPASS_LEAD) + MPASS_AFTER
        self._mpass_timer    = 0.0
        self.state           = "MPASS_WARN"
        self.timer           = 0.0
        self.audio.play("warn_missile")

    def _fire(self, cursor):
        dx, dy = self.pass_dir
        nx, ny = -dy, dx
        sx, sy = self.pass_start
        hw = STRIP_WIDTH / 2
        for _ in range(IMPACTS_PER_TICK):
            along = cursor + random.uniform(-10, 10)
            lat   = random.uniform(-hw, hw)
            self.impacts.append(_Impact(sx + dx * along + nx * lat,
                                        sy + dy * along + ny * lat,
                                        self._impact_size))
        if not self.audio.is_loop("fire"):
            self.audio.play("fire")

    def _fire_still(self, player_pos):
        tx, ty     = player_pos
        dx, dy     = tx - self.x, ty - self.y
        d          = math.hypot(dx, dy)
        if d < 1:
            return
        base_angle = math.atan2(dy, dx)
        cone_rad   = math.radians(STILL_CONE_HALF)
        extra_rand = math.radians(STILL_SPREAD_RAND)
        for _ in range(STILL_BURST_SIZE):
            a    = base_angle + random.uniform(-cone_rad, cone_rad)
            a   += random.uniform(-extra_rand, extra_rand)
            dist = random.uniform(STILL_RANGE_MIN, STILL_RANGE)
            ix   = self.x + math.cos(a) * dist
            iy   = self.y + math.sin(a) * dist
            self.impacts.append(_Impact(ix, iy, self._impact_size))
        if not self.audio.is_loop("fire"):
            self.audio.play("fire")

    def _spawn_barrage_missile(self):
        ax, ay   = self._air_pos()
        dx, dy   = self._mpass_dir
        nx, ny   = -dy, dx
        sx, sy   = self._mpass_start
        along    = self._mpass_t + MPASS_LEAD + random.uniform(-25, 25)
        along    = max(self._mpass_strip_lo, min(self._mpass_strip_hi, along))
        lat      = random.uniform(-MPASS_STRIP_WIDTH / 2, MPASS_STRIP_WIDTH / 2)
        target_x = sx + dx * along + nx * lat
        target_y = sy + dy * along + ny * lat
        m = _BarrageMissile(ax, ay, target_x, target_y, self._sprites["missile"])
        self._barrage_missiles.append(m)

    def _wanted_loops(self):
        s      = self.state
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
        elif s == "MPASS":
            wanted.add("fly")
        elif s in ("STILL_WARN", "STILL_FIRE"):
            wanted.add("orbit")
            if s == "STILL_FIRE" and self.audio.is_loop("fire"):
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
        self._update_barrage_missiles(dt, player, cover_rects)
        self._firing = False

        if self.state == "TAKEOFF":
            self._update_takeoff(dt, player)
            return

        if self.state == "DOWN":
            self.timer += dt
            if self.timer >= DOWN_TIME:
                self.dead_done = True
            return

        if not self._centered:
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
                self._begin_attack_sequence(player)

        elif self.state == "WARN":
            if self.timer >= cfg["warn"]:
                self.state      = "PASS"
                self.timer      = 0.0
                self.pass_t     = 0.0
                self.fire_timer = 0.0

        elif self.state == "PASS":
            self.pass_t += cfg["pass_speed"] * dt
            self._place(self.pass_start[0] + self.pass_dir[0] * self.pass_t,
                        self.pass_start[1] + self.pass_dir[1] * self.pass_t)
            cursor = self.pass_t + self.lead
            if self.strip_lo <= cursor <= self.strip_hi:
                self._firing = True
                self.fire_timer -= dt
                n = 0
                while self.fire_timer <= 0 and n < 10:
                    self._fire(cursor)
                    self.fire_timer += FIRE_INTERVAL
                    n += 1
            if self.pass_t >= self.pass_len:
                gap = cfg.get("gap", 0.0)
                if gap > 0 and self._attack_idx < len(self._attack_seq):
                    self.state = "GAP"
                    self.timer = 0.0
                else:
                    self._launch_next_attack(player)

        elif self.state == "GAP":
            if self.timer >= cfg.get("gap", 0.0) + GAP_PAUSE_EXTRA:
                self._launch_next_attack(player)

        elif self.state == "STILL_WARN":
            if self.timer >= STILL_WARN_TIME:
                self.state              = "STILL_FIRE"
                self.timer              = 0.0
                self._still_burst_timer = 0.0
                self._still_player_pos  = player.rect.center

        elif self.state == "STILL_FIRE":
            if STILL_FOLLOW:
                tx, ty = player.rect.center
                dx, dy = tx - self.x, ty - self.y
                d      = math.hypot(dx, dy)
                if d > 0:
                    self._heading = math.atan2(dy / d, dx / d)
            self._still_burst_timer -= dt
            if self._still_burst_timer <= 0:
                self._fire_still(player.rect.center)
                self._still_burst_timer = STILL_BURST_GAP
            if self.timer >= STILL_DURATION:
                self._launch_next_attack(player)

        elif self.state == "MPASS_WARN":
            if self.timer >= MPASS_WARN_TIME:
                self.state        = "MPASS"
                self.timer        = 0.0
                self._mpass_t     = 0.0
                self._mpass_timer = 0.0

        elif self.state == "MPASS":
            self._mpass_t += MPASS_SPEED * dt
            self._place(self._mpass_start[0] + self._mpass_dir[0] * self._mpass_t,
                        self._mpass_start[1] + self._mpass_dir[1] * self._mpass_t)
            self._mpass_timer -= dt
            if self._mpass_timer <= 0:
                self._spawn_barrage_missile()
                self._mpass_timer = MPASS_INTERVAL
            if self._mpass_t >= self._mpass_len:
                self._launch_next_attack(player)

    def _update_barrage_missiles(self, dt, player, cover_rects=()):
        covers   = list(cover_rects) if cover_rects else []
        in_cover = player.is_hidden or (covers and player.rect.collidelist(covers) != -1)
        
        alive = []
        for m in self._barrage_missiles:
            m.update(dt)
            if m.exploded:
                self._missile_explosions.append(
                    _MissileExplosion(m.target_x, m.target_y, self._sprites["explo"])
                )
                # Si el jugador NO está en cobertura y se encuentra dentro del radio de explosión, recibe daño severo
                if not in_cover:
                    dx = player.rect.centerx - m.target_x
                    dy = player.rect.centery - m.target_y
                    if math.hypot(dx, dy) <= MPASS_EXPLODE_R + 12:
                        player.take_damage(MPASS_DAMAGE)
            else:
                alive.append(m)
        self._barrage_missiles = alive

        for e in self._missile_explosions:
            e.update(dt)
        self._missile_explosions = [e for e in self._missile_explosions if not e.done]

    def _update_impacts(self, dt, player, cover_rects):
        covers   = list(cover_rects) if cover_rects else []
        in_cover = player.is_hidden or (covers and player.rect.collidelist(covers) != -1)
        for im in self.impacts[:]:
            im.life -= dt
            if im.life <= 0:
                self.impacts.remove(im)
            elif not in_cover and im.rect.colliderect(player.rect):
                player.take_damage(IMPACT_DAMAGE)

    def _update_takeoff(self, dt, player):
        if self._skip_takeoff:
            self._finish_takeoff(player)
            return
        if not self.cutscene_go:
            return
        self.timer += dt
        if self.tk_phase == "HOLD":
            if self.timer >= TAKEOFF_HOLD:
                self.tk_phase, self.timer = "SPIN", 0.0
        elif self.tk_phase == "SPIN":
            if self.timer >= TAKEOFF_SPIN:
                self.tk_phase, self.timer = "RISE", 0.0
        elif self.tk_phase == "RISE":
            self._tk_vel  = min(TAKEOFF_MAX_SPEED, self._tk_vel + TAKEOFF_ACCEL * dt)
            self.altitude += self._tk_vel * dt
            if self.altitude >= TAKEOFF_RISE_DISTANCE:
                self.tk_phase, self.timer = "WAIT", 0.0
        elif self.tk_phase == "WAIT":
            if self.timer >= TAKEOFF_AFTER:
                self._finish_takeoff(player)

    def _finish_takeoff(self, player):
        self.altitude     = 0.0
        self.takeoff_done = True
        self.radius       = self.cfg["radius"]
        self.cx, self.cy  = self._clamp_center(*player.rect.center)
        self._centered    = True
        self._begin_enter((self.x, self.y))
        self._dir_idx     = DOWN_IDX
        self._turn_timer  = 0.0

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
        r = img.get_rect(center=(int(sx), int(sy)))
        surface.blit(img, r)
        self._sprite_rect = r

    def draw_ground(self, surface, camera):
        ticks = pygame.time.get_ticks()
        self._sprite_rect = None

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

        # Franja de peligro para la pasada normal (Fase 1)
        if DEBUG["strip_box"] and self.state in ("WARN", "PASS"):
            dx, dy = self.pass_dir
            nx, ny = -dy, dx
            sx, sy = self.pass_start
            hw     = STRIP_WIDTH / 2

            def pt(along, lat):
                return camera.apply_pos(sx + dx * along + nx * lat,
                                        sy + dy * along + ny * lat)

            pygame.draw.line(surface, (120, 35, 30), pt(0, 0), pt(self.strip_lo, 0), 1)
            fast = self.state == "PASS" or self.timer > self.cfg["warn"] * 0.6
            if (ticks // (60 if fast else 130)) % 2 == 0:
                corners = [pt(self.strip_lo, -hw), pt(self.strip_hi, -hw),
                           pt(self.strip_hi,  hw), pt(self.strip_lo,  hw)]
                pygame.draw.lines(surface, (230, 60, 50), True, corners, 2)

        # Franja anticipatoria clara y rectangular para el barrage de misiles (MPASS_WARN / MPASS)
        if self.state in ("MPASS_WARN", "MPASS"):
            dx, dy = self._mpass_dir
            nx, ny = -dy, dx
            sx, sy = self._mpass_start
            hw     = MPASS_STRIP_WIDTH / 2

            def pt_m(along, lat):
                return camera.apply_pos(sx + dx * along + nx * lat,
                                        sy + dy * along + ny * lat)

            # Dibujamos un rectángulo anticipatorio parpadeante en el suelo que avisa la zona de impacto inesquivable
            if (ticks // 100) % 2 == 0:
                corners = [
                    pt_m(self._mpass_strip_lo, -hw),
                    pt_m(self._mpass_strip_hi, -hw),
                    pt_m(self._mpass_strip_hi,  hw),
                    pt_m(self._mpass_strip_lo,  hw)
                ]
                # Superficie semitransparente para marcar el área de muerte de los misiles
                poly_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
                pygame.draw.polygon(poly_surf, (255, 70, 30, 80), corners)
                pygame.draw.polygon(poly_surf, (255, 180, 50, 200), corners, 3)
                surface.blit(poly_surf, (0, 0))

        # Indicador visual para STILL (cono semitransparente)
        if self.state in ("STILL_WARN", "STILL_FIRE"):
            sx, sy       = camera.apply_pos(self.x, self.y)
            angle_center = self._heading
            cone_rad     = math.radians(STILL_CONE_HALF)
            a1, a2       = angle_center - cone_rad, angle_center + cone_rad
            steps        = 10
            pts          = [(sx, sy)]
            for i in range(steps + 1):
                a  = a1 + (a2 - a1) * i / steps
                px = sx + math.cos(a) * STILL_RANGE
                py = sy + math.sin(a) * STILL_RANGE
                pts.append((px, py))
            color     = (230, 60, 50, 60) if self.state == "STILL_FIRE" else (230, 130, 50, 40)
            cone_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(cone_surf, color, pts)
            surface.blit(cone_surf, (0, 0))

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

        for m in self._barrage_missiles:
            m.draw(surface, camera)
        for e in self._missile_explosions:
            e.draw(surface, camera)

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
            rng    = random.Random(ticks // 120)
            explo  = self._sprites["explo"]
            for i in range(4):
                ox, oy = rng.randint(-40, 40), rng.randint(-40, 40)
                if explo:
                    img = explo[((ticks // 120) + i) % len(explo)]
                    surface.blit(img, img.get_rect(center=(int(sx + ox), int(sy + oy))))
                else:
                    pygame.draw.circle(surface, (255, 150, 40),
                                       (int(sx + ox), int(sy + oy)), rng.randint(8, 18))

        if HIND_DEBUG and self.state != "TAKEOFF":
            self._draw_debug(surface, camera)
        self._draw_debug_boxes(surface, camera)

    def _draw_placeholder(self, surface, sx, sy, ticks, color):
        a    = self._heading
        c, s = math.cos(a), math.sin(a)
        nose  = (sx + c * 40, sy + s * 40)
        left  = (sx - c * 30 - s * 22, sy - s * 30 + c * 22)
        right = (sx - c * 30 + s * 22, sy - s * 30 - c * 22)
        pygame.draw.polygon(surface, color, [nose, left, right])
        ra = ticks * 0.04
        for off in (0, math.pi / 2):
            rx, ry = math.cos(ra + off) * 48, math.sin(ra + off) * 48
            pygame.draw.line(surface, (110, 110, 110),
                             (sx - rx, sy - ry), (sx + rx, sy + ry), 2)

    def _draw_debug_boxes(self, surface, camera):
        if DEBUG["impact_hitbox"]:
            for im in self.impacts:
                x, y = camera.apply_pos(im.rect.x, im.rect.y)
                pygame.draw.rect(surface, (255, 255, 0),
                                 (int(x), int(y), im.rect.w, im.rect.h), 1)
        if DEBUG["hind_hitbox"]:
            x, y = camera.apply_pos(self.rect.x, self.rect.y)
            pygame.draw.rect(surface, (0, 255, 0),
                             (int(x), int(y), self.rect.w, self.rect.h), 1)
        if DEBUG["sprite_rect"] and self._sprite_rect is not None:
            pygame.draw.rect(surface, (255, 0, 255), self._sprite_rect, 1)
        if DEBUG["player_hitbox"] and self._player_rect is not None:
            r    = self._player_rect
            x, y = camera.apply_pos(r.x, r.y)
            pygame.draw.rect(surface, (0, 200, 255),
                             (int(x), int(y), r.w, r.h), 1)

    def _draw_debug(self, surface, camera):
        ccx, ccy = camera.apply_pos(self.cx, self.cy)
        pygame.draw.circle(surface, (0, 255, 255), (int(ccx), int(ccy)), int(self.radius), 1)
        pygame.draw.circle(surface, (0, 255, 255), (int(ccx), int(ccy)), 3)
        sx, sy   = camera.apply_pos(self.x, self.y)
        label    = f"{self.state} F{self.phase} HP{self.health} {self._dir_name()}"
        surface.blit(self._dbg_font.render(label, True, (255, 255, 255)), (sx - 40, sy - 50))


# ─── BARRA DE VIDA DEL JEFE ───────────────────────────────────────────────────
class BossHealthBar:
    def __init__(self):
        self.label_font  = pygame.font.Font(None, BOSS_BAR_LABEL_SIZE)
        self.number_font = pygame.font.Font(None, HEALTH_NUMBER_SIZE)
        self.trail       = 1.0
        self.trail_delay = 0.0
        self.last_ratio  = 1.0

    def update(self, dt, ratio):
        if ratio < self.last_ratio:
            self.trail_delay = 0.45
        self.last_ratio = ratio
        if self.trail_delay > 0:
            self.trail_delay -= dt
        elif self.trail > ratio:
            self.trail = max(ratio, self.trail - 0.25 * dt)
        else:
            self.trail = ratio

    def draw(self, surface, boss):
        W     = BOSS_BAR_WIDTH
        H     = BOSS_BAR_HEIGHT
        ratio = max(0.0, min(1.0, boss.health / boss.max_health))
        sw    = surface.get_width()

        if BOSS_BAR_ANCHOR == "center":
            x = (sw - W) // 2
        elif BOSS_BAR_ANCHOR == "left":
            x = HEALTH_BAR_X
        else:
            group_w = W + (HEALTH_NUMBER_GAP + HEALTH_NUMBER_RESERVED
                           if BOSS_BAR_SHOW_NUMBER else 0)
            x = sw - HEALTH_BAR_X - group_w
        x += BOSS_BAR_OFFSET[0]
        y  = HEALTH_BAR_Y + BOSS_BAR_OFFSET[1]

        label_y = y - self.label_font.get_height() - 5
        draw_text_shadow(surface, self.label_font, HIND_NAME, COLOR_TEXT, x, label_y)
        if BOSS_BAR_SHOW_PHASE:
            draw_text_shadow(surface, self.label_font, f"FASE {boss.phase}", BOSS_BAR_LINE,
                             x + W, label_y, align_right=True)

        pygame.draw.rect(surface, COLOR_HEALTH_SHADOW, (x - 4, y - 4, W + 8, H + 8))
        pygame.draw.rect(surface, BOSS_BAR_FRAME,      (x - 3, y - 3, W + 6, H + 6), 2)
        pygame.draw.rect(surface, BOSS_BAR_EMPTY,      (x, y, W, H))
        fill_width = int(W * ratio)
        if BOSS_BAR_TRAIL:
            tw = int(W * self.trail)
            if tw > fill_width:
                pygame.draw.rect(surface, BOSS_BAR_TRAIL_COLOR, (x, y, tw, H))
        if fill_width > 0:
            pygame.draw.rect(surface, BOSS_BAR_FILL,     (x, y, fill_width, H))
            pygame.draw.rect(surface, BOSS_BAR_HIGHLIGHT, (x, y, fill_width, H // 2))

        line_y = y + H + 8
        pygame.draw.line(surface, COLOR_HEALTH_SHADOW, (x, line_y + 1), (x + W, line_y + 1), 2)
        pygame.draw.line(surface, BOSS_BAR_LINE,        (x, line_y),     (x + W, line_y),     1)
        for i in range(HEALTH_TICKS + 1):
            tick_x = x + int(W * i / HEALTH_TICKS)
            pygame.draw.line(surface, BOSS_BAR_LINE, (tick_x, line_y - 3), (tick_x, line_y), 1)
        for frac in (1 / 3, 2 / 3):
            tick_x = x + int(W * frac)
            pygame.draw.line(surface, COLOR_HEALTH_SHADOW,
                             (tick_x + 1, line_y - 7), (tick_x + 1, line_y + 1), 2)
            pygame.draw.line(surface, COLOR_HEALTH_SHADOW,
                             (tick_x,     line_y - 7), (tick_x,     line_y),     2)

        if BOSS_BAR_SHOW_NUMBER:
            number_right = x + W + HEALTH_NUMBER_GAP + HEALTH_NUMBER_RESERVED
            number_h     = self.number_font.get_height()
            number_y     = y + (H + 8) // 2 - number_h // 2
            draw_text_shadow(surface, self.number_font, str(boss.health), COLOR_TEXT,
                             number_right, number_y, align_right=True)