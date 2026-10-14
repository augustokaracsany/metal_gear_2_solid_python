import pygame
from src.settings import PLAYER_SPEED
from src.obstacle import Obstacle

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        
        # Posición exacta en decimales para que el movimiento sea fluido.
        self.x = float(x)
        self.y = float(y)
        
        # Variables para golpear (añadidas por Lautaro)
        self.is_punching = False
        self.init_time_punch = 0
        self.punch_length = 500
        self.last_punch = 0
        self.cooldown_punch = 600
        
        # Dirección actual ("UP", "DOWN", "LEFT", "RIGHT").
        self.facing = "DOWN"
        self.is_moving = False

        # Control de animación y carga de sprites.
        self.anim_timer = 0.0
        self.frame_index = 0
        self.animation_speed = 0.15  # Segundos por CADA frame.
        
        # CARGAR SPRITES ( Inicializa self.rect con el tamaño real de la imagen escalada. ).
        self.load_sprites()

    def punch_self_event(self, event):
        current_time = pygame.time.get_ticks()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e:
                if current_time - self.last_punch >= self.cooldown_punch:
                    self.is_punching = True
                    self.init_time_punch = current_time
                    self.last_punch = current_time

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
                "DOWN": cs("assets/sprites/solid_python/stand_down.png"),
                "UP": cs("assets/sprites/solid_python/stand_up.png"),
                "LEFT": cs("assets/sprites/solid_python/stand_left.png"),
                "RIGHT": cs("assets/sprites/solid_python/stand_right.png"),
            },
            "WALK": {
                "DOWN": [
                    cs("assets/sprites/solid_python/stand_down.png"),
                    cs("assets/sprites/solid_python/walk_down1.png"),
                    cs("assets/sprites/solid_python/stand_down.png"),
                    cs("assets/sprites/solid_python/walk_down2.png")
                ],
                "UP": [
                    cs("assets/sprites/solid_python/stand_up.png"),
                    cs("assets/sprites/solid_python/walk_up1.png"),
                    cs("assets/sprites/solid_python/stand_up.png"),
                    cs("assets/sprites/solid_python/walk_up2.png")
                ],
                "LEFT": [
                    cs("assets/sprites/solid_python/stand_left.png"),
                    cs("assets/sprites/solid_python/walk_left1.png"),
                    cs("assets/sprites/solid_python/stand_left.png"),
                    cs("assets/sprites/solid_python/walk_left2.png")
                ],
                "RIGHT": [
                    cs("assets/sprites/solid_python/stand_right.png"),
                    cs("assets/sprites/solid_python/walk_right1.png"),
                    cs("assets/sprites/solid_python/stand_right.png"),
                    cs("assets/sprites/solid_python/walk_right2.png")
                ]
            },
            "PUNCH": {
                "DOWN": cs("assets/sprites/solid_python/punch_down.png"),
                "UP": cs("assets/sprites/solid_python/punch_up.png"),
                "LEFT": cs("assets/sprites/solid_python/punch_left.png"),
                "RIGHT": cs("assets/sprites/solid_python/punch_right.png"),
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

    def handle_input(self):
        keys = pygame.key.get_pressed()
        dx = 0
        dy = 0
        
        # Detecta teclas solo si no está golpeando
        if not self.is_punching:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                dx = -1
                self.facing = "LEFT"
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                dx = 1
                self.facing = "RIGHT"
                
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                dy = -1
                self.facing = "UP"
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                dy = 1
                self.facing = "DOWN"
            
        # Normalizar diagonal para velocidad constante
        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071
            
        return dx, dy

    def update(self, dt, walls_group):
        current_time = pygame.time.get_ticks()

        # Control del temporizador del golpe
        if self.is_punching:
            if current_time - self.init_time_punch >= self.punch_length:
                self.is_punching = False

        dx, dy = self.handle_input()
        
        if (dx != 0 or dy != 0) and not self.is_punching:
            self.is_moving = True
            
            # MOVIMIENTO Y COLISIÓN EN EJE X (usando método auxiliar de Lautaro)
            vel_x = dx * PLAYER_SPEED * dt
            self.x += vel_x
            self.rect.x = round(self.x)
            self.check_collisions_x(walls_group, vel_x)
            self.x = float(self.rect.x)

            # MOVIMIENTO Y COLISIÓN EN EJE Y (usando método auxiliar de Lautaro)
            vel_y = dy * PLAYER_SPEED * dt
            self.y += vel_y
            self.rect.y = round(self.y)
            self.check_collisions_y(walls_group, vel_y)
            self.y = float(self.rect.y)
        else:
            self.is_moving = False

        # GESTIÓN DE ANIMACIÓN.
        if self.is_moving:
            self.anim_timer += dt
            if self.anim_timer >= self.animation_speed:
                self.anim_timer = 0.0
                self.frame_index = (self.frame_index + 1) % 4
        else:
            self.frame_index = 0
            self.anim_timer = 0.0

    def check_collisions_x(self, walls_group, dx):
        hits = pygame.sprite.spritecollide(self, walls_group, False)
        for wall in hits:
            if dx > 0:
                self.rect.right = wall.rect.left
            elif dx < 0:
                self.rect.left = wall.rect.right
            self.x = float(self.rect.x)

    def check_collisions_y(self, walls_group, dy):
        hits = pygame.sprite.spritecollide(self, walls_group, False)
        for wall in hits:
            if dy > 0:
                self.rect.bottom = wall.rect.top
            elif dy < 0:
                self.rect.top = wall.rect.bottom
            self.y = float(self.rect.y)

    def draw(self, surface):
        if self.is_punching:
            current_image = self.animations["PUNCH"][self.facing]
        elif self.is_moving:
            current_image = self.animations["WALK"][self.facing][self.frame_index]
        else:
            current_image = self.animations["IDLE"][self.facing]
            
        draw_pos = (self.rect.x - self.offset_x, self.rect.y - self.offset_y)
        surface.blit(current_image, draw_pos)

    def draw_with_camera(self, surface, camera):
        if self.is_punching:
            current_image = self.animations["PUNCH"][self.facing]
        elif self.is_moving:
            current_image = self.animations["WALK"][self.facing][self.frame_index]
        else:
            current_image = self.animations["IDLE"][self.facing]
            
        dest_rect = camera.apply(self)
        
        draw_x = dest_rect.x - self.offset_x
        draw_y = dest_rect.y - self.offset_y
        
        surface.blit(current_image, (draw_x, draw_y))