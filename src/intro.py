import pygame
import sys
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_BG, COLOR_TEXT

class IntroState:
    def __init__(self, frame_list, music_path=None, max_loops=30):
        self.raw_frames = frame_list
        self.current_frame = 0
        self.frame_timer = 0.0
        self.frame_duration = 0.15  # Velocidad por frame.
        self.finished = False
        
        # Control de bucles para los 12 frames.
        self.loop_count = 0
        self.max_loops = max_loops

        # Escalado de los frames.
        self.scale_factor = 2 
        self.scaled_frames = self._prepare_scaled_frames()

        # Nombres equipo.
        self.textos_equipo = [
            "Augusto Karacsany",
            "Lautaro Medina",
            "Valentina Artaza",
            "Ambar Fiszman"
        ]
        
        # Efecto de máquina de escribir.
        self.current_name_index = 0
        self.current_displayed_text = ""
        self.lines_completed = []  # Lista con los nombres que ya terminaron de escribirse.
        self.char_timer = 0.0
        self.char_speed = 0.08  # Segundos por letra.
        self.pause_timer = 0.0
        self.pause_duration = 0.6  # Pausa breve entre el fin de un nombre y el inicio del siguiente.

        # Fuente para los nombres.
        try:
            self.font_names = pygame.font.Font(None, 24)
        except:
            self.font_names = pygame.font.SysFont("Arial", 24)

        if music_path:
            try:
                pygame.mixer.music.load(music_path)
                pygame.mixer.music.play(0)
            except Exception as e:
                print(f"No se pudo cargar la música de intro: {e}")

    def _prepare_scaled_frames(self):
        scaled = []
        for img in self.raw_frames:
            w = int(img.get_width() * self.scale_factor)
            h = int(img.get_height() * self.scale_factor)
            scaled.append(pygame.transform.scale(img, (w, h)))
        return scaled

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                self.finished = True
                pygame.mixer.music.stop()

    def update(self, dt):
        if not self.scaled_frames:
            self.finished = True
            return

        # 1. Actualizar la animación de los 12 frames en bucle ( Independiente del texto. )
        self.frame_timer += dt
        if self.frame_timer >= self.frame_duration:
            self.frame_timer = 0.0
            self.current_frame += 1
            
            if self.current_frame >= len(self.scaled_frames):
                self.current_frame = 0
                self.loop_count += 1
                
                if self.loop_count >= self.max_loops:
                    self.finished = True
                    pygame.mixer.music.stop()

        # 2. Actualizar el efecto de máquina de escribir.
        if self.current_name_index < len(self.textos_equipo):
            target_text = self.textos_equipo[self.current_name_index]
            
            if len(self.current_displayed_text) < len(target_text):
                self.char_timer += dt
                if self.char_timer >= self.char_speed:
                    self.char_timer = 0.0
                    self.current_displayed_text += target_text[len(self.current_displayed_text)]
            else:
                # Terminó este nombre, hacemos una pausa breve y lo pasamos a la lista fija de completados.
                self.pause_timer += dt
                if self.pause_timer >= self.pause_duration:
                    self.pause_timer = 0.0
                    self.lines_completed.append(self.current_displayed_text)
                    self.current_displayed_text = ""
                    self.current_name_index += 1

    def draw(self, surface):
        surface.fill(COLOR_BG)
        
        # Dibujar el frame actual de fondo.
        if self.scaled_frames and self.current_frame < len(self.scaled_frames):
            img = self.scaled_frames[self.current_frame]
            rect = img.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            surface.blit(img, rect)
            
        # DIBUJAR LISTA ABAJO DE "GAME PROGRAMMING"
        start_x = (SCREEN_WIDTH // 8) + 150  # Margen izquierdo dentro del cuadrante. Modificar a conveniencia.
        start_y = SCREEN_HEIGHT // 3 + (SCREEN_HEIGHT // 6)  # Posición vertical base.
        line_spacing = 22  # Espacio vertical entre cada nombre.

        # 1. Dibujar los nombres que ya terminaron de escribirse ( Fijos. )
        for i, line in enumerate(self.lines_completed):
            text_surf = self.font_names.render(line, True, (0, 255, 0)) # Verde.
            surface.blit(text_surf, (start_x, start_y + (i * line_spacing)))

        # 2. Dibujar el nombre que se está escribiendo actualmente justo debajo del último.
        if self.current_name_index < len(self.textos_equipo):
            current_surf = self.font_names.render(self.current_displayed_text, True, (0, 255, 0))
            surface.blit(current_surf, (start_x, start_y + (len(self.lines_completed) * line_spacing)))