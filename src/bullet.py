import math
import pygame
from src.settings import (
    BULLET_SPEED, BULLET_STEP, BULLET_LENGTH, BULLET_THICKNESS,
    BULLET_DAMAGE, BULLET_COLOR, BULLET_HIT_PADDING, BULLET_DRAW_OFFSET_Y,
)

DIRECTIONS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}


class Bullet(pygame.sprite.Sprite):
    def __init__(self, owner_rect, facing):
        super().__init__()
        self.dir_x, self.dir_y = DIRECTIONS[facing]
        self.damage = BULLET_DAMAGE

        # Horizontal: largo x grosor. Vertical: grosor x largo.
        if self.dir_x != 0:
            width, height = BULLET_LENGTH, BULLET_THICKNESS
        else:
            width, height = BULLET_THICKNESS, BULLET_LENGTH

        # Nace justo delante del hitbox de quien dispara.
        self.cx = float(owner_rect.centerx + self.dir_x * (owner_rect.width // 2 + 4))
        self.cy = float(owner_rect.centery + self.dir_y * (owner_rect.height // 2 + 4))

        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = (round(self.cx), round(self.cy))

    def update(self, dt, walls, enemies, bounds):
        #Mueve la bala de a pasos chicos y se elimina si choca con algo.
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

            # Chocó con una pared.
            for wall in walls:
                if self.rect.colliderect(wall):
                    self.kill()
                    return

            # Chocó con un enemigo.
            for enemy in enemies:
                if self.rect.colliderect(enemy.rect.inflate(BULLET_HIT_PADDING, BULLET_HIT_PADDING)):
                    enemy.take_damage(self.damage)
                    self.kill()
                    return

    def draw_with_camera(self, surface, camera):
        draw_rect = self.rect.move(camera.camera_rect.x,
                                   camera.camera_rect.y - BULLET_DRAW_OFFSET_Y)
        pygame.draw.rect(surface, BULLET_COLOR, draw_rect)