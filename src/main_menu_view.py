import math
import os

import pygame

try:  # sonidos del menú (los mismos de la pausa); si falta el módulo, queda en silencio
    from src.menu import play_sound
except Exception:
    def play_sound(name):
        pass

# ---------------------------------------------------------------------------
# MENÚ PRINCIPAL — Metal Gear 2: Solid Python
# Vista del menú principal (imagen de Snake a la izquierda, logo con brillo
# pulsante + opciones a la derecha). Se adapta al tamaño real de la pantalla
# (ventana o pantalla completa) y se maneja con teclado y mouse.
# ---------------------------------------------------------------------------

ACCENT = (0, 255, 128)
ACCENT_SOFT = (0, 220, 110)
TEXT = (205, 235, 215)
TEXT_DIM = (105, 150, 122)
DARK = (5, 20, 10)

KEYS_UP = (pygame.K_UP, pygame.K_w)
KEYS_DOWN = (pygame.K_DOWN, pygame.K_s)
KEYS_OK = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FONT_PATH = os.path.join(BASE_DIR, "assets", "fonts", "PressStart2P-Regular.ttf")

# Imágenes (se prueba en orden; la primera que exista se usa)
LOGO_PATHS = [
    os.path.join(BASE_DIR, "assets", "menu", "logo.png"),
]
SNAKE_PATHS = [
    os.path.join(BASE_DIR, "assets", "menu", "snake.png"),
]
BACKGROUND_PATHS = [
    os.path.join(BASE_DIR, "assets", "menu", "background.png"),
]

# Qué mostrar a la izquierda:
#   "background" -> ilustración grande (assets/menu/background.png)
#   "snake"      -> retrato pixel art del juego original (assets/menu/snake.png)
# Si falta el archivo elegido, se usa el otro; y si faltan los dos, el sprite de Snake.
MENU_ART = "background"
ART_FOCUS_X = 0.12   # qué parte queda visible si se recorta a lo ancho (0 = izquierda, 1 = derecha)
ART_FOCUS_Y = 0.45   # qué parte queda visible si se recorta a lo alto (0 = arriba, 1 = abajo)
ART_DIM = 1.0        # brillo de la ilustración (1 = original, menor = más oscura)
SPRITE_FALLBACK = os.path.join(BASE_DIR, "assets", "sprites", "solid_python", "stand_down.png")

# Efecto del logo: respiración suave de brillo + halo ajustado + destello que lo recorre
GLOW_PERIOD_S = 3.4   # duración de un ciclo de "respiración" del brillo
GLOW_GAIN_MIN = 0.90  # brillo del logo en el punto más tenue (1 = el de la imagen)
GLOW_GAIN_MAX = 1.55  # brillo del logo en el punto más intenso
HALO_MIN = 0.10       # intensidad del halo (0 a 1) en el punto más tenue
HALO_MAX = 0.38       # intensidad del halo en el punto más intenso
SHINE_FIRST_S = 1.2   # cuánto tarda en pasar el primer destello al abrir el menú
SHINE_EVERY_S = 5.0   # cada cuántos segundos pasa un destello
SHINE_DURATION_S = 1.0  # cuánto dura el recorrido del destello
SHINE_POWER = 0.9     # intensidad del destello (0 a 1)
GLOW_LEVELS = 24      # pasos de brillo precalculados


def _font(size):
    try:
        return pygame.font.Font(FONT_PATH, size)
    except (FileNotFoundError, OSError, pygame.error):
        return pygame.font.SysFont("Courier", int(size * 1.4), bold=True)


def _ease_out(p):
    p = max(0.0, min(1.0, p))
    return 1 - (1 - p) ** 3


def _first_image(paths, alpha=False):
    for path in paths:
        if os.path.exists(path):
            try:
                img = pygame.image.load(path)
                return img.convert_alpha() if alpha else img.convert()
            except pygame.error:
                continue
    return None


class MainMenuView:
    def __init__(self, labels):
        self.labels = list(labels)
        self.selected = 0

        self._logo_raw = _first_image(LOGO_PATHS)
        self._snake_raw = _first_image(SNAKE_PATHS, alpha=True)
        self._bg_raw = _first_image(BACKGROUND_PATHS)
        self._sprite_raw = None
        if self._snake_raw is None and self._bg_raw is None:
            self._sprite_raw = _first_image([SPRITE_FALLBACK], alpha=True)

        self._size = None
        self._last_draw = -100000
        self._open_time = 0
        self._hl_y = None
        self._logo_cache = {}
        self._glow_cache = {}

        surf = pygame.display.get_surface()
        self._build(surf.get_size() if surf else (1360, 768))

    # ------------------------------------------------------------------ layout
    def _build(self, size):
        W, H = size
        self._size = size
        self._logo_cache = {}
        self._glow_cache = {}
        self._hl_y = None

        self.panel_x = int(W * 0.58)
        self.panel_right = W - int(W * 0.04)
        self.panel_w = self.panel_right - self.panel_x
        inner = int(self.panel_w * 0.05)

        self.font_opt = _font(max(12, int(H * 0.026)))
        self.font_hint = _font(max(8, int(H * 0.014)))

        # --- Logo ---
        self.logo = None
        self.logo_glow = None
        self.logo_pad = 0
        self.logo_mask = None
        self.logo_band = None
        self._shine_tmp = None
        if self._logo_raw:
            lw = self.panel_w - inner * 2
            lh = int(lw * self._logo_raw.get_height() / self._logo_raw.get_width())
            max_h = int(H * 0.34)
            if lh > max_h:
                lh = max_h
                lw = int(lh * self._logo_raw.get_width() / self._logo_raw.get_height())
            self.logo = pygame.transform.smoothscale(self._logo_raw, (lw, lh))
            self.logo_rect = self.logo.get_rect(midtop=(self.panel_x + self.panel_w // 2, int(H * 0.07)))

            # Halo ajustado: un desenfoque corto, para que el logo siga nítido
            pad = max(10, int(H * 0.02))
            self.logo_pad = pad
            canvas = pygame.Surface((lw + pad * 2, lh + pad * 2))
            canvas.fill((0, 0, 0))
            canvas.blit(self.logo, (pad, pad))
            small = pygame.transform.smoothscale(canvas, (max(4, canvas.get_width() // 4), max(4, canvas.get_height() // 4)))
            glow = pygame.transform.smoothscale(small, canvas.get_size())
            glow.blit(glow, (0, 0), special_flags=pygame.BLEND_ADD)
            self.logo_glow = glow

            # Máscara blanca con la forma del logo (el destello solo se ve sobre las letras)
            try:
                bg_mask = pygame.mask.from_threshold(self.logo, (0, 0, 0, 255), (28, 28, 28, 255))
                bg_mask.invert()
                self.logo_mask = bg_mask.to_surface(setcolor=(255, 255, 255, 255),
                                                    unsetcolor=(0, 0, 0, 255)).convert()
            except Exception:
                self.logo_mask = self.logo.copy()

            # Banda de luz inclinada que recorre el logo
            band_w = max(12, int(lw * 0.16))
            slant = int(lh * 0.35)
            band = pygame.Surface((band_w + slant, lh))
            band.fill((0, 0, 0))
            row = pygame.Surface((band_w, 1))
            for x in range(band_w):
                v = int(255 * math.sin(math.pi * x / float(band_w)) ** 2)
                row.set_at((x, 0), (v, v, v))
            for y in range(lh):
                band.blit(row, (int(slant * (1 - y / float(lh))), y))
            self.logo_band = band
            self._shine_tmp = pygame.Surface((lw, lh))
        else:
            self.logo_rect = pygame.Rect(self.panel_x, int(H * 0.07), self.panel_w, int(H * 0.2))

        # --- Opciones ---
        box_h = int(H * 0.075)
        gap = int(H * 0.02)
        start_y = self.logo_rect.bottom + int(H * 0.07)
        self.rects = []
        for i in range(len(self.labels)):
            self.rects.append(pygame.Rect(self.panel_x + inner, start_y + i * (box_h + gap),
                                          self.panel_w - inner * 2, box_h))
        self.box_h = box_h
        self.step = box_h + gap

        self._box_fill = pygame.Surface((self.rects[0].w, box_h), pygame.SRCALPHA)
        self._box_fill.fill((4, 14, 9, 215))

        self._build_background(size, inner)
        self._build_overlays(size)

    def _build_background(self, size, inner):
        W, H = size
        bg = pygame.Surface(size)
        for y in range(H):
            k = y / float(H)
            bg.fill((int(3 + 4 * (1 - k)), int(12 + 12 * (1 - k)), int(7 + 6 * (1 - k))), (0, y, W, 1))

        art_w = self.panel_x
        bg.set_clip(pygame.Rect(0, 0, art_w, H))
        self._draw_art(bg, art_w, H)
        bg.set_clip(None)

        # Desvanecer el borde derecho de la imagen hacia el panel
        fade_w = max(40, int(art_w * 0.22))
        fade = pygame.Surface((fade_w, H), pygame.SRCALPHA)
        for x in range(fade_w):
            a = int(255 * (x / float(fade_w)) ** 1.6)
            pygame.draw.line(fade, (3, 12, 7, a), (x, 0), (x, H))
        bg.blit(fade, (art_w - fade_w, 0))

        # Panel derecho
        panel = pygame.Surface((W - self.panel_x, H), pygame.SRCALPHA)
        panel.fill((3, 11, 7, 235))
        bg.blit(panel, (self.panel_x, 0))
        pygame.draw.line(bg, (0, 110, 60), (self.panel_x, 0), (self.panel_x, H), 2)
        pygame.draw.rect(bg, ACCENT, (self.panel_x - 1, int(H * 0.07), 4, int(H * 0.06)))

        # Línea separadora entre el logo y las opciones
        ly = self.logo_rect.bottom + int(H * 0.035)
        pygame.draw.line(bg, (0, 110, 60), (self.panel_x + inner, ly), (self.panel_right - inner, ly), 1)
        pygame.draw.rect(bg, ACCENT, (self.panel_x + inner, ly - 1, int(self.panel_w * 0.22), 3))
        self.bg = bg

    def _draw_art(self, bg, art_w, H):
        use_background = self._bg_raw is not None and (MENU_ART == "background" or self._snake_raw is None)
        if use_background:
            self._draw_cover(bg, self._bg_raw, art_w, H)
        else:
            self._draw_portrait(bg, art_w, H)

    def _draw_cover(self, bg, raw, art_w, H):
        """Ilustración a pantalla completa en la zona izquierda (recorta lo que sobre)."""
        scale = max(H / float(raw.get_height()), art_w / float(raw.get_width()))
        w, h = int(raw.get_width() * scale) + 1, int(raw.get_height() * scale) + 1
        img = pygame.transform.smoothscale(raw, (w, h))
        x = -int((w - art_w) * ART_FOCUS_X) if w > art_w else (art_w - w) // 2
        y = -int((h - H) * ART_FOCUS_Y) if h > H else (H - h) // 2
        bg.blit(img, (x, y))
        if ART_DIM < 1.0:
            dim = pygame.Surface((art_w, H))
            dim.fill((0, 0, 0))
            dim.set_alpha(int(255 * (1 - ART_DIM)))
            bg.blit(dim, (0, 0))

    def _draw_portrait(self, bg, art_w, H):
        """Retrato pixel art (o sprite) centrado sobre un resplandor y una grilla."""
        grid = pygame.Surface((art_w, H), pygame.SRCALPHA)
        step = max(24, int(H * 0.06))
        for x in range(0, art_w, step):
            pygame.draw.line(grid, (0, 255, 128, 14), (x, 0), (x, H))
        for y in range(0, H, step):
            pygame.draw.line(grid, (0, 255, 128, 14), (0, y), (art_w, y))
        bg.blit(grid, (0, 0))

        cx, cy = art_w // 2, int(H * 0.52)
        radius = int(min(art_w, H) * 0.48)
        small = pygame.Surface((64, 64), pygame.SRCALPHA)
        for yy in range(64):
            for xx in range(64):
                d = min(1.0, math.hypot(xx - 31.5, yy - 31.5) / 32.0)
                small.set_at((xx, yy), (0, 255, 128, int(70 * (1 - d) ** 2)))
        bg.blit(pygame.transform.smoothscale(small, (radius * 2, radius * 2)), (cx - radius, cy - radius))

        src = self._snake_raw if self._snake_raw is not None else self._sprite_raw
        if src is None:
            return
        # Escala entera (sin suavizar) para conservar los píxeles nítidos
        factor = max(1, int(H * (0.72 if src is self._snake_raw else 0.55) / src.get_height()))
        big = pygame.transform.scale(src, (src.get_width() * factor, src.get_height() * factor))
        rect = big.get_rect(center=(cx, cy))
        bg.blit(big, rect)

        if src is self._snake_raw:
            # Marco estilo HUD alrededor del retrato
            frame = rect.inflate(28, 28)
            size = max(14, frame.w // 8)
            for (px, py, dx, dy) in ((frame.left, frame.top, 1, 1), (frame.right - 1, frame.top, -1, 1),
                                     (frame.left, frame.bottom - 1, 1, -1), (frame.right - 1, frame.bottom - 1, -1, -1)):
                pygame.draw.line(bg, ACCENT, (px, py), (px + dx * size, py), 3)
                pygame.draw.line(bg, ACCENT, (px, py), (px, py + dy * size), 3)

    def _build_overlays(self, size):
        W, H = size
        self.scanlines = pygame.Surface(size, pygame.SRCALPHA)
        for y in range(0, H, 4):
            pygame.draw.line(self.scanlines, (0, 0, 0, 40), (0, y), (W, y))

        sw, sh = 48, 27
        vig = pygame.Surface((sw, sh), pygame.SRCALPHA)
        for yy in range(sh):
            for xx in range(sw):
                dx = (xx / (sw - 1.0)) * 2 - 1
                dy = (yy / (sh - 1.0)) * 2 - 1
                d = min(1.0, math.sqrt(dx * dx + dy * dy) / 1.25)
                vig.set_at((xx, yy), (0, 0, 0, int(150 * d ** 2.2)))
        self.vignette = pygame.transform.smoothscale(vig, size)

        self.black = pygame.Surface(size)
        self.black.fill((0, 0, 0))

    # ------------------------------------------------------------------- input
    def handle_event(self, event):
        """Devuelve el índice de la opción elegida, o None."""
        n = len(self.labels)
        if event.type == pygame.KEYDOWN:
            if event.key in KEYS_UP:
                self._set_selected((self.selected - 1) % n)
            elif event.key in KEYS_DOWN:
                self._set_selected((self.selected + 1) % n)
            elif event.key in KEYS_OK:
                play_sound("select")
                return self.selected
        elif event.type == pygame.MOUSEMOTION:
            for i, r in enumerate(self.rects):
                if r.collidepoint(event.pos):
                    self._set_selected(i)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.rects):
                if r.collidepoint(event.pos):
                    self.selected = i
                    play_sound("select")
                    return i
        return None

    def _set_selected(self, index):
        if index != self.selected:
            self.selected = index
            play_sound("select")

    # -------------------------------------------------------------------- draw
    def _logo_frame(self, level):
        frame = self._logo_cache.get(level)
        if frame is None:
            k = level / float(GLOW_LEVELS - 1)
            gain = GLOW_GAIN_MIN + (GLOW_GAIN_MAX - GLOW_GAIN_MIN) * k
            frame = self.logo.copy()
            v = int(255 * min(1.0, gain))
            frame.fill((v, v, v), special_flags=pygame.BLEND_MULT)
            if gain > 1.0:  # por encima de 1 se suma una copia más tenue de sí mismo
                extra = self.logo.copy()
                v2 = int(255 * (gain - 1.0))
                extra.fill((v2, v2, v2), special_flags=pygame.BLEND_MULT)
                frame.blit(extra, (0, 0), special_flags=pygame.BLEND_ADD)
            self._logo_cache[level] = frame
        return frame

    def _glow_frame(self, level):
        frame = self._glow_cache.get(level)
        if frame is None:
            k = level / float(GLOW_LEVELS - 1)
            v = int(255 * (HALO_MIN + (HALO_MAX - HALO_MIN) * k))
            frame = self.logo_glow.copy()
            frame.fill((v, v, v), special_flags=pygame.BLEND_MULT)
            self._glow_cache[level] = frame
        return frame

    def _draw_shine(self, surface, t):
        """Destello inclinado que recorre las letras de izquierda a derecha cada tanto."""
        secs = t / 1000.0 - SHINE_FIRST_S
        if secs < 0:
            return
        p = (secs % SHINE_EVERY_S) / SHINE_DURATION_S
        if p >= 1.0:
            return
        eased = p * p * (3 - 2 * p)
        lw = self.logo.get_width()
        bw = self.logo_band.get_width()
        x = int(-bw + (lw + bw) * eased)

        tmp = self._shine_tmp
        tmp.fill((0, 0, 0))
        tmp.blit(self.logo_band, (x, 0), special_flags=pygame.BLEND_ADD)
        tmp.blit(self.logo_mask, (0, 0), special_flags=pygame.BLEND_MULT)
        if SHINE_POWER < 1.0:
            v = int(255 * SHINE_POWER)
            tmp.fill((v, v, v), special_flags=pygame.BLEND_MULT)
        surface.blit(tmp, self.logo_rect.topleft, special_flags=pygame.BLEND_ADD)

    def draw(self, surface):
        size = surface.get_size()
        if size != self._size:
            self._build(size)
        W, H = size

        now = pygame.time.get_ticks()
        if now - self._last_draw > 250:  # el menú se acaba de mostrar
            self._open_time = now
            self._hl_y = None
        self._last_draw = now
        t = now - self._open_time

        surface.blit(self.bg, (0, 0))

        # --- Logo que se ilumina y se disilumina ---
        if self.logo is not None:
            phase = 0.5 + 0.5 * math.sin(now / 1000.0 * (2 * math.pi / GLOW_PERIOD_S) - math.pi / 2)
            level = int(round(phase * (GLOW_LEVELS - 1)))
            surface.blit(self._glow_frame(level),
                         (self.logo_rect.x - self.logo_pad, self.logo_rect.y - self.logo_pad),
                         special_flags=pygame.BLEND_ADD)
            surface.blit(self._logo_frame(level), self.logo_rect.topleft, special_flags=pygame.BLEND_ADD)
            self._draw_shine(surface, t)
        else:
            title = self.font_opt.render("METAL GEAR 2: SOLID PYTHON", True, ACCENT)
            surface.blit(title, title.get_rect(center=self.logo_rect.center))

        self._draw_options(surface, t, now)
        self._draw_hint(surface)

        if self.logo is not None:
            lr = self.logo_rect.inflate(self.logo_pad * 2, self.logo_pad * 2).clip(pygame.Rect(0, 0, W, H))
            for area in (pygame.Rect(0, 0, W, lr.top),
                         pygame.Rect(0, lr.bottom, W, H - lr.bottom),
                         pygame.Rect(0, lr.top, lr.left, lr.height),
                         pygame.Rect(lr.right, lr.top, W - lr.right, lr.height)):
                if area.w > 0 and area.h > 0:
                    surface.blit(self.scanlines, area.topleft, area)
        else:
            surface.blit(self.scanlines, (0, 0))
        surface.blit(self.vignette, (0, 0))

        fade = _ease_out(t / 500.0)
        if fade < 1.0:
            self.black.set_alpha(int(255 * (1 - fade)))
            surface.blit(self.black, (0, 0))

    def _draw_options(self, surface, t, now):
        # Barra de selección que se desliza suave hasta la opción elegida
        target = self.rects[self.selected].y
        if self._hl_y is None:
            self._hl_y = float(target)
        else:
            self._hl_y += (target - self._hl_y) * 0.3

        progress = [_ease_out((t - 250 - i * 80) / 320.0) for i in range(len(self.rects))]

        # Cajas (contorno oscuro) entrando desde la derecha
        for i, rect in enumerate(self.rects):
            p = progress[i]
            if p <= 0:
                continue
            r = rect.move(int((1 - p) * 70), 0)
            self._box_fill.set_alpha(int(255 * p))
            surface.blit(self._box_fill, r.topleft)
            pygame.draw.rect(surface, (0, 120, 65), r, 2)

        # Resaltado de la opción activa
        sel_p = progress[self.selected]
        if sel_p >= 1.0:
            self._draw_highlight(surface, rect_x=self.rects[self.selected].x, y=self._hl_y, now=now)

        # Textos
        for i, rect in enumerate(self.rects):
            p = progress[i]
            if p <= 0:
                continue
            near = (sel_p >= 1.0) and abs(self._hl_y - rect.y) < self.step * 0.5
            txt = self.font_opt.render(self.labels[i], True, DARK if near else TEXT)
            txt.set_alpha(int(255 * p))
            off = int((1 - p) * 70)
            surface.blit(txt, (rect.x + int(rect.w * 0.05) + off, rect.centery - txt.get_height() // 2))

    def _draw_highlight(self, surface, rect_x, y, now):
        x, w, h = rect_x, self.rects[0].w, self.box_h
        y = int(y)
        pulse = 0.5 + 0.5 * math.sin(now / 260.0)

        glow = pygame.Surface((w + 24, h + 24), pygame.SRCALPHA)
        pygame.draw.rect(glow, (0, 255, 128, int(26 + 22 * pulse)), glow.get_rect(), border_radius=10)
        surface.blit(glow, (x - 12, y - 12))

        cut = max(8, h // 4)
        pts = [(x, y), (x + w, y), (x + w, y + h - cut), (x + w - cut, y + h), (x, y + h)]
        pygame.draw.polygon(surface, ACCENT_SOFT, pts)
        pygame.draw.rect(surface, (190, 255, 220), (x, y, 6, h))

        ax = x + w - int(h * 0.8) + int(4 * pulse)
        cy = y + h // 2
        s = max(6, h // 7)
        pygame.draw.polygon(surface, DARK, [(ax, cy - s), (ax + s * 3 // 2, cy), (ax, cy + s)])

    def _draw_hint(self, surface):
        hint = self.font_hint.render("W/S MOVER  |  ENTER SELECCIONAR", True, TEXT_DIM)
        surface.blit(hint, (self.panel_right - hint.get_width(), self._size[1] - int(self._size[1] * 0.07)))