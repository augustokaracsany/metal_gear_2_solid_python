import pygame
import sys
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS
from src.player import Player

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Metal Gear 2: Solid Python")
        self.clock = pygame.time.Clock()
        
        self.running = True 
        
        # Instanciamos a Snake en el centro de la pantalla
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

    def run(self):
        while self.running:
            # 1. Calcular Delta Time
            dt = self.clock.tick(FPS) / 1000.0

            # 2. Eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            # 3. Actualización de Lógica
            self.player.update(dt)

            # 4. Renderizado
            self.screen.fill((20, 20, 25))  # Fondo oscuro estilo búnker
            self.player.draw(self.screen)

            pygame.display.flip()

        pygame.quit()
        sys.exit()