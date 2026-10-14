import pygame
from src.player import Player
from src.camera import Camera
from src.tilemap import TiledMap  # Tu sistema de mapas TMX

class Game:
    def __init__(self, mission_number=1):
        self.mission_number = mission_number
        
        # Grupos de sprites y colisiones
        self.all_sprites = pygame.sprite.Group()
        self.walls_group = pygame.sprite.Group()

        # CARGAMOS EL MAPA DESDE TILED (.tmx)
        try:
            self.map = TiledMap("assets/sprites/maps/entry_point_brightness3-576x768.tmx", scale=2)
        except Exception as e:
            print(f"AVISO: No se pudo cargar el mapa TMX ({e}). Usando imagen plana de respaldo.")
            self.map = None
            self.raw_map = pygame.image.load("assets/sprites/maps/entry_point_brightness3-576x768.png").convert()
            self.map_scale = 2 
            self.map_image = pygame.transform.scale(self.raw_map, (self.raw_map.get_width() * self.map_scale, self.raw_map.get_height() * self.map_scale))

        # Definimos las dimensiones del mapa para la cámara.
        if self.map:
            map_width = self.map.width
            map_height = self.map.height
        else:
            map_width = self.map_image.get_width()
            map_height = self.map_image.get_height()

        # Cargar colisiones estáticas adicionales si usas map_data de Lautaro
        for data in BUILDING_1_COLLIDERS:
            wall = Obstacle(data["x"], data["y"], data["w"], data["h"])
            self.walls_group.add(wall)

        # Instanciamos la cámara con las dimensiones reales del mapa.
        self.camera = Camera(map_width, map_height)
        
        # Instanciamos a Snake en la posición inicial.
        self.player = Player(400, 350)
        self.all_sprites.add(self.player)

    def handle_events(self, events):
        # Procesamos eventos individuales (como el golpe con la 'E' de Lautaro)
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                import sys
                sys.exit()
            
            # Incorporamos la función de golpear de Lautaro
            self.player.punch_self_event(event)

    def update(self, dt):
        # 1. Obtener lista de rectángulos de colisión de Tiled o del grupo de paredes.
        walls = self.map.get_collision_rects() if self.map else []
        
        # Si prefieres usar también el walls_group, puedes combinarlos o pasar walls directamente.
        # 2. Actualización de Lógica del jugador pasándole los muros.
        self.player.update(dt, walls)
        
        # 3. Actualizamos la posición de la cámara centrada en Snake.
        self.camera.update(self.player)

    def draw(self, surface):
        # 1. Limpiar pantalla.
        surface.fill((0, 0, 0))

        # 2. Dibujamos el mapa (Tiled renderiza sus capas o usa la imagen plana de respaldo).
        if self.map:
            self.map.render(surface, self.camera)
        else:
            surface.blit(self.map_image, self.camera.camera_rect.topleft)

        # (Opcional de Lautaro) Si quieres dibujar los rects de colisión para debug, descomenta esto:
        # for wall in self.walls_group:
        #     rect_en_pantalla = self.camera.apply(wall)
        #     pygame.draw.rect(surface, (255, 0, 0), rect_en_pantalla, 2)

        # 3. Dibujamos a Snake aplicando el desplazamiento de la cámara.
        self.player.draw_with_camera(surface, self.camera)