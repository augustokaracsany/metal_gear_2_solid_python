import os
import pygame
import sys
import math
import pytmx
from src.enemy import Enemy
from src.player import Player
from src.camera import Camera
from src.tilemap import TiledMap  # Mapas TMX
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS
from src.items import Item  
from src.hud import HealthBar
from src.codec import CodecManager
from src.settings import ENEMY_CONTACT_DAMAGE
from src.pause import PauseMenu
from src.settings import PUNCH_DAMAGE, PUNCH_HIT_PADDING, PUNCH_STUN_TIME
from src.settings import PUNCH_HIT_SOUND_PATH, PUNCH_HIT_SOUND_VOLUME
from src.inventory import InventoryMenu
from src.item_message import ItemMessage
from src.hud_inventory import HUDInventory  # <--- HUD de inventario equipado activo
from src.fox import FoxScreenManager
from src.flashback import FlashbackManager
import numpy as np
from src.rain import Rain
from src.radar import Radar
from src.vent_cinematic import VentCinematic

import src.hind as hind_mod
from src.hind import (
    HindD, BossHealthBar, HIT_DAMAGE,
    CINE_START_DELAY, CINE_PAN_IN_TIME, CINE_PAN_OUT_TIME, CINE_CAM_OFFSET,
    MUSIC, MUSIC_MASTER, MUSIC_FADE_MS, AUDIO_DIR,
)
from src import weapon_settings as WS
from src.weapons import WeaponManager, collect_pickups, make_pickup, PICKUPS
from src.weapon_hud import WeaponHUD
from src.fire_fx import FireFX


# Misión (clave de levels_data) donde pelea el jefe HIND-D.
BOSS_MISSION = 4


class _CamTarget:
    """Objeto con rect para que Camera.update() lo siga durante la cinemática (y al apuntar el Stinger)."""
    def __init__(self):
        self.rect = pygame.Rect(0, 0, 1, 1)


class Game:
    ALERT_MAX = 99
    ALERT_DECAY_TIME = 15.0    # en segundos
    FOUND_SFX_PATH = "assets/audio/sfx/found.mp3"
    CHASE_MUSIC_PATH = "assets/audio/music/encounter.mp3"
    # Volumen relativo de cada canción (1.0 = tal cual el slider de OPCIONES; 0.7 = 30 % más bajo).
    # Va de 0.0 a 1.0: si el slider ya está al 100 % no se puede subir más, por eso conviene bajar
    # las demás canciones y dejar la que querés más fuerte en 1.0.
    TRACK_GAIN = {
        "assets/audio/music/musica_entry_point.mp3": 0.7,   # primer mapa: un poco más bajo
        "assets/audio/music/Advance Immediately.mp3": 1.0,
        "assets/audio/music/encounter.mp3": 1.0,            # persecución: más fuerte que el resto
        "assets/audio/music/2048_63.mp3": 1.0,
    }
    CHASE_MUSIC_ENABLED = True   # True = al ser detectado suena la música de persecución en bucle
    ALERT_FONT_PATH = "assets/fonts/PixelOperator8-Bold.ttf"
    ALERTED_STATES = ("ALERT", "CHASE")
    NOISE_PUNCH_RADIUS = 250   # px
    ALLY_CALL_RADIUS = 320     # px: a quién avisa el guardia que te ve
    PUNCH_REACH = 14           # px por delante del jugador
    EXIT_FADE_MS = 700
    DEATH_MUSIC_DELAY_MS = 1500
    DEATH_FADE_DELAY_MS = 1000
    DEAD_TEXT = "P Y T H O N   I S   D E A D"
    DEAD_TEXT_DELAY_MS = 250
    DEAD_TEXT_FADE_MS = 1000
    DEAD_BLUR_LEVELS = 10
    DEATH_FADE_MAX = 100
    DEATH_FADE_RATE = 0.04
    VENT_MUSIC_PATH = "assets/audio/music/the_man_who_sold_the_world.mp3"
    MUSIC_FADE_OUT_S = 0.8     # baja la música del nivel
    MUSIC_FADE_IN_S = 2.0      # entra la música de la cinemática
    # Pantalla de victoria: el título se escribe, después aparecen las estadísticas una por una
    # y recién al final el menú REINTENTAR / SIGUIENTE / SALIR.
    VICTORY_STATS_START_MS = 1400
    VICTORY_ROW_MS = 280
    VICTORY_MENU_DELAY_MS = 3100
    VICTORY_ANIM_FRAME_MS = 80                         # duración de cada frame de la animación
    VICTORY_ANIM_SHADE = 55                            # oscurecimiento general del fondo animado (0-255)
    VICTORY_BG_PATH = "assets/images/victory_bg.png"   # fondo de la pantalla de victoria (si no existe, usa el degradado de siempre)
    VENT_ZONE_MUSIC_PATH = "assets/audio/music/2048_63.mp3"
    DEBUG_ENABLED_AT_START = False
    debug_mode = DEBUG_ENABLED_AT_START
    intro_cinematic_played = False

    def __init__(self, mission_number=1, skip_boss_intro=False):
        # Por si venimos de una partida anterior con el Stinger apuntando: mouse normal.
        pygame.mouse.set_visible(True)
        pygame.event.set_grab(False)

        self.mission_number = mission_number
        self.pending_action = None   # ("restart", n) o ("menu", None)
        self._current_track = None   # canción que debería estar sonando
        self.death_music_started = False
        self.exit_fade_start = 0
        self.exit_fade_volume = 1.0
        self._mf = None
        
        # Estados del juego
        self.state = "PLAYING"
        self.fade_alpha = 255
        self.fading_in = True
        self.game_over = False
        self.game_over_timer = 0.0
        self.victory_selected_option = 0
        self.victory_timer = 0.0
        self.game_over_selected_option = 0
        self.return_to_menu = False
        self._dead_text_levels = None

        # Música y audio
        self._music_key = None
        self.restart_music = False

        # --- SISTEMA DE PAUSA ---
        self.is_paused = False
        self.pause_menu = PauseMenu(SCREEN_WIDTH, SCREEN_HEIGHT)

        # --- JEFE ---
        self.boss = None
        self.boss_mode = "NORMAL"
        self.cine_phase = "NONE"
        
        # --- INVENTARIO COMPLETO (MENÚ) ---
        self.inventory_open = False
        self.inventory_menu = InventoryMenu(SCREEN_WIDTH, SCREEN_HEIGHT)


        # --- HUD EQUIPAMIENTO ACTIVO (PANTALLA PRINCIPAL) ---
        self.hud_inventory = HUDInventory(position="bottom-left")

        # --- CODEC ---
        self.codec_manager = CodecManager()

        # --- PANTALLA DEL ZORRO ---
        
        self.fox_screen = FoxScreenManager()

        # --- FLASHBACKS ---

        self.flashbacks = FlashbackManager()

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
                "tmx": "assets/sprites/maps/swamp-960x768.tmx",
                "png": "assets/sprites/maps/swamp-960x768.png"
            },
            4: {
                "tmx": "assets/sprites/maps/hind-d_boss_fight-576x1344.tmx",
                "png": "assets/sprites/maps/hind-d_boss_fight-576x1344.png"
            },
            
        }
        
        current_level = self.levels_data.get(self.mission_number, self.levels_data[1])

        # --- ATRIBUTOS DE CONTROL DEL JEFE (HIND-D) ---
        self.boss = None
        self.boss_mode = "NORMAL"     # Puede ser "NORMAL", "CUTSCENE", "FIGHT", etc.
        self.cine_phase = "NONE"
        self.skip_boss_intro = skip_boss_intro

        # --- MÚSICA DE FONDO ---
        self.start_level_music()

        # Grupos de Sprites
        self.all_sprites = pygame.sprite.Group()
        self.enemies_group = pygame.sprite.Group()
        self.items_group = pygame.sprite.Group()
        self.bullets_group = pygame.sprite.Group()
        self.missiles_group = pygame.sprite.Group()    # Misiles Stinger y sus explosiones (capa aérea).

        # Armas/munición del mapa ya recogidas (para que no reaparezcan al recargar el mapa).
        self.picked_pickups = set()
        self.ration_eaten = False   # True cuando Snake ya se comió la ración (para que no reaparezca en el camión).
        
        self.enemy_bullets = pygame.sprite.Group()

        # Estado guardado de cada mapa visitado (guardias muertos y posiciones de los vivos).
        self.map_states = {}
        self.current_map_key = None
        self.current_route_count = 0
        self.codec_zones = []
        self.vent_zones = []

        self.alert_level = 0.0
        self.chase_music_active = False   # True si la música de persecución tomó el control
        self.music_delay = None           # segundos hasta que arranque la música tras el SFX
        try:
            self.punch_hit_sfx = pygame.mixer.Sound(PUNCH_HIT_SOUND_PATH)
            self.punch_hit_sfx.set_volume(PUNCH_HIT_SOUND_VOLUME)
        except Exception as e:
            print(f"Aviso sonido de golpe a enemigo: {e}")
            self.punch_hit_sfx = None
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
        self.radar = Radar(self.ALERTED_STATES)
        self._shot_noise_cd = 0.0     # espera entre ruidos de disparo
        self._reset_mission_stats()   # estadísticas para la pantalla de victoria

        # Escalado final de la pantalla virtual a la ventana ( ver _scale_to_screen ).
        self._scale_mode = "direct"   # "direct" | "buffer" | "plain"
        self._scale_buf = None

        # Instanciación inicial del mapa y entidades
        self.load_level(current_level["tmx"])

        self.virtual_width = SCREEN_WIDTH // 2
        self.virtual_height = SCREEN_HEIGHT // 2
        self.virtual_surface = pygame.Surface((self.virtual_width, self.virtual_height))

        self.rain = Rain(self.virtual_width, self.virtual_height)

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
        self.item_message = ItemMessage()

        # --- ARMAS (Beretta / M16 / UZI / Stinger) ---
        self.reset_weapons()
        self.weapon_hud = WeaponHUD()
        self.fire_fx = FireFX("assets/sprites/solid_python", scale=2)
        # self.fire_fx.DEBUG_MUZZLE = True  # Descomentá para ver el punto celeste y ajustar offsets
        self.player.fire_fx = self.fire_fx

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

        # Siempre al final: el fundido se mide desde que terminó de cargar todo.
        self.fading_in = True
        self.fade_alpha = 255
        self.fade_in_timer = pygame.time.get_ticks()

        self.cine = None
        self.cutscenes_done = set()
        if self.mission_number == 2 and not Game.intro_cinematic_played:
            Game.intro_cinematic_played = True
            self.start_vent_cutscene(fade_in=True)

    def _level_music_path(self):
        if self.mission_number == 1:
            music_path = "assets/audio/music/musica_entry_point.mp3"
        elif self.mission_number == 2:
            music_path = "assets/audio/music/Advance Immediately.mp3"
        elif self.mission_number == 3:
            music_path = "assets/audio/music/Shallow (Alert Mode Level 1 Part 4 & Swamp BGM).mp3"
        elif self.mission_number == 4:
            music_path = "assets/audio/music/Level 1 Warning (Alert Mode Level 1 Part 5).mp3"
        else:
            return None  # Si hay otra misión que aún no tiene canción, no hace nada
        return music_path

    def _desired_track(self, in_vents):
        return self.VENT_ZONE_MUSIC_PATH if in_vents else self._level_music_path()

    def start_level_music(self):
        music_path = self._level_music_path()
        if music_path is None:
            return
        try:
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.set_volume(self.pause_menu.music_volume)
            if self.restart_music:
                self.pause_menu.music_gain = self.TRACK_GAIN.get(music_path, 1.0)
                pygame.mixer.music.set_volume(self.pause_menu.music_volume * self.pause_menu.music_gain)
                pygame.mixer.music.play(-1, 0, 1000)
            else:
                pygame.mixer.music.play(-1)
            self._current_track = music_path
        except Exception as e:
            print(f"Aviso música (Misión {self.mission_number}): {e}")

    def fade_to_music(self, path, out_s=None, in_s=None, loops=-1):
        self._current_track = path
        self._mf = {
            "path": path, "loops": loops,
            "gain": self.TRACK_GAIN.get(path, 1.0),
            "out": self.MUSIC_FADE_OUT_S if out_s is None else out_s,
            "in": self.MUSIC_FADE_IN_S if in_s is None else in_s,
            "t": 0.0,
            "v0": pygame.mixer.music.get_volume(),
            "phase": "out" if pygame.mixer.music.get_busy() else "load",
        }

    def _update_music_fade(self, dt):
        mf = self._mf
        if not mf:
            return
        if mf["phase"] == "out":
            mf["t"] += dt
            k = min(1.0, mf["t"] / max(0.01, mf["out"]))
            pygame.mixer.music.set_volume(mf["v0"] * (1 - k))
            if k >= 1.0:
                mf["phase"] = "load"
        if mf["phase"] == "load":
            try:
                pygame.mixer.music.load(mf["path"])
                pygame.mixer.music.set_volume(0.0)
                pygame.mixer.music.play(mf["loops"])
            except Exception as e:
                print(f"Aviso música de cinemática: {e}")
                self._mf = None
                return
            mf["phase"], mf["t"] = "in", 0.0
            return
        if mf["phase"] == "in":
            mf["t"] += dt
            k = min(1.0, mf["t"] / max(0.01, mf["in"]))
            pygame.mixer.music.set_volume(self.pause_menu.music_volume * mf["gain"] * k)
            if k >= 1.0:
                self._mf = None

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

    # ===================== ARMAS =====================
    def reset_weapons(self):
        """Crea un WeaponManager nuevo (y deja el mouse normal si había uno anterior)."""
        if hasattr(self, "weapons"):
            self.weapons.shutdown()
        starting = getattr(WS, "MISSION_START_WEAPONS", {}).get(self.mission_number, WS.STARTING_WEAPONS)
        self.weapons = WeaponManager(self.player, starting=list(starting))
        self.player.weapon_manager = self.weapons
        self.player.weapons = self.weapons.owned      # La lista que lee el inventario.
        self.player.weapon_locked = False

    def shoot_bullet(self, damage_mult):
        """Callback del WeaponManager: crea la bala de las armas de fuego."""
        self.stat_shots += 1
        muzzle = self.fire_fx.muzzle_pos(self.player, self.weapons.current_id)
        self.bullets_group.add(self.player.fire_bullet(damage_mult, muzzle=muzzle))
        self.fire_fx.on_shot(self.player, self.weapons.current_id)
        self._emit_shot_noise()

    def _emit_shot_noise(self):
        """Disparar hace ruido: los guardias dentro del radio del arma van a investigar.
        Se emite como máximo cada WS.SHOT_NOISE_INTERVAL s (cada ruido hace calcular rutas)."""
        if self._shot_noise_cd > 0:
            return
        radius = WS.WEAPON_DEFS.get(self.weapons.current_id, {}).get("noise_radius", 0)
        if radius <= 0:
            return
        self._shot_noise_cd = WS.SHOT_NOISE_INTERVAL
        self.emit_noise(self.player.rect.center, radius)
        
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

        # La lluvia solo se activa en el mapa exterior de la misión 1 (no en el camión).
        self.rain_active = (os.path.normpath(tmx_path) == os.path.normpath(self.levels_data[1]["tmx"]))

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
            # Zonas de ventilación (capa "vents_trigger"): ahí Snake va siempre cuerpo a tierra.
            self.vent_zones = []
            scale = self.map.scale
            for o in self.find_objects("vents_trigger"):
                self.vent_zones.append(pygame.Rect(
                    int(o.x * scale), int(o.y * scale),
                    int(o.width * scale), int(o.height * scale)))
            print(f"[VENTS] zonas de ventilación cargadas: {len(self.vent_zones)}")   # TEMPORAL: borrar después de probar.

            self.radar.build(self.map.width, self.map.height, self.walls)
        self.enemies_group.empty()
        self.items_group.empty()
        self.bullets_group.empty()
        self.missiles_group.empty()

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
                guardia = Enemy(ruta[0][0], ruta[0][1], ruta, start_delay=i * 0.5)

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

                # Ración de comida (camión de truck_interior_2)
                elif obj.name == "food_ration" and hasattr(self, 'player') and "food_ration" not in self.player.inventory and not self.ration_eaten:
                    scale = self.map.scale
                    try:
                        ration_item = Item("food_ration", 0, 0, "assets/sprites/items/racion_roja.png", scale=1.7)
                        ration_item.rect.center = (int((obj.x + obj.width / 2) * scale), int((obj.y + obj.height / 2) * scale))
                        self.items_group.add(ration_item)
                    except Exception as e:
                        print(f"Error cargando sprite de la ración: {e}")

                # Armas y munición del equipo (PICKUPS: stinger_launcher, stinger_missiles, etc.)
                elif obj.name in PICKUPS:
                    uid = (obj.name, getattr(obj, "id", None))
                    if uid in self.picked_pickups:
                        continue
                    scale = self.map.scale
                    center = (int((obj.x + (obj.width or 0) / 2) * scale),
                              int((obj.y + (obj.height or 0) / 2) * scale))
                    self.items_group.add(make_pickup(obj.name, center, uid))

            # C. GRILLA DE PATHFINDING (después de crear los enemigos: usa el tamaño de su hitbox)
            if self.enemies_group:
                actor_size = self.enemies_group.sprites()[0].rect.size
                self.pathfinding_grid = self.map.create_pathfinding_grid(
                    cell_px=8, actor_size=actor_size)
                self.pathfinding_grid._tiled_map = self.map
            else:
                self.pathfinding_grid = None
        else:
            self.hidden_zones = []
            self.hidden_zones_top = []
            self.hidden_zones_bottom = []
            self.top_barriers = []
            self.walls = []
            self.pathfinding_grid = None
            self.radar.clear()
            self.codec_zones = None

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
        self._mf = None
        self._music_key = None
        # Al salir al menú el mouse tiene que volver a ser el normal (el Stinger lo oculta).
        if hasattr(self, "weapons"):
            self.weapons.shutdown()

    def set_paused(self, value):
        """Pausa/reanuda el juego y también los sonidos y la música."""
        self.is_paused = value
        # Solo se pausan los efectos de sonido. La música sigue sonando durante la pausa
        # (así se oye el cambio de volumen del slider de OPCIONES al moverlo).
        try:
            if value:
                pygame.mixer.pause()
                self.weapons.suspend()
            else:
                pygame.mixer.unpause()
                self.weapons.resume()
        except pygame.error:
            pass
        # El menú de pausa se maneja con mouse: lo liberamos mientras dura la pausa.
        if value:
            self.weapons.suspend()
        else:
            self.weapons.resume()

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
        mientras el Hind despega (así se ve cómo sale volando por arriba) y vuelve a Snake.
        Con el Stinger equipado sigue a Snake desplazada hacia donde apunta la mira."""
        if self.boss_mode != "CUTSCENE":
            offset = self.weapons.camera_offset()
            if offset is not None:
                cx, cy = self.player.rect.center
                self._cam_target.rect.center = (int(cx + offset.x), int(cy + offset.y))
                return self._cam_target
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

        for trigger in self.map.get_triggers():
            if self.player.rect.colliderect(trigger["rect"]):
                props = trigger["properties"]
                target = props.get("target_map")
                use_fox = props.get("fox_menu", True)      # false = sin pantalla del zorro

                # Camión o fox_menu=false: cambio directo, sin zorro.
                if self._is_truck(target) or self._is_truck(self.current_map_key) or not use_fox:
                    self._do_transition(trigger)
                else:
                    self.fox_screen.start(lambda t=trigger: self._do_transition(t))
                break

    def _mission_for_map(self, tmx_path):
        """Número de misión al que pertenece un mapa principal (entry point = 1, edificio = 2, etc.).
        Devuelve None para mapas que no son el inicio de una misión (ducto, pantano, camión...)."""
        if not tmx_path:
            return None
        destino = os.path.normpath(tmx_path)
        for num, data in self.levels_data.items():
            if isinstance(num, int) and os.path.normpath(data["tmx"]) == destino:
                return num
        return None

    def _do_transition(self, trigger):
        props = trigger["properties"]
        target_map = props.get("target_map")
        self.player.set_force_crawl(False)   # Se vuelve a activar solo si el mapa nuevo tiene zonas de ventilación.
        self.load_level(target_map)

        # La misión sale del mapa de destino. Antes se tomaba solo de la propiedad "mission" del
        # trigger, y la salida del ducto hacia el Entry Point decía mission=2: volvías a la misión 1
        # pero el juego creía que estabas en la 2, y "Reiniciar misión" te mandaba a la 2.
        mision_destino = self._mission_for_map(target_map)
        if mision_destino is not None:
            nueva_mision = mision_destino
        elif "mission" in props:
            nueva_mision = int(props["mission"])
        else:
            nueva_mision = self.mission_number
        if nueva_mision != self.mission_number:
            self.mission_number = nueva_mision
            self.start_level_music()    # la música cambia junto con la misión
            # Si llegamos al mapa del jefe, inicializar el boss fight
            if self.mission_number == BOSS_MISSION:
                self.boss      = None
                self.boss_mode = None
                self.setup_boss()

        scale = self.map.scale if self.map else 2
        spawn_x = float(props.get("spawn_x", 180)) * scale
        spawn_y = float(props.get("spawn_y", 550)) * scale
        self.player.x = spawn_x
        self.player.y = spawn_y
        self.player.rect.x = int(spawn_x)
        self.player.rect.y = int(spawn_y)

        if "prone" in props:
            self.player.set_stance("CRAWL" if props["prone"] else "STAND")

        map_width = self.map.width if self.map else self.map_image.get_width()
        map_height = self.map.height if self.map else self.map_image.get_height()
        self.camera = Camera(map_width, map_height, self.virtual_width, self.virtual_height)
        self.camera.update(self.player)

        target_map = props.get("target_map")
        goes_to_building = (
            target_map is not None
            and os.path.normpath(str(target_map)) == os.path.normpath(self.levels_data[2]["tmx"])
        )
        if goes_to_building and props.get("start_cinematic", True):
            self.start_vent_cutscene()

    def trigger_victory_sequence(self):
        if self.state == "PLAYING":
            self.stop_boss_audio()
            self.weapons.suspend()      # Mouse normal para el menú de victoria.
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
            self.stop_boss_audio()
            self.weapons.suspend()      # Mouse normal para el menú de game over.
            self.state = "DYING"
            self.death_timer = pygame.time.get_ticks()
            self.fade_alpha = 0

            pygame.mixer.music.stop()

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

    # ===================== ESTADÍSTICAS DE MISIÓN =====================
    def _reset_mission_stats(self):
        self.stat_time = 0.0     # segundos jugados (la pausa, el inventario y el codec no cuentan)
        self.stat_alerts = 0     # veces que te descubrieron
        self.stat_items = 0      # raciones usadas
        self.stat_shots = 0      # disparos efectuados
        Enemy.kills = 0

    def _count_life_items_used(self, inventory_before):
        """Cuenta las raciones que salieron del inventario entre antes y ahora."""
        used = inventory_before.count("food_ration") - self.player.inventory.count("food_ration")
        if used > 0:
            self.stat_items += used

    def _victory_menu_ready(self):
        return pygame.time.get_ticks() - self.victory_timer >= self.VICTORY_MENU_DELAY_MS

    def _get_victory_bg(self, w, h):
        """Fondo de victoria ya escalado, oscurecido y con degradado arriba/abajo (se arma una sola vez)."""
        if getattr(self, "_vic_bg_key", None) == (w, h):
            return self._vic_bg
        self._vic_bg_key = (w, h)
        self._vic_bg = None
        try:
            img = pygame.image.load(self.VICTORY_BG_PATH).convert()
        except Exception as e:
            print(f"Aviso fondo de victoria: {e}")
            return None
        iw, ih = img.get_size()
        k = max(w / iw, h / ih)                       # "cover": llena la pantalla sin deformar
        img = pygame.transform.smoothscale(img, (int(iw * k) + 1, int(ih * k) + 1))
        bg = pygame.Surface((w, h))
        bg.blit(img, ((w - img.get_width()) // 2, (h - img.get_height()) // 2))

        shade = pygame.Surface((w, h), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 85))                     # oscurece todo un poco
        top_h, bot_h = int(h * 0.26), int(h * 0.30)   # degradados negros: el título y el menú se leen bien
        for y in range(top_h):
            pygame.draw.line(shade, (0, 0, 0, int(190 * (1 - y / top_h) ** 1.4)), (0, y), (w, y))
        for y in range(bot_h):
            pygame.draw.line(shade, (0, 0, 0, int(230 * (1 - y / bot_h) ** 1.4)), (0, h - 1 - y), (w, h - 1 - y))
        bg.blit(shade, (0, 0))
        self._vic_bg = bg
        return bg

    def _load_victory_anim(self):
        """Carga una sola vez los frames del fondo animado de victoria (si la carpeta no existe, queda vacío)."""
        self._vic_anim_src = []
        try:
            names = sorted(n for n in os.listdir(self.VICTORY_ANIM_DIR) if n.lower().endswith(".png"))
            for n in names:
                self._vic_anim_src.append(pygame.image.load(os.path.join(self.VICTORY_ANIM_DIR, n)).convert())
        except Exception as e:
            print(f"Aviso fondo animado de victoria: {e}")
            self._vic_anim_src = []

    def _build_victory_shade(self, w, h):
        """Capa de sombra con degradados arriba/abajo para que el título y el menú se lean bien."""
        shade = pygame.Surface((w, h), pygame.SRCALPHA)
        shade.fill((0, 0, 0, self.VICTORY_ANIM_SHADE))
        top_h, bot_h = int(h * 0.26), int(h * 0.30)
        for y in range(top_h):
            pygame.draw.line(shade, (0, 0, 0, int(190 * (1 - y / top_h) ** 1.4)), (0, y), (w, y))
        for y in range(bot_h):
            pygame.draw.line(shade, (0, 0, 0, int(230 * (1 - y / bot_h) ** 1.4)), (0, h - 1 - y), (w, h - 1 - y))
        return shade

    def _get_victory_anim_frame(self, w, h):
        """Frame actual del fondo animado ya escalado y oscurecido (se cachea cada frame al usarlo). None si no hay animación."""
        if not hasattr(self, "_vic_anim_src"):
            self._load_victory_anim()
        src = self._vic_anim_src
        if not src:
            return None
        if getattr(self, "_vic_anim_key", None) != (w, h):
            self._vic_anim_key = (w, h)
            self._vic_anim_cache = {}
            self._vic_anim_shade = self._build_victory_shade(w, h)
        idx = ((pygame.time.get_ticks() - self.victory_timer) // self.VICTORY_ANIM_FRAME_MS) % len(src)
        frame = self._vic_anim_cache.get(idx)
        if frame is None:
            img = src[idx]
            iw, ih = img.get_size()
            k = max(w / iw, h / ih)                   # "cover": llena la pantalla sin deformar
            img = pygame.transform.smoothscale(img, (int(iw * k) + 1, int(ih * k) + 1))
            frame = pygame.Surface((w, h))
            frame.blit(img, ((w - img.get_width()) // 2, (h - img.get_height()) // 2))
            frame.blit(self._vic_anim_shade, (0, 0))
            self._vic_anim_cache[idx] = frame
        return frame

    def start_vent_cutscene(self, fade_in=False):
        if "vent_exit" in self.cutscenes_done:
            return
        self.cutscenes_done.add("vent_exit")
        self.fade_to_music(self.VENT_MUSIC_PATH)
        self.cine = VentCinematic(fade_in=fade_in)
        self.state = "VENT_CINE"

    @staticmethod
    def _render_spaced(font, text, color, spacing):
        """Texto con espacio extra entre letras (el título se ve más 'cinemático')."""
        glyphs = [font.render(c, False, color) for c in text]
        width = sum(g.get_width() for g in glyphs) + spacing * max(0, len(glyphs) - 1)
        surf = pygame.Surface((max(1, width), font.get_height()), pygame.SRCALPHA)
        x = 0
        for g in glyphs:
            surf.blit(g, (x, 0))
            x += g.get_width() + spacing
        return surf

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

        # Cuando termina el sonido de alerta, la música del nivel vuelve a sonar.
        if self.music_delay is not None:
            self.music_delay -= dt
            if self.music_delay <= 0:
                self.music_delay = None
                if self.CHASE_MUSIC_ENABLED:
                    self._start_chase_music()
                else:
                    try:
                        pygame.mixer.music.unpause()
                    except pygame.error:
                        pass

    def _on_alert_start(self):
        self.stat_alerts += 1
        self._mf = None                                   # no dejar un fundido viejo pisando la alarma
        self.chase_music_active = self.CHASE_MUSIC_ENABLED
        if self.CHASE_MUSIC_ENABLED:
            pygame.mixer.music.stop()
            self._current_track = self.CHASE_MUSIC_PATH
        else:
            pygame.mixer.music.pause()
        if self.found_sfx:
            self.found_sfx.play()
            self.music_delay = self.found_sfx.get_length()
        else:
            self.music_delay = 0.0

    def _start_chase_music(self):
        try:
            pygame.mixer.music.load(self.CHASE_MUSIC_PATH)
            self.pause_menu.music_gain = self.TRACK_GAIN.get(self.CHASE_MUSIC_PATH, 1.0)
            pygame.mixer.music.set_volume(self.pause_menu.music_volume * self.pause_menu.music_gain)
            pygame.mixer.music.play(-1)
        except Exception as e:
            print(f"Aviso música de persecución: {e}")

    def _on_alert_end(self):
        self.music_delay = None
        if self.chase_music_active:
            self.chase_music_active = False
            self._current_track = None     # fuerza el fundido a la música del nivel / ventilación
            self.start_level_music()

    def _reset_alert(self):
        """Apaga todo de golpe (cambio de nivel, muerte)."""
        if self.chase_music_active:
            pygame.mixer.music.stop()
        elif self.music_delay is not None:
            pygame.mixer.music.unpause()    # la alarma se cortó a la mitad: la música no se queda pausada
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
        
        """Reinicia la misión completa: mapa, enemigos, ítems, jefe (CON su cinemática de inicio),
        música y estado de Snake."""
        # 0) Cortar los sonidos y la música del intento anterior.
        self.stop_boss_audio()
        try:
            pygame.mixer.music.stop()
            pygame.mixer.stop()
        except pygame.error:
            pass

        self._reset_mission_stats()

        # 1) Estado del jugador (ANTES de cargar el nivel: la caja solo reaparece
        #    si Snake no la tiene en el inventario).
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
        p.facing = "UP"
        p.frame_index = 0
        p.anim_timer = 0.0
        p.input_locked = False
        p.health = p.max_health
        p.damage_taken = 0
        p.is_dead = False
        p.update_offsets_for_stance()

        # 1b) Armas de cero (sin Stinger, munición inicial) y pickups del mapa disponibles otra vez.
        self.reset_weapons()
        self.picked_pickups = set()
        self.ration_eaten = False

        # 1c) Olvidar el estado guardado de los mapas (guardias muertos y posiciones). Sin esto,
        #     load_level() guardaba cómo quedó el mapa actual justo antes de recargarlo y los
        #     guardias que habías matado no reaparecían. Con la clave en None no guarda nada.
        self.map_states = {}
        self.current_map_key = None

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
        else:
            self.start_level_music()        # La canción de la misión vuelve a sonar desde 0.

    def handle_events(self, events):
        for event in events:
            if self.fox_screen.active and event.type != pygame.QUIT:
                continue
            if self.pending_action:
                continue
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if self.state == "VICTORY":
                has_next = self.has_next_mission()
                max_options = 3 if has_next else 2

                if not self._victory_menu_ready():
                    if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.victory_timer = pygame.time.get_ticks() - self.VICTORY_MENU_DELAY_MS   # saltar animación
                    continue

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

            if self.state == "DYING":
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

            if self.state == "VENT_CINE":
                self.cine.handle_events([event])
                continue

            # Abrir Pausa con la tecla ESC (cerrar / volver lo maneja el propio menú de pausa)
            if (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                    and not self.is_paused and not self.inventory_open):
                self.set_paused(True)
                continue        # Sin esto, el MISMO ESC le llega al menú de pausa y la cierra al instante.
            # Inventario: se abre con la tecla I y mientras está abierto el juego queda pausado.
            if self.inventory_open:
                inv_before = list(self.player.inventory)
                inv_action = self.inventory_menu.handle_input(event, self.player)
                self._count_life_items_used(inv_before)
                if inv_action == "CLOSE":
                    self.inventory_open = False
                    self.weapons.resume()       # Si quedó equipado el Stinger, vuelve la mira.
                continue
            if (event.type == pygame.KEYDOWN and event.key == pygame.K_i
                    and not self.is_paused and self.state == "PLAYING"):
                self.inventory_menu.open(self.player)
                self.inventory_open = True
                continue

            # Abrir la pausa con ESC (cerrar / volver lo maneja el propio menú de pausa)
            if (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                    and not self.is_paused and not self.inventory_open
                    and self.state == "PLAYING"):
                self.set_paused(True)
                self.weapons.suspend()          # Mouse normal mientras está el inventario.
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
                    self.weapons.suspend()         # Mouse normal para el menú principal.
                    self.set_paused(False)
                    return "GOTO_MENU"
            else:
                # Armas: disparo (ESPACIO), recarga (R), modo de tiro (F), cambio de arma (1) y mouse del Stinger.
                if self.state == "PLAYING" and not self.player.input_locked:
                    self.weapons.handle_event(event)

                # Si el juego NO está en pausa, responde a las acciones del jugador
                if event.type == pygame.KEYDOWN:
                    # --- Activar / desactivar el modo DEBUG ---
                    if event.key == pygame.K_F9:
                        self.debug_mode = not self.debug_mode
                        self.weapons.notify("DEBUG: ACTIVADO" if self.debug_mode else "DEBUG: DESACTIVADO")

                    # --- Teclas normales del juego (siempre activas) ---
                    elif event.key == pygame.K_j:
                        self.use_ration()
                    elif event.key == pygame.K_TAB:
                        self.state = "RADIO_MENU"
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE) and self.boss_mode == "CUTSCENE":
                        self.boss.skip_takeoff()                # saltear cinemática
                        if self.cine_phase in ("DELAY", "PAN_IN"):
                            self.cine_phase = "TAKEOFF"

                    # --- Teclas de DEBUG (solo con el modo activo) ---
                    elif self.debug_mode:
                        if event.key == pygame.K_k:
                            self.cleanup()
                            self.trigger_death_sequence()
                        elif event.key == pygame.K_v:
                            self.cleanup()
                            self.trigger_victory_sequence()
                        elif event.key == pygame.K_h:
                            self.player.take_damage(10)
                        elif event.key == pygame.K_F1:
                            self.debug_start_boss()
                        elif event.key == pygame.K_F2 and self.boss:
                            self.boss.take_hit(HIT_DAMAGE)
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
                        elif event.key == pygame.K_F8:
                            for wid in ("beretta", "m16", "uzi", "stinger"):
                                self.weapons.add_weapon(wid)
                            self.weapons.add_ammo("stinger", WS.STINGER_MISSILES_PER_PICKUP)
                            self.weapons.notify("DEBUG: TODAS LAS ARMAS + MISILES")
                self.player.punch_self_event(event)
        return None

    def use_ration(self):
        """Tecla J: Snake se come la ración y recupera 40 de vida."""
        p = self.player
        if self.state != "PLAYING" or p.is_dead or p.is_dying:
            return
        if "food_ration" not in p.inventory:
            self.weapons.notify("NO TENÉS RACIONES")
            return
        if p.health >= p.max_health:
            self.weapons.notify("TENÉS LA VIDA COMPLETA")   # No gasta la ración si no hace falta.
            return

        p.inventory.remove("food_ration")
        self.stat_items += 1          # <- nueva
        self.ration_eaten = True
        if getattr(p, "equipped_item", None) == "food_ration":
            p.equipped_item = None
        p.heal(40)
        self.weapons.notify("RACIÓN: +40 DE VIDA")

    def execute_radio_call(self):
        target_call_id = "default"

        for zone in self.codec_zones:
            if self.player.rect.colliderect(zone["rect"]):
                target_call_id = zone["call_id"]
                break

        self.state = "CODEC"
        self.codec_manager.start_call(target_call_id, calling=True)

    def execute_radio_call_id(self, call_id, calling):
        self.state = "CODEC"
        self.codec_manager.start_call(call_id, calling)      # calling=False: sin tono

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
        self.stop_boss_audio()
        action, mission = self.pending_action
        pygame.mixer.music.stop()
        pygame.mixer.music.set_volume(self.pause_menu.music_volume)
        if action == "restart":
            self.__init__(mission)    # __init__ pone pending_action = None
        else:
            self.pending_action = None
            self.return_to_menu = True
            self.stop_all_audio()       # Salir: nada de música colgada en el menú.
            self.return_to_menu = True  # Activamos la bandera

    def update(self, dt, surface):
        if self.pending_action:
            self._update_exit_fade()
            return
        if not self.is_paused:
            self._update_music_fade(dt)

        if self.fox_screen.active:
            self.fox_screen.update(dt)
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
            fade_elapsed = max(0, elapsed_death - self.DEATH_FADE_DELAY_MS)
            self.fade_alpha = min(self.DEATH_FADE_MAX, int(fade_elapsed * self.DEATH_FADE_RATE))

            self.player.update_death(dt)
            self.flashbacks.update(dt)
            
            if not self.death_music_started and elapsed_death >= self.DEATH_MUSIC_DELAY_MS:
                self.death_music_started = True
                
                try:
                    pygame.mixer.music.load("assets/audio/music/game_over.mp3")
                    pygame.mixer.music.play()
                except Exception as e:
                    print(f"No se pudo cargar la música game_over.mp3: {e}")

            if elapsed_death >= max(4500, self.flashbacks.total_ms() + 500):
                self.state = "GAME_OVER"
                self.game_over_timer = pygame.time.get_ticks()
            return

        if self.state == "GAME_OVER" or self.state == "VICTORY":
            return

        if self.state == "CODEC":
            self.codec_manager.update(dt)
            if self.codec_manager.finished:
                self.state = "PLAYING"
            return

        if self.state == "VENT_CINE":
            self.cine.update(dt)
            if self.cine.finished:
                self.cine = None
                self.state = "PLAYING"
                self.fade_to_music("assets/audio/music/Advance Immediately.mp3", out_s=1.5, in_s=1.5)
                self.execute_radio_call_id("vent_radio", True)
            return
        
        self.stat_time += dt

        walls = self.walls

        if self.rain_active:
            self.rain.update(dt)

        # Dentro de las ventilaciones Snake va siempre cuerpo a tierra.
        in_vents = any(self.player.rect.colliderect(zone) for zone in self.vent_zones)
        self.player.set_force_crawl(in_vents)

        if (self.state == "PLAYING" and not self.chase_music_active
                and self.music_delay is None and self._mf is None):
            want = self._desired_track(in_vents)
            if want and want != self._current_track:
                self.fade_to_music(want)

        # El Stinger no se puede usar cuerpo a tierra: vuelve al arma de fuego anterior.
        if in_vents and self.weapons.current.kind == "launcher":
            if self.weapons.last_firearm_id in self.weapons.owned:
                self.weapons.equip(self.weapons.last_firearm_id)
            else:
                self.weapons.current.on_unequip(self.player)
                self.weapons.current_id = None

        # Con el Stinger equipado Snake queda quieto y mira hacia donde apunta la mira.
        self.player.weapon_locked = self.weapons.blocks_movement
        forced_facing = self.weapons.facing_override
        if forced_facing:
            self.player.facing = forced_facing

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

        # Armas y munición del mapa (camiones del Stinger).
        got = collect_pickups(self.player.rect, self.items_group, self.weapons,
                            item_message=self.item_message, sfx_volume=self.pause_menu.sfx_volume)
        self.picked_pickups.update(uid for uid in got if uid is not None)

        # Armas: cadencia, balas, recarga, Stinger (lock-on / misiles) y auto-desequipado.
        boss_target = self.boss if (self.boss and self.boss_mode == "FIGHT") else None
        missiles_before = len(self.missiles_group)
        self.weapons.update(
            dt,
            self.shoot_bullet,
            can_fire=self.player.can_use_weapon(),
            target=boss_target,
            projectiles=self.missiles_group,
        )
        self.stat_shots += max(0, len(self.missiles_group) - missiles_before)   # misiles lanzados
        self.fire_fx.update(dt)
        self._shot_noise_cd = max(0.0, self._shot_noise_cd - dt)
        if not self.weapons.blocks_movement:
            self.player.weapon_locked = False

        self.check_map_transitions()

        alerted = self.alert_level > 0
        # Presupuesto de búsquedas A* de ESTE frame (compartido entre todos los guardias).
        Enemy.begin_frame()
        for enemy in self.enemies_group:
            enemy.global_alert = alerted
            enemy.update(dt, walls, self.player, self.pathfinding_grid, self.enemy_bullets)

        self._update_alert(dt)

        self.update_boss(dt)
        if self.player.is_dead:
            self.trigger_death_sequence()

        # La cámara sigue a Snake, o al punto de la cinemática / de la mira del Stinger.
        self.camera.update(self.camera_target())
        self.weapons.constrain_aim(self.camera, self.virtual_width, self.virtual_height)

        # Golpe: mientras dura, daña al primer enemigo que tenga delante (una vez por golpe).
        if self.player.is_punching and not self.player.punch_hit_done:
            punch_rect = self.player.get_punch_rect()
            for enemy in self.enemies_group:
                if punch_rect.colliderect(enemy.rect.inflate(PUNCH_HIT_PADDING, PUNCH_HIT_PADDING)):
                    enemy.take_damage(PUNCH_DAMAGE, PUNCH_STUN_TIME, self.player.rect.center)
                    self.player.punch_hit_done = True
                    if self.punch_hit_sfx:
                        self.punch_hit_sfx.play()   # solo suena cuando el golpe conecta
                    break

        # Balas: se mueven y chocan contra paredes, enemigos o el borde del mapa.
        if self.map:
            bounds = pygame.Rect(0, 0, self.map.width, self.map.height)
        else:
            bounds = self.map_image.get_rect()
        self.bullets_group.update(dt, walls, self.enemies_group, bounds)

        # Balas enemigas: chocan con paredes y alcanzan a Snake por su hitbox (con invulnerabilidad).
        self.enemy_bullets.update(dt, walls, self.player.rect)
        for bullet in list(self.enemy_bullets):
            if bullet.hit_target:
                self.player.take_damage(bullet.damage)
                bullet.kill()
                
        # Misiles del Stinger (vuelan por el aire: no chocan con paredes).
        self.missiles_group.update(dt, walls, self.enemies_group, bounds)

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
        # Barato: cada guardia solo deja el ruido pendiente; el A* se reparte entre frames (ver Enemy.hear_noise).
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

    def cleanup(self):
        """Llamar siempre que se abandone el nivel (ESC, menú, salir)."""
        self._reset_alert()
        pygame.mixer.music.stop()   # por si quedó sonando algo del nivel
        self._mf = None

    def _build_dead_text(self):
        font = pygame.font.Font("assets/fonts/PixelOperator8-Bold.ttf", 28)
        base = font.render(self.DEAD_TEXT, True, (190, 190, 160))
        pad = 24                                   # margen para que el difuminado no se recorte
        w, h = base.get_size()
        canvas = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        canvas.blit(base, (pad, pad))
        cw, ch = canvas.get_size()

        self._dead_text_levels = [canvas]          # nivel 0 = nítido
        for i in range(1, self.DEAD_BLUR_LEVELS):
            k = 1.0 / (1 + i * 1.0)
            small = pygame.transform.smoothscale(canvas, (max(1, int(cw * k)), max(1, int(ch * k))))
            self._dead_text_levels.append(pygame.transform.smoothscale(small, (cw, ch)))

    def _draw_dead_text(self, surface, elapsed, center):
        if self._dead_text_levels is None:
            self._build_dead_text()
        p = (elapsed - self.DEAD_TEXT_DELAY_MS) / self.DEAD_TEXT_FADE_MS
        p = max(0.0, min(1.0, p))
        if p <= 0:
            return
        levels = self._dead_text_levels
        img = levels[int((1 - p) * (len(levels) - 1) + 0.5)]   # empieza borroso y se enfoca
        img.set_alpha(int(255 * p))                            # y aparece a la vez
        surface.blit(img, img.get_rect(center=center))

    def _draw_exit_fade(self, surface):
        if not self.pending_action:
            return
        t = min(1.0, (pygame.time.get_ticks() - self.exit_fade_start) / self.EXIT_FADE_MS)
        overlay = pygame.Surface(surface.get_size())
        overlay.set_alpha(int(255 * t))
        surface.blit(overlay, (0, 0))

    def _scale_to_screen(self, surface):
        """Escala la pantalla virtual a la ventana SIN crear una Surface nueva por frame.

        1) "direct": escala directo sobre `surface` ( ahorra la alocación y el blit a pantalla completa ).
        2) "buffer": si el formato no coincide, escala a un buffer reutilizable y lo blitea.
        3) "plain":  el camino original ( Surface nueva por frame ), como último recurso.
        Si un modo falla, baja al siguiente una sola vez y se queda ahí."""
        size = surface.get_size()
        if self._scale_mode == "direct":
            try:
                pygame.transform.scale(self.virtual_surface, size, surface)
                return
            except (ValueError, pygame.error, TypeError):
                self._scale_mode = "buffer"
        if self._scale_mode == "buffer":
            try:
                if self._scale_buf is None or self._scale_buf.get_size() != size:
                    self._scale_buf = pygame.Surface(size)
                pygame.transform.scale(self.virtual_surface, size, self._scale_buf)
                surface.blit(self._scale_buf, (0, 0))
                return
            except (ValueError, pygame.error, TypeError):
                self._scale_mode = "plain"
        scaled_surface = pygame.transform.scale(self.virtual_surface, size)
        surface.blit(scaled_surface, (0, 0))

    @staticmethod
    def _is_truck(map_key):
        """True si la clave o ruta corresponde a un mapa del camión (truck, truck_interior, truck_interior_2...)."""
        return map_key is not None and "truck" in os.path.basename(str(map_key)).lower()

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
            
            # --- Fondo (imagen) ---
            bg = self._get_victory_anim_frame(w, h) or self._get_victory_bg(w, h)   # animado; si no hay frames, el fondo estático
            if bg:
                surface.blit(bg, (0, 0))

            # --- Título: letras grandes con espaciado, sombra y brillo verde ---
            title_size = 48 if h >= 640 else 32
            if getattr(self, "_vic_title_size", None) != title_size:
                self._vic_title_size = title_size
                self._vic_title_font = pygame.font.Font("assets/fonts/PixelOperator8-Bold.ttf", title_size)
            spacing = title_size // 8
            full_w = self._render_spaced(self._vic_title_font, target_text, (0, 0, 0), spacing).get_width()
            title_left = (w - full_w) // 2
            title_top = int(h * 0.13) - self._vic_title_font.get_height() // 2
            if chars_to_show > 0:
                part = text_to_render
                shadow = self._render_spaced(self._vic_title_font, part, (0, 0, 0), spacing)
                glow = self._render_spaced(self._vic_title_font, part, (15, 95, 50), spacing)
                main = self._render_spaced(self._vic_title_font, part, (60, 235, 115), spacing)
                surface.blit(shadow, (title_left + 4, title_top + 4))
                for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, -2), (-2, 2), (2, 2)):
                    surface.blit(glow, (title_left + ox, title_top + oy))
                surface.blit(main, (title_left, title_top))
            if chars_to_show >= len(target_text):
                line_y = title_top + self._vic_title_font.get_height() + 14
                pygame.draw.line(surface, (60, 235, 115), (title_left, line_y), (title_left + full_w, line_y), 2)
                pygame.draw.rect(surface, (60, 235, 115), (title_left - 10, line_y - 3, 6, 8))
                pygame.draw.rect(surface, (60, 235, 115), (title_left + full_w + 4, line_y - 3, 6, 8))

            # --- Estadísticas de la misión (panel oscuro: se leen bien sobre la imagen) ---
            if elapsed >= self.VICTORY_STATS_START_MS:
                if not hasattr(self, "_vic_stat_font"):
                    self._vic_stat_font = pygame.font.Font("assets/fonts/PixelOperator8.ttf", 16)
                total = int(self.stat_time)
                tiempo = f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"
                filas = [
                    ("TIEMPO DE JUEGO", tiempo),
                    ("VECES DESCUBIERTO", str(self.stat_alerts)),
                    ("ENEMIGOS ELIMINADOS", str(Enemy.kills)),
                    ("RACIONES USADAS", str(self.stat_items)),
                    ("DISPAROS EFECTUADOS", str(self.stat_shots)),
                    ("DAÑO TOTAL RECIBIDO", str(int(self.player.damage_taken))),
                ]
                step = max(26, int(h * 0.042))
                pad = step // 2
                pw, ph = min(560, w - 40), step * len(filas) + pad * 2
                px, py = (w - pw) // 2, int(h * 0.38)
                panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
                panel.fill((6, 8, 6, 175))
                surface.blit(panel, (px, py))
                pygame.draw.rect(surface, (60, 235, 115), (px, py, pw, ph), 1)
                pygame.draw.line(surface, (60, 235, 115), (px, py), (px + pw, py), 3)
                col_l, col_r = px + 28, px + pw - 28
                fh = self._vic_stat_font.get_height()
                for i, (etiqueta, valor) in enumerate(filas):
                    if elapsed < self.VICTORY_STATS_START_MS + i * self.VICTORY_ROW_MS:
                        break
                    cell = py + pad + i * step
                    text_y = cell + (step - fh) // 2
                    s_lab = self._vic_stat_font.render(etiqueta, True, (205, 205, 205))
                    s_val = self._vic_stat_font.render(valor, True, (60, 235, 115))
                    surface.blit(s_lab, (col_l, text_y))
                    surface.blit(s_val, s_val.get_rect(topright=(col_r, text_y)))
                    if i < len(filas) - 1:
                        pygame.draw.line(surface, (70, 80, 70), (col_l, cell + step - 1), (col_r, cell + step - 1), 1)

            prompt_delay = self.VICTORY_MENU_DELAY_MS
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
            w = surface.get_width()
            h = surface.get_height()
            
            porcentajes = np.random.rand(w, h)
            
            # 2. Crear la matriz RGB final vacía
            ruido_rgb = np.zeros((w, h, 3), dtype=np.uint8)
            
            # 3. Escalar cada canal multiplicando el porcentaje por el valor máximo de tu color
            ruido_rgb[:, :, 0] = (porcentajes * 42).astype(np.uint8)  # Canal Rojo
            ruido_rgb[:, :, 1] = (porcentajes * 20).astype(np.uint8)  # Canal Verde
            ruido_rgb[:, :, 2] = (porcentajes * 15).astype(np.uint8)  # Canal Azul
            
            # 4. Dibujar la estática en la pantalla
            pygame.surfarray.blit_array(surface, ruido_rgb)

            bar_height = int(h * 0.22)  
            
            pygame.draw.rect(surface, (0, 0, 0), (0, 0, w, bar_height))
            pygame.draw.rect(surface, (0, 0, 0), (0, h - bar_height, w, bar_height))

            # surface.blit(top_surface, (0, 0))
            # surface.blit(bottom_surface, (0, h - bar_height))
            
            font_large = pygame.font.Font("assets/fonts/PixelOperator8-Bold.ttf", 28)
            font_small = pygame.font.Font("assets/fonts/PixelOperator8.ttf", 16)
            font_medium = pygame.font.Font("assets/fonts/PixelOperator8-bold.ttf", 16)
            
            current_time = pygame.time.get_ticks()
            elapsed = current_time - self.game_over_timer
            
            self._draw_dead_text(surface, elapsed, (w // 2, h // 2))

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

        if self.state == "VENT_CINE" and self.cine:
            self.cine.draw(surface)
            self.fox_screen.draw(surface)
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

        for bullet in self.bullets_group:
            bullet.draw_with_camera(self.virtual_surface, self.camera)
        # Balas enemigas: igual que las de Snake, por encima de los sprites (salen a la altura del arma).
        for bullet in self.enemy_bullets:
            bullet.draw_with_camera(self.virtual_surface, self.camera)

        # for enemy in self.enemies_group:
        #     enemy.draw_vision(self.virtual_surface, self.camera)
        # self.fire_fx.draw(self.virtual_surface, self.camera)
        
        if self.map:
            self.map.render_roofs(
                self.virtual_surface,
                self.camera,
                render_condition=self.player.is_hidden or self.player.is_near_hidden_zone(margin=15),
            )

        if self.rain_active:
            self.rain.draw(self.virtual_surface)
        # Jefe, capa aérea: helicóptero elevándose, explosiones y debug (sobre los techos).
        if self.boss:
            self.boss.draw_air(self.virtual_surface, self.camera)

        # Misiles Stinger y sus explosiones: también son aéreos, van sobre los techos.
        for missile in self.missiles_group:
            missile.draw_with_camera(self.virtual_surface, self.camera)

        if self.state == "DYING" or self.fading_in:
            fade_surface = pygame.Surface((self.virtual_surface.get_width(), self.virtual_surface.get_height()))
            fade_surface.fill((0, 0, 0))
            fade_surface.set_alpha(self.fade_alpha)
            self.virtual_surface.blit(fade_surface, (0, 0))

        self._scale_to_screen(surface)

        if self.state == "PLAYING":
            self.health_bar.draw(surface, self.player)
            self._draw_alert(surface)
            self.radar.draw(surface, self.player, self.enemies_group)
            self.item_message.draw(surface)
            if self.debug_mode:
                tag = self.alert_font.render("DEBUG", True, (255, 60, 60))
                surface.blit(tag, (10, surface.get_height() - tag.get_height() - 10))

        # DIBUJAR HUD DE INVENTARIO SOBRE LA PANTALLA PRINCIPAL
        self.hud_inventory.draw(surface, self.player)

        if self.state == "DYING":
            self.flashbacks.draw(surface)

        # Mira del Stinger (se dibuja sobre la pantalla real, así queda nítida) y HUD del arma equipada.
        if self.state == "PLAYING" and self.boss_mode != "CUTSCENE":
            scale = surface.get_width() / self.virtual_width
            self.weapons.draw_overlay(surface, self.camera, scale)
            self.weapon_hud.draw(surface, self.weapons)

        # Barra del jefe: después del escalado, sobre la pantalla real.
        if self.boss and self.boss_mode in ("FIGHT", "DEFEATED"):
            self.boss_bar.draw(surface, self.boss)
        # INVENTARIO ENCIMA DE TODO SI ESTÁ ABIERTO
        if self.inventory_open:
            self.inventory_menu.draw(surface, self.player, self.health_bar)

        # RENDERIZAR PAUSA ENCIMA DE TODO SI ESTÁ ACTIVA
        if self.is_paused:
            self.pause_menu.draw(surface)

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
            option_text = "> Cuartel General <"
            opt_surf = font_medium.render(option_text, True, (38, 212, 99))
            opt_rect = opt_surf.get_rect(center=(w // 2, h // 2))
            surface.blit(opt_surf, opt_rect)

            # Instrucción abajo
            hint_surf = font_small.render("ENTER - Llamar | ESC - Salir", True, (180, 180, 180))
            hint_rect = hint_surf.get_rect(center=(w // 2, h - 80))
            surface.blit(hint_surf, hint_rect)

        elif self.state == "CODEC":
            self.codec_manager.draw(surface)

        self.fox_screen.draw(surface)