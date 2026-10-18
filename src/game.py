import os
import pygame
from src.player import Player
from src.camera import Camera
from src.enemy import Enemy
from src.tilemap import TiledMap
from src.items import Item  # Asegúrate de importar la clase Item si la usas

# Escala de dibujo de cada mapa (por defecto 2). La imagen del interior del camión es mucho más
# grande que la del resto de los mapas, por eso se dibuja más chico (0.5). Subir/bajar este número
# agranda/achica el camión respecto de Snake.
DEFAULT_MAP_SCALE = 2
MAP_SCALES = {"truck_interior1.tmx": 2}

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

        # 1. Instanciamos a Snake
        self.player = Player(400, 350)
        self.all_sprites.add(self.player)

        # 2. Cargar el nivel inicial y sus entidades (enemigos, ítems)
        self.load_level(current_level["tmx"])

        # Posicionar a Snake en el spawn point inicial del mapa si existe
        if self.map:
            spawn_x, spawn_y = self.map.get_spawn_point("player_spawn", (400, 350))
            self.player.x = float(spawn_x)
            self.player.y = float(spawn_y)
            self.player.rect.x = int(spawn_x)
            self.player.rect.y = int(spawn_y)

    def load_level(self, tmx_path):
        """Carga o cambia el mapa TMX y regenera enemigos e ítems dinámicamente."""
        print(f"Cargando mapa TMX: {tmx_path}")
        try:
            map_scale = MAP_SCALES.get(os.path.basename(tmx_path), DEFAULT_MAP_SCALE)
            self.map = TiledMap(tmx_path, scale=map_scale)
        except Exception as e:
            print(f"AVISO: No se pudo cargar el mapa TMX ({tmx_path}): {e}")
            self.map = None

        map_width = self.map.width if self.map else 800
        map_height = self.map.height if self.map else 600

        self.camera = Camera(map_width, map_height)
        
        # Limpiar grupos de la escena previa
        self.enemies_group.empty()
        self.items_group.empty()

        if self.map:
            # A. RE-INSTANCIAR ENEMIGOS: Si el mapa actual contiene la capa 'enemy_patrols'
            patrol_routes = self.map.get_patrol_path("enemy_patrols")
            if patrol_routes:
                for ruta in patrol_routes:
                    pos_inicial_x = ruta[0][0]
                    pos_inicial_y = ruta[0][1]
                    guardia = Enemy(pos_inicial_x, pos_inicial_y, ruta)
                    self.enemies_group.add(guardia)

            # B. RE-INSTANCIAR LA CAJA DE CARTÓN: Si existe el objeto en Tiled y no se ha recogido
            if hasattr(self.map.tmx_data, 'objects'):
                for obj in self.map.tmx_data.objects:
                    if obj.name == "cardboard_box" and hasattr(self, 'player') and "cardboard_box" not in self.player.inventory:
                        scale = self.map.scale
                        try:
                            # El objeto de Tiled es una zona; dibujamos la caja (a la escala del mapa) en el centro.
                            box_item = Item("cardboard_box", 0, 0, "assets/sprites/solid_python/cardboard_box.png", scale=2)  # x2 = mismo factor que los sprites de Snake
                            box_item.rect.center = (int((obj.x + obj.width / 2) * scale), int((obj.y + obj.height / 2) * scale))
                            self.items_group.add(box_item)
                        except Exception as e:
                            print(f"Error cargando sprite de la caja: {e}")

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

                # La escala se toma del mapa NUEVO (ya cargado), porque cada mapa puede tener la suya.
                scale = self.map.scale
                spawn_x = float(props.get("spawn_x", 180)) * scale
                spawn_y = float(props.get("spawn_y", 550)) * scale
                self.player.x = spawn_x
                self.player.y = spawn_y
                self.player.rect.x = int(spawn_x)
                self.player.rect.y = int(spawn_y)
                break

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                import sys
                sys.exit()
            
            # Pasa eventos a Snake (E = Golpear, B = Equipar Caja, C = Agacharse)
            self.player.punch_self_event(event)

    def update(self, dt):
        # 1. Obtener rectángulos de colisión de paredes
        walls = self.map.get_collision_rects() if self.map else []

        # 2. Movimiento de Snake con colisiones
        self.player.update(dt, walls)

        # 3. Recoger ítems del piso
        if hasattr(self.player, 'collect_items'):
            self.player.collect_items(self.items_group)

        # 4. Transición de mapa
        self.check_map_transitions()

        # 5. Actualizar enemigos
        for enemy in self.enemies_group:
            enemy.update(dt)
        
        # 6. Actualizar cámara centrada en Snake
        self.camera.update(self.player)

    def draw(self, surface):
        surface.fill((0, 0, 0))

        # 1. Dibujar mapa TMX
        if self.map:
            self.map.render(surface, self.camera)

        # 2. Dibujar ítems del piso
        for item in self.items_group:
            item_rect = self.camera.apply(item)
            surface.blit(item.image, item_rect)

        # 3. Dibujar a Snake y Enemigos
        self.player.draw_with_camera(surface, self.camera)

        for enemy in self.enemies_group:
            enemy.draw_with_camera(surface, self.camera)