import pygame

class Camera:
    def __init__(self, width, height, viewport_width=None, viewport_height=None):
        self.width = width
        self.height = height
        
        from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT
        self.viewport_width = viewport_width if viewport_width else SCREEN_WIDTH
        self.viewport_height = viewport_height if viewport_height else SCREEN_HEIGHT
        
        self.camera_rect = pygame.Rect(0, 0, width, height)

    def apply(self, entity):
        return entity.rect.move(self.camera_rect.topleft)

    def apply_pos(self, x, y):
        return x + self.camera_rect.x, y + self.camera_rect.y

    def update(self, target):
        x = -target.rect.centerx + int(self.viewport_width / 2)
        y = -target.rect.centery + int(self.viewport_height / 2)

        # Limitamos usando el tamaño del visor virtual para evitar espacios negros.
        x = min(0, x)
        y = min(0, y)
        x = max(-(self.width - self.viewport_width), x)
        y = max(-(self.height - self.viewport_height), y)

        self.camera_rect = pygame.Rect(int(x), int(y), self.width, self.height)