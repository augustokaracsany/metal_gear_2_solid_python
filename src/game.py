import os
import pygame
from src import enemy
from src.player import Player
from src.camera import Camera
from src.enemy import Enemy  # MERGE.
from src.tilemap import TiledMap  # Mapas TMX
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from src.items import Item  
from src.pause import PauseMenu

class Game:
    def __init__(self, mission_number=1):
        self.mission_number = mission_number

        # --- SISTEMA DE PAUSA ---
        self.is_paused = False
        self.pause_menu = PauseMenu(SCREEN_WIDTH, SCREEN_HEIGHT)
        
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
        
        # Instanciación inicial del mapa y entidades
        self.load_level(current_level["tmx"])

        self.virtual_width = SCREEN_WIDTH // 2
        self.virtual_height = SCREEN_HEIGHT // 2
        self.virtual_surface = pygame.Surface((self.virtual_width, self.virtual_height))

        if self.map:
            map_width = self.map.width
            map_height = self.map.height
        else:
            map_width = self.map_image.get_width()
            map_height = self.map_image.get_height()

        self.camera = Camera(map_width, map_height, self.virtual_width, self.virtual_height)
        
        spawn_x, spawn_y = self.map.get_spawn_point("player_spawn", (400, 350)) if self.map else (400, 350)
        self.player = Player(spawn_x, spawn_y)
        self.all_sprites.add(self.player)

    def load_level(self, tmx_or_key):
        """Carga un nivel"""
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
                self.raw_map = pygame.Surface((576, 768))
            self.map_scale = 2 
            self.map_image = pygame.transform.scale(self.raw_map, (self.raw_map.get_width() * self.map_scale, self.raw_map.get_height() * self.map_scale))

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

        self.enemies_group.empty()
        self.items_group.empty()

        if self.map:
            patrol_routes = self.map.get_patrol_path("enemy_patrols")
            if patrol_routes:
                for ruta in patrol_routes:
                    pos_inicial_x = ruta[0][0]
                    pos_inicial_y = ruta[0][1]
                    guardia = Enemy(pos_inicial_x, pos_inicial_y, ruta)
                    self.enemies_group.add(guardia)

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

    def check_map_transitions(self):
        if not self.map:
            return

        triggers = self.map.get_triggers()
        for trigger in triggers:
            if self.player.rect.colliderect(trigger["rect"]):
                props = trigger["properties"]
                target_map = props.get("target_map")
                self.load_level(target_map)

                scale = self.map.scale if self.map else 2
                spawn_x = float(props.get("spawn_x", 180)) * scale
                spawn_y = float(props.get("spawn_y", 550)) * scale
                self.player.x = spawn_x
                self.player.y = spawn_y
                self.player.rect.x = int(spawn_x)
                self.player.rect.y = int(spawn_y)
                
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

            # Abrir/cerrar Pausa con la tecla M
            if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                self.is_paused = not self.is_paused
                continue

            # Si el juego está en pausa, la navegación y selección las procesa la pausa
            if self.is_paused:
                action = self.pause_menu.handle_input(event)
                if action == "CONTINUAR":
                    self.is_paused = False
                elif action == "PUNTO DE CONTROL":
                    self.pause_menu.trigger_feedback("No se encontró ningún punto de guardado previo.")
                elif action == "REINICIAR MISIÓN":
                    # Reinicia el nivel y reubica a Snake en el spawn
                    current_key = self.mission_number
                    self.load_level(current_key)
                    spawn_x, spawn_y = self.map.get_spawn_point("player_spawn", (400, 350)) if self.map else (400, 350)
                    self.player.x, self.player.y = spawn_x, spawn_y
                    self.player.rect.x, self.player.rect.y = int(spawn_x), int(spawn_y)
                    self.is_paused = False
                elif action == "VOLVER AL MENÚ":
                    self.is_paused = False
                    return "GOTO_MENU"
            else:
                # Si el juego NO está en pausa, responde a las acciones del jugador
                self.player.punch_self_event(event)
        return None

    def update(self, dt):
        if self.is_paused:
            return

        walls = self.map.get_collision_rects() if self.map else []

        self.player.update(
            dt,
            walls,
            self.top_barriers,
            self.hidden_zones,
            self.hidden_zones_top,
            self.hidden_zones_bottom,
        )

        if hasattr(self.player, 'collect_items'):
            self.player.collect_items(self.items_group)

        self.check_map_transitions()

        for enemy in self.enemies_group:
            enemy.update(dt, walls)  

        self.camera.update(self.player)

    def draw(self, surface):
        self.virtual_surface.fill((0, 0, 0))

        walls = self.map.get_collision_rects() if self.map else []

        if self.map:
            self.map.render_below(self.virtual_surface, self.camera)
        else:
            self.virtual_surface.blit(self.map_image, self.camera.camera_rect.topleft) 

        for item in self.items_group:
            item_rect = self.camera.apply(item)
            self.virtual_surface.blit(item.image, item_rect)
        
        entities_to_draw = [self.player] + list(self.enemies_group)
        entities_to_draw.sort(key=lambda entity: entity.rect.bottom)

        for entity in entities_to_draw:
            entity.draw_with_camera(self.virtual_surface, self.camera)

        for enemy in self.enemies_group:
            enemy.check_vision(self.player, walls, self.virtual_surface, self.camera)
        
        if self.map:
            self.map.render_roofs(
                self.virtual_surface,
                self.camera,
                render_condition=self.player.is_hidden or self.player.is_near_hidden_zone(margin=15),
            )

        scaled_surface = pygame.transform.scale(self.virtual_surface, (surface.get_width(), surface.get_height()))
        surface.blit(scaled_surface, (0, 0))

        if hasattr(self, "hidden_zones") and self.hidden_zones:
            for zone in self.hidden_zones:
                debug_screen_rect = zone.move(self.camera.camera_rect.topleft)
                pygame.draw.rect(self.virtual_surface, (0, 255, 255), debug_screen_rect, 2)

        # RENDERIZAR PAUSA
        if self.is_paused:
            self.pause_menu.draw(surface)