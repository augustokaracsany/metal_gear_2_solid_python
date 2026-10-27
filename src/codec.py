import pygame
import json
import sys

class CodecManager:
    def __init__(self, json_path="assets/json/codec_calls.json"):
        with open(json_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
            
        self.active = False
        self.current_call_data = None
        self.line_index = 0
        self.finished = False  # Bandera para indicar que terminó la llamada y el fade
        
        # Efecto de máquina de escribir
        self.displayed_text = ""
        self.full_text = ""
        self.text_speed = 20 
        self.char_timer = 0.0
        self.char_index = 0
        self.is_text_finished = False

        # Delays y tiempos
        self.waiting_delay = False
        self.text_start_time = 0
        self.text_delay_duration = 500

        # 1. Variables para el texto parpadeante "Enter"
        self.blink_timer = 0
        self.show_enter_prompt = True
        self.blink_interval = 500  # Parpadea cada 500ms

        # 2. Variables para el Fade Out (2 segundos = 2000 ms)
        self.is_fading = False
        self.fade_alpha = 0
        self.fade_duration = 2000
        self.fade_start_time = 0
        self.has_skipped = False

        # 4. Variables para la advertencia de skip con ESC
        self.skip_warning_active = False
        self.skip_warning_timer = 0

        try:
            self.text_sound = pygame.mixer.Sound("assets/audio/sfx/text_scroll.wav")
            self.text_sound_playing = False
        except Exception as e:
            print(f"Aviso: No se pudo cargar el sonido text_scroll.wav: {e}")
            self.text_sound = None
        
        self.font = pygame.font.Font("assets/fonts/PixelOperator8.ttf", 14)

    def start_call(self, call_id):
        if call_id in self.data["calls"]:
            self.current_call_data = self.data["calls"][call_id]
            self.active = True
            self.finished = False
            self.line_index = 0
            self.is_fading = False
            self.fade_alpha = 0
            
            bg_path = self.current_call_data.get("codec_background", "assets/codec/codec1.png")
            try:
                self.background_image = pygame.image.load(bg_path).convert()
                scale_factor = 3  
                new_width = self.background_image.get_width() * scale_factor
                new_height = self.background_image.get_height() * scale_factor
                self.current_image = pygame.transform.scale(self.background_image, (new_width, new_height))
            except Exception as e:
                print(f"Error al cargar el fondo de códec {bg_path}: {e}")
                self.current_image = pygame.Surface((800, 600)) 

            self._load_line()

    def _load_line(self):
        line_data = self.current_call_data["dialogo"][self.line_index]
        self.character_name = line_data["habla"]
        self.full_text = line_data["texto"]
        self.displayed_text = ""
        self.char_index = 0
        self.char_timer = 0.0
        self.is_text_finished = False

        self.waiting_delay = True
        self.text_start_time = pygame.time.get_ticks()
        self.text_delay_duration = 500

    def update(self, dt):
        if not self.active:
            return

        tiempo_actual = pygame.time.get_ticks()

        keys = pygame.key.get_pressed()
        is_speeding_up = keys[pygame.K_RETURN] or keys[pygame.K_SPACE]

        self.text_speed = 40 if is_speeding_up else 20  # 20 normal, 40 acelerado

        # 2. Controlar la transición de Fade Out al terminar la llamada
        if self.is_fading:
            if self.has_skipped:
                self.fade_duration = 500
            else:
                self.fade_duration = 2000
            elapsed_fade = tiempo_actual - self.fade_start_time
            progress = min(1.0, elapsed_fade / self.fade_duration)
            self.fade_alpha = int(progress * 255)
            if progress >= 1.0:
                self.active = False
                self.finished = True  # Señal para main.py de que ya puede pasar al juego
            return

        # 1. Actualizar parpadeo del texto "Enter"
        if tiempo_actual - self.blink_timer >= self.blink_interval:
            self.show_enter_prompt = not self.show_enter_prompt
            self.blink_timer = tiempo_actual

        # 4. Desactivar advertencia de skip si pasa más de 3 segundos sin presionar ESC de nuevo
        if self.skip_warning_active and tiempo_actual - self.skip_warning_timer > 3000:
            self.skip_warning_active = False

        # Manejo del delay inicial de 500ms por línea
        if getattr(self, "waiting_delay", False):
            if tiempo_actual - self.text_start_time >= self.text_delay_duration:
                self.waiting_delay = False
                if "audio" in self.current_call_data["dialogo"][self.line_index] and self.current_call_data["dialogo"][self.line_index]["audio"]:
                    try:
                        pygame.mixer.Sound(self.current_call_data["dialogo"][self.line_index]["audio"]).play()
                    except Exception as e:
                        print(f"Error al reproducir audio de voz: {e}")
            return

        keys = pygame.key.get_pressed()
        is_speeding_up = keys[pygame.K_RETURN] or keys[pygame.K_SPACE]
        self.text_speed = 40 if is_speeding_up else 20

        # Efecto de máquina de escribir
        if not self.is_text_finished:
            self.char_timer += dt
            if self.text_sound and not self.text_sound_playing:
                self.text_sound.play(-1)
                self.text_sound_playing = True
            
            if self.char_timer >= (1.0 / self.text_speed):
                self.char_timer = 0.0
                self.char_index += 1
                self.displayed_text = self.full_text[:self.char_index]
                
                if self.char_index >= len(self.full_text):
                    self.is_text_finished = True
                    if self.text_sound and self.text_sound_playing:
                        self.text_sound.stop()
                        self.text_sound_playing = False

    def handle_input(self, events):
        if not self.active or self.is_fading:
            return False

        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                # 4. Lógica de Skip con ESC
                if event.key == pygame.K_ESCAPE:
                    if not self.skip_warning_active:
                        self.skip_warning_active = True
                        self.skip_warning_timer = pygame.time.get_ticks()
                    else:
                        # Segunda vez que presiona ESC: Iniciamos fade out directo para saltear
                        self.has_skipped = True
                        self.is_fading = True
                        self.fade_start_time = pygame.time.get_ticks()
                        if self.text_sound and self.text_sound_playing:
                            self.text_sound.stop()
                            self.text_sound_playing = False
                        return False
                    return False

                # Avanzar texto con RETURN o SPACE (excluidos de activar advertencia de skip)
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    if self.is_text_finished:
                        self.line_index += 1
                        if self.line_index < len(self.current_call_data["dialogo"]):
                            self._load_line()
                        else:
                            self.is_fading = True
                            self.fade_start_time = pygame.time.get_ticks()
        return False

    def draw(self, surface):
        if not self.active and not self.is_fading:
            return

        w = surface.get_width()
        h = surface.get_height()

        # 1. Dibujar imagen del códec
        if hasattr(self, "current_image") and self.current_image:
            img_final_pos = self.current_image.get_rect(center=(w // 2, (h // 2) - 80))
            surface.blit(self.current_image, img_final_pos)

        # Caja de diálogo
        box_width = 720
        box_height = 110
        box_x = (w - box_width) // 2  
        box_y = (h // 2) + 140        

        pygame.draw.rect(surface, (255, 255, 255), (box_x, box_y, box_width, box_height), 3)
        inner_rect = pygame.Rect(box_x + 3, box_y + 3, box_width - 6, box_height - 6)
        pygame.draw.rect(surface, (0, 0, 204), inner_rect)  

        # 3. Renderizar Nombre y Texto con espaciado personalizado
        name_surf = self.font.render(f"{self.character_name}:", True, (255, 255, 100))
        surface.blit(name_surf, (box_x + 25, box_y + 18))

        text_surf = self.font.render(self.displayed_text, True, (255, 255, 255))
        surface.blit(text_surf, (box_x + 25, box_y + 50))

        # 1. Texto parpadeante "Enter" abajo del bloque azul
        if self.show_enter_prompt and self.is_text_finished and not self.is_fading:
            enter_surf = self.font.render("ENTER", True, (200, 200, 200))
            surface.blit(enter_surf, (box_x + box_width - 100, box_y + box_height + 10))

        # 4. Advertencia de skip en pantalla si se presionó ESC una vez
        if self.skip_warning_active:
            warning_surf = self.font.render("Presiona ESC nuevamente para saltear llamada", True, (255, 255, 255))
            warning_rect = warning_surf.get_rect(center=(w // 2, 50))
            surface.blit(warning_surf, warning_rect)

        # 2. Superficie de Fade Out (Pantalla negra que se oscurece gradualmente)
        if self.fade_alpha > 0:
            fade_surface = pygame.Surface((w, h))
            fade_surface.fill((0, 0, 0))
            fade_surface.set_alpha(self.fade_alpha)
            surface.blit(fade_surface, (0, 0))