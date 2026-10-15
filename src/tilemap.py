import pygame
from pytmx.util_pygame import load_pygame

class TiledMap:
    def __init__(self, filename, scale=2):
        self.tmx_data = load_pygame(filename)
        self.scale = scale
        self.width = int(self.tmx_data.width * self.tmx_data.tilewidth * self.scale)
        self.height = int(self.tmx_data.height * self.tmx_data.tileheight * self.scale)

    def render(self, surface, camera):
        offset = camera.camera_rect.topleft

        for layer in self.tmx_data.visible_layers:
            # 1. Capa de imagen de fondo ( El nivel en sí. ) ESCALADO X2
            if hasattr(layer, "image") and layer.image:
                img_scaled = pygame.transform.scale(
                    layer.image, 
                    (int(layer.image.get_width() * self.scale), int(layer.image.get_height() * self.scale))
                )
                surface.blit(img_scaled, offset)
                
            # 2. Capa de patrones de colisión ( Capa "colisiones_grid" en Tiled. ) ESCALADO X2
            elif hasattr(layer, "data") and layer.name == "colisiones_grid":
                for x, y, gid in layer:
                    tile = self.tmx_data.get_tile_image_by_gid(gid)
                    if tile:
                        tile_scaled = pygame.transform.scale(
                            tile, 
                            (int(tile.get_width() * self.scale), int(tile.get_height() * self.scale))
                        )
                        pos_x = (x * self.tmx_data.tilewidth * self.scale) + offset[0]
                        pos_y = (y * self.tmx_data.tileheight * self.scale) + offset[1]
                        surface.blit(tile_scaled, (pos_x, pos_y))

    def get_collision_rects(self):
        rects = []
        
        # 1. Cajas de objetos, formas, selecciones ( Capa "colisiones_objs" Tiled. ) ESCALADO X2
        for layer in self.tmx_data.visible_layers:
            if layer.name == "colisiones_objs":
                for obj in layer:
                    rects.append(pygame.Rect(
                        int(obj.x * self.scale), 
                        int(obj.y * self.scale), 
                        int(obj.width * self.scale), 
                        int(obj.height * self.scale)
                    ))
            
            
        # 2. Tiles de grilla de CELDAS ( "colisiones_grid" Tiled. ) ESCALADO X2
        for layer in self.tmx_data.visible_layers:
            if layer.name == "colisiones_grid":
                if hasattr(layer, "data"):
                    for x, y, gid in layer:
                        if gid != 0:
                            rects.append(pygame.Rect(
                                int(x * self.tmx_data.tilewidth * self.scale), 
                                int(y * self.tmx_data.tileheight * self.scale), 
                                int(self.tmx_data.tilewidth * self.scale), 
                                int(self.tmx_data.tileheight * self.scale)
                            ))
        return rects

    def get_spawn_point(self, name="player_spawn", default=(400, 350)):
        """Busca un objeto en el mapa de Tiled por su nombre y devuelve sus coordenadas escaladas."""
        for obj in self.tmx_data.objects:
            if obj.name == name:
                return int(obj.x * self.scale), int(obj.y * self.scale)
        return default

    def get_patrol_path(self, layer_name="enemy_patrols"):
        patrol_paths = []

# PATRULLA ENEMIGO. RUTA.
        for layer in self.tmx_data.visible_layers:
            if layer.name == layer_name:
                for obj in layer:
                    if hasattr(obj, 'points'):
                        scaled_points = []
                        for p in obj.points:
                            px = p[0] * self.scale
                            # Si quieres subir toda la ruta, puedes restar un valor fijo (ej. 30 o 40 píxeles)
                            py = (p[1] * self.scale) - 35 
                            scaled_points.append((int(px), int(py)))
                        
                        if scaled_points:
                            patrol_paths.append(scaled_points)
                            
        return patrol_paths
