"""HUD de armas en carrusel de esquina (estilo MGS3 / Metal Gear 2D).

Layout (esquina inferior derecha):

              [ ARRIBA  ]      <- arma anterior (la que acabás de guardar)
    [ IZQUIERDA ] [ ACTIVA ]   <- siguiente arma (la que entra al apretar 1)

Reposo: solo se ve la caja activa (esquina).
Popup (al cambiar de arma o modo): aparecen las otras dos con fade.

Cada caja: fondo negro semi-transparente, nombre arriba a la derecha,
modo de disparo arriba a la izquierda (solo armas con fire_mode), ícono al
centro, munición en números y tira de balas abajo de todo.

TODO lo que es tamaño, fuente, color o posición está en la sección CONFIG.
"""
import pygame
from src import weapon_settings as WS
from src.hud import draw_text_shadow

# ═══════════════════════════════════════════════════════════════════════════
#  CONFIG  (tocá solo esto)
# ═══════════════════════════════════════════════════════════════════════════

# ── Fuente ─────────────────────────────────────────────────────────────────
# Poné acá la MISMA fuente que usa HealthBar para "SOLID PYTHON".
FONT_PATH        = WS.UI_FONT_BOLD
FONT_SIZE_NAME   = 12     # nombre del arma (si no entra en la caja se achica solo hasta FONT_SIZE_NAME_MIN)
FONT_SIZE_NAME_MIN = 8
FONT_SIZE_AMMO   = 16     # "15/60"
FONT_SIZE_MODE   = 10     # "semi" / "burst" / "auto"
FONT_SIZE_NOTICE = 12     # avisos centrados arriba

# ── Cajas ──────────────────────────────────────────────────────────────────
SLOT_W      = 150         # ancho de cada caja
SLOT_H      = 100         # alto de cada caja
SLOT_GAP_X  = 16          # separación horizontal entre cajas
SLOT_GAP_Y  = 14          # separación vertical entre cajas
MARGIN      = WS.HUD_MARGIN
PAD         = 7           # margen interno de las cajas

# ── Colores ────────────────────────────────────────────────────────────────
BG_COLOR      = (10, 8, 5)
BG_ALPHA      = 190       # 0 = invisible, 255 = opaco
BORDER_COLOR  = (88, 98, 92)   # borde fino de la caja; None = sin borde
DIVIDER_COLOR = (62, 70, 65)   # línea que separa el nombre del arma
COLOR_TEXT    = (240, 240, 235)
COLOR_DIM     = (120, 120, 112)
COLOR_LOW     = (230, 70, 60)     # munición baja
COLOR_MODE    = (235, 235, 230)   # texto/íconos del modo de disparo

# ── Íconos ─────────────────────────────────────────────────────────────────
ICON_TOP     = 24         # espacio reservado arriba (nombre)
ICON_BOTTOM  = 34         # espacio reservado abajo (números + balas)

# ── Texto de munición ─────────────────────────────────────────────────────
AMMO_ALIGN   = "right"    # "right" o "left"

# ── Tira de balas ──────────────────────────────────────────────────────────
BULLET_H         = 6
BULLET_FILL      = 0.5    # 0..1: qué parte del paso ocupa cada bala (grosor)
BULLET_COLOR_ON  = (240, 240, 235)
BULLET_COLOR_OFF = (70, 68, 62)

# ── Modo de disparo ────────────────────────────────────────────────────────
MODE_STYLE   = "text"     # "text" -> "semi"   |  "icon" -> 1/2/3 balitas
MODE_LABELS  = {"SEMI": "SEMI", "BURST": "RÁFAGA", "AUTO": "AUTO"}
MODE_BULLETS = {"SEMI": 1, "BURST": 2, "AUTO": 3}   # para MODE_STYLE = "icon"

# ── Animación ──────────────────────────────────────────────────────────────
POPUP_FADE        = 0.4   # segundos del fade-out de las cajas vecinas
INACTIVE_ALPHA    = 1.0   # opacidad extra de las cajas no activas (0..1)

# ═══════════════════════════════════════════════════════════════════════════


def _font(path, size):
    try:
        return pygame.font.Font(path, size)
    except Exception:
        return pygame.font.Font(None, size + 6)


def _fire_mode(weapon):
    """'SEMI' | 'BURST' | 'AUTO', o None si el arma no tiene selector.

    Solo muestra el modo si el arma puede cambiarlo (2+ modos): hoy, el M16.
    """
    modes = getattr(weapon, "modes", None)
    mode = getattr(weapon, "mode", None)
    if not modes or len(modes) < 2 or mode not in MODE_LABELS:
        return None
    return mode


class WeaponHUD:
    def __init__(self):
        self.font_name   = _font(FONT_PATH, FONT_SIZE_NAME)
        self.font_ammo   = _font(FONT_PATH, FONT_SIZE_AMMO)
        self.font_mode   = _font(FONT_PATH, FONT_SIZE_MODE)
        self.font_notice = _font(FONT_PATH, FONT_SIZE_NOTICE)
        self._icon_cache = {}
        self._name_fonts = {}

    def _fit_name_font(self, text, max_w):
        """Fuente más grande (hasta FONT_SIZE_NAME) con la que el nombre entra en max_w."""
        for size in range(FONT_SIZE_NAME, FONT_SIZE_NAME_MIN - 1, -1):
            font = self._name_fonts.get(size)
            if font is None:
                font = self._name_fonts[size] = _font(FONT_PATH, size)
            if font.size(text)[0] <= max_w:
                return font
        return font

    # ── helpers ──────────────────────────────────────────────────────────────
    def _scaled_icon(self, key, icon, max_w, max_h):
        ck = (key, max_w, max_h)
        if ck not in self._icon_cache:
            scale = min(max_w / icon.get_width(), max_h / icon.get_height())
            size = (max(1, int(icon.get_width() * scale)),
                    max(1, int(icon.get_height() * scale)))
            self._icon_cache[ck] = pygame.transform.scale(icon, size)
        return self._icon_cache[ck]

    def _draw_icon(self, surf, weapon, info, area):
        icon = info.get("icon")
        if icon is None:
            lbl = self.font_mode.render(info["name"][:6], True, COLOR_DIM)
            surf.blit(lbl, lbl.get_rect(center=area.center))
            return
        img = self._scaled_icon(weapon.id, icon, area.w, area.h)
        surf.blit(img, img.get_rect(center=area.center))

    # ── modo de disparo ──────────────────────────────────────────────────────
    def _draw_fire_mode(self, surf, weapon):
        mode = _fire_mode(weapon)
        if mode is None:
            return
        x, y = PAD, PAD + 1
        if MODE_STYLE == "icon":
            lit = MODE_BULLETS[mode]
            for i in range(3):
                color = COLOR_MODE if i < lit else BULLET_COLOR_OFF
                pygame.draw.rect(surf, color, (x + i * 5, y, 3, 10))
        else:
            draw_text_shadow(surf, self.font_mode, MODE_LABELS[mode],
                             COLOR_MODE, x, y)

    # ── tira de balas (cargador actual) ──────────────────────────────────────
    def _draw_bullet_strip(self, surf, w, h, weapon, info):
        mag_size = getattr(weapon, "mag_size", None)
        if not mag_size:
            return
        try:
            current = int(info["main"])
        except (ValueError, KeyError, TypeError):
            return
        mag_size = int(mag_size)
        avail = w - 2 * PAD
        pitch = avail / mag_size
        tick_w = max(1, int(pitch * BULLET_FILL))
        y = h - PAD - BULLET_H
        for i in range(mag_size):
            px = PAD + int(i * pitch)
            on = i < current          # las gastadas se apagan desde la derecha
            pygame.draw.rect(surf,
                             BULLET_COLOR_ON if on else BULLET_COLOR_OFF,
                             (px, y, tick_w, BULLET_H))

    def _draw_reload_bar(self, surf, w, h, progress):
        bar = pygame.Rect(PAD, h - PAD - BULLET_H // 2 - 2, w - 2 * PAD, 4)
        pygame.draw.rect(surf, COLOR_DIM, bar, 1)
        pygame.draw.rect(surf, COLOR_TEXT,
                         (bar.x, bar.y, int(bar.w * progress), bar.h))

    # ── una caja ─────────────────────────────────────────────────────────────
    def _draw_slot(self, surface, rect, weapon, alpha=1.0):
        info = weapon.hud_info()
        w, h = rect.size

        slot = pygame.Surface((w, h), pygame.SRCALPHA)
        slot.fill((*BG_COLOR, BG_ALPHA))
        if BORDER_COLOR is not None:
            pygame.draw.rect(slot, BORDER_COLOR, slot.get_rect(), 1)

        # Nombre (arriba a la derecha). Deja lugar al modo de disparo si el arma lo tiene.
        mode = _fire_mode(weapon)
        reserved = (self.font_mode.size(MODE_LABELS[mode])[0] + 8) if (mode and MODE_STYLE == "text") else 0
        name_font = self._fit_name_font(info["name"], w - 2 * PAD - reserved)
        draw_text_shadow(slot, name_font, info["name"], COLOR_TEXT,
                         w - PAD, PAD, align_right=True)
        pygame.draw.line(slot, DIVIDER_COLOR, (PAD, ICON_TOP - 3), (w - PAD, ICON_TOP - 3))

        # Modo de disparo (arriba a la izquierda)
        self._draw_fire_mode(slot, weapon)

        # Ícono (centro)
        icon_area = pygame.Rect(PAD, ICON_TOP, w - 2 * PAD,
                                h - ICON_TOP - ICON_BOTTOM)
        self._draw_icon(slot, weapon, info, icon_area)

        # Números de munición (encima de la tira de balas)
        text_y = h - PAD - BULLET_H - 4 - self.font_ammo.get_height()
        if info["progress"] is not None:
            draw_text_shadow(slot, self.font_ammo, "RECARGA", COLOR_DIM,
                             w - PAD, text_y, align_right=True)
            self._draw_reload_bar(slot, w, h, info["progress"])
        else:
            # Cargador en blanco (rojo si queda poco) y reserva "/60" más apagada.
            color = COLOR_LOW if info["low"] else COLOR_TEXT
            main_txt, sub_txt = str(info["main"]), str(info["sub"])
            main_w = self.font_ammo.size(main_txt)[0]
            sub_w = self.font_ammo.size(sub_txt)[0]
            x0 = PAD if AMMO_ALIGN == "left" else w - PAD - main_w - sub_w
            draw_text_shadow(slot, self.font_ammo, main_txt, color, x0, text_y)
            draw_text_shadow(slot, self.font_ammo, sub_txt, COLOR_DIM, x0 + main_w, text_y)
            self._draw_bullet_strip(slot, w, h, weapon, info)

        if alpha < 1.0:
            slot.set_alpha(int(255 * alpha))
        surface.blit(slot, rect.topleft)

    def _draw_empty_slot(self, surface, rect):
        """Caja vacía: todavía no hay ningún arma."""
        slot = pygame.Surface(rect.size, pygame.SRCALPHA)
        slot.fill((*BG_COLOR, BG_ALPHA))
        if BORDER_COLOR is not None:
            pygame.draw.rect(slot, BORDER_COLOR, slot.get_rect(), 1)
        surface.blit(slot, rect.topleft)

    # ── avisos ───────────────────────────────────────────────────────────────
    def _draw_notices(self, surface, manager):
        w = surface.get_width()
        for i, (text, t) in enumerate(manager.notices):
            color = COLOR_TEXT if t > 0.5 else COLOR_DIM
            tw = self.font_notice.size(text)[0]
            draw_text_shadow(surface, self.font_notice, text, color,
                             w // 2 - tw // 2, 70 + i * 22)

    # ── API principal ────────────────────────────────────────────────────────
    def draw(self, surface, manager):
        sw, sh = surface.get_size()

        main = pygame.Rect(sw - MARGIN - SLOT_W, sh - MARGIN - SLOT_H,
                           SLOT_W, SLOT_H)
        if manager.current_id is None:
            self._draw_empty_slot(surface, main)
        else:
            self._draw_slot(surface, main, manager.current)

        if manager.current_id is not None and manager.popup_timer > 0:
            fade = min(1.0, manager.popup_timer / POPUP_FADE) * INACTIVE_ALPHA
            prev_w, next_w = manager.neighbors()

            # Arriba de la activa: el arma anterior (la que acabás de guardar)
            if prev_w:
                up = main.move(0, -(SLOT_H + SLOT_GAP_Y))
                self._draw_slot(surface, up, prev_w, fade)
            # A la izquierda de la activa: la siguiente (entra a la esquina con 1)
            if next_w:
                left = main.move(-(SLOT_W + SLOT_GAP_X), 0)
                self._draw_slot(surface, left, next_w, fade)

        self._draw_notices(surface, manager)