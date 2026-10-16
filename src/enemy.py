import pygame
from src.settings import PLAYER_SPEED

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, patrol_points):
        super().__init__()

        self.x = float(x)
        self.y = float(y)

        self.patrol_points = patrol_points  # Lista de coordenadas (x, y) sacadas de Tiled
        self.current_target_index = 0
        self.speed = 1.55

        self.facing = "DOWN"

        # Control de animación y carga de sprites.
        self.anim_timer = 0.0
        self.frame_index = 0
        self.animation_speed = 0.2  # Segundos por CADA frame.

        self.state = "WALKING"
        self.look_timer = 0.0
        self.look_duration = 1.5
        self.look_step = 0
        
        # CARGAR SPRITES ( Inicializa self.rect con el tamaño real de la imagen escalada. ).
        self.load_sprites()

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
                "DOWN": [
                    cs("assets/sprites/red_beret/walk_down1.png"),
                    cs("assets/sprites/red_beret/walk_down2.png")
                ],
                "UP": [
                    cs("assets/sprites/red_beret/walk_up1.png"),
                    cs("assets/sprites/red_beret/walk_up2.png")
                ],
                "LEFT": [
                    cs("assets/sprites/red_beret/walk_left1.png"),
                    cs("assets/sprites/red_beret/walk_left2.png")
                ],
                "RIGHT": [
                    cs("assets/sprites/red_beret/walk_right1.png"),
                    cs("assets/sprites/red_beret/walk_right2.png")
                ]
            },
            "LOOK": {
                "DOWN": [
                    cs("assets/sprites/red_beret/walk_down2.png"),
                    cs("assets/sprites/red_beret/look_down1.png"),
                    cs("assets/sprites/red_beret/walk_down2.png"),
                    cs("assets/sprites/red_beret/look_down2.png")
                ],
                "UP": [
                    cs("assets/sprites/red_beret/walk_up1.png"),
                    cs("assets/sprites/red_beret/look_up1.png"),
                    cs("assets/sprites/red_beret/walk_up1.png"),
                    cs("assets/sprites/red_beret/look_up2.png")
                ],
                "LEFT": [
                    cs("assets/sprites/red_beret/walk_left1.png"),
                    cs("assets/sprites/red_beret/look_left1.png"),
                    cs("assets/sprites/red_beret/walk_left1.png"),
                    cs("assets/sprites/red_beret/look_left2.png")
                ],
                "RIGHT": [
                    cs("assets/sprites/red_beret/walk_right1.png"),
                    cs("assets/sprites/red_beret/look_right1.png"),
                    cs("assets/sprites/red_beret/walk_right1.png"),
                    cs("assets/sprites/red_beret/look_right2.png")
                ]
            }
        }
        
        # Obtenemos la primera imagen para medir dimensiones.
        first_image = self.animations["IDLE"]["DOWN"]
        img_width, img_height = first_image.get_size()

        # CREAMOS UN RECT DE COLISIÓN AJUSTADO
        col_width = int(img_width * 0.6)   # 60% del ancho del Sprite.
        col_height = int(img_height * 0.3) # 30% de la altura ( Zona de los pies. )
        
        self.rect = pygame.Rect(self.x, self.y, col_width, col_height)
        
        # Guardamos un offset para saber cuánto subir la imagen al dibujarla respecto al rect de colisión.
        self.offset_x = (img_width - col_width) // 2
        self.offset_y = img_height - col_height

    def update(self, dt):
        if self.state == "WALKING":
            target_x, target_y = self.patrol_points[self.current_target_index]

            dx = target_x - self.x
            dy = target_y - self.y
            distance = (dx ** 2 + dy ** 2) ** 0.5

            if distance < 3.0:  
                self.state = "LOOKING"
                self.look_timer = 0.0
                self.look_step = 0
                
                # Avanzamos el índice del target de una vez para que sepa a dónde irá después
                self.current_target_index = (self.current_target_index + 1) % len(self.patrol_points)
            else:
                # Nos movemos hacia el target
                direction_x = dx / distance
                direction_y = dy / distance

                self.x += direction_x * self.speed * dt * 60  # Multiplicado por 60 para ajustar escala de velocidad por frame
                self.y += direction_y * self.speed * dt * 60

                # Actualizar hacia dónde mira según el movimiento
                if abs(dx) > abs(dy):
                    self.facing = "RIGHT" if dx > 0 else "LEFT"
                else:
                    self.facing = "DOWN" if dy > 0 else "UP"

            # Animación normal de caminar (si usa 2 frames)
            self.anim_timer += dt
            if self.anim_timer >= self.animation_speed:
                self.anim_timer = 0.0
                self.frame_index = (self.frame_index + 1) % 2

        elif self.state == "LOOKING":
            self.look_timer += dt
            
            # Cada vez que transcurra 'look_duration' segundos, pasa al siguiente paso de giro
            if self.look_timer >= self.look_duration:
                self.look_timer = 0.0
                self.look_step += 1
                
                # Si ya completó los 4 pasos (0: frente, 1: izq, 2: frente nuevamente, 3: der), vuelve a caminar
                if self.look_step > 3:
                    self.state = "WALKING"
                    self.look_step = 0

            # Aquí manejas qué frame mostrar según el 'look_step' y tu diccionario LOOK
            # frame_index 0 = Frente (walk_X2 o look_X1)
            # frame_index 1 = Costado izquierdo
            # frame_index 2 = Costado derecho
            self.frame_index = self.look_step 

        # Sincronizamos el rect de colisión con la posición flotante
        self.rect.x = round(self.x)
        self.rect.y = round(self.y)

    # Sistema de colisiones, se va a implementar una vez se desarrolle la logica de redireccion

    # def check_collisions_x(self, walls, dx):
    #     for wall in walls:
    #         if self.rect.colliderect(wall):
    #             if dx > 0:
    #                 self.rect.right = wall.left
    #             elif dx < 0:
    #                 self.rect.left = wall.right
    #             self.x = float(self.rect.x)

    # def check_collisions_y(self, walls, dy):
    #     for wall in walls:
    #         if self.rect.colliderect(wall):
    #             if dy > 0:
    #                 self.rect.bottom = wall.top
    #             elif dy < 0:
    #                 self.rect.top = wall.bottom
    #             self.y = float(self.rect.y)

    def has_reached(self, target):
        # Esta función auxiliar evalúa si está muy cerca del objetivo
        target_x, target_y = target
        distance = ((target_x - self.x) ** 2 + (target_y - self.y) ** 2) ** 0.5
        return distance < 2.0

    def check_vision(self, player, walls_rects, screen_surface, camera):
        # Configuración del cono
        max_distance = 5 * 32  # 5 tiles de distancia (160 px con scale=2)
        cone_color_green = (0, 255, 0, 100)   # Verde semitransparente
        cone_color_red = (255, 0, 0, 100)     # Rojo si detecta al jugador
        
        # Centro del enemigo (origen de la visión)
        start_x = self.x + self.rect.width / 2
        start_y = self.y + self.rect.height / 2
        
        # Rotar la dirección del cono adaptado a tus 4 pasos de LOOK:
        # [Frente, Izquierda, Frente, Derecha]
        current_facing = self.facing
        if getattr(self, "state", "") == "LOOKING":
            look_rotations = {
                "DOWN": ["DOWN", "LEFT", "DOWN", "RIGHT"],
                "UP": ["UP", "LEFT", "UP", "RIGHT"],
                "LEFT": ["LEFT", "DOWN", "LEFT", "UP"],
                "RIGHT": ["RIGHT", "DOWN", "RIGHT", "UP"]
            }
            steps_list = look_rotations.get(self.facing, ["DOWN", "LEFT", "DOWN", "RIGHT"])
            step_idx = min(getattr(self, "look_step", 0), len(steps_list) - 1)
            current_facing = steps_list[step_idx]

        angles = {
            "UP": (0, -1),
            "DOWN": (0, 1),
            "LEFT": (-1, 0),
            "RIGHT": (1, 0)
        }
        
        dir_x, dir_y = angles.get(current_facing, (0, 1))
        
        detected = False
        
        # Superficie con transparencia para el cono
        vision_surface = pygame.Surface((screen_surface.get_width(), screen_surface.get_height()), pygame.SRCALPHA)
        
        # Vector perpendicular para abrir el cono a los costados
        perp_x, perp_y = -dir_y, dir_x
        cone_width_factor = 0.8
        
        left_edge_x = start_x + (dir_x - perp_x * cone_width_factor) * max_distance
        left_edge_y = start_y + (dir_y - perp_y * cone_width_factor) * max_distance
        
        right_edge_x = start_x + (dir_x + perp_x * cone_width_factor) * max_distance
        right_edge_y = start_y + (dir_y + perp_y * cone_width_factor) * max_distance
        
        p_center = (start_x + camera.camera_rect.x, start_y + camera.camera_rect.y)
        p_left = (left_edge_x + camera.camera_rect.x, left_edge_y + camera.camera_rect.y)
        p_right = (right_edge_x + camera.camera_rect.x, right_edge_y + camera.camera_rect.y)
        
        # Coordenadas del centro del jugador
        player_center_x = player.rect.centerx
        player_center_y = player.rect.centery
        
        # Vector hacia el jugador y distancia
        to_player_x = player_center_x - start_x
        to_player_y = player_center_y - start_y
        dist_to_player = (to_player_x**2 + to_player_y**2)**0.5
        
        in_cone = False
        if dist_to_player <= max_distance and dist_to_player > 0:
            norm_px = to_player_x / dist_to_player
            norm_py = to_player_y / dist_to_player
            
            # Producto escalar para verificar si está dentro del ángulo frontal (~35 grados de apertura)
            dot_product = norm_px * dir_x + norm_py * dir_y
            if dot_product >= 0.65:
                in_cone = True

        if in_cone:
            # Comprobación de paredes más fina y precisa (caja de colisión más pequeña para evitar falsos positivos en pasillos)
            blocked_by_wall = False
            steps = 15  # Mayor muestreo para mayor precisión en espacios cerrados
            for i in range(1, steps + 1):
                check_x = start_x + to_player_x * (i / steps)
                check_y = start_y + to_player_y * (i / steps)
                
                # Rectángulo de prueba más pequeño (1x1 píxel) para no chocar con las paredes de los costados
                test_rect = pygame.Rect(check_x, check_y, 1, 1)
                for wall in walls_rects:
                    if test_rect.colliderect(wall):
                        blocked_by_wall = True
                        break
                if blocked_by_wall:
                    break
                    
            if not blocked_by_wall:
                detected = True

        # Color del cono según si detectó o no a Snake
        current_color = cone_color_red if detected else cone_color_green
        
        # Dibujar el triángulo del cono en pantalla
        pygame.draw.polygon(vision_surface, current_color, [p_center, p_left, p_right])
        screen_surface.blit(vision_surface, (0, 0))
        
        return detected

    def draw_with_camera(self, surface, camera):
        if self.state == "LOOKING":
            current_image = self.animations["LOOK"][self.facing][self.frame_index]
        else:
            current_image = self.animations["WALK"][self.facing][self.frame_index]
        
        # Obtenemos el rectángulo ajustado por la cámara
        dest_rect = camera.apply(self)

        # Dibujamos la imagen del enemigo en la posición de la cámara
        surface.blit(current_image, dest_rect)