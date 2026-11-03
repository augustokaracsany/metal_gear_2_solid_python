import random
import pygame
from src.settings import (
    RAIN_DROPS, RAIN_SPEED_MIN, RAIN_SPEED_MAX, RAIN_LENGTH_MIN, RAIN_LENGTH_MAX,
    RAIN_WIND, RAIN_COLOR, RAIN_TINT_COLOR, RAIN_TINT_ALPHA,
)


class Rain:
    def __init__(self, width, height):
        self.w = width
        self.h = height
        self.drops = [self._new_drop(anywhere=True) for _ in range(RAIN_DROPS)]

        # Velo oscuro azulado sobre toda la escena.
        self.tint = None
        if RAIN_TINT_ALPHA > 0:
            self.tint = pygame.Surface((width, height), pygame.SRCALPHA)
            self.tint.fill((*RAIN_TINT_COLOR, RAIN_TINT_ALPHA))

    def _new_drop(self, anywhere=False):
        """Gota = [x, y, velocidad, largo]. Al inicio se reparten por toda la pantalla."""
        x = random.uniform(0, self.w + abs(RAIN_WIND) * 1.5)
        y = random.uniform(0, self.h) if anywhere else random.uniform(-self.h * 0.25, 0)
        return [x, y, random.uniform(RAIN_SPEED_MIN, RAIN_SPEED_MAX),
                random.randint(RAIN_LENGTH_MIN, RAIN_LENGTH_MAX)]

    def update(self, dt):
        for i, drop in enumerate(self.drops):
            drop[0] += RAIN_WIND * dt
            drop[1] += drop[2] * dt
            if drop[1] > self.h or drop[0] < -20 or drop[0] > self.w + 120:
                self.drops[i] = self._new_drop()

    def draw(self, surface):
        if self.tint:
            surface.blit(self.tint, (0, 0))
        for x, y, speed, length in self.drops:
            slant = RAIN_WIND / speed * length   # Cuánto se desplaza de costado a lo largo de la gota.
            pygame.draw.line(surface, RAIN_COLOR,
                             (int(x - slant), int(y - length)), (int(x), int(y)))