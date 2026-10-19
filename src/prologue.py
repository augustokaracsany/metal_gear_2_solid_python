import pygame
import json
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_BG, COLOR_TEXT

class PrologueState:
    def __init__(self, json_path="assets/json/prologue_data.json"):
        with open(json_path, "r", encoding="utf-8") as f:
            cutscene_data = json.load(f)

        self.music_path = cutscene_data.get("background_music")
        self.panels = cutscene_data["panels"]

        self.current_panel_index = 0
        self.finished = False

        if self.music_path:
            try:
                pygame.mixer.music.load(self.music_path)
                pygame.mixer.music.play(-1)
            except Exception as e:
                print(f"Aviso: No se pudo cargar la música del prólogo: {e}")

        # Variables para el texto y la máquina de escribir
        self.full_text = ""
        self.displayed_text = ""
        self.text_index = 0.0
        self.text_speed = 20  # Caracteres por segundo
        self.text_finished = False
        
        # Variable para el retardo inicial antes de escribir el texto en cada panel
        self.panel_start_time = 0
        self.text_delay_duration = 1250

        # Variables para imágenes y fade condicional
        self.current_image = None
        self.previous_image_path = None
        self.fade_alpha = 0
        self.is_fading = False
        self.fade_timer = 0

        # Cargar el primer panel al arrancar
        self.load_panel()

    def load_panel(self):
        if self.current_panel_index < len(self.panels):
            panel = self.panels[self.current_panel_index]
            self.full_text = panel["text"]
            self.displayed_text = ""
            self.text_index = 0.0
            self.text_finished = False
            
            # Reiniciamos el temporizador de retardo para este panel
            self.panel_start_time = pygame.time.get_ticks()

            new_image_path = panel.get("image")

            # Verificamos si la imagen cambió respecto al panel anterior
            if new_image_path != self.previous_image_path:
                if new_image_path:
                    try:
                        raw_image = pygame.image.load(new_image_path).convert_alpha()
                        
                        # --- REESCALADO DE LA IMAGEN ---
                        scale_factor = 3  
                        new_width = raw_image.get_width() * scale_factor
                        new_height = raw_image.get_height() * scale_factor
                        self.current_image = pygame.transform.scale(raw_image, (new_width, new_height))
                        
                    except Exception as e:
                        print(f"No se pudo cargar la imagen {new_image_path}: {e}")
                        self.current_image = None
                else:
                    self.current_image = None
                
                # Activamos el fade solo si cambió de imagen
                self.is_fading = True
                self.fade_alpha = 255
                self.fade_timer = pygame.time.get_ticks()
            
            self.previous_image_path = new_image_path

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                import sys
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    # Si aún está en la pausa inicial de la imagen o escribiendo el texto, salta directo al texto completo
                    elapsed_panel = pygame.time.get_ticks() - self.panel_start_time
                    if elapsed_panel < self.text_delay_duration:
                        self.panel_start_time = 0
                    elif not self.text_finished:
                        self.displayed_text = self.full_text
                        self.text_finished = True
                    else:
                        # Si el texto ya terminó, pasa al siguiente panel
                        self.current_panel_index += 1
                        if self.current_panel_index >= len(self.panels):
                            self.finished = True
                            pygame.mixer.music.fadeout(1000)
                        else:
                            self.load_panel()

    def update(self, dt):
        current_time = pygame.time.get_ticks()
        
        # Verificamos si ya pasó el tiempo de espera inicial de la imagen
        elapsed_panel = current_time - self.panel_start_time
        if elapsed_panel >= self.text_delay_duration:
            # 1. Lógica de la máquina de escribir
            if not self.text_finished:
                self.text_index += self.text_speed * dt
                chars_to_show = int(self.text_index)
                if chars_to_show >= len(self.full_text):
                    self.displayed_text = self.full_text
                    self.text_finished = True
                else:
                    self.displayed_text = self.full_text[:chars_to_show]

        # 2. Lógica del fade condicional cuando cambia la imagen
        if self.is_fading:
            elapsed_fade = current_time - self.fade_timer
            fade_duration = 600  # Duración del fundido en milisegundos (0.6s)
            if elapsed_fade < fade_duration:
                self.fade_alpha = int(255 * (1 - (elapsed_fade / fade_duration)))
            else:
                self.fade_alpha = 0
                self.is_fading = False

    def draw(self, surface):
        surface.fill((10, 5, 5))  # Fondo base oscuro

        w = surface.get_width()
        h = surface.get_height()

        # 1. Dibujar la imagen actual reescalada y centrada si existe
        if self.current_image:
            img_rect = self.current_image.get_rect(center=(w // 2, h // 2))
            surface.blit(self.current_image, img_rect)

        # 2. Capa negra semitransparente para opacar la imagen de fondo
        overlay = pygame.Surface((w, h))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(140)  # Nivel de opacidad (0 a 255; ajusta si lo quieres más claro u oscuro)
        surface.blit(overlay, (0, 0))

        # 3. Dibujar el texto centrado en la pantalla
        font = pygame.font.Font("assets/fonts/PixelOperator8.ttf", 16)
        
        lines = self.displayed_text.split('\n')
        line_height = 30
        total_text_height = len(lines) * line_height
        
        # Calculamos el punto de inicio vertical para que el bloque de texto quede perfectamente centrado
        start_y = (h - total_text_height) // 2
        
        for i, line in enumerate(lines):
            text_surface = font.render(line, True, (220, 220, 200))
            text_rect = text_surface.get_rect(center=(w // 2, start_y + (i * line_height)))
            surface.blit(text_surface, text_rect)

        # --- 4. SÍMBOLO DE FLECHA PARPADEANTE CUANDO TERMINA EL TEXTO ---
        if self.text_finished:
            if (pygame.time.get_ticks() // 300) % 2 == 0:
                arrow_surface = font.render(">", True, (255, 255, 0))
                # Se coloca un poco más abajo del bloque de texto centrado
                arrow_rect = arrow_surface.get_rect(midtop=(w // 2, start_y + total_text_height + 20))
                surface.blit(arrow_surface, arrow_rect)

        # 5. Aplicar la superficie de fundido (fade) de cambio de imagen si está activa
        if self.is_fading and self.fade_alpha > 0:
            fade_surf = pygame.Surface((w, h))
            fade_surf.fill((0, 0, 0))
            fade_surf.set_alpha(self.fade_alpha)
            surface.blit(fade_surf, (0, 0))