"""Toda la configuración del sistema de armas. Tocá acá para balancear."""
import pygame

# ----------------------------------------------------------------- RUTAS
WEAPON_ICON_DIR   = "assets/sprites/weapons"
WEAPON_SOUND_DIR  = "assets/audio/weapons"
STINGER_SOUND_DIR = "assets/audio/stinger"
SOLID_SPRITE_DIR  = "assets/sprites/solid_python"
UI_FONT_BOLD      = "assets/fonts/PixelOperator8-Bold.ttf"
UI_FONT           = "assets/fonts/PixelOperator8.ttf"
PICKUP_ICON_DIR   = "assets/sprites/pickups"
PICKUP_ICON_SCALE = 2

# ----------------------------------------------------------------- TECLAS
KEY_NEXT_WEAPON = (pygame.K_1, pygame.K_KP1)
KEY_RELOAD      = pygame.K_r
KEY_FIRE_MODE   = pygame.K_f
KEY_FIRE        = pygame.K_SPACE

AUTO_RELOAD = False

# ----------------------------------------------------------------- ARMAS DE FUEGO
WEAPON_DEFS = {
    "beretta": {
        "name": "BERETTA M92FS", "icon_keyword": "beretta", "sprite_set": "gun",
        "mag_size": 15, "reserve": 45, "modes": ["SEMI"],
        "interval": 0.28, "reload_time": 1.4, "damage_mult": 1.0,
        "blocks_movement": False,
        "hud_tag": "CQC",
    },
    "m16": {
        "name": "M16", "icon_keyword": "m16", "sprite_set": "m16",
        "mag_size": 30, "reserve": 90, "modes": ["AUTO", "SEMI", "BURST"],
        "interval": 0.10, "reload_time": 2.0, "damage_mult": 1.0,
        "blocks_movement": True,
        "hud_tag": "DMG",
    },
    "uzi": {
        "name": "MICRO UZI", "icon_keyword": "uzi", "sprite_set": "gun",
        "mag_size": 32, "reserve": 96, "modes": ["AUTO"],
        "interval": 0.065, "reload_time": 1.6, "damage_mult": 1.0,
        "blocks_movement": False,
        "hud_tag": "CQC",
    },
}
MODE_LABELS = {"AUTO": "AUTO", "SEMI": "SEMI", "BURST": "RÁFAGA"}

BURST_COUNT    = 3
BURST_INTERVAL = 0.06
BURST_PAUSE    = 0.28

STARTING_WEAPONS = ["beretta", "m16", "uzi", "stinger"]

# ----------------------------------------------------------------- STINGER
STINGER_DAMAGE              = 50
STINGER_MISSILES_PER_PICKUP = 8
HIND_ALTITUDE               = 90

STINGER_AIM_RANGE_X      = 400
STINGER_AIM_RANGE_Y      = 300
STINGER_SENSITIVITY      = 0.5
STINGER_CAMERA_FOLLOW    = 0.75
STINGER_SCREEN_MARGIN    = 24

STINGER_LOCK_RADIUS        = 46
STINGER_LOCK_TIME          = 1.5   # reducido de 2.5 → más ágil
STINGER_LOCK_GRACE         = 0.5   # aumentado de 0.30 → más tolerante al movimiento
STINGER_LOCK_BEEP_INTERVAL = 0.25

MISSILE_START_SPEED = 120.0
MISSILE_MAX_SPEED   = 520.0
MISSILE_ACCEL       = 380.0
MISSILE_TURN_RATE   = 5.0
MISSILE_HIT_RADIUS  = 14
MISSILE_LIFETIME    = 8.0
MISSILE_TRAIL_LIFE  = 0.6
EXPLOSION_RADIUS    = 56
EXPLOSION_LIFE      = 0.5

# ----------------------------------------------------------------- HUD
HUD_MARGIN            = 24
HUD_BOX_W, HUD_BOX_H = 250, 104
HUD_SMALL_W, HUD_SMALL_H = 120, 58
HUD_POPUP_TIME        = 2.0
NOTICE_TIME           = 2.5

HUD_BULLET_W         = 3
HUD_BULLET_H         = 6
HUD_BULLET_GAP       = 1
HUD_BULLET_ROWS      = 2
HUD_BULLET_COLOR_ON  = (232, 232, 226)
HUD_BULLET_COLOR_OFF = ( 55,  65,  58)