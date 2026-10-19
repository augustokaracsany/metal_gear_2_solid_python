# Configuración de la pantalla/ventana. 
SCREEN_WIDTH = 768
SCREEN_HEIGHT = 672
FPS = 60

# Velocidad de movimiento ( En píxeles por segundo, independiente de los FPS. )
PLAYER_SPEED = 500  # Se puede subir o bajar según qué tan rápido quieren que corra el Snake.
# Velocidad = 500

# Colores del MENÚ.
COLOR_BG = (0, 0, 0) # Color de Fondo BackGround, Negro.
COLOR_TEXT = (240, 240, 240)
COLOR_ACCENT = (50, 205, 50)  # Verde.
COLOR_HOVER = (255, 215, 0)   # Amarillo <- HOVER/Selección.
COLOR_DISABLED = (80, 80, 80)

ENEMY_SPEED = 40

# Vida del jugador y barra de vida (HUD).
PLAYER_MAX_HEALTH = 100
PLAYER_INVULNERABLE_TIME = 1000   # ms de invulnerabilidad después de recibir daño.
ENEMY_CONTACT_DAMAGE = 10         # Daño provisional por tocar a un enemigo.

HEALTH_BAR_WIDTH = 220            # Largo total (también el de la línea fina).
HEALTH_BAR_HEIGHT = 8             # Grosor de la barra gruesa.
HEALTH_BAR_MARGIN_BOTTOM = 30     # Distancia al borde inferior de la pantalla.
HEALTH_LABEL_TEXT = "SNAKE"
HEALTH_LABEL_SIZE = 16            # Tamaño del texto de arriba.
HEALTH_NUMBER_SIZE = 40           # Tamaño del número de la derecha.
HEALTH_NUMBER_GAP = 14            # Espacio entre la barra y el número.
HEALTH_NUMBER_RESERVED = 55       # Ancho reservado para el número (entran 3 dígitos).
HEALTH_TICKS = 10                 # Cantidad de marcas sobre la línea fina.

# Posición: el conjunto (barra + número) queda centrado y abajo.
HEALTH_BAR_X = (SCREEN_WIDTH - (HEALTH_BAR_WIDTH + HEALTH_NUMBER_GAP + HEALTH_NUMBER_RESERVED)) // 2
HEALTH_BAR_Y = SCREEN_HEIGHT - HEALTH_BAR_MARGIN_BOTTOM - HEALTH_BAR_HEIGHT

# Colores.
COLOR_HEALTH_FILL = (225, 225, 225)       # Barra gruesa.
COLOR_HEALTH_HIGHLIGHT = (255, 255, 255)  # Brillo en la parte de arriba de la barra.
COLOR_HEALTH_LOW = (220, 40, 40)          # Barra cuando la vida es 30% o menos.
COLOR_HEALTH_LINE = (190, 190, 190)       # Línea fina y marcas.
COLOR_HEALTH_SHADOW = (0, 0, 0)           # Sombra para que se lea sobre cualquier mapa.