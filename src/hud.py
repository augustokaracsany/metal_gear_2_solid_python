import pygame
from src.settings import (
    HEALTH_BAR_X, HEALTH_BAR_Y, HEALTH_BAR_WIDTH, HEALTH_BAR_HEIGHT,
    HEALTH_LABEL_TEXT, HEALTH_LABEL_SIZE, HEALTH_NUMBER_SIZE,
    HEALTH_NUMBER_GAP, HEALTH_NUMBER_RESERVED, HEALTH_TICKS,
    COLOR_HEALTH_FILL, COLOR_HEALTH_HIGHLIGHT, COLOR_HEALTH_LOW,
    COLOR_HEALTH_LINE, COLOR_HEALTH_SHADOW, COLOR_TEXT,
)


def draw_text_shadow(surface, font, text, color, x, y, align_right=False):
    """Dibuja texto con una sombra negra para que se lea sobre cualquier fondo."""
    shadow = font.render(text, True, COLOR_HEALTH_SHADOW)
    main = font.render(text, True, color)
    if align_right:
        x = x - main.get_width()
    surface.blit(shadow, (x + 1, y + 1))
    surface.blit(main, (x, y))
    return main


class HealthBar:
    def __init__(self):
        self.label_font = pygame.font.Font(None, HEALTH_LABEL_SIZE)
        self.number_font = pygame.font.Font(None, HEALTH_NUMBER_SIZE)

    def draw(self, surface, player):
        x = HEALTH_BAR_X
        y = HEALTH_BAR_Y
        ratio = player.health / player.max_health

        # 1. Nombre chiquito arriba a la izquierda.
        label = self.label_font.render(HEALTH_LABEL_TEXT, True, COLOR_TEXT)
        draw_text_shadow(surface, self.label_font, HEALTH_LABEL_TEXT, COLOR_TEXT,
                         x, y - label.get_height() - 3)

        # 2. Barra gruesa: sombra + parte llena + brillo arriba.
        pygame.draw.rect(surface, COLOR_HEALTH_SHADOW,
                         (x - 1, y - 1, HEALTH_BAR_WIDTH + 2, HEALTH_BAR_HEIGHT + 2))
        fill_width = int(HEALTH_BAR_WIDTH * ratio)
        if fill_width > 0:
            color = COLOR_HEALTH_LOW if ratio <= 0.3 else COLOR_HEALTH_FILL
            pygame.draw.rect(surface, color, (x, y, fill_width, HEALTH_BAR_HEIGHT))
            if ratio > 0.3:
                pygame.draw.rect(surface, COLOR_HEALTH_HIGHLIGHT,
                                 (x, y, fill_width, HEALTH_BAR_HEIGHT // 2))

        # 3. Línea fina de capacidad máxima, debajo de la barra, con marcas.
        line_y = y + HEALTH_BAR_HEIGHT + 4
        pygame.draw.line(surface, COLOR_HEALTH_SHADOW,
                         (x, line_y + 1), (x + HEALTH_BAR_WIDTH, line_y + 1), 2)
        pygame.draw.line(surface, COLOR_HEALTH_LINE,
                         (x, line_y), (x + HEALTH_BAR_WIDTH, line_y), 1)
        for i in range(HEALTH_TICKS + 1):
            tick_x = x + int(HEALTH_BAR_WIDTH * i / HEALTH_TICKS)
            pygame.draw.line(surface, COLOR_HEALTH_LINE,
                             (tick_x, line_y - 3), (tick_x, line_y), 1)

        # 4. Número grande a la derecha, alineado a la derecha y centrado con la barra.
        number_right = x + HEALTH_BAR_WIDTH + HEALTH_NUMBER_GAP + HEALTH_NUMBER_RESERVED
        number_color = COLOR_HEALTH_LOW if ratio <= 0.3 else COLOR_TEXT
        number_h = self.number_font.get_height()
        number_y = y + (HEALTH_BAR_HEIGHT + 4) // 2 - number_h // 2
        draw_text_shadow(surface, self.number_font, str(player.health), number_color,
                         number_right, number_y, align_right=True)