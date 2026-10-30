# Configuración de la pantalla/ventana. 
SCREEN_WIDTH = 1360
SCREEN_HEIGHT = 768
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

HEALTH_BAR_WIDTH = 300            # Largo total (también el de la línea fina).
HEALTH_BAR_HEIGHT = 20            # Grosor de la barra gruesa.
HEALTH_BAR_MARGIN_BOTTOM = 30     # Distancia al borde inferior de la pantalla.
HEALTH_LABEL_TEXT = "SOLID PYTHON"
HEALTH_LABEL_SIZE = 30            # Tamaño del texto de arriba.
HEALTH_NUMBER_SIZE = 40           # Tamaño del número de la derecha.
HEALTH_NUMBER_GAP = 14            # Espacio entre la barra y el número.
HEALTH_NUMBER_RESERVED = 55       # Ancho reservado para el número (entran 3 dígitos).
HEALTH_TICKS = 10                 # Cantidad de marcas sobre la línea fina.

# Posición: el conjunto ( Barra + Número. ). 
HEALTH_BAR_X = 20
HEALTH_BAR_Y = 40

# Colores.
COLOR_HEALTH_FILL = (225, 225, 225)       # Barra gruesa.
COLOR_HEALTH_HIGHLIGHT = (255, 255, 255)  # Brillo en la parte de arriba de la barra.
COLOR_HEALTH_LOW = (220, 40, 40)          # Barra cuando la vida es 30% o menos.
COLOR_HEALTH_LINE = (190, 190, 190)       # Línea fina y marcas.
COLOR_HEALTH_SHADOW = (0, 0, 0)           # Sombra para que se lea sobre cualquier mapa.

# Disparo.
PLAYER_SHOOT_COOLDOWN = 400       # ms mínimos entre un disparo y otro.
BULLET_SPEED = 600                # px/seg.
BULLET_STEP = 4                   # La bala avanza de a 4 px para no atravesar paredes finas.
BULLET_LENGTH = 8                 # Largo de la bala.
BULLET_THICKNESS = 3              # Grosor de la bala.
BULLET_DAMAGE = 100
BULLET_COLOR = (255, 230, 120)
BULLET_HIT_PADDING = 12           # Agranda la hitbox del enemigo para que sea menos difícil pegarle.
BULLET_DRAW_OFFSET_Y = 34         # Solo visual: dibuja la bala más arriba, a la altura del arma.

# Enemigos.
ENEMY_MAX_HEALTH = 100            # Con daño 25 mueren a los 4 disparos.

# Sprites de Snake con arma.
PLAYER_GUN_SPRITES_PATH = "assets/sprites/solid_python/"
PLAYER_GUN_SHOW_TIME = 600   # ms que se ve la pose con arma después de disparar.

# Sonido del disparo.
SHOOT_SOUND_PATH = "assets/audio/sfx/gunshot.wav"   # CAMBIAR por el nombre y extensión reales de tu archivo.
SHOOT_SOUND_VOLUME = 0.1                             # De 0.0 (mudo) a 1.0 (volumen máximo).

# Golpe.
PUNCH_RANGE = 24                              # Alcance del puño delante de Snake (px).
PUNCH_HIT_PADDING = 12                        # Agranda la hitbox del enemigo para que sea menos difícil pegarle.
PUNCH_DAMAGE = (ENEMY_MAX_HEALTH + 2) // 3    # Un tercio de la vida del enemigo, redondeado para arriba: 3 golpes lo matan.
PUNCH_STUN_TIME = 1.5   # Segundos que el enemigo queda quieto después de recibir un golpe.

# Sonido del golpe.
PUNCH_SOUND_PATH = "assets/audio/sfx/punch.wav"   # CAMBIAR si el archivo tiene otro nombre o extensión.
PUNCH_SOUND_VOLUME = 0.5                          # De 0.0 (mudo) a 1.0 (volumen máximo).

# Lluvia (misión 1).
RAIN_DROPS = 170                  # Cantidad de gotas en pantalla.
RAIN_SPEED_MIN = 280              # Velocidad de caída (px/seg en la pantalla virtual).
RAIN_SPEED_MAX = 420
RAIN_LENGTH_MIN = 4               # Largo de cada gota.
RAIN_LENGTH_MAX = 9
RAIN_WIND = -70                   # Inclinación: negativo = cae hacia la izquierda, positivo = derecha, 0 = vertical.
RAIN_COLOR = (140, 175, 235)
RAIN_TINT_COLOR = (25, 55, 110)    # Color del velo oscuro que da clima de tormenta.
RAIN_TINT_ALPHA = 55              # Intensidad del velo (0 = sin velo, 100 = muy oscuro).