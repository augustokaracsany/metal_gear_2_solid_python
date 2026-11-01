import math


import pygame
from pathfinding.finder.a_star import AStarFinder
from src.settings import ENEMY_MAX_HEALTH
from pathfinding.core.diagonal_movement import DiagonalMovement
from src.enemy_bullet import enemyBullet


class Enemy(pygame.sprite.Sprite):
    """
    Guardia con máquina de estados:

        WALKING  -> Patrulla entre los puntos de Tiled.
        LOOKING  -> Mira alrededor ( Al llegar a un punto de patrulla o al terminar de buscar. )
        ALERT    -> Pausa corta con el icono de alerta cuando ve al player.
        CHASE    -> ALGORITMOS ALGORITMOS ALGORITMOS 
        SEARCH   -> Te perdió de vista: Te busca en la última posición donde te vió.
        RETURN   -> Vuelve a su ruta de patrulla con A*.

    self.x / self.y son la esquina superior izquierda del rect ( Igual que Player. ).
    Para la IA se trabaja con el centro en float ( _fcenter ), no con rect.center. <- ¿Inchequeable?

    MOVIMIENTO POR CARRILES: La grilla se construye con el tamaño del hitbox del guardia
    ( Ver TiledMap.create_pathfinding_grid. ), así que para el guardia, una celda libre = "acá entro entero".
    El guardia sigue la ruta moviéndose de a UN eje por vez, siempre por el centro de las
    celdas, y solo recalcula la ruta cuando está justo en el centro de una celda. ( Osea, se mueve por EJE X o por EJE Y, núnca por ambos en diagonal. )
    Resultado: no corta esquinas ni se come paredes.
    """

    GRID_TILE = 32             # Tiene que coincidir con tile_size de create_pathfinding_grid()
    PATROL_SPEED = 1 * 60       # px/seg
    CHASE_SPEED = 1.5 * 60    # px/seg ( Debería ser más rápido que patrullando)
    SEARCH_SPEED = 1.5 * 60         # px/seg

    VISION_RANGE = 3 * 120        # Alcance del cono en px
    CONE_HALF_ANGLE = 20        # Ángulo del cono en grados ( Dibujo Y detección usan lo mismo. )
    CONE_TAN = math.tan(math.radians(CONE_HALF_ANGLE))
    AWARENESS_RADIUS = 250         # En ALERT/CHASE te "siente" cerca aunque estés fuera del cono de VISIÓN.
# A* <- Algoritmo.
    ALERT_TIME = 0.8               # Segundos que se queda con el ícono de alerta antes de correr.
    LOSE_SIGHT_TIME = 4.0          # S sin verte antes de pasar de CHASE a SEARCH.
    SEARCH_TIMEOUT = 20.0           # S máx. buscando antes de rendirse
    SEARCH_LOOK_TIME = 0.8         # Duración de cada paso del "mirar alrededor" al buscar.
    PATROL_LOOK_TIME = 1.5         # idem en patrulla.
    RETURN_TIMEOUT = 15.0   # S máx. volviendo a la patrulla
    REPATH_INTERVAL = 1          # Cada cuánto PUEDE recalcular A* ( En segundos. ) 0.4 DEFAULT
    CATCH_DISTANCE = 20            # A esta distancia de Snake se frena ( Acá iría el disparo/golpe. )
    HIT_SEARCH_EXTRA = 48          # Cuánto pasa de largo el punto del golpe al buscar (px).

    # Icono de alerta.
    ALERT_ICON_PATH = "assets/sprites/alerts/alert.png"
    ALERT_ICON_SCALE = 2           # los demás sprites se escalan x2.

    # ---- COMBATE (todo ajustable) ------------------------------------------------------
    BULLET_DAMAGE = 20        # vida que le saca cada bala a Snake
    GUN_HEIGHT = 0.40         # altura del arma, como fracción del alto del sprite (sobre el hitbox)
    MUZZLE_FORWARD = 8        # px que sale la boca del arma hacia donde mira
    FLASH_TIME = 0.07         # segundos que dura el destello del disparo
    FLASH_SIZE = 9            # tamaño del destello (px)
    FLASH_COLOR = (255, 225, 120)
    FLASH_CORE = (255, 255, 245)
    SHOT_SOUND_PATH = "assets/audio/sfx/gunshot.wav"
    SHOT_VOLUME = 0.5         # volumen máximo (0..1); baja con la distancia a Snake
    SHOT_HEAR_DISTANCE = 700  # px a los que el disparo ya no se escucha
    _shot_sound = None
    _shot_sound_failed = False

    # Si Snake lleva la caja y está quieto, no lo ven. FALSE para que lo vean igualmente. ( NO FUNCIONA. )
    BOX_FOOLS_GUARDS = True

    # True = Dibuja la ruta A* en amarillo. (Se eliminaron los prints molestos de consola).
    DEBUG_AI = True

    DIRS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}

    ARRIVE_DIST = 4      # llegó si está a esta distancia (px) del destino
    FINISH_DIST = 16     # o si terminó su ruta y está a esta distancia (px)

    SEPARATION = 28        # px mínimos entre guardias que van al mismo lugar
    ALLY_WAIT_MAX = 1.2    # s máx. esperando a un compañero antes de seguir igual

    NOISE_REACT_TIME = 0.9                          # segundos con el ícono antes de ir a investigar
    SOUND_ICON_PATH = "assets/sprites/alerts/sound.png"
    _sound_icon = None
    _alert_icon = None  

    def __init__(self, x, y, patrol_points, start_delay=0.0):
        super().__init__()

        self.x = float(x)
        self.y = float(y)

        self.patrol_points = patrol_points
        self.current_target_index = 0

        self.facing = "DOWN"
        self.is_moving = False

        # Vida.
        self.max_health = ENEMY_MAX_HEALTH
        self.health = self.max_health
        self.stun_timer = 0.0   # Segundos que le quedan quieto por un golpe.
        self.hit_from = None    # Posición de quien lo golpeó (para girarse hacia ahí al terminar el aturdimiento).

        # Animación.
        self.anim_timer = 0.0
        self.frame_index = 0
        self.animation_speed = 0.2

        # MÁQUINA DE ESTADOS.
        self.state = "WALKING"
        self.state_timer = 0.0
        self.alert_timer = 0.0
        self.lost_timer = 0.0
        self.repath_timer = 0.0
        self.stuck_timer = 0.0
        self.sees_player = False

        # LOOKING.
        self.look_timer = 0.0
        self.look_duration = self.PATROL_LOOK_TIME
        self.look_step = 0
        self.after_look = "WALKING"

        # Memoria / pathfinding.
        self.last_known_pos = None   # ( x, y ) de la última vez que vio a Solid Python.
        self.path = []               # lista de ( x, y ) en píxeles ( Centros de celda. ).
        self.path_finished = False   # True si ya recorrió completa la última ruta calculada.
        self.others = []          # Todos los guardias del nivel
        self.ally_wait = 0.0

        self.current_walls = []

        self.load_sprites()

        # Los puntos de Tiled eran la esquina sup. izq. del rect los pasamos al centro.
        self.patrol_targets = [
            (px + self.rect.width / 2, py + self.rect.height / 2)
            for px, py in self.patrol_points
        ]

        # Variables de combate / balística
        self.shoot_timer = 0.0
        self.shoot_cooldown = 1.5  # Segundos entre disparos
        self.bullet_speed = 6 * 60
        self.bullet_group = pygame.sprite.Group()
        self.flash_timer = 0.0          # destello del disparo
        self._flash_off = (0.0, 0.0)
        self._flash_dir = (1.0, 0.0)

        self.start_delay = float(start_delay) # Guardamos el retraso inicial
        self.path_fail_count = 0
        self.search_target = None
        self.global_alert = False

    # CARGAR SPRITES.
    def load_sprites(self):
        SCALE_FACTOR = 2

        def cs(path):
            img = pygame.image.load(path).convert_alpha()
            w = int(img.get_width() * SCALE_FACTOR)
            h = int(img.get_height() * SCALE_FACTOR)
            return pygame.transform.scale(img, (w, h))

        self.animations = {
            "IDLE": {
                "DOWN": cs("assets/sprites/red_beret/look_down1.png"),
                "UP": cs("assets/sprites/red_beret/look_up1.png"),
                "LEFT": cs("assets/sprites/red_beret/look_left1.png"),
                "RIGHT": cs("assets/sprites/red_beret/look_right2.png"),
            },
            "WALK": {
                "DOWN": [cs("assets/sprites/red_beret/walk_down1.png"), cs("assets/sprites/red_beret/walk_down2.png")],
                "UP": [cs("assets/sprites/red_beret/walk_up1.png"), cs("assets/sprites/red_beret/walk_up2.png")],
                "LEFT": [cs("assets/sprites/red_beret/walk_left1.png"), cs("assets/sprites/red_beret/walk_left2.png")],
                "RIGHT": [cs("assets/sprites/red_beret/walk_right1.png"), cs("assets/sprites/red_beret/walk_right2.png")]
            },
            "LOOK": {
                "DOWN": [cs("assets/sprites/red_beret/walk_down2.png"), cs("assets/sprites/red_beret/look_down1.png"), cs("assets/sprites/red_beret/walk_down2.png"), cs("assets/sprites/red_beret/look_down2.png")],
                "UP": [cs("assets/sprites/red_beret/walk_up1.png"), cs("assets/sprites/red_beret/look_up1.png"), cs("assets/sprites/red_beret/walk_up1.png"), cs("assets/sprites/red_beret/look_up2.png")],
                "LEFT": [cs("assets/sprites/red_beret/walk_left1.png"), cs("assets/sprites/red_beret/look_left1.png"), cs("assets/sprites/red_beret/walk_left1.png"), cs("assets/sprites/red_beret/look_left2.png")],
                "RIGHT": [cs("assets/sprites/red_beret/walk_right1.png"), cs("assets/sprites/red_beret/look_right1.png"), cs("assets/sprites/red_beret/walk_right1.png"), cs("assets/sprites/red_beret/look_right2.png")]
            }
        }

        first_image = self.animations["IDLE"]["DOWN"]
        img_width, img_height = first_image.get_size()

        col_width = int(img_width * 0.5)
        col_height = int(img_height * 0.3)

        self.rect = pygame.Rect(self.x, self.y, col_width, col_height)

        self.offset_x = (img_width - col_width) // 2
        self.offset_y = img_height - col_height

    # UPDATE PRINCIPAL
    def update(self, dt, walls, player, grid=None, bullet_group=None):
        self.current_walls = walls
        
        # Destello del disparo (efecto visual: corre siempre).
        self.flash_timer = max(0.0, self.flash_timer - dt)

        # Aturdido por un golpe: CONGELADO por completo. No camina, no mira alrededor, no dispara
        # ni cambia de estado; conserva la pose y la dirección en la que estaba.
        if self.stun_timer > 0:
            self.stun_timer -= dt
            self.is_moving = False
            if self.stun_timer > 0:
                return
            if self.hit_from is not None:
                self._react_to_hit()
                self.hit_from = None
        if grid is not None:
            self.GRID_TILE = grid.cell_px

        # Si todavía tiene delay inicial al arrancar el nivel, se congela totalmente (sin animaciones ni movimiento)
        if self.start_delay > 0:
            self.start_delay -= dt
            self.is_moving = False
            return

        moving = False
        

        # 1) Percepción
        self._update_perception(dt, player, walls)

        # 2) Comportamiento del estado actual
        if self.state == "WALKING":
            moving = self._patrol(dt)
        elif self.state == "LOOKING":
            self._look(dt)
        elif self.state == "ALERT":
            self._alert(dt, player)
        elif self.state == "CHASE":
            moving = self._chase(dt, player, grid, bullet_group)
        elif self.state == "SEARCH":
            moving = self._search(dt, grid)
        elif self.state == "RETURN":
            moving = self._return(dt, grid)
        elif self.state == "NOISE":
            self._heard(dt)

        self.is_moving = moving

        # 3) Animación de caminar
        if moving:
            self.anim_timer += dt
            if self.anim_timer >= self.animation_speed:
                self.anim_timer = 0.0
                self.frame_index = (self.frame_index + 1) % 2

    # PERCEPCIÓN
    def _update_perception(self, dt, player, walls):
        self.sees_player = self.can_see_player(player, walls)

        if self.sees_player:
            self.last_known_pos = player.rect.center
            self.search_target = None
            self.lost_timer = 0.0
            if self.state not in ("ALERT", "CHASE"):
                # En alerta general no hay pausa con el "!": persigue directo.
                self._set_state("CHASE" if self.global_alert else "ALERT")
                self._face_towards(*player.rect.center)

    def _eye_pos(self):
        return self.rect.centerx, self.rect.top - self.offset_y // 2

    def _vision_facing(self):
        if self.state == "LOOKING":
            look_rotations = {
                "DOWN": ["DOWN", "LEFT", "DOWN", "RIGHT"],
                "UP": ["UP", "LEFT", "UP", "RIGHT"],
                "LEFT": ["LEFT", "DOWN", "LEFT", "UP"],
                "RIGHT": ["RIGHT", "DOWN", "RIGHT", "UP"],
            }
            steps = look_rotations.get(self.facing, look_rotations["DOWN"])
            return steps[min(self.look_step, len(steps) - 1)]
        return self.facing

    def can_see_player(self, player, walls):
        if getattr(player, "is_hidden", False):
            return False
        if (self.BOX_FOOLS_GUARDS
                and getattr(player, "is_disguised", False)
                and not getattr(player, "is_moving", False)):
            return False

        ex, ey = self._eye_pos()
        px, py = player.rect.center
        dx, dy = px - ex, py - ey
        dist = math.hypot(dx, dy)
        if dist == 0:
            return True

        close = self.state in ("ALERT", "CHASE") and dist <= self.AWARENESS_RADIUS

        if not close:
            fx, fy = self.DIRS[self._vision_facing()]
            forward = dx * fx + dy * fy
            side = abs(-dx * fy + dy * fx)
            in_cone = 0 < forward <= self.VISION_RANGE and side <= forward * self.CONE_TAN
            if not in_cone:
                return False

        return self._has_line_of_sight(player.rect.center, walls)

    def _has_line_of_sight(self, target, walls):
        start = self.rect.center
        box = pygame.Rect(min(start[0], target[0]) - 1, min(start[1], target[1]) - 1,
                          abs(target[0] - start[0]) + 2, abs(target[1] - start[1]) + 2)
        for i in box.collidelistall(walls):      # un muro que corta el segmento está en su caja
            if walls[i].clipline(start, target):
                return False
        return True

    # ESTADOS.
    def _set_state(self, new_state):
        # Limpieza de prints molestos de DEBUG de estado
        self.state = new_state
        self.path_fail_count = 0
        self.state_timer = 0.0
        self.path = []
        self.path_finished = False
        self.repath_timer = 0.0
        self.stuck_timer = 0.0
        if new_state == "ALERT":
            self.alert_timer = 0.0

    def _start_looking(self, step_duration, next_state):
        self._set_state("LOOKING")
        self.look_timer = 0.0
        self.look_step = 0
        self.look_duration = step_duration
        self.after_look = next_state

    def _patrol(self, dt):
        if not self.patrol_targets:
            return False

        tx, ty = self.patrol_targets[self.current_target_index]
        fx, fy = self._fcenter()
        dx, dy = tx - fx, ty - fy
        dist = math.hypot(dx, dy)

        if dist < 3.0:
            self.current_target_index = (self.current_target_index + 1) % len(self.patrol_targets)
            self._start_looking(self.PATROL_LOOK_TIME, "WALKING")
            return False

        step = min(self.PATROL_SPEED * dt, dist)
        self._face_vector(dx, dy)
        before = self.rect.center
        self._move_by(dx / dist * step, dy / dist * step)

        if self.rect.center == before:
            self.stuck_timer += dt
            if self.stuck_timer > 0.5:
                self._set_state("RETURN")
                return False
        else:
            self.stuck_timer = 0.0
        return True

    def _look(self, dt):
        self.look_timer += dt
        if self.look_timer >= self.look_duration:
            self.look_timer = 0.0
            self.look_step += 1
            if self.look_step > 3:
                self.look_step = 0
                self.frame_index = 0
                self._set_state(self.after_look)
                return
        self.frame_index = self.look_step

    def _alert(self, dt, player):
        self._face_towards(*player.rect.center)
        self.alert_timer += dt
        if self.alert_timer >= self.ALERT_TIME:
            self._set_state("CHASE")

    def _chase(self, dt, player, grid, bullet_group):
        if self.sees_player:
            tx, ty = player.rect.center
            fx, fy = self._fcenter()
            dist = math.hypot(tx - fx, ty - fy)
            
            # Margen reducido para mantener menos distancia con el jugador
            PREFERRED_MIN = 40
            PREFERRED_MAX = 80
            
            moved = False
            if dist > PREFERRED_MAX:
                moved, _ = self._go_to(dt, grid, tx, ty, self.CHASE_SPEED, PREFERRED_MAX)
            elif dist < PREFERRED_MIN:
                moved = False
            else:
                moved = False
            
            # Camina mirando hacia donde va; recién al frenarse se gira hacia Snake
            # (al disparar también se gira: ver shoot_bullet).
            if not moved:
                self._face_towards(tx, ty)
            self._handle_shooting(dt, player, bullet_group)
            
            return moved
        else:
            self.state_timer += dt
            if self.search_target is None and self.last_known_pos:
                self.search_target = self._spread_target(grid, self._reachable_target(grid, *self.last_known_pos))
            tx, ty = self.search_target or player.rect.center
            moved, arrived = self._go_to(dt, grid, tx, ty, self.SEARCH_SPEED, self.ARRIVE_DIST, self.FINISH_DIST)
            if self.path_fail_count >= 3:
                self._set_state("RETURN")
                return False
            if arrived:
                self._start_looking(self.SEARCH_LOOK_TIME, "RETURN")
            return moved

    def _search(self, dt, grid):
        self.state_timer += dt
        if self.last_known_pos is None or self.state_timer > self.SEARCH_TIMEOUT:
            self._set_state("RETURN")
            return False

        if self.search_target is None:
            self.search_target = self._spread_target(grid, self._reachable_target(grid, *self.last_known_pos))
        tx, ty = self.search_target
        moved, arrived = self._go_to(dt, grid, tx, ty, self.SEARCH_SPEED, self.ARRIVE_DIST, self.FINISH_DIST)
        if self.path_fail_count >= 3:
            self._set_state("RETURN")
            return False
        if arrived:
            self._start_looking(self.SEARCH_LOOK_TIME, "RETURN")
        return moved

    def _return(self, dt, grid):
        self.state_timer += dt
        if not self.patrol_targets or self.state_timer > self.RETURN_TIMEOUT:
            self._set_state("WALKING")
            return False

        tx, ty = self.patrol_targets[self.current_target_index]
        moved, arrived = self._go_to(dt, grid, tx, ty, self.PATROL_SPEED,
                                     self.GRID_TILE, 3 * self.GRID_TILE)
        if self.path_fail_count >= 3:
            self._set_state("WALKING")
            return False
        if arrived:
            self._set_state("WALKING")
        return moved

    def take_damage(self, amount, stun_time=0.0, source_pos=None):
        self.health = max(0, self.health - amount)
        if self.health == 0:
            self.kill()  # Lo saca de enemies_group (y de cualquier otro grupo).
        else:
            self.stun_timer = max(self.stun_timer, stun_time)
            if stun_time > 0 and source_pos is not None:
                self.hit_from = source_pos

    def _react_to_hit(self):
        #Termina el aturdimiento: se gira hacia donde lo golpearon y va a buscar por ese lado.
        hx, hy = self.hit_from
        self._face_towards(hx, hy)

        # Si ya estaba en alerta o persiguiendo a Snake, sigue con eso.
        if self.state in ("ALERT", "CHASE"):
            return

        # El punto de búsqueda queda un poco más allá de donde estaba Snake,
        # para que siga buscando hacia ese lado y no se frene justo ahí.
        fx, fy = self._fcenter()
        dx, dy = hx - fx, hy - fy
        dist = math.hypot(dx, dy)
        if dist > 0:
            hx += dx / dist * self.HIT_SEARCH_EXTRA
            hy += dy / dist * self.HIT_SEARCH_EXTRA

        self.last_known_pos = (hx, hy)
        self._set_state("SEARCH")

    def on_reach_player(self, player):
        """
        Gancho: Se llama cada frame mientras el guardia está pegado a Snake.
        Acá van después el disparo / golpe / game over.
        """
        pass

    
    # MOVIMIENTO Y PATHFINDING
    def _fcenter(self):
        return self.x + self.rect.width / 2, self.y + self.rect.height / 2

    def _on_lane(self):
        ts = self.GRID_TILE
        fx, fy = self._fcenter()
        return abs(fx % ts - ts / 2) < 0.75 and abs(fy % ts - ts / 2) < 0.75

    def _go_to(self, dt, grid, tx, ty, speed, arrive_dist, finish_dist=None):
        fx, fy = self._fcenter()
        dist = math.hypot(tx - fx, ty - fy)

        if dist <= arrive_dist:
            self.path = []
            return False, True
        if (finish_dist is not None and self.path_finished
                and not self.path and dist <= finish_dist):
            return False, True

        self.repath_timer -= dt
        if self.repath_timer <= 0 and (not self.path or self._on_lane()):
            self.repath_timer = self.REPATH_INTERVAL
            new_path = self._find_path(grid, tx, ty)
            if new_path is None:
                self.path = []
                self.path_finished = False
                self.path_fail_count += 1
            else:
                self.path = new_path
                self.path_finished = (len(new_path) == 0)
                if len(new_path) == 0:
                    self.path_fail_count += 1
                else:
                    self.path_fail_count = 0

        return self._follow_path(dt, speed), False

    def _follow_path(self, dt, speed):
        while self.path:
            tx, ty = self.path[0]
            fx, fy = self._fcenter()
            dx, dy = tx - fx, ty - fy

            if abs(dx) <= 0.5 and abs(dy) <= 0.5:
                self.path.pop(0)
                if not self.path:
                    self.path_finished = True
                continue

            step = speed * dt
            if abs(dx) > 0.5:
                mx, my = math.copysign(min(step, abs(dx)), dx), 0.0
            else:
                mx, my = 0.0, math.copysign(min(step, abs(dy)), dy)

            if self._blocked_by_ally(mx, my):
                self.ally_wait += dt
                if self.ally_wait < self.ALLY_WAIT_MAX:
                    return False              # espera a que el de adelante avance
            else:
                self.ally_wait = 0.0

            self._face_vector(mx, my)
            before = self.rect.center
            self._move_by(mx, my)

            if self.rect.center == before:
                self.stuck_timer += dt
                if self.stuck_timer > 0.4:
                    self.stuck_timer = 0.0
                    self.repath_timer = 0.0
                    self.path.pop(0)
            else:
                self.stuck_timer = 0.0
            return True
        return False

    def _cells_near(self, grid, cx, cy, px, py, radius, limit):
        ts = self.GRID_TILE
        cells = []
        for oy in range(-radius, radius + 1):
            for ox in range(-radius, radius + 1):
                x, y = cx + ox, cy + oy
                if grid.inside(x, y) and grid.walkable(x, y):
                    d = (x * ts + ts / 2 - px) ** 2 + (y * ts + ts / 2 - py) ** 2
                    cells.append((d, (x, y)))
        cells.sort()
        return [c for _, c in cells[:limit]]

    def _closest_in_region(self, grid, rid, px, py):
        ts = self.GRID_TILE
        best, best_d = None, None
        for y in range(grid.height):
            for x in range(grid.width):
                if grid.region[y][x] == rid:
                    d = (x * ts + ts / 2 - px) ** 2 + (y * ts + ts / 2 - py) ** 2
                    if best is None or d < best_d:
                        best, best_d = (x, y), d
        return best

    def _astar(self, grid, start, goal, own_cell):
        ts = self.GRID_TILE
        try:
            grid.cleanup()
            path, _ = AStarFinder(diagonal_movement=DiagonalMovement.never).find_path(
                grid.node(*start), grid.node(*goal), grid)
        except Exception:
            return None
        if not path:
            return None
        points = []
        for node in path:
            nx, ny = (node.x, node.y) if hasattr(node, "x") else node
            points.append((nx * ts + ts / 2, ny * ts + ts / 2))
        if start == own_cell and self._on_lane():
            points.pop(0)
        return points

    def _find_path(self, grid, tx, ty):
        if grid is None:
            return [(tx, ty)]

        ts = self.GRID_TILE
        fx, fy = self._fcenter()
        own = (int(fx // ts), int(fy // ts))
        region = grid.region

        starts = self._cells_near(grid, own[0], own[1], fx, fy, 2, 4)
        goals = self._cells_near(grid, int(tx // ts), int(ty // ts), tx, ty, 6, 12)

        for s in starts:
            for g in goals:
                if region[s[1]][s[0]] != region[g[1]][g[0]]:
                    continue
                points = self._astar(grid, s, g, own)
                if points is not None:
                    return points

        if starts:
            s = starts[0]
            g = self._closest_in_region(grid, region[s[1]][s[0]], tx, ty)
            if g is not None:
                points = self._astar(grid, s, g, own)
                if points is not None:
                    return points

        return None

    def _move_by(self, mx, my):
        self.x += mx
        self.rect.x = round(self.x)
        self.check_collisions_x(self.current_walls, mx)

        self.y += my
        self.rect.y = round(self.y)
        self.check_collisions_y(self.current_walls, my)

    def _face_vector(self, dx, dy):
        if abs(dx) > abs(dy):
            self.facing = "RIGHT" if dx > 0 else "LEFT"
        else:
            self.facing = "DOWN" if dy > 0 else "UP"

    def _face_towards(self, tx, ty):
        fx, fy = self._fcenter()
        self._face_vector(tx - fx, ty - fy)

    def check_collisions_x(self, walls, dx):
        for _ in range(3):                       # 3 pasadas por si un empujón roza otro muro
            hits = self.rect.collidelistall(walls)
            if not hits:
                return
            pushed = False
            for i in hits:
                wall = walls[i]
                if self.rect.colliderect(wall):
                    if dx > 0:
                        self.rect.right = wall.left
                        pushed = True
                    elif dx < 0:
                        self.rect.left = wall.right
                        pushed = True
                    self.x = float(self.rect.x)
            if not pushed:
                return

    def check_collisions_y(self, walls, dy):
        for _ in range(3):
            hits = self.rect.collidelistall(walls)
            if not hits:
                return
            pushed = False
            for i in hits:
                wall = walls[i]
                if self.rect.colliderect(wall):
                    if dy > 0:
                        self.rect.bottom = wall.top
                        pushed = True
                    elif dy < 0:
                        self.rect.top = wall.bottom
                        pushed = True
                    self.y = float(self.rect.y)
            if not pushed:
                return

    def _handle_shooting(self, dt, player, bullet_group):
        self.shoot_timer += dt
        if self.shoot_timer >= self.shoot_cooldown:
            self.shoot_timer = 0.0
            self.shoot_bullet(player, bullet_group)

    def shoot_bullet(self, player, bullet_group):
        """La bala viaja en el PLANO DEL PISO (donde están todos los hitboxes), recta del
        hitbox del guardia al de Snake; solo se DIBUJA a la altura del arma."""
        if bullet_group is None:
            return
        fx, fy = self._fcenter()
        px, py = player.rect.center
        dx, dy = px - fx, py - fy
        dist = math.hypot(dx, dy)
        if dist == 0:
            return
        ux, uy = dx / dist, dy / dist

        self._face_vector(dx, dy)                # al disparar se gira hacia Snake
        fdx, fdy = self.DIRS[self.facing]
        sprite_h = self.offset_y + self.rect.height
        draw_dx = fdx * self.MUZZLE_FORWARD
        draw_dy = -self.GUN_HEIGHT * sprite_h + fdy * self.MUZZLE_FORWARD

        bullet_group.add(enemyBullet(fx, fy, ux * self.bullet_speed, uy * self.bullet_speed,
                                     draw_dx=draw_dx, draw_dy=draw_dy,
                                     damage=self.BULLET_DAMAGE))
        self._flash_off = (draw_dx, draw_dy)
        self._flash_dir = (ux, uy)
        self.flash_timer = self.FLASH_TIME
        self._play_shot_sound(player)

    @classmethod
    def _get_shot_sound(cls):
        if cls._shot_sound is None and not cls._shot_sound_failed:
            try:
                cls._shot_sound = pygame.mixer.Sound(cls.SHOT_SOUND_PATH)
            except Exception:
                cls._shot_sound_failed = True
        return cls._shot_sound

    def _play_shot_sound(self, player):
        """Sonido del disparo; baja con la distancia a Snake. Usa un canal libre (nunca pisa los tuyos)."""
        if not pygame.mixer.get_init():
            return
        snd = self._get_shot_sound()
        if snd is None:
            return
        fx, fy = self._fcenter()
        px, py = player.rect.center
        vol = self.SHOT_VOLUME * max(0.0, 1.0 - math.hypot(px - fx, py - fy) / self.SHOT_HEAR_DISTANCE)
        if vol < 0.02:
            return
        ch = pygame.mixer.find_channel()
        if ch:
            ch.play(snd)
            ch.set_volume(vol)

    def _reachable_target(self, grid, tx, ty):
        if grid is None:
            return (tx, ty)
        ts = self.GRID_TILE
        fx, fy = self._fcenter()
        own = (int(fx // ts), int(fy // ts))
        starts = self._cells_near(grid, own[0], own[1], fx, fy, max(2, 24 // ts), 4)
        if not starts:
            return (tx, ty)
        s = starts[0]
        rid = grid.region[s[1]][s[0]]
        goals = self._cells_near(grid, int(tx // ts), int(ty // ts), tx, ty, max(6, 96 // ts), 16)
        for g in goals:
            if grid.region[g[1]][g[0]] == rid:
                return (g[0] * ts + ts / 2, g[1] * ts + ts / 2)
        g = self._closest_in_region(grid, rid, tx, ty)
        if g is not None:
            return (g[0] * ts + ts / 2, g[1] * ts + ts / 2)
        return (tx, ty)

    def _strict_target(self, grid, tx, ty, max_path):
        """Punto alcanzable cerca de (tx, ty), o None. NO usa el 'más cercano en toda la región':
        si la fuente está en un hueco inaccesible, se ignora."""
        if grid is None:
            return (tx, ty)
        ts = self.GRID_TILE
        fx, fy = self._fcenter()
        own = (int(fx // ts), int(fy // ts))
        starts = self._cells_near(grid, own[0], own[1], fx, fy, max(2, 24 // ts), 4)
        goals = self._cells_near(grid, int(tx // ts), int(ty // ts), tx, ty, max(2, 16 // ts), 6)
        for s in starts:
            for g in goals:
                if grid.region[s[1]][s[0]] != grid.region[g[1]][g[0]]:
                    continue
                pts = self._astar(grid, s, g, own)
                if pts is not None and len(pts) * ts <= max_path:
                    return (g[0] * ts + ts / 2, g[1] * ts + ts / 2)
        return None

    def _heard(self, dt):
        """Gesto de "escuché algo": se queda quieto mirando hacia la fuente y luego investiga."""
        if self.search_target:
            self._face_towards(*self.search_target)
        self.state_timer += dt
        if self.state_timer >= self.NOISE_REACT_TIME:
            self._set_state("SEARCH")   # _set_state no borra search_target

    def _taken_targets(self):
        """Destinos que otros guardias ya están usando."""
        return [o.search_target for o in self.others
                if o is not self and o.search_target
                and o.state in ("NOISE", "SEARCH", "CHASE")]

    def _spread_target(self, grid, target):
        """Si otro guardia ya va a ese punto, busca una celda libre cercana en la misma región."""
        if grid is None or target is None:
            return target
        taken = self._taken_targets()
        sep2 = self.SEPARATION ** 2

        def free(p):
            return all((p[0] - t[0]) ** 2 + (p[1] - t[1]) ** 2 >= sep2 for t in taken)

        if free(target):
            return target

        ts = self.GRID_TILE
        cx, cy = int(target[0] // ts), int(target[1] // ts)
        if not grid.inside(cx, cy):
            return target
        rid = grid.region[cy][cx]
        radius = int(self.SEPARATION * 3 // ts) + 1

        best, best_d = None, None
        for oy in range(-radius, radius + 1):
            for ox in range(-radius, radius + 1):
                x, y = cx + ox, cy + oy
                if not grid.inside(x, y) or not grid.walkable(x, y):
                    continue
                if grid.region[y][x] != rid:
                    continue
                p = (x * ts + ts / 2, y * ts + ts / 2)
                if not free(p):
                    continue
                d = (p[0] - target[0]) ** 2 + (p[1] - target[1]) ** 2
                if best is None or d < best_d:
                    best, best_d = p, d
        return best or target

    def _blocked_by_ally(self, mx, my):
        """True si hay un compañero justo adelante y a este le toca ceder el paso."""
        fx, fy = self._fcenter()
        for o in self.others:
            if o is self or o.start_delay > 0:
                continue
            ox, oy = o._fcenter()
            dx, dy = ox - fx, oy - fy
            if math.hypot(dx, dy) >= self.SEPARATION:
                continue
            if dx * mx + dy * my <= 0:        # no está adelante
                continue
            if id(self) > id(o):              # prioridad fija: solo uno cede
                return True
        return False

    def hear_noise(self, pos, radius, grid, origin=None, gesture=True):
        """gesture=True: hace la pausa con el ícono. gesture=False: va directo a investigar."""
        if self.start_delay > 0 or self.stun_timer > 0 or self.state in ("ALERT", "CHASE", "NOISE"):
            return False
        if self.state == "SEARCH":
            gesture = False      # ya está investigando: no repite la pausa con el "?" (evita trabarse)

        ox, oy = origin if origin else pos
        fx, fy = self._fcenter()
        if math.hypot(ox - fx, oy - fy) > radius:
            return False

        target = self._strict_target(grid, pos[0], pos[1], max_path=radius * 2.5)
        if target is None:
            return False

        target = self._spread_target(grid, target)

        self.last_known_pos = target
        self.search_target = target
        self._set_state("NOISE" if gesture else "SEARCH")
        self._face_towards(*target)
        return True

    # DIBUJO
    @classmethod
    def _get_alert_icon(cls):
        if cls._alert_icon is None:
            try:
                img = pygame.image.load(cls.ALERT_ICON_PATH).convert_alpha()
                s = cls.ALERT_ICON_SCALE
                cls._alert_icon = pygame.transform.scale(
                    img, (int(img.get_width() * s), int(img.get_height() * s))
                )
            except Exception as e:
                cls._alert_icon = pygame.Surface((1, 1), pygame.SRCALPHA)
        return cls._alert_icon

    @classmethod
    def _get_sound_icon(cls):
        if cls._sound_icon is None:
            try:
                img = pygame.image.load(cls.SOUND_ICON_PATH).convert_alpha()
                s = cls.ALERT_ICON_SCALE
                cls._sound_icon = pygame.transform.scale(
                    img, (int(img.get_width() * s), int(img.get_height() * s))
                )
            except Exception:
                cls._sound_icon = pygame.Surface((1, 1), pygame.SRCALPHA)
        return cls._sound_icon

    def draw_vision(self, surface, camera):
        dir_x, dir_y = self.DIRS[self._vision_facing()]
        start_x, start_y = self._eye_pos()
        perp_x, perp_y = -dir_y, dir_x

        rng = self.VISION_RANGE
        w = self.CONE_TAN
        left = (start_x + (dir_x - perp_x * w) * rng, start_y + (dir_y - perp_y * w) * rng)
        right = (start_x + (dir_x + perp_x * w) * rng, start_y + (dir_y + perp_y * w) * rng)

        ox, oy = camera.camera_rect.x, camera.camera_rect.y
        points = [(start_x + ox, start_y + oy), (left[0] + ox, left[1] + oy), (right[0] + ox, right[1] + oy)]

        alerted = self.state in ("ALERT", "CHASE")
        color = (255, 0, 0, 100) if alerted else (0, 255, 0, 100)

        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        x0, y0 = math.floor(min(xs)), math.floor(min(ys))
        box = pygame.Rect(x0, y0, math.ceil(max(xs)) - x0 + 2, math.ceil(max(ys)) - y0 + 2)
        box = box.clip(surface.get_rect())
        if box.width > 0 and box.height > 0:
            vision_surface = pygame.Surface(box.size, pygame.SRCALPHA)
            local = [(x - box.x, y - box.y) for x, y in points]
            pygame.draw.polygon(vision_surface, color, local)
            surface.blit(vision_surface, box.topleft)

        if self.DEBUG_AI and self.path:
            fx, fy = self._fcenter()
            line = [(fx + ox, fy + oy)] + [(px + ox, py + oy) for px, py in self.path]
            if len(line) > 1:
                pygame.draw.lines(surface, (255, 255, 0), False, line, 1)

    def draw_with_camera(self, surface, camera):
        if self.state == "LOOKING":
            idx = min(self.frame_index, len(self.animations["LOOK"][self.facing]) - 1)
            current_image = self.animations["LOOK"][self.facing][idx]
        elif self.is_moving:
            frames = self.animations["WALK"][self.facing]
            current_image = frames[self.frame_index % len(frames)]
        else:
            current_image = self.animations["IDLE"][self.facing]

        dest_rect = camera.apply(self)
        draw_x = dest_rect.x - self.offset_x
        draw_y = dest_rect.y - self.offset_y

        pygame.draw.rect(surface, (255, 0, 0), dest_rect, 1)
        surface.blit(current_image, (draw_x, draw_y))
        if self.flash_timer > 0:
            self._draw_muzzle_flash(surface, dest_rect)

        if self.state == "ALERT":
            icon = self._get_alert_icon()
            surface.blit(icon, (dest_rect.centerx - icon.get_width() // 2,
                                draw_y - icon.get_height() - 2))
        if self.state == "NOISE":
            icon = self._get_sound_icon()
            surface.blit(icon, (dest_rect.centerx - icon.get_width() // 2,
                                draw_y - icon.get_height() - 2))

    def _draw_muzzle_flash(self, surface, dest_rect):
        """Destello en la boca del arma, orientado hacia donde sale la bala."""
        cx = dest_rect.centerx + self._flash_off[0]
        cy = dest_rect.centery + self._flash_off[1]
        ux, uy = self._flash_dir
        size = self.FLASH_SIZE
        w = size * 0.45
        tip = (cx + ux * size * 1.6, cy + uy * size * 1.6)
        pts = [(cx - uy * w, cy + ux * w), tip, (cx + uy * w, cy - ux * w)]
        pygame.draw.polygon(surface, self.FLASH_COLOR, pts)
        pygame.draw.circle(surface, self.FLASH_CORE, (round(cx), round(cy)), max(1, size // 3))

    def draw_regions_debug(self, surface, camera, grid):
        ts = self.GRID_TILE
        ox, oy = camera.camera_rect.x, camera.camera_rect.y
        for y in range(grid.height):
            for x in range(grid.width):
                rid = grid.region[y][x]
                if rid >= 0:
                    color = ((rid * 67) % 200 + 55, (rid * 131) % 200 + 55, (rid * 29) % 200 + 55)
                    pygame.draw.rect(surface, color, (x * ts + ox, y * ts + oy, ts, ts), 1)