import pygame

# Textos al recoger cada ítem.
# Clave = el mismo nombre que se guarda en player.inventory.
# Valor = (línea de arriba, línea de abajo).
ITEM_MESSAGES = {
    "food_ration": ("Recogido", "Ración [Unidad B1]."),
    "cardboard_box": ("Recogido", "Caja de cartón."),
    "pistola": ("Recogido", "Pistola Beretta 92FS."),
}

FONT_PATH = "assets/fonts/PixelOperator8.ttf"   # la misma fuente del prólogo
SOUND_PATH = "assets/audio/sfx/item_obtenido.wav"

# --- Tamaño del cartel (tocá estos números para agrandar o achicar) ---
FONT_SIZE = 24            # tamaño de la letra (conviene múltiplos de 8: 16, 24, 32)
ALTO_LINEA = 32           # separación entre las dos líneas
PAD_X = 28                # margen interno izquierdo/derecho
PAD_Y = 16                # margen interno arriba/abajo
ANCHO_MINIMO = 520        # el cartel nunca es más angosto que esto
TAM_FLECHA = 16           # alto de la flecha ➤ que va antes del nombre del ítem
SEPARACION_FLECHA = 8     # espacio entre la flecha y la palabra
MARGEN_INFERIOR = 30      # distancia al borde de abajo de la pantalla

COLOR_FONDO = (24, 52, 168)       # azul del cartel
COLOR_BORDE = (214, 214, 226)     # borde claro exterior
COLOR_BORDE_INT = (10, 22, 110)   # línea azul oscuro interior
COLOR_TEXTO = (255, 255, 255)
COLOR_SOMBRA = (6, 14, 80)
COLOR_FLECHA = (255, 255, 255)


class ItemMessage:
    """Cartel azul abajo de la pantalla + sonido cuando Snake recoge un ítem."""

    DURACION_MS = 2000

    def __init__(self):
        try:
            self.font = pygame.font.Font(FONT_PATH, FONT_SIZE)
        except Exception as e:
            print(f"Aviso: no se pudo cargar la fuente del cartel de ítems: {e}")
            self.font = pygame.font.Font(None, FONT_SIZE + 8)

        try:
            self.sound = pygame.mixer.Sound(SOUND_PATH)
        except Exception as e:
            print(f"Aviso: no se pudo cargar el sonido {SOUND_PATH}: {e}")
            self.sound = None

        self.line_surfaces = []
        self.shadow_surfaces = []
        self.box_width = 0
        self.start_time = 0

    def show(self, item_name, sfx_volume=1.0):
        """Reproduce el sonido y muestra el cartel del ítem (si tiene texto definido)."""
        if self.sound:
            try:
                self.sound.set_volume(sfx_volume)
                self.sound.play()
            except pygame.error:
                pass

        lines = ITEM_MESSAGES.get(item_name)
        if lines is None:
            return

        self.line_surfaces = [self.font.render(t, True, COLOR_TEXTO) for t in lines]
        self.shadow_surfaces = [self.font.render(t, True, COLOR_SOMBRA) for t in lines]
        # El ancho se ajusta al texto más largo.
        ancho_flecha = int(TAM_FLECHA * 0.9) + SEPARACION_FLECHA
        anchos = [s.get_width() for s in self.line_surfaces]
        anchos[-1] += ancho_flecha         # la última línea (el nombre del ítem) lleva la flecha adelante
        ancho_texto = max(anchos)
        self.box_width = max(ANCHO_MINIMO, ancho_texto + PAD_X * 2)
        self.start_time = pygame.time.get_ticks()

    def draw(self, surface):
        if not self.line_surfaces:
            return
        if pygame.time.get_ticks() - self.start_time >= self.DURACION_MS:
            self.line_surfaces = []
            self.shadow_surfaces = []
            return

        w, h = surface.get_size()
        box_h = PAD_Y * 2 + ALTO_LINEA * len(self.line_surfaces)
        rect = pygame.Rect(0, 0, self.box_width, box_h)
        rect.midbottom = (w // 2, h - MARGEN_INFERIOR)

        pygame.draw.rect(surface, COLOR_FONDO, rect)
        pygame.draw.rect(surface, COLOR_BORDE, rect, 3)
        pygame.draw.rect(surface, COLOR_BORDE_INT, rect.inflate(-8, -8), 2)

        for i, (txt, sombra) in enumerate(zip(self.line_surfaces, self.shadow_surfaces)):
            x = rect.x + PAD_X
            y = rect.y + PAD_Y + i * ALTO_LINEA

            if i == len(self.line_surfaces) - 1:
                # Flecha ➤ antes del nombre del ítem (segunda línea)
                largo = int(TAM_FLECHA * 0.9)
                mitad = TAM_FLECHA // 2
                cy = y + txt.get_height() // 2
                puntos = [
                    (x, cy - mitad),                  # esquina de arriba
                    (x + largo, cy),                  # punta
                    (x, cy + mitad),                  # esquina de abajo
                    (x + int(largo * 0.3), cy),       # muesca de atrás
                ]
                pygame.draw.polygon(surface, COLOR_SOMBRA, [(px + 2, py + 2) for px, py in puntos])
                pygame.draw.polygon(surface, COLOR_FLECHA, puntos)
                x += largo + SEPARACION_FLECHA

            surface.blit(sombra, (x + 2, y + 2))
            surface.blit(txt, (x, y))