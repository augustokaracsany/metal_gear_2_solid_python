import pygame
import sys
import os
from src.player import Player
from src.camera import Camera
from src.enemy import Enemy  # MERGE.
from src.tilemap import TiledMap  # Mapas TMX
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT

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
        
        # 1. DICCIONARIO DE NIVELES: Mapea cada misión a sus respectivas rutas de archivos
        self.levels_data = {
            1: {
                "tmx": "assets/sprites/maps/entry_point_brightness3-576x768.tmx",
                "png": "assets/sprites/maps/entry_point_brightness3-576x768.png"
            },
            2: {
                "tmx": "assets/sprites/maps/building1_floor1-960x960.tmx",  # Reemplaza con la ruta real de tu misión 2
                "png": "assets/sprites/maps/building1_floor1-960x960.png"
            },
            3: {
                "tmx": "assets/sprites/maps/mission3_map.tmx",  # Reemplaza con la ruta real de tu misión 3
                "png": "assets/sprites/maps/mission3_map.png"
            },
            4: {
                "tmx": "assets/sprites/maps/mission4_map.tmx",  # Reemplaza con la ruta real de tu misión 4
                "png": "assets/sprites/maps/mission4_map.png"
            }
        }
        
        # Obtenemos los datos de la misión actual (si el número no existe, por defecto usa la misión 1)
        current_level = self.levels_data.get(self.mission_number, self.levels_data[1])
        
        # Grupos de sprites y colisiones
        self.all_sprites = pygame.sprite.Group()
        self.walls_group = pygame.sprite.Group()
        self.enemies_group = pygame.sprite.Group()
        
        # 2. CARGAMOS EL MAPA DINÁMICAMENTE SEGÚN LA MISIÓN SELECCIONADA
        try:
            self.map = TiledMap(current_level["tmx"], scale=2)
        except Exception as e:
            print(f"AVISO: No se pudo cargar el mapa TMX para la misión {self.mission_number} ({e}). Usando imagen plana de respaldo.")
            self.map = None
            self.raw_map = pygame.image.load(current_level["png"]).convert()
            self.map_scale = 2 
            self.map_image = pygame.transform.scale(self.raw_map, (self.raw_map.get_width() * self.map_scale, self.raw_map.get_height() * self.map_scale))

        # Obtenemos las dimensiones reales del mapa para la cámara.
        if self.map:
            map_width = self.map.width
            map_height = self.map.height
        else:
            map_width = self.map_image.get_width()
            map_height = self.map_image.get_height()

        # Definimos una resolución virtual más pequeña (la mitad de la pantalla = zoom x2 visual perfecto)
        self.virtual_width = SCREEN_WIDTH // 2
        self.virtual_height = SCREEN_HEIGHT // 2
        self.virtual_surface = pygame.Surface((self.virtual_width, self.virtual_height))

        # Instanciamos la cámara pasándole el tamaño virtual correcto
        self.camera = Camera(map_width, map_height, self.virtual_width, self.virtual_height)
        
        # Obtenemos las coordenadas de inicio desde el objeto 'player_spawn' del mapa Tiled
        spawn_x, spawn_y = self.map.get_spawn_point("player_spawn", (400, 350)) if self.map else (400, 350)

        # Cargamos las zonas ocultas de forma segura
        if self.map:
            self.hidden_zones = self.map.get_hidden_zones("zonas_oculto")
            self.hidden_zones_top = self.map.get_hidden_zones_top()
            self.hidden_zones_bottom = self.map.get_hidden_zones_bottom()
        if not hasattr(self, "hidden_zones") or self.hidden_zones is None:
            self.hidden_zones = []
        if not hasattr(self, "hidden_zones_top") or self.hidden_zones_top is None:
            self.hidden_zones_top = []
        if not hasattr(self, "hidden_zones_bottom") or self.hidden_zones_bottom is None:
            self.hidden_zones_bottom = []

        # LÍMITES SUPERIORES DE ZONAS OCULTAS POR DONDE NO SE PUEDE ENTRAR Y SALIR VERTICALMENTE.
        self.top_barriers = self.map.get_top_barriers("limites_top") if self.map else []
                
        # Instanciamos a Snake en la posición del mapa
        self.player = Player(spawn_x, spawn_y)
        self.all_sprites.add(self.player)

        self.camera.update(self.player)

        patrol_routes = self.map.get_patrol_path("enemy_patrols")

        if patrol_routes:
            ruta_actual = patrol_routes[0]
            pos_inicial_x = ruta_actual[0][0]
            pos_inicial_y = ruta_actual[0][1]
            guardia = Enemy(pos_inicial_x, pos_inicial_y, ruta_actual)
            self.enemies_group.add(guardia)

    def trigger_victory_sequence(self):
        if self.state == "PLAYING":
            self.state = "VICTORY"
            self.victory_timer = pygame.time.get_ticks()
            self.fade_alpha = 0
            try:
                pygame.mixer.music.load("assets/audio/music/mission_complete.mp3") # O la pista que uses de victoria
                pygame.mixer.music.play()
            except Exception as e:
                print(f"Aviso música de victoria: {e}")

    def trigger_death_sequence(self):
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
        
        # Verificamos si los archivos de la siguiente misión existen realmente en la PC
        data = self.levels_data[next_num]
        tmx_exists = os.path.exists(data.get("tmx", ""))
        png_exists = os.path.exists(data.get("png", ""))
        
        return tmx_exists or png_exists
        
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

            elif self.state == "PLAYING":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_k:  # Tecla de prueba de muerte
                        self.trigger_death_sequence()
                    elif event.key == pygame.K_v:
                        self.trigger_victory_sequence()
                self.player.punch_self_event(event)

    def confirm_victory_option(self):
        """Ejecuta la acción seleccionada en el menú de Victoria"""
        pygame.mixer.music.fadeout(1000)
        
        has_next = self.has_next_mission()
        
        if self.victory_selected_option == 0:
            # Reintentar la misión actual
            self.__init__(self.mission_number)
        elif self.victory_selected_option == 1 and has_next:
            # Siguiente misión
            self.__init__(self.mission_number + 1)
        else:
            # Salir al menú principal (si es la opción Salir o si era el último nivel disponible)
            self.return_to_menu = True

    def confirm_game_over_option(self):
        pygame.mixer.music.fadeout(1000)
        if self.game_over_selected_option == 0:
            # Reintentar la misión
            self.__init__(self.mission_number)
        else:
            # Indicar que queremos volver al menú principal
            self.return_to_menu = True

    def update(self, dt):
        # Manejo limpio del fundido de entrada (Fade-in) sin alterar la velocidad del juego
        if self.fading_in:
            elapsed_fade = pygame.time.get_ticks() - self.fade_in_timer
            self.fade_alpha = max(0, 255 - int((elapsed_fade / 1000.0) * 255))
            if self.fade_alpha == 0:
                self.fading_in = False
            # Dejamos que el juego corra por debajo para que la cámara y el mundo actúen normal

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

        for enemy in self.enemies_group:
            enemy.update(dt, walls) 

        self.camera.update(self.player)

    def draw(self, surface):
        if self.state == "VICTORY":
            surface.fill((42, 20, 15)) 
            
            w = surface.get_width()
            h = surface.get_height()
            
            bar_height = int(h * 0.22)  
            
            # Efecto de bordes sutiles
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
                    # CORREGIDO: Se usa color_center en la segunda parte de la suma
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

            # --- OPCIONES DINÁMICAS EN LA FRANJA INFERIOR ---
            prompt_delay = 1500
            if elapsed > prompt_delay:
                has_next = self.has_next_mission()
                max_options = 3 if has_next else 2

                if self.victory_selected_option >= max_options:
                    self.victory_selected_option = max_options - 1

                center_y = h - (bar_height // 2)

                if has_next:
                    # CASO 1: Hay 3 opciones (REINTENTAR, SIGUIENTE, SALIR)
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
                    # CASO 2: No hay archivos de la siguiente misión. Solo 2 opciones (REINTENTAR, SALIR)
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

            # --- TRANSICIÓN TIPO FADE DE ENTRADA ---
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
            
            bar_height = int(h * 0.22)  # Ocupan el 22% de la altura cada una
            
            color_center = (42, 20, 15)
            color_edge = (15, 7, 5)     # Tono oscuro para el resto de la barra
            gradient_size = 75          # Altura en píxeles donde se aplica el desvanecimiento del borde
            
            # 1. Barra superior (sólida y con degradado solo en su borde inferior)
            top_surface = pygame.Surface((w, bar_height))
            top_surface.fill(color_edge)
            for y in range(bar_height - gradient_size, bar_height):
                if y >= 0:
                    factor = (y - (bar_height - gradient_size)) / gradient_size
                    r = int(color_edge[0] * (1 - factor) + color_center[0] * factor)
                    g = int(color_edge[1] * (1 - factor) + color_center[1] * factor)
                    b = int(color_edge[2] * (1 - factor) + color_center[2] * factor)
                    pygame.draw.line(top_surface, (r, g, b), (0, y), (w, y))
            
            # 2. Barra inferior (sólida y con degradado solo en su borde superior)
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
            
            paradox_delay = 12500 # 12.5 segundos
            
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

            # --- OPCIONES EN LA FRANJA INFERIOR ---
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

            # --- TRANSICIÓN TIPO FADE DE ENTRADA ---
            fade_duration = 1000  
            if elapsed < fade_duration:
                fade_alpha = int(255 * (1 - (elapsed / fade_duration)))
                fade_surface = pygame.Surface((w, h))
                fade_surface.fill((0, 0, 0))
                fade_surface.set_alpha(fade_alpha)
                surface.blit(fade_surface, (0, 0))
                
            return

        # --- 2. RENDERIZADO NORMAL DEL JUEGO (PLAYING / DYING) ---
        self.virtual_surface.fill((0, 0, 0))
        
        # Obtenemos las paredes
        walls = self.map.get_collision_rects() if self.map else []

        if self.map:
            self.map.render_below(self.virtual_surface, self.camera)
        else:
            self.virtual_surface.blit(self.map_image, self.camera.camera_rect.topleft) 
        
        # Dibujamos ordenados por profundidad (Z-index clásico de Metal Gear basado en rect.bottom)
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

        # --- 3. EFECTO DE FADE-OUT SI ESTAMOS EN EL ESTADO "DYING" ---
        if self.state == "DYING" or self.fading_in:
            fade_surface = pygame.Surface((self.virtual_surface.get_width(), self.virtual_surface.get_height()))
            fade_surface.fill((0, 0, 0))
            fade_surface.set_alpha(self.fade_alpha)
            self.virtual_surface.blit(fade_surface, (0, 0))

        # Escalamos la superficie virtual a la pantalla principal
        scaled_surface = pygame.transform.scale(self.virtual_surface, (surface.get_width(), surface.get_height()))
        surface.blit(scaled_surface, (0, 0))

        # --- DEBUG VISUAL DE ZONAS OCULTAS ---
        if hasattr(self, "hidden_zones") and self.hidden_zones:
            for zone in self.hidden_zones:
                debug_screen_rect = zone.move(self.camera.camera_rect.topleft)
                pygame.draw.rect(self.virtual_surface, (0, 255, 255), debug_screen_rect, 2)