"""Radar estilo Soliton: mapa en miniatura, conos de visión, guardias y Snake.

Tamaño FIJO (igual al recuadro de armas): si el mapa es más chico que el radar se dibuja
centrado sobre el fondo oscuro; si es más grande, la ventana sigue al jugador.

Uso desde Game:
    self.radar = Radar(alerted_states=("ALERT", "CHASE"))
    self.radar.build(map.width, map.height, walls)     # al cargar un nivel
    self.radar.clear()                                 # si el nivel no tiene mapa
    self.radar.draw(surface, player, enemies_group)    # cada frame, en la pantalla real
"""
import math
import pygame
from src.weapon_hud import SLOT_W, SLOT_H

# ═══════════════════════════════════════════════════════════════════════════
#  CONFIG  (tocá solo esto)
# ═══════════════════════════════════════════════════════════════════════════
RADAR_W      = SLOT_W        # mismo tamaño que el recuadro de armas (222)
RADAR_H      = SLOT_H        # (143)
RADAR_SCALE  = 0.15          # 1 px del radar = ~6,7 px del mapa
RADAR_MARGIN = 20            # separación con el borde de la pantalla (arriba a la derecha)

DOT_SIZE     = 4             # lado de los puntos de guardias y jugador

COLOR_VOID   = (0, 12, 0)    # fuera del mapa
COLOR_FLOOR  = (0, 25, 0)    # piso del mapa
COLOR_WALL   = (0, 150, 0)   # paredes / colisiones
COLOR_BORDER = (0, 200, 0)

CONE_ALPHA        = 90
COLOR_CONE_CALM   = (0, 255, 0)
COLOR_CONE_ALERT  = (255, 0, 0)
COLOR_GUARD_CALM  = (255, 200, 0)
COLOR_GUARD_ALERT = (255, 40, 40)

COLOR_PLAYER_A    = (255, 255, 255)   # el jugador parpadea suave entre A y B
COLOR_PLAYER_B    = (110, 170, 110)
PLAYER_BLINK_MS   = 180               # más chico = parpadeo más rápido
# ═══════════════════════════════════════════════════════════════════════════


def _view_origin(center, map_len, view_len):
    """Esquina de la ventana en un eje. Mapa chico: centrado (queda margen oscuro)."""
    if map_len <= view_len:
        return (map_len - view_len) // 2
    return max(0, min(center - view_len // 2, map_len - view_len))


def _lerp_color(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


class Radar:
    def __init__(self, alerted_states=("ALERT", "CHASE")):
        self.alerted_states = tuple(alerted_states)
        self.map_surface = None
        # Superficies reutilizadas en cada frame (no se crean de nuevo).
        self._view = pygame.Surface((RADAR_W, RADAR_H))
        self._cones = pygame.Surface((RADAR_W, RADAR_H), pygame.SRCALPHA)

    # ── carga del nivel ──────────────────────────────────────────────────────
    def build(self, map_width, map_height, walls):
        """Pinta UNA SOLA VEZ el mapa en miniatura (paredes sobre el piso)."""
        s = RADAR_SCALE
        surf = pygame.Surface((max(1, int(map_width * s)), max(1, int(map_height * s))))
        surf.fill(COLOR_FLOOR)
        for r in walls:
            x0, y0 = int(r.x * s), int(r.y * s)
            x1, y1 = math.ceil(r.right * s), math.ceil(r.bottom * s)
            pygame.draw.rect(surf, COLOR_WALL, (x0, y0, max(1, x1 - x0), max(1, y1 - y0)))
        self.map_surface = surf

    def clear(self):
        self.map_surface = None

    # ── dibujo ───────────────────────────────────────────────────────────────
    def draw(self, surface, player, enemies):
        if self.map_surface is None:
            return
        s = RADAR_SCALE
        mw, mh = self.map_surface.get_size()
        px, py = player.rect.center

        vx = _view_origin(int(px * s), mw, RADAR_W)
        vy = _view_origin(int(py * s), mh, RADAR_H)

        view = self._view
        view.fill(COLOR_VOID)
        view.blit(self.map_surface, (-vx, -vy))

        # Conos de visión (misma geometría que Enemy.draw_vision), con transparencia.
        cones = self._cones
        cones.fill((0, 0, 0, 0))
        for e in enemies:
            dir_x, dir_y = e.DIRS[e._vision_facing()]
            perp_x, perp_y = -dir_y, dir_x
            sx, sy = e.rect.center
            rng, w = e.VISION_RANGE, e.CONE_TAN
            world_pts = [
                (sx, sy),
                (sx + (dir_x - perp_x * w) * rng, sy + (dir_y - perp_y * w) * rng),
                (sx + (dir_x + perp_x * w) * rng, sy + (dir_y + perp_y * w) * rng),
            ]
            pts = [(x * s - vx, y * s - vy) for x, y in world_pts]
            base = COLOR_CONE_ALERT if e.state in self.alerted_states else COLOR_CONE_CALM
            pygame.draw.polygon(cones, (*base, CONE_ALPHA), pts)
        view.blit(cones, (0, 0))

        # Guardias
        half = DOT_SIZE // 2
        for e in enemies:
            ex, ey = e.rect.center
            x, y = int(ex * s) - vx, int(ey * s) - vy
            if -half <= x < RADAR_W + half and -half <= y < RADAR_H + half:
                color = COLOR_GUARD_ALERT if e.state in self.alerted_states else COLOR_GUARD_CALM
                pygame.draw.rect(view, color, (x - half, y - half, DOT_SIZE, DOT_SIZE))

        # Jugador (parpadea suave para ubicarlo rápido)
        phase = (math.sin(pygame.time.get_ticks() / PLAYER_BLINK_MS) + 1) / 2
        x, y = int(px * s) - vx, int(py * s) - vy
        pygame.draw.rect(view, _lerp_color(COLOR_PLAYER_A, COLOR_PLAYER_B, phase),
                         (x - half, y - half, DOT_SIZE, DOT_SIZE))

        pygame.draw.rect(view, COLOR_BORDER, view.get_rect(), 1)
        surface.blit(view, (surface.get_width() - RADAR_W - RADAR_MARGIN, RADAR_MARGIN))