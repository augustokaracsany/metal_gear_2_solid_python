import pygame
from src.player import Player
from src.camera import Camera
from src.tilemap import TiledMap  # Tu sistema de mapas TMX

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

        # 2. CARGAMOS EL MAPA DINÁMICAMENTE SEGÚN LA MISIÓN SELECCIONADA
        try:
            self.map = TiledMap(current_level["tmx"], scale=2)
        except Exception as e:
            print(f"AVISO: No se pudo cargar el mapa TMX para la misión {self.mission_number} ({e}). Usando imagen plana de respaldo.")
            self.map = None
            self.raw_map = pygame.image.load(current_level["png"]).convert()
            self.map_scale = 2 
            self.map_image = pygame.transform.scale(self.raw_map, (self.raw_map.get_width() * self.map_scale, self.raw_map.get_height() * self.map_scale))

        # Definimos las dimensiones del mapa para la cámara.
        if self.map:
            map_width = self.map.width
            map_height = self.map.height
        else:
            map_width = self.map_image.get_width()
            map_height = self.map_image.get_height()

        # Instanciamos la cámara con las dimensiones reales del mapa del nivel.
        self.camera = Camera(map_width, map_height)
        
        # Obtenemos las coordenadas de inicio desde el objeto 'player_spawn' del mapa Tiled actual
        spawn_x, spawn_y = self.map.get_spawn_point("player_spawn", (400, 350)) if self.map else (400, 350)
        
        # Instanciamos a Snake en la posición de inicio específica de este mapa
        self.player = Player(spawn_x, spawn_y)
        self.all_sprites.add(self.player)
        
    def handle_events(self, events):
        # Procesamos eventos individuales (Como GOLPEAR con la 'E'. )
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                import sys
                sys.exit()
            
            # Incorporamos la función de golpear.
            self.player.punch_self_event(event)

    def update(self, dt):
        # 1. Obtener lista de rectángulos de colisión del mapa Tiled actual o lista vacía.
        walls = self.map.get_collision_rects() if self.map else []

        # 2. Actualización de Lógica del jugador pasándole los muros de este nivel.
        self.player.update(dt, walls)
        
        # 3. Actualizamos la posición de la cámara centrada en Snake.
        self.camera.update(self.player)

    def draw(self, surface):
        # 1. Limpiar pantalla.
        surface.fill((0, 0, 0))

        # 2. Dibujamos el mapa correspondiente a la misión activa.
        if self.map:
            self.map.render(surface, self.camera)
        else:
            surface.blit(self.map_image, self.camera.camera_rect.topleft)

        # 3. Dibujamos a Snake aplicando el desplazamiento de la cámara.
        self.player.draw_with_camera(surface, self.camera)