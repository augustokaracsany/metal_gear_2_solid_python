import traceback
import pygame


class VentTransition:
    """
    Entrada/salida de ductos de ventilación.

    Secuencia: cuerpo a tierra -> se arrastra al centro del agujero
    -> fundido a negro -> carga del mapa -> fundido de vuelta.

    Propiedades del objeto de Tiled (capa "triggers", "vent_trigger"):
        target_map (string), spawn_x (int), spawn_y (int),
        prone (bool): True = Snake queda cuerpo a tierra al llegar.

    Requisitos mínimos en tu jugador:
        player.rect          (pygame.Rect, o adapta a player.x / player.y)
        player.prone         (bool)
        player.input_locked  (bool)  -> tu código debe ignorar las teclas
                                        mientras sea True

    Pon debug=True para ver en la consola en qué paso va.
    """

    CRAWL_MAX = 1.2   # segundos máximos arrastrándose (evita que se trabe)

    def __init__(self, screen_size, debug=False):
        self.debug = debug
        self.state = "idle"   # idle, go_prone, crawl, fade_out, fade_in
        self.timer = 0.0
        self.fade = 0.0
        self.cooldown = 0.0
        self.target = None
        self.prone_after = False
        self.center = (0, 0)
        self.overlay = pygame.Surface(screen_size)
        self.overlay.fill((0, 0, 0))

    def _set(self, estado):
        self.state = estado
        self.timer = 0.0
        if self.debug:
            print(f"[VENT] estado -> {estado}")

    @property
    def active(self):
        return self.state != "idle"

    @property
    def can_trigger(self):
        return self.state == "idle" and self.cooldown <= 0

    def start(self, obj, player):
        """obj: objeto de pytmx de la capa 'triggers'."""
        props = obj.properties
        self.target = (
            props["target_map"],
            int(props["spawn_x"]),
            int(props["spawn_y"]),
        )
        self.prone_after = bool(props.get("prone", False))
        self.center = (obj.x + obj.width / 2, obj.y + obj.height / 2)

        if self.debug:
            print(f"[VENT] start -> {self.target}, centro={self.center}")

        player.input_locked = True
        player.prone = True
        self._set("go_prone")

    def update(self, dt, player, load_map):
        """load_map(target_map, spawn_x, spawn_y): tu función de cambio
        de mapa (la misma que usas para truck_trigger)."""
        if dt > 1:            # si tu dt viene en milisegundos
            dt /= 1000.0

        self.cooldown = max(0.0, self.cooldown - dt)

        if self.state == "go_prone":
            self.timer += dt
            if self.timer >= 0.35:
                self._set("crawl")

        elif self.state == "crawl":
            self.timer += dt
            cx, cy = self.center
            dx = cx - player.rect.centerx
            dy = cy - player.rect.centery
            dist = (dx * dx + dy * dy) ** 0.5
            paso = 45 * dt

            if dist <= max(paso, 2) or self.timer >= self.CRAWL_MAX:
                self._set("fade_out")   # llegó o se acabó el tiempo
            else:
                player.rect.centerx += round(dx / dist * paso)
                player.rect.centery += round(dy / dist * paso)

        elif self.state == "fade_out":
            self.fade = min(255.0, self.fade + 450 * dt)
            if self.fade >= 255:
                try:
                    if self.debug:
                        print(f"[VENT] cargando {self.target}")
                    load_map(*self.target)
                except Exception:
                    print("[VENT] ERROR al cargar el mapa:")
                    traceback.print_exc()
                player.prone = self.prone_after
                self._set("fade_in")

        elif self.state == "fade_in":
            self.fade = max(0.0, self.fade - 450 * dt)
            if self.fade <= 0:
                self._set("idle")
                self.cooldown = 0.6
                player.input_locked = False

    def draw(self, surface):
        if self.fade > 0:
            self.overlay.set_alpha(int(self.fade))
            surface.blit(self.overlay, (0, 0))