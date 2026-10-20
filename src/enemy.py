import math

import pygame
from pathfinding.finder.a_star import AStarFinder


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

    GRID_TILE = 16                 # Tiene que coincidir con tile_size de create_pathfinding_grid()
    PATROL_SPEED = 1 * 60       # px/seg
    CHASE_SPEED = 1.5 * 60  # px/seg ( Debería ser más rápido que patrullando)
    SEARCH_SPEED = 1.5 * 60        # px/seg

    VISION_RANGE = 3 * 120      # Alcance del cono en px
    CONE_HALF_ANGLE = 20        # Ángulo del cono en grados ( Dibujo Y detección usan lo mismo. )
    CONE_TAN = math.tan(math.radians(CONE_HALF_ANGLE))
    AWARENESS_RADIUS = 10000          # En ALERT/CHASE te "siente" cerca aunque estés fuera del cono de VISIÓN.
# A* <- Algoritmo.
    ALERT_TIME = 0.8               # Segundos que se queda con el ícono de alerta antes de correr.
    LOSE_SIGHT_TIME = 600.0          # S sin verte antes de pasar de CHASE a SEARCH.
    SEARCH_TIMEOUT = 20.0           # S máx. buscando antes de rendirse
    SEARCH_LOOK_TIME = 0.8         # Duración de cada paso del "mirar alrededor" al buscar.
    PATROL_LOOK_TIME = 1.5         # idem en patrulla.
    RETURN_TIMEOUT = 15.0   # S máx. volviendo a la patrulla
    REPATH_INTERVAL = 0.4          # Cada cuánto PUEDE recalcular A* ( En segundos. )
    CATCH_DISTANCE = 20            # A esta distancia de Snake se frena ( Acá iría el disparo/golpe. )

    # Icono de alerta.
    ALERT_ICON_PATH = "assets/sprites/alerts/alert.png"
    ALERT_ICON_SCALE = 2           # los demás sprites se escalan x2.

    # Si Snake lleva la caja y está quieto, no lo ven. FALSE para que lo vean igualmente. ( NO FUNCIONA. )
    BOX_FOOLS_GUARDS = True

    # True = Dibuja la ruta A* en amarillo y avisa por consola si no encuentra camino.
    DEBUG_AI = True

    DIRS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}

    _alert_icon = None  

    def __init__(self, x, y, patrol_points):
        super().__init__()

        self.x = float(x)
        self.y = float(y)

        self.patrol_points = patrol_points
        self.current_target_index = 0

        self.facing = "DOWN"
        self.is_moving = False

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

        self.current_walls = []

        self.load_sprites()

        # Los puntos de Tiled eran la esquina sup. izq. del rect los pasamos al centro.
        self.patrol_targets = [
            (px + self.rect.width / 2, py + self.rect.height / 2)
            for px, py in self.patrol_points
        ]

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

        # Hitbox compacto en los pies ( Igual que Snake. ) para evitar que se trabe en esquinas.
        col_width = int(img_width * 0.5)
        col_height = int(img_height * 0.3)

        self.rect = pygame.Rect(self.x, self.y, col_width, col_height)

        # Offsets para alinear el sprite visual con su hitbox.
        self.offset_x = (img_width - col_width) // 2
        self.offset_y = img_height - col_height

    # UPDATE PRINCIPAL
    def update(self, dt, walls, player, grid=None):
        """
        Llamar UNA vez por frame por cada enemigo:
            enemy.update(dt, walls, self.player, self.pathfinding_grid)
        """
        self.current_walls = walls
        moving = False

        # 1) Percepción: Decide si cambia de estado por haber visto / perdido a Snake.
        self._update_perception(dt, player, walls)

        # 2) Comportamiento del estado actual:
        if self.state == "WALKING":
            moving = self._patrol(dt)
        elif self.state == "LOOKING":
            self._look(dt)
        elif self.state == "ALERT":
            self._alert(dt, player)
        elif self.state == "CHASE":
            moving = self._chase(dt, player, grid)
        elif self.state == "SEARCH":
            moving = self._search(dt, grid)
        elif self.state == "RETURN":
            moving = self._return(dt, grid)

        self.is_moving = moving

        # 3) Animación de caminar.
        if moving:
            self.anim_timer += dt
            if self.anim_timer >= self.animation_speed:
                self.anim_timer = 0.0
                self.frame_index = (self.frame_index + 1) % 2

    # PERCEPCIÓN (lógica pura, NO dibuja nada)
    
    def _update_perception(self, dt, player, walls):
        self.sees_player = self.can_see_player(player, walls)

        if self.sees_player:
            self.last_known_pos = player.rect.center
            self.lost_timer = 0.0
            if self.state not in ("ALERT", "CHASE"):
                self._set_state("ALERT")
                self._face_towards(*player.rect.center)
                # SE VUELVE LOCO EL GUARDIA SI SE QUEDA MIRANDO A LA PARED.
        elif self.state == "CHASE":
            # No corta al instante: Tiene un margen para no "parpadear" entre CHASE y SEARCH. 
            self.lost_timer += dt
            if self.lost_timer >= self.LOSE_SIGHT_TIME:
                self._set_state("SEARCH")

    def _eye_pos(self):
        """Origen del cono de visión ( A la altura de la cabeza. Democracia. )."""
        return self.rect.centerx, self.rect.top - self.offset_y // 2

    def _vision_facing(self):
        """Hacia dónde mira realmente ( En LOOKING va girando la cabeza. )."""
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
        """True si Snake está dentro del cono Y no hay una pared en el medio."""
        if getattr(player, "is_hidden", False):
            return False
        if (self.BOX_FOOLS_GUARDS
                and getattr(player, "is_disguised", False) # <- Para la Cardboard_Box.png.
                and not getattr(player, "is_moving", False)):
            return False

        ex, ey = self._eye_pos()
        px, py = player.rect.center
        dx, dy = px - ex, py - ey
        dist = math.hypot(dx, dy)
        if dist == 0:
            return True

        # Si ya te está persiguiendo, te "siente" cerca aunque estés a su espalda.
        close = self.state in ("ALERT", "CHASE") and dist <= self.AWARENESS_RADIUS

        if not close:
            fx, fy = self.DIRS[self._vision_facing()]
            forward = dx * fx + dy * fy          # Distancia en la dirección en que mira.
            side = abs(-dx * fy + dy * fx)       # Distancia lateral.
            in_cone = 0 < forward <= self.VISION_RANGE and side <= forward * self.CONE_TAN
            if not in_cone:
                return False

        return self._has_line_of_sight(player.rect.center, walls)

    def _has_line_of_sight(self, target, walls):
        start = self.rect.center
        for wall in walls:
            if wall.clipline(start, target):   # Rect.clipline: ¿la línea cruza este rect?
                return False
        return True

    # ESTADOS.
    def _set_state(self, new_state):
        self.state = new_state
        self.state_timer = 0.0
        self.path = []
        self.path_finished = False
        self.repath_timer = 0.0   # Permite calcular ruta en cuanto esté en un carril.
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
        self._move_by(dx / dist * step, dy / dist * step)
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

    def _chase(self, dt, player, grid):
        if self.sees_player:
            # Te ve: Va a tu posición real y se frena al estar pegado.
            tx, ty = player.rect.center
            arrive = self.CATCH_DISTANCE
            finish = None
        else:
            # No te ve: Camina a donde te vió por última vez ( Ya no hace trampa siguiendo la posición real de Snake. )
            tx, ty = self.last_known_pos if self.last_known_pos else player.rect.center
            arrive = self.GRID_TILE
            finish = 3 * self.GRID_TILE

        moved, arrived = self._go_to(dt, grid, tx, ty, self.CHASE_SPEED, arrive, finish)

        if arrived:
            if self.sees_player:
                self._face_towards(tx, ty)
                self.on_reach_player(player)
            else:
                # Llegó al último punto donde te vio y no estás: Mira alrededor y vuelve a su patrulla.
                self._start_looking(self.SEARCH_LOOK_TIME, "RETURN")
        return moved

    def _search(self, dt, grid):
        self.state_timer += dt
        if self.last_known_pos is None or self.state_timer > self.SEARCH_TIMEOUT:
            self._set_state("RETURN")
            return False

        tx, ty = self.last_known_pos
        moved, arrived = self._go_to(dt, grid, tx, ty, self.SEARCH_SPEED,
                                     self.GRID_TILE, 3 * self.GRID_TILE)
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
        if arrived:
            self._set_state("WALKING")
        return moved

    def on_reach_player(self, player):
        """
        Gancho: Se llama cada frame mientras el guardia está pegado a Snake.
        Acá van después el disparo / golpe / game over.
        """
        pass

    
    # MOVIMIENTO Y PATHFINDING
    
    def _fcenter(self):
        """Centro del hitbox en float ( Más preciso que rect.center, que redondea. )."""
        return self.x + self.rect.width / 2, self.y + self.rect.height / 2

    def _on_lane(self):
        """True si el centro del guardia está justo en el centro de una celda de la grilla."""
        ts = self.GRID_TILE
        fx, fy = self._fcenter()
        return abs(fx % ts - ts / 2) < 0.75 and abs(fy % ts - ts / 2) < 0.75

    def _go_to(self, dt, grid, tx, ty, speed, arrive_dist, finish_dist=None):
        """
        Va hacia ( tx, ty ) con A*. Devuelve ( "se_movio", "llego").

        arrive_dist: Llegó si está a esta distancia o menos.
        finish_dist: Además, llegó si terminó de recorrer su ruta y está a esta distancia
                    o menos ( Evita quedarse dando vueltas si el destino está pegado a una
                    pared y la grilla lo corrió a la celda libre más cercana. ).
        """
        fx, fy = self._fcenter()
        dist = math.hypot(tx - fx, ty - fy)

        if dist <= arrive_dist:
            self.path = []
            return False, True
        if (finish_dist is not None and self.path_finished
                and not self.path and dist <= finish_dist):
            return False, True

        # Solo recalcula cuando venció el timer Y está en el centro de una celda ( O perdido sin ruta, ).
        # Así nunca cambia de ruta "a mitad de camino" y no hay tirones ni giros ni vueltas en U ni caminatas de espaldas.
        self.repath_timer -= dt
        if self.repath_timer <= 0 and (not self.path or self._on_lane()):
            self.repath_timer = self.REPATH_INTERVAL
            new_path = self._find_path(grid, tx, ty)
            if new_path is None:
                self.path = []
                self.path_finished = False
            else:
                self.path = new_path
                self.path_finished = (len(new_path) == 0)

        return self._follow_path(dt, speed), False

    def _follow_path(self, dt, speed):
        """
        Avanza por la ruta moviéndose de a UN eje por vez ( Núnca en diagonal. O EJE X O EJE Y.),
        siempre hacia el centro del siguiente nodo. True si se movió.
        """
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

            self._face_vector(mx, my)
            before = self.rect.center
            self._move_by(mx, my)

            # Red de seguridad: Si no avanza nada ( Pared inesperada. ), descarta el nodo y recalcula ruta.
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

    def _find_path(self, grid, tx, ty):
        """
        A* sobre la grilla. Devuelve una lista de puntos ( px, py ), [] si ya está en el
        destino, o None si no hay camino.
        """
        if grid is None:
            return [(tx, ty)]  # Sin grilla: línea recta ( Igual respeta colisiones al moverse. )

        ts = self.GRID_TILE
        fx, fy = self._fcenter()
        own_cell = (int(fx // ts), int(fy // ts))

        start = self._nearest_walkable(grid, own_cell[0], own_cell[1], fx, fy)
        goal = self._nearest_walkable(grid, int(tx // ts), int(ty // ts), tx, ty)
        if start is None or goal is None:
            if self.DEBUG_AI:
                print(f"[IA] sin celda libre cerca: start={start} goal={goal}")
            return None

        try:
            grid.cleanup()
            path, _runs = AStarFinder().find_path(grid.node(*start), grid.node(*goal), grid)
        except Exception as e:
            print(f"Aviso: falló el pathfinding: {e}")
            return None

        if not path:
            if self.DEBUG_AI:
                print(f"[IA] A* no encontró camino de {start} a {goal}")
            return None

        points = []
        for node in path:
            # Según la versión de la librería, un nodo es objeto ( .x/.y ) o una tupla.
            nx, ny = (node.x, node.y) if hasattr(node, "x") else node
            points.append((nx * ts + ts / 2, ny * ts + ts / 2))

        # Si ya está parado en el centro de su celda, ese primer nodo sobra.
        # Si NO está centrado, lo conservamos: Es decir, primero se alinea al carril y después avanza.
        if start == own_cell and self._on_lane():
            points.pop(0)
        return points

    def _nearest_walkable(self, grid, cx, cy, px, py, radius=4):
        """
        Si la celda ( cx, cy ) está bloqueada, busca la celda libre más cercana al punto ( px, py ),
        mirando en anillos crecientes.
        """
        ts = self.GRID_TILE
        for r in range(radius + 1):
            best = None
            best_d = None
            for oy in range(-r, r + 1):
                for ox in range(-r, r + 1):
                    if max(abs(ox), abs(oy)) != r:
                        continue
                    x, y = cx + ox, cy + oy
                    if grid.inside(x, y) and grid.walkable(x, y):
                        d = (x * ts + ts / 2 - px) ** 2 + (y * ts + ts / 2 - py) ** 2
                        if best is None or d < best_d:
                            best, best_d = (x, y), d
            if best is not None:
                return best
        return None

    def _move_by(self, mx, my):
        """Mueve en píxeles resolviendo colisiones por eje ( X y después Y. )."""
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
        for wall in walls:
            if self.rect.colliderect(wall):
                if dx > 0:
                    self.rect.right = wall.left
                elif dx < 0:
                    self.rect.left = wall.right
                self.x = float(self.rect.x)

    def check_collisions_y(self, walls, dy):
        for wall in walls:
            if self.rect.colliderect(wall):
                if dy > 0:
                    self.rect.bottom = wall.top
                elif dy < 0:
                    self.rect.top = wall.bottom
                self.y = float(self.rect.y)

    # DIBUJO
    
    @classmethod
    def _get_alert_icon(cls):
        """Carga ( Una sola vez. ) el PNG del icono de alerta."""
        if cls._alert_icon is None:
            try:
                img = pygame.image.load(cls.ALERT_ICON_PATH).convert_alpha()
                s = cls.ALERT_ICON_SCALE
                cls._alert_icon = pygame.transform.scale(
                    img, (int(img.get_width() * s), int(img.get_height() * s))
                )
            except Exception as e:
                print(f"Aviso: No se pudo cargar.  {cls.ALERT_ICON_PATH}: {e}")
                cls._alert_icon = pygame.Surface((1, 1), pygame.SRCALPHA)  # invisible
        return cls._alert_icon

    def draw_vision(self, surface, camera):
        """Dibuja el cono de visión ( Solo visual: la detección está en "can_see_player". )."""
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

        vision_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(vision_surface, color, points)
        surface.blit(vision_surface, (0, 0))

        # Debug: ruta A* actual
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

        pygame.draw.rect(surface, (255, 0, 0), dest_rect, 1)  # Debug del hitbox.
        surface.blit(current_image, (draw_x, draw_y))

        # Icono de alerta sobre la cabeza mientras reacciona.
        if self.state == "ALERT":
            icon = self._get_alert_icon()
            surface.blit(icon, (dest_rect.centerx - icon.get_width() // 2,
                                draw_y - icon.get_height() - 2))
