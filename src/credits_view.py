import math
import os

import pygame

# ---------------------------------------------------------------------------
# PANTALLA DE CRÉDITOS — Metal Gear 2: Solid Python
# Mismo estilo que la pantalla de controles: fuente PressStart2P, fondo verde
# oscuro con grilla, scanlines y viñeta. A la izquierda las tarjetas del equipo
# (entran deslizándose y se resaltan con el mouse); a la derecha el logo del
# juego y las atribuciones.
# ---------------------------------------------------------------------------

ACCENT = (0, 255, 128)
TEXT = (205, 235, 215)
TEXT_DIM = (105, 150, 122)
DARK = (5, 20, 10)
LINE = (0, 110, 60)
PANEL = (4, 14, 9)
BORDER = (0, 120, 65)

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FONT_PATH = os.path.join(BASE_DIR, "assets", "fonts", "PressStart2P-Regular.ttf")
LOGO_PATH = os.path.join(BASE_DIR, "assets", "menu", "logo.png")

GAME_TITLE = "METAL GEAR 2: SOLID PYTHON"

# Equipo: (nombre, color de la tarjeta). Para agregar o cambiar a alguien, editá esta lista.
TEAM = [
    ("Augusto Abel Karacsany", (0, 255, 128)),
    ("Lautaro Ezequiel Medina", (80, 200, 255)),
    ("Ambar Fiszman Stivelman", (255, 200, 60)),
    ("Valentina Artaza", (170, 140, 255)),
]

# Atribuciones: ("label", texto chico) o ("value", texto destacado)
ATTRIBUTIONS = [
    ("label", "BASADO EN"),
    ("value", "METAL GEAR 2: SOLID SNAKE (MSX2)"),
    ("label", "DE"),
    ("value", "HIDEO KOJIMA & KONAMI"),
]

FOOTER_TEXT = ''


def _font(size):
    try:
        return pygame.font.Font(FONT_PATH, size)
    except (FileNotFoundError, OSError, pygame.error):
        return pygame.font.SysFont("Courier", int(size * 1.4), bold=True)


def _mix(c1, c2, t):
    return tuple(int(a * (1 - t) + b * t) for a, b in zip(c1, c2))


def _ease_out(p):
    p = max(0.0, min(1.0, p))
    return 1 - (1 - p) ** 3


def _wrap(font, text, max_w):
    lines, cur = [], ""
    for word in text.split():
        test = word if not cur else cur + " " + word
        if font.size(test)[0] <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _initials(name):
    parts = name.split()
    return (parts[0][0] + parts[-1][0]).upper() if len(parts) > 1 else parts[0][:2].upper()


class CreditsView:
    def __init__(self):
        self._size = None
        self._last_draw = -100000
        self._open_time = 0
        surf = pygame.display.get_surface()
        self._build(surf.get_size() if surf else (1360, 768))

    # ------------------------------------------------------------------ layout
    def _build(self, size):
        W, H = size
        self._size = size
        m = int(W * 0.05)
        self.margin = m

        self.f_title = _font(max(18, int(H * 0.036)))
        self.f_sec = _font(max(10, int(H * 0.02)))
        self.f_sub = _font(max(8, int(H * 0.013)))
        self.f_name = _font(max(12, int(H * 0.021)))
        self.f_val = _font(max(10, int(H * 0.0175)))
        self.f_desc = _font(max(8, int(H * 0.0125)))
        self.f_badge = _font(max(12, int(H * 0.026)))
        self.f_hint = _font(max(8, int(H * 0.014)))

        top = int(H * 0.23)
        card_h = int(H * 0.13)
        gap = int(H * 0.022)
        left_w = int(W * 0.50)
        col_gap = int(W * 0.03)
        right_x = m + left_w + col_gap
        right_w = W - m - right_x
        total_h = len(TEAM) * card_h + (len(TEAM) - 1) * gap

        self.member_rects = [pygame.Rect(m, top + i * (card_h + gap), left_w, card_h)
                             for i in range(len(TEAM))]
        self.panel = pygame.Rect(right_x, top, right_w, total_h)
        self.left_x, self.left_w = m, left_w
        self._card_fill = pygame.Surface((left_w, card_h), pygame.SRCALPHA)
        self._card_fill.fill((*PANEL, 215))

        self._build_background(size)
        self._build_overlays(size)

    def _section_label(self, bg, text, x, w, y):
        t = self.f_sec.render(text, True, ACCENT)
        bg.blit(t, (x, y))
        ly = y + t.get_height() + 10
        pygame.draw.line(bg, LINE, (x, ly), (x + w, ly), 1)
        pygame.draw.rect(bg, ACCENT, (x, ly - 1, int(w * 0.22), 3))

    def _build_background(self, size):
        W, H = size
        m = self.margin
        bg = pygame.Surface(size)
        for y in range(H):
            k = y / float(H)
            bg.fill((int(3 + 4 * (1 - k)), int(12 + 12 * (1 - k)), int(7 + 6 * (1 - k))), (0, y, W, 1))

        grid = pygame.Surface(size, pygame.SRCALPHA)
        step = max(24, int(H * 0.06))
        for x in range(0, W, step):
            pygame.draw.line(grid, (0, 255, 128, 12), (x, 0), (x, H))
        for y in range(0, H, step):
            pygame.draw.line(grid, (0, 255, 128, 12), (0, y), (W, y))
        bg.blit(grid, (0, 0))

        # Encabezado
        title = self.f_title.render("CRÉDITOS", True, ACCENT)
        ty = int(H * 0.045)
        pygame.draw.rect(bg, ACCENT, (m, ty - 2, 6, title.get_height() + 4))
        bg.blit(title, (m + 22, ty))
        sub = self.f_sub.render(GAME_TITLE, True, TEXT_DIM)
        bg.blit(sub, (m + 22, ty + title.get_height() + 8))
        ly = int(H * 0.138)
        pygame.draw.line(bg, LINE, (m, ly), (W - m, ly), 1)
        pygame.draw.rect(bg, ACCENT, (m, ly - 1, int(W * 0.12), 3))

        # Títulos de sección
        sec_y = int(H * 0.165)
        self._section_label(bg, "EQUIPO DE DESARROLLO", self.left_x, self.left_w, sec_y)
        self._section_label(bg, "ATRIBUCIONES ESPECIALES", self.panel.x, self.panel.w, sec_y)

        self._build_panel(bg)

        # Pie de pantalla (a la altura del botón VOLVER, del lado derecho)
        foot = self.f_hint.render(FOOTER_TEXT, True, TEXT_DIM)
        bg.blit(foot, (W - m - foot.get_width(), H - int(H * 0.065)))
        self.bg = bg

    def _build_panel(self, bg):
        p = self.panel
        pad = max(16, int(p.w * 0.05))

        plate = pygame.Surface(p.size, pygame.SRCALPHA)
        plate.fill((*PANEL, 215))
        bg.blit(plate, p.topleft)
        pygame.draw.rect(bg, BORDER, p, 2)
        c = max(14, p.w // 30)
        for (px, py, dx, dy) in ((p.left, p.top, 1, 1), (p.right - 1, p.top, -1, 1),
                                 (p.left, p.bottom - 1, 1, -1), (p.right - 1, p.bottom - 1, -1, -1)):
            pygame.draw.line(bg, ACCENT, (px, py), (px + dx * c, py), 3)
            pygame.draw.line(bg, ACCENT, (px, py), (px, py + dy * c), 3)

        # Logo (si no está el archivo, se escribe el título del juego)
        logo_bottom = p.y + pad
        raw = None
        if os.path.exists(LOGO_PATH):
            try:
                raw = pygame.image.load(LOGO_PATH).convert()
            except pygame.error:
                raw = None
        if raw is not None:
            lw = p.w - pad * 2
            lh = int(lw * raw.get_height() / raw.get_width())
            max_h = int(p.h * 0.34)
            if lh > max_h:
                lh = max_h
                lw = int(lh * raw.get_width() / raw.get_height())
            logo = pygame.transform.smoothscale(raw, (lw, lh))
            lx = p.centerx - lw // 2
            bg.blit(logo, (lx, logo_bottom + 6), special_flags=pygame.BLEND_ADD)
            logo_bottom += lh + 12
        else:
            for line in ("METAL GEAR 2", "SOLID PYTHON"):
                t = self.f_val.render(line, True, ACCENT)
                bg.blit(t, t.get_rect(midtop=(p.centerx, logo_bottom + 6)))
                logo_bottom += t.get_height() + 12
            logo_bottom += 6

        sep_y = logo_bottom + int(self._size[1] * 0.015)
        pygame.draw.line(bg, LINE, (p.x + pad, sep_y), (p.right - pad, sep_y), 1)
        pygame.draw.rect(bg, ACCENT, (p.x + pad, sep_y - 1, int(p.w * 0.18), 3))

        # Texto de atribuciones, centrado en el espacio que queda
        max_w = p.w - pad * 2
        blocks = []  # (superficie, espacio_después)
        for kind, text in ATTRIBUTIONS:
            if kind == "label":
                blocks.append((self.f_desc.render(text, True, TEXT_DIM), 10))
            else:
                for line in _wrap(self.f_val, text, max_w):
                    blocks.append((self.f_val.render(line, True, TEXT), 8))
                blocks[-1] = (blocks[-1][0], 26)
        total = sum(s.get_height() + after for s, after in blocks) - blocks[-1][1]
        region_top, region_bottom = sep_y + 8, p.bottom - pad
        y = region_top + max(0, (region_bottom - region_top - total) // 2)
        for s, after in blocks:
            bg.blit(s, s.get_rect(midtop=(p.centerx, y)))
            y += s.get_height() + after

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

    # -------------------------------------------------------------------- draw
    def _draw_member(self, surface, i, hovered, progress):
        name, color = TEAM[i]
        r = self.member_rects[i]
        card = pygame.Surface(r.size, pygame.SRCALPHA)
        local = card.get_rect()

        card.blit(self._card_fill, (0, 0))
        if hovered:
            tint = pygame.Surface(r.size, pygame.SRCALPHA)
            tint.fill((*color, 26))
            card.blit(tint, (0, 0))
        pygame.draw.rect(card, color if hovered else BORDER, local, 2)
        pygame.draw.rect(card, color, (0, 0, 6, local.h))

        # Recuadro con las iniciales
        bs = int(local.h * 0.62)
        b = pygame.Rect(24, local.centery - bs // 2, bs, bs)
        pygame.draw.rect(card, _mix(color, PANEL, 0.78), b)
        pygame.draw.rect(card, color, b, 2)
        ini = self.f_badge.render(_initials(name), True, _mix(color, (255, 255, 255), 0.55))
        card.blit(ini, ini.get_rect(center=b.center))

        # Nombre y número de integrante
        n = self.f_name.render(name.upper(), True, TEXT)
        d = self.f_desc.render(f"INTEGRANTE {i + 1:02d}", True, color if hovered else TEXT_DIM)
        total = n.get_height() + 10 + d.get_height()
        tx = b.right + 20
        ty = (local.h - total) // 2
        card.blit(n, (tx, ty))
        card.blit(d, (tx, ty + n.get_height() + 10))

        card.set_alpha(int(255 * progress))
        surface.blit(card, (r.x + int((1 - progress) * 70), r.y))

    def draw(self, surface, mouse_pos=None):
        size = surface.get_size()
        if size != self._size:
            self._build(size)

        now = pygame.time.get_ticks()
        if now - self._last_draw > 250:  # la pantalla se acaba de mostrar
            self._open_time = now
        self._last_draw = now
        t = now - self._open_time
        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()

        surface.blit(self.bg, (0, 0))

        for i, r in enumerate(self.member_rects):
            p = _ease_out((t - 150 - i * 90) / 320.0)
            if p > 0:
                self._draw_member(surface, i, r.collidepoint(mouse_pos), p)

        surface.blit(self.scanlines, (0, 0))
        surface.blit(self.vignette, (0, 0))

        fade = _ease_out(t / 400.0)
        if fade < 1.0:
            self.black.set_alpha(int(255 * (1 - fade)))
            surface.blit(self.black, (0, 0))
