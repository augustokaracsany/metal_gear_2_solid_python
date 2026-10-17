import pygame
from src.player import Player
from src.camera import Camera
from src.enemy import Enemy # MERGE.
from src.tilemap import TiledMap  # Mapas TMX
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT

class Game:
    def __init__(self, mission_number=1):
        self.mission_number = mission_number
        
        # 1. DICCIONARIO DE NIVELES: Mapea cada misión a sus respectivas rutas de archivos
        self.levels_data = {
            1: {
                "tmx": "assets/sprites/maps/entry_point_brightness3-576x768.tmx",
                "png": "assets/sprites/maps/entry_point_brightness3-576x768.png"
            },
            2: {
                "tmx": "assets/sprites/maps/building1_floor1-960x960.tmx",  # Reemplaza con la ruta real de tu misión 2
                "png": "assets/sprites/maps/building1_floor1-960x960.png"
            },
            3: {
                "tmx": "assets/sprites/maps/mission3_map.tmx",  # Reemplaza con la ruta real de tu misión 3
                "png": "assets/sprites/maps/mission3_map.png"
            },
            4: {
                "tmx": "assets/sprites/maps/mission4_map.tmx",  # Reemplaza con la ruta real de tu misión 4
                "png": "assets/sprites/maps/mission4_map.png"
            }
        }
        
        # Obtenemos los datos de la misión actual (si el número no existe, por defecto usa la misión 1)
        current_level = self.levels_data.get(self.mission_number, self.levels_data[1])
        
        # Grupos de sprites y colisiones
        self.all_sprites = pygame.sprite.Group()
        self.walls_group = pygame.sprite.Group()
        self.enemies_group = pygame.sprite.Group()
        
        # 2. CARGAMOS EL MAPA DINÁMICAMENTE SEGÚN LA MISIÓN SELECCIONADA
        try:
            self.map = TiledMap(current_level["tmx"], scale=2)
        except Exception as e:
            print(f"AVISO: No se pudo cargar el mapa TMX para la misión {self.mission_number} ({e}). Usando imagen plana de respaldo.")
            self.map = None
            self.raw_map = pygame.image.load(current_level["png"]).convert()
            self.map_scale = 2 
            self.map_image = pygame.transform.scale(self.raw_map, (self.raw_map.get_width() * self.map_scale, self.raw_map.get_height() * self.map_scale))

        # Obtenemos las dimensiones reales del mapa para la cámara.
        if self.map:
            map_width = self.map.width
            map_height = self.map.height
        else:
            map_width = self.map_image.get_width()
            map_height = self.map_image.get_height()

        # Definimos una resolución virtual más pequeña (la mitad de la pantalla = zoom x2 visual perfecto)
        self.virtual_width = SCREEN_WIDTH // 2
        self.virtual_height = SCREEN_HEIGHT // 2
        self.virtual_surface = pygame.Surface((self.virtual_width, self.virtual_height))

        # Instanciamos la cámara pasándole el tamaño virtual correcto
        self.camera = Camera(map_width, map_height, self.virtual_width, self.virtual_height)
        
        # Obtenemos las coordenadas de inicio desde el objeto 'player_spawn' del mapa Tiled
        spawn_x, spawn_y = self.map.get_spawn_point("player_spawn", (400, 350)) if self.map else (400, 350)

        # Cargamos las zonas ocultas de forma segura
        if self.map:
            self.hidden_zones = self.map.get_hidden_zones("zonas_oculto")
            self.hidden_zones_top = self.map.get_hidden_zones_top()
            self.hidden_zones_bottom = self.map.get_hidden_zones_bottom()
        if not hasattr(self, "hidden_zones") or self.hidden_zones is None:
            self.hidden_zones = []
        if not hasattr(self, "hidden_zones_top") or self.hidden_zones_top is None:
            self.hidden_zones_top = []
        if not hasattr(self, "hidden_zones_bottom") or self.hidden_zones_bottom is None:
            self.hidden_zones_bottom = []

        # LÍMITES SUPERIORES DE ZONAS OCULTAS POR DONDE NO SE PUEDE ENTRAR Y SALIR VERTICALMENTE. ( Que SÍ tienen límite. Un "tope superior." )
        self.top_barriers = self.map.get_top_barriers("limites_top") if self.map else []
                
        # Instanciamos a Snake en la posición del mapa
        self.player = Player(spawn_x, spawn_y)
        self.all_sprites.add(self.player)

        patrol_routes = self.map.get_patrol_path("enemy_patrols")

        if patrol_routes:
            ruta_actual = patrol_routes[0]
            pos_inicial_x = ruta_actual[0][0]
            pos_inicial_y = ruta_actual[0][1]
            guardia = Enemy(pos_inicial_x, pos_inicial_y, ruta_actual)
            self.enemies_group.add(guardia)
        
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                import sys
                sys.exit()
            self.player.punch_self_event(event)

    def update(self, dt):
        walls = self.map.get_collision_rects() if self.map else []

        # Actualización de Lógica del jugador (toda la responsabilidad de estado y zonas vive en player.py)
        self.player.update(
            dt,
            walls,
            self.top_barriers,
            self.hidden_zones,
            self.hidden_zones_top,
            self.hidden_zones_bottom,
        )

        for enemy in self.enemies_group:
            enemy.update(dt)

        # 3. Actualizamos la posición de la cámara centrada en Snake.
        self.camera.update(self.player)

    def draw(self, surface):
        self.virtual_surface.fill((0, 0, 0))

        if self.map:
            self.map.render_below(self.virtual_surface, self.camera)
        else:
            self.virtual_surface.blit(self.map_image, self.camera.camera_rect.topleft) 
        
        self.player.draw_with_camera(self.virtual_surface, self.camera)

        for enemy in self.enemies_group:
            enemy.draw_with_camera(self.virtual_surface, self.camera)

        if self.map:
            self.map.render_roofs(
                self.virtual_surface,
                self.camera,
                render_condition=self.player.is_hidden or self.player.is_near_hidden_zone(margin=30),
            )

        scaled_surface = pygame.transform.scale(self.virtual_surface, (surface.get_width(), surface.get_height()))
        surface.blit(scaled_surface, (0, 0))

        # --- DEBUG VISUAL DE ZONAS OCULTAS ---
        if hasattr(self, "hidden_zones") and self.hidden_zones:
            for zone in self.hidden_zones:
                debug_screen_rect = zone.move(self.camera.camera_rect.topleft)
                pygame.draw.rect(self.virtual_surface, (0, 255, 255), debug_screen_rect, 2)
