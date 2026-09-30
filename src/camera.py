import pygame

class Camera:
    def __init__(self, width, height):
        # Ancho y alto total del mapa de fondo en píxeles
        self.width = width
        self.height = height
        self.camera_rect = pygame.Rect(0, 0, width, height)

    def apply(self, entity):
        # Desplaza la posición de cualquier entidad (Snake, paredes, etc.) según la cámara
        return entity.rect.move(self.camera_rect.topleft)

    def apply_pos(self, x, y):
        # Útil si necesitas desplazar coordenadas sueltas
        return x + self.camera_rect.x, y + self.camera_rect.y

    def update(self, target):
        # Centra la cámara en el objetivo (Snake)
        # SCREEN_WIDTH y SCREEN_HEIGHT deben coincidir con tus settings
        from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT
        
        x = -target.rect.centerx + int(SCREEN_WIDTH / 2)
        y = -target.rect.centery + int(SCREEN_HEIGHT / 2)

        # Limitamos la cámara para que no muestre "afuera" de los bordes del mapa
        x = min(0, x)  # Bordes izquierdos
        y = min(0, y)  # Bordes superiores
        x = max(-(self.width - SCREEN_WIDTH), x)   # Bordes derechos
        y = max(-(self.height - SCREEN_HEIGHT), y) # Bordes inferiores

        self.camera_rect = pygame.Rect(x, y, self.width, self.height)