import pygame
from src.settings import PLAYER_SPEED

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        
        # Posición exacta en decimales para que el movimiento sea fluido.
        self.x = float(x)
        self.y = float(y)
        
        # Variables para golpear
        self.is_punching = False
        self.init_time_punch = 0
        self.punch_length = 500
        self.last_punch = 0
        self.cooldown_punch = 600
        
        # Estados de postura: "STAND", "CROUCH", "CRAWL"
        self.stance = "STAND"

        # Bandera para saber si se agachó automáticamente por chocar o no tener espacio
        self.forced_crouch = False
        self.crouch_hold_timer = 0.0
        self.crouch_hold_duration = 1.5  # Tiempo mínimo en segundos que se quedará agachado.

        # Control de transición de posturas
        self.is_transitioning = False
        self.transition_timer = 0.0
        self.transition_duration = 0.18
        self.target_stance = None
        
        # Dirección actual ("UP", "DOWN", "LEFT", "RIGHT")
        self.facing = "DOWN"
        self.is_moving = False
        self.is_hidden = False
        self.hidden_zones = []
        self.hidden_zones_top = []
        self.hidden_zones_bottom = []
        self.top_barriers = []
        self.active_hidden_top_zone = None
        self.active_hidden_bottom_marker = None

        # Control de animación y carga de sprites
        self.anim_timer = 0.0
        self.frame_index = 0
        self.animation_speed = 0.15

        # Cargar sprites
        self.load_sprites_data()

        # Instancia el rect de colisión base
        stand_img = self.animations["IDLE"]["DOWN"]
        stand_w, stand_h = stand_img.get_size()
        col_width = int(stand_w * 0.6)
        col_height = int(stand_h * 0.3)
        self.rect = pygame.Rect(self.x, self.y, col_width, col_height)
        
        self.update_offsets_for_stance()

    def punch_self_event(self, event):
        current_time = pygame.time.get_ticks()
        if event.type == pygame.KEYDOWN:
            if (
                event.key in (pygame.K_c, pygame.K_LCTRL, pygame.K_RCTRL)
                and self.stance == "CRAWL"
                and self._is_inside_hidden_zone(self.rect)
            ):
                return

            if event.key == pygame.K_e:
                if self.stance == "STAND":
                    if current_time - self.last_punch >= self.cooldown_punch:
                        self.is_punching = True
                        self.init_time_punch = current_time
                        self.last_punch = current_time
            
            elif event.key == pygame.K_c:
                if self.stance == "STAND":
                    self.set_stance("CROUCH")
                elif self.stance == "CROUCH":
                    self.set_stance("STAND")
                elif self.stance == "CRAWL":
                    self.set_stance("CROUCH")
                    
            elif event.key in (pygame.K_LCTRL, pygame.K_RCTRL):
                if self.stance in ("STAND", "CROUCH"):
                    # AUTOMATIZACIÓN DE SEGURIDAD: Solo permite pasar a CRAWL si hay espacio adelante y atrás
                    if self.can_crawl() and self.has_space_behind():
                        self.start_stance_transition("CRAWL")
                elif self.stance == "CRAWL":
                    self.start_stance_transition("STAND")

    def set_stance(self, new_stance):
        if new_stance != "CRAWL" and self._is_inside_hidden_zone(self.rect):
            return

        if new_stance != self.stance:
            self.stance = new_stance
            self.frame_index = 0 
            self.anim_timer = 0.0
            self.update_offsets_for_stance()
            if new_stance != "CROUCH":
                self.forced_crouch = False

    def load_sprites_data(self):
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
                    cs("assets/sprites/solid_python/stand_down.png"), cs("assets/sprites/solid_python/walk_down1.png"),
                    cs("assets/sprites/solid_python/stand_down.png"), cs("assets/sprites/solid_python/walk_down2.png")
                ],
                "UP": [
                    cs("assets/sprites/solid_python/stand_up.png"), cs("assets/sprites/solid_python/walk_up1.png"),
                    cs("assets/sprites/solid_python/stand_up.png"), cs("assets/sprites/solid_python/walk_up2.png")
                ],
                "LEFT": [
                    cs("assets/sprites/solid_python/stand_left.png"), cs("assets/sprites/solid_python/walk_left1.png"),
                    cs("assets/sprites/solid_python/stand_left.png"), cs("assets/sprites/solid_python/walk_left2.png")
                ],
                "RIGHT": [
                    cs("assets/sprites/solid_python/stand_right.png"), cs("assets/sprites/solid_python/walk_right1.png"),
                    cs("assets/sprites/solid_python/stand_right.png"), cs("assets/sprites/solid_python/walk_right2.png")
                ]
            },
            "CROUCH": {
                "DOWN": [cs("assets/sprites/solid_python/crouch_down1.png"), cs("assets/sprites/solid_python/crouch_down2.png")],
                "UP": [cs("assets/sprites/solid_python/crouch_up1.png"), cs("assets/sprites/solid_python/crouch_up2.png")],
                "LEFT": [cs("assets/sprites/solid_python/crouch_left1.png"), cs("assets/sprites/solid_python/crouch_left2.png")],
                "RIGHT": [cs("assets/sprites/solid_python/crouch_right1.png"), cs("assets/sprites/solid_python/crouch_right2.png")]
            },
            "CRAWL": {
                "DOWN": [
                    cs("assets/sprites/solid_python/crawl_down.png"), 
                    cs("assets/sprites/solid_python/crawl_down1.png"), 
                    cs("assets/sprites/solid_python/crawl_down.png"), 
                    cs("assets/sprites/solid_python/crawl_down2.png")
                ],
                "UP": [
                    cs("assets/sprites/solid_python/crawl_up.png"), 
                    cs("assets/sprites/solid_python/crawl_up1.png"), 
                    cs("assets/sprites/solid_python/crawl_up.png"), 
                    cs("assets/sprites/solid_python/crawl_up2.png")
                ],
                "LEFT": [
                    cs("assets/sprites/solid_python/crawl_left.png"), 
                    cs("assets/sprites/solid_python/crawl_left1.png"), 
                    cs("assets/sprites/solid_python/crawl_left.png"), 
                    cs("assets/sprites/solid_python/crawl_left2.png")
                ],
                "RIGHT": [
                    cs("assets/sprites/solid_python/crawl_right.png"), 
                    cs("assets/sprites/solid_python/crawl_right1.png"), 
                    cs("assets/sprites/solid_python/crawl_right.png"), 
                    cs("assets/sprites/solid_python/crawl_right2.png")
                ]
            },
            "PUNCH": {
                "DOWN": cs("assets/sprites/solid_python/punch_down.png"),
                "UP": cs("assets/sprites/solid_python/punch_up.png"),
                "LEFT": cs("assets/sprites/solid_python/punch_left.png"),
                "RIGHT": cs("assets/sprites/solid_python/punch_right.png"),
            }
        }

    def update_offsets_for_stance(self):
        stand_img = self.animations["IDLE"]["DOWN"]
        stand_w, stand_h = stand_img.get_size()
        col_width = int(stand_w * 0.6)
        col_height = int(stand_h * 0.3)

        if self.stance == "STAND":
            ref_img = self.animations["IDLE"][self.facing]
        elif self.stance == "CROUCH":
            ref_img = self.animations["CROUCH"][self.facing][0]
        else: 
            ref_img = self.animations["CRAWL"][self.facing][0]

        img_width, img_height = ref_img.get_size()

        self.offset_x = (img_width - col_width) // 2
        
        if self.stance == "CRAWL" and self.facing in ("UP", "DOWN"):
            self.offset_y = (img_height - col_height) // 2
        elif self.stance == "CRAWL":
            self.offset_y = img_height - (col_height // 1.2)
        else:
            self.offset_y = img_height - col_height

    def start_stance_transition(self, target_stance):
        if not self.is_transitioning and not self._is_inside_hidden_zone(self.rect):
            self.target_stance = target_stance
            self.is_transitioning = True
            self.transition_timer = 0.0
            self.stance = "CROUCH"
            self.frame_index = 0
            self.update_offsets_for_stance()

    def handle_input(self):
        keys = pygame.key.get_pressed()
        dx = 0
        dy = 0
        
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

        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071
            
        return dx, dy

    def update(self, dt, walls_group, top_barriers=None, hidden_zones=None, hidden_zones_top=None, hidden_zones_bottom=None):
        self.current_walls = walls_group
        self.top_barriers = top_barriers if top_barriers is not None else []
        self.hidden_zones = hidden_zones if hidden_zones is not None else []
        self.hidden_zones_top = hidden_zones_top if hidden_zones_top is not None else []
        self.hidden_zones_bottom = hidden_zones_bottom if hidden_zones_bottom is not None else []

        self.is_hidden = self.stance == "CRAWL" and self._is_inside_hidden_zone(self.rect)

        if self.is_transitioning:
            self.transition_timer += dt
            if self.transition_timer >= self.transition_duration:
                self.set_stance(self.target_stance)
                self.is_transitioning = False
                self.target_stance = None

        current_time = pygame.time.get_ticks()

        if self.is_punching:
            if current_time - self.init_time_punch >= self.punch_length:
                self.is_punching = False

        facing_before_input = self.facing
        dx, dy = self.handle_input()

        self.update_offsets_for_stance()

        if self.stance == "STAND":
            current_speed = PLAYER_SPEED * 0.20 
        elif self.stance == "CROUCH":
            current_speed = PLAYER_SPEED * 0.10 
        elif self.stance == "CRAWL":
            current_speed = PLAYER_SPEED * 0.08  

        if self.stance == "CRAWL" and dy < 0 and self.active_hidden_top_zone is None:
            proposed_rect = self.rect.copy()
            proposed_rect.x = round(self.x + dx * current_speed * dt)
            proposed_rect.y = round(self.y + dy * current_speed * dt)
            entry = self._find_hidden_top_entry(proposed_rect, self.rect)
            if entry is not None:
                self.active_hidden_top_zone, self.active_hidden_bottom_marker = entry

        was_inside_hidden_zone = self.stance == "CRAWL" and self._is_inside_hidden_zone(self.rect)
        if was_inside_hidden_zone:
            dx = 0
            if dy < 0:
                self.facing = "UP"
            elif dy > 0:
                self.facing = "DOWN"
            else:
                self.facing = facing_before_input if facing_before_input in ("UP", "DOWN") else "UP"
            self.update_offsets_for_stance()

        # Descontar temporizador de retención si está agachado forzosamente
        if self.forced_crouch:
            if self.crouch_hold_timer > 0:
                self.crouch_hold_timer -= dt

        if (dx != 0 or dy != 0) and not self.is_punching:
            self.is_moving = True

            # AUTOMATIZACIÓN 1: Anticipación frontal.
            if self.stance == "CRAWL" and not was_inside_hidden_zone and self.check_upcoming_obstacle():
                self.set_stance("CROUCH")
                self.forced_crouch = True
                self.crouch_hold_timer = self.crouch_hold_duration

            # AUTOMATIZACIÓN 2: Recuperación trasera/lateral con temporizador.
            if self.stance == "CROUCH" and self.forced_crouch:
                if self.crouch_hold_timer <= 0 and self.can_crawl() and self.has_space_behind():
                    self.set_stance("CRAWL")
                    self.forced_crouch = False

            # Movimiento en Eje X
            vel_x = dx * current_speed * dt
            self.x += vel_x
            self.rect.x = round(self.x)
            self.check_collisions_x(walls_group, vel_x)

            # Movimiento en Eje Y
            vel_y = dy * current_speed * dt
            previous_rect = self.rect.copy()
            self.y += vel_y
            self.rect.y = round(self.y)
            self.check_collisions_y(walls_group, vel_y, previous_rect)
        else:
            self.is_moving = False

        # GESTIÓN DE ANIMACIÓN
        if self.is_moving:
            self.anim_timer += dt
            if self.anim_timer >= self.animation_speed:
                self.anim_timer = 0.0
                if self.stance == "CROUCH":
                    num_frames = len(self.animations["CROUCH"][self.facing])
                    self.frame_index = (self.frame_index + 1) % num_frames
                elif self.stance == "CRAWL":
                    num_frames = len(self.animations["CRAWL"][self.facing])
                    self.frame_index = (self.frame_index + 1) % num_frames
                else:
                    self.frame_index = (self.frame_index + 1) % 4  
        else:
            if self.stance != "STAND":
                self.frame_index = 0
            self.anim_timer = 0.0

        if (
            self.active_hidden_top_zone is not None
            and not self.rect.colliderect(self.active_hidden_top_zone)
            and not self.rect.colliderect(self.active_hidden_bottom_marker)
        ):
            self.active_hidden_top_zone = None
            self.active_hidden_bottom_marker = None

        self.is_hidden = self.stance == "CRAWL" and self._is_inside_hidden_zone(self.rect)

    def check_collisions_x(self, walls, dx):
        collided = False
        collided_with_normal_wall = False

        for wall in walls:
            if self.rect.colliderect(wall):
                is_crawl_passage_wall = self._wall_is_in_crawlable_zone(wall)
                if self.stance == "CRAWL" and is_crawl_passage_wall:
                    continue

                collided = True
                if dx > 0:
                    self.rect.right = wall.left
                elif dx < 0:
                    self.rect.left = wall.right
                self.x = float(self.rect.x)

                if not is_crawl_passage_wall:
                    collided_with_normal_wall = True

        if collided_with_normal_wall and self.stance == "CRAWL":
            self.set_stance("CROUCH")
            self.forced_crouch = True
            self.crouch_hold_timer = self.crouch_hold_duration

    def check_collisions_y(self, walls, dy, previous_rect=None):
        collided = False
        collided_with_normal_wall = False
        previous_rect = previous_rect if previous_rect is not None else self.rect.copy()

        # 1. Comprobamos colisión con paredes normales
        for wall in walls:
            if self.rect.colliderect(wall):
                is_crawl_passage_wall = self._wall_is_in_crawlable_zone(wall)
                if self.stance == "CRAWL" and is_crawl_passage_wall:
                    continue

                collided = True
                if dy > 0:
                    self.rect.bottom = wall.top
                elif dy < 0:
                    self.rect.top = wall.bottom
                self.y = float(self.rect.y)

                if not is_crawl_passage_wall:
                    collided_with_normal_wall = True

        if self.stance == "CRAWL" and self.top_barriers:
            for barrier in self.top_barriers:
                if not self.rect.colliderect(barrier):
                    continue

                for zone in self.hidden_zones_top:
                    if not self._barrier_belongs_to_top_zone(barrier, zone):
                        continue
                    if not zone.left <= previous_rect.centerx < zone.right:
                        continue

                    if dy > 0 and previous_rect.bottom <= barrier.top:
                        self.rect.bottom = barrier.top
                    elif (
                        dy < 0
                        and self.active_hidden_top_zone is zone
                        and self._rect_is_inside_top_zone(previous_rect, zone)
                    ):
                        self.rect.top = barrier.bottom
                    else:
                        continue

                    self.y = float(self.rect.y)
                    break

        if collided_with_normal_wall and self.stance == "CRAWL":
            self.set_stance("CROUCH")
            self.forced_crouch = True
            self.crouch_hold_timer = self.crouch_hold_duration

    def _rect_is_inside_top_zone(self, rect, zone):
        return (
            zone.left <= rect.centerx < zone.right
            and zone.top <= rect.centery < zone.bottom
        )

    def _barrier_belongs_to_top_zone(self, barrier, zone):
        horizontal_overlap = barrier.left < zone.right and barrier.right > zone.left
        return horizontal_overlap and barrier.bottom == zone.top

    def _is_inside_hidden_zone(self, rect):
        if any(rect.colliderect(zone) for zone in self.hidden_zones):
            return True
        return (
            self.active_hidden_top_zone is not None
            and (
                self._rect_is_inside_top_zone(rect, self.active_hidden_top_zone)
                or rect.colliderect(self.active_hidden_bottom_marker)
            )
        )

    def _find_hidden_top_entry(self, proposed_rect, previous_rect):
        for marker in self.hidden_zones_bottom:
            if not proposed_rect.colliderect(marker) or previous_rect.centery < marker.bottom:
                continue

            zone = next(
                (
                    zone for zone in self.hidden_zones_top
                    if zone.left < marker.right
                    and zone.right > marker.left
                    and zone.bottom == marker.top
                ),
                None,
            )
            if zone is not None:
                return zone, marker
        return None

    def _wall_is_in_crawlable_zone(self, wall, player_rect=None):
        player_rect = player_rect if player_rect is not None else self.rect
        return (
            any(player_rect.colliderect(zone) and zone.colliderect(wall) for zone in self.hidden_zones)
            or (
                self.active_hidden_top_zone is not None
                and (
                    player_rect.colliderect(self.active_hidden_top_zone)
                    or player_rect.colliderect(self.active_hidden_bottom_marker)
                )
                and self.active_hidden_top_zone.colliderect(wall)
            )
        )

    def _wall_is_on_inactive_top_surface(self, wall, player_rect):
        return (
            self.active_hidden_top_zone is None
            and any(
                zone.colliderect(wall)
                and zone.left <= player_rect.centerx < zone.right
                and player_rect.bottom <= zone.top
                for zone in self.hidden_zones_top
            )
        )

    def _wall_is_ahead_of_bottom_entry(self, wall, player_rect):
        if self.stance != "CRAWL" or self.facing != "UP" or self.active_hidden_top_zone is not None:
            return False

        for marker in self.hidden_zones_bottom:
            if not marker.left <= player_rect.centerx < marker.right or player_rect.top < marker.top:
                continue

            zone = next(
                (
                    zone for zone in self.hidden_zones_top
                    if zone.left < marker.right
                    and zone.right > marker.left
                    and zone.bottom == marker.top
                ),
                None,
            )
            if zone is not None and zone.colliderect(wall):
                return True
        return False

    def can_crawl(self):
        if not hasattr(self, 'current_walls') or not self.current_walls:
            return True

        test_rect = self.rect.copy()
        check_distance = 6

        if self.facing == "UP":
            test_rect.y -= check_distance
        elif self.facing == "DOWN":
            test_rect.y += check_distance
        elif self.facing == "LEFT":
            test_rect.x -= check_distance
        elif self.facing == "RIGHT":
            test_rect.x += check_distance

        for wall in self.current_walls:
            if test_rect.colliderect(wall):
                if (
                    not self._wall_is_in_crawlable_zone(wall, test_rect)
                    and not self._wall_is_on_inactive_top_surface(wall, self.rect)
                ):
                    return False
        return True

    def check_upcoming_obstacle(self):
        if not hasattr(self, 'current_walls') or not self.current_walls:
            return False

        test_rect = self.rect.copy()
        look_ahead = 30

        if self.facing == "UP":
            test_rect.y -= look_ahead
        elif self.facing == "DOWN":
            test_rect.y += look_ahead
        elif self.facing == "LEFT":
            test_rect.x -= look_ahead
        elif self.facing == "RIGHT":
            test_rect.x += look_ahead

        for wall in self.current_walls:
            if test_rect.colliderect(wall):
                if (
                    not self._wall_is_in_crawlable_zone(wall, test_rect)
                    and not self._wall_is_on_inactive_top_surface(wall, self.rect)
                    and not self._wall_is_ahead_of_bottom_entry(wall, self.rect)
                ):
                    return True
        return False

    def has_space_behind(self):
        if not hasattr(self, 'current_walls') or not self.current_walls:
            return True

        body_length = 26 
        test_rect = self.rect.copy()

        if self.facing == "UP":
            test_rect.height += body_length
        elif self.facing == "DOWN":
            test_rect.y -= body_length
            test_rect.height += body_length
        elif self.facing == "LEFT":
            test_rect.width += body_length
        elif self.facing == "RIGHT":
            test_rect.x -= body_length
            test_rect.width += body_length

        for wall in self.current_walls:
            if test_rect.colliderect(wall):
                if not self._wall_is_in_crawlable_zone(wall, test_rect):
                    return False
        return True
    
    def draw_with_camera(self, surface, camera):
        current_image = None
        if self.is_punching:
            current_image = self.animations["PUNCH"][self.facing]
        elif self.is_moving:
            if self.stance == "CROUCH":
                current_image = self.animations["CROUCH"][self.facing][self.frame_index]
            elif self.stance == "CRAWL":
                current_image = self.animations["CRAWL"][self.facing][self.frame_index]
            else:
                current_image = self.animations["WALK"][self.facing][self.frame_index]
        else:
            if self.stance == "CROUCH":
                current_image = self.animations["CROUCH"][self.facing][0]
            elif self.stance == "CRAWL":
                current_image = self.animations["CRAWL"][self.facing][0]
            else:
                current_image = self.animations["IDLE"][self.facing]
            
        dest_rect = camera.apply(self)
        
        draw_x = dest_rect.x - self.offset_x
        draw_y = dest_rect.y - self.offset_y
        
        surface.blit(current_image, (draw_x, draw_y))
        # pygame.draw.rect(surface, (255, 0, 0), dest_rect, 2)