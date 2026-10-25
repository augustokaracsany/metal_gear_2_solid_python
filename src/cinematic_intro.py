import pygame
import pytmx
import sys

class CinematicIntroState:
    def __init__(self, tmx_path="assets/sprites/maps/intro_entry_point.tmx"):
        self.map_scale = 3  # Factor de escala de los mapas en tu juego

        # Cargar el fondo PNG del mapa
        try:
            raw_bg = pygame.image.load("assets/sprites/maps/intro_entry_point.png").convert()
            bg_w = raw_bg.get_width() * self.map_scale
            bg_h = raw_bg.get_height() * self.map_scale
            self.bg_image = pygame.transform.scale(raw_bg, (bg_w, bg_h))
            self.map_width = bg_w
            self.map_height = bg_h
        except Exception as e:
            print(f"Aviso: No se pudo cargar el fondo intro_entry_point.png: {e}")
            self.bg_image = None
            self.map_width = 800  # Respaldo por defecto
            self.map_height = 2000
        
        # 1. Carga segura del mapa Tiled
        try:
            self.tmx_data = pytmx.load_pygame(tmx_path, pixelalpha=True)
        except Exception as e:
            print(f"Error al cargar el mapa Tiled {tmx_path}: {e}")
            self.tmx_data = None

        if self.tmx_data:
            self.map_width = self.tmx_data.width * self.tmx_data.tilewidth * self.map_scale
            self.map_height = self.tmx_data.height * self.tmx_data.tileheight * self.map_scale

            # Extraer y escalar las coordenadas de los objetos de Tiled
            try:
                start_obj = self.tmx_data.get_object_by_name("start_point")
                self.start_pos = [start_obj.x * self.map_scale, start_obj.y * self.map_scale]
            except ValueError:
                print("Aviso: No se encontró 'start_point', usando respaldo.")
                self.start_pos = [100, 700]

            try:
                middle_obj = self.tmx_data.get_object_by_name("middle_point")
                self.middle_pos = [middle_obj.x * self.map_scale, middle_obj.y * self.map_scale]
            except ValueError:
                print("Aviso: No se encontró 'middle_point', usando respaldo.")
                self.middle_pos = [100, 300]

            try:
                end_obj = self.tmx_data.get_object_by_name("end_point")
                self.end_pos = [end_obj.x * self.map_scale, end_obj.y * self.map_scale]
            except ValueError:
                print("Aviso: No se encontró 'end_point', usando respaldo.")
                self.end_pos = [300, 300]
        else:
            self.start_pos = [100, 700]
            self.middle_pos = [100, 300]
            self.end_pos = [300, 300]

        # 2. Posición inicial y fase (arranca explícitamente escalando)
        self.snake_pos = list(self.start_pos)
        self.phase = "CLIMBING"  

        # 3. Carga de sprites de Snake (con factor de escala 3)
        self.climb_frames = []
        for i in range(1, 6):
            try:
                img = pygame.image.load(f"assets/sprites/solid_python/climb{i}.png").convert_alpha()
                scaled_img = pygame.transform.scale(img, (img.get_width() * 3, img.get_height() * 3))
                self.climb_frames.append(scaled_img)
            except Exception as e:
                print(f"Aviso: No se pudo cargar climb{i}.png: {e}")

        self.left_crawl_frames = []
        for i in range(1, 3):
            try:
                img = pygame.image.load(f"assets/sprites/solid_python/crawl_left{i}.png").convert_alpha()
                scaled_img = pygame.transform.scale(img, (img.get_width() * 3, img.get_height() * 3))
                self.left_crawl_frames.append(scaled_img)
            except Exception as e:
                print(f"Aviso: No se pudo cargar crawl_left{i}.png: {e}")

        self.left_crouch_frames = []
        for i in range(1, 3):
            try:
                img = pygame.image.load(f"assets/sprites/solid_python/crouch_left{i}.png").convert_alpha()
                scaled_img = pygame.transform.scale(img, (img.get_width() * 3, img.get_height() * 3))
                self.left_crouch_frames.append(scaled_img)
            except Exception as e:
                print(f"Aviso: No se pudo cargar crouch_left{i}.png: {e}")

        self.up_crawl = []
        try:
            img = pygame.image.load(f"assets/sprites/solid_python/crouch_up1.png").convert_alpha()
            scaled_img = pygame.transform.scale(img, (img.get_width() * 3, img.get_height() * 3))
            self.up_crawl.append(scaled_img)
        except Exception as e:
            print(f"Aviso: No se pudo cargar crouch_up1.png: {e}")

        self.up_stand = []
        try:
            img = pygame.image.load(f"assets/sprites/solid_python/stand_up.png").convert_alpha()
            scaled_img = pygame.transform.scale(img, (img.get_width() * 3, img.get_height() * 3))
            self.up_stand.append(scaled_img)
        except Exception as e:
            print(f"Aviso: No se pudo cargar stand_up.png: {e}")

        # 4. Variables de control, temporizadores y música
        self.timer = 0
        self.animation_timer = 0
        self.current_frame = 0
        self.finished = False
        self.action_timer = 0
        self.cinematic_start_time = pygame.time.get_ticks()

        # 5. Variables para los Créditos
        self.developers_list = ["Lautaro Medina", "Augusto Karacsany", "Valentina Artaza", "Ambar Fiszman"] # Podes cambiar los nombres aca
        self.title_target_text = "Desarrolladores"
        self.title_current_len = 0
        self.credits_typewriter_timer = 0
        self.credits_phase = 0  # 0: Esperando 3s, 1: Escribiendo título, 2: Mostrando listado pop, 3: Esperando 5s finales, 4: Oculto
        self.credits_start_phase_time = 0
        self.visible_devs_count = 0
        self.credits_alpha = 255
        self.credits_fade_start_time = 0

        # 6. Variables para saltar la cinematica
        self.show_skip_warning = False
        self.warning_timer = 0
        self.warning_duration = 5000  # 5 segundos de visibilidad del aviso
        self.is_exiting = False
        self.exit_timer = 0
        self.is_fading = False
        self.fade_alpha = 0
        self.fade_timer = 0

        try:
            pygame.mixer.music.load("assets/audio/music/arriving.mp3")
            pygame.mixer.music.play(loops=0)  # Reproduce una sola vez
        except Exception as e:
            print(f"Aviso: No se pudo cargar la música arriving.mp3: {e}")

        try:
            raw_call = pygame.image.load("assets/sprites/radio/call.png").convert_alpha()
            self.call_sprite = pygame.transform.scale(
                raw_call, (raw_call.get_width() * self.map_scale, raw_call.get_height() * self.map_scale)
            )
        except Exception as e:
            print(f"Aviso: No se pudo cargar call.png: {e}")
            self.call_sprite = None

        try:
            self.radio_sfx = pygame.mixer.Sound("assets/audio/sfx/radio.mp3")
        except Exception as e:
            print(f"Aviso: No se pudo cargar radio.mp3: {e}")
            self.radio_sfx = None

        self.radio_channel = None

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                # Si presiona CUALQUIER TECLA que no sea ESC inicialmente
                if event.key != pygame.K_ESCAPE:
                    if not self.is_exiting:
                        if not self.show_skip_warning:
                            self.show_skip_warning = True
                            self.warning_timer = pygame.time.get_ticks()

                # Si presiona ESC
                elif event.key == pygame.K_ESCAPE:
                    if not self.is_exiting:
                        # Si el aviso ya estaba activo, SE SALTEA la cinemática
                        if self.show_skip_warning:
                            self.is_exiting = True
                            self.skipped = True
                            self.exit_timer = pygame.time.get_ticks()
                            self.is_fading = True
                            self.fade_alpha = 0
                            self.fade_timer = pygame.time.get_ticks()
                            pygame.mixer.music.fadeout(300)  # Desvanecer música rápido
                            if self.radio_channel:
                                self.radio_channel.stop()
                        else:
                            self.show_skip_warning = True
                            self.warning_timer = pygame.time.get_ticks()

    def update(self, dt):
        current_time = pygame.time.get_ticks()

        if self.show_skip_warning:
            if current_time - self.warning_timer >= self.warning_duration:
                self.show_skip_warning = False

        # Si se está saliendo / salteando la cinemática con fundido de salida
        if self.is_exiting:
            elapsed_exit = current_time - self.exit_timer
            if elapsed_exit < 500:  # Medio segundo de fundido negro de salida
                self.fade_alpha = int(255 * (elapsed_exit / 500))
                self.is_fading = True
            else:
                self.fade_alpha = 255
                self.finished = True  # Termina la cinemática y pasa al juego
            return

        # --- LÓGICA DE CRÉDITOS ---
        if self.credits_phase == 0:
            # Esperar 3 segundos desde que arranca la cinemática
            if current_time - self.cinematic_start_time >= 3000:
                self.credits_phase = 1
                self.credits_typewriter_timer = current_time
        elif self.credits_phase == 1:
            # Efecto máquina de escribir para el título "Desarrolladores" (cada ~80ms una letra)
            if current_time - self.credits_typewriter_timer >= 80:
                self.credits_typewriter_timer = current_time
                if self.title_current_len < len(self.title_target_text):
                    self.title_current_len += 1
                else:
                    # Termino de escribir el título, pasamos a mostrar los 4 creadores (pop cada 1 segundo)
                    self.credits_phase = 2
                    self.visible_devs_count = 1
                    self.credits_start_phase_time = current_time
        elif self.credits_phase == 2:
            # Mostrar cada uno de los 4 desarrolladores con efecto pop (1 por segundo)
            if current_time - self.credits_start_phase_time >= 1000:
                self.credits_start_phase_time = current_time
                if self.visible_devs_count < len(self.developers_list):
                    self.visible_devs_count += 1
                else:
                    # Terminaron de aparecer los 4, pasamos a la espera de 5 segundos
                    self.credits_phase = 3
                    self.credits_start_phase_time = current_time
        elif self.credits_phase == 3:
            # Esperar 5 segundos para que los créditos permanezcan en pantalla antes de desaparecer
            if current_time - self.credits_start_phase_time >= 5000:
                self.credits_phase = 4  # Ocultos definitivamente
        elif self.credits_phase == 4:
            # Desvanecer los créditos durante 1 segundo (1000 ms)
            elapsed_fade = current_time - self.credits_fade_start_time
            if elapsed_fade < 1000:
                self.credits_alpha = int(255 * (1.0 - (elapsed_fade / 1000)))
            else:
                self.credits_alpha = 0
                self.credits_phase = 5  # Ocultos definitivamente

        # FASE 1: ESCALANDO DESDE START_POINT HASTA MIDDLE_POINT
        if self.phase == "CLIMBING":
            # Nos aseguramos de que Snake esté quieto en el punto de inicio
            self.snake_pos = list(self.start_pos)
            
            # Control del tiempo de animación: 1.5 segundos exacto por frame
            self.animation_timer += dt
            if self.animation_timer >= 1.5:
                self.animation_timer = 0
                self.current_frame += 1
                
                # Si ya recorrió todos los frames de la animación de escalada, 
                # pasa a la fase de arrastrarse hacia el middle_point
                if self.current_frame >= len(self.climb_frames):
                    self.current_frame = 0
                    self.phase = "MOVING_TO_MIDDLE"

        # FASE 2: ARRASTRÁNDOSE HASTA EL MIDDLE_POINT
        elif self.phase == "MOVING_TO_MIDDLE":
            target_x, target_y = self.middle_pos
            speed = 30 * dt
            
            if self.snake_pos[0] < target_x:
                self.snake_pos[0] = min(self.snake_pos[0] + speed, target_x)
            elif self.snake_pos[0] > target_x:
                self.snake_pos[0] = max(self.snake_pos[0] - speed, target_x)

            if self.snake_pos[1] < target_y:
                self.snake_pos[1] = min(self.snake_pos[1] + speed, target_y)
            elif self.snake_pos[1] > target_y:
                self.snake_pos[1] = max(self.snake_pos[1] - speed, target_y)

            self.animation_timer += dt
            if self.animation_timer >= 0.4:
                self.current_frame = (self.current_frame + 1) % len(self.left_crawl_frames) if self.left_crawl_frames else 0
                self.animation_timer = 0

            distance = ((self.snake_pos[0] - target_x) ** 2 + (self.snake_pos[1] - target_y) ** 2) ** 0.5
            if distance < 5:
                self.snake_pos = [target_x, target_y]
                self.phase = "WAITING_CRAWLED"  # Cambiamos a movimiento agachado
                self.current_frame = 0
                self.animation_timer = 0
                self.action_timer = current_time

        # FASE 3: Esperar cuerpo a tierra.
        elif self.phase == "WAITING_CRAWLED":
            if current_time - self.action_timer >= 1000:
                self.phase = "WAITING_CROUCHED"
                self.action_timer = current_time

        # FASE 4: Esperar agachado.
        elif self.phase == "WAITING_CROUCHED":
            if current_time - self.action_timer >= 1000:
                self.phase = "MOVING_CROUCHED"
                self.action_timer = current_time

        # FASE 5: CAMINANDO/MOVIÉNDOSE AGACHADO HASTA EL END_POINT
        elif self.phase == "MOVING_CROUCHED":
            target_x, target_y = self.end_pos
            speed = 40 * dt  # Velocidad ligeramente menor por ir agachado
            
            if self.snake_pos[0] < target_x:
                self.snake_pos[0] = min(self.snake_pos[0] + speed, target_x)
            elif self.snake_pos[0] > target_x:
                self.snake_pos[0] = max(self.snake_pos[0] - speed, target_x)

            if self.snake_pos[1] < target_y:
                self.snake_pos[1] = min(self.snake_pos[1] + speed, target_y)
            elif self.snake_pos[1] > target_y:
                self.snake_pos[1] = max(self.snake_pos[1] - speed, target_y)

            # Animación usando los frames de agacharse (left_crouch_frames)
            self.animation_timer += dt
            if self.animation_timer >= 0.25:
                self.current_frame = (self.current_frame + 1) % len(self.left_crouch_frames) if self.left_crouch_frames else 0
                self.animation_timer = 0

            distance = ((self.snake_pos[0] - target_x) ** 2 + (self.snake_pos[1] - target_y) ** 2) ** 0.5
            if distance < 5:
                self.snake_pos = [target_x, target_y]
                self.phase = "WAITING_INITIAL"
                self.action_timer = current_time

        # FASE 6: ESPERA DE TIEMPO (AGACHADO EN END_POINT)
        elif self.phase == "WAITING_INITIAL":
            if current_time - self.action_timer >= 3000:
                self.phase = "FACING_FORWARD"
                self.action_timer = current_time

        # FASE 7: MIRA HACIA EL FRENTE
        elif self.phase == "FACING_FORWARD":
            if current_time - self.action_timer >= 2000:
                self.phase = "STANDING"
                self.action_timer = current_time

        # FASE 8: SE PONE DE PIE Y ESPERA A QUE TERMINE LA MÚSICA
        elif self.phase == "STANDING":
            if not pygame.mixer.music.get_busy():
                # Al terminar la música, disparamos el sonido de radio y pasamos a la fase RADIO_CALL
                if self.radio_sfx:
                    self.radio_channel = self.radio_sfx.play()
                self.phase = "RADIO_CALL"

        # FASE 9: LLAMADA DE RADIO ACTIVA (MUESTRA EL SPRITE 'CALL' Y ESPERA A QUE TERMINE EL SONIDO)
        elif self.phase == "RADIO_CALL":
            if self.radio_channel and not self.radio_channel.get_busy():
                self.finished = True
            elif not self.radio_sfx:
                self.finished = True

    def get_current_snake_sprite(self):
        if self.phase == "CLIMBING":
            return self.climb_frames[self.current_frame % len(self.climb_frames)] if self.climb_frames else None
        elif self.phase == "MOVING_TO_MIDDLE":
            return self.left_crawl_frames[self.current_frame % len(self.left_crawl_frames)] if self.left_crawl_frames else None
        elif self.phase == "WAITING_CRAWLED":
            return self.left_crawl_frames[0] if self.left_crawl_frames else None
        elif self.phase == "WAITING_CROUCHED":
            return self.left_crouch_frames[0] if self.left_crouch_frames else None
        elif self.phase == "MOVING_CROUCHED":
            return self.left_crouch_frames[self.current_frame % len(self.left_crouch_frames)] if self.left_crouch_frames else None
        elif self.phase == "WAITING_INITIAL":
            return self.left_crouch_frames[0] if self.left_crouch_frames else None
        elif self.phase == "FACING_FORWARD":
            return self.up_crawl[0] if self.up_crawl else None
        elif self.phase == "STANDING" or self.phase == "RADIO_CALL":
            return self.up_stand[0] if self.up_stand else None
        return None

    def draw(self, surface):
        surface.fill((0, 0, 0))
        screen_w = surface.get_width()
        screen_h = surface.get_height()

        if self.bg_image:
            camera_x = max(0, min(self.end_pos[0] - screen_w // 2, self.map_width - screen_w))
            camera_y = max(0, min(self.end_pos[1] - screen_h // 2, self.map_height - screen_h))
            # Dibujar la imagen de fondo desplazada por la cámara
            surface.blit(self.bg_image, (-camera_x, -camera_y))

        # Dibujar a Snake respecto a la cámara
        current_sprite = self.get_current_snake_sprite()
        if current_sprite:
            snake_screen_pos = (self.snake_pos[0] - camera_x, self.snake_pos[1] - camera_y)
            snake_rect = current_sprite.get_rect(center=snake_screen_pos)
            surface.blit(current_sprite, snake_rect)

        # --- RENDERIZADO DE CRÉDITOS A LA IZQUIERDA ---
        if self.credits_phase in [1, 2, 3]:
            try:
                font = pygame.font.Font("assets/fonts/PixelOperator8.ttf", 16)
                fontBold = pygame.font.Font("assets/fonts/PixelOperator8-bold.ttf", 16)
                credits_surf = pygame.Surface((350, 150), pygame.SRCALPHA)

                start_x = 40
                start_y = 60

                # 1. Dibujar Título con efecto máquina de escribir
                title_to_draw = self.title_target_text[:self.title_current_len]
                if title_to_draw:
                    title_surface = fontBold.render(title_to_draw, True, (235, 198, 26))
                    title_surface.set_alpha(self.credits_alpha)
                    surface.blit(title_surface, (start_x, start_y))

                # 2. Dibujar el listado de desarrolladores (efecto pop progresivo)
                if self.credits_phase >= 2:
                    for i in range(self.visible_devs_count):
                        dev_name = self.developers_list[i]
                        dev_surface = font.render(f"{dev_name}", True, (255, 224, 138))
                        dev_surface.set_alpha(self.credits_alpha)
                        surface.blit(dev_surface, (start_x + 10, start_y + 22 + (i * 20)))

                credits_surf.set_alpha(self.credits_alpha)
                
                # Dibujar la superficie de créditos en la pantalla principal (posición fija a la izquierda)
                surface.blit(credits_surf, (40, 60))

            except Exception as e:
                pass

        if self.show_skip_warning:
            try:
                font = pygame.font.Font("assets/fonts/PixelOperator8.ttf", 16)
                warning_surface = font.render("Presiona ESC nuevamente para saltear", True, (255, 255, 255))
                surface.blit(warning_surface, (20, 20))
            except Exception:
                pass

        # Aplicar fundido (fade) negro si está activo al salir/saltear
        if self.is_fading and self.fade_alpha > 0:
            fade_surf = pygame.Surface((screen_w, screen_h))
            fade_surf.fill((0, 0, 0))
            fade_surf.set_alpha(self.fade_alpha)
            surface.blit(fade_surf, (0, 0))

        if self.phase == "RADIO_CALL" and self.call_sprite:
            call_x = screen_w - self.call_sprite.get_width() - 30  # 30 px de margen desde la derecha
            call_y = 30  # 30 px de margen desde arriba
            surface.blit(self.call_sprite, (call_x, call_y))