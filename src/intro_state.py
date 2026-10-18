import pygame
import os
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_BG

class IntroState:
    def __init__(self, sequence_script, music_path=None):
        """
        sequence_script: Lista de diccionarios con las secuencias.
        music_path: Ruta al archivo .wav o .mp3 que sonará de fondo en toda la intro.
        """
        self.script = sequence_script
        self.current_seq_index = 0
        self.finished = False

        self.scaled_frames_cache = {} 
        self.current_sequence_frames = []
        self.playback_queue = []
        self.queue_index = 0
        
        self.frame_timer = 0.0
        self.frame_duration = 0.15

        # Reproducir la música global una sola vez al arrancar la intro
        if music_path and os.path.exists(music_path):
            try:
                pygame.mixer.music.load(music_path)
                pygame.mixer.music.play(-1)  # -1 para que se mantenga en bucle durante toda la intro
            except Exception as e:
                print(f"Error al cargar la música global de la intro: {e}")
        
        # Cargar la primera secuencia
        self._load_sequence(self.current_seq_index)

    def _prepare_scaled_frames(self, raw_frames, scale_factor):
        id_frames = id(raw_frames)
        cache_key = (id_frames, scale_factor)
        if cache_key in self.scaled_frames_cache:
            return self.scaled_frames_cache[cache_key]

        scaled = []
        for img in raw_frames:
            w = int(img.get_width() * scale_factor)
            h = int(img.get_height() * scale_factor)
            scaled.append(pygame.transform.scale(img, (w, h)))
        
        self.scaled_frames_cache[cache_key] = scaled
        return scaled

    def _load_sequence(self, index):
        if index >= len(self.script):
            self.finished = True
            pygame.mixer.music.stop()
            return

        data = self.script[index]
        scale = data.get("scale", 2)
        self.frame_duration = data.get("fps", 0.15)
        
        # Escalar frames de esta secuencia
        self.current_sequence_frames = self._prepare_scaled_frames(data["frames"], scale)
        
        # Construir la cola de reproducción exacta
        self.playback_queue = []
        max_len = len(self.current_sequence_frames)

        play_once = data.get("play_once", [])
        for f in play_once:
            if f < max_len:
                self.playback_queue.append(f)

        loop_range = data.get("loop_range", [])
        loop_count = data.get("loop_count", 1)
        if loop_range:
            valid_loop_frames = [f for f in loop_range if f < max_len]
            for _ in range(loop_count):
                self.playback_queue.extend(valid_loop_frames)

        self.queue_index = 0
        self.frame_timer = 0.0

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                # Si el usuario presiona tecla o clic, avanza o salta la intro completa
                self.current_seq_index += 1
                if self.current_seq_index < len(self.script):
                    self._load_sequence(self.current_seq_index)
                else:
                    self.finished = True
                    pygame.mixer.music.stop()

    def update(self, dt):
        if self.finished:
            return

        self.frame_timer += dt
        if self.frame_timer >= self.frame_duration:
            self.frame_timer = 0.0
            self.queue_index += 1
            
            if self.queue_index >= len(self.playback_queue):
                self.current_seq_index += 1
                if self.current_seq_index < len(self.script):
                    self._load_sequence(self.current_seq_index)
                else:
                    self.finished = True
                    pygame.mixer.music.stop()

    def draw(self, surface):
        surface.fill(COLOR_BG)
        
        if self.finished or not self.playback_queue:
            return

        current_frame_idx = self.playback_queue[self.queue_index]
        if current_frame_idx < len(self.current_sequence_frames):
            img = self.current_sequence_frames[current_frame_idx]
            rect = img.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            surface.blit(img, rect)