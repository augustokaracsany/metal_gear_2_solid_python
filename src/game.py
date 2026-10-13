import pygame
from src.player import Player
from src.camera import Camera
from src.tilemap import TiledMap  # Asegúrate de haber creado este archivo

class Game:
    def __init__(self, mission_number=1):
        self.mission_number = mission_number
        
        # CARGAMOS EL MAPA DESDE TILED (.tmx)
        try:
            self.map = TiledMap("assets/sprites/maps/entry_point_brightness3-576x768.tmx", scale=2)
            
        except Exception as e:
            print(f"AVISO: No se pudo cargar el mapa TMX ({e}). Usando imagen plana de respaldo.")
            self.map = None
            # Retroceso a imagen anterior si falla Tiled o .tmx.
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

        # Instanciamos la cámara con las dimensiones reales del mapa.
        self.camera = Camera(map_width, map_height)
        
        # Instanciamos a Snake en la posición inicial. <- Modificar si aparece afuera de límites.
        self.player = Player(400, 350)

    def handle_events(self, events):
        # Eventos particulares del juego a futuro ( Pausa, disparos, etc. ).
        pass

    def update(self, dt):
        # 1. Obtener lista de rectángulos de colisión de Tiled.
        walls = self.map.get_collision_rects() if self.map else []
        
        # 2. Actualización de Lógica del jugador pasándole los muros ( Walls. ).
        self.player.update(dt, walls)
        
        # 3. Actualizamos la posición de la cámara centrada en Snake.
        self.camera.update(self.player)

    def draw(self, surface):
        # 1. Limpiar pantalla.
        surface.fill((0, 0, 0))

        # 2. Dibujamos el mapa ( Tiled renderiza sus capas o usa la imagen plana de respaldo si falla. )
        # NOTA: Dibujar el mapa de Tiled pasándole la cámara.
        if self.map:
            self.map.render(surface, self.camera)

        # 3. Dibujamos a Snake aplicando el desplazamiento de la cámara. Explota.
        self.player.draw_with_camera(surface, self.camera)