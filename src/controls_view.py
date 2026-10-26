import math
import os

import pygame

# ---------------------------------------------------------------------------
# PANTALLA DE CONTROLES — Metal Gear 2: Solid Python
# Teclado ilustrado con las teclas del juego resaltadas + una tarjeta por
# acción (numerada y del mismo color que su tecla). Mismo estilo retro que el
# menú principal. Si pasás el mouse sobre una tarjeta o una tecla, se resalta
# esa acción y las demás se atenúan.
# ---------------------------------------------------------------------------

ACCENT = (0, 255, 128)
TEXT = (205, 235, 215)
TEXT_DIM = (105, 150, 122)
DARK = (5, 20, 10)
LINE = (0, 110, 60)
PANEL = (4, 14, 9)

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FONT_PATH = os.path.join(BASE_DIR, "assets", "fonts", "PressStart2P-Regular.ttf")

# Colores por acción
C_MOVE = (0, 255, 128)
C_SHOOT = (255, 90, 90)
C_CROUCH = (80, 200, 255)
C_PRONE = (170, 140, 255)
C_CQC = (255, 200, 60)
C_PAUSE = (200, 215, 205)

# Para agregar o cambiar una acción: editá esta lista y KEY_ACTION más abajo.
ACTIONS = [
    {"name": "MOVIMIENTO",      "desc": "Mover a Snake",            "color": C_MOVE,
     "caps": ["W", "A", "S", "D", "/", "LEFT", "UP", "DOWN", "RIGHT"]},
    {"name": "DISPARAR",        "desc": "Disparar el arma",         "color": C_SHOOT,
     "caps": ["ESPACIO"]},
    {"name": "AGACHARSE",       "desc": "Agacharse / levantarse",   "color": C_CROUCH,
     "caps": ["C"]},
    {"name": "CUERPO A TIERRA", "desc": "Arrastrarse por el suelo", "color": C_PRONE,
     "caps": ["CTRL"]},
    {"name": "ACCIÓN CQC",      "desc": "Golpe cuerpo a cuerpo",    "color": C_CQC,
     "caps": ["E"]},
    {"name": "PAUSA / SALIR",   "desc": "Pausa durante la partida", "color": C_PAUSE,
     "caps": ["ESC"]},
]

# Qué tecla del teclado dibujado pertenece a qué acción (índice de ACTIONS)
KEY_ACTION = {
    "W": 0, "A": 0, "S": 0, "D": 0, "UP": 0, "LEFT": 0, "DOWN": 0, "RIGHT": 0,
    "ESPACIO": 1, "C": 2, "CTRL": 3, "E": 4, "ESC": 5,
}
# En qué teclas se pone el numerito de la acción
BADGE_KEYS = {"W": 0, "UP": 0, "ESPACIO": 1, "C": 2, "CTRL": 3, "E": 4, "ESC": 5}

ARROWS = ("UP", "DOWN", "LEFT", "RIGHT")

KB_UNITS_WIDE = 15.75   # ancho total del teclado dibujado, en "teclas"


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


def _draw_arrow(surface, rect, direction, color):
    cx, cy = rect.center
    s = max(4, int(min(rect.w, rect.h) * 0.22))
    k = s * 0.7
    pts = {
        "UP":    [(cx, cy - s), (cx - s, cy + k), (cx + s, cy + k)],
        "DOWN":  [(cx, cy + s), (cx - s, cy - k), (cx + s, cy - k)],
        "LEFT":  [(cx - s, cy), (cx + k, cy - s), (cx + k, cy + s)],
        "RIGHT": [(cx + s, cy), (cx - k, cy - s), (cx - k, cy + s)],
    }[direction]
    pygame.draw.polygon(surface, color, [(int(x), int(y)) for x, y in pts])


class ControlsView:
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
        self.margin = int(W * 0.05)

        self.f_title = _font(max(18, int(H * 0.036)))
        self.f_sub = _font(max(8, int(H * 0.013)))
        self.f_name = _font(max(10, int(H * 0.017)))
        self.f_desc = _font(max(8, int(H * 0.0125)))
        self.f_key = _font(max(8, int(H * 0.0145)))
        self.f_cap = _font(max(8, int(H * 0.0115)))
        self.f_num = _font(max(8, int(H * 0.0125)))
        self.f_hint = _font(max(8, int(H * 0.014)))

        # --- Teclado ---
        u = int(min(W * 0.042, H * 0.074))
        self.u = u
        g = max(4, int(u * 0.1))
        self.kb_x = (W - int(KB_UNITS_WIDE * u)) // 2
        self.kb_y = int(H * 0.19)

        D = 1.25  # donde empieza la fila de números (después de ESC)
        layout = [("ESC", 0, 0, 1.0)]
        layout += [(ch, D + i, 0, 1) for i, ch in enumerate("1234567890")]
        layout += [("TAB", 0, 1, 1.65)]
        layout += [(ch, D + 0.5 + i, 1, 1) for i, ch in enumerate("QWERTYUIOP")]
        layout += [("CAPS", 0, 2, 1.9)]
        layout += [(ch, D + 0.75 + i, 2, 1) for i, ch in enumerate("ASDFGHJKL")]
        layout += [("SHIFT", 0, 3, 2.4)]
        layout += [(ch, D + 1.25 + i, 3, 1) for i, ch in enumerate("ZXCVBNM")]
        layout += [("CTRL", 0, 4, 1.5), ("ALT", 1.5, 4, 1.25),
                   ("ESPACIO", 2.75, 4, 5.5), ("ALT", 8.25, 4, 1.25)]
        A = 12.75  # bloque de flechas
        layout += [("UP", A + 1, 3, 1), ("LEFT", A, 4, 1), ("DOWN", A + 1, 4, 1), ("RIGHT", A + 2, 4, 1)]

        self.keys = []  # (label, rect, índice de acción o None)
        for label, x, row, w in layout:
            r = pygame.Rect(self.kb_x + int(x * u), self.kb_y + row * u, int(w * u) - g, u - g)
            self.keys.append((label, r, KEY_ACTION.get(label)))

        self.kb_plate = pygame.Rect(self.kb_x - 24, self.kb_y - 24,
                                    int(KB_UNITS_WIDE * u) + 48 - g, 5 * u + 48 - g)

        # --- Tarjetas de acciones ---
        gap_x = int(W * 0.018)
        card_w = (W - self.margin * 2 - gap_x) // 2
        card_h = int(H * 0.08)
        gap_y = int(H * 0.015)
        top = int(H * 0.615)
        self.card_rects = []
        for i in range(len(ACTIONS)):
            col, row = i % 2, i // 2
            self.card_rects.append(pygame.Rect(self.margin + col * (card_w + gap_x),
                                               top + row * (card_h + gap_y), card_w, card_h))
        self._card_fill = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        self._card_fill.fill((*PANEL, 215))

        self._build_background(size)
        self._build_overlays(size)

    def _build_background(self, size):
        W, H = size
        bg = pygame.Surface(size)
        for y in range(H):
            k = y / float(H)
            bg.fill((int(3 + 4 * (1 - k)), int(12 + 12 * (1 - k)), int(7 + 6 * (1 - k))), (0, y, W, 1))

        # Grilla tenue
        grid = pygame.Surface(size, pygame.SRCALPHA)
        step = max(24, int(H * 0.06))
        for x in range(0, W, step):
            pygame.draw.line(grid, (0, 255, 128, 12), (x, 0), (x, H))
        for y in range(0, H, step):
            pygame.draw.line(grid, (0, 255, 128, 12), (0, y), (W, y))
        bg.blit(grid, (0, 0))

        # Encabezado
        m = self.margin
        title = self.f_title.render("CONTROLES", True, ACCENT)
        ty = int(H * 0.045)
        pygame.draw.rect(bg, ACCENT, (m, ty - 2, 6, title.get_height() + 4))
        bg.blit(title, (m + 22, ty))
        sub = self.f_sub.render("PASA EL MOUSE SOBRE UNA ACCIÓN PARA RESALTARLA", True, TEXT_DIM)
        bg.blit(sub, (m + 22, ty + title.get_height() + 8))
        ly = int(H * 0.138)
        pygame.draw.line(bg, LINE, (m, ly), (W - m, ly), 1)
        pygame.draw.rect(bg, ACCENT, (m, ly - 1, int(W * 0.12), 3))

        # Placa del teclado con esquinas estilo HUD
        plate = pygame.Surface(self.kb_plate.size, pygame.SRCALPHA)
        plate.fill((*PANEL, 215))
        bg.blit(plate, self.kb_plate.topleft)
        pygame.draw.rect(bg, (0, 120, 65), self.kb_plate, 2)
        p, c = self.kb_plate, max(14, self.kb_plate.w // 40)
        for (px, py, dx, dy) in ((p.left, p.top, 1, 1), (p.right - 1, p.top, -1, 1),
                                 (p.left, p.bottom - 1, 1, -1), (p.right - 1, p.bottom - 1, -1, -1)):
            pygame.draw.line(bg, ACCENT, (px, py), (px + dx * c, py), 3)
            pygame.draw.line(bg, ACCENT, (px, py), (px, py + dy * c), 3)

        self.bg = bg

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
    def _draw_key(self, surface, label, rect, action, hovered, pulse):
        active = action is not None and (hovered is None or hovered == action)
        if active:
            color = ACTIONS[action]["color"]
            face = _mix(color, PANEL, 0.80)
            side = _mix(color, (0, 0, 0), 0.55)
            border = color
            text = _mix(color, (255, 255, 255), 0.55)
            boost = 1.6 if hovered == action else 1.0
            glow = pygame.Surface((rect.w + 20, rect.h + 20), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*color, int((28 + 30 * pulse) * boost)), glow.get_rect(), border_radius=10)
            surface.blit(glow, (rect.x - 10, rect.y - 10))
        else:
            face, side, border, text = (8, 24, 16), (3, 10, 6), (0, 70, 40), (55, 95, 75)

        depth = max(3, rect.h // 11)
        pygame.draw.rect(surface, side, rect, border_radius=5)
        face_r = pygame.Rect(rect.x, rect.y, rect.w, rect.h - depth)
        pygame.draw.rect(surface, face, face_r, border_radius=5)
        pygame.draw.rect(surface, border, face_r, 2 if active else 1, border_radius=5)

        if label in ARROWS:
            _draw_arrow(surface, face_r, label, text)
        else:
            t = self.f_key.render(label, True, text)
            surface.blit(t, t.get_rect(center=face_r.center))

    def _draw_badge(self, surface, rect, number, color):
        bw = max(14, int(self.u * 0.3))
        b = pygame.Rect(rect.right - bw + 5, rect.y - 5, bw, bw)
        pygame.draw.rect(surface, color, b)
        t = self.f_num.render(str(number), True, DARK)
        surface.blit(t, t.get_rect(center=b.center))

    def _draw_cap(self, surface, rect, label, color):
        pygame.draw.rect(surface, _mix(color, PANEL, 0.80), rect, border_radius=4)
        pygame.draw.rect(surface, color, rect, 2, border_radius=4)
        if label in ARROWS:
            _draw_arrow(surface, rect, label, _mix(color, (255, 255, 255), 0.55))
        else:
            t = self.f_cap.render(label, True, _mix(color, (255, 255, 255), 0.55))
            surface.blit(t, t.get_rect(center=rect.center))

    def _draw_card(self, surface, i, hovered):
        a = ACTIONS[i]
        r = self.card_rects[i]
        color = a["color"]
        active = hovered is None or hovered == i
        tone = color if active else (60, 100, 80)

        surface.blit(self._card_fill, r.topleft)
        if hovered == i:
            tint = pygame.Surface(r.size, pygame.SRCALPHA)
            tint.fill((*color, 24))
            surface.blit(tint, r.topleft)
        pygame.draw.rect(surface, color if hovered == i else (0, 120, 65), r, 2)
        pygame.draw.rect(surface, tone, (r.x, r.y, 6, r.h))

        # Numerito
        bs = int(r.h * 0.46)
        b = pygame.Rect(r.x + 20, r.centery - bs // 2, bs, bs)
        pygame.draw.rect(surface, tone, b)
        n = self.f_num.render(str(i + 1), True, DARK)
        surface.blit(n, n.get_rect(center=b.center))

        # Nombre y descripción
        name = self.f_name.render(a["name"], True, TEXT if active else TEXT_DIM)
        desc = self.f_desc.render(a["desc"], True, TEXT_DIM)
        total = name.get_height() + 6 + desc.get_height()
        tx = b.right + 14
        ty = r.y + (r.h - total) // 2
        surface.blit(name, (tx, ty))
        surface.blit(desc, (tx, ty + name.get_height() + 6))

        # Teclas de la acción (alineadas a la derecha)
        cs = int(r.h * 0.44)
        cgap = 4
        items = []
        for cap in a["caps"]:
            if cap == "/":
                s = self.f_cap.render("/", True, TEXT_DIM)
                items.append(("sep", s, s.get_width() + 8))
            elif cap in ARROWS or len(cap) == 1:
                items.append(("cap", cap, cs))
            else:
                tw = self.f_cap.size(cap)[0]
                items.append(("cap", cap, max(cs, tw + 14)))
        total_w = sum(w for _, _, w in items) + cgap * (len(items) - 1)
        x = r.right - 18 - total_w
        for kind, obj, w in items:
            if kind == "sep":
                surface.blit(obj, (x + 4, r.centery - obj.get_height() // 2))
            else:
                self._draw_cap(surface, pygame.Rect(x, r.centery - cs // 2, w, cs), obj, tone)
            x += w + cgap

    def draw(self, surface, mouse_pos=None):
        size = surface.get_size()
        if size != self._size:
            self._build(size)

        now = pygame.time.get_ticks()
        if now - self._last_draw > 250:  # la pantalla se acaba de mostrar
            self._open_time = now
        self._last_draw = now
        t = now - self._open_time
        pulse = 0.5 + 0.5 * math.sin(now / 300.0)
        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()

        # Acción bajo el mouse (tarjeta o tecla)
        hovered = None
        for i, r in enumerate(self.card_rects):
            if r.collidepoint(mouse_pos):
                hovered = i
        for _label, r, a in self.keys:
            if a is not None and r.collidepoint(mouse_pos):
                hovered = a

        surface.blit(self.bg, (0, 0))

        for label, rect, action in self.keys:
            self._draw_key(surface, label, rect, action, hovered, pulse)
        for label, rect, action in self.keys:  # numeritos arriba de todo
            if label in BADGE_KEYS:
                a = BADGE_KEYS[label]
                if hovered is None or hovered == a:
                    self._draw_badge(surface, rect, a + 1, ACTIONS[a]["color"])

        for i in range(len(ACTIONS)):
            self._draw_card(surface, i, hovered)

        surface.blit(self.scanlines, (0, 0))
        surface.blit(self.vignette, (0, 0))

        fade = _ease_out(t / 400.0)
        if fade < 1.0:
            self.black.set_alpha(int(255 * (1 - fade)))
            surface.blit(self.black, (0, 0))
