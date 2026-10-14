import pygame
import sys
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS
from src.player import Player
from src.camera import Camera
from src.enemy import Enemy
from src.tilemap import TiledMap  # Tu sistema de mapas TMX

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
        self.enemies_group = pygame.sprite.Group()

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

        # Instanciamos la cámara con las dimensiones reales del mapa.
        self.camera = Camera(map_width, map_height)
        
        # Obtenemos las coordenadas de inicio desde el objeto 'player_spawn' del mapa Tiled
        spawn_x, spawn_y = self.map.get_spawn_point("player_spawn", (400, 350)) if self.map else (400, 350)
        
        # Instanciamos a Snake en la posición del mapa
        self.player = Player(spawn_x, spawn_y)
        self.all_sprites.add(self.player)

        patrol_routes = self.map.get_patrol_path("enemy_patrols")

        if patrol_routes:
            # Tomamos la primera ruta completa
            ruta_actual = patrol_routes[0]
            
            # El punto de inicio (x, y) es el primer nodo de esa ruta (índice 0, 0 para X y 0, 1 para Y)
            pos_inicial_x = ruta_actual[0][0]
            pos_inicial_y = ruta_actual[0][1]
            
            # Instanciamos al enemigo usando tu constructor tal cual lo escribiste
            guardia = Enemy(pos_inicial_x, pos_inicial_y, ruta_actual)
            self.enemies_group.add(guardia)
        
    def handle_events(self, events):
        # Procesamos eventos individuales ( Como GOLPEAR con la 'E'. )
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                import sys
                sys.exit()
            
            # Incorporamos la función de golpear.
            self.player.punch_self_event(event)

        # Llenar el grupo de paredes
        for data in BUILDING_1_COLLIDERS:
            wall = Obstacle(data["x"], data["y"], data["w"], data["h"])
            self.walls_group.add(wall)

        # 2. Actualización de Lógica del jugador pasándole los muros.
        self.player.update(dt, walls)

        for enemy in self.enemies_group:
            enemy.update(dt)
        
        # 3. Actualizamos la posición de la cámara centrada en Snake.
        self.camera.update(self.player)

    def run(self):
        while self.running:
            # 1. Calcular Delta Time
            dt = self.clock.tick(FPS) / 1000.0

            # 2. Eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

        # 3. Dibujamos a Snake aplicando el desplazamiento de la cámara.
        self.player.draw_with_camera(surface, self.camera)

        for enemy in self.enemies_group:
            enemy.draw_with_camera(surface, self.camera)
