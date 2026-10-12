import pygame
import sys
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS
from src.player import Player
from src.obstacle import Obstacle
from src.map_data import BUILDING_1_COLLIDERS
from src.camera import Camera # Cámara.

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Metal Gear 2: Solid Python")
        self.clock = pygame.time.Clock()

        pygame.mouse.set_visible(False)
        self.running = True 

        # IMPORTANTE: Guardarlas como atributos de la clase (self.)
        self.all_sprites = pygame.sprite.Group()
        self.walls_group = pygame.sprite.Group()

        # CARGAR EL MAPA DE FONDO (Tu código actual de carga y escala...)
        try:
            raw_map = pygame.image.load("assets/sprites/maps/building1floor1.png").convert()
        except FileNotFoundError:
            print("AVISO: No se encontró el mapa en assets/maps/. Usando escenario VR temporal.")
            raw_map = pygame.Surface((500, 500))
            raw_map.fill((40, 40, 50))

        self.map_scale = 2 
        new_width = raw_map.get_width() * self.map_scale
        new_height = raw_map.get_height() * self.map_scale
        self.map_image = pygame.transform.scale(raw_map, (new_width, new_height))

        self.map_width = self.map_image.get_width()
        self.map_height = self.map_image.get_height()

        # Llenar el grupo de paredes
        for data in BUILDING_1_COLLIDERS:
            wall = Obstacle(data["x"], data["y"], data["w"], data["h"])
            self.walls_group.add(wall)

        # Instanciamos la cámara y al jugador
        self.camera = Camera(self.map_width, self.map_height)
        self.player = Player(400, 400)

    def run(self):
        while self.running:
            # 1. Calcular Delta Time
            dt = self.clock.tick(FPS) / 1000.0

            # 2. Eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                self.player.punch_self_event(event)

            # 3. Actualización de Lógica
            self.player.update(dt, self.walls_group)

            # 4. Renderizado
            self.screen.fill((0, 0, 0))  # Limpiar pantalla

            # Actualizamos la posición de la cámara centrada en Snake
            self.camera.update(self.player)

            # Dibujamos el mapa desplazado por la cámara
            self.screen.blit(self.map_image, self.camera.camera_rect.topleft)

            for wall in self.walls_group:
                rect_en_pantalla = self.camera.apply(wall)
                pygame.draw.rect(self.screen, (255, 0, 0), rect_en_pantalla, 2)

            # Dibujamos a Snake aplicando el desplazamiento de la cámara
            # En lugar de pasarle self.screen directo, dibujamos usando la posición ajustada por la cámara:
            self.player.draw_with_camera(self.screen, self.camera)

            pygame.display.flip()

        pygame.quit()
        sys.exit()