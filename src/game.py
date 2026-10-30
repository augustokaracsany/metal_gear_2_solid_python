import os
import pygame
import sys
import math
from src.enemy import Enemy
from src.player import Player
from src.camera import Camera
from src.tilemap import TiledMap  # Mapas TMX
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from src.items import Item  
from src.hud import HealthBar
from src.codec import CodecManager
from src.settings import ENEMY_CONTACT_DAMAGE
from src.pause import PauseMenu
from src.settings import PUNCH_DAMAGE, PUNCH_HIT_PADDING, PUNCH_STUN_TIME
from src.inventory import InventoryMenu
from src.item_message import ItemMessage
from src.hud_inventory import HUDInventory  # <--- HUD de inventario equipado activo

class Game:
    ALERT_MAX = 99
    ALERT_DECAY_TIME = 15.0    # en segundos
    FOUND_SFX_PATH = "assets/audio/sfx/found.mp3"
    CHASE_MUSIC_PATH = "assets/audio/music/encounter.mp3"
    ALERT_FONT_PATH = "assets/fonts/PixelOperator8-Bold.ttf"
    ALERTED_STATES = ("ALERT", "CHASE")
    NOISE_PUNCH_RADIUS = 250   # px
    ALLY_CALL_RADIUS = 320     # px: a quién avisa el guardia que te ve
    PUNCH_REACH = 14           # px por delante del jugador
    RADAR_W = 140
    RADAR_H = 100
    RADAR_SCALE = 0.1       # 1 px del radar = 10 px del mapa
    RADAR_MARGIN = 20
    EXIT_FADE_MS = 700
    def __init__(self, mission_number=1):
        self.mission_number = mission_number
        self.pending_action = None   # ("restart", n) o ("menu", None)
        self.exit_fade_start = 0
        self.exit_fade_volume = 1.0
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
        self.game_over_selected_option = 0
        self.return_to_menu = False

        # --- SISTEMA DE PAUSA ---
        self.is_paused = False
        self.pause_menu = PauseMenu(SCREEN_WIDTH, SCREEN_HEIGHT)

        # --- INVENTARIO COMPLETO (MENÚ) ---
        self.inventory_open = False
        self.inventory_menu = InventoryMenu(SCREEN_WIDTH, SCREEN_HEIGHT)

        # --- HUD EQUIPAMIENTO ACTIVO (PANTALLA PRINCIPAL) ---
        # Puedes cambiar la posición a: 'bottom-right', 'bottom-left', 'top-right' o 'top-left'
        self.hud_inventory = HUDInventory(position="bottom-right")

        # --- CODEC ---

        self.codec_manager = CodecManager()

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

        # Estado guardado de cada mapa visitado (guardias muertos y posiciones de los vivos).
        self.map_states = {}
        self.current_map_key = None
        self.current_route_count = 0
        self.codec_zones = []

        self.alert_level = 0.0
        self.chase_music_active = False   # True si la música de persecución tomó el control
        self.music_delay = None           # segundos hasta que arranque la música tras el SFX
        try:
            self.found_sfx = pygame.mixer.Sound(self.FOUND_SFX_PATH)
        except Exception as e:
            print(f"Aviso SFX de alerta: {e}")
            self.found_sfx = None
        try:
            self.alert_font = pygame.font.Font(self.ALERT_FONT_PATH, 16)
        except Exception as e:
            print(f"Aviso fuente de alerta: {e}")
            self.alert_font = pygame.font.Font(None, 24)

        self._was_punching = False

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

        self.fading_in = True
        self.fade_alpha = 255
        self.fade_in_timer = pygame.time.get_ticks()

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

    def _save_map_state(self):
        """Guarda qué guardias siguen vivos en el mapa actual y dónde estaban."""
        key = self.current_map_key
        if key is None or not self.map:
            return

        snapshots = {}
        for enemy in self.enemies_group:
            i = getattr(enemy, "route_index", None)
            if i is None:
                continue
            snapshots[i] = {
                "x": enemy.x,
                "y": enemy.y,
                "facing": enemy.facing,
                "target_index": enemy.current_target_index,
                "health": enemy.health,
                "state": enemy.state,
            }

        # Los que no están vivos ahora, están muertos y no tienen que reaparecer.
        dead = set(range(self.current_route_count)) - set(snapshots.keys())
        self.map_states[key] = {"dead": dead, "snapshots": snapshots}

    def load_level(self, tmx_or_key):

        # Antes de dejar el mapa actual, guardamos cómo quedó.
        self._save_map_state()

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

        self.current_map_key = tmx_path
        self.enemies_group.empty()
        self.items_group.empty()
        self.enemy_bullets.empty()
        self._reset_alert()

        # Actualizar zonas ocultas y barreras de forma segura
        if self.map:
            self.hidden_zones = self.map.get_hidden_zones("zonas_oculto") or []
            self.hidden_zones_top = self.map.get_hidden_zones_top() or []
            self.hidden_zones_bottom = self.map.get_hidden_zones_bottom() or []
            self.top_barriers = self.map.get_top_barriers("limites_top") or []
            self.walls = self.map.get_collision_rects()   # cacheadas una sola vez
            self.codec_zones = self.map.load_codec_zones()

            self._build_radar_map()

            patrol_routes = self.map.get_patrol_path("enemy_patrols")
            self.current_route_count = len(patrol_routes)

            # Si ya visitaste este mapa: guardias muertos y posiciones de los vivos.
            saved = self.map_states.get(tmx_path, {"dead": set(), "snapshots": {}})

            for i, ruta in enumerate(patrol_routes):
                if i in saved["dead"]:
                    continue   # Este guardia ya murió: no reaparece.

                snap = saved["snapshots"].get(i)
                if snap:
                    # Vuelve exactamente donde estaba cuando saliste del mapa.
                    guardia = Enemy(snap["x"], snap["y"], ruta, start_delay=0.0)
                    guardia.facing = snap["facing"]
                    guardia.current_target_index = snap["target_index"]
                    guardia.health = snap["health"]
                    if snap["state"] not in ("WALKING", "LOOKING") and hasattr(guardia, "_set_state"):
                        guardia._set_state("RETURN")   # Si estaba persiguiendo, vuelve a su patrulla.
                else:
                    guardia = Enemy(ruta[0][0], ruta[0][1], ruta, start_delay=i * 1.0)

                guardia.route_index = i
                self.enemies_group.add(guardia)

            for g in self.enemies_group:
                g.others = list(self.enemies_group)

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

            # Municiones (ductos). Se agrega aparte, igual que la caja, la ración y la pistola.
            if hasattr(self.map.tmx_data, 'objects'):
                for obj in self.map.tmx_data.objects:
                    if obj.name == "ammo" and (not hasattr(self, 'player') or "ammo" not in self.player.inventory):
                        scale = self.map.scale
                        try:
                            ammo_item = Item("ammo", 0, 0, "assets/sprites/items/municiones.png", scale=1.5)
                            ammo_item.rect.center = (int((obj.x + obj.width / 2) * scale), int((obj.y + obj.height / 2) * scale))
                            self.items_group.add(ammo_item)
                        except Exception as e:
                            print(f"Error cargando sprite de las municiones: {e}")

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
            self.radar_map = None
            self.codec_zones = None

    def check_map_transitions(self):
        if not self.map:
            return

        triggers = self.map.get_triggers()
        for trigger in triggers:
            if self.player.rect.colliderect(trigger["rect"]):
                props = trigger["properties"]
                target_map = props.get("target_map")
                self.load_level(target_map)

                # Propiedad opcional "mission": el trigger cambia el número de misión actual.
                if "mission" in props:
                    self.mission_number = int(props["mission"])

                scale = self.map.scale if self.map else 2
                spawn_x = float(props.get("spawn_x", 180)) * scale
                spawn_y = float(props.get("spawn_y", 550)) * scale
                self.player.x = spawn_x
                self.player.y = spawn_y
                self.player.rect.x = int(spawn_x)
                self.player.rect.y = int(spawn_y)

                # Propiedad opcional "prone": True = llega cuerpo a tierra, False = de pie.
                if "prone" in props:
                    self.player.set_stance("CRAWL" if props["prone"] else "STAND")
                
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

        self._reset_alert()
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

    def _update_alert(self, dt):
        detected = any(e.sees_player for e in self.enemies_group)
        hunting = any(e.state in self.ALERTED_STATES for e in self.enemies_group)

        if detected:
            if self.alert_level <= 0:
                self._on_alert_start()
                self._call_allies()
            self.alert_level = self.ALERT_MAX
        elif self.alert_level > 0 and not hunting:
            # Solo baja cuando TODOS los conos están en verde
            decay = self.ALERT_MAX / self.ALERT_DECAY_TIME
            self.alert_level = max(0.0, self.alert_level - decay * dt)
            if self.alert_level <= 0:
                self._on_alert_end()

        # La música arranca cuando termina el sonido de alerta.
        if self.music_delay is not None:
            self.music_delay = 0
            if self.music_delay <= 0:
                self.music_delay = None
                self._start_chase_music()

    def _on_alert_start(self):
        self.chase_music_active = True
        pygame.mixer.music.stop()   # corta la música del nivel para que se oiga el SFX
        if self.found_sfx:
            self.found_sfx.play()
            self.music_delay = self.found_sfx.get_length()
        else:
            self.music_delay = 0.0

    def _start_chase_music(self):
        try:
            pygame.mixer.music.load(self.CHASE_MUSIC_PATH)
            pygame.mixer.music.play(-1)
        except Exception as e:
            print(f"Aviso música de persecución: {e}")

    def _on_alert_end(self):
        self.music_delay = None
        if self.chase_music_active:
            pygame.mixer.music.fadeout(1500)
            self.chase_music_active = False

    def _reset_alert(self):
        """Apaga todo de golpe (cambio de nivel, muerte)."""
        if self.chase_music_active:
            pygame.mixer.music.stop()
        if getattr(self, "found_sfx", None):
            self.found_sfx.stop()
        self.alert_level = 0.0
        self.music_delay = None
        self.chase_music_active = False

    def _draw_alert(self, surface):
        if self.alert_level <= 0:
            return
        value = math.ceil(self.alert_level)
        color = (255, 40, 40) if self.alert_level >= self.ALERT_MAX else (255, 200, 0)
        text = f"ALERTA {value}"
        shadow = self.alert_font.render(text, True, (0, 0, 0))
        label = self.alert_font.render(text, True, color)
        rect = label.get_rect(midtop=(surface.get_width() // 2, 20))
        surface.blit(shadow, rect.move(2, 2))
        surface.blit(label, rect)
        
    def restart_mission(self):
        """Reinicia la misión completa: mapa, enemigos, ítems y estado de Snake."""
        p = self.player
        p.inventory = []
        p.equipped_item = None      # si no, el HUD sigue mostrando lo que tenía equipado
        p.equipped_weapon = None
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

        self.map_states = {}

        self.load_level(self.mission_number)

        if self.map:
            map_width, map_height = self.map.width, self.map.height
        else:
            map_width, map_height = self.map_image.get_width(), self.map_image.get_height()
        self.camera = Camera(map_width, map_height, self.virtual_width, self.virtual_height)

        spawn_x, spawn_y = self.map.get_spawn_point("player_spawn", (400, 350)) if self.map else (400, 350)
        p.x, p.y = float(spawn_x), float(spawn_y)
        p.rect.x, p.rect.y = int(spawn_x), int(spawn_y)
        self.camera.update(p)

    def handle_events(self, events):
        for event in events:
            if self.pending_action:
                continue
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

            if self.state == "RADIO_MENU":
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        self.execute_radio_call()
                    elif event.key in (pygame.K_ESCAPE, pygame.K_TAB):
                        self.state = "PLAYING"
                continue

            if self.state == "CODEC":
                self.codec_manager.handle_input([event])
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

            # Abrir la pausa con ESC (cerrar / volver lo maneja el propio menú de pausa)
            if (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                    and not self.is_paused and self.state == "PLAYING"):
                self.cleanup()
                self.is_paused = True
                continue

            # Si el juego está en pausa, la navegación y selección las procesa la pausa
            if self.is_paused:
                action = self.pause_menu.handle_input(event)
                if action == "CONTINUAR":
                    self.is_paused = False
                elif action == "PUNTO DE CONTROL":
                    self.pause_menu.trigger_feedback("No se encontró ningún punto de guardado previo.")
                elif action == "REINICIAR MISIÓN":
                    self.restart_mission()
                    self.is_paused = False
                elif action == "VOLVER AL MENÚ":
                    self.is_paused = False
                    pygame.mixer.music.stop()  # corta la música de la misión al volver al menú principal
                    return "GOTO_MENU"
            else:
                # Si el juego NO está en pausa, responde a las acciones del jugador
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_k:  # Tecla de prueba de muerte
                        self.cleanup()
                        self.trigger_death_sequence()
                    elif event.key == pygame.K_v:
                        self.cleanup()
                        self.trigger_victory_sequence()
                    elif event.key == pygame.K_h:
                        self.player.take_damage(10)
                    elif event.key == pygame.K_j:
                        self.player.heal(10)
                    elif event.key == pygame.K_SPACE:
                        self.player_shoot()
                    elif event.key == pygame.K_TAB:
                        self.state = "RADIO_MENU"
                self.player.punch_self_event(event)
        return None

    def trigger_contextual_codec(self):
        # 1. Buscamos por defecto la llamada "default"
        chosen_call_id = "default"
        
        # 2. Comprobamos si el rect del jugador colisiona con alguna zona de Tiled
        for zone in self.codec_zones:
            if self.player.rect.colliderect(zone["rect"]):
                chosen_call_id = zone["call_id"]
                break # Encontró una zona, nos quedamos con su ID
                
        # 3. Cambiamos al estado de Códec y le pasamos el ID correspondiente
        self.state = "CODEC"
        self.codec_manager.start_call(chosen_call_id)

    def execute_radio_call(self):
        # Por defecto, si no está en ninguna zona especial, llamamos al "default"
        target_call_id = "default"
        
        # Comprobamos si el rect del jugador colisiona con alguna zona de Tiled
        for zone in self.codec_zones:
            if self.player.rect.colliderect(zone["rect"]):
                target_call_id = zone["call_id"]
                break # Encontró la zona, nos quedamos con ese ID y salimos del bucle
                
        # Cambiamos el estado del juego a CODEC
        self.state = "CODEC"
        
        # Llamamos a tu método que ya tienes hecho pasándole el ID correspondiente
        self.codec_manager.start_call(target_call_id)

    def player_shoot(self):
        if self.state != "PLAYING":
            return
        bullet = self.player.shoot()
        print("DISPARO:", "OK" if bullet else "bloqueado", "| postura:", self.player.stance)
        if bullet:
            self.bullets_group.add(bullet)

    def _begin_exit_fade(self, action, mission=None):
        if self.pending_action:
            return
        self.pending_action = (action, mission)
        self.exit_fade_start = pygame.time.get_ticks()
        self.exit_fade_volume = pygame.mixer.music.get_volume()

    def confirm_victory_option(self):
        has_next = self.has_next_mission()
        if self.victory_selected_option == 0:
            self._begin_exit_fade("restart", self.mission_number)
        elif self.victory_selected_option == 1 and has_next:
            self._begin_exit_fade("restart", self.mission_number + 1)
        else:
            self._begin_exit_fade("menu")

    def confirm_game_over_option(self):
        if self.game_over_selected_option == 0:
            self._begin_exit_fade("restart", self.mission_number)
        else:
            self._begin_exit_fade("menu")

    def _update_exit_fade(self):
        t = (pygame.time.get_ticks() - self.exit_fade_start) / self.EXIT_FADE_MS
        pygame.mixer.music.set_volume(self.exit_fade_volume * max(0.0, 1 - t))
        if t < 1:
            return
        action, mission = self.pending_action
        pygame.mixer.music.stop()
        pygame.mixer.music.set_volume(self.pause_menu.music_volume)
        if action == "restart":
            self.__init__(mission)     # __init__ pone pending_action = None
        else:
            self.pending_action = None
            self.return_to_menu = True

    def update(self, dt, surface):
        if self.pending_action:
            self._update_exit_fade()
            return
        if self.fading_in:
            elapsed_fade = pygame.time.get_ticks() - self.fade_in_timer
            self.fade_alpha = max(0, 255 - int((elapsed_fade / 1000.0) * 255))
            if self.fade_alpha == 0:
                self.fading_in = False

        if self.is_paused or self.inventory_open or self.state == "RADIO_MENU":
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

        if self.state == "CODEC":
            self.codec_manager.update(dt)
            if self.codec_manager.finished:
                self.state = "PLAYING"
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

        self._check_punch_noise()

        self.check_map_transitions()

        alerted = self.alert_level > 0
        for enemy in self.enemies_group:
            enemy.global_alert = alerted
            enemy.update(dt, walls, self.player, self.pathfinding_grid, self.enemy_bullets)

        self._update_alert(dt)

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

    def emit_noise(self, pos, radius):
        for e in self.enemies_group:
            e.hear_noise(pos, radius, self.pathfinding_grid)

    def _check_punch_noise(self):
        """Ruido solo en el primer frame del golpe, y solo si pega contra un sólido."""
        p = self.player
        if p.is_punching and not self._was_punching:
            r, d = p.rect, self.PUNCH_REACH
            probe = {
                "UP": r.move(0, -d), "DOWN": r.move(0, d),
                "LEFT": r.move(-d, 0), "RIGHT": r.move(d, 0),
            }[p.facing]
            if probe.collidelist(self.walls) != -1:
                self.emit_noise(p.rect.center, self.NOISE_PUNCH_RADIUS)
        self._was_punching = p.is_punching

    def _call_allies(self):
        """El guardia que te ve avisa a los cercanos: van a donde te vieron."""
        for spotter in [e for e in self.enemies_group if e.sees_player]:
            for other in self.enemies_group:
                if other is not spotter:
                    other.hear_noise(self.player.rect.center, self.ALLY_CALL_RADIUS,
                                    self.pathfinding_grid, origin=spotter.rect.center,
                                    gesture=False)

    def _build_radar_map(self):
        s = self.RADAR_SCALE
        self.radar_map = pygame.Surface((max(1, int(self.map.width * s)),
                                         max(1, int(self.map.height * s))))
        self.radar_map.fill((0, 25, 0))
        for r in self.walls:
            pygame.draw.rect(self.radar_map, (0, 150, 0),
                             (int(r.x * s), int(r.y * s),
                              max(1, int(r.w * s)), max(1, int(r.h * s))))

    def cleanup(self):
        """Llamar siempre que se abandone el nivel (ESC, menú, salir)."""
        self._reset_alert()
        pygame.mixer.music.stop()   # por si quedó sonando algo del nivel

    def _draw_radar(self, surface):
        if not getattr(self, "radar_map", None):
            return
        s = self.RADAR_SCALE
        mw, mh = self.radar_map.get_size()

        # Si el mapa es más chico que el radar, el radar se achica a su tamaño.
        W = min(self.RADAR_W, mw)
        H = min(self.RADAR_H, mh)

        # Esquina superior izquierda de la ventana, limitada a los bordes del mapa.
        px, py = self.player.rect.center
        vx = max(0, min(int(px * s) - W // 2, mw - W))
        vy = max(0, min(int(py * s) - H // 2, mh - H))

        radar = pygame.Surface((W, H))
        radar.blit(self.radar_map, (-vx, -vy))

        # Conos de visión (misma geometría que Enemy.draw_vision), con transparencia.
        cones = pygame.Surface((W, H), pygame.SRCALPHA)
        for e in self.enemies_group:
            dir_x, dir_y = e.DIRS[e._vision_facing()]
            perp_x, perp_y = -dir_y, dir_x
            sx, sy = e.rect.center
            rng, w = e.VISION_RANGE, e.CONE_TAN
            world_pts = [
                (sx, sy),
                (sx + (dir_x - perp_x * w) * rng, sy + (dir_y - perp_y * w) * rng),
                (sx + (dir_x + perp_x * w) * rng, sy + (dir_y + perp_y * w) * rng),
            ]
            pts = [(x * s - vx, y * s - vy) for x, y in world_pts]
            color = (255, 0, 0, 90) if e.state in self.ALERTED_STATES else (0, 255, 0, 90)
            pygame.draw.polygon(cones, color, pts)
        radar.blit(cones, (0, 0))

        # Guardias
        for e in self.enemies_group:
            ex, ey = e.rect.center
            x, y = int(ex * s) - vx, int(ey * s) - vy
            if 0 <= x < W and 0 <= y < H:
                color = (255, 40, 40) if e.state in self.ALERTED_STATES else (255, 200, 0)
                pygame.draw.rect(radar, color, (x - 1, y - 1, 3, 3))

        # Jugador
        x, y = int(px * s) - vx, int(py * s) - vy
        pygame.draw.rect(radar, (255, 255, 255), (x - 1, y - 1, 3, 3))

        pygame.draw.rect(radar, (0, 200, 0), radar.get_rect(), 1)
        surface.blit(radar, (surface.get_width() - W - self.RADAR_MARGIN, self.RADAR_MARGIN))

    def _draw_exit_fade(self, surface):
        if not self.pending_action:
            return
        t = min(1.0, (pygame.time.get_ticks() - self.exit_fade_start) / self.EXIT_FADE_MS)
        overlay = pygame.Surface(surface.get_size())
        overlay.set_alpha(int(255 * t))
        surface.blit(overlay, (0, 0))

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
            self._draw_exit_fade(surface)
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
            self._draw_exit_fade(surface)
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

        # for enemy in self.enemies_group:
        #     enemy.draw_vision(self.virtual_surface, self.camera)
        
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

        if self.state == "PLAYING":
            self.health_bar.draw(surface, self.player)
            self._draw_alert(surface)
            self._draw_radar(surface)
            self.item_message.draw(surface)

        # DIBUJAR HUD DE INVENTARIO SOBRE LA PANTALLA PRINCIPAL
        self.hud_inventory.draw(surface, self.player)

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

        if self.state == "RADIO_MENU":
            w, h = surface.get_width(), surface.get_height()
            
            # Fondo negro semitransparente
            overlay = pygame.Surface((w, h))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(180)
            surface.blit(overlay, (0, 0))

            font_large = pygame.font.Font("assets/fonts/PixelOperator8-Bold.ttf", 28)
            font_small = pygame.font.Font("assets/fonts/PixelOperator8.ttf", 16)
            font_medium = pygame.font.Font("assets/fonts/PixelOperator8-bold.ttf", 16)

            # Título "Codec" centrado arriba
            title_surf = font_large.render("CODEC", True, (32, 179, 84))
            title_rect = title_surf.get_rect(center=(w // 2, 80))
            surface.blit(title_surf, title_rect)

            # Opción de llamar al Cuartel General (resaltada)
            option_text = "> Cuartel General (CQ) <"
            opt_surf = font_medium.render(option_text, True, (38, 212, 99))
            opt_rect = opt_surf.get_rect(center=(w // 2, h // 2))
            surface.blit(opt_surf, opt_rect)

            # Instrucción abajo
            hint_surf = font_small.render("ENTER - Llamar | ESC - Salir", True, (180, 180, 180))
            hint_rect = hint_surf.get_rect(center=(w // 2, h - 80))
            surface.blit(hint_surf, hint_rect)

        elif self.state == "CODEC":
            self.codec_manager.draw(surface)