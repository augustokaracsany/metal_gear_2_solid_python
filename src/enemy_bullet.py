import pygame
import math

class enemyBullet(pygame.sprite.Sprite):
    _bullet_image = None  # Caché para cargar la imagen una sola vez

    def __init__(self, x, y, vx, vy):
        super().__init__()

        # Cargar y escalar la imagen de la bala si no está cargada
        if enemyBullet._bullet_image is None:
            try:
                img = pygame.image.load("assets/sprites/weapons/bullet.png").convert_alpha()
                scale = 1  # Ajusta este factor si necesitas que la bala sea más grande o chica
                enemyBullet._bullet_image = pygame.transform.scale(
                    img, (int(img.get_width() * scale), int(img.get_height() * scale))
                )
            except Exception as e:
                print(f"Aviso: No se pudo cargar bullet.png: {e}")
                # Superficie de respaldo por si falla la carga del archivo
                enemyBullet._bullet_image = pygame.Surface((6, 6))
                enemyBullet._bullet_image.fill((255, 255, 0))

        self.image = enemyBullet._bullet_image
        self.rect = self.image.get_rect(center=(x, y))

        # Posiciones en float para un movimiento suave y preciso
        self.x = float(x)
        self.y = float(y)

        # Velocidades direccionales (permiten diagonales exactas)
        self.vx = vx
        self.vy = vy

        self.distance_traveled = 0

    def update(self, dt):
        # 1. Movemos la bala en base a su velocidad y el delta time
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.rect.center = (round(self.x), round(self.y))
        
        # 2. Acumulamos la distancia recorrida en este frame
        distance_moved = math.hypot(self.vx * dt, self.vy * dt)
        self.distance_traveled += distance_moved
        
        # 3. Si supera el límite establecido (ej. 150 píxeles), se elimina
        if self.distance_traveled >= 750:
            self.kill()

    def draw_with_camera(self, surface, camera):
        # Si tu juego usa un objeto de cámara para desplazar el mapa
        dest_rect = camera.apply(self)
        surface.blit(self.image, dest_rect)