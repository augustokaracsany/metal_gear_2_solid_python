import pygame

class FoxScreenManager():
    FADE_DURATION = 500 # en ms
    ANIMATION_DELAY = 1500 # en ms
    ENDING_DELAY = 1500 # en ms
    SPRITE_FRAME_INDEX = 0.05 # en segundos

    FRAME_PATH = "assets/sprites/fox/zorro{}.png"
    FRAME_COUNT = 12

    FADE_IN, DELAY, ANIMATING, ENDING, FADE_OUT = range(5)

    def __init__(self):
        self.frames = []
        for i in range(1, self.FRAME_COUNT + 1):
            try:
                self.frames.append(pygame.image.load(self.FRAME_PATH.format(i)).convert_alpha())
            except Exception as e:
                print(f"Aviso: no se pudo cargar zorro{i}.png: {e}")
        self._cache = {}
        self.active = False
        self.phase = self.FADE_IN
        self.timer = 0.0           # segundos dentro de la fase actual
        self.frame_index = 0
        self.on_covered = None

    def start(self, on_covered=None):
        """on_covered se ejecuta una vez, cuando la pantalla ya tapa todo (acá se carga el nivel)."""
        if self.active:
            return
        self.active = True
        self.phase = self.FADE_IN
        self.timer = 0.0
        self.frame_index = 0
        self.on_covered = on_covered

    def update(self, dt):
        if not self.active:
            return
        self.timer += dt

        if self.phase == self.FADE_IN:
            if self.timer >= self.FADE_DURATION / 1000:
                if self.on_covered:
                    self.on_covered()
                    self.on_covered = None
                self._next(self.DELAY)

        elif self.phase == self.DELAY:
            if self.timer >= self.ANIMATION_DELAY / 1000:
                self._next(self.ANIMATING)

        elif self.phase == self.ANIMATING:
            self.frame_index = int(self.timer / self.SPRITE_FRAME_INDEX)
            if self.frame_index >= len(self.frames) - 1:
                self.frame_index = len(self.frames) - 1
                # termina cuando el último frame cumplió su tiempo
                if self.timer >= len(self.frames) * self.SPRITE_FRAME_INDEX:
                    self._next(self.ENDING)

        elif self.phase == self.ENDING:
            if self.timer >= self.ENDING_DELAY / 1000:
                self._next(self.FADE_OUT)

        elif self.phase == self.FADE_OUT:
            if self.timer >= self.FADE_DURATION / 1000:
                self.active = False

    def _next(self, phase):
        self.phase = phase
        self.timer = 0.0

    def _alpha(self):
        fade = self.FADE_DURATION / 1000
        if self.phase == self.FADE_IN:
            return int(255 * min(1.0, self.timer / fade))
        if self.phase == self.FADE_OUT:
            return int(255 * max(0.0, 1 - self.timer / fade))
        return 255

    def _scaled(self, index, size):
        key = (index, size)
        if key not in self._cache:
            img = self.frames[index]
            w, h = img.get_size()
            k = min(size[0] / w, size[1] / h)
            scaled = pygame.transform.scale(img, (int(w * k), int(h * k)))
            canvas = pygame.Surface(size, pygame.SRCALPHA)   # transparente, sin negro
            canvas.blit(scaled, scaled.get_rect(center=(size[0] // 2, size[1] // 2)))
            self._cache[key] = canvas
        return self._cache[key]

    def draw(self, surface):
        if not self.active or not self.frames:
            return
        index = self.frame_index if self.phase == self.ANIMATING else 0
        if self.phase in (self.ENDING, self.FADE_OUT):
            index = len(self.frames) - 1

        alpha = self._alpha()

        # Fondo azul con el mismo fade que el zorro
        bg = pygame.Surface(surface.get_size())
        bg.fill((0, 72, 218))
        bg.set_alpha(alpha)
        surface.blit(bg, (0, 0))

        canvas = self._scaled(index, surface.get_size())
        canvas.set_alpha(alpha)
        surface.blit(canvas, (0, 0))