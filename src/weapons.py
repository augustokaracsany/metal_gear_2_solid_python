"""Sistema de armas: Beretta, M16 (auto/semi/ráfaga), Micro UZI y el Stinger (ver weapon_stinger.py)."""
import os
import pygame
from src import weapon_settings as WS


# ====================================================================== UTILIDADES
def find_file(folder, keyword, exts):
    """Busca en `folder` un archivo cuyo nombre contenga `keyword` y termine en alguna de `exts`."""
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return None
    keyword = keyword.lower()
    for name in names:
        low = name.lower()
        if keyword in low and low.endswith(exts):
            return os.path.join(folder, name)
    return None


def load_sound(folder, keyword, volume=0.6):
    """Devuelve un Sound o None (si falta el archivo el juego sigue en silencio)."""
    path = find_file(folder, keyword, (".wav", ".ogg", ".mp3"))
    if not path:
        return None
    try:
        snd = pygame.mixer.Sound(path)
        snd.set_volume(volume)
        return snd
    except pygame.error:
        return None


def load_icon(keyword):
    path = find_file(WS.WEAPON_ICON_DIR, keyword, (".png", ".jpg", ".jpeg", ".webp"))
    if not path:
        return None
    try:
        return pygame.image.load(path).convert_alpha()
    except pygame.error:
        return None


def play(snd):
    if not snd:
        return None
    ch = snd.play()
    if ch is None:                              # los canales estaban todos ocupados
        ch = pygame.mixer.find_channel(True)    # fuerza el canal más viejo
        if ch:
            ch.play(snd)
    return ch

# ====================================================================== ARMAS DE FUEGO
class Firearm:
    kind = "firearm"
    blocks_movement = False
    wants_unequip = False

    def __init__(self, wid):
        cfg = WS.WEAPON_DEFS[wid]
        self.id = wid
        self.name = cfg["name"]
        self.sprite_set = cfg["sprite_set"]
        self.mag_size = cfg["mag_size"]
        self.mag = self.mag_size
        self.reserve = cfg["reserve"]
        self.modes = list(cfg["modes"])
        self.mode_index = 0
        self.interval = cfg["interval"]
        self.reload_time = cfg["reload_time"]
        self.damage_mult = cfg["damage_mult"]

        self.icon = load_icon(cfg["icon_keyword"])
        self.snd_fire = load_sound(WS.WEAPON_SOUND_DIR, f"{wid}_fire")
        self.snd_reload = load_sound(WS.WEAPON_SOUND_DIR, f"{wid}_reload")
        self.snd_empty = (load_sound(WS.WEAPON_SOUND_DIR, f"{wid}_empty")
                          or load_sound(WS.WEAPON_SOUND_DIR, "empty"))
        self.snd_mode = load_sound(WS.WEAPON_SOUND_DIR, "mode_switch")

        self.cooldown = 0.0
        self.burst_left = 0
        self.reloading = False
        self.reload_timer = 0.0

    # ---- estado
    @property
    def mode(self):
        return self.modes[self.mode_index]

    def cycle_mode(self):
        if len(self.modes) < 2 or self.burst_left > 0:
            return
        self.mode_index = (self.mode_index + 1) % len(self.modes)
        play(self.snd_mode)

    def add_ammo(self, amount):
        self.reserve += amount

    def start_reload(self):
        if self.reloading or self.mag >= self.mag_size or self.reserve <= 0:
            return
        self.reloading = True
        self.reload_timer = self.reload_time
        self.burst_left = 0
        play(self.snd_reload)

    def _finish_reload(self):
        take = min(self.mag_size - self.mag, self.reserve)
        self.mag += take
        self.reserve -= take
        self.reloading = False

    def on_equip(self, player):
        pass

    def on_unequip(self, player):
        # Cambiar de arma cancela la recarga y la ráfaga en curso.
        self.reloading = False
        self.burst_left = 0

    # ---- loop
    def update(self, dt, pressed, held, shoot, **_):
        self.cooldown = max(0.0, self.cooldown - dt)

        if self.reloading:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                self._finish_reload()
            return

        if self.burst_left > 0:
            if self.cooldown <= 0:
                self._fire(shoot, in_burst=True)
            return

        mode = self.mode
        wants = held if mode == "AUTO" else pressed
        if not wants or self.cooldown > 0:
            return

        if self.mag <= 0:
            if pressed:
                play(self.snd_empty)
                if getattr(WS, "AUTO_RELOAD", False):
                    self.start_reload()
            return

        if mode == "BURST":
            self.burst_left = WS.BURST_COUNT
        self._fire(shoot, in_burst=(mode == "BURST"))

    def _fire(self, shoot, in_burst):
        self.mag -= 1
        play(self.snd_fire)
        shoot(self.damage_mult)
        if in_burst:
            self.burst_left -= 1
            if self.burst_left <= 0 or self.mag <= 0:
                self.burst_left = 0
                self.cooldown = WS.BURST_PAUSE
            else:
                self.cooldown = WS.BURST_INTERVAL
        else:
            self.cooldown = self.interval
        # Cargador vacío: recarga sola si hay reserva
        if (getattr(WS, "AUTO_RELOAD", False)
                and self.mag <= 0 and self.burst_left == 0 and self.reserve > 0):
            self.start_reload()

    # ---- datos para el HUD
    def hud_info(self):
        return {
            "name": self.name,
            "icon": self.icon,
            "main": str(self.mag),
            "sub": f"/{self.reserve}",
            "modes": [WS.MODE_LABELS[m] for m in self.modes],
            "mode_index": self.mode_index,
            "progress": (1 - self.reload_timer / self.reload_time) if self.reloading else None,
            "low": self.mag <= max(1, int(self.mag_size * 0.2)),
        }


# ====================================================================== MANAGER
class WeaponManager:
    def __init__(self, player=None, starting=None):
        from src.weapon_stinger import StingerLauncher   # import tardío: evita ciclo

        self.player = player
        self.weapons = {wid: Firearm(wid) for wid in WS.WEAPON_DEFS}
        self.weapons["stinger"] = StingerLauncher()

        # Si falta el sonido propio de un arma, usa el disparo que ya tenía Player.
        fallback = getattr(player, "shoot_sound", None)
        if fallback:
            for w in self.weapons.values():
                if w.kind == "firearm" and w.snd_fire is None:
                    w.snd_fire = fallback

        self.owned = list(starting if starting is not None else WS.STARTING_WEAPONS)
        self.current_id = self.owned[0]
        self.last_firearm_id = self.current_id
        self.popup_timer = 0.0      # cuánto tiempo se ven las cajitas de arma anterior/siguiente
        self.notices = []           # [texto, tiempo restante]
        self._fire_pressed = False

    # ---- acceso
    @property
    def current(self):
        return self.weapons[self.current_id]

    @property
    def blocks_movement(self):
        return self.current.blocks_movement

    @property
    def facing_override(self):
        """Dirección que debe usar el sprite de Snake (el Stinger apunta con el mouse), o None."""
        return getattr(self.current, "facing", None)

    def camera_offset(self):
        """Desplazamiento de cámara (Vector2) mientras apunta con el Stinger, o None."""
        return getattr(self.current, "cam_offset", None)

    def neighbors(self):
        n = len(self.owned)
        if n < 2:
            return None, None
        i = self.owned.index(self.current_id)
        return self.weapons[self.owned[(i - 1) % n]], self.weapons[self.owned[(i + 1) % n]]

    def notify(self, text):
        self.notices.append([text, WS.NOTICE_TIME])

    # ---- inventario de armas
    def add_weapon(self, wid):
        if wid in self.owned:
            return False
        self.owned.append(wid)      # misma lista que lee inventory.py via player.weapons
        return True

    def add_ammo(self, wid, amount):
        weapon = self.weapons[wid]
        if wid == "stinger":
            weapon.missiles += amount
        else:
            weapon.add_ammo(amount)

    def equip(self, wid):
        if wid not in self.owned or wid == self.current_id:
            return False
        new = self.weapons[wid]
        # El Stinger exige estar de pie y sin caja.
        if (new.kind == "launcher" and self.player is not None
                and hasattr(self.player, "can_use_weapon") and not self.player.can_use_weapon()):
            self.notify("NO PODÉS USARLO AHORA")
            return False
        self.current.on_unequip(self.player)
        self.current_id = wid
        if new.kind == "firearm":
            self.last_firearm_id = wid
        new.on_equip(self.player)
        self.popup_timer = WS.HUD_POPUP_TIME
        return True

    def cycle(self, step=1):
        if len(self.owned) < 2:
            return
        i = self.owned.index(self.current_id)
        self.equip(self.owned[(i + step) % len(self.owned)])

    # ---- mouse (pausa / inventario / menú)
    def suspend(self):
        if hasattr(self.current, "suspend"):
            self.current.suspend()

    def resume(self):
        if hasattr(self.current, "resume"):
            self.current.resume()

    def shutdown(self):
        """Deja el mouse como estaba (llamar al salir del nivel o reiniciar)."""
        self.current.on_unequip(self.player)

    # ---- eventos / loop
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in WS.KEY_NEXT_WEAPON:
                self.cycle(1)
            elif event.key == WS.KEY_RELOAD and hasattr(self.current, "start_reload"):
                self.current.start_reload()
            elif event.key == WS.KEY_FIRE_MODE and hasattr(self.current, "cycle_mode"):
                self.current.cycle_mode()
            elif event.key == WS.KEY_FIRE:
                self._fire_pressed = True
        if hasattr(self.current, "handle_event"):
            self.current.handle_event(event)

    def update(self, dt, shoot, can_fire=True, target=None, projectiles=None):
        """shoot(damage_mult) crea la bala. target = el Hind. projectiles = grupo de misiles."""
        keys = pygame.key.get_pressed()
        held = bool(keys[WS.KEY_FIRE]) and can_fire
        pressed = self._fire_pressed and can_fire
        self._fire_pressed = False

        self.current.update(dt, pressed, held, shoot,
                            player=self.player, target=target, projectiles=projectiles)

        if getattr(self.current, "wants_unequip", False):
            self.equip(self.last_firearm_id)

        self.popup_timer = max(0.0, self.popup_timer - dt)
        for notice in self.notices:
            notice[1] -= dt
        self.notices = [n for n in self.notices if n[1] > 0]

    # ---- cámara / dibujo (solo el Stinger usa estos)
    def constrain_aim(self, camera, virtual_w, virtual_h):
        """Llamar DESPUÉS de camera.update(): evita que la mira se salga de la pantalla."""
        if hasattr(self.current, "constrain_to_screen"):
            self.current.constrain_to_screen(camera, virtual_w, virtual_h)

    def draw_overlay(self, surface, camera, scale=1):
        """Mira del Stinger. `surface` = pantalla real; scale = pantalla real / superficie virtual."""
        if hasattr(self.current, "draw_overlay"):
            self.current.draw_overlay(surface, camera, scale)


# ====================================================================== PICKUPS EN EL MAPA
class WeaponPickup(pygame.sprite.Sprite):
    """Objeto del piso (compatible con items_group: tiene name, image y rect)."""

    def __init__(self, name, center, uid=None):
        super().__init__()
        self.name = name
        self.pickup_id = uid
        self.image = _pickup_image(name)
        self.rect = self.image.get_rect(center=center)

def _load_pickup_png(name):
    """PNG del pickup: <PICKUP_ICON_DIR>/<nombre del objeto de Tiled>.png, o None."""
    path = os.path.join(WS.PICKUP_ICON_DIR, name + ".png")
    if not os.path.exists(path):
        return None
    try:
        img = pygame.image.load(path).convert_alpha()
    except pygame.error:
        return None
    k = WS.PICKUP_ICON_SCALE
    if k != 1:
        img = pygame.transform.scale(img, (img.get_width() * k, img.get_height() * k))
    return img

def _pickup_image(name):
    img = _load_pickup_png(name)
    if img is not None:
        return img
    if name == "stinger_launcher":
        icon = load_icon("stinger")
        if icon:
            w = 44
            h = max(1, int(icon.get_height() * w / icon.get_width()))
            return pygame.transform.scale(icon, (w, h))
        s = pygame.Surface((48, 12), pygame.SRCALPHA)
        pygame.draw.rect(s, (90, 98, 84), (0, 3, 48, 6))
        pygame.draw.rect(s, (40, 46, 38), (0, 3, 48, 6), 1)
        pygame.draw.rect(s, (60, 66, 56), (30, 0, 8, 12))
        return s
    


def make_pickup(name, center, uid=None):
    return WeaponPickup(name, center, uid)


# La clave es el nombre del objeto de Tiled (y Item.name).
PICKUPS = {
    "stinger_launcher": {"weapon": "stinger", "msg": "OBTENIDO: FIM-92 STINGER"},
    "stinger_missiles": {"ammo": ("stinger", WS.STINGER_MISSILES_PER_PICKUP),
                         "msg": "MISILES STINGER x{n}"},
    "ammo_beretta": {"ammo": ("beretta", 15), "msg": "MUNICIÓN BERETTA x{n}"},
    "ammo_m16": {"ammo": ("m16", 30), "msg": "MUNICIÓN M16 x{n}"},
    "ammo_uzi": {"ammo": ("uzi", 32), "msg": "MUNICIÓN UZI x{n}"},
}


def collect_pickups(player_rect, items, manager, reach=20):
    """Recoge armas/munición al acercarse (los camiones suelen ser sólidos, por eso `reach`).
    Devuelve la lista de pickup_id recogidos (para no volver a generarlos al recargar el mapa)."""
    collected = []
    for item in list(items):
        spec = PICKUPS.get(getattr(item, "name", None))
        if not spec:
            continue
        if not player_rect.colliderect(item.rect.inflate(reach * 2, reach * 2)):
            continue
        n = 0
        if "weapon" in spec:
            manager.add_weapon(spec["weapon"])
        if "ammo" in spec:
            wid, n = spec["ammo"]
            manager.add_ammo(wid, n)
        manager.notify(spec["msg"].format(n=n))
        collected.append(getattr(item, "pickup_id", None))
        item.kill()
    return collected