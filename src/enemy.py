import pygame
from src.settings import PLAYER_SPEED

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, patrol_points):
        super().__init__()

        self.x = float(x)
        self.y = float(y)

        self.patrol_points = patrol_points  
        self.current_target_index = 0
        self.speed = 1.55

        self.facing = "DOWN"

        # Control de animación y carga de sprites.
        self.anim_timer = 0.0
        self.frame_index = 0
        self.animation_speed = 0.2  

        self.state = "WALKING"
        self.look_timer = 0.0
        self.look_duration = 1.5
        self.look_step = 0
        
        self.current_walls = []
        
        # CARGAR SPRITES 
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

        # Hitbox compacto en los pies (igual que Snake) para evitar que se trabe en esquinas
        col_width = int(img_width * 0.5) 
        col_height = int(img_height * 0.3) 
        
        self.rect = pygame.Rect(self.x, self.y, col_width, col_height)
        
        # Offsets correctos para alinear el sprite visual con su hitbox
        self.offset_x = (img_width - col_width) // 2
        self.offset_y = img_height - col_height

    def update(self, dt, walls_group=None):
        self.current_walls = walls_group if walls_group is not None else []

        if self.state == "WALKING":
            target_x, target_y = self.patrol_points[self.current_target_index]

            dx = target_x - self.x
            dy = target_y - self.y
            distance = (dx ** 2 + dy ** 2) ** 0.5

            if distance < 3.0:  
                self.state = "LOOKING"
                self.look_timer = 0.0
                self.look_step = 0
                self.current_target_index = (self.current_target_index + 1) % len(self.patrol_points)
            else:
                direction_x = dx / distance
                direction_y = dy / distance

                vel_x = direction_x * self.speed * dt * 60
                vel_y = direction_y * self.speed * dt * 60

                # Movimiento y colisiones en X separadas
                self.x += vel_x
                self.rect.x = round(self.x)
                self.check_collisions_x(self.current_walls, vel_x)

                # Movimiento y colisiones en Y separadas
                self.y += vel_y
                self.rect.y = round(self.y)
                self.check_collisions_y(self.current_walls, vel_y)

                # Actualizar hacia dónde mira según el movimiento dominante
                if abs(dx) > abs(dy):
                    self.facing = "RIGHT" if dx > 0 else "LEFT"
                else:
                    self.facing = "DOWN" if dy > 0 else "UP"

            self.anim_timer += dt
            if self.anim_timer >= self.animation_speed:
                self.anim_timer = 0.0
                self.frame_index = (self.frame_index + 1) % 2

        elif self.state == "LOOKING":
            self.look_timer += dt
            if self.look_timer >= self.look_duration:
                self.look_timer = 0.0
                self.look_step += 1
                
                if self.look_step > 3:
                    self.state = "WALKING"
                    self.look_step = 0

            self.frame_index = self.look_step 

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

    def check_vision(self, player, walls_rects, surface, camera):
        max_distance = 5 * 32  
        cone_color_green = (0, 255, 0, 100)  
        cone_color_red = (255, 0, 0, 100)    
        
        # Origen del cono: alineado al centro superior del rect (pecho/cabeza)
        start_x = self.rect.centerx
        start_y = self.rect.top - (self.offset_y // 2)  # Ajustado a la cabeza del soldado
        
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
        
        # Crear superficie para transparencias del tamaño de la superficie de juego
        vision_surface = pygame.Surface((surface.get_width(), surface.get_height()), pygame.SRCALPHA)
        
        perp_x, perp_y = -dir_y, dir_x
        cone_width_factor = 0.4
        
        left_edge_x = start_x + (dir_x - perp_x * cone_width_factor) * max_distance
        left_edge_y = start_y + (dir_y - perp_y * cone_width_factor) * max_distance
        
        right_edge_x = start_x + (dir_x + perp_x * cone_width_factor) * max_distance
        right_edge_y = start_y + (dir_y + perp_y * cone_width_factor) * max_distance
        
        # Convertir a coordenadas de cámara
        p_center = (start_x + camera.camera_rect.x, start_y + camera.camera_rect.y)
        p_left = (left_edge_x + camera.camera_rect.x, left_edge_y + camera.camera_rect.y)
        p_right = (right_edge_x + camera.camera_rect.x, right_edge_y + camera.camera_rect.y)
        
        player_center_x = player.rect.centerx
        player_center_y = player.rect.centery
        
        to_player_x = player_center_x - start_x
        to_player_y = player_center_y - start_y
        dist_to_player = (to_player_x**2 + to_player_y**2)**0.5
        
        in_cone = False
        if dist_to_player <= max_distance and dist_to_player > 0:
            norm_px = to_player_x / dist_to_player
            norm_py = to_player_y / dist_to_player
            
            dot_product = norm_px * dir_x + norm_py * dir_y
            if dot_product >= 0.65:
                in_cone = True

        if in_cone:
            blocked_by_wall = False
            steps = 15  
            for i in range(1, steps + 1):
                check_x = start_x + to_player_x * (i / steps)
                check_y = start_y + to_player_y * (i / steps)
                
                test_rect = pygame.Rect(check_x, check_y, 1, 1)
                for wall in walls_rects:
                    if test_rect.colliderect(wall):
                        blocked_by_wall = True
                        break
                if blocked_by_wall:
                    break
                    
            if not blocked_by_wall:
                detected = True

        current_color = cone_color_red if detected else cone_color_green
        
        # Renderizado del polígono
        pygame.draw.polygon(vision_surface, current_color, [p_center, p_left, p_right])
        surface.blit(vision_surface, (0, 0))
        
        return detected

    def draw_with_camera(self, surface, camera):
        if self.state == "LOOKING":
            current_image = self.animations["LOOK"][self.facing][self.frame_index]
        else:
            current_image = self.animations["WALK"][self.facing][self.frame_index]
        
        dest_rect = camera.apply(self)
        
        # Aplicamos los offsets correctamente para que no se dibuje desfasado ni duplicado
        draw_x = dest_rect.x - self.offset_x
        draw_y = dest_rect.y - self.offset_y

        pygame.draw.rect(surface, (255, 0, 0), dest_rect, 1)
        
        surface.blit(current_image, (draw_x, draw_y))
