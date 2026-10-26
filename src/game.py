import os
import pygame
import sys
from src.enemy import Enemy
from src.player import Player
from src.camera import Camera
from src.tilemap import TiledMap  # Mapas TMX
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from src.items import Item  
from src.hud import HealthBar
from src.settings import ENEMY_CONTACT_DAMAGE
from src.pause import PauseMenu
from src.settings import PUNCH_DAMAGE, PUNCH_HIT_PADDING, PUNCH_STUN_TIME
from src.inventory import InventoryMenu
from src.item_message import ItemMessage

class Game:
    def __init__(self, mission_number=1):
        self.mission_number = mission_number
        # "PLAYING" -> Jugador con vida
        # "DYING"   -> Animación de muerte
        # "GAME_OVER" -> Pantalla de muerte
        self.state = "PLAYING"
        self.fade_alpha = 255
        self.fading_in = True
        self.game_over = False
        self.game_over_timer = 0.0
        self.victory_selected_option = 0
        self.victory_timer = 0.0
        self.fade_in_timer = pygame.time.get_ticks()
        self.game_over_selected_option = 0
        self.return_to_menu = False

        # --- SISTEMA DE PAUSA ---
        self.is_paused = False
        self.pause_menu = PauseMenu(SCREEN_WIDTH, SCREEN_HEIGHT)

        # --- INVENTARIO ---
        self.inventory_open = False
        self.inventory_menu = InventoryMenu(SCREEN_WIDTH, SCREEN_HEIGHT)
        # --- MÚSICA DE FONDO (solo misión 1: Entry Point) ---
        self.start_level_music()
        
        # 1. DICCIONARIO DE NIVELES: Mapea cada misión a sus respectivas rutas de archivos
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
        self.bullets_group = pygame.sprite.Group()
        
        self.enemy_bullets = pygame.sprite.Group()

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

        self.health_bar = HealthBar()
        self.item_message = ItemMessage()

    def start_level_music(self):
        """Música de fondo en bucle del mapa Entry Point (misión 1).

        Usa el volumen actual del slider de OPCIONES de la pausa, así lo que se ve
        en pantalla coincide con lo que suena. Si el archivo no está, el juego sigue
        sin música (solo avisa por consola)."""
        if self.mission_number != 1:
            return
        try:
            pygame.mixer.music.load("assets/audio/music/musica_entry_point.mp3")
            pygame.mixer.music.set_volume(self.pause_menu.music_volume)
            pygame.mixer.music.play(-1)  # -1 = bucle infinito
        except Exception as e:
            print(f"Aviso música de Entry Point: {e}")

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

        self.enemies_group.empty()
        self.items_group.empty()
        self.enemy_bullets.empty()

        # Actualizar zonas ocultas y barreras de forma segura
        if self.map:
            self.hidden_zones = self.map.get_hidden_zones("zonas_oculto") or []
            self.hidden_zones_top = self.map.get_hidden_zones_top() or []
            self.hidden_zones_bottom = self.map.get_hidden_zones_bottom() or []
            self.top_barriers = self.map.get_top_barriers("limites_top") or []
            self.walls = self.map.get_collision_rects()   # cacheadas una sola vez

        self.enemies_group.empty()
        self.items_group.empty()
        self.bullets_group.empty()

        if self.map:
            patrol_routes = self.map.get_patrol_path("enemy_patrols")
            for i, ruta in enumerate(patrol_routes):
                guardia = Enemy(ruta[0][0], ruta[0][1], ruta, start_delay=i * 1.0)
                self.enemies_group.add(guardia)

            if hasattr(self.map.tmx_data, 'objects'):
                for obj in self.map.tmx_data.objects:
                    if obj.name == "cardboard_box" and hasattr(self, 'player') and "cardboard_box" not in self.player.inventory:
                        scale = self.map.scale
                        try:
                            box_item = Item("cardboard_box", 0, 0, "assets/sprites/solid_python/box2.png", scale=2)
                            box_item.rect.center = (int((obj.x + obj.width / 2) * scale), int((obj.y + obj.height / 2) * scale))
                            self.items_group.add(box_item)
                        except Exception as e:
                            print(f"Error cargando sprite de la caja: {e}")

            # Ración de comida (camión de truck_interior_2). Se agrega aparte, igual que la caja.
            if hasattr(self.map.tmx_data, 'objects'):
                for obj in self.map.tmx_data.objects:
                    if obj.name == "food_ration" and hasattr(self, 'player') and "food_ration" not in self.player.inventory:
                        scale = self.map.scale
                        try:
                            ration_item = Item("food_ration", 0, 0, "assets/sprites/items/racion_roja.png", scale=1.7)
                            ration_item.rect.center = (int((obj.x + obj.width / 2) * scale), int((obj.y + obj.height / 2) * scale))
                            self.items_group.add(ration_item)
                        except Exception as e:
                            print(f"Error cargando sprite de la ración: {e}")

            # Pistola (Entry Point). Se agrega aparte, igual que la caja y la ración.
            # OJO: acá NO se exige que ya exista self.player, porque este mapa se carga
            # en __init__ antes de crear a Snake.
            if hasattr(self.map.tmx_data, 'objects'):
                for obj in self.map.tmx_data.objects:
                    if obj.name == "pistola" and (not hasattr(self, 'player') or "pistola" not in self.player.inventory):
                        scale = self.map.scale
                        try:
                            pistol_item = Item("pistola", 0, 0, "assets/sprites/weapons/pistola.png", scale=1.2)
                            pistol_item.rect.center = (int((obj.x + obj.width / 2) * scale), int((obj.y + obj.height / 2) * scale))
                            self.items_group.add(pistol_item)
                        except Exception as e:
                            print(f"Error cargando sprite de la pistola: {e}")

            # Grilla: DESPUÉS de crear los enemigos, con el hitbox real del guardia
            if self.enemies_group:
                actor_size = self.enemies_group.sprites()[0].rect.size
                self.pathfinding_grid = self.map.create_pathfinding_grid(
                    cell_px=8, actor_size=actor_size)
            else:
                self.pathfinding_grid = None
        else:
            self.hidden_zones = []
            self.hidden_zones_top = []
            self.hidden_zones_bottom = []
            self.top_barriers = []
            self.walls = []
            self.pathfinding_grid = None

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

    def trigger_victory_sequence(self):
        if self.state == "PLAYING":
            self.state = "VICTORY"
            self.victory_timer = pygame.time.get_ticks()
            self.fade_alpha = 0
            try:
                pygame.mixer.music.load("assets/audio/music/mission_complete.mp3")
                pygame.mixer.music.play()
            except Exception as e:
                print(f"Aviso música de victoria: {e}")

    def trigger_death_sequence(self):

        self.player.is_dead = True
        self.player.frame_index = 0
        self.player.anim_timer = 0.0

        if self.state == "PLAYING":
            self.state = "DYING"
            self.death_timer = pygame.time.get_ticks()
            self.fade_alpha = 0

            self.player.start_death_animation()
            
            try:
                death_sfx = pygame.mixer.Sound("assets/audio/sfx/snake_scream.mp3")
                death_sfx.play()
            except Exception as e:
                print(f"Aviso SFX de muerte: {e}")

    def has_next_mission(self):
        """Verifica si existe una siguiente misión en el diccionario Y si sus archivos existen en el disco."""
        next_num = self.mission_number + 1
        if next_num not in self.levels_data:
            return False
        
        data = self.levels_data[next_num]
        tmx_exists = os.path.exists(data.get("tmx", ""))
        png_exists = os.path.exists(data.get("png", ""))
        
        return tmx_exists or png_exists
        
        data = self.levels_data[next_num]
        tmx_exists = os.path.exists(data.get("tmx", ""))
        png_exists = os.path.exists(data.get("png", ""))
        
        return tmx_exists or png_exists
        
    def restart_mission(self):
        """Reinicia la misión completa: mapa, enemigos, ítems y estado de Snake."""
        # 1) Estado del jugador (ANTES de cargar el nivel: la caja solo reaparece
        #    si Snake no la tiene en el inventario).
        p = self.player
        p.inventory = []
        p.is_disguised = False
        p.is_punching = False
        p.is_transitioning = False
        p.target_stance = None
        p.forced_crouch = False
        p.crouch_hold_timer = 0.0
        p.is_hidden = False
        p.is_moving = False
        p.active_hidden_top_zone = None
        p.active_hidden_bottom_marker = None
        p.stance = "STAND"
        p.facing = "DOWN"
        p.frame_index = 0
        p.anim_timer = 0.0
        p.update_offsets_for_stance()

        # 2) Mapa de la misión desde cero (enemigos + ítems como la caja del camión).
        #    Si Snake estaba dentro del camión, esto también lo devuelve al mapa principal.
        self.load_level(self.mission_number)

        # 3) Cámara con las medidas del mapa recargado.
        if self.map:
            map_width, map_height = self.map.width, self.map.height
        else:
            map_width, map_height = self.map_image.get_width(), self.map_image.get_height()
        self.camera = Camera(map_width, map_height, self.virtual_width, self.virtual_height)

        # 4) Snake de vuelta al spawn.
        spawn_x, spawn_y = self.map.get_spawn_point("player_spawn", (400, 350)) if self.map else (400, 350)
        p.x, p.y = float(spawn_x), float(spawn_y)
        p.rect.x, p.rect.y = int(spawn_x), int(spawn_y)
        self.camera.update(p)

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if self.state == "VICTORY":
                has_next = self.has_next_mission()
                max_options = 3 if has_next else 2

                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_a, pygame.K_LEFT):
                        self.victory_selected_option = (self.victory_selected_option - 1) % max_options
                    elif event.key in (pygame.K_d, pygame.K_RIGHT):
                        self.victory_selected_option = (self.victory_selected_option + 1) % max_options
                    elif event.key in (pygame.K_RETURN,):
                        self.confirm_victory_option()

                elif event.type == pygame.MOUSEMOTION:
                    mx, my = event.pos
                    if hasattr(self, "vic_retry_rect") and self.vic_retry_rect.collidepoint(mx, my):
                        self.victory_selected_option = 0
                    elif hasattr(self, "vic_next_rect") and has_next and self.vic_next_rect.collidepoint(mx, my):
                        self.victory_selected_option = 1
                    elif hasattr(self, "vic_exit_rect") and self.vic_exit_rect.collidepoint(mx, my):
                        self.victory_selected_option = (2 if has_next else 1)

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    if hasattr(self, "vic_retry_rect") and self.vic_retry_rect.collidepoint(mx, my):
                        self.victory_selected_option = 0
                        self.confirm_victory_option()
                    elif hasattr(self, "vic_next_rect") and has_next and self.vic_next_rect.collidepoint(mx, my):
                        self.victory_selected_option = 1
                        self.confirm_victory_option()
                    elif hasattr(self, "vic_exit_rect") and self.vic_exit_rect.collidepoint(mx, my):
                        self.victory_selected_option = (2 if has_next else 1)
                        self.confirm_victory_option()
                continue
            
            if self.state == "GAME_OVER":
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_a, pygame.K_LEFT):
                        self.game_over_selected_option = 0  # Reintentar
                    elif event.key in (pygame.K_d, pygame.K_RIGHT):
                        self.game_over_selected_option = 1  # Salir
                    elif event.key in (pygame.K_RETURN,):
                        self.confirm_game_over_option()
                elif event.type == pygame.MOUSEMOTION:
                    mx, my = event.pos
                    if hasattr(self, "retry_rect") and self.retry_rect.collidepoint(mx, my):
                        self.game_over_selected_option = 0
                    elif hasattr(self, "exit_rect") and self.exit_rect.collidepoint(mx, my):
                        self.game_over_selected_option = 1

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    if hasattr(self, "retry_rect") and self.retry_rect.collidepoint(mx, my):
                        self.game_over_selected_option = 0
                        self.confirm_game_over_option()
                    elif hasattr(self, "exit_rect") and self.exit_rect.collidepoint(mx, my):
                        self.game_over_selected_option = 1
                        self.confirm_game_over_option()
                continue

            # Inventario: se abre con la tecla I y mientras está abierto el juego queda pausado.
            if self.inventory_open:
                if self.inventory_menu.handle_input(event, self.player) == "CLOSE":
                    self.inventory_open = False
                continue
            if (event.type == pygame.KEYDOWN and event.key == pygame.K_i
                    and not self.is_paused and self.state == "PLAYING"):
                self.inventory_menu.open(self.player)
                self.inventory_open = True
                continue

            # Abrir Pausa con la tecla P (cerrar / volver lo maneja el propio menú de pausa)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and not self.is_paused:
                self.is_paused = True

            # Si el juego está en pausa, la navegación y selección las procesa la pausa
            if self.is_paused:
                action = self.pause_menu.handle_input(event)
                if action == "CONTINUAR":
                    self.is_paused = False
                elif action == "PUNTO DE CONTROL":
                    self.pause_menu.trigger_feedback("No se encontró ningún punto de guardado previo.")
                elif action == "REINICIAR MISIÓN":
                    self.restart_mission()
                    current_key = self.mission_number
                    self.load_level(current_key)
                    spawn_x, spawn_y = self.map.get_spawn_point("player_spawn", (400, 350)) if self.map else (400, 350)
                    self.player.x, self.player.y = spawn_x, spawn_y
                    self.player.rect.x, self.player.rect.y = int(spawn_x), int(spawn_y)
                    self.is_paused = False
                elif action == "VOLVER AL MENÚ":
                    self.is_paused = False
                    pygame.mixer.music.stop()  # corta la música de la misión al volver al menú principal
                    return "GOTO_MENU"
            else:
                # Si el juego NO está en pausa, responde a las acciones del jugador
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_k:  # Tecla de prueba de muerte
                        self.trigger_death_sequence()
                    elif event.key == pygame.K_v:
                        self.trigger_victory_sequence()
                    elif event.key == pygame.K_h:
                        self.player.take_damage(10)
                    elif event.key == pygame.K_j:
                        self.player.heal(10)
                    elif event.key == pygame.K_SPACE:
                        self.player_shoot()
                self.player.punch_self_event(event)
        return None

    def player_shoot(self):
        if self.state != "PLAYING":
            return
        bullet = self.player.shoot()
        print("DISPARO:", "OK" if bullet else "bloqueado", "| postura:", self.player.stance)
        if bullet:
            self.bullets_group.add(bullet)

    def confirm_victory_option(self):
        """Ejecuta la acción seleccionada en el menú de Victoria"""
        pygame.mixer.music.fadeout(1000)
        has_next = self.has_next_mission()
        
        if self.victory_selected_option == 0:
            self.__init__(self.mission_number)
        elif self.victory_selected_option == 1 and has_next:
            self.__init__(self.mission_number + 1)
        else:
            self.return_to_menu = True  # Activamos la bandera

    def confirm_game_over_option(self):
        pygame.mixer.music.fadeout(1000)
        if self.game_over_selected_option == 0:
            self.__init__(self.mission_number)
        else:
            self.return_to_menu = True  # Activamos la bandera

    def update(self, dt):
        # Manejo limpio del fundido de entrada (Fade-in)

        if self.fading_in:
            elapsed_fade = pygame.time.get_ticks() - self.fade_in_timer
            self.fade_alpha = max(0, 255 - int((elapsed_fade / 1000.0) * 255))
            if self.fade_alpha == 0:
                self.fading_in = False

        if self.is_paused or self.inventory_open:
            return

        if self.state == "DYING":
            elapsed_death = pygame.time.get_ticks() - self.death_timer
            self.fade_alpha = min(255, int(elapsed_death * 0.1))

            self.player.update_death(dt)
            
            if elapsed_death >= 4500:
                self.state = "GAME_OVER"
                self.game_over_timer = pygame.time.get_ticks()
                
                try:
                    pygame.mixer.music.load("assets/audio/music/Snake_is_dead.mp3")
                    pygame.mixer.music.play()
                except Exception as e:
                    print(f"No se pudo cargar la música Snake_is_dead.mp3: {e}")
            return

        if self.state == "GAME_OVER" or self.state == "VICTORY":
            return

        walls = self.walls

        self.player.update(
            dt,
            walls,
            self.top_barriers,
            self.hidden_zones,
            self.hidden_zones_top,
            self.hidden_zones_bottom,
        )

        inventario_previo = list(self.player.inventory)
        if hasattr(self.player, 'collect_items'):
            self.player.collect_items(self.items_group)
        for nombre_item in self.player.inventory:
            if nombre_item not in inventario_previo:
                self.item_message.show(nombre_item, self.pause_menu.sfx_volume)

        self.check_map_transitions()

        for enemy in self.enemies_group:
            enemy.update(dt, walls, self.player, self.pathfinding_grid, self.enemy_bullets)

        # Golpe: mientras dura, daña al primer enemigo que tenga delante (una vez por golpe).
        if self.player.is_punching and not self.player.punch_hit_done:
            punch_rect = self.player.get_punch_rect()
            for enemy in self.enemies_group:
                if punch_rect.colliderect(enemy.rect.inflate(PUNCH_HIT_PADDING, PUNCH_HIT_PADDING)):
                    enemy.take_damage(PUNCH_DAMAGE, PUNCH_STUN_TIME, self.player.rect.center)
                    self.player.punch_hit_done = True
                    break

        # Balas: se mueven y chocan contra paredes, enemigos o el borde del mapa.
        if self.map:
            bounds = pygame.Rect(0, 0, self.map.width, self.map.height)
        else:
            bounds = self.map_image.get_rect()
        self.bullets_group.update(dt, walls, self.enemies_group, bounds)

        self.enemy_bullets.update(dt)

        hits = pygame.sprite.spritecollide(self.player, self.enemy_bullets, True)
        for hit in hits:
            self.player.health -= 20
            if self.player.health <= 0 and not getattr(self.player, "is_dead", False):
                self.trigger_death_sequence()
                
        self.camera.update(self.player)

        if self.state == "PLAYING":
            # Si el jugador se queda sin vida
            if getattr(self.player, "is_dead", False):
                if getattr(self.player, "death_finished", False):
                    self.state = "GAME_OVER"
                return
            
        if self.player.health <= 0:
            self.trigger_death_sequence()
            return

    def draw(self, surface):
        self.virtual_surface.fill((0, 0, 0))
        
        if self.state == "VICTORY":
            surface.fill((42, 20, 15)) 
            
            w = surface.get_width()
            h = surface.get_height()
            
            bar_height = int(h * 0.22)  
            
            color_center = (42, 20, 15)
            color_edge = (15, 7, 5)     
            gradient_size = 25          
            
            top_surface = pygame.Surface((w, bar_height))
            top_surface.fill(color_edge)
            for y in range(bar_height - gradient_size, bar_height):
                if y >= 0:
                    factor = (y - (bar_height - gradient_size)) / gradient_size
                    r = int(color_edge[0] * (1 - factor) + color_center[0] * factor)
                    g = int(color_edge[1] * (1 - factor) + color_center[1] * factor)
                    b = int(color_edge[2] * (1 - factor) + color_center[2] * factor)
                    pygame.draw.line(top_surface, (r, g, b), (0, y), (w, y))
            
            bottom_surface = pygame.Surface((w, bar_height))
            bottom_surface.fill(color_edge)
            for y in range(gradient_size):
                if y < bar_height:
                    factor = 1.0 - (y / gradient_size)
                    r = int(color_edge[0] * (1 - factor) + color_center[0] * factor)
                    g = int(color_edge[1] * (1 - factor) + color_center[1] * factor)
                    b = int(color_edge[2] * (1 - factor) + color_center[2] * factor)
                    pygame.draw.line(bottom_surface, (r, g, b), (0, y), (w, y))
            
            surface.blit(top_surface, (0, 0))
            surface.blit(bottom_surface, (0, h - bar_height))
            
            font_large = pygame.font.Font("assets/fonts/PixelOperator8-Bold.ttf", 28)
            font_small = pygame.font.Font("assets/fonts/PixelOperator8.ttf", 14)
            font_medium = pygame.font.Font("assets/fonts/PixelOperator8-bold.ttf", 14)
            
            current_time = pygame.time.get_ticks()
            elapsed = current_time - self.victory_timer
            
            target_text = "MISION COMPLETADA"
            chars_to_show = min(len(target_text), int(elapsed / 80))
            text_to_render = target_text[:chars_to_show]
            
            text_surface = font_large.render(text_to_render, True, (50, 225, 100))
            text_rect = text_surface.get_rect(center=(w // 2, h // 2))
            surface.blit(text_surface, text_rect)

            prompt_delay = 1500
            if elapsed > prompt_delay:
                has_next = self.has_next_mission()
                max_options = 3 if has_next else 2

                if self.victory_selected_option >= max_options:
                    self.victory_selected_option = max_options - 1

                center_y = h - (bar_height // 2)

                if has_next:
                    c_retry = (255, 255, 0) if self.victory_selected_option == 0 else (120, 120, 120)
                    c_next  = (255, 255, 0) if self.victory_selected_option == 1 else (120, 120, 120)
                    c_exit  = (255, 255, 0) if self.victory_selected_option == 2 else (120, 120, 120)
                    
                    t_retry = "> REINTENTAR <" if self.victory_selected_option == 0 else "  REINTENTAR  "
                    t_next  = "> SIGUIENTE <" if self.victory_selected_option == 1 else "  SIGUIENTE  "
                    t_exit  = "> SALIR <" if self.victory_selected_option == 2 else "  SALIR  "
                    
                    s_retry = font_medium.render(t_retry, True, c_retry) if self.victory_selected_option == 0 else font_small.render(t_retry, True, c_retry)
                    s_next  = font_medium.render(t_next, True, c_next) if self.victory_selected_option == 1 else font_small.render(t_next, True, c_next)
                    s_exit  = font_medium.render(t_exit, True, c_exit) if self.victory_selected_option == 2 else font_small.render(t_exit, True, c_exit)
                    
                    self.vic_retry_rect = s_retry.get_rect(center=(w // 2 - 200, center_y))
                    self.vic_next_rect  = s_next.get_rect(center=(w // 2, center_y))
                    self.vic_exit_rect  = s_exit.get_rect(center=(w // 2 + 190, center_y))
                    
                    surface.blit(s_retry, self.vic_retry_rect)
                    surface.blit(s_next, self.vic_next_rect)
                    surface.blit(s_exit, self.vic_exit_rect)
                else:
                    c_retry = (255, 255, 0) if self.victory_selected_option == 0 else (120, 120, 120)
                    c_exit  = (255, 255, 0) if self.victory_selected_option == 1 else (120, 120, 120)
                    
                    t_retry = "> REINTENTAR <" if self.victory_selected_option == 0 else "  REINTENTAR  "
                    t_exit  = "> SALIR <" if self.victory_selected_option == 1 else "  SALIR  "
                    
                    s_retry = font_medium.render(t_retry, True, c_retry) if self.victory_selected_option == 0 else font_small.render(t_retry, True, c_retry)
                    s_exit  = font_medium.render(t_exit, True, c_exit) if self.victory_selected_option == 1 else font_small.render(t_exit, True, c_exit)
                    
                    self.vic_retry_rect = s_retry.get_rect(center=(w // 2 - 120, center_y))
                    self.vic_exit_rect  = s_exit.get_rect(center=(w // 2 + 120, center_y))
                    
                    if hasattr(self, "vic_next_rect"):
                        delattr(self, "vic_next_rect")
                    
                    surface.blit(s_retry, self.vic_retry_rect)
                    surface.blit(s_exit, self.vic_exit_rect)

            fade_duration = 1000  
            if elapsed < fade_duration:
                fade_alpha = int(255 * (1 - (elapsed / fade_duration)))
                fade_surface = pygame.Surface((w, h))
                fade_surface.fill((0, 0, 0))
                fade_surface.set_alpha(fade_alpha)
                surface.blit(fade_surface, (0, 0))
            return

        if self.state == "GAME_OVER":
            surface.fill((42, 20, 15)) 
            
            w = surface.get_width()
            h = surface.get_height()
            
            bar_height = int(h * 0.22)  
            
            color_center = (42, 20, 15)
            color_edge = (15, 7, 5)     
            gradient_size = 75          
            
            top_surface = pygame.Surface((w, bar_height))
            top_surface.fill(color_edge)
            for y in range(bar_height - gradient_size, bar_height):
                if y >= 0:
                    factor = (y - (bar_height - gradient_size)) / gradient_size
                    r = int(color_edge[0] * (1 - factor) + color_center[0] * factor)
                    g = int(color_edge[1] * (1 - factor) + color_center[1] * factor)
                    b = int(color_edge[2] * (1 - factor) + color_center[2] * factor)
                    pygame.draw.line(top_surface, (r, g, b), (0, y), (w, y))
            
            bottom_surface = pygame.Surface((w, bar_height))
            bottom_surface.fill(color_edge)
            for y in range(gradient_size):
                if y < bar_height:
                    factor = 1.0 - (y / gradient_size)
                    r = int(color_edge[0] * (1 - factor) + color_center[0] * factor)
                    g = int(color_edge[1] * (1 - factor) + color_center[1] * factor)
                    b = int(color_edge[2] * (1 - factor) + color_center[2] * factor)
                    pygame.draw.line(bottom_surface, (r, g, b), (0, y), (w, y))
            
            surface.blit(top_surface, (0, 0))
            surface.blit(bottom_surface, (0, h - bar_height))
            
            font_large = pygame.font.Font("assets/fonts/PixelOperator8-Bold.ttf", 28)
            font_small = pygame.font.Font("assets/fonts/PixelOperator8.ttf", 16)
            font_medium = pygame.font.Font("assets/fonts/PixelOperator8-bold.ttf", 16)
            
            current_time = pygame.time.get_ticks()
            elapsed = current_time - self.game_over_timer
            
            paradox_delay = 12500 
            
            if elapsed < paradox_delay:
                target_text = "S N A K E  I S  D E A D"
                chars_to_show = min(len(target_text), int(elapsed / 80))
            else:
                target_text = "T I M E  P A R A D O X"
                time_since_paradox = elapsed - paradox_delay
                chars_to_show = min(len(target_text), int(time_since_paradox / 80))
                
            text_to_render = target_text[:chars_to_show]
            text_surface = font_large.render(text_to_render, True, (190, 190, 160))
            text_rect = text_surface.get_rect(center=(w // 2, h // 2))
            surface.blit(text_surface, text_rect)

            prompt_delay = 2000
            if elapsed > prompt_delay:
                color_retry = (255, 255, 0) if self.game_over_selected_option == 0 else (120, 120, 120)
                color_exit = (255, 255, 0) if self.game_over_selected_option == 1 else (120, 120, 120)
                
                text_retry_str = "> REINTENTAR <" if self.game_over_selected_option == 0 else "  REINTENTAR  "
                text_exit_str = "> SALIR <" if self.game_over_selected_option == 1 else "  SALIR  "
                
                retry_surface = font_medium.render(text_retry_str, True, color_retry) if self.game_over_selected_option == 0 else font_small.render(text_retry_str, True, color_retry)
                exit_surface = font_medium.render(text_exit_str, True, color_exit) if self.game_over_selected_option == 1 else font_small.render(text_exit_str, True, color_exit)
                
                center_y = h - (bar_height // 2)
                
                self.retry_rect = retry_surface.get_rect(center=(w // 2 - 120, center_y))
                self.exit_rect = exit_surface.get_rect(center=(w // 2 + 120, center_y))
                
                surface.blit(retry_surface, self.retry_rect)
                surface.blit(exit_surface, self.exit_rect)

            fade_duration = 1000  
            if elapsed < fade_duration:
                fade_alpha = int(255 * (1 - (elapsed / fade_duration)))
                fade_surface = pygame.Surface((w, h))
                fade_surface.fill((0, 0, 0))
                fade_surface.set_alpha(fade_alpha)
                surface.blit(fade_surface, (0, 0))
            return

        # --- RENDERIZADO NORMAL DEL JUEGO (PLAYING / DYING) ---
        if self.map:
            self.map.render_below(self.virtual_surface, self.camera)
        else:
            self.virtual_surface.blit(self.map_image, self.camera.camera_rect.topleft) 

        for item in self.items_group:
            item_rect = self.camera.apply(item)
            self.virtual_surface.blit(item.image, item_rect)

        for bullet in self.enemy_bullets:
            bullet.draw_with_camera(self.virtual_surface, self.camera)
        
        entities_to_draw = [self.player] + list(self.enemies_group)
        entities_to_draw.sort(key=lambda entity: entity.rect.bottom)

        for entity in entities_to_draw:
            entity.draw_with_camera(self.virtual_surface, self.camera)

        for bullet in self.bullets_group:
            bullet.draw_with_camera(self.virtual_surface, self.camera)

        for enemy in self.enemies_group:
            enemy.draw_vision(self.virtual_surface, self.camera)
        
        if self.map:
            self.map.render_roofs(
                self.virtual_surface,
                self.camera,
                render_condition=self.player.is_hidden or self.player.is_near_hidden_zone(margin=15),
            )

        if self.state == "DYING" or self.fading_in:
            fade_surface = pygame.Surface((self.virtual_surface.get_width(), self.virtual_surface.get_height()))
            fade_surface.fill((0, 0, 0))
            fade_surface.set_alpha(self.fade_alpha)
            self.virtual_surface.blit(fade_surface, (0, 0))

        scaled_surface = pygame.transform.scale(self.virtual_surface, (surface.get_width(), surface.get_height()))
        surface.blit(scaled_surface, (0, 0))

        self.health_bar.draw(surface, self.player)
        self.item_message.draw(surface)

        # INVENTARIO ENCIMA DE TODO SI ESTÁ ABIERTO
        if self.inventory_open:
            self.inventory_menu.draw(surface, self.player, self.health_bar)

        # RENDERIZAR PAUSA ENCIMA DE TODO SI ESTÁ ACTIVA
        if self.is_paused:
            self.pause_menu.draw(surface)

        if self.pathfinding_grid:
            for enemy in self.enemies_group:
                enemy.draw_regions_debug(self.virtual_surface, self.camera, self.pathfinding_grid)
                break