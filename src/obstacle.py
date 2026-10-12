import pygame

class Obstacle(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height):
        super().__init__()
        # Rectángulo invisible para colisiones
        self.rect = pygame.Rect(x, y, width, height)