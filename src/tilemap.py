import pygame
import pytmx
from pytmx.util_pygame import load_pygame
from pathfinding.core.grid import Grid

class TiledMap:
    def __init__(self, filename, scale=2):
        self.tmx_data = load_pygame(filename)
        self.scale = scale
        self.width = int(self.tmx_data.width * self.tmx_data.tilewidth * self.scale)
        self.height = int(self.tmx_data.height * self.tmx_data.tileheight * self.scale)

    def render_below(self, surface, camera):
        """Renderiza todas las capas EXCEPTO la capa de techos aplicando la escala correcta."""
        offset = camera.camera_rect.topleft

        for layer in self.tmx_data.visible_layers:
            # Si es la capa de techos, la ignoramos por ahora
            if layer.name in ("techos", "roof", "capa_techo"):
                continue

            # 1. Capa de imagen de fondo
            if hasattr(layer, "image") and layer.image:
                img_scaled = pygame.transform.scale(
                    layer.image, 
                    (int(layer.image.get_width() * self.scale), int(layer.image.get_height() * self.scale))
                )
                # Aplicamos la posición con el offset de la cámara
                surface.blit(img_scaled, offset)
                
            # 2. Capa de patrones de colisión / grid o tilelayers normales
            elif hasattr(layer, "data"):
                for x, y, gid in layer:
                    if gid != 0:
                        tile = self.tmx_data.get_tile_image_by_gid(gid)
                        if tile:
                            tile_scaled = pygame.transform.scale(
                                tile, 
                                (int(tile.get_width() * self.scale), int(tile.get_height() * self.scale))
                            )
                            pos_x = (x * self.tmx_data.tilewidth * self.scale) + offset[0]
                            pos_y = (y * self.tmx_data.tileheight * self.scale) + offset[1]
                            surface.blit(tile_scaled, (pos_x, pos_y))

    def render_roofs(self, surface, camera, render_condition=True):
        """Renderiza la capa de techos únicamente si se cumple la condición (Snake oculto en recoveco)."""
        # Si Snake no está oculto/bajo techo, no dibujamos nada de esta capa
        if not render_condition:
            return

        offset = camera.camera_rect.topleft

        for layer in self.tmx_data.visible_layers:
            if layer.name in ("techos", "roof", "capa_techo"):
                if hasattr(layer, "image") and layer.image:
                    img_scaled = pygame.transform.scale(
                        layer.image, 
                        (int(layer.image.get_width() * self.scale), int(layer.image.get_height() * self.scale))
                    )
                    surface.blit(img_scaled, offset)
                elif hasattr(layer, "data"):
                    standard_tile_h = self.tmx_data.tileheight

                    for x, y, gid in layer:
                        if gid != 0:
                            tile = self.tmx_data.get_tile_image_by_gid(gid)
                            if tile:
                                tile_scaled = pygame.transform.scale(
                                    tile, 
                                    (int(tile.get_width() * self.scale), int(tile.get_height() * self.scale))
                                )
                                pos_x = (x * self.tmx_data.tilewidth * self.scale) + offset[0]
                                
                                tile_h = tile.get_height()
                                height_difference = tile_h - standard_tile_h
                                
                                pos_y = (y * standard_tile_h * self.scale) + offset[1] - (height_difference * self.scale)
                                
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

    def load_codec_zones(self, layer_name="codec_trigger"):
        codec_zones = []
        for layer in self.tmx_data.layers:   # .layers incluye capas ocultas
            if layer.name != layer_name or not isinstance(layer, pytmx.TiledObjectGroup):
                continue
            layer_props = dict(layer.properties) if layer.properties else {}
            for obj in layer:
                props = dict(layer_props)
                if getattr(obj, "properties", None):
                    props.update(obj.properties)
                call_id = props.get("call_id") or getattr(obj, "call_id", None) or "default"
                codec_zones.append({
                    "rect": pygame.Rect(
                        int(obj.x * self.scale),
                        int(obj.y * self.scale),
                        int(obj.width * self.scale),
                        int(obj.height * self.scale),
                    ),
                    "call_id": call_id,
                })
        return codec_zones

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
                            py = (p[1] * self.scale) - 7
                            scaled_points.append((int(px), int(py)))
                        
                        if scaled_points:
                            patrol_paths.append(scaled_points)
                            
        return patrol_paths

    def get_hidden_zones(self, layer_name="zonas_oculto"):
        """Devuelve una lista de pygame.Rect con las zonas donde Snake debe quedar oculto."""
        hidden_rects = []
        print(f"Buscando capa: {layer_name}")
        
        try:
            if self.tmx_data:
                layer = self.tmx_data.get_layer_by_name(layer_name)
                obj_list = getattr(layer, 'objects', layer)
                
                for obj in obj_list:
                    print(f"¡Objeto encontrado en {layer_name}!")
                    rx = obj.x * self.scale
                    ry = obj.y * self.scale
                    rw = obj.width * self.scale
                    rh = obj.height * self.scale
                    hidden_rects.append(pygame.Rect(rx, ry, rw, rh))
        except Exception as e:
            print(f"Aviso al leer las zonas ocultas (se ignora de forma segura): {e}")
            
        return hidden_rects  # SIEMPRE devuelve una lista, nunca None

    def get_hidden_zones_top(self):
        return self.get_hidden_zones("zonas_oculto_top")

    def get_hidden_zones_bottom(self):
        return self.get_hidden_zones("zonas_oculto_bottom")
    
    def get_top_barriers(self, layer_name="limites_top"):
        barriers = []
        try:
            layer = self.tmx_data.get_layer_by_name(layer_name)
            obj_list = getattr(layer, 'objects', layer)
            for obj in obj_list:
                rx = obj.x * self.scale
                ry = obj.y * self.scale
                rw = obj.width * self.scale
                rh = obj.height * self.scale
                barriers.append(pygame.Rect(rx, ry, rw, rh))
        except Exception:
            # Si la capa aún no fue creada en Tiled, devuelve una lista vacía sin romper nada
            pass
        return barriers
    
    def get_triggers(self):
        """Busca y retorna una lista de rectángulos de los triggers junto con sus propiedades escaladas."""
        triggers = []
        for layer in self.tmx_data.visible_layers:
            # Solo recorremos los objetos si la capa se llama estrictamente 'triggers'
            # (Un grupo de objetos de pytmx no tiene atributo 'objects', hay que chequear el tipo.)
            if layer.name == "triggers" and isinstance(layer, pytmx.TiledObjectGroup):
                for obj in layer:
                    if obj.name in ["truck_trigger", "exit_trigger", "vent_trigger"]:
                        rect = pygame.Rect(
                            int(obj.x * self.scale),
                            int(obj.y * self.scale),
                            int(obj.width * self.scale),
                            int(obj.height * self.scale)
                        )
                        # Extracción segura de propiedades tanto si están en obj.properties como en atributos del objeto
                        # Las propiedades pueden estar en la capa 'triggers' (truck_interior1.tmx) o en el
                        # propio objeto (entry_point...tmx). Si están en los dos, manda el objeto.
                        props = dict(layer.properties) if layer.properties else {}
                        if hasattr(obj, 'properties') and obj.properties:
                            props.update(obj.properties)
                        for key in ['target_map', 'spawn_x', 'spawn_y']:
                            if hasattr(obj, key) and getattr(obj, key) is not None:
                                props[key] = getattr(obj, key)

                        triggers.append({
                            "name": obj.name,
                            "rect": rect,
                            "properties": props
                        })
        return triggers

    def create_pathfinding_grid(self, cell_px=16, actor_size=(16, 16)):
        """cell_px: tamaño de celda en píxeles REALES (ya escalados)."""
        cols = self.width // cell_px
        rows = self.height // cell_px
        walls = self.get_collision_rects()
        aw, ah = actor_size

        matrix = []
        for row in range(rows):
            line = []
            for col in range(cols):
                body = pygame.Rect(0, 0, aw, ah)
                body.center = (col * cell_px + cell_px // 2, row * cell_px + cell_px // 2)
                line.append(0 if body.collidelist(walls) != -1 else 1)
            matrix.append(line)

        grid = Grid(matrix=matrix)
        grid.cell_px = cell_px          # <- el enemigo lo lee de acá
        grid.region = self._label_regions(matrix)
        return grid

    def _label_regions(self, matrix):
        rows, cols = len(matrix), len(matrix[0])
        region = [[-1] * cols for _ in range(rows)]
        rid = 0
        for r in range(rows):
            for c in range(cols):
                if matrix[r][c] and region[r][c] == -1:
                    stack = [(c, r)]
                    region[r][c] = rid
                    while stack:
                        x, y = stack.pop()
                        for nx, ny in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
                            if 0 <= nx < cols and 0 <= ny < rows \
                                    and matrix[ny][nx] and region[ny][nx] == -1:
                                region[ny][nx] = rid
                                stack.append((nx, ny))
                    rid += 1
        return region