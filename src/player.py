import pygame
from src.settings import PLAYER_SPEED

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        
        # Posición exacta en decimales para que el movimiento sea fluido.
        self.x = float(x)
        self.y = float(y)
        
        # Dirección actual ("UP", "DOWN", "LEFT", "RIGHT").
        self.facing = "DOWN"
        self.is_moving = False

        # Control de animación y carga de sprites.
        self.anim_timer = 0.0
        self.frame_index = 0
        self.animation_speed = 0.15  # Segundos por CADA frame.
        
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
            }
        }
        
        # Obtenemos la primera imagen para medir dimensiones.
        first_image = self.animations["IDLE"]["DOWN"]
        img_width, img_height = first_image.get_size()

        # CREAMOS UN RECT DE COLISIÓN AJUSTADO ( Más chico y ubicado en los pies. )
        # Ancho menor para que no se trabe en pasillos angostos y alto reducido ( Ej: un tercio inferior. )
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

    def update(self, dt, walls):
        dx, dy = self.handle_input()
        
        if dx != 0 or dy != 0:
            self.is_moving = True
            
            # MOVIMIENTO Y COLISIÓN EN EJE X 
            self.x += dx * PLAYER_SPEED * dt
            self.rect.x = round(self.x)
            
            for wall in walls:
                if self.rect.colliderect(wall):
                    if dx > 0:
                        self.rect.right = wall.left
                    elif dx < 0:
                        self.rect.left = wall.right # <- No volver a cambiar esto.
                    self.x = float(self.rect.x)

            # MOVIMIENTO Y COLISIÓN EN EJE Y 
            self.y += dy * PLAYER_SPEED * dt
            self.rect.y = round(self.y)
            
            for wall in walls:
                if self.rect.colliderect(wall):
                    if dy > 0:
                        self.rect.bottom = wall.top
                    elif dy < 0:
                        self.rect.top = wall.bottom
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

    def draw(self, surface):
        if self.is_moving:
            current_image = self.animations["WALK"][self.facing][self.frame_index]
        else:
            current_image = self.animations["IDLE"][self.facing]
            
        # Se dibuja la imagen desplazada hacia arriba para que los pies coincidan con "self.rect".
        draw_pos = (self.rect.x - self.offset_x, self.rect.y - self.offset_y)
        surface.blit(current_image, draw_pos)

    def draw_with_camera(self, surface, camera):
        if self.is_moving:
            current_image = self.animations["WALK"][self.facing][self.frame_index]
        else:
            current_image = self.animations["IDLE"][self.facing]
            
        # Se obtiene la posición de la cámara basada en el rect de colisión ( Ubicado en los pies. )
        dest_rect = camera.apply(self)
        
        # Offset visual para que el cuerpo quede arriba de los pies.
        draw_x = dest_rect.x - self.offset_x
        draw_y = dest_rect.y - self.offset_y
        
        surface.blit(current_image, (draw_x, draw_y))