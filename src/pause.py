import math
import os

import pygame

# ---------------------------------------------------------------------------
# PAUSA — Metal Gear 2: Solid Python
# Mantiene la misma interfaz que usa game.py:
#   PauseMenu(w, h) / handle_input(event) / draw(surface) / trigger_feedback(txt)
# y devuelve exactamente los mismos textos de acción:
#   "CONTINUAR", "PUNTO DE CONTROL", "REINICIAR MISIÓN", "VOLVER AL MENÚ"
# ---------------------------------------------------------------------------

ACCENT = (0, 255, 128)
ACCENT_SOFT = (0, 220, 110)
TEXT = (205, 235, 215)
TEXT_DIM = (105, 150, 122)
DARK = (5, 20, 10)
PANEL = (8, 22, 14)
WARN = (255, 220, 50)
DANGER = (255, 90, 70)

KEYS_UP = (pygame.K_UP, pygame.K_w)
KEYS_DOWN = (pygame.K_DOWN, pygame.K_s)
KEYS_LEFT = (pygame.K_LEFT, pygame.K_a)
KEYS_RIGHT = (pygame.K_RIGHT, pygame.K_d)
KEYS_OK = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
KEYS_BACK = (pygame.K_ESCAPE, pygame.K_BACKSPACE)

FONT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fonts", "PressStart2P-Regular.ttf"
)

SFX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "audio", "sfx")
SFX_MAX_MS = 2000  # cada sonido del menú suena como máximo 2 segundos


def _load_font(size):
    """Usa la fuente pixelada del juego; si no está, cae a Courier."""
    try:
        return pygame.font.Font(FONT_PATH, size)
    except (FileNotFoundError, OSError, pygame.error):
        return pygame.font.SysFont("Courier", int(size * 1.4), bold=True)


def _ease_out(p):
    p = max(0.0, min(1.0, p))
    return 1 - (1 - p) ** 3


def _brackets(surface, rect, color, size=14, width=2):
    """Esquinas estilo HUD / codec en los cuatro vértices del rect."""
    x, y, w, h = rect
    r, b = x + w - 1, y + h - 1
    for (cx, cy, dx, dy) in ((x, y, 1, 1), (r, y, -1, 1), (x, b, 1, -1), (r, b, -1, -1)):
        pygame.draw.line(surface, color, (cx, cy), (cx + dx * size, cy), width)
        pygame.draw.line(surface, color, (cx, cy), (cx, cy + dy * size), width)


class PauseMenu:
    FADE_MS = 180

    MENU_X = 70
    MENU_Y = 175
    MENU_W = 700
    ITEM_H = 54
    ITEM_STEP = 68

    # Opciones que piden confirmación antes de devolverse a game.py
    CONFIRMS = {
        "REINICIAR MISIÓN": ("¿REINICIAR MISIÓN?", "Empezarás de nuevo desde el inicio."),
        "VOLVER AL MENÚ": ("¿VOLVER AL MENÚ?", "Se perderá el progreso de la misión actual."),
    }

    SUB_DESCS = [
        "Ajusta el volumen de la música de fondo.",
        "Ajusta el volumen de los efectos de sonido.",
        "Volver al menú de pausa.",
    ]

    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height

        self.main_options = [
            {"title": "CONTINUAR", "desc": "Reanudar la misión de infiltración actual."},
            {"title": "PUNTO DE CONTROL", "desc": "Cargar el último punto de control guardado."},
            {"title": "REINICIAR MISIÓN", "desc": "Reiniciar la misión actual desde el inicio."},
            {"title": "OPCIONES", "desc": "Ajustar volumen de sonido y configuración."},
            {"title": "VOLVER AL MENÚ", "desc": "Salir del juego actual y regresar al menú principal."},
        ]

        self.options_menu = [
            {"title": "VOLUMEN MÚSICA", "val": 80},
            {"title": "VOLUMEN SFX", "val": 100},
            {"title": "VOLVER", "val": None},
        ]

        self.in_sub_options = False
        self.selected_index = 0
        self.selected_sub_index = 0
        self.confirm = None  # {"action", "title", "text", "index"} cuando hay diálogo abierto

        self.font_title = _load_font(44)
        self.font_option = _load_font(20)
        self.font_desc = _load_font(12)
        self.font_small = _load_font(12)
        self.font_tiny = _load_font(10)

        self.feedback_message = ""
        self.feedback_timer = 0

        # Estado de animación
        self._last_draw = -100000
        self._open_time = 0
        self._hl_y = None
        self._desc_key = None
        self._desc_time = 0

        self._build_static_layers()
        self._sounds = self._load_sounds()

    # ------------------------------------------------------------------ setup
    def _build_static_layers(self):
        w, h = self.screen_width, self.screen_height

        self.overlay = pygame.Surface((w, h))
        self.overlay.fill((6, 14, 9))

        # Viñeta: oscurece los bordes (se genera chica y se escala suave)
        small_w, small_h = 48, 27
        vig = pygame.Surface((small_w, small_h), pygame.SRCALPHA)
        for yy in range(small_h):
            for xx in range(small_w):
                dx = (xx / (small_w - 1)) * 2 - 1
                dy = (yy / (small_h - 1)) * 2 - 1
                d = min(1.0, math.sqrt(dx * dx + dy * dy) / 1.25)
                vig.set_at((xx, yy), (0, 0, 0, int(150 * d ** 2.2)))
        self.vignette = pygame.transform.smoothscale(vig, (w, h))

        # Scanlines sutiles estilo CRT
        self.scanlines = pygame.Surface((w, h), pygame.SRCALPHA)
        for yy in range(0, h, 4):
            pygame.draw.line(self.scanlines, (0, 0, 0, 40), (0, yy), (w, yy))

    # --------------------------------------------------------------- API pública
    @property
    def music_volume(self):
        return self.options_menu[0]["val"] / 100.0

    @property
    def sfx_volume(self):
        return self.options_menu[1]["val"] / 100.0

    def trigger_feedback(self, text):
        self.feedback_message = text
        self.feedback_timer = 120  # ~2 segundos

    # ------------------------------------------------------------------ sonido
    def _load_sounds(self):
        sounds = {}
        for name in ("select", "cancel"):
            path = os.path.join(SFX_DIR, name + ".wav")
            try:
                sounds[name] = pygame.mixer.Sound(path)
            except (FileNotFoundError, OSError, pygame.error) as e:
                print(f"Aviso sonido de pausa '{name}': {e}")
        return sounds

    def _play(self, name):
        snd = self._sounds.get(name)
        if snd is None:
            return
        try:
            snd.set_volume(self.sfx_volume)
            snd.play(maxtime=SFX_MAX_MS)
        except pygame.error:
            pass

    def handle_input(self, event):
        if event.type == pygame.MOUSEMOTION:
            self._on_mouse_move(event)
            return None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._on_click(event.pos)
        if event.type == pygame.KEYDOWN:
            return self._on_key(event.key)
        return None

    # ----------------------------------------------------------------- layout
    def _row_rect(self, i):
        return pygame.Rect(self.MENU_X, self.MENU_Y + i * self.ITEM_STEP, self.MENU_W, self.ITEM_H)

    def _slider_rect(self, i):
        row = self._row_rect(i)
        return pygame.Rect(row.x + 340, row.centery - 9, 218, 18)

    def _confirm_box(self):
        box = pygame.Rect(0, 0, 680, 240)
        box.center = (self.screen_width // 2, self.screen_height // 2)
        return box

    def _confirm_buttons(self):
        box = self._confirm_box()
        y = box.bottom - 80
        return [
            pygame.Rect(box.centerx - 250, y, 230, 48),
            pygame.Rect(box.centerx + 20, y, 230, 48),
        ]

    # ------------------------------------------------------------------ input
    def _move(self, delta):
        self._play("select")
        if self.in_sub_options:
            self.selected_sub_index = (self.selected_sub_index + delta) % len(self.options_menu)
        else:
            self.selected_index = (self.selected_index + delta) % len(self.main_options)

    def _set_volume(self, i, value):
        value = max(0, min(100, int(round(value / 10.0)) * 10))
        self.options_menu[i]["val"] = value
        if i == 0:
            try:
                pygame.mixer.music.set_volume(value / 100.0)
            except pygame.error:
                pass

    def _activate(self, i):
        self._play("select")
        title = self.main_options[i]["title"]
        if title == "OPCIONES":
            self.in_sub_options = True
            self.selected_sub_index = 0
            self._hl_y = None
            return None
        if title in self.CONFIRMS:
            ctitle, ctext = self.CONFIRMS[title]
            # Por defecto queda marcado "CANCELAR" para evitar accidentes
            self.confirm = {"action": title, "title": ctitle, "text": ctext, "index": 1}
            return None
        return title

    def _close_sub_options(self):
        self._play("cancel")
        self.in_sub_options = False
        self._hl_y = None

    def _on_key(self, key):
        # --- Diálogo de confirmación (tiene prioridad) ---
        if self.confirm:
            if key in KEYS_LEFT or key in KEYS_RIGHT or key in KEYS_UP or key in KEYS_DOWN:
                self._play("select")
                self.confirm["index"] = 1 - self.confirm["index"]
            elif key in KEYS_BACK:
                self._play("cancel")
                self.confirm = None
            elif key in KEYS_OK:
                self._play("select" if self.confirm["index"] == 0 else "cancel")
                action = self.confirm["action"] if self.confirm["index"] == 0 else None
                self.confirm = None
                return action
            return None

        # --- Submenú de audio ---
        if self.in_sub_options:
            if key in KEYS_UP:
                self._move(-1)
            elif key in KEYS_DOWN:
                self._move(1)
            elif key in KEYS_LEFT and self.selected_sub_index < 2:
                i = self.selected_sub_index
                self._set_volume(i, self.options_menu[i]["val"] - 10)
            elif key in KEYS_RIGHT and self.selected_sub_index < 2:
                i = self.selected_sub_index
                self._set_volume(i, self.options_menu[i]["val"] + 10)
            elif key in KEYS_BACK:
                self._close_sub_options()
            elif key in KEYS_OK and self.selected_sub_index == 2:
                self._close_sub_options()
            return None

        # --- Menú principal ---
        if key in KEYS_UP:
            self._move(-1)
        elif key in KEYS_DOWN:
            self._move(1)
        elif key in KEYS_OK:
            return self._activate(self.selected_index)
        elif key == pygame.K_ESCAPE:
            self._play("cancel")
            return "CONTINUAR"
        return None

    def _on_mouse_move(self, event):
        pos = event.pos
        if self.confirm:
            for i, r in enumerate(self._confirm_buttons()):
                if r.collidepoint(pos):
                    if self.confirm["index"] != i:
                        self._play("select")
                    self.confirm["index"] = i
            return

        count = len(self.options_menu) if self.in_sub_options else len(self.main_options)
        for i in range(count):
            if self._row_rect(i).collidepoint(pos):
                current = self.selected_sub_index if self.in_sub_options else self.selected_index
                if current != i:
                    self._play("select")
                if self.in_sub_options:
                    self.selected_sub_index = i
                else:
                    self.selected_index = i

        # Arrastrar el slider con el mouse apretado
        if self.in_sub_options and event.buttons[0]:
            for i in (0, 1):
                if self._slider_rect(i).inflate(30, 30).collidepoint(pos):
                    self._set_from_mouse(i, pos[0])

    def _set_from_mouse(self, i, mouse_x):
        rect = self._slider_rect(i)
        ratio = (mouse_x - rect.x) / float(rect.w)
        self._set_volume(i, max(0.0, min(1.0, ratio)) * 100)

    def _on_click(self, pos):
        if self.confirm:
            for i, r in enumerate(self._confirm_buttons()):
                if r.collidepoint(pos):
                    self._play("select" if i == 0 else "cancel")
                    action = self.confirm["action"] if i == 0 else None
                    self.confirm = None
                    return action
            return None

        if self.in_sub_options:
            for i in range(len(self.options_menu)):
                if not self._row_rect(i).collidepoint(pos):
                    continue
                self.selected_sub_index = i
                if i == 2:
                    self._close_sub_options()
                elif self._slider_rect(i).inflate(30, 30).collidepoint(pos):
                    self._set_from_mouse(i, pos[0])
                break
            return None

        for i in range(len(self.main_options)):
            if self._row_rect(i).collidepoint(pos):
                self.selected_index = i
                return self._activate(i)
        return None

    # ------------------------------------------------------------------- draw
    def _on_open(self, now):
        """Se llama solo cuando la pausa aparece (reinicia animación y estado)."""
        self._open_time = now
        self.selected_index = 0
        self.selected_sub_index = 0
        self.in_sub_options = False
        self.confirm = None
        self._hl_y = None
        self._desc_key = None

    def draw(self, surface):
        now = pygame.time.get_ticks()
        if now - self._last_draw > 250:  # la pausa se acaba de abrir
            self._on_open(now)
        self._last_draw = now

        elapsed = now - self._open_time
        fade = min(1.0, elapsed / float(self.FADE_MS))

        if self.feedback_timer > 0:
            self.feedback_timer -= 1

        self.overlay.set_alpha(int(212 * fade))
        surface.blit(self.overlay, (0, 0))
        self.vignette.set_alpha(int(255 * fade))
        surface.blit(self.vignette, (0, 0))
        surface.blit(self.scanlines, (0, 0))

        self._draw_header(surface, elapsed)
        if self.in_sub_options:
            self._draw_audio(surface, elapsed, now)
        else:
            self._draw_main(surface, elapsed, now)
        self._draw_footer(surface, now)

        if self.confirm:
            self._draw_confirm(surface)

    def _item_progress(self, elapsed, i):
        return _ease_out((elapsed - 60 - i * 45) / 260.0)

    def _draw_header(self, surface, elapsed):
        w = self.screen_width
        p = _ease_out(elapsed / 400.0)

        shadow = self.font_title.render("PAUSA", True, (0, 70, 35))
        surface.blit(shadow, (self.MENU_X + 3, 48 + 3))
        title = self.font_title.render("PAUSA", True, ACCENT)
        surface.blit(title, (self.MENU_X, 48))

        tag = self.font_tiny.render("METAL GEAR 2: SOLID PYTHON", True, TEXT_DIM)
        surface.blit(tag, (w - self.MENU_X - tag.get_width(), 70))

        y = 118
        pygame.draw.line(surface, (0, 110, 60), (self.MENU_X, y), (w - self.MENU_X, y), 1)
        pygame.draw.rect(surface, ACCENT, (self.MENU_X, y - 1, int(180 * p), 4))

    def _draw_highlight(self, surface, y, now):
        x, w, h = self.MENU_X, self.MENU_W, self.ITEM_H
        y = int(y)
        pulse = 0.5 + 0.5 * math.sin(now / 260.0)

        glow = pygame.Surface((w + 24, h + 24), pygame.SRCALPHA)
        pygame.draw.rect(glow, (0, 255, 128, int(26 + 22 * pulse)), glow.get_rect(), border_radius=10)
        surface.blit(glow, (x - 12, y - 12))

        pts = [(x, y), (x + w, y), (x + w, y + h - 14), (x + w - 14, y + h), (x, y + h)]
        pygame.draw.polygon(surface, ACCENT_SOFT, pts)
        pygame.draw.rect(surface, (190, 255, 220), (x, y, 6, h))

        ax = x + w - 44 + int(4 * pulse)
        cy = y + h // 2
        pygame.draw.polygon(surface, DARK, [(ax, cy - 8), (ax + 12, cy), (ax, cy + 8)])

    def _draw_row_texts(self, surface, i, title, sel, progress):
        row = self._row_rect(i)
        off = int((1 - progress) * -40)
        alpha = int(255 * progress)

        txt = self.font_option.render(title, True, DARK if sel else TEXT)
        txt.set_alpha(alpha)
        surface.blit(txt, (row.x + 28 + off, row.centery - txt.get_height() // 2))
        return row

    def _smooth_highlight(self, target_y):
        if self._hl_y is None:
            self._hl_y = float(target_y)
        else:
            self._hl_y += (target_y - self._hl_y) * 0.3
        return self._hl_y

    def _draw_main(self, surface, elapsed, now):
        label = self.font_tiny.render("SELECCIONA UNA OPCIÓN", True, TEXT_DIM)
        surface.blit(label, (self.MENU_X, 145))

        hl_y = self._smooth_highlight(self._row_rect(self.selected_index).y)
        if elapsed > 60:
            self._draw_highlight(surface, hl_y, now)

        for i, opt in enumerate(self.main_options):
            p = self._item_progress(elapsed, i)
            if p <= 0:
                continue
            sel = abs(hl_y - self._row_rect(i).y) < self.ITEM_STEP * 0.5 and elapsed > 60
            self._draw_row_texts(surface, i, opt["title"], sel, p)

    def _draw_audio(self, surface, elapsed, now):
        label = self.font_tiny.render("CONFIGURACIÓN DE AUDIO", True, ACCENT)
        surface.blit(label, (self.MENU_X, 145))

        hl_y = self._smooth_highlight(self._row_rect(self.selected_sub_index).y)
        self._draw_highlight(surface, hl_y, now)

        for i, opt in enumerate(self.options_menu):
            sel = abs(hl_y - self._row_rect(i).y) < self.ITEM_STEP * 0.5
            self._draw_row_texts(surface, i, opt["title"], sel, 1.0)

            if opt["val"] is None:
                continue

            rect = self._slider_rect(i)
            val = opt["val"]
            for b in range(10):
                block = pygame.Rect(rect.x + b * 22, rect.y, 18, rect.h)
                filled = (b + 1) * 10 <= val
                if filled:
                    color = DARK if sel else ACCENT
                else:
                    color = (0, 120, 60) if sel else (30, 62, 42)
                pygame.draw.rect(surface, color, block)

            val_surf = self.font_small.render(f"{val}%", True, DARK if sel else TEXT)
            surface.blit(val_surf, (rect.right + 14, rect.centery - val_surf.get_height() // 2))

    def _current_description(self):
        if self.feedback_timer > 0:
            return f"[ AVISO ] {self.feedback_message}", WARN
        if self.confirm:
            return "Esta acción no se puede deshacer.", DANGER
        if self.in_sub_options:
            return self.SUB_DESCS[self.selected_sub_index], (200, 255, 210)
        return self.main_options[self.selected_index]["desc"], (200, 255, 210)

    def _hint_text(self):
        if self.confirm:
            return "A/D ELEGIR  |  ENTER CONFIRMAR  |  ESC CANCELAR"
        if self.in_sub_options:
            return "W/S MOVER  |  A/D AJUSTAR  |  ESC VOLVER"
        return "W/S MOVER  |  ENTER SELECCIONAR"

    def _draw_footer(self, surface, now):
        w, h = self.screen_width, self.screen_height

        hint = self.font_tiny.render(self._hint_text(), True, TEXT_DIM)
        surface.blit(hint, (w - self.MENU_X - hint.get_width(), h - 116))

        box = pygame.Rect(self.MENU_X, h - 92, w - self.MENU_X * 2, 52)
        bg = pygame.Surface(box.size, pygame.SRCALPHA)
        bg.fill((PANEL[0], PANEL[1], PANEL[2], 225))
        surface.blit(bg, box.topleft)
        pygame.draw.rect(surface, ACCENT, (box.x, box.y, 6, box.h))
        _brackets(surface, box, ACCENT, size=12, width=2)

        text, color = self._current_description()
        key = (text, self.in_sub_options, self.selected_sub_index, self.selected_index)
        if key != self._desc_key:
            self._desc_key = key
            self._desc_time = now

        chars = int((now - self._desc_time) / 14) + 1
        typing = chars < len(text)
        surf = self.font_desc.render(text[:chars], True, color)
        tx, ty = box.x + 26, box.centery - surf.get_height() // 2
        surface.blit(surf, (tx, ty))

        if typing or (now // 400) % 2 == 0:
            pygame.draw.rect(surface, color, (tx + surf.get_width() + 4, ty, 9, surf.get_height()))

    def _draw_confirm(self, surface):
        dim = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        surface.blit(dim, (0, 0))

        box = self._confirm_box()
        pygame.draw.rect(surface, PANEL, box)
        pygame.draw.rect(surface, (WARN[0] // 3, WARN[1] // 3, 10), box, 1)
        _brackets(surface, box, WARN, size=18, width=3)

        title = self.font_option.render(self.confirm["title"], True, WARN)
        surface.blit(title, title.get_rect(center=(box.centerx, box.y + 52)))
        text = self.font_desc.render(self.confirm["text"], True, TEXT)
        surface.blit(text, text.get_rect(center=(box.centerx, box.y + 100)))

        labels = ["CONFIRMAR", "CANCELAR"]
        for i, rect in enumerate(self._confirm_buttons()):
            sel = (i == self.confirm["index"])
            base = ACCENT if i == 0 else DANGER
            if sel:
                pygame.draw.rect(surface, base, rect)
                label = self.font_small.render(labels[i], True, DARK)
            else:
                pygame.draw.rect(surface, base, rect, 2)
                label = self.font_small.render(labels[i], True, TEXT)
            surface.blit(label, label.get_rect(center=rect.center))