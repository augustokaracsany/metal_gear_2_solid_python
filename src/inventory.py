import pygame

# Colores del inventario (tonos verde oscuro, como el menú de referencia).
COLOR_PANEL_BG = (16, 24, 18, 238)
COLOR_RING = (120, 140, 125, 70)
COLOR_ROW_BG = (34, 46, 36)
COLOR_ROW_BORDER = (95, 110, 98)
COLOR_ROW_SELECTED = (232, 232, 226)
COLOR_ROW_SELECTED_TEXT = (18, 24, 18)
COLOR_ROW_TEXT = (225, 228, 220)
COLOR_ROW_DISABLED = (110, 122, 112)
COLOR_ICON = (130, 140, 130)
COLOR_BAR_BG = (10, 14, 11)
COLOR_TITLE = (150, 165, 152)

CATEGORIES = [
    {"name": "ITEMS", "desc": "Objetos que Snake lleva encima."},
    {"name": "ARMAS", "desc": "Armamento disponible."},
]

WEAPON_KEYS = {"pistola"}

ITEM_INFO = {
    "cardboard_box": {
        "name": "CAJA DE CARTÓN",
        "desc": "El disfraz clásico. Si te quedás quieto, los guardias no te ven. "
                "ENTER para equipar/usar.",
        "sprite": None,
    },
    "food_ration": {
        "name": "RACIÓN",
        "desc": "Ración de combate. Comida para mantenerse en pie durante la misión. "
                "ENTER para equipar.",
        "sprite": "assets/sprites/items/racion_roja.png",
    },
    "ammo": {
        "name": "MUNICIONES",
        "desc": "Cargador para la pistola.",
        "sprite": "assets/sprites/items/municiones.png",
    },
}

# Descripciones de cada arma (la clave es el id del arma en weapons.py).
WEAPON_INFO = {
    "beretta": {
        "name": "BERETTA M92FS",
        "desc": "Pistola semiautomática. ESPACIO dispara hacia donde mira Snake, R recarga. "
                "Solo se puede usar de pie. ENTER para equiparla.",
    },
    "m16": {
        "name": "M16",
        "desc": "Fusil de asalto. ESPACIO dispara, R recarga y F cambia entre AUTO, SEMI y RÁFAGA. "
                "ENTER para equiparlo.",
    },
    "uzi": {
        "name": "MICRO UZI",
        "desc": "Subfusil automático de altísima cadencia. Mantené ESPACIO para disparar, R recarga. "
                "ENTER para equiparla.",
    },
    "stinger": {
        "name": "FIM-92 STINGER",
        "desc": "Lanzamisiles guiado. Snake queda quieto: mové el mouse para apuntar, "
                "fijá al helicóptero hasta READY TO FIRE y disparás con clic o ESPACIO. "
                "ENTER para equiparlo.",
    },
}

def load_font(path, size):
    try:
        return pygame.font.Font(path, size)
    except Exception:
        return pygame.font.Font(None, size + 6)

class InventoryMenu:
    def __init__(self, screen_width, screen_height):
        self.w = screen_width
        self.h = screen_height

        self.font_title = load_font("assets/fonts/PixelOperator8-Bold.ttf", 24)
        self.font_row = load_font("assets/fonts/PixelOperator8-Bold.ttf", 20)
        self.font_small = load_font("assets/fonts/PixelOperator8.ttf", 16)

        self.category_index = 0
        self.entry_index = 0
        self.in_entries = False
        self.entries = []
        self._sprite_cache = {}

        self.ring_center = (int(self.w * 0.30), int(self.h * 0.43))

        self.background = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        self.background.fill(COLOR_PANEL_BG)
        pygame.draw.circle(self.background, COLOR_RING, self.ring_center, 235, 16)
        pygame.draw.circle(self.background, COLOR_RING, self.ring_center, 275, 3)
        title = self.font_small.render("I N V E N T A R I O", True, COLOR_TITLE)
        self.background.blit(title, (self.ring_center[0] - title.get_width() // 2,
                                     self.ring_center[1] + 300))

    def open(self, player):
        self.category_index = 0
        self.entry_index = 0
        self.in_entries = False
        self._refresh_entries(player)

    def _weapon_manager(self, player):
        return getattr(player, "weapon_manager", None)

    def _refresh_entries(self, player):
        self.entries = []
        want_weapons = (self.category_index == 1)
        for key in player.inventory:
            is_weapon = key in WEAPON_KEYS
            if is_weapon != want_weapons:
                continue
            info = (WEAPON_INFO if is_weapon else ITEM_INFO).get(
                key, {"name": key.upper(), "desc": "Sin descripción."})
            self.entries.append({
                "key": key,
                "kind": "weapon" if is_weapon else "item",
                "name": info["name"],
                "desc": info["desc"],
                "sprite": info.get("sprite"),
            })

    def _entry_tag(self, entry, player):
        if entry["key"] == "cardboard_box" and player.is_disguised:
            return "PUESTA"
        if entry["kind"] == "weapon":
            manager = self._weapon_manager(player)
            if manager is not None and manager.current_id == entry["key"]:
                return "EQUIPADA"
        return None

    def handle_input(self, event, player):
        if event.type != pygame.KEYDOWN:
            return None

        key = event.key
        if key in (pygame.K_i, pygame.K_ESCAPE):
            return "CLOSE"

        up = key in (pygame.K_UP, pygame.K_w)
        down = key in (pygame.K_DOWN, pygame.K_s)

        if not self.in_entries:
            if up or down:
                self.category_index = (self.category_index + (1 if down else -1)) % len(CATEGORIES)
                self.entry_index = 0
                self._refresh_entries(player)
            elif key in (pygame.K_RETURN, pygame.K_RIGHT, pygame.K_d):
                self.in_entries = True
                self.entry_index = 0
        else:
            if (up or down) and self.entries:
                self.entry_index = (self.entry_index + (1 if down else -1)) % len(self.entries)
            elif key in (pygame.K_LEFT, pygame.K_a, pygame.K_BACKSPACE):
                self.in_entries = False
            elif key == pygame.K_RETURN and self.entries:
                # Equipar un arma cierra el inventario para volver directo al juego.
                if self._use_entry(player):
                    return "CLOSE"
        return None

    def _use_entry(self, player):
        """Devuelve True si hay que cerrar el inventario después de usar la entrada."""
        entry = self.entries[self.entry_index]
        if entry["key"] == "cardboard_box":
            player.toggle_box_disguise()
        elif entry["kind"] == "weapon":
            manager = self._weapon_manager(player)
            if manager is None:
                return False
            if manager.current_id == entry["key"]:
                return True             # Ya la tenía equipada: solo cierra.
            return manager.equip(entry["key"])
        return False

    def _wrap(self, text, font, max_width):
        lines, line = [], ""
        for word in text.split(" "):
            test = f"{line} {word}".strip()
            if font.size(test)[0] <= max_width:
                line = test
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
        return lines

    def _entry_icon(self, entry, player):
        if entry["kind"] != "weapon":
            return None
        manager = self._weapon_manager(player)
        if manager is None or entry["key"] not in manager.weapons:
            return None
        return manager.weapons[entry["key"]].icon

    def _draw_row(self, surface, rect, text, font, state, tag=None, icon=None):
        """state: "normal", "outline" (categoría activa mientras elegís un elemento) o "selected"."""
        if state == "selected":
            pygame.draw.rect(surface, COLOR_ROW_SELECTED, rect)
            text_color = COLOR_ROW_SELECTED_TEXT
        else:
            pygame.draw.rect(surface, COLOR_ROW_BG, rect)
            border = COLOR_ROW_SELECTED if state == "outline" else COLOR_ROW_BORDER
            pygame.draw.rect(surface, border, rect, 2 if state == "outline" else 1)
            text_color = COLOR_ROW_TEXT

        icon_box = pygame.Rect(rect.x + 14, rect.centery - 7, 34, 14)
        if icon is not None:
            # Ícono del arma ajustado a la cajita, sin deformarlo.
            scale = min(icon_box.w / icon.get_width(), icon_box.h / icon.get_height())
            size = (max(1, int(icon.get_width() * scale)), max(1, int(icon.get_height() * scale)))
            small = pygame.transform.scale(icon, size)
            surface.blit(small, small.get_rect(center=icon_box.center))
        else:
            pygame.draw.rect(surface, COLOR_ICON, icon_box)
            pygame.draw.rect(surface, COLOR_ROW_BORDER, icon_box, 1)

        label = font.render(text, True, text_color)
        surface.blit(label, (rect.x + 62, rect.centery - label.get_height() // 2))

        if tag:
            tag_surface = self.font_small.render(tag, True, text_color)
            surface.blit(tag_surface, (rect.right - tag_surface.get_width() - 14,
                                       rect.centery - tag_surface.get_height() // 2))

    def _preview_image(self, player):
        entry = self.entries[self.entry_index] if (self.in_entries and self.entries) else None
        if entry and entry["key"] == "cardboard_box" and getattr(player, "box_sprite", None):
            return player.box_sprite
        if entry and entry["kind"] == "weapon":
            # Snake con el arma elegida (m16, stinger, etc.); si no hay sprites, el de pistola.
            manager = self._weapon_manager(player)
            anims = getattr(player, "weapon_animations", {})
            if manager is not None and entry["key"] in manager.weapons:
                frames = anims.get(manager.weapons[entry["key"]].sprite_set)
                if frames:
                    return frames["RIGHT"][0]
            if getattr(player, "gun_animations", None):
                return player.gun_animations["RIGHT"][0]
        return player.animations["IDLE"]["DOWN"]

    def _load_sprite(self, path):
        if path not in self._sprite_cache:
            try:
                self._sprite_cache[path] = pygame.image.load(path).convert_alpha()
            except Exception as e:
                print(f"AVISO: no se pudo cargar {path} para el inventario ({e}).")
                self._sprite_cache[path] = None
        return self._sprite_cache[path]
    
    def draw(self, surface, player, health_bar):
        surface.blit(self.background, (0, 0))

        health_bar.draw(surface, player)

        image = self._preview_image(player)
        box = 300
        scale = min(box / max(image.get_width(), 1), box / max(image.get_height(), 1))
        big = pygame.transform.scale(image, (int(image.get_width() * scale), int(image.get_height() * scale)))
        surface.blit(big, big.get_rect(center=self.ring_center))

        x0 = self.w - 480
        row_w = 440
        y = 170
        for i, category in enumerate(CATEGORIES):
            if self.in_entries and i != self.category_index:
                continue
            rect = pygame.Rect(x0, y, row_w, 54)
            if i == self.category_index:
                state = "outline" if self.in_entries else "selected"
            else:
                state = "normal"
            self._draw_row(surface, rect, category["name"], self.font_title, state)
            y += 64

        if self.in_entries:
            y += 20
            if self.entries:
                for i, entry in enumerate(self.entries):
                    rect = pygame.Rect(x0 + 30, y, row_w - 30, 46)
                    state = "selected" if i == self.entry_index else "normal"
                    self._draw_row(surface, rect, entry["name"], self.font_row, state,
                                   tag=self._entry_tag(entry, player),
                                   icon=self._entry_icon(entry, player))
                    y += 54
            else:
                empty = self.font_row.render("- VACÍO -", True, COLOR_ROW_DISABLED)
                surface.blit(empty, (x0 + 30, y + 10))

        bar_h = 150
        bar_y = self.h - bar_h
        pygame.draw.rect(surface, COLOR_BAR_BG, (0, bar_y, self.w, bar_h))
        pygame.draw.line(surface, COLOR_ROW_BORDER, (0, bar_y), (self.w, bar_y), 2)

        if self.in_entries and self.entries:
            entry = self.entries[self.entry_index]
            title_text, desc_text = entry["name"], entry["desc"]
        else:
            category = CATEGORIES[self.category_index]
            title_text, desc_text = category["name"], category["desc"]

        title = self.font_title.render(title_text, True, COLOR_ROW_TEXT)
        surface.blit(title, (self.w // 2 - title.get_width() // 2, bar_y + 26))
        for n, line in enumerate(self._wrap(desc_text, self.font_small, self.w - 400)):
            text = self.font_small.render(line, True, COLOR_ROW_TEXT)
            surface.blit(text, (self.w // 2 - text.get_width() // 2, bar_y + 70 + n * 24))

        hint = self.font_small.render("W/S: mover    ENTER: equipar    A: volver    I: cerrar", True, COLOR_TITLE)
        surface.blit(hint, (self.w - hint.get_width() - 24, self.h - hint.get_height() - 12))