import sys
import pygame
import pytmx
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT


def _smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class VentCinematic:
    TMX_PATH = "assets/sprites/maps/cinematic_building1.tmx"
    BG_PATH = "assets/sprites/maps/cinematic_building1.png"     # ajustá la ruta
    MAP_SCALE = 2

    SOLDIER_SPRITE = "assets/sprites/red_beret/look_down1.png"
    PRISONER_SPRITES = [
        "assets/sprites/prisoners/lau_walkdown1.png",     # prisioner1
        "assets/sprites/prisoners/ambar_walkdown1.png",   # prisioner2
        "assets/sprites/prisoners/valen_walkdown1.png",   # prisioner3
        "assets/sprites/prisoners/gus_walkdown1.png",     # prisioner4
    ]
    SNAKE_DIR = "assets/sprites/solid_python/"

    FADE_OUT_S = 0.6
    TEXT_SPEED = 20                   # caracteres por segundo
    TEXT_SOUND_PATH = "assets/audio/sfx/text_scroll.wav"
    FAST_MULT = 1.5          # multiplicador de velocidad al mantener ENTER/ESPACIO
    FINAL_HOLD_S = 3.0       # segundos con Snake en pantalla antes de la llamada
    ROOF_UNTIL = "CRAWL"              # el techo se dibuja solo durante esta fase

    TEXT_DELAY_S = 0.5        # pausa antes de que arranque cada línea
    CRAWL_END_WAIT_S = 1.0    # Snake quieto en el suelo al terminar de arrastrarse
    STAND_WAIT_S = 2.0        # Snake de pie, antes de mover la cámara
    CROUCH_WAIT_S = 1.0
    ENTER_BLINK_MS = 500      # parpadeo del "ENTER"
    SKIP_FADE_S = 0.6

    # (quién habla, texto). Reemplazalos por los diálogos reales.
    DIALOGUE = [
        ("Soldado", "¿Alguna vez han escuchado hablar sobre Outer Heaven?"),
        ("Lautaro", "No."),
        ("Ambar", "No."),
        ("Valen", "No."),
        ("Augusto", "¡Si!... digo, no."),
        ("Soldado", "Outer Heaven era un palacio, y nos lo arrebataron..."),
        ("Soldado", "estan obligados a ayudarnos a reconstruirlo. Si se abstienen, TABLA."),
        ("Soldado", "O les vamos a pegar con cables pelados."),
        ("Ambar", "¿Cómo que reconstruirlo?"),
        ("Valen", "No sabemos absolutamente nada de construcción."),
        ("Soldado", "Todo se aprende. Van a hacer cursos de albañilería."),
        ("Lautaro", "¡NOOOOOOO! NO UN TRABAJO DE TIEMPO COMPLETO."),
        ("Augusto", "No es para tanto. Yo hice cosas peores."),
        ("Ambar", "Hay algo que no entiendo, ¿por qué nos reclutarían a nosotros?"),
        ("Lautaro (dev)", "En realidad nos forzaron a incluirnos, por eso estamos acá."),
        ("Lautaro (dev)", "Pero bueno... le voy a meter una excusa mas elaborada."),
        ("Soldado", "Por que ustedes son los elegidos por el..."),
        ("Soldado", "¡THE BIGGEST BOSS!"),
        ("Valen", "Que feo nombre, ¿no tenía otro mejor?"),
        ("Augusto", "Re poco original el wachin."),
        ("Soldado", "Ya me estoy arrepintiendo de haberlos secuestado..."),
        ("Soldado", "no importa. Ahora los voy a llevar a las salas de entrenamiento, para luego..."),
        ("Soldado", "¡empezar a trabajar!"),
    ]

    def __init__(self):
        self.finished = False
        self.t = 0.0
        self.cam_t = 0.0          # reloj de la cámara (solo avanza en CRAWL y WATCH)
        self.phase_t = 0.0
        self.line_delay = 0.0
        self._last_c = (0, 0)     # último centro de cámara, para volver suave a Snake
        self.phase = "CRAWL"
        self.vw, self.vh = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        self.vs = pygame.Surface((self.vw, self.vh))
        self.k = self.MAP_SCALE

        self.tmx = pytmx.load_pygame(self.TMX_PATH)
        self.map_w = self.tmx.width * self.tmx.tilewidth * self.k
        self.map_h = self.tmx.height * self.tmx.tileheight * self.k

        try:
            bg = pygame.image.load(self.BG_PATH).convert()
            self.bg = pygame.transform.scale(bg, (bg.get_width() * self.k, bg.get_height() * self.k))
        except Exception as e:
            print(f"Aviso: no se pudo cargar el fondo de la cinemática: {e}")
            self.bg = None

        # --- Datos de Tiled ---
        pm = self._points("player_movement")
        self.snake_start = pm.get("start_position", (0, 0))
        self.snake_end = pm.get("final_position", (0, 0))
        self.soldiers = [p for _, p in self._points_sorted("soldiers_pos")]
        self.prisoners = [p for _, p in self._points_sorted("prisioners_pos")]
        self._build_camera()
        self._load_sprites()
        self._build_roofs()

        # Snake
        self.snake_pos = list(self.snake_start)
        self.anim_t = 0.0
        self.frame = 0

        # Diálogo
        self.line = 0
        self.chars = 0.0
        self.font = pygame.font.Font("assets/fonts/PixelOperator8.ttf", 14)
        self.final_t = 0.0
        try:
            self.text_sound = pygame.mixer.Sound(self.TEXT_SOUND_PATH)
        except Exception as e:
            print(f"Aviso: no se pudo cargar text_scroll.wav: {e}")
            self.text_sound = None
        self.text_sound_playing = False

        # Saltear con doble ESC
        self.skip_warning = False
        self.warning_t = 0
        self.fade_t = 0.0
        self.skipping = False
        self.skip_fade_t = 0.0

    def _go(self, phase):
        self.phase = phase
        self.phase_t = 0.0

    def _skip(self):
        """Congela todo y hace fundido a negro; al terminar, Game lanza la radio."""
        self.skipping = True
        self.skip_fade_t = 0.0
        self.skip_warning = False
        self._set_text_sound(False)

    # ---------- lectura de Tiled ----------
    def _layer_objects(self, name):
        try:
            return list(self.tmx.get_layer_by_name(name))
        except Exception:
            print(f"Aviso: no se encontró la capa '{name}'")
            return []

    def _points_sorted(self, layer):
        objs = sorted(self._layer_objects(layer), key=lambda o: o.id)
        return [(o, (o.x * self.k, o.y * self.k)) for o in objs]

    def _points(self, layer):
        return {o.name: p for o, p in self._points_sorted(layer)}

    def _set_text_sound(self, on):
        if not self.text_sound or on == self.text_sound_playing:
            return
        if on:
            self.text_sound.play(-1)
        else:
            self.text_sound.stop()
        self.text_sound_playing = on

    def _speeding_up(self):
        keys = pygame.key.get_pressed()
        return (keys[pygame.K_RETURN] or keys[pygame.K_KP_ENTER] or keys[pygame.K_SPACE]
                or pygame.mouse.get_pressed()[0])

    def _build_camera(self):
        """Línea de tiempo: [(t0, t1, desde, hasta), ...].
        El primer waypoint es el encuadre inicial: la cámara arranca ahí y se queda
        (duration + hold) segundos, que es lo que dura el arrastre de Snake."""
        pts = self._points_sorted("camera_pos")
        self.cam_segments = []
        if not pts:
            self.crawl_time = self.cam_total = 3.0
            self.cam_last = self.snake_start
            return

        o0, p0 = pts[0]
        t = float(o0.properties.get("duration", 0)) + float(o0.properties.get("hold", 0))
        self.cam_segments.append((0.0, t, p0, p0))      # estática en el primer punto
        self.crawl_time = max(t, 0.01)

        pos = p0
        for o, p in pts[1:]:
            dur = float(o.properties.get("duration", 1))
            hold = float(o.properties.get("hold", 0))
            self.cam_segments.append((t, t + dur, pos, p))
            t += dur + hold
            pos = p
        self.cam_total = t
        self.cam_last = pos

    def _cam_center(self):
        for t0, t1, a, b in self.cam_segments:
            if self.cam_t < t1:
                s = _smooth((self.cam_t - t0) / max(0.01, t1 - t0))
                return a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s
        return self.cam_last

    # ---------- sprites ----------
    def _img(self, path):
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))

    def _load_sprites(self):
        d = self.SNAKE_DIR
        try:
            self.crawl = [self._img(d + n) for n in ("crawl_up.png", "crawl_up1.png", "crawl_up.png", "crawl_up2.png")]
            self.crouch = self._img(d + "crouch_up1.png")
            self.stand = self._img(d + "stand_up.png")
        except Exception as e:
            print(f"Aviso: sprites de Snake: {e}")
            self.crawl, self.crouch, self.stand = [], None, None
        try:
            self.soldier_img = self._img(self.SOLDIER_SPRITE)
        except Exception:
            self.soldier_img = None
        try:
            self.prisoner_imgs = []
            for path in self.PRISONER_SPRITES:
                try:
                    self.prisoner_imgs.append(self._img(path))
                except Exception as e:
                    print(f"Aviso: no se pudo cargar {path}: {e}")
                    self.prisoner_imgs.append(None)
        except Exception:
            self.prisoner_img = None
        if self.prisoner_imgs is None and self.soldier_img is not None:
            self.prisoner_img = self.soldier_img.copy()
            self.prisoner_img.fill((90, 90, 90, 255), special_flags=pygame.BLEND_RGBA_MULT)

    def _build_roofs(self):
        """Pre-dibuja la capa de techos en una superficie del tamaño del mapa."""
        self.roof = pygame.Surface((self.map_w, self.map_h), pygame.SRCALPHA)
        th = self.tmx.tileheight
        for layer in self.tmx.visible_layers:
            if layer.name != "hidden_roofs2" or not hasattr(layer, "data"):
                continue
            for x, y, gid in layer:
                if not gid:
                    continue
                tile = self.tmx.get_tile_image_by_gid(gid)
                if not tile:
                    continue
                scaled = pygame.transform.scale(tile, (tile.get_width() * self.k, tile.get_height() * self.k))
                px = x * self.tmx.tilewidth * self.k
                py = y * th * self.k - (tile.get_height() - th) * self.k
                self.roof.blit(scaled, (px, py))

    # ---------- eventos ----------
    def _advance(self):
        text = self.DIALOGUE[self.line][1]
        if self.chars < len(text) or self.line_delay > 0:
            return
        self.line += 1
        self.chars = 0.0
        self.line_delay = self.TEXT_DELAY_S
        if self.line >= len(self.DIALOGUE):
            self._set_text_sound(False)
            self._go("FINAL")

    def handle_events(self, events):
        for e in events:
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if self.skipping or self.phase == "FADE":
                continue
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.phase == "DIALOGUE":
                self._advance()
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if self.skip_warning:
                        self._skip()
                    else:
                        self.skip_warning = True
                        self.warning_t = pygame.time.get_ticks()
                elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) and self.phase == "DIALOGUE":
                    self._advance()

    # ---------- lógica ----------
    def update(self, dt):
        if self.finished:
            return
        if self.skip_warning and pygame.time.get_ticks() - self.warning_t > 3000:
            self.skip_warning = False

        if self.skipping:
            self.skip_fade_t += dt
            if self.skip_fade_t >= self.SKIP_FADE_S:
                self.finished = True
            return
        
        if self.phase == "FADE":
            self.fade_t += dt
            if self.fade_t >= self.FADE_OUT_S:
                self.finished = True
            return

        self.phase_t += dt

        if self.phase == "CRAWL":
            self.t += dt
            self.cam_t = min(self.t, self.crawl_time)
            s = min(1.0, self.t / max(0.01, self.crawl_time))
            self.snake_pos[0] = self.snake_start[0] + (self.snake_end[0] - self.snake_start[0]) * s
            self.snake_pos[1] = self.snake_start[1] + (self.snake_end[1] - self.snake_start[1]) * s
            self.anim_t += dt
            if self.anim_t >= 0.4:
                self.anim_t = 0.0
                self.frame = (self.frame + 1) % max(1, len(self.crawl))
            if s >= 1.0:
                self.snake_pos = list(self.snake_end)
                self._go("CRAWLED")

        elif self.phase == "CRAWLED":          # 1 s quieto en el suelo
            if self.phase_t >= self.CRAWL_END_WAIT_S:
                self._go("CROUCH")

        elif self.phase == "CROUCH":         # agachado, 1 s antes de pararse
            if self.phase_t >= self.CROUCH_WAIT_S:
                self._go("STANDING")

        elif self.phase == "STANDING":         # de pie, 2 s antes de mover la cámara
            if self.phase_t >= self.STAND_WAIT_S:
                self._go("WATCH")

        elif self.phase == "WATCH":            # la cámara viaja a los prisioneros
            self.cam_t += dt
            if self.cam_t >= self.cam_total:
                self.line_delay = self.TEXT_DELAY_S
                self._go("DIALOGUE")

        elif self.phase == "DIALOGUE":
            if self.line < len(self.DIALOGUE):
                if self.line_delay > 0:
                    self.line_delay -= dt
                    self._set_text_sound(False)
                    return
                text = self.DIALOGUE[self.line][1]
                speed = self.TEXT_SPEED * (self.FAST_MULT if self._speeding_up() else 1.0)
                writing = self.chars < len(text)
                self.chars = min(len(text), self.chars + speed * dt)
                self._set_text_sound(writing and self.chars < len(text))

        elif self.phase == "FINAL":
            self.final_t += dt
            if self.final_t >= self.FINAL_HOLD_S:
                self.finished = True

    # ---------- dibujo ----------
    def _blit_actor(self, img, pos, cam):
        if img:
            self.vs.blit(img, img.get_rect(center=(pos[0] - cam[0], pos[1] - cam[1])))

    def _wrap(self, text, width):
        lines, cur = [], ""
        for w in text.split(" "):
            test = (cur + " " + w).strip()
            if self.font.size(test)[0] <= width:
                cur = test
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        return lines

    def draw(self, surface):
        vs = self.vs
        vs.fill((0, 0, 0))

        # 1) Centro de cámara (UN solo bloque, ANTES de calcular cam_x / cam_y)
        if self.phase == "FINAL":
            s = _smooth(self.final_t / 1.0)
            cx = self._last_c[0] + (self.snake_end[0] - self._last_c[0]) * s
            cy = self._last_c[1] + (self.snake_end[1] - self._last_c[1]) * s
        elif self.phase == "FADE":
            cx, cy = self.snake_end
        else:
            cx, cy = self._cam_center()
            self._last_c = (cx, cy)

        # 2) Esquina de la cámara
        cam_x = max(0, min(cx - self.vw / 2, self.map_w - self.vw))
        cam_y = max(0, min(cy - self.vh / 2, self.map_h - self.vh))
        cam = (cam_x, cam_y)

        if self.bg:
            vs.blit(self.bg, (-cam_x, -cam_y))

        for i, p in enumerate(self.prisoners):
            img = self.prisoner_imgs[i % len(self.prisoner_imgs)] if self.prisoner_imgs else None
            self._blit_actor(img, p, cam)
        for p in self.soldiers:
            self._blit_actor(self.soldier_img, p, cam)

        if self.phase == "CRAWL" and self.crawl:
            snake = self.crawl[self.frame % len(self.crawl)]
        elif self.phase == "CRAWLED" and self.crawl:
            snake = self.crawl[0]            # quieto en el suelo
        elif self.phase == "CROUCH" and self.crouch:
            snake = self.crouch
        else:
            snake = self.stand               # de pie
        self._blit_actor(snake, self.snake_pos, cam)

        if self.phase == self.ROOF_UNTIL:
            vs.blit(self.roof, (-cam_x, -cam_y))

        sw, sh = surface.get_size()
        surface.blit(pygame.transform.scale(vs, (sw, sh)), (0, 0))

        # Cuadro de diálogo (sobre la pantalla real)
        if self.phase == "DIALOGUE" and self.line < len(self.DIALOGUE):
            who, text = self.DIALOGUE[self.line]
            bw, bh = 720, 110
            bx, by = (sw - bw) // 2, sh - bh - 40
            pygame.draw.rect(surface, (255, 255, 255), (bx, by, bw, bh), 3)
            pygame.draw.rect(surface, (0, 0, 204), (bx + 3, by + 3, bw - 6, bh - 6))
            surface.blit(self.font.render(f"{who}:", True, (255, 255, 100)), (bx + 25, by + 12))
            y = by + 42
            for ln in self._wrap(text[:int(self.chars)], bw - 50):
                surface.blit(self.font.render(ln, True, (255, 255, 255)), (bx + 25, y))
                y += self.font.get_linesize() + 4
            if (self.line_delay <= 0 and self.chars >= len(text)
                    and (pygame.time.get_ticks() // self.ENTER_BLINK_MS) % 2 == 0):
                enter = self.font.render("ENTER", True, (200, 200, 200))
                surface.blit(enter, (bx + bw - 100, by + bh + 10))

        if self.skip_warning:
            msg = self.font.render("Presiona ESC nuevamente para saltear", True, (255, 255, 255))
            surface.blit(msg, (20, 20))

        if self.phase == "FADE":
            a = int(255 * min(1.0, self.fade_t / self.FADE_OUT_S))
            fade = pygame.Surface((sw, sh))
            fade.set_alpha(a)
            surface.blit(fade, (0, 0))

        if self.skipping:
            a = int(255 * min(1.0, self.skip_fade_t / self.SKIP_FADE_S))
            fade = pygame.Surface((sw, sh))
            fade.set_alpha(a)
            surface.blit(fade, (0, 0))