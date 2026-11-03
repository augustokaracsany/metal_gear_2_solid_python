import math
import pygame
from src.bullet import play_ricochet            # mismo ricochet que las balas de Snake
from src.settings import BULLET_HIT_PADDING

# ═══════════════════════════════════════════════════════════════════════════
#  CONFIG  (tocá solo esto)
# ═══════════════════════════════════════════════════════════════════════════
BULLET_RANGE    = 750      # px máximos que recorre antes de desaparecer
STEP_PX         = 4        # la bala avanza de a pasos de este tamaño (no atraviesa nada)
HIT_SIZE        = 4        # lado del hitbox de la bala (px)
TRACER_LENGTH   = 9        # largo de la estela dibujada (px)
TRACER_WIDTH    = 2
COLOR_TRACER    = (255, 215, 110)
COLOR_HEAD      = (255, 255, 235)
AUDIBLE_RADIUS  = 450      # el ricochet solo suena si el impacto está cerca de Snake
# ═══════════════════════════════════════════════════════════════════════════


class enemyBullet(pygame.sprite.Sprite):
    """Bala de guardia.

    Igual que las de Snake: su posición LÓGICA (x, y) está en el plano del piso, donde viven
    los hitboxes, y viaja recta hacia Snake. Solo se DIBUJA desplazada (draw_dx, draw_dy) para
    que salga de la altura del arma. Choca con paredes (ricochet) y no atraviesa a Snake
    aunque el FPS caiga, porque avanza de a pasos.
    """

    def __init__(self, x, y, vx, vy, draw_dx=0.0, draw_dy=0.0, damage=20):
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.draw_dx = draw_dx
        self.draw_dy = draw_dy
        self.damage = damage
        self.hit_target = False           # True cuando alcanzó a Snake (Game aplica el daño y la quita)
        self.distance_traveled = 0.0

        speed = math.hypot(vx, vy) or 1.0
        self._ux = vx / speed
        self._uy = vy / speed

        self.rect = pygame.Rect(0, 0, HIT_SIZE, HIT_SIZE)
        self.rect.center = (round(self.x), round(self.y))

    def update(self, dt, walls=None, target=None):
        """walls: lista de Rect de paredes. target: hitbox de Snake (pygame.Rect)."""
        dist = math.hypot(self.vx * dt, self.vy * dt)
        steps = max(1, math.ceil(dist / STEP_PX))
        sx = self.vx * dt / steps
        sy = self.vy * dt / steps
        hit_rect = target.inflate(BULLET_HIT_PADDING, BULLET_HIT_PADDING) if target is not None else None

        for _ in range(steps):
            self.x += sx
            self.y += sy
            self.rect.center = (round(self.x), round(self.y))

            if walls and self.rect.collidelist(walls) != -1:
                if (target is not None
                        and math.hypot(self.x - target.centerx, self.y - target.centery) <= AUDIBLE_RADIUS):
                    play_ricochet()
                self.kill()
                return

            if hit_rect is not None and self.rect.colliderect(hit_rect):
                self.hit_target = True
                return

        self.distance_traveled += dist
        if self.distance_traveled >= BULLET_RANGE:
            self.kill()

    def draw_with_camera(self, surface, camera):
        ox, oy = camera.camera_rect.x, camera.camera_rect.y
        hx = self.x + self.draw_dx + ox
        hy = self.y + self.draw_dy + oy
        tx = hx - self._ux * TRACER_LENGTH
        ty = hy - self._uy * TRACER_LENGTH
        pygame.draw.line(surface, COLOR_TRACER, (round(tx), round(ty)), (round(hx), round(hy)), TRACER_WIDTH)
        pygame.draw.rect(surface, COLOR_HEAD, (round(hx) - 1, round(hy) - 1, 2, 2))