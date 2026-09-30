import pygame
from src.settings import PLAYER_SPEED

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        
        # Posición exacta en decimales para que no sea tosco.
        self.x = float(x)
        self.y = float(y)
        
        # Dimensiones temporales del sprite ( Placeholder esto. ).
        self.width = 32
        self.height = 32
        
        # Rect para colisiones y dibujado.
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        
        # Dirección actual ( "UP", "DOWN", "LEFT", "RIGHT" ).
        self.facing = "DOWN"
        self.is_moving = False

    def handle_input(self):
        keys = pygame.key.get_pressed()
        
        # Vector de movimiento en 2D.
        dx = 0
        dy = 0
        
        # Detecta teclas ( Flechas o WASD, como prefieras. ).
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -1
            self.facing = "LEFT"
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = 1
            self.facing = "RIGHT"
            
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -1
            self.facing = "UP"
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = 1
            self.facing = "DOWN"
            
        # Si se mueve en diagonal, se normaliza el vector para que no vaya más rápido de lo que debería en diagonal.
        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071
            
        return dx, dy

    def update(self, dt):
        dx, dy = self.handle_input()
        
        if dx != 0 or dy != 0:
            self.is_moving = True
            # Actualizamos la posición usando velocidad * delta_time.
            self.x += dx * PLAYER_SPEED * dt
            self.y += dy * PLAYER_SPEED * dt
        else:
            self.is_moving = False

        # Sincronizamos el rect con la posición redondeada ( Clave para evitar tirones ).
        self.rect.x = round(self.x)
        self.rect.y = round(self.y)

    def draw(self, surface):
        # Por ahora dibujamos un rectángulo ( Snake cuadrado ). 
        # Más adelante acá va a ir la lógica de los sprites y los frames. Si Dios quiere.
        color = (50, 168, 82) if self.facing != "UP" else (30, 100, 50)
        pygame.draw.rect(surface, color, self.rect)

        # Indicador de dirección.
        # Indicador visual simple de hacia dónde mira el Snake cuadrado ( Una barra blanca. ).
        eye_rects = {
            "DOWN": (self.rect.centerx - 4, self.rect.bottom - 6, 8, 4),
            "UP": (self.rect.centerx - 4, self.rect.top + 2, 8, 4),
            "LEFT": (self.rect.left + 2, self.centery if hasattr(self, 'centery') else self.rect.centery - 4, 4, 8),
            "RIGHT": (self.rect.right - 6, self.rect.centery - 4, 4, 8)
        }
        # Dibujar indicador de dirección rápido.
        if self.facing == "DOWN":
            pygame.draw.rect(surface, (255, 255, 255), (self.rect.x + 12, self.rect.y + 24, 8, 4))
        elif self.facing == "UP":
            pygame.draw.rect(surface, (255, 255, 255), (self.rect.x + 12, self.rect.y + 4, 8, 4))
        elif self.facing == "LEFT":
            pygame.draw.rect(surface, (255, 255, 255), (self.rect.x + 4, self.rect.y + 12, 4, 8))
        elif self.facing == "RIGHT":
            pygame.draw.rect(surface, (255, 255, 255), (self.rect.x + 24, self.rect.y + 12, 4, 8))