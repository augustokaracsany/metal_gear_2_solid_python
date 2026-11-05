import pygame
import numpy as np


class FlashbackManager:
    FRAME_PATH = "assets/sprites/flashbacks/frame{}.png"   # ajustá la carpeta/nombre
    FRAME_COUNT = 8

    START_DELAY_MS = 1000    # igual que DEATH_FADE_DELAY_MS
    IMAGE_MS = 600           # fase lenta: duración de cada imagen
    FADE_MS = 200            # fundido máximo de cada imagen
    MAX_ALPHA = 230          # ahora el fondo es negro, se puede subir
    ZOOM = 0.07
    GAP_MS = 100             # pantalla del juego (Snake muerto) entre imágenes lentas
    FLASH_MS = 20            # duración del flash blanco
    FLASH_ALPHA = 200        # 0-255: intensidad del flash
    RAPID_FLASH = True       # también un flash mínimo entre imágenes de la ráfaga

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
        self._white = None
        self._dim = (0, 0)
        self._build_schedule()

    def reset(self):
        self.time_ms = 0.0

    def _build_schedule(self):
        """Lista de (inicio_ms, duración_ms, índice_de_imagen, tipo).
        tipos: "slow" (imagen), "gap" (se ve el juego), "rapid0"/"rapid" (ráfaga final)."""
        n = len(self.raw)
        self._sched = []
        t = self.START_DELAY_MS
        for k in range(n):
            self._sched.append((t, self.IMAGE_MS, k, "slow"))
            t += self.IMAGE_MS
            self._sched.append((t, self.GAP_MS, k, "gap"))
            t += self.GAP_MS
        d = self.RAPID_FIRST_MS
        for k in range(n):
            dur = max(self.RAPID_MIN_MS, int(d))
            self._sched.append((t, dur, k, "rapid0" if k == 0 else "rapid"))
            t += dur
            d *= self.RAPID_DECAY

    def total_ms(self):
        if not self._sched:
            return self.START_DELAY_MS
        start, dur, _, _ = self._sched[-1]
        return start + dur

    def _segment(self):
        for seg in self._sched:
            if seg[0] <= self.time_ms < seg[0] + seg[1]:
                return seg
        return None

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
        self._white = pygame.Surface(size)
        self._white.fill((255, 255, 255))
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

        seg = self._segment()
        if seg is None:                       # la secuencia terminó: queda negro
            self._black.set_alpha(255)
            surface.blit(self._black, (0, 0))
            return

        start, dur, idx, kind = seg
        t = self.time_ms - start

        if kind != "gap":                     # en "gap" no se tapa: se ve a Snake muerto
            cover = min(1.0, t / self.FADE_MS) if seg is self._sched[0] else 1.0
            self._black.set_alpha(int(255 * cover))
            surface.blit(self._black, (0, 0))

            dw, dh = self._dim
            if self.ZOOM > 0:
                z = 1.0 + self.ZOOM * (t / dur)
                cw, ch = int(dw / z), int(dh / z)
                crop = pygame.Rect((dw - cw) // 2, (dh - ch) // 2, cw, ch)
                frame = pygame.transform.scale(self._bases[idx].subsurface(crop), (dw, dh))
            else:
                frame = self._bases[idx].copy()

            frame.blit(self._grain[int(self.time_ms / 1000 * self.GRAIN_FPS) % len(self._grain)], (0, 0))
            frame.blit(self._vignette, (0, 0))

            fade_ms = max(1.0, min(self.FADE_MS, dur / 3))
            fade = min(1.0, t / fade_ms, (dur - t) / fade_ms)
            frame.set_alpha(int(self.MAX_ALPHA * max(0.0, fade)))
            surface.blit(frame, frame.get_rect(center=surface.get_rect().center))

        # Flash blanco al inicio del segmento que sigue a cada imagen.
        flash_ms = 0
        if kind == "gap":
            flash_ms = self.FLASH_MS
        elif kind == "rapid" and self.RAPID_FLASH:
            flash_ms = min(self.FLASH_MS, dur * 0.5)
        if flash_ms and t < flash_ms:
            self._white.set_alpha(int(self.FLASH_ALPHA * (1 - t / flash_ms)))
            surface.blit(self._white, (0, 0))