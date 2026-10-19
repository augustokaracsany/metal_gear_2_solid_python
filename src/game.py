import os
import pygame
from src.enemy import Enemy
from src.player import Player
from src.camera import Camera
from src.tilemap import TiledMap  # Mapas TMX
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from src.items import Item  

class Game:
    def __init__(self, mission_number=1):
        self.mission_number = mission_number
        
        # DICCIONARIO DE NIVELES
        self.levels_data = {
            1: {
                "tmx": "assets/sprites/maps/entry_point_brightness3-576x768.tmx",
                "png": "assets/sprites/maps/entry_point_brightness3-576x768.png"
            },
            2: {
                "tmx": "assets/sprites/maps/building1_floor1-960x960.tmx",
                "png": "assets/sprites/maps/building1_floor1-960x960.png"
            },
            3: {
                "tmx": "assets/sprites/maps/mission3_map.tmx",
                "png": "assets/sprites/maps/mission3_map.png"
            },
            4: {
                "tmx": "assets/sprites/maps/mission4_map.tmx",
                "png": "assets/sprites/maps/mission4_map.png"
            },
            # === AGREGADO: MAPA INTERIOR DEL CAMIÓN ===
            "truck": {
                "tmx": "assets/sprites/maps/truck_interior.tmx",
                "png": "assets/sprites/maps/truck_interior.jpg"
            }
        }
        
        current_level = self.levels_data.get(self.mission_number, self.levels_data[1])
        
        # Grupos de Sprites
        self.all_sprites = pygame.sprite.Group()
        self.enemies_group = pygame.sprite.Group()
        self.items_group = pygame.sprite.Group()
        
        # Instanciación inicial del mapa y entidades mediante el método modular
        self.load_level(current_level["tmx"])

        # Definimos una resolución virtual más pequeña (la mitad de la pantalla = zoom x2 visual perfecto)
        self.virtual_width = SCREEN_WIDTH // 2
        self.virtual_height = SCREEN_HEIGHT // 2
        self.virtual_surface = pygame.Surface((self.virtual_width, self.virtual_height))

        # Instanciamos la cámara pasándole el tamaño virtual correcto
        if self.map:
            map_width = self.map.width
            map_height = self.map.height
        else:
            map_width = self.map_image.get_width()
            map_height = self.map_image.get_height()

        self.camera = Camera(map_width, map_height, self.virtual_width, self.virtual_height)
        
        # Obtenemos las coordenadas de inicio desde el objeto 'player_spawn' del mapa Tiled
        spawn_x, spawn_y = self.map.get_spawn_point("player_spawn", (400, 350)) if self.map else (400, 350)
                
        # Instanciamos a Snake en la posición del mapa
        self.player = Player(spawn_x, spawn_y)
        self.all_sprites.add(self.player)

    def load_level(self, tmx_or_key):
        """Carga un nivel (puede recibir la ruta tmx o la clave del diccionario como 'truck')"""
        if tmx_or_key in self.levels_data:
            level_info = self.levels_data[tmx_or_key]
            tmx_path = level_info["tmx"]
            png_path = level_info["png"]
        else:
            tmx_path = tmx_or_key
            png_path = None

        try:
            self.map = TiledMap(tmx_path, scale=2)
        except Exception as e:
            print(f"AVISO: No se pudo cargar el mapa TMX ({e}). Usando imagen plana de respaldo.")
            self.map = None
            if png_path and os.path.exists(png_path):
                self.raw_map = pygame.image.load(png_path).convert()
            else:
                self.raw_map = pygame.Surface((576, 768)) # Respaldo por defecto
            self.map_scale = 2 
            self.map_image = pygame.transform.scale(self.raw_map, (self.raw_map.get_width() * self.map_scale, self.raw_map.get_height() * self.map_scale))

                # Actualizar zonas ocultas y barreras de forma segura
        if self.map:
            self.hidden_zones = self.map.get_hidden_zones("zonas_oculto") or []
            self.hidden_zones_top = self.map.get_hidden_zones_top() or []
            self.hidden_zones_bottom = self.map.get_hidden_zones_bottom() or []
            self.top_barriers = self.map.get_top_barriers("limites_top") or []
        else:
            self.hidden_zones = []
            self.hidden_zones_top = []
            self.hidden_zones_bottom = []
            self.top_barriers = []
            self.pathfinding_grid = None

        # Limpiar grupos de la escena previa
        self.enemies_group.empty()
        self.items_group.empty()

        if self.map:
            # A. RE-INSTANCIAR ENEMIGOS
            patrol_routes = self.map.get_patrol_path("enemy_patrols")
            if patrol_routes:
                for ruta in patrol_routes:
                    pos_inicial_x = ruta[0][0]
                    pos_inicial_y = ruta[0][1]
                    guardia = Enemy(pos_inicial_x, pos_inicial_y, ruta)
                    self.enemies_group.add(guardia)

            # B. RE-INSTANCIAR ÍTEMS (CAJA DE CARTÓN, ETC.)
            if hasattr(self.map.tmx_data, 'objects'):
                for obj in self.map.tmx_data.objects:
                    if obj.name == "cardboard_box" and hasattr(self, 'player') and "cardboard_box" not in self.player.inventory:
                        scale = self.map.scale
                        try:
                            box_item = Item("cardboard_box", 0, 0, "assets/sprites/solid_python/cardboard_box.png", scale=2)
                            box_item.rect.center = (int((obj.x + obj.width / 2) * scale), int((obj.y + obj.height / 2) * scale))
                            self.items_group.add(box_item)
                        except Exception as e:
                            print(f"Error cargando sprite de la caja: {e}")

            # C. GRILLA DE PATHFINDING (después de crear los enemigos: usa el tamaño de su hitbox)
            if self.enemies_group:
                actor_size = self.enemies_group.sprites()[0].rect.size
                self.pathfinding_grid = self.map.create_pathfinding_grid(16, actor_size)
            else:
                self.pathfinding_grid = None

    def check_map_transitions(self):
        """Detecta colisiones con triggers de cambio de mapa."""
        if not self.map:
            return

        triggers = self.map.get_triggers()
        for trigger in triggers:
            if self.player.rect.colliderect(trigger["rect"]):
                props = trigger["properties"]
                target_map = props.get("target_map")
                
                print(f"¡Transición! Entrando a: {target_map}")

                # Cargar el mapa objetivo y reubicar a Snake
                self.load_level(target_map)

                scale = self.map.scale if self.map else 2
                spawn_x = float(props.get("spawn_x", 180)) * scale
                spawn_y = float(props.get("spawn_y", 550)) * scale
                self.player.x = spawn_x
                self.player.y = spawn_y
                self.player.rect.x = int(spawn_x)
                self.player.rect.y = int(spawn_y)
                
                # Actualizar dimensiones de la cámara para el nuevo mapa
                map_width = self.map.width if self.map else self.map_image.get_width()
                map_height = self.map.height if self.map else self.map_image.get_height()
                self.camera = Camera(map_width, map_height, self.virtual_width, self.virtual_height)
                break

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                import sys
                sys.exit()
            self.player.punch_self_event(event)

    def update(self, dt):
        walls = self.map.get_collision_rects() if self.map else []

        # Actualización de Lógica del jugador
        self.player.update(
            dt,
            walls,
            self.top_barriers,
            self.hidden_zones,
            self.hidden_zones_top,
            self.hidden_zones_bottom,
        )

        # Recoger ítems del piso
        if hasattr(self.player, 'collect_items'):
            self.player.collect_items(self.items_group)

        # Transición de mapa
        self.check_map_transitions()

        for enemy in self.enemies_group:
            enemy.update(dt, walls, self.player, self.pathfinding_grid)

        # Actualizamos la posición de la cámara centrada en Snake.
        self.camera.update(self.player)

    def draw(self, surface):
        self.virtual_surface.fill((0, 0, 0))

        walls = self.map.get_collision_rects() if self.map else []

        if self.map:
            self.map.render_below(self.virtual_surface, self.camera)
        else:
            self.virtual_surface.blit(self.map_image, self.camera.camera_rect.topleft) 

        # Dibujar ítems del piso
        for item in self.items_group:
            item_rect = self.camera.apply(item)
            self.virtual_surface.blit(item.image, item_rect)
        
        # Dibujamos ordenados por profundidad (Z-index clásico de Metal Gear)
        entities_to_draw = [self.player] + list(self.enemies_group)
        entities_to_draw.sort(key=lambda entity: entity.rect.bottom)

        for entity in entities_to_draw:
            entity.draw_with_camera(self.virtual_surface, self.camera)

        # Dibujar conos de visión de los enemigos
        for enemy in self.enemies_group:
            enemy.draw_vision(self.virtual_surface, self.camera)
        
        if self.map:
            self.map.render_roofs(
                self.virtual_surface,
                self.camera,
                render_condition=self.player.is_hidden or self.player.is_near_hidden_zone(margin=15),
            )

        scaled_surface = pygame.transform.scale(self.virtual_surface, (surface.get_width(), surface.get_height()))
        surface.blit(scaled_surface, (0, 0))

        # --- DEBUG VISUAL DE ZONAS OCULTAS ---
        if hasattr(self, "hidden_zones") and self.hidden_zones:
            for zone in self.hidden_zones:
                debug_screen_rect = zone.move(self.camera.camera_rect.topleft)
                pygame.draw.rect(self.virtual_surface, (0, 255, 255), debug_screen_rect, 2)