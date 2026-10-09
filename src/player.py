import pygame
from src.settings import PLAYER_SPEED

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        
        # Posición exacta en decimales para que no sea tosco.
        self.x = float(x)
        self.y = float(y)
        
        # Dimensiones temporales del sprite ( Placeholder esto. ).
        self.width = 128
        self.height = 128
        
        # Rect para colisiones y dibujado.
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

        # Variables para golpear

        self.is_punching = False
        self.init_time_punch = 0
        self.punch_length = 500

        self.last_punch = 0
        self.cooldown_punch = 600
        
        # Dirección actual ( "UP", "DOWN", "LEFT", "RIGHT" ).
        self.facing = "DOWN"
        self.is_moving = False

        # CARGAR SPRITES.
        # Control de animación y carga de sprites.
        self.load_sprites()
        self.anim_timer = 0.0
        self.frame_index = 0
        self.animation_speed = 0.15  # Velocidad de cambio de frame ( Segundos. )

    # CARGAR SPRITES.
    def load_sprites(self):
        SCALE_FACTOR = 2
        def cs(path):
            img = pygame.image.load(path).convert_alpha()
            w = int(img.get_width() * SCALE_FACTOR)
            h = int(img.get_height() * SCALE_FACTOR)
            return pygame.transform.scale(img, (w, h))
        # Diccionario estructurado para acceder fácil a los sprites de las animaciones.
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
        # Actualizamos el ancho y alto del rect del jugador según el tamaño de la nueva imagen escalada
        first_image = self.animations["IDLE"]["DOWN"]
        self.rect = first_image.get_rect(topleft=(self.x, self.y))

    def handle_input(self):
        keys = pygame.key.get_pressed()

        current_time = pygame.time.get_ticks()
        
        # Vector de movimiento en 2D.
        dx = 0
        dy = 0
        
        # Detecta teclas ( Flechas o WASD, como prefieras. ).
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
            if keys[pygame.K_e]:
                if current_time - self.last_punch >= self.cooldown_punch:
                    self.is_punching = True
                    self.init_time_punch = current_time
                    self.last_punch = current_time

            
        # Si se mueve en diagonal, se normaliza el vector para que no vaya más rápido de lo que debería en diagonal.
        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071
            
        return dx, dy

    def update(self, dt):
        current_time = pygame.time.get_ticks()

        if self.is_punching:
            if current_time - self.init_time_punch >= self.punch_length:
                self.is_punching = False

        dx, dy = self.handle_input()
        
        if (dx != 0 or dy != 0) and not self.is_punching:
            self.is_moving = True
            # Actualizamos la posición usando velocidad * delta_time.
            self.x += dx * PLAYER_SPEED * dt
            self.y += dy * PLAYER_SPEED * dt
        else:
            self.is_moving = False

        # Sincronizamos el rect con la posición redondeada ( Clave para evitar tirones ).
        self.rect.x = round(self.x)
        self.rect.y = round(self.y)

        # Lógica de animación por tiempo ( dt ).
        if self.is_moving:
            self.anim_timer += dt
            if self.anim_timer >= self.animation_speed:
                self.anim_timer = 0.0
                # Alterna el índice del frame entre 0 y 1 ( Porque cuatro frames componen la anim. )
                self.frame_index = (self.frame_index + 1) % 4
        else:
            # Si se detiene, se resetea al frame estático principal, el IDLE.
            self.frame_index = 0
            self.anim_timer = 0.0

    def draw(self, surface):
        # Seleccionamos el sprite correspondiente según el estado.
        if self.is_punching:
            current_image = self.animations["PUNCH"][self.facing]
        elif self.is_moving:
            current_image = self.animations["WALK"][self.facing][self.frame_index]
        else:
            current_image = self.animations["IDLE"][self.facing]
            
        # Dibujamos la imagen en la posición exacta del rect del jugador.
        surface.blit(current_image, self.rect)

    def draw_with_camera(self, surface, camera):
        # Seleccionamos el sprite correspondiente según el estado
        if self.is_punching:
            current_image = self.animations["PUNCH"][self.facing]
        elif self.is_moving:
            current_image = self.animations["WALK"][self.facing][self.frame_index]
        else:
            current_image = self.animations["IDLE"][self.facing]
            
        # Obtenemos el rectángulo ajustado por la cámara
        dest_rect = camera.apply(self)
        
        # Dibujamos la imagen en la posición de la cámara
        surface.blit(current_image, dest_rect)

        