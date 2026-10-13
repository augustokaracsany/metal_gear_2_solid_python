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
        for obj in self.tmx_data.objects:
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