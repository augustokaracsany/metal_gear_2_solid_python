import pygame
import numpy as np


class FlashbackManager:
    FRAME_PATH = "assets/sprites/flashbacks/frame{}.png"   # ajustá la carpeta/nombre
    FRAME_COUNT = 8

    START_DELAY_MS = 1000    # igual que DEATH_FADE_DELAY_MS
    IMAGE_MS = 700           # fase lenta: duración de cada imagen
    FADE_MS = 200            # fundido máximo de cada imagen
    MAX_ALPHA = 230          # ahora el fondo es negro, se puede subir
    ZOOM = 0.12

    # Fase final: las mismas imágenes, cada vez más cortas
    RAPID_FIRST_MS = 260     # duración de la primera imagen de la ráfaga
    RAPID_DECAY = 0.75       # cada imagen dura 75 % de la anterior
    RAPID_MIN_MS = 30

    GRAYSCALE = True
    CONTRAST = 1.15
    GRAIN_ALPHA = 45
    GRAIN_SCALE = 3
    GRAIN_VARIANTS = 4
    GRAIN_FPS = 12
    VIGNETTE_STRENGTH = 210

    def __init__(self):
        self.raw = []
        for i in range(1, self.FRAME_COUNT + 1):
            try:
                img = pygame.image.load(self.FRAME_PATH.format(i)).convert()
                self.raw.append(self._gray(img) if self.GRAYSCALE else img)
            except Exception as e:
                print(f"Aviso: no se pudo cargar flashback{i}.png: {e}")
        self.time_ms = 0.0
        self._size = None
        self._bases = []
        self._grain = []
        self._vignette = None
        self._black = None
        self._dim = (0, 0)
        self._build_schedule()

    def reset(self):
        self.time_ms = 0.0

    def _build_schedule(self):
        """Lista de (inicio_ms, duración_ms, índice_de_imagen)."""
        n = len(self.raw)
        durs = [self.IMAGE_MS] * n
        d = self.RAPID_FIRST_MS
        for _ in range(n):
            durs.append(max(self.RAPID_MIN_MS, int(d)))
            d *= self.RAPID_DECAY
        self._sched = []
        t = self.START_DELAY_MS
        for k, dur in enumerate(durs):
            self._sched.append((t, dur, k % n if n else 0))
            t += dur

    def total_ms(self):
        if not self._sched:
            return self.START_DELAY_MS
        start, dur, _ = self._sched[-1]
        return start + dur

    # ---------- preparación ----------
    def _gray(self, img):
        arr = pygame.surfarray.array3d(img).astype(np.float32)
        g = arr @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
        g = np.clip((g - 128) * self.CONTRAST + 128, 0, 255)
        rgb = np.repeat(g[:, :, None], 3, axis=2).astype(np.uint8)
        return pygame.surfarray.make_surface(rgb)

    def _build(self, size):
        sw, sh = size
        w0, h0 = self.raw[0].get_size()
        k = min(sw / w0, sh / h0)
        dw, dh = int(w0 * k), int(h0 * k)
        self._dim = (dw, dh)

        self._bases = [pygame.transform.scale(img, (dw, dh)) for img in self.raw]

        gw, gh = dw // self.GRAIN_SCALE + 1, dh // self.GRAIN_SCALE + 1
        self._grain = []
        for _ in range(self.GRAIN_VARIANTS):
            g = np.random.randint(0, 256, (gw, gh), dtype=np.uint8)
            s = pygame.Surface((gw, gh), pygame.SRCALPHA)
            rgb = pygame.surfarray.pixels3d(s)
            rgb[:] = g[:, :, None]
            del rgb
            a = pygame.surfarray.pixels_alpha(s)
            a[:] = self.GRAIN_ALPHA
            del a
            self._grain.append(pygame.transform.scale(s, (dw, dh)))

        ys, xs = np.ogrid[0:dh, 0:dw]
        d = np.sqrt(((xs - dw / 2) / (dw / 2)) ** 2 + ((ys - dh / 2) / (dh / 2)) ** 2) / 1.414
        alpha = (np.clip((d - 0.4) / 0.6, 0, 1) ** 2 * self.VIGNETTE_STRENGTH).astype(np.uint8)
        v = pygame.Surface((dw, dh), pygame.SRCALPHA)
        arr = pygame.surfarray.pixels_alpha(v)
        arr[:] = alpha.T
        del arr
        self._vignette = v

        self._black = pygame.Surface(size)
        self._black.fill((0, 0, 0))
        self._size = size

    # ---------- lógica ----------
    def update(self, dt):
        self.time_ms += dt * 1000

    def _current(self):
        """(índice, ms dentro de la imagen, duración) o None si no hay imagen en este instante."""
        for start, dur, idx in self._sched:
            if start <= self.time_ms < start + dur:
                return idx, self.time_ms - start, dur
        return None

    # ---------- dibujo ----------
    def draw(self, surface):
        if not self.raw or self.time_ms < self.START_DELAY_MS:
            return

        if self._size != surface.get_size():
            self._build(surface.get_size())

        # Fondo negro que tapa el gameplay (entra con un fundido corto y se queda).
        cover = min(1.0, (self.time_ms - self.START_DELAY_MS) / self.FADE_MS)
        self._black.set_alpha(int(255 * cover))
        surface.blit(self._black, (0, 0))

        cur = self._current()
        if cur is None:
            return
        idx, t, dur = cur
        dw, dh = self._dim

        z = 1.0 + self.ZOOM * (t / dur)
        cw, ch = int(dw / z), int(dh / z)
        crop = pygame.Rect((dw - cw) // 2, (dh - ch) // 2, cw, ch)
        frame = pygame.transform.scale(self._bases[idx].subsurface(crop), (dw, dh))

        frame.blit(self._grain[int(self.time_ms / 1000 * self.GRAIN_FPS) % len(self._grain)], (0, 0))
        frame.blit(self._vignette, (0, 0))

        # El fundido se acorta en las imágenes rápidas.
        fade_ms = max(1.0, min(self.FADE_MS, dur / 3))
        fade = min(1.0, t / fade_ms, (dur - t) / fade_ms)
        frame.set_alpha(int(self.MAX_ALPHA * max(0.0, fade)))

        surface.blit(frame, frame.get_rect(center=surface.get_rect().center))