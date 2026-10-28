import math
import pygame


class HUDInventory:
    """
    HUD de inventario militar retro inspirado en los videojuegos
    de los años 90. Compatible con Pygame y los sprites existentes.
    """

    def __init__(self, position="bottom-right"):
        self.position = position
        self._sprite_cache = {}

        # Fuentes pixel art
        try:
            self.font_small = pygame.font.Font(
                "assets/fonts/PixelOperator8-Bold.ttf", 9
            )
            self.font_medium = pygame.font.Font(
                "assets/fonts/PixelOperator8-Bold.ttf", 10
            )
            self.font_large = pygame.font.Font(
                "assets/fonts/PixelOperator8-Bold.ttf", 13
            )
        except Exception:
            self.font_small = pygame.font.Font(None, 12)
            self.font_medium = pygame.font.Font(None, 14)
            self.font_large = pygame.font.Font(None, 17)

        # Paleta militar retro
        self.C_FONDO = (10, 14, 9)
        self.C_INTERIOR = (17, 24, 14)
        self.C_PANEL = (27, 37, 21)
        self.C_PANEL_CLARO = (38, 49, 28)

        self.C_OLIVA = (112, 132, 69)
        self.C_OLIVA_CLARO = (158, 171, 103)
        self.C_OLIVA_OSCURO = (49, 62, 34)

        self.C_TEXTO = (218, 223, 191)
        self.C_TEXTO_SECUNDARIO = (143, 157, 102)
        self.C_AMBAR = (218, 173, 79)
        self.C_AMBAR_OSCURO = (104, 68, 27)

        self.C_SOMBRA = (4, 6, 4)
        self.C_SCANLINE = (20, 28, 16)
        self.C_SEGMENTO_APAGADO = (42, 51, 32)

        # Nombres en español
        self.nombres_items = {
            "cardboard_box": "CAJA",
            "food_ration": "RACION",
            "pistola": "PISTOLA",
            "munition": "MUNICION",
            "ammo": "MUNICION",
            "ammunition": "MUNICION",
            "keycard": "TARJETA",
            "key_card": "TARJETA",
            "card": "TARJETA",
            "ration": "RACION",
            "box": "CAJA",
        }

    def _load_sprite(self, path):
        """Carga un sprite una sola vez y lo guarda en caché."""
        if not path:
            return None

        if path not in self._sprite_cache:
            try:
                self._sprite_cache[path] = (
                    pygame.image.load(path).convert_alpha()
                )
            except Exception as error:
                print(
                    f"Aviso del inventario: "
                    f"no se pudo cargar {path}: {error}"
                )
                self._sprite_cache[path] = None

        return self._sprite_cache[path]

    def _get_item_sprite(self, item_key, player):
        """Obtiene el sprite asociado a cada objeto conocido."""
        if not item_key:
            return None

        if item_key == "cardboard_box":
            return getattr(player, "box_sprite", None)

        if item_key == "food_ration":
            return self._load_sprite(
                "assets/sprites/items/racion_roja.png"
            )

        if item_key == "pistola":
            return self._load_sprite(
                "assets/sprites/weapons/pistola.png"
            )

        # Permite incorporar sprites adicionales sin cambiar el HUD.
        sprites = getattr(player, "item_sprites", {})
        if isinstance(sprites, dict):
            sprite = sprites.get(item_key)
            if sprite is not None:
                return sprite

        return None

    def _get_item_name(self, item_key):
        """Devuelve el nombre en español del objeto."""
        if not item_key:
            return "NINGUNO"

        return self.nombres_items.get(
            str(item_key).lower(),
            str(item_key).replace("_", " ").upper()
        )

    def _draw_corners(self, surface, rect):
        """Dibuja esquinas mecánicas pixeladas."""
        x, y = rect.topleft
        w, h = rect.size
        largo = 8

        esquinas = [
            (x + 3, y + 3, 1, 1),
            (x + w - 4, y + 3, -1, 1),
            (x + 3, y + h - 4, 1, -1),
            (x + w - 4, y + h - 4, -1, -1),
        ]

        for cx, cy, dx, dy in esquinas:
            pygame.draw.line(
                surface,
                self.C_OLIVA_CLARO,
                (cx, cy),
                (cx + dx * largo, cy),
                1
            )
            pygame.draw.line(
                surface,
                self.C_OLIVA_CLARO,
                (cx, cy),
                (cx, cy + dy * largo),
                1
            )

    def _draw_indicators(self, surface, x, y, active):
        """Pequeños indicadores electrónicos de estilo retro."""
        for i in range(8):
            color = (
                self.C_AMBAR
                if active and i == 0
                else (
                    self.C_OLIVA
                    if active and i < 6
                    else self.C_SEGMENTO_APAGADO
                )
            )

            pygame.draw.rect(
                surface,
                color,
                pygame.Rect(x + i * 5, y, 3, 5)
            )

    # ------------------------------------------------------------------
    # EXTRAS VISUALES PARA EL PANEL DE OBJETOS (estilo Metal Gear 2)
    # ------------------------------------------------------------------
    def _draw_item_backdrop(self, surface, content_rect, tiene_sprite):
        """Fondo táctico: rejilla de puntos y resplandor ámbar pulsante."""
        t = pygame.time.get_ticks()

        # Rejilla de puntos tipo radar / pantalla táctica
        for gx in range(content_rect.x + 4, content_rect.right - 2, 8):
            for gy in range(content_rect.y + 4, content_rect.bottom - 2, 8):
                surface.set_at((gx, gy), self.C_OLIVA_OSCURO)

        if not tiene_sprite:
            return

        # Resplandor que "respira" detrás del objeto
        pulso = (math.sin(t / 380) + 1) / 2
        glow = pygame.Surface(content_rect.size, pygame.SRCALPHA)

        for k in range(4):
            capa = glow.get_rect().inflate(-k * 14, -k * 9)
            if capa.width <= 0 or capa.height <= 0:
                break
            alpha = int(10 + k * 7 + pulso * 12)
            pygame.draw.rect(glow, (*self.C_AMBAR, alpha), capa)

        surface.blit(glow, content_rect.topleft)

    def _draw_sprite_shadow(self, surface, sprite, sprite_rect):
        """Sombra dura del sprite para darle profundidad (pygame 2+)."""
        try:
            silueta = pygame.mask.from_surface(sprite).to_surface(
                setcolor=(*self.C_SOMBRA, 255),
                unsetcolor=(0, 0, 0, 0)
            )
            surface.blit(silueta, sprite_rect.move(2, 2))
        except Exception:
            pass

    def _draw_item_overlay(self, surface, rect, content_rect):
        """Elementos llamativos encima: barrido, corchetes y etiqueta."""
        t = pygame.time.get_ticks()

        # Línea de barrido que recorre el área de imagen
        barrido_y = content_rect.y + (t // 35) % content_rect.height
        barrido = pygame.Surface((content_rect.width - 2, 1), pygame.SRCALPHA)
        barrido.fill((*self.C_OLIVA_CLARO, 70))
        surface.blit(barrido, (content_rect.x + 1, barrido_y))

        # Corchetes ámbar de "objetivo fijado" (parpadean suavemente)
        if (t // 450) % 5 != 0:
            r = content_rect.inflate(-4, -4)
            largo = 6
            for cx, cy, dx, dy in (
                (r.left, r.top, 1, 1),
                (r.right - 1, r.top, -1, 1),
                (r.left, r.bottom - 1, 1, -1),
                (r.right - 1, r.bottom - 1, -1, -1),
            ):
                pygame.draw.line(
                    surface, self.C_AMBAR,
                    (cx, cy), (cx + dx * largo, cy), 1
                )
                pygame.draw.line(
                    surface, self.C_AMBAR,
                    (cx, cy), (cx, cy + dy * largo), 1
                )


    def draw_card(
        self,
        surface,
        x,
        y,
        width,
        height,
        slot_type,
        item_key,
        sprite,
        subtitle_text=None
    ):
        """Dibuja un panel individual de armas o de objetos."""

        rect = pygame.Rect(x, y, width, height)

        # Sombra dura, propia del pixel art
        pygame.draw.rect( surface, self.C_SOMBRA, rect.move(3, 3) )

        # Marco exterior
        pygame.draw.rect( surface, self.C_OLIVA_OSCURO, rect )

        # Fondo interior
        pygame.draw.rect( surface, self.C_FONDO, rect.inflate(-4, -4) )

        # Líneas horizontales CRT
        for line_y in range(y + 24, y + height - 3, 4):
            pygame.draw.line(
                surface,
                self.C_SCANLINE,
                (x + 3, line_y),
                (x + width - 4, line_y)
            )

        # Marco doble
        pygame.draw.rect( surface, self.C_OLIVA, rect.inflate(-4, -4), 1 )

        self._draw_corners(surface, rect)

        # Cabecera militar
        header = pygame.Rect(
            x + 6,
            y + 5,
            width - 12,
            17
        )

        pygame.draw.rect(
            surface,
            self.C_PANEL,
            header
        )

        pygame.draw.line(
            surface,
            self.C_OLIVA,
            (x + 6, y + 23),
            (x + width - 7, y + 23),
            1
        )

        # Título de la categoría
        categoria = (
            "ARMAS" if slot_type == "ARMAS" else "OBJETOS"
        )

        titulo_categoria = self.font_small.render(
            categoria,
            True,
            self.C_TEXTO_SECUNDARIO
        )

        surface.blit(
            titulo_categoria,
            (x + 9, y + 9)
        )

        # Indicadores de estado
        self._draw_indicators(
            surface,
            x + width - 47,
            y + 10,
            bool(item_key)
        )

        # Nombre del objeto
        nombre = self._get_item_name(item_key)

        nombre_color = (
            self.C_AMBAR if item_key else self.C_TEXTO_SECUNDARIO
        )

        nombre_surface = self.font_medium.render( nombre, True, nombre_color)

        nombre_rect = nombre_surface.get_rect(
            center=(x + width // 2, y + height - 12)
        )

        # Área de imagen, más grande que la versión anterior
        content_rect = pygame.Rect(
            x + 8,
            y + 27,
            width - 16,
            height - 48
        )

        # Marco interior del área de imagen
        pygame.draw.rect( surface, self.C_INTERIOR, content_rect)

        pygame.draw.rect( surface, self.C_OLIVA_OSCURO, content_rect, 1)

        # NUEVO: fondo táctico y resplandor (armas y objetos)
        self._draw_item_backdrop( surface, content_rect, sprite is not None)

        # Sprite nítido, sin suavizado
        if sprite is not None:
            sw, sh = sprite.get_size()

            max_w = max(1, content_rect.width - 8)
            max_h = max(1, content_rect.height - 6)

            escala = min(
                max_w / max(sw, 1),
                max_h / max(sh, 1)
            )

            nuevo_ancho = max(1, int(sw * escala))
            nuevo_alto = max(1, int(sh * escala))

            sprite_escalado = pygame.transform.scale(
                sprite,
                (nuevo_ancho, nuevo_alto)
            )

            sprite_rect = sprite_escalado.get_rect(
                center=(
                    content_rect.centerx,
                    content_rect.centery
                )
            )

            # NUEVO: sombra dura del sprite
            self._draw_sprite_shadow(
                surface,
                sprite_escalado,
                sprite_rect
            )

            surface.blit(sprite_escalado, sprite_rect)

        # (Vacío: ya no se muestra ningún texto cuando no hay equipo)

        # Nombre del objeto en la banda inferior (solo si hay objeto)
        if item_key:
            surface.blit(nombre_surface, nombre_rect)

        # NUEVO: barrido y corchetes ámbar (armas y objetos)
        if item_key:
            self._draw_item_overlay(surface, rect, content_rect)

        # Contador de munición, si se proporciona
        if subtitle_text is not None:
            municion = self.font_small.render(
                str(subtitle_text),
                True,
                self.C_TEXTO
            )

            municion_fondo = pygame.Rect(
                x + width - municion.get_width() - 15,
                y + height - 27,
                municion.get_width() + 8,
                13
            )

            pygame.draw.rect(surface, self.C_PANEL_CLARO, municion_fondo)

            pygame.draw.rect(surface, self.C_OLIVA, municion_fondo, 1)

            surface.blit(
                municion,
                municion.get_rect(center=municion_fondo.center)
            )

        # Marca ámbar en la esquina inferior
        pygame.draw.polygon(
            surface,
            self.C_AMBAR_OSCURO,
            [
                (x + width - 10, y + height - 3),
                (x + width - 3, y + height - 10),
                (x + width - 3, y + height - 3)
            ]
        )

        pygame.draw.line(
            surface,
            self.C_AMBAR,
            (x + width - 10, y + height - 3),
            (x + width - 3, y + height - 10),
            1
        )

    def _player_is_dead(self, player):
        """Detecta si el jugador está muerto, probando nombres comunes."""
        for nombre in ("dead", "is_dead", "game_over", "muerto"):
            if getattr(player, nombre, False) is True:
                return True

        if getattr(player, "alive", True) is False:
            return True

        for nombre in ("health", "hp", "vida", "life"):
            valor = getattr(player, nombre, None)
            if isinstance(valor, (int, float)) and valor <= 0:
                return True

        return False

    def draw(self, surface, player):
        """Dibuja los paneles de armas y objetos en pantalla."""

        # NUEVO: si Snake murió, el HUD de inventario no se dibuja
        if self._player_is_dead(player):
            return

        # Mismo ancho en ambos paneles para que queden alineados
        weapon_w, weapon_h = 155, 90
        item_w, item_h = 155, 105

        spacing = 16
        margin_x, margin_y = 20, 25

        screen_w, screen_h = surface.get_size()

        # Posicionamiento
        if self.position == "bottom-right":
            x = screen_w - item_w - margin_x
            y_bottom = screen_h - item_h - margin_y
            y_top = y_bottom - spacing - weapon_h

        elif self.position == "top-right":
            x = screen_w - item_w - margin_x
            y_top = margin_y + 15
            y_bottom = y_top + weapon_h + spacing

        elif self.position == "top-left":
            x = margin_x
            y_top = margin_y + 15
            y_bottom = y_top + weapon_h + spacing

        else:
            x = margin_x
            y_bottom = screen_h - item_h - margin_y
            y_top = y_bottom - spacing - weapon_h

        # Leer equipamiento actual
        eq_weapon = getattr( player, "equipped_weapon", None)

        eq_item = getattr( player, "equipped_item", None)

        inventory = getattr(player, "inventory", [])

        # Selección automática del arma, como en la versión original
        if not eq_weapon and "pistola" in inventory:
            eq_weapon = "pistola"
            player.equipped_weapon = eq_weapon

        # Selección automática del primer objeto que no sea un arma
        if not eq_item:
            for item in inventory:
                if item != "pistola":
                    eq_item = item
                    player.equipped_item = item
                    break

        # Panel superior: armas
        weapon_sprite = self._get_item_sprite( eq_weapon, player)

        # Se conserva el contador original hasta conectar
        # la variable real de munición del jugador.
        ammo_text = "0" if eq_weapon else None

        self.draw_card( surface, x, y_top, weapon_w, weapon_h, "ARMAS", eq_weapon, weapon_sprite, ammo_text)

        # Panel inferior: objetos en mano
        item_sprite = self._get_item_sprite( eq_item, player )

        self.draw_card( surface, x, y_bottom, item_w, item_h, "OBJETOS", eq_item, item_sprite, None )