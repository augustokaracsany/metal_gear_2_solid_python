import pygame
from src.settings import PLAYER_SPEED

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, patrol_points):
        super().__init__()

        self.x = float(x)
        self.y = float(y)

        self.patrol_points = patrol_points  # Lista de coordenadas (x, y) sacadas de Tiled
        self.current_target_index = 0
        self.speed = 1.75

        self.facing = "DOWN"

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
                "DOWN": cs("assets/sprites/red_beret/look_down1.png"),
                "UP": cs("assets/sprites/red_beret/look_up1.png"),
                "LEFT": cs("assets/sprites/red_beret/look_left1.png"),
                "RIGHT": cs("assets/sprites/red_beret/look_right2.png"),
            },
            "WALK": {
                "DOWN": [
                    cs("assets/sprites/red_beret/walk_down2.png"),
                    cs("assets/sprites/red_beret/walk_down1.png")
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
        target_x, target_y = self.patrol_points[self.current_target_index]

        # 2. Calculamos la distancia y dirección hacia el target
        dx = target_x - self.x
        dy = target_y - self.y
        
        # Distancia en línea recta usando el Teorema de Pitágoras
        distance = (dx ** 2 + dy ** 2) ** 0.5

        # 3. Verificamos si ya llegó al objetivo
        if distance < 2.0:  # Umbral de cercanía (2 píxeles)
            # Pasamos al siguiente punto de la lista de forma cíclica
            self.current_target_index = (self.current_target_index + 1) % len(self.patrol_points)
        else:
            # 4. Si aún no llega, nos movemos hacia él
            # Normalizamos el vector de movimiento y multiplicamos por la velocidad y dt
            direction_x = dx / distance
            direction_y = dy / distance

            self.x += direction_x * self.speed * dt * 60  # Multiplicado por 60 para ajustar escala de velocidad por frame
            self.y += direction_y * self.speed * dt * 60

            # 5. Opcional: Actualizar hacia dónde mira el guardia según el movimiento
            if abs(dx) > abs(dy):
                self.facing = "RIGHT" if dx > 0 else "LEFT"
            else:
                self.facing = "DOWN" if dy > 0 else "UP"

        # Sincronizamos el rect de colisión con la posición flotante
        self.rect.x = round(self.x)
        self.rect.y = round(self.y)

        self.anim_timer += dt
        if self.anim_timer >= self.animation_speed:
            self.anim_timer = 0.0
            self.frame_index = (self.frame_index + 1) % 2

    def has_reached(self, target):
        # Esta función auxiliar evalúa si está muy cerca del objetivo
        target_x, target_y = target
        distance = ((target_x - self.x) ** 2 + (target_y - self.y) ** 2) ** 0.5
        return distance < 2.0

    def draw_with_camera(self, surface, camera):
        # Seleccionamos la imagen actual según hacia dónde mira (facing)
        # Por ahora, si no tienes animación de caminar completa, puedes usar el IDLE:
        current_image = self.animations["WALK"][self.facing][self.frame_index]
        
        # Obtenemos el rectángulo ajustado por la cámara
        dest_rect = camera.apply(self)

        # Dibujamos la imagen del enemigo en la posición de la cámara
        surface.blit(current_image, dest_rect)