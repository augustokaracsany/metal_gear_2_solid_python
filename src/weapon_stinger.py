"""FIM-92 Stinger: mira con mouse, lock-on sobre el Hind, misil guiado y auto-desequipado.

Cambios respecto a la versión anterior:
  - Sprite del misil por dirección (8 dirs, missile-<dir>.png).
  - Sonido de vuelo del misil (loop mientras viaja, se corta al detonar).
  - Guiado confiable: el misil llega siempre. Se calcula dirección directa al objetivo
    cada frame con lerp fuerte; ya no puede orbitar.

Requisitos del objetivo (el Hind):
  - .rect, .take_hit(n, force=True) o .take_damage(n)
  - .air_pos        posición real en el aire (x, y)  [si falta: rect.center - HIND_ALTITUDE]
  - .targetable     (opcional) False = no se puede fijar (despegando / destruido)
  - .health / .hp   (opcional)
"""
import math
import os
import pygame
from pygame.math import Vector2
from src import weapon_settings as WS
from src.weapons import load_sound, load_icon, play

SEARCH, LOCKING, LOCKED, FIRED = range(4)
DIRS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}

COLOR_SEARCH  = (230, 235, 225)
COLOR_LOCKING = (255, 200, 60)
COLOR_LOCKED  = (255, 70,  60)

# ── Sprites del misil ─────────────────────────────────────────────────────────
# Carpeta donde están missile-right.png, missile-upleft.png, etc.
MISSILE_SPRITE_DIR   = "assets/sprites/hind-d"
MISSILE_SPRITE_SCALE = 2

# Nombres de los 8 sprites direccionales (clockwise desde right=0°)
_MISSILE_DIR_NAMES = [
    "right", "downright", "down", "downleft",
    "left",  "upleft",    "up",   "upright",
]

# Ángulo (rad) de cada dirección, en el sistema pygame (y hacia abajo = positivo)
_MISSILE_DIR_ANGLES = [
    0,                  # right
    math.pi / 4,        # downright
    math.pi / 2,        # down
    3 * math.pi / 4,    # downleft
    math.pi,            # left
    -3 * math.pi / 4,   # upleft
    -math.pi / 2,       # up
    -math.pi / 4,       # upright
]

# Velocidad de giro del guiado: fracción del ángulo restante que se corrige por frame.
# 1.0 = corrección instantánea (sin inercia); 0.15 = suave pero nunca orbita.
MISSILE_STEER_FACTOR = 0.25    # por frame a 60 fps. Ajustable.


def _load_missile_sprites():
    """Carga los 8 PNGs del misil. Si falta alguno devuelve None para esa dirección."""
    sprites = {}
    for name in _MISSILE_DIR_NAMES:
        path = os.path.join(MISSILE_SPRITE_DIR, f"missile-{name}.png")
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                w = int(img.get_width() * MISSILE_SPRITE_SCALE)
                h = int(img.get_height() * MISSILE_SPRITE_SCALE)
                sprites[name] = pygame.transform.scale(img, (w, h))
            except Exception as e:
                print(f"[Stinger] No se pudo cargar {path}: {e}")
                sprites[name] = None
        else:
            sprites[name] = None
    missing = [n for n, v in sprites.items() if v is None]
    if missing:
        print(f"[Stinger] Aviso: faltan sprites de misil para {missing} en '{MISSILE_SPRITE_DIR}'")
    return sprites


# Cache global: se carga la primera vez que se crea un misil
_MISSILE_SPRITES = None


def _get_missile_sprites():
    global _MISSILE_SPRITES
    if _MISSILE_SPRITES is None:
        _MISSILE_SPRITES = _load_missile_sprites()
    return _MISSILE_SPRITES


def _dir_for_angle(angle_rad):
    """Devuelve el nombre de dirección más cercano al ángulo dado."""
    best, best_diff = _MISSILE_DIR_NAMES[0], float("inf")
    for name, a in zip(_MISSILE_DIR_NAMES, _MISSILE_DIR_ANGLES):
        diff = abs(math.atan2(math.sin(angle_rad - a), math.cos(angle_rad - a)))
        if diff < best_diff:
            best, best_diff = name, diff
    return best


# ====================================================================== HELPERS
def _is_alive(target):
    targetable = getattr(target, "targetable", None)
    if targetable is not None:
        return bool(targetable)
    for attr in ("health", "hp"):
        value = getattr(target, attr, None)
        if value is not None:
            return value > 0
    return True


def _ground_pos(target):
    return Vector2(target.rect.center)


def _air_pos(target):
    if hasattr(target, "air_pos"):
        v = target.air_pos() if callable(target.air_pos) else target.air_pos
        return Vector2(v)
    return Vector2(target.rect.center) - Vector2(0, WS.HIND_ALTITUDE)


def _segment_distance(p, a, b):
    ab = b - a
    l2 = ab.length_squared()
    if l2 == 0:
        return p.distance_to(a)
    t = max(0.0, min(1.0, (p - a).dot(ab) / l2))
    return p.distance_to(a + ab * t)


def _font(size):
    try:
        return pygame.font.Font(WS.UI_FONT_BOLD, size)
    except Exception:
        return pygame.font.Font(None, size + 8)


_explosion_snd = None


def _play_explosion():
    global _explosion_snd
    if _explosion_snd is None:
        _explosion_snd = load_sound(WS.STINGER_SOUND_DIR, "explosion") or False
    if _explosion_snd:
        _explosion_snd.play()


# ====================================================================== PROYECTILES
class Explosion(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.pos = Vector2(pos)
        self.age = 0.0
        self.rect = pygame.Rect(0, 0, 2, 2)
        self.rect.center = (round(pos.x), round(pos.y))

    def update(self, dt, walls=None, enemies=None, bounds=None):
        self.age += dt
        if self.age >= WS.EXPLOSION_LIFE:
            self.kill()

    def draw_with_camera(self, surface, camera):
        t = min(1.0, self.age / WS.EXPLOSION_LIFE)
        r = max(2, int(WS.EXPLOSION_RADIUS * (0.3 + 0.7 * t)))
        alpha = int(255 * (1 - t))
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 120, 30, alpha), (r, r), r)
        pygame.draw.circle(s, (255, 220, 90, alpha), (r, r), int(r * 0.6))
        pygame.draw.circle(s, (255, 255, 230, alpha), (r, r), int(r * 0.25))
        surface.blit(s, (self.pos.x + camera.camera_rect.x - r,
                         self.pos.y + camera.camera_rect.y - r))


class StingerMissile(pygame.sprite.Sprite):
    """
    Misil guiado: vuela hacia la posición AÉREA del Hind.

    Guiado: cada frame se calcula el ángulo directo al objetivo y se mezcla
    con el ángulo actual usando MISSILE_STEER_FACTOR. Esto garantiza que
    el misil siempre converge y nunca orbita, aunque el Hind esté cerca.
    """

    def __init__(self, start, target, damage, flight_sound=None):
        super().__init__()
        self.pos       = Vector2(start)
        self.target    = target
        self.damage    = damage
        self.aim_point = _air_pos(target)
        self.speed     = WS.MISSILE_START_SPEED
        self.age       = 0.0
        self.trail     = []
        self.trail_timer = 0.0

        # Dirección inicial: apunta directo al objetivo
        desired = self.aim_point - self.pos
        self.dir = desired.normalize() if desired.length() > 0.001 else Vector2(0, -1)
        self._angle = math.atan2(self.dir.y, self.dir.x)

        # Sprites de dirección
        self._sprites = _get_missile_sprites()

        # Sonido de vuelo (loop)
        self._flight_channel = None
        if flight_sound:
            try:
                self._flight_channel = flight_sound.play(loops=-1)
            except Exception:
                pass

        self.rect = pygame.Rect(0, 0, 8, 8)
        self.rect.center = (round(self.pos.x), round(self.pos.y))

    def _stop_flight_sound(self):
        if self._flight_channel:
            try:
                self._flight_channel.stop()
            except Exception:
                pass
            self._flight_channel = None

    def update(self, dt, walls=None, enemies=None, bounds=None):
        self.age += dt
        self.speed = min(WS.MISSILE_MAX_SPEED, self.speed + WS.MISSILE_ACCEL * dt)

        # Actualizar objetivo
        if self.target is not None and _is_alive(self.target):
            self.aim_point = _air_pos(self.target)

        to_target = self.aim_point - self.pos
        dist = to_target.length()

        # Condiciones de impacto
        if dist <= WS.MISSILE_HIT_RADIUS or dist <= self.speed * dt or self.age > WS.MISSILE_LIFETIME:
            self._detonate()
            return

        # Guiado: ángulo directo al objetivo, mezclado con el ángulo actual
        target_angle = math.atan2(to_target.y, to_target.x)
        angle_diff = math.atan2(
            math.sin(target_angle - self._angle),
            math.cos(target_angle - self._angle)
        )
        # Corrección proporcional: a más distancia, más agresiva; de cerca, suave
        steer = MISSILE_STEER_FACTOR * (1.0 + 2.0 / max(1.0, dist / 50.0))
        self._angle += angle_diff * min(1.0, steer)
        self.dir = Vector2(math.cos(self._angle), math.sin(self._angle))

        self.pos += self.dir * self.speed * dt
        self.rect.center = (round(self.pos.x), round(self.pos.y))

        # Estela
        self.trail_timer -= dt
        if self.trail_timer <= 0:
            self.trail.append([Vector2(self.pos), 0.0])
            self.trail_timer = 0.02
        for puff in self.trail:
            puff[1] += dt
        self.trail = [p for p in self.trail if p[1] < WS.MISSILE_TRAIL_LIFE]

    def _detonate(self):
        self._stop_flight_sound()
        hit = (self.target is not None
               and _is_alive(self.target)
               and self.age <= WS.MISSILE_LIFETIME)
        if hit:
            if hasattr(self.target, "take_hit"):
                self.target.take_hit(self.damage, force=True)
            else:
                self.target.take_damage(self.damage)
        for group in self.groups():
            group.add(Explosion(self.aim_point if hit else self.pos))
        _play_explosion()
        self.kill()

    def draw_with_camera(self, surface, camera):
        ox, oy = camera.camera_rect.x, camera.camera_rect.y

        # Estela
        for p, age in self.trail:
            t = age / WS.MISSILE_TRAIL_LIFE
            shade = int(235 - 140 * t)
            pygame.draw.circle(surface, (shade, shade, shade),
                               (int(p.x + ox), int(p.y + oy)), int(2 + 4 * t))

        # Sprite direccional
        dir_name = _dir_for_angle(self._angle)
        img = self._sprites.get(dir_name) if self._sprites else None
        if img:
            surface.blit(img, img.get_rect(center=(int(self.pos.x + ox), int(self.pos.y + oy))))
        else:
            # Fallback: línea con punto (igual que antes)
            tip  = self.pos + self.dir * 8
            tail = self.pos - self.dir * 8
            pygame.draw.line(surface, (235, 235, 230),
                             (tail.x + ox, tail.y + oy), (tip.x + ox, tip.y + oy), 3)
            pygame.draw.circle(surface, (220, 50, 40),  (int(tip.x  + ox), int(tip.y  + oy)), 2)
            pygame.draw.circle(surface, (255, 170, 40), (int(tail.x + ox), int(tail.y + oy)), 3)


# ====================================================================== LANZADOR
class StingerLauncher:
    kind = "launcher"
    id = "stinger"
    name = "FIM-92 STINGER"
    sprite_set = "stinger"
    blocks_movement = True
    hud_tag = ""             # Sin etiqueta en el HUD (no es CQC ni DMG)

    def __init__(self):
        self.missiles = 0
        self.icon = load_icon("stinger")

        # Sonidos del lanzador
        self.snd_lock  = load_sound(WS.STINGER_SOUND_DIR, "lock_on")
        self.snd_ready = load_sound(WS.STINGER_SOUND_DIR, "ready_to_fire")
        self.snd_lost  = load_sound(WS.STINGER_SOUND_DIR, "lost")
        self.snd_launch = load_sound(WS.STINGER_SOUND_DIR, "launch")
        self.snd_empty  = load_sound(WS.STINGER_SOUND_DIR, "empty")

        # Sonido de vuelo del misil (loop mientras el misil viaja)
        self.snd_flight = load_sound(WS.STINGER_SOUND_DIR, "missile_flight")

        self.font = _font(20)
        self._chan = None
        self._reset()

    def _reset(self):
        self.state = SEARCH
        self.lock_timer  = 0.0
        self.grace       = 0.0
        self.beep_timer  = 0.0
        self.aim_offset  = Vector2()
        self.cam_offset  = Vector2()
        self.facing      = "DOWN"
        self.fire_click  = False
        self.lost_flash  = 0.0
        self.deny_flash  = 0.0
        self.deny_text   = ""
        self._aim_world  = None
        self._target_air = None

    # ── equipar / desequipar / suspender ─────────────────────────────────────
    def on_equip(self, player):
        self._reset()
        self.facing = getattr(player, "facing", "DOWN")
        dx, dy = DIRS.get(self.facing, (0, 1))
        self.aim_offset = Vector2(dx, dy) * 60
        self._aim_world = Vector2(player.rect.center) + self.aim_offset
        self.resume()

    def on_unequip(self, player):
        self.suspend()
        if self._chan:
            self._chan.stop()
        self.cam_offset = Vector2()

    def suspend(self):
        pygame.mouse.set_visible(True)
        pygame.event.set_grab(False)

    def resume(self):
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)
        pygame.mouse.get_rel()

    # ── entrada ───────────────────────────────────────────────────────────────
    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.aim_offset += Vector2(event.rel) * WS.STINGER_SENSITIVITY
            self._clamp_aim()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.fire_click = True

    def _clamp_aim(self):
        nx = self.aim_offset.x / WS.STINGER_AIM_RANGE_X
        ny = self.aim_offset.y / WS.STINGER_AIM_RANGE_Y
        d  = math.hypot(nx, ny)
        if d > 1:
            self.aim_offset.x /= d
            self.aim_offset.y /= d

    # ── loop principal ────────────────────────────────────────────────────────
    def update(self, dt, pressed, held, shoot, player=None, target=None, projectiles=None, **_):
        fire = pressed or self.fire_click
        self.fire_click = False
        self.lost_flash = max(0.0, self.lost_flash - dt)
        self.deny_flash = max(0.0, self.deny_flash - dt)
        self.cam_offset += (self.aim_offset * WS.STINGER_CAMERA_FOLLOW - self.cam_offset) * min(1.0, 6 * dt)

        self._aim_world = Vector2(player.rect.center) + self.aim_offset
        if self.aim_offset.length() > 10:
            if abs(self.aim_offset.x) >= abs(self.aim_offset.y):
                self.facing = "RIGHT" if self.aim_offset.x > 0 else "LEFT"
            else:
                self.facing = "DOWN" if self.aim_offset.y > 0 else "UP"

        alive = target is not None and _is_alive(target)
        on_target = False
        if alive:
            ground, air = _ground_pos(target), _air_pos(target)
            self._target_air = air
            on_target = _segment_distance(self._aim_world, ground, air) <= WS.STINGER_LOCK_RADIUS
        else:
            self._target_air = None

        if not alive:
            self._lose()
        elif self.state == SEARCH:
            if on_target:
                self.state = LOCKING
                self.lock_timer = self.grace = self.beep_timer = 0.0
        elif self.state == LOCKING:
            if on_target:
                self.grace = 0.0
                self.lock_timer += dt
                self.beep_timer -= dt
                if self.beep_timer <= 0 and not (self._chan and self._chan.get_busy()):
                    self._chan = play(self.snd_lock)
                    self.beep_timer = WS.STINGER_LOCK_BEEP_INTERVAL
                if self.lock_timer >= WS.STINGER_LOCK_TIME:
                    self.state = LOCKED
                    if self._chan:
                        self._chan.stop()
                    play(self.snd_ready)
            else:
                self.grace += dt
                if self.grace > WS.STINGER_LOCK_GRACE:
                    self._lose()
        elif self.state == LOCKED:
            self.grace = 0.0 if on_target else self.grace + dt
            if self.grace > WS.STINGER_LOCK_GRACE:
                self._lose()

        if fire:
            if self.missiles <= 0:
                play(self.snd_empty)
                self._deny("SIN MISILES")
            elif self.state == LOCKED and projectiles is not None:
                self._launch(player, target, projectiles)
            else:
                self._deny("SIN LOCK-ON")

    def _lose(self):
        if self.state in (LOCKING, LOCKED):
            if self._chan:
                self._chan.stop()
            play(self.snd_lost)
            self.lost_flash = 1.2
        self.state = SEARCH
        self.lock_timer = 0.0

    def _deny(self, text):
        self.deny_text = text
        self.deny_flash = 1.0

    def _launch(self, player, target, projectiles):
        self.missiles -= 1
        start = Vector2(player.rect.center) - Vector2(0, 24)
        missile = StingerMissile(start, target, WS.STINGER_DAMAGE,
                                  flight_sound=self.snd_flight)
        projectiles.add(missile)
        play(self.snd_launch)
        self.state = SEARCH 
    # ── cámara ────────────────────────────────────────────────────────────────
    def constrain_to_screen(self, camera, vw, vh):
        if self._aim_world is None:
            return
        m  = WS.STINGER_SCREEN_MARGIN
        sx = self._aim_world.x + camera.camera_rect.x
        sy = self._aim_world.y + camera.camera_rect.y
        nsx = max(m, min(vw - m, sx))
        nsy = max(m, min(vh - m, sy))
        if nsx != sx or nsy != sy:
            self.aim_offset.x += nsx - sx
            self.aim_offset.y += nsy - sy
            self._aim_world.x += nsx - sx
            self._aim_world.y += nsy - sy

    # ── dibujo de la mira ─────────────────────────────────────────────────────
    def draw_overlay(self, surface, camera, scale=1):
        if self._aim_world is None:
            return
        ox, oy = camera.camera_rect.x, camera.camera_rect.y
        cx = int((self._aim_world.x + ox) * scale)
        cy = int((self._aim_world.y + oy) * scale)
        radius = int(WS.STINGER_LOCK_RADIUS * scale)
        color = {SEARCH: COLOR_SEARCH, LOCKING: COLOR_LOCKING,
                 LOCKED: COLOR_LOCKED, FIRED: COLOR_LOCKED}[self.state]

        pygame.draw.circle(surface, color, (cx, cy), radius, 1)
        gap, ln = 10, 22
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            pygame.draw.line(surface, color,
                             (cx + dx * gap, cy + dy * gap),
                             (cx + dx * (gap + ln), cy + dy * (gap + ln)), 2)
        pygame.draw.circle(surface, color, (cx, cy), 2)

        progress = 0.0
        if self._target_air is not None:
            tx = int((self._target_air.x + ox) * scale)
            ty = int((self._target_air.y + oy) * scale)
            if self.state == SEARCH:
                d = 9
                pygame.draw.polygon(surface, (150, 160, 150),
                                    [(tx, ty - d), (tx + d, ty), (tx, ty + d), (tx - d, ty)], 1)
            else:
                progress = 1.0 if self.state != LOCKING else min(1.0, self.lock_timer / WS.STINGER_LOCK_TIME)
                half = int(70 - 40 * progress)
                c    = 12
                for sx in (-1, 1):
                    for sy in (-1, 1):
                        px, py = tx + sx * half, ty + sy * half
                        pygame.draw.line(surface, color, (px, py), (px - sx * c, py), 2)
                        pygame.draw.line(surface, color, (px, py), (px, py - sy * c), 2)

        if self.state == LOCKING:
            text, tcolor = f"LOCK-ON {int(progress * 100)}%", COLOR_LOCKING
        elif self.state == LOCKED:
            text, tcolor = "READY TO FIRE", COLOR_LOCKED
        elif self.lost_flash > 0:
            text, tcolor = "LOST", COLOR_LOCKED
        elif self.deny_flash > 0:
            text, tcolor = self.deny_text, COLOR_LOCKING
        else:
            text, tcolor = "BUSCANDO OBJETIVO", COLOR_SEARCH

        from src.hud import draw_text_shadow
        w = self.font.size(text)[0]
        draw_text_shadow(surface, self.font, text, tcolor, cx - w // 2, cy + radius + 12)

    # ── datos para el HUD ─────────────────────────────────────────────────────
    def hud_info(self):
        return {
            "name":       self.name,
            "icon":       self.icon,
            "main":       str(self.missiles),
            "sub":        " MISILES",
            "modes":      ["LOCK-ON"],
            "mode_index": 0,
            "progress":   None,
            "low":        self.missiles <= 0,
        }