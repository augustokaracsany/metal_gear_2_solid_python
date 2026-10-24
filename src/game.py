import os
import pygame
import sys
import pytmx
from src.enemy import Enemy
from src.player import Player
from src.camera import Camera
from src.tilemap import TiledMap  # Mapas TMX
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from src.items import Item  
from src.hud import HealthBar
from src.settings import ENEMY_CONTACT_DAMAGE
from src.pause import PauseMenu
import src.hind as hind_mod
from src.hind import (
    HindD, BossHealthBar, HIT_DAMAGE,
    CINE_START_DELAY, CINE_PAN_IN_TIME, CINE_PAN_OUT_TIME, CINE_CAM_OFFSET,
    MUSIC, MUSIC_MASTER, MUSIC_FADE_MS, AUDIO_DIR,
)

# Misión (clave de levels_data) donde pelea el jefe HIND-D.
BOSS_MISSION = 3


class _CamTarget:
    """Objeto con rect para que Camera.update() lo siga durante la cinemática."""
    def __init__(self):
        self.rect = pygame.Rect(0, 0, 1, 1)


class Game:
    def __init__(self, mission_number=1, skip_boss_intro=False):
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

        # Música de la misión del jefe ("level" | "cutscene" | "boss"); None = todavía ninguna.
        self._music_key = None

        # --- SISTEMA DE PAUSA ---
        self.is_paused = False
        self.pause_menu = PauseMenu(SCREEN_WIDTH, SCREEN_HEIGHT)
        
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
                "tmx": "assets/sprites/maps/hind-d_boss_fight-576x1344.tmx",
                "png": "assets/sprites/maps/hind-d_boss_fight-576x1344.png"
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
        
        spawn_x, spawn_y = self.get_player_spawn()
        self.player = Player(spawn_x, spawn_y)
        self.all_sprites.add(self.player)

        self.health_bar = HealthBar()

        # --- JEFE (HIND-D) ---
        self.skip_boss_intro = skip_boss_intro
        self.boss = None
        self.boss_mode = None      # None | "WAITING" | "CUTSCENE" | "FIGHT" | "DEFEATED"
        self.boss_bar = BossHealthBar()
        self.boss_trigger = None
        self.cine_phase = None     # "DELAY" | "PAN_IN" | "TAKEOFF" | "PAN_OUT"
        self.cine_timer = 0.0
        self.cine_from = (0, 0)
        self.cine_focus = (0, 0)
        self._cam_target = _CamTarget()
        if self.mission_number == BOSS_MISSION:
            self.setup_boss()

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

            # C. GRILLA DE PATHFINDING (después de crear los enemigos: usa el tamaño de su hitbox)
            if self.enemies_group:
                actor_size = self.enemies_group.sprites()[0].rect.size
                self.pathfinding_grid = self.map.create_pathfinding_grid(16, actor_size)
            else:
                self.pathfinding_grid = None

    # ===================== MAPA: objetos de Tiled =====================
    def find_objects(self, name):
        """Objetos de Tiled cuyo NOMBRE, CLASE o CAPA coincida con `name`."""
        found = []
        if not self.map:
            return found
        for layer in self.map.tmx_data.layers:
            if not isinstance(layer, pytmx.TiledObjectGroup):
                continue
            for obj in layer:
                if (layer.name == name
                        or getattr(obj, "name", None) == name
                        or getattr(obj, "type", None) == name
                        or getattr(obj, "class_", None) == name):
                    found.append(obj)
        return found

    def find_rect(self, name):
        objs = self.find_objects(name)
        if not objs:
            return None
        o, s = objs[0], self.map.scale
        return pygame.Rect(int(o.x * s), int(o.y * s), int(o.width * s), int(o.height * s))

    def find_point(self, name, center=False):
        objs = self.find_objects(name)
        if not objs:
            return None
        o, s = objs[0], self.map.scale
        if center and getattr(o, "width", 0):
            return ((o.x + o.width / 2) * s, (o.y + o.height / 2) * s)
        return (o.x * s, o.y * s)

    def get_player_spawn(self, default=(400, 350)):
        """player_spawn por capa, nombre o clase; si no aparece, cae al método viejo del TiledMap."""
        pt = self.find_point("player_spawn")
        if pt is not None:
            return pt
        if self.map:
            return self.map.get_spawn_point("player_spawn", default)
        return default

    # ===================== AUDIO / MÚSICA / PAUSA =====================
    def play_music(self, key):
        """Música de la misión del jefe: key = "level" | "cutscene" | "boss" (ver MUSIC en hind.py).
        Solo actúa en BOSS_MISSION y no reinicia la pista si ya es la que suena."""
        if self.mission_number != BOSS_MISSION or key == self._music_key:
            return
        self._music_key = key
        cfg = MUSIC.get(key)
        if not cfg or not cfg.get("file"):
            return                                  # Sin archivo: no toca lo que ya suena.
        path = os.path.join(AUDIO_DIR, cfg["file"])
        if not os.path.exists(path):
            print(f"Aviso: música '{key}' no encontrada: {path}")
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(max(0.0, min(1.0, cfg.get("volume", 1.0) * MUSIC_MASTER)))
            pygame.mixer.music.play(loops=-1 if cfg.get("loop", True) else 0, fade_ms=MUSIC_FADE_MS)
        except Exception as e:
            print(f"Aviso música '{key}': {e}")

    def stop_boss_audio(self):
        if self.boss:
            self.boss.stop_audio()

    def stop_all_audio(self):
        """Corta TODO el sonido del nivel (música + efectos + loops del jefe).
        Se usa al salir al menú, para que la música no se traslade."""
        self.stop_boss_audio()
        try:
            pygame.mixer.music.stop()
            pygame.mixer.stop()
        except pygame.error:
            pass
        self._music_key = None

    def set_paused(self, value):
        """Pausa/reanuda el juego y también los sonidos y la música."""
        self.is_paused = value
        try:
            if value:
                pygame.mixer.pause()
                pygame.mixer.music.pause()
            else:
                pygame.mixer.unpause()
                pygame.mixer.music.unpause()
        except pygame.error:
            pass

    # ===================== JEFE (HIND-D) =====================
    def setup_boss(self):
        """Crea el jefe según los objetos del mapa:
             boss_spawn        (punto, centro de la pista)  -> habilita la cinemática de despegue
             trigger_cutscene  (rectángulo, opcional)       -> la cinemática arranca al pisarlo
        Sin boss_spawn: el Hind entra desde lejos, sin cinemática.
        Con skip_boss_intro: directo a la pelea."""
        if self.map:
            w, h = self.map.width, self.map.height
        else:
            w, h = self.map_image.get_width(), self.map_image.get_height()

        pad = self.find_point("boss_spawn", center=True)
        self.boss_trigger = self.find_rect("trigger_cutscene")

        if self.skip_boss_intro or pad is None:
            self.boss = HindD(w, h, attacks_enabled=True)
            if self.skip_boss_intro:
                self.boss.skip_to_orbit()
            self.boss_mode = "FIGHT"
            self.play_music("boss")
            return

        self.boss = HindD(w, h, attacks_enabled=False, pad_pos=pad)
        if self.boss_trigger is None:
            self.begin_cutscene()
        else:
            self.boss_mode = "WAITING"      # El Hind espera en la pista hasta que Snake pise el trigger.
            self.play_music("level")        # Música del nivel, antes de la cinemática.

    def debug_start_boss(self):
        """F1: crea el jefe (si no existe) o dispara la cinemática ignorando el trigger."""
        if self.boss_mode == "WAITING":
            self.begin_cutscene()
        elif not self.boss:
            self.setup_boss()

    def begin_cutscene(self):
        self.boss_mode = "CUTSCENE"
        self.cine_phase = "DELAY"           # DELAY -> PAN_IN -> TAKEOFF -> PAN_OUT
        self.cine_timer = 0.0
        self.cine_from = self.player.rect.center
        self.cine_focus = (self.boss.x + CINE_CAM_OFFSET[0], self.boss.y + CINE_CAM_OFFSET[1])
        self.player.input_locked = True
        self.play_music("cutscene")

    def camera_target(self):
        """Durante la cinemática la cámara sigue un punto que va a la pista, se queda ahí
        mientras el Hind despega (así se ve cómo sale volando por arriba) y vuelve a Snake."""
        if self.boss_mode != "CUTSCENE" or self.cine_phase == "DELAY":
            return self.player
        fx, fy = self.cine_focus
        if self.cine_phase == "PAN_IN":
            t = min(1.0, self.cine_timer / max(0.01, CINE_PAN_IN_TIME))
            ax, ay = self.cine_from
            bx, by = fx, fy
        elif self.cine_phase == "TAKEOFF":
            t, ax, ay, bx, by = 1.0, fx, fy, fx, fy
        else:  # PAN_OUT
            t = min(1.0, self.cine_timer / max(0.01, CINE_PAN_OUT_TIME))
            ax, ay = fx, fy
            bx, by = self.player.rect.center
        s = t * t * (3 - 2 * t)
        self._cam_target.rect.center = (int(ax + (bx - ax) * s), int(ay + (by - ay) * s))
        return self._cam_target

    def update_boss(self, dt):
        if not self.boss:
            return
        self.boss.update(dt, self.player, self.hidden_zones)
        self.boss_bar.update(dt, self.boss.health / self.boss.max_health)

        if self.boss_mode == "WAITING":
            if self.boss_trigger and self.player.rect.colliderect(self.boss_trigger):
                self.begin_cutscene()

        elif self.boss_mode == "CUTSCENE":
            self.cine_timer += dt
            if self.cine_phase == "DELAY":
                if self.cine_timer >= CINE_START_DELAY:
                    self.cine_phase, self.cine_timer = "PAN_IN", 0.0
                    self.cine_from = self.player.rect.center
            elif self.cine_phase == "PAN_IN":
                if self.cine_timer >= CINE_PAN_IN_TIME:
                    self.cine_phase, self.cine_timer = "TAKEOFF", 0.0
                    self.boss.cutscene_go = True
            elif self.cine_phase == "TAKEOFF":
                if self.boss.takeoff_done:
                    self.cine_phase, self.cine_timer = "PAN_OUT", 0.0
            elif self.cine_phase == "PAN_OUT":
                if self.cine_timer >= CINE_PAN_OUT_TIME:
                    self.boss_mode = "FIGHT"
                    self.boss.attacks_enabled = True
                    self.player.input_locked = False
                    self.play_music("boss")

        elif self.boss_mode == "FIGHT":
            self.boss.consume_phase_change()   # acá va la ración del paso 3
            if self.boss.is_defeated:
                self.boss_mode = "DEFEATED"
                self.player.input_locked = True

        elif self.boss_mode == "DEFEATED":
            if self.boss.dead_done:
                self.player.input_locked = False
                self.boss_mode = None
                self.trigger_victory_sequence()   # mismo camino que ya tenés

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
            self.stop_boss_audio()
            self.state = "VICTORY"
            self.victory_timer = pygame.time.get_ticks()
            self.fade_alpha = 0
            try:
                pygame.mixer.music.load("assets/audio/music/mission_complete.mp3")
                pygame.mixer.music.play()
            except Exception as e:
                print(f"Aviso música de victoria: {e}")

    def trigger_death_sequence(self):
        if self.state == "PLAYING":
            self.stop_boss_audio()
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
        
    def restart_mission(self):
        """Reinicia la misión completa: mapa, enemigos, ítems, jefe (CON su cinemática de inicio),
        música y estado de Snake."""
        # 0) Cortar los sonidos y la música del intento anterior.
        self.stop_boss_audio()
        try:
            pygame.mixer.music.stop()
            pygame.mixer.stop()
        except pygame.error:
            pass

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
        p.input_locked = False
        p.health = p.max_health
        p.is_dead = False
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
        spawn_x, spawn_y = self.get_player_spawn()
        p.x, p.y = float(spawn_x), float(spawn_y)
        p.rect.x, p.rect.y = int(spawn_x), int(spawn_y)
        self.camera.update(p)

        # 5) Jefe de cero: vuelve a empezar TODO, cinemática incluida.
        self.boss = None
        self.boss_mode = None
        self.boss_trigger = None
        self.cine_phase = None
        self.cine_timer = 0.0
        self.cine_from = (0, 0)
        self.cine_focus = (0, 0)
        self.boss_bar = BossHealthBar()
        self._music_key = None              # Para que la música vuelva a arrancar.
        if self.mission_number == BOSS_MISSION:
            self.skip_boss_intro = False    # Cinemática de inicio otra vez.
            self.setup_boss()

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

            # Abrir Pausa con la tecla ESC (cerrar / volver lo maneja el propio menú de pausa)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and not self.is_paused:
                self.set_paused(True)
                continue

            # Si el juego está en pausa, la navegación y selección las procesa la pausa
            if self.is_paused:
                action = self.pause_menu.handle_input(event)
                if action == "CONTINUAR":
                    self.set_paused(False)
                elif action == "PUNTO DE CONTROL":
                    self.pause_menu.trigger_feedback("No se encontró ningún punto de guardado previo.")
                elif action == "REINICIAR MISIÓN":
                    self.restart_mission()
                    self.set_paused(False)
                elif action == "VOLVER AL MENÚ":
                    self.stop_all_audio()          # Música + efectos fuera: no se trasladan al menú.
                    self.set_paused(False)
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
                    elif event.key == pygame.K_F1:
                        self.debug_start_boss()
                    elif event.key == pygame.K_F2 and self.boss:
                        self.boss.take_hit(HIT_DAMAGE)          # respeta "un impacto por ventana"
                    # --- Debug del jefe (flags en hind.DEBUG) ---
                    elif event.key == pygame.K_F3:
                        hind_mod.DEBUG["strip_box"] = not hind_mod.DEBUG["strip_box"]
                    elif event.key == pygame.K_F4:
                        hind_mod.DEBUG["impact_hitbox"] = not hind_mod.DEBUG["impact_hitbox"]
                    elif event.key == pygame.K_F5:
                        hind_mod.DEBUG["hind_hitbox"] = not hind_mod.DEBUG["hind_hitbox"]
                    elif event.key == pygame.K_F6:
                        hind_mod.HIND_DEBUG = not hind_mod.HIND_DEBUG
                    elif event.key == pygame.K_F7:
                        on = not hind_mod.DEBUG["sprite_rect"]
                        hind_mod.DEBUG["sprite_rect"] = on
                        hind_mod.DEBUG["player_hitbox"] = on
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE) and self.boss_mode == "CUTSCENE":
                        self.boss.skip_takeoff()                # saltear cinemática
                        if self.cine_phase in ("DELAY", "PAN_IN"):
                            self.cine_phase = "TAKEOFF"
                self.player.punch_self_event(event)
        return None

    def confirm_victory_option(self):
        """Ejecuta la acción seleccionada en el menú de Victoria"""
        pygame.mixer.music.fadeout(1000)
        self.stop_boss_audio()
        has_next = self.has_next_mission()
        
        if self.victory_selected_option == 0:
            # Reintentar: la misión arranca de cero, con su cinemática de inicio.
            self.__init__(self.mission_number, skip_boss_intro=False)
        elif self.victory_selected_option == 1 and has_next:
            self.__init__(self.mission_number + 1)
        else:
            self.stop_all_audio()       # Salir: nada de música colgada en el menú.
            self.return_to_menu = True  # Activamos la bandera

    def confirm_game_over_option(self):
        pygame.mixer.music.fadeout(1000)
        self.stop_boss_audio()
        if self.game_over_selected_option == 0:
            # Reintentar: la misión arranca de cero, con su cinemática de inicio.
            self.__init__(self.mission_number, skip_boss_intro=False)
        else:
            self.stop_all_audio()       # Salir: nada de música colgada en el menú.
            self.return_to_menu = True  # Activamos la bandera

    def update(self, dt):
        # Manejo limpio del fundido de entrada (Fade-in)
        if self.fading_in:
            elapsed_fade = pygame.time.get_ticks() - self.fade_in_timer
            self.fade_alpha = max(0, 255 - int((elapsed_fade / 1000.0) * 255))
            if self.fade_alpha == 0:
                self.fading_in = False

        if self.is_paused:
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
            enemy.update(dt, walls, self.player, self.pathfinding_grid)

        self.update_boss(dt)
        if self.player.is_dead:
            self.trigger_death_sequence()

        # La cámara sigue a Snake, o al punto de la cinemática cuando está activa.
        self.camera.update(self.camera_target())

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
                    r = int(color_edge[0] * (1 - factor) + color_edge[0] * factor)
                    g = int(color_edge[1] * (1 - factor) + color_edge[1] * factor)
                    b = int(color_edge[2] * (1 - factor) + color_edge[2] * factor)
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
                    r = int(color_edge[0] * (1 - factor) + color_edge[0] * factor)
                    g = int(color_edge[1] * (1 - factor) + color_edge[1] * factor)
                    b = int(color_edge[2] * (1 - factor) + color_edge[2] * factor)
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

        # Jefe, capa de suelo: franja de aviso, impactos y sombra del Hind (debajo de las entidades).
        if self.boss:
            self.boss.draw_ground(self.virtual_surface, self.camera)
        
        entities_to_draw = [self.player] + list(self.enemies_group)
        entities_to_draw.sort(key=lambda entity: entity.rect.bottom)

        for entity in entities_to_draw:
            entity.draw_with_camera(self.virtual_surface, self.camera)

        for enemy in self.enemies_group:
            enemy.draw_vision(self.virtual_surface, self.camera)
        
        if self.map:
            self.map.render_roofs(
                self.virtual_surface,
                self.camera,
                render_condition=self.player.is_hidden or self.player.is_near_hidden_zone(margin=15),
            )

        # Jefe, capa aérea: helicóptero elevándose, explosiones y debug (sobre los techos).
        if self.boss:
            self.boss.draw_air(self.virtual_surface, self.camera)

        if self.state == "DYING" or self.fading_in:
            fade_surface = pygame.Surface((self.virtual_surface.get_width(), self.virtual_surface.get_height()))
            fade_surface.fill((0, 0, 0))
            fade_surface.set_alpha(self.fade_alpha)
            self.virtual_surface.blit(fade_surface, (0, 0))

        scaled_surface = pygame.transform.scale(self.virtual_surface, (surface.get_width(), surface.get_height()))
        surface.blit(scaled_surface, (0, 0))

        self.health_bar.draw(surface, self.player)

        # Barra del jefe: después del escalado, sobre la pantalla real.
        if self.boss and self.boss_mode in ("FIGHT", "DEFEATED"):
            self.boss_bar.draw(surface, self.boss)

        # RENDERIZAR PAUSA ENCIMA DE TODO SI ESTÁ ACTIVA
        if self.is_paused:
            self.pause_menu.draw(surface)