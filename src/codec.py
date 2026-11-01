import pygame
import json
import sys
import random
import numpy as np

class CodecManager:
    FADE_IN_MS = 500
    CALL_SOUND_PATH = "assets/audio/sfx/radio.mp3"
    CALLING_TEXT = "Llamando..."
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

        self.fading_in = False
        self.fade_in_start = 0

        # Fase "Llamando..."
        self.calling = False        # True solo si la llamada la inicia el jugador
        self.ringing = False
        self.ring_start = 0
        self.ring_duration = 0
        try:
            self.call_sound = pygame.mixer.Sound(self.CALL_SOUND_PATH)
        except Exception as e:
            print(f"Aviso: no se pudo cargar radio.mp3: {e}")
            self.call_sound = None

        # Efecto CRT
        self._crt_cache = None  
        
        self.font = pygame.font.Font("assets/fonts/PixelOperator8.ttf", 14)

    def start_call(self, call_id, calling=False):
        """calling=True: el jugador llama a Cuartel General (suena el tono y dice 'Llamando...').
        calling=False: llamada entrante (ej. después de la cinemática), sin tono."""
        if call_id not in self.data["calls"]:
            print(f"Llamada '{call_id}' no existe en el JSON, uso 'default'")
            call_id = "default"

        self.current_call_data = self.data["calls"][call_id]
        self.active = True
        self.finished = False
        self.line_index = 0
        self.is_fading = False
        self.has_skipped = False
        self.is_text_finished = False
        self.displayed_text = ""
        self.skip_warning_active = False

        # El nombre se muestra desde el primer momento (también durante "Llamando...")
        self.character_name = self.current_call_data["dialogo"][0]["habla"]

        # Fundido de entrada: arranca en negro
        self.calling = calling and self.call_sound is not None
        self.ringing = False
        self.fading_in = True
        self.fade_in_start = pygame.time.get_ticks()
        self.fade_alpha = 255

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

        # _load_line() se llama al terminar el fundido (o el tono)

    def _start_ringing(self):
        self.ringing = True
        self.ring_start = pygame.time.get_ticks()
        self.call_sound.play()
        self.ring_duration = int(self.call_sound.get_length() * 1000)

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

        # Fade Out al terminar la llamada
        if self.is_fading:
            self.fade_duration = 500
            progress = min(1.0, (tiempo_actual - self.fade_start_time) / self.fade_duration)
            self.fade_alpha = int(progress * 255)
            if progress >= 1.0:
                self.active = False
                self.finished = True
            return

        # Parpadeo de "ENTER" y advertencia de skip (siguen corriendo en todas las fases)
        if tiempo_actual - self.blink_timer >= self.blink_interval:
            self.show_enter_prompt = not self.show_enter_prompt
            self.blink_timer = tiempo_actual
        if self.skip_warning_active and tiempo_actual - self.skip_warning_timer > 3000:
            self.skip_warning_active = False

        # Fase 1: fundido de entrada (de negro a la pantalla del códec)
        if self.fading_in:
            progress = min(1.0, (tiempo_actual - self.fade_in_start) / self.FADE_IN_MS)
            self.fade_alpha = int(255 * (1 - progress))
            if progress >= 1.0:
                self.fading_in = False
                self.fade_alpha = 0
                if self.calling:
                    self._start_ringing()
                else:
                    self._load_line()
            return

        # Fase 2: "Llamando..." mientras suena el tono
        if self.ringing:
            if tiempo_actual - self.ring_start >= self.ring_duration:
                self.ringing = False
                self._load_line()      # la conversación arranca sola
            return

        # Fase 3: conversación
        if getattr(self, "waiting_delay", False):
            if tiempo_actual - self.text_start_time >= self.text_delay_duration:
                self.waiting_delay = False
                line = self.current_call_data["dialogo"][self.line_index]
                if line.get("audio"):
                    try:
                        pygame.mixer.Sound(line["audio"]).play()
                    except Exception as e:
                        print(f"Error al reproducir audio de voz: {e}")
            return

        keys = pygame.key.get_pressed()
        is_speeding_up = keys[pygame.K_RETURN] or keys[pygame.K_SPACE]
        self.text_speed = 40 if is_speeding_up else 20

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
                        self.ringing = False
                        self.fading_in = False
                        if self.call_sound:
                            self.call_sound.stop()
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

    def wrap_text(self, text, font, max_width):
        """
        Toma un texto (puede contener \n) y lo divide en una lista de strings 
        de modo que ninguna línea supere el max_width en píxeles.
        """
        lines = []
        # Primero separamos por los saltos de línea explícitos que ya tengas en el JSON
        explicit_paragraphs = text.split('\n')
        
        for paragraph in explicit_paragraphs:
            if not paragraph.strip():
                lines.append("")  # Línea en blanco si hay un salto doble
                continue
                
            words = paragraph.split(' ')
            current_line = ""
            
            for word in words:
                # Probamos cómo queda la línea actual agregando la siguiente palabra
                test_line = current_line + (" " if current_line else "") + word
                # Medimos el ancho en píxeles con la fuente de Pygame
                width, _ = font.size(test_line)
                
                if width <= max_width:
                    current_line = test_line
                else:
                    # Si se pasa del ancho, guardamos la línea actual y empezamos una nueva
                    if current_line:
                        lines.append(current_line)
                    current_line = word
                    
            if current_line:
                lines.append(current_line)
                
        return lines

    def _build_crt(self, size):
        w, h = size

        # Scanlines (una línea oscura cada 3 px) + viñeta en los bordes
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(0, h, 3):
            pygame.draw.line(overlay, (0, 0, 0, 70), (0, y), (w, y))

        ys, xs = np.ogrid[0:h, 0:w]
        d = np.sqrt(((xs - w / 2) / (w / 2)) ** 2 + ((ys - h / 2) / (h / 2)) ** 2) / 1.414
        alpha = (np.clip((d - 0.45) / 0.55, 0, 1) ** 2 * 200).astype(np.uint8)
        vignette = pygame.Surface((w, h), pygame.SRCALPHA)
        arr = pygame.surfarray.pixels_alpha(vignette)
        arr[:] = alpha.T
        del arr
        overlay.blit(vignette, (0, 0))

        # Banda de refresco que baja lentamente
        band = pygame.Surface((w, 40), pygame.SRCALPHA)
        band.fill((255, 255, 255, 10))

        # Capa para el parpadeo
        flicker = pygame.Surface((w, h))
        flicker.fill((255, 255, 255))

        self._crt_cache = (size, overlay, band, flicker)

    def _draw_crt(self, surface):
        size = surface.get_size()
        if self._crt_cache is None or self._crt_cache[0] != size:
            self._build_crt(size)
        _, overlay, band, flicker = self._crt_cache

        # Banda que recorre la pantalla
        y = (pygame.time.get_ticks() // 15) % (size[1] + 40) - 40
        surface.blit(band, (0, y))

        # Parpadeo leve
        flicker.set_alpha(random.randint(0, 9))
        surface.blit(flicker, (0, 0))

        surface.blit(overlay, (0, 0))

    def draw(self, surface):
        if not self.active and not self.is_fading:
            return

        w = surface.get_width()
        h = surface.get_height()

        surface.fill((0, 0, 0))

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

        # 3. Renderizar Nombre
        if not self.ringing and not self.fading_in:
            name_surf = self.font.render(f"{self.character_name}:", True, (255, 255, 100))
            surface.blit(name_surf, (box_x + 25, box_y + 12))

        # --- CAMBIO AQUÍ: Renderizar texto con saltos de línea automáticos y manuales ---
        # Ancho máximo disponible dentro de la caja (restando márgenes izquierdo y derecho)
        max_text_width = box_width - 50 
        
        # Obtenemos la lista de líneas procesadas (respeta \n y corta si se pasa del ancho)
        texto = self.CALLING_TEXT if self.ringing else self.displayed_text
        lineas_procesadas = self.wrap_text(texto, self.font, max_text_width)

        # Dibujamos cada línea renglón por renglón con su respectivo interlineado
        y_offset = box_y + 42  # Posición inicial Y para el primer renglón del texto
        line_spacing = 4       # Espacio extra entre líneas

        for linea in lineas_procesadas:
            text_surf = self.font.render(linea, True, (255, 255, 255))
            surface.blit(text_surf, (box_x + 25, y_offset))
            # Avanzamos el offset vertical según el alto de la fuente + espaciado
            y_offset += self.font.get_linesize() + line_spacing

        # 1. Texto parpadeante "Enter" abajo del bloque azul
        if self.show_enter_prompt and self.is_text_finished and not self.is_fading:
            enter_surf = self.font.render("ENTER", True, (200, 200, 200))
            surface.blit(enter_surf, (box_x + box_width - 100, box_y + box_height + 10))

        # 4. Advertencia de skip en pantalla si se presionó ESC una vez
        if self.skip_warning_active:
            warning_surf = self.font.render("Presiona ESC nuevamente para saltear llamada", True, (255, 255, 255))
            warning_rect = warning_surf.get_rect(center=(w // 2, 50))
            surface.blit(warning_surf, warning_rect)

        self._draw_crt(surface)

        # 2. Superficie de Fade Out (Pantalla negra que se oscurece gradualmente)
        if self.fade_alpha > 0:
            fade_surface = pygame.Surface((w, h))
            fade_surface.fill((0, 0, 0))
            fade_surface.set_alpha(self.fade_alpha)
            surface.blit(fade_surface, (0, 0))