import pygame
import os     
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_BG, COLOR_TEXT, COLOR_ACCENT, COLOR_HOVER, COLOR_DISABLED
from src.controls_view import ControlsView
from src.credits_view import CreditsView
import math


# ---- Sonidos del menú (nuevo) ----
_SFX_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "assets", "audio", "sfx")
_sounds = {}

def play_sound(name):
    """Reproduce assets/audio/sfx/<name>.wav ('select' o 'cancel'). Si falla, queda en silencio."""
    try:
        snd = _sounds.get(name)
        if snd is None:  # se carga la primera vez, cuando el mixer ya está inicializado
            snd = pygame.mixer.Sound(os.path.join(_SFX_DIR, f"{name}.wav"))
            _sounds[name] = snd
        snd.play()
    except Exception:
        pass


from src.main_menu_view import MainMenuView

class Button:
    def __init__(self, text, x, y, width, height, font):
        self.text = text
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.is_enabled = True

    def draw(self, surface, mouse_pos):
        color = COLOR_ACCENT if self.is_enabled else COLOR_DISABLED
        if self.is_enabled and self.rect.collidepoint(mouse_pos):
            color = COLOR_HOVER

        # Líneas finas y rectangulares características del iDroid
        pygame.draw.rect(surface, color, self.rect, 1)
        
        txt_surf = self.font.render(self.text, True, color if self.is_enabled else COLOR_DISABLED)
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        surface.blit(txt_surf, txt_rect)

    def is_clicked(self, event):
        if self.is_enabled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False

class RetroButton:
    """Botón con el estilo retro del menú principal. Misma interfaz que Button."""
    _ACCENT = (0, 255, 128)
    _ACCENT_SOFT = (0, 220, 110)
    _TEXT = (205, 235, 215)
    _DARK = (5, 20, 10)
    _PANEL = (4, 14, 9)
    _BORDER = (0, 120, 65)
    _FONT_PATH = "assets/fonts/PressStart2P-Regular.ttf"

    def __init__(self, text, x, y, width, height, back=False, key_hint=None):
        self.text = text
        self.rect = pygame.Rect(x, y, width, height)
        self.back = back
        self.key_hint = key_hint
        self.is_enabled = True
        self.font = self._font(max(8, int(height * 0.30)))
        self.font_key = self._font(max(8, int(height * 0.21)))

    def _font(self, size):
        try:
            return pygame.font.Font(self._FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            return pygame.font.SysFont("Courier", int(size * 1.4), bold=True)

    def draw(self, surface, mouse_pos):
        r = self.rect
        hover = self.is_enabled and r.collidepoint(mouse_pos)
        h = r.h

        if hover:
            cut = max(6, h // 4)
            pts = [(r.x, r.y), (r.right, r.y), (r.right, r.bottom - cut),
                    (r.right - cut, r.bottom), (r.x, r.bottom)]
            glow = pygame.Surface((r.w + 24, h + 24), pygame.SRCALPHA)
            pygame.draw.rect(glow, (0, 255, 128, 40), glow.get_rect(), border_radius=10)
            surface.blit(glow, (r.x - 12, r.y - 12))
            pygame.draw.polygon(surface, self._ACCENT_SOFT, pts)
            pygame.draw.rect(surface, (190, 255, 220), (r.x, r.y, 5, h))
            fg = self._DARK
        else:
            fill = pygame.Surface(r.size, pygame.SRCALPHA)
            fill.fill((*self._PANEL, 215))
            surface.blit(fill, r.topleft)
            pygame.draw.rect(surface, self._BORDER if self.is_enabled else (50, 50, 50), r, 2)
            pygame.draw.rect(surface, self._ACCENT if self.is_enabled else (50, 50, 50), (r.x, r.y, 4, h))
            fg = self._TEXT if self.is_enabled else (80, 80, 80)

        x = r.x + 18
        cy = r.centery

        if self.back:
            s = max(5, h // 7)
            pygame.draw.polygon(surface, fg, [(x, cy), (x + s * 3 // 2, cy - s), (x + s * 3 // 2, cy + s)])
            x += s * 3 // 2 + 12

        txt = self.font.render(self.text, True, fg)
        surface.blit(txt, (x, cy - txt.get_height() // 2))

        if self.key_hint:
            k = self.font_key.render(self.key_hint, True, fg)
            kw, kh = k.get_width() + 12, k.get_height() + 10
            key_r = pygame.Rect(r.right - 14 - kw, cy - kh // 2, kw, kh)
            pygame.draw.rect(surface, fg, key_r, 1, border_radius=3)
            surface.blit(k, k.get_rect(center=key_r.center))

    def is_clicked(self, event):
        if self.is_enabled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False

# ---- Estilo retro para la pantalla de misiones ----
_R_ACCENT = (0, 255, 128)
_R_TEXT = (205, 235, 215)
_R_DIM = (105, 150, 122)
_R_DARK = (5, 20, 10)
_R_LINE = (0, 110, 60)
_R_PANEL = (4, 14, 9)
_R_BORDER = (0, 120, 65)
_R_FONT_PATH = "assets/fonts/PressStart2P-Regular.ttf"
_r_fonts = {}


def retro_font(size):
    f = _r_fonts.get(size)
    if f is None:
        try:
            f = pygame.font.Font(_R_FONT_PATH, size)
        except (FileNotFoundError, OSError, pygame.error):
            f = pygame.font.SysFont("Courier", int(size * 1.4), bold=True)
        _r_fonts[size] = f
    return f


def _r_mix(c1, c2, t):
    return tuple(int(a * (1 - t) + b * t) for a, b in zip(c1, c2))


def _r_ease(p):
    p = max(0.0, min(1.0, p))
    return 1 - (1 - p) ** 3


def _r_wrap(font, text, max_w):
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


_SKULL = [
    ".#####.",
    "#######",
    "#..#..#",
    "#..#..#",
    "#######",
    ".#.#.#.",
]


def _draw_skull(surface, x, y, px, color):
    for ry, row in enumerate(_SKULL):
        for rx, ch in enumerate(row):
            if ch == "#":
                surface.fill(color, (x + rx * px, y + ry * px, px, px))


def _r_plate(surface, rect):
    """Panel oscuro con borde verde y esquinas estilo HUD."""
    plate = pygame.Surface(rect.size, pygame.SRCALPHA)
    plate.fill((*_R_PANEL, 215))
    surface.blit(plate, rect.topleft)
    pygame.draw.rect(surface, _R_BORDER, rect, 2)
    c = max(14, rect.w // 30)
    for (px, py, dx, dy) in ((rect.left, rect.top, 1, 1), (rect.right - 1, rect.top, -1, 1),
                            (rect.left, rect.bottom - 1, 1, -1), (rect.right - 1, rect.bottom - 1, -1, -1)):
        pygame.draw.line(surface, _R_ACCENT, (px, py), (px + dx * c, py), 3)
        pygame.draw.line(surface, _R_ACCENT, (px, py), (px, py + dy * c), 3)


def _r_section(surface, text, x, w, y, font):
    t = font.render(text, True, _R_ACCENT)
    surface.blit(t, (x, y))
    ly = y + t.get_height() + 10
    pygame.draw.line(surface, _R_LINE, (x, ly), (x + w, ly), 1)
    pygame.draw.rect(surface, _R_ACCENT, (x, ly - 1, int(w * 0.22), 3))


def _r_cap(surface, rect, text, font):
    pygame.draw.rect(surface, _r_mix(_R_ACCENT, _R_PANEL, 0.80), rect, border_radius=4)
    pygame.draw.rect(surface, _R_ACCENT, rect, 2, border_radius=4)
    t = font.render(text, True, _r_mix(_R_ACCENT, (255, 255, 255), 0.55))
    surface.blit(t, t.get_rect(center=rect.center))

class MenuManager:
    def __init__(self):
        self.state = "MAIN_MENU"  # MAIN_MENU, MISSIONS, CONTROLS, CREDITS, START_GAME, EXIT
        FONT_PATH = "assets/fonts/PressStart2P-Regular.ttf"
        self.font_title = pygame.font.Font(FONT_PATH, 24)
        self.font_subtitle = pygame.font.Font(FONT_PATH, 14) 
        self.font_btn = pygame.font.Font(FONT_PATH, 12)       
        self.font_small = pygame.font.Font(FONT_PATH, 9)      

        # Cargar e escalar la imagen del título del juego
        try:
            raw_title_img = pygame.image.load("assets/intro/title_logo.png").convert_alpha()
            # Escalar la imagen a un tamaño adecuado para la pantalla del menú
            self.title_img = pygame.transform.scale(raw_title_img, (450, 90))
        except Exception:
            self.title_img = None

        
        
        # Fuentes tipográficas del sistema o Pygame
        self.font_title = pygame.font.Font(None, 28)
        self.font_btn = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 16)
        
        self.selected_mission_id = 1

        # Base de datos de misiones con numeración Peace Walker, calaveras de dificultad,
        # mapas TMX reales y tareas (Mission Tasks estilo MGSV)
        self.missions_data = {
            1: {
                "id": "001",
                "title": "ENTRY POINT",
                "difficulty": 2, # Cantidad de calaveras
                "map_file": "assets/maps/mapa_edificio1.tmx", # Ajusta según tu ruta de TMX
                "unlocked": True,
                "objective": "Infiltrarse en la nación fortificada de Zanzibar Land.",
                "situation": "El agente legendario Solid Snake ha sido movilizado de urgencia para rescatar al Dr. Kio Marv, creador del OILIX.",
                "tasks": [
                    "Evitar la alerta antes de entrar a la base.",
                    "Localizar el conducto de ventilación",
                    "Asegurar el acceso al Edificio 1"
                ]
            },
            2: {
                "id": "002",
                "title": "Edificio 1",
                "difficulty": 3,
                "map_file": "assets/maps/mapa_pantano.tmx", # Ajusta según tu ruta de TMX
                "unlocked": True,
                "objective": "Localizar el paradero del Dr. Marv en el edificio.",
                "situation": "El edificio está fuertemente custodiado por fuerzas especiales y cámaras de seguridad.",
                "tasks": [
                    "Evitar la alerta.",
                    "Encontrar la tarjeta de acceso de nivel superior.",
                    "Localizar al Dr. Kio Marv."
                ]
            }
        }

        # Botones del Menú Principal
        self.main_buttons = [
            Button("EMPEZAR PARTIDA", SCREEN_WIDTH // 2 - 140, 180, 280, 32, self.font_btn),
            Button("VER CONTROLES", SCREEN_WIDTH // 2 - 140, 230, 280, 32, self.font_btn),
            Button("VER CRÉDITOS", SCREEN_WIDTH // 2 - 140, 280, 280, 32, self.font_btn),
            Button("SALIR DEL JUEGO", SCREEN_WIDTH // 2 - 140, 330, 280, 32, self.font_btn),
        ]
        # Vista del menú principal (imagen de Snake + logo con brillo + opciones)
        self.main_view = MainMenuView([b.text for b in self.main_buttons])
        self.controls_view = ControlsView()
        self.credits_view = CreditsView()

        # Botones de navegación interna
        self.back_button = RetroButton("VOLVER", int(SCREEN_WIDTH * 0.05), SCREEN_HEIGHT - 64, 190, 42, back=True, key_hint="ESC")
        self.deploy_button = RetroButton("DESPLEGAR", SCREEN_WIDTH - 280, SCREEN_HEIGHT - 64, 250, 42, key_hint="ENTER")

    def handle_events(self, events):
        mouse_pos = pygame.mouse.get_pos()
        action = None

        for event in events:
            if event.type == pygame.QUIT:
                return "EXIT"

            # ESC: volver al menú principal desde Misiones, Controles o Créditos   <- nuevo
            if (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                    and self.state in ("MISSIONS", "CONTROLS", "CREDITS")):
                play_sound("cancel")
                self.state = "MAIN_MENU"
                continue

            if self.state == "MAIN_MENU":
                chosen = self.main_view.handle_event(event)
                if chosen == 0:
                    self.state = "MISSIONS"
                elif chosen == 1:
                    self.state = "CONTROLS"
                elif chosen == 2:
                    self.state = "CREDITS"
                elif chosen == 3:
                    play_sound("cancel")        # <- nuevo (salir del juego)
                    return "EXIT"

            elif self.state == "MISSIONS":
                lay = self._mission_layout(*pygame.display.get_surface().get_size())

                # Clic en una misión de la lista
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for idx, rect in lay["items"].items():
                        if rect.collidepoint(event.pos) and idx != self.selected_mission_id:
                            self.selected_mission_id = idx
                            play_sound("select")

                # Teclado: W/S o flechas para elegir, Enter para desplegar
                if event.type == pygame.KEYDOWN:
                    ids = sorted(self.missions_data)
                    pos = ids.index(self.selected_mission_id)
                    if event.key in (pygame.K_UP, pygame.K_w):
                        self.selected_mission_id = ids[(pos - 1) % len(ids)]
                        play_sound("select")
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.selected_mission_id = ids[(pos + 1) % len(ids)]
                        play_sound("select")
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        result = self._try_deploy()
                        if result:
                            return result

                # Botón Desplegar
                if self.deploy_button.is_clicked(event):
                    result = self._try_deploy()
                    if result:
                        return result

                # Botón Volver
                if self.back_button.is_clicked(event):
                    play_sound("cancel")
                    self.state = "MAIN_MENU"

            elif self.state in ["CONTROLS", "CREDITS"]:
                if self.back_button.is_clicked(event):
                    play_sound("cancel")        # <- nuevo
                    self.state = "MAIN_MENU"

        return action

    def update(self, dt):
        pass

    # ------------------------------------------------------------ MISIONES
    def _mission_layout(self, W, H):
        """Calcula dónde va cada cosa según el tamaño real de la pantalla (y ubica el botón DESPLEGAR)."""
        m = int(W * 0.05)
        top = int(H * 0.23)
        bottom = self.back_button.rect.y - int(H * 0.03)
        left_w = int(W * 0.30)
        right_x = m + left_w + int(W * 0.03)

        card_h, card_gap = int(H * 0.105), int(H * 0.018)
        items = {}
        for i, idx in enumerate(sorted(self.missions_data)):
            items[idx] = pygame.Rect(m, top + i * (card_h + card_gap), left_w, card_h)

        sh = int(H * 0.2)
        dw = max(250, int(W * 0.19))
        self.deploy_button.rect.update(W - m - dw, self.back_button.rect.y, dw, self.back_button.rect.h)

        return {
            "m": m, "top": top, "left_w": left_w, "right_x": right_x,
            "items": items,
            "keys": pygame.Rect(m, bottom - sh, left_w, sh),
            "detail": pygame.Rect(right_x, top, W - m - right_x, bottom - top),
        }

    def _mission_assets(self, W, H, lay):
        """Fondo, atajos y overlays: se arman una sola vez por tamaño de pantalla."""
        a = getattr(self, "_m_assets", None)
        if a is not None and a["size"] == (W, H):
            return a

        m = lay["m"]
        bg = pygame.Surface((W, H))
        for y in range(H):
            k = y / float(H)
            bg.fill((int(3 + 4 * (1 - k)), int(12 + 12 * (1 - k)), int(7 + 6 * (1 - k))), (0, y, W, 1))
        grid = pygame.Surface((W, H), pygame.SRCALPHA)
        step = max(24, int(H * 0.06))
        for x in range(0, W, step):
            pygame.draw.line(grid, (0, 255, 128, 12), (x, 0), (x, H))
        for y in range(0, H, step):
            pygame.draw.line(grid, (0, 255, 128, 12), (0, y), (W, y))
        bg.blit(grid, (0, 0))

        # Encabezado
        f_title = retro_font(max(18, int(H * 0.036)))
        f_sub = retro_font(max(8, int(H * 0.013)))
        f_sec = retro_font(max(10, int(H * 0.02)))
        title = f_title.render("SELECCIÓN DE MISIÓN", True, _R_ACCENT)
        ty = int(H * 0.045)
        pygame.draw.rect(bg, _R_ACCENT, (m, ty - 2, 6, title.get_height() + 4))
        bg.blit(title, (m + 22, ty))
        sub = f_sub.render("ELIGE UNA MISIÓN PARA COMENZAR", True, _R_DIM)
        bg.blit(sub, (m + 22, ty + title.get_height() + 8))
        ly = int(H * 0.138)
        pygame.draw.line(bg, _R_LINE, (m, ly), (W - m, ly), 1)
        pygame.draw.rect(bg, _R_ACCENT, (m, ly - 1, int(W * 0.12), 3))

        sec_y = int(H * 0.165)
        _r_section(bg, "MISIONES", m, lay["left_w"], sec_y, f_sec)
        _r_section(bg, "DETALLE DE LA MISIÓN", lay["right_x"], lay["detail"].w, sec_y, f_sec)

        # Panel de detalle
        _r_plate(bg, lay["detail"])

        # Panel de atajos de teclado
        kr = lay["keys"]
        _r_plate(bg, kr)
        f_desc = retro_font(max(8, int(H * 0.0125)))
        f_cap = retro_font(max(8, int(H * 0.0115)))
        pad = max(12, int(kr.h * 0.1))
        lab = f_desc.render("ATAJOS", True, _R_DIM)
        bg.blit(lab, (kr.x + pad + 8, kr.y + pad))
        rows = [(["W", "S"], "ELEGIR MISIÓN"), (["ENTER"], "DESPLEGAR"), (["ESC"], "VOLVER")]
        area_top = kr.y + pad + lab.get_height() + 12
        row_h = (kr.bottom - pad - area_top) // len(rows)
        cs = int(row_h * 0.72)
        for i, (caps, text) in enumerate(rows):
            cy = area_top + i * row_h + row_h // 2
            x = kr.x + pad + 8
            for c in caps:
                w = max(cs, f_cap.size(c)[0] + 14)
                _r_cap(bg, pygame.Rect(x, cy - cs // 2, w, cs), c, f_cap)
                x += w + 6
            t = f_desc.render(text, True, _R_TEXT)
            bg.blit(t, (x + 12, cy - t.get_height() // 2))

        # Scanlines, viñeta y negro para el fundido de entrada
        scan = pygame.Surface((W, H), pygame.SRCALPHA)
        for y in range(0, H, 4):
            pygame.draw.line(scan, (0, 0, 0, 40), (0, y), (W, y))
        sw, sh = 48, 27
        vig = pygame.Surface((sw, sh), pygame.SRCALPHA)
        for yy in range(sh):
            for xx in range(sw):
                dx = (xx / (sw - 1.0)) * 2 - 1
                dy = (yy / (sh - 1.0)) * 2 - 1
                d = min(1.0, math.sqrt(dx * dx + dy * dy) / 1.25)
                vig.set_at((xx, yy), (0, 0, 0, int(150 * d ** 2.2)))
        black = pygame.Surface((W, H))
        black.fill((0, 0, 0))

        self._m_assets = {"size": (W, H), "bg": bg, "scan": scan,
                          "vig": pygame.transform.smoothscale(vig, (W, H)), "black": black}
        return self._m_assets

    def _try_deploy(self):
        if self.missions_data[self.selected_mission_id]["unlocked"]:
            play_sound("select")
            return f"START_MISSION_{self.selected_mission_id}"
        return None

    def _draw_missions(self, surface, mouse_pos):
        W, H = surface.get_size()
        lay = self._mission_layout(W, H)
        assets = self._mission_assets(W, H, lay)

        now = pygame.time.get_ticks()
        if now - getattr(self, "_m_last", -100000) > 250:  # la pantalla se acaba de mostrar
            self._m_open = now
        self._m_last = now
        t = now - self._m_open

        surface.blit(assets["bg"], (0, 0))
        for pos, (idx, rect) in enumerate(lay["items"].items()):
            p = _r_ease((t - 150 - pos * 90) / 320.0)
            if p > 0:
                self._draw_mission_card(surface, idx, rect, mouse_pos, p, H)
        self._draw_mission_detail(surface, lay, H)

        surface.blit(assets["scan"], (0, 0))
        surface.blit(assets["vig"], (0, 0))
        fade = _r_ease(t / 400.0)
        if fade < 1.0:
            assets["black"].set_alpha(int(255 * (1 - fade)))
            surface.blit(assets["black"], (0, 0))

        self.deploy_button.is_enabled = self.missions_data[self.selected_mission_id]["unlocked"]
        self.back_button.draw(surface, mouse_pos)
        self.deploy_button.draw(surface, mouse_pos)

    def _draw_mission_card(self, surface, idx, rect, mouse_pos, progress, H):
        m = self.missions_data[idx]
        selected = idx == self.selected_mission_id
        hover = rect.collidepoint(mouse_pos)
        locked = not m["unlocked"]

        card = pygame.Surface(rect.size, pygame.SRCALPHA)
        loc = card.get_rect()
        card.fill((*_R_PANEL, 215))
        if selected:
            tint = pygame.Surface(rect.size, pygame.SRCALPHA)
            tint.fill((*_R_ACCENT, 34))
            card.blit(tint, (0, 0))
        pygame.draw.rect(card, _R_ACCENT if (selected or hover) else _R_BORDER, loc, 2)
        pygame.draw.rect(card, _R_ACCENT if selected else (0, 70, 40), (0, 0, 6, loc.h))

        # Número de misión
        bs = int(loc.h * 0.62)
        b = pygame.Rect(24, loc.centery - bs // 2, bs, bs)
        pygame.draw.rect(card, _r_mix(_R_ACCENT, _R_PANEL, 0.78) if selected else (8, 24, 16), b)
        pygame.draw.rect(card, _R_ACCENT if selected else _R_BORDER, b, 2)
        idt = retro_font(max(10, int(H * 0.0165))).render(
            m["id"], True, _r_mix(_R_ACCENT, (255, 255, 255), 0.55) if selected else _R_DIM)
        card.blit(idt, idt.get_rect(center=b.center))

        # Nombre y calaveras de dificultad
        name = retro_font(max(11, int(H * 0.0185))).render(
            m["title"].upper(), True, _R_TEXT if (selected or hover) else _R_DIM)
        px = max(2, int(H * 0.0035))
        total = name.get_height() + 10 + 6 * px
        tx, ty = b.right + 20, (loc.h - total) // 2
        card.blit(name, (tx, ty))
        sy = ty + name.get_height() + 10
        for i in range(5):
            _draw_skull(card, tx + i * (9 * px), sy, px, _R_ACCENT if i < m["difficulty"] else (35, 70, 50))

        if locked:
            lk = retro_font(max(8, int(H * 0.0125))).render("BLOQUEADA", True, (200, 90, 90))
            card.blit(lk, (loc.w - lk.get_width() - 16, loc.centery - lk.get_height() // 2))

        card.set_alpha(int(255 * progress))
        surface.blit(card, (rect.x + int((1 - progress) * 70), rect.y))

    def _draw_mission_detail(self, surface, lay, H):
        d = lay["detail"]
        sel = self.missions_data[self.selected_mission_id]
        pad = max(20, int(d.w * 0.035))
        x, right = d.x + pad, d.right - pad
        max_w = right - x
        limit = d.bottom - pad
        f_small = retro_font(max(8, int(H * 0.0125)))
        f_head = retro_font(max(14, int(H * 0.026)))
        f_body = retro_font(max(9, int(H * 0.0135)))
        lh = f_body.get_height() + 10
        y = d.y + pad

        # Encabezado: número, nombre y dificultad
        tag = f_small.render(f"MISIÓN {sel['id']}", True, _R_DIM)
        surface.blit(tag, (x, y))
        dl = f_small.render("DIFICULTAD", True, _R_DIM)
        surface.blit(dl, (right - dl.get_width(), y))
        y += tag.get_height() + 10
        title = f_head.render(sel["title"].upper(), True, _R_ACCENT)
        surface.blit(title, (x, y))
        px = max(3, int(H * 0.0045))
        step = 9 * px
        sx = right - (step * 5 - 2 * px)
        sy = y + (title.get_height() - 6 * px) // 2
        for i in range(5):
            _draw_skull(surface, sx + i * step, sy, px, _R_ACCENT if i < sel["difficulty"] else (35, 70, 50))
        y += title.get_height() + 16
        pygame.draw.line(surface, _R_LINE, (x, y), (right, y), 1)
        pygame.draw.rect(surface, _R_ACCENT, (x, y - 1, int(max_w * 0.18), 3))
        y += 26

        def label(text):
            nonlocal y
            s = f_small.render(text, True, (0, 200, 100))
            surface.blit(s, (x, y))
            y += s.get_height() + 10

        def paragraph(text, indent=0):
            nonlocal y
            for line in _r_wrap(f_body, text, max_w - indent):
                if y + lh > limit:
                    return
                surface.blit(f_body.render(line, True, _R_TEXT), (x + indent, y))
                y += lh

        label("OBJETIVO PRINCIPAL")
        paragraph(sel["objective"])
        y += 18
        label("SITUACIÓN")
        paragraph(sel["situation"])
        y += 18
        label("TAREAS DE LA MISIÓN")
        box = max(10, int(f_body.get_height() * 0.85))
        for task in sel["tasks"]:
            if y + lh > limit:
                break
            pygame.draw.rect(surface, _R_ACCENT, (x, y + (f_body.get_height() - box) // 2, box, box), 2)
            paragraph(task, indent=box + 14)
            y += 6

    def draw(self, surface):
        surface.fill(COLOR_BG)
        mouse_pos = pygame.mouse.get_pos()

        if self.state == "MAIN_MENU":
            self.main_view.draw(surface)

        elif self.state == "MISSIONS":
            self._draw_missions(surface, mouse_pos)


        elif self.state == "CONTROLS":
            self.controls_view.draw(surface)
            self.back_button.draw(surface, mouse_pos)
        

        elif self.state == "CREDITS":
            self.credits_view.draw(surface)
            self.back_button.draw(surface, mouse_pos)
