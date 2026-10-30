import math
import os
import random
import pygame
from src import weapon_settings as WS
from src.settings import (
    BULLET_SPEED, BULLET_STEP, BULLET_LENGTH, BULLET_THICKNESS,
    BULLET_DAMAGE, BULLET_COLOR, BULLET_HIT_PADDING, BULLET_DRAW_OFFSET_Y,
)

DIRECTIONS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}

# ----------------------------------------------------------------- RICOCHET
# Toma al azar un archivo que EMPIECE con RICOCHET_PREFIX (ric1.wav, ric2.ogg, ...)
# de la carpeta WS.WEAPON_SOUND_DIR (assets/audio/weapons).
RICOCHET_PREFIX     = "ric"
RICOCHET_EXTS       = (".wav", ".ogg", ".mp3")
RICOCHET_VOLUME     = 0.5     # 0..1
RICOCHET_MIN_GAP_MS = 60      # separación mínima entre ricochets (evita saturar en AUTO)

_ricochets = None             # None = todavía no se cargaron
_last_ricochet = None
_last_ricochet_ms = 0


def _load_ricochets():
    """Carga todos los ric*.wav una sola vez (perezoso: el mixer ya debe estar iniciado)."""
    global _ricochets
    sounds = []
    try:
        names = sorted(os.listdir(WS.WEAPON_SOUND_DIR))
    except OSError:
        names = []
    for name in names:
        low = name.lower()
        if low.startswith(RICOCHET_PREFIX) and low.endswith(RICOCHET_EXTS):
            try:
                snd = pygame.mixer.Sound(os.path.join(WS.WEAPON_SOUND_DIR, name))
                snd.set_volume(RICOCHET_VOLUME)
                sounds.append(snd)
            except pygame.error:
                pass
    _ricochets = sounds


def play_ricochet():
    """Suena un ricochet al azar (sin repetir el anterior). Baja prioridad:
    solo usa un canal libre, así nunca pisa los disparos."""
    global _last_ricochet, _last_ricochet_ms
    if not pygame.mixer.get_init():
        return
    if _ricochets is None:
        _load_ricochets()
    if not _ricochets:
        return
    now = pygame.time.get_ticks()
    if now - _last_ricochet_ms < RICOCHET_MIN_GAP_MS:
        return
    pool = [s for s in _ricochets if s is not _last_ricochet] or _ricochets
    snd = random.choice(pool)
    channel = pygame.mixer.find_channel()      # sin forzar: si no hay libre, no suena
    if channel is None:
        return
    channel.play(snd)
    _last_ricochet = snd
    _last_ricochet_ms = now


class Bullet(pygame.sprite.Sprite):
    def __init__(self, owner_rect, facing, damage=None, muzzle=None):
        super().__init__()
        self.dir_x, self.dir_y = DIRECTIONS[facing]
        # damage=None -> el daño base de settings (cada arma lo multiplica con su damage_mult).
        self.damage = BULLET_DAMAGE if damage is None else damage

        # Horizontal: largo x grosor. Vertical: grosor x largo.
        if self.dir_x != 0:
            width, height = BULLET_LENGTH, BULLET_THICKNESS
        else:
            width, height = BULLET_THICKNESS, BULLET_LENGTH

        # Posición LÓGICA (colisiones): justo delante del hitbox, como siempre.
        # Los hitboxes de paredes y enemigos están a nivel del piso, por eso la
        # bala NO sube hasta la altura del arma: solo se DIBUJA ahí.
        self.cx = float(owner_rect.centerx + self.dir_x * (owner_rect.width // 2 + 4))
        self.cy = float(owner_rect.centery + self.dir_y * (owner_rect.height // 2 + 4))

        # Posición VISUAL: la bala se dibuja saliendo de la boca del cañón (muzzle).
        #   draw_dx / draw_dy = desplazamiento fijo entre la posición lógica y la dibujada.
        #   _show_from_x      = en disparos horizontales no se dibuja hasta pasar la boca.
        self.draw_dx = 0.0
        self.draw_dy = float(-BULLET_DRAW_OFFSET_Y)    # sin muzzle: el offset global de antes
        self._show_from_x = None
        if muzzle is not None:
            mx, my = muzzle
            self.draw_dy = my - self.cy
            if self.dir_x != 0:
                self._show_from_x = mx
            else:
                self.draw_dx = mx - self.cx

        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = (round(self.cx), round(self.cy))

    def update(self, dt, walls, enemies, bounds):
        # Mueve la bala de a pasos chicos y se elimina si choca con algo.
        distance = BULLET_SPEED * dt
        steps = max(1, math.ceil(distance / BULLET_STEP))
        step_distance = distance / steps

        for _ in range(steps):
            self.cx += self.dir_x * step_distance
            self.cy += self.dir_y * step_distance
            self.rect.center = (round(self.cx), round(self.cy))

            # Salió del mapa.
            if not bounds.contains(self.rect):
                self.kill()
                return

            # Chocó con una pared -> ricochet.
            for wall in walls:
                if self.rect.colliderect(wall):
                    play_ricochet()
                    self.kill()
                    return

            # Chocó con un enemigo.
            for enemy in enemies:
                if self.rect.colliderect(enemy.rect.inflate(BULLET_HIT_PADDING, BULLET_HIT_PADDING)):
                    enemy.take_damage(self.damage)
                    self.kill()
                    return

    def draw_with_camera(self, surface, camera):
        # Horizontal: invisible hasta que pasa la boca del cañón.
        if self._show_from_x is not None:
            if self.dir_x > 0 and self.cx < self._show_from_x:
                return
            if self.dir_x < 0 and self.cx > self._show_from_x:
                return
        draw_rect = self.rect.move(camera.camera_rect.x + round(self.draw_dx),
                                   camera.camera_rect.y + round(self.draw_dy))
        pygame.draw.rect(surface, BULLET_COLOR, draw_rect)