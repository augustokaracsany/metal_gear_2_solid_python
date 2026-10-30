import os
import pygame
from src.settings import PLAYER_SPEED, PLAYER_MAX_HEALTH, PLAYER_INVULNERABLE_TIME, PLAYER_SHOOT_COOLDOWN, PLAYER_GUN_SPRITES_PATH, PLAYER_GUN_SHOW_TIME
from src.bullet import Bullet
from src.settings import SHOOT_SOUND_PATH, SHOOT_SOUND_VOLUME
from src.settings import PUNCH_RANGE
from src.settings import PUNCH_SOUND_PATH, PUNCH_SOUND_VOLUME
from src.settings import BULLET_DAMAGE
from src import weapon_settings as WS
from src.weapons import PICKUPS

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        
        self.x = float(x)
        self.y = float(y)

        self.is_dying = False
        self.death_frame_index = 0
        self.death_timer = 0.0
        self.death_animation_speed = 0.6
        
        self.is_punching = False
        self.init_time_punch = 0
        self.punch_length = 500
        self.last_punch = 0
        self.cooldown_punch = 600
        self.punch_hit_done = False
        
        self.stance = "STAND"

        self.forced_crouch = False
        self.crouch_hold_timer = 0.0
        self.crouch_hold_duration = 1.5

        self.is_transitioning = False
        self.transition_timer = 0.0
        self.transition_duration = 0.18
        self.target_stance = None
        
        self.facing = "DOWN"
        self.is_moving = False
        self.is_hidden = False
        self.hidden_zones = []
        self.hidden_zones_top = []
        self.hidden_zones_bottom = []
        self.top_barriers = []
        self.active_hidden_top_zone = None
        self.active_hidden_bottom_marker = None

        self.max_health = PLAYER_MAX_HEALTH
        self.health = self.max_health
        self.is_dead = False
        self.last_hit_time = -PLAYER_INVULNERABLE_TIME

        self.last_shot_time = -PLAYER_SHOOT_COOLDOWN
        self.gun_until = 0

        self.weapon_manager = None
        self.weapons = ["beretta"]
        self.weapon_locked = False
        self.weapon_animations = {}

        self.shoot_sound = None
        try:
            self.shoot_sound = pygame.mixer.Sound(SHOOT_SOUND_PATH)
            self.shoot_sound.set_volume(SHOOT_SOUND_VOLUME)
        except Exception as e:
            print(f"AVISO: no se pudo cargar el sonido del disparo ({e}).")

        self.punch_sound = None
        try:
            self.punch_sound = pygame.mixer.Sound(PUNCH_SOUND_PATH)
            self.punch_sound.set_volume(PUNCH_SOUND_VOLUME)
        except Exception as e:
            print(f"AVISO: no se pudo cargar el sonido del golpe ({e}).")

        self.anim_timer = 0.0
        self.frame_index = 0
        self.animation_speed = 0.15

        self.inventory = []
        self.is_disguised = False
        self.input_locked = False

        self.load_sprites_data()

        stand_img = self.animations["IDLE"]["DOWN"]
        stand_w, stand_h = stand_img.get_size()
        col_width = int(stand_w * 0.6)
        col_height = int(stand_h * 0.3)
        self.rect = pygame.Rect(self.x, self.y, col_width, col_height)
        
        self.update_offsets_for_stance()

    def collect_items(self, items_group):
        hits = pygame.sprite.spritecollide(self, items_group, False)
        for item in hits:
            if item.name in PICKUPS:
                continue
            item.kill()
            if item.name not in self.inventory:
                self.inventory.append(item.name)
                print(f"¡Conseguido ítem: {item.name}!")

    def toggle_box_disguise(self):
        if "cardboard_box" in self.inventory:
            self.is_disguised = not self.is_disguised
            if self.is_disguised:
                self.is_transitioning = False
                self.target_stance = None
                self.forced_crouch = False
                self.set_stance("STAND")
            print("Disfraz:", "Caja equipada" if self.is_disguised else "Sin caja")

    def punch_self_event(self, event):
        if self.input_locked or self.weapon_locked:
            return
        current_time = pygame.time.get_ticks()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_b:
                if "cardboard_box" in self.inventory:
                    self.toggle_box_disguise()

            if event.key == pygame.K_e:
                if self.stance == "STAND" and not self.is_disguised:
                    if current_time - self.last_punch >= self.cooldown_punch:
                        self.is_punching = True
                        self.init_time_punch = current_time
                        self.last_punch = current_time
                        self.punch_hit_done = False
                        if self.punch_sound:
                            self.punch_sound.play()
            
            elif event.key == pygame.K_c:
                if not self.is_disguised:
                    if self.stance == "STAND":
                        self.set_stance("CROUCH")
                    elif self.stance == "CROUCH":
                        self.set_stance("STAND")
                    elif self.stance == "CRAWL":
                        self.set_stance("CROUCH")
                    
            elif event.key in (pygame.K_LCTRL, pygame.K_RCTRL):
                if not self.is_disguised:
                    if self.stance in ("STAND", "CROUCH"):
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

        try:
            raw_box = pygame.image.load("assets/sprites/solid_python/cardboard_box.png").convert_alpha()
            w = int(raw_box.get_width() * SCALE_FACTOR)
            h = int(raw_box.get_height() * SCALE_FACTOR)
            self.box_sprite = pygame.transform.scale(raw_box, (w, h))
        except Exception as e:
            print(f"Error cargando sprite de la caja: {e}")
            self.box_sprite = None

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
            },
            "DIE": [
                cs("assets/sprites/solid_python/crouch_down1.png"),
                cs("assets/sprites/solid_python/crawl_down1.png"),
                cs("assets/sprites/solid_python/crawl_down2.png")
            ]
        }

        self.gun_animations = None
        try:
            gun_animations = {}
            for direction in ("DOWN", "UP", "LEFT", "RIGHT"):
                d = direction.lower()
                stand = cs(f"{PLAYER_GUN_SPRITES_PATH}armed_stand_{d}.png")
                gun_animations[direction] = [
                    stand,
                    cs(f"{PLAYER_GUN_SPRITES_PATH}armed_walk_{d}1.png"),
                    stand,
                    cs(f"{PLAYER_GUN_SPRITES_PATH}armed_walk_{d}2.png"),
                ]
            self.gun_animations = gun_animations
        except Exception as e:
            print(f"AVISO: no se pudieron cargar los sprites con arma ({e}). Se usan los normales.")
            self.gun_animations = None

        self.weapon_animations = {}
        if self.gun_animations:
            self.weapon_animations["gun"] = self.gun_animations
        for set_name in ("m16", "stinger"):
            anims = self._load_weapon_animations(cs, set_name)
            if anims:
                self.weapon_animations[set_name] = anims
            else:
                print(f"AVISO: no se encontraron sprites de Snake para '{set_name}' en {WS.SOLID_SPRITE_DIR}.")

    def _load_weapon_animations(self, cs, keyword):
        folder = WS.SOLID_SPRITE_DIR
        try:
            names = sorted(os.listdir(folder))
        except OSError:
            return None
        keyword = keyword.lower()

        def find(kind, d, suffix=""):
            for name in names:
                low = name.lower()
                if not low.endswith(".png"):
                    continue
                stem = low[:-4]
                if keyword in stem and kind in stem and stem.endswith(d + suffix):
                    return os.path.join(folder, name)
            return None

        anims = {}
        for direction in ("DOWN", "UP", "LEFT", "RIGHT"):
            d = direction.lower()
            stand_path = find("stand", d)
            if not stand_path:
                return None
            try:
                stand = cs(stand_path)
                walk1, walk2 = find("walk", d, "1"), find("walk", d, "2")
                if walk1 and walk2:
                    anims[direction] = [stand, cs(walk1), stand, cs(walk2)]
                else:
                    anims[direction] = [stand]
            except Exception as e:
                print(f"AVISO: error cargando sprites '{keyword}' ({e}).")
                return None
        return anims

    def update_offsets_for_stance(self):
        stand_img = self.animations["IDLE"]["DOWN"]
        stand_w, stand_h = stand_img.get_size()
        col_width = int(stand_w * 0.6)
        col_height = int(stand_h * 0.3)

        if self.is_disguised and self.box_sprite:
            ref_img = self.box_sprite
        elif self.stance == "STAND":
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
        if self.input_locked or self.weapon_locked:
            return 0, 0
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

        if self.forced_crouch:
            if self.crouch_hold_timer > 0:
                self.crouch_hold_timer -= dt

        if (dx != 0 or dy != 0) and not self.is_punching:
            self.is_moving = True

            if self.stance == "CRAWL" and not was_inside_hidden_zone and self.check_upcoming_obstacle():
                self.set_stance("CROUCH")
                self.forced_crouch = True
                self.crouch_hold_timer = self.crouch_hold_duration

            if self.stance == "CROUCH" and self.forced_crouch:
                if self.crouch_hold_timer <= 0 and self.can_crawl() and self.has_space_behind():
                    self.set_stance("CRAWL")
                    self.forced_crouch = False

            vel_x = dx * current_speed * dt
            self.x += vel_x
            self.rect.x = round(self.x)
            self.check_collisions_x(walls_group, vel_x)

            vel_y = dy * current_speed * dt
            previous_rect = self.rect.copy()
            self.y += vel_y
            self.rect.y = round(self.y)
            self.check_collisions_y(walls_group, vel_y, previous_rect)
        else:
            self.is_moving = False

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

    def is_near_hidden_zone(self, margin=15):
        if self.stance != "CRAWL":
            return False
        test_rect = self.rect.copy()
        test_rect.inflate_ip(margin, margin)
        return self._is_inside_hidden_zone(test_rect)

    def start_death_animation(self):
        self.is_dying = True
        self.death_frame_index = 0
        self.death_timer = 0.0

    def update_death(self, dt):
        if not self.is_dying:
            return
        self.death_timer += dt
        if self.death_timer >= self.death_animation_speed:
            self.death_timer = 0.0
            if self.death_frame_index < len(self.animations["DIE"]) - 1:
                self.death_frame_index += 1

    def _weapon_pose_frames(self):
        """Frames de Snake con el arma equipada, o None si hay que usar los sprites normales."""
        if self.stance != "STAND" or self.is_transitioning:
            return None
        manager = self.weapon_manager
        if manager is None:
            if self.is_aiming() and self.gun_animations:
                return self.gun_animations[self.facing]
            return None
        set_name = manager.current.sprite_set
        anims = self.weapon_animations.get(set_name)
        if not anims:
            return None
        if set_name == "gun" and not self.is_aiming():
            return None
        return anims[self.facing]

    def draw_with_camera(self, surface, camera):
        current_image = None
        gun_pose = False

        if self.is_dying:
            current_image = self.animations["DIE"][self.death_frame_index]
        else:
            pose_frames = self._weapon_pose_frames()
            if self.is_disguised and self.box_sprite:
                current_image = self.box_sprite
            elif self.is_punching:
                current_image = self.animations["PUNCH"][self.facing]
            elif pose_frames is not None:
                # fire_fx sobreescribe esto más abajo si está disparando
                current_image = pose_frames[self.frame_index % len(pose_frames)] if self.is_moving else pose_frames[0]
                gun_pose = True
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

        # Sprite de disparo del M16: sobreescribe el sprite normal mientras está disparando.
        # Pasa is_moving y frame_index para que el ciclo de pasos esté sincronizado.
        fire_fx = getattr(self, "fire_fx", None)
        if fire_fx and self.weapon_manager and not self.is_dying:
            fire_img = fire_fx.get_fire_image(
                self.weapon_manager.current_id,
                self.facing,
                is_moving=self.is_moving,
                frame_index=self.frame_index,
            )
            if fire_img:
                current_image = fire_img
                gun_pose = True   # usa el mismo centrado que los sprites con arma

        dest_rect = camera.apply(self)
        draw_x = dest_rect.x - self.offset_x
        draw_y = dest_rect.y - self.offset_y

        if gun_pose:
            draw_x = dest_rect.centerx - current_image.get_width() // 2
            draw_y = dest_rect.bottom - current_image.get_height()

        # Parpadeo mientras es invulnerable
        if self.is_invulnerable() and not self.is_dead and (pygame.time.get_ticks() // 100) % 2 == 0:
            return

        surface.blit(current_image, (draw_x, draw_y))
        # pygame.draw.rect(surface, (255, 0, 0), dest_rect, 2)  # debug hitbox

    def is_aiming(self):
        return pygame.time.get_ticks() < self.gun_until

    def get_punch_rect(self):
        r = self.rect
        if self.facing == "UP":
            return pygame.Rect(r.x, r.top - PUNCH_RANGE, r.width, PUNCH_RANGE)
        elif self.facing == "DOWN":
            return pygame.Rect(r.x, r.bottom, r.width, PUNCH_RANGE)
        elif self.facing == "LEFT":
            return pygame.Rect(r.left - PUNCH_RANGE, r.y, PUNCH_RANGE, r.height)
        else:
            return pygame.Rect(r.right, r.y, PUNCH_RANGE, r.height)

    def can_use_weapon(self):
        if self.is_dying or self.is_dead or self.input_locked:
            return False
        if self.stance != "STAND" or self.is_transitioning:
            return False
        if self.is_punching or self.is_disguised:
            return False
        return True

    def fire_bullet(self, damage_mult=1.0, muzzle=None):
        self.last_shot_time = pygame.time.get_ticks()
        self.gun_until = self.last_shot_time + PLAYER_GUN_SHOW_TIME
        return Bullet(self.rect, self.facing, damage=BULLET_DAMAGE * damage_mult, muzzle=muzzle)
    
    def can_shoot(self):
        if not self.can_use_weapon():
            return False
        return pygame.time.get_ticks() - self.last_shot_time >= PLAYER_SHOOT_COOLDOWN

    def shoot(self):
        if not self.can_shoot():
            return None
        self.last_shot_time = pygame.time.get_ticks()
        self.gun_until = self.last_shot_time + PLAYER_GUN_SHOW_TIME
        if self.shoot_sound:
            self.shoot_sound.play()
        return Bullet(self.rect, self.facing)

    def is_invulnerable(self):
        return pygame.time.get_ticks() - self.last_hit_time < PLAYER_INVULNERABLE_TIME

    def take_damage(self, amount):
        if self.is_dead or self.is_invulnerable():
            return
        self.health = max(0, self.health - amount)
        self.last_hit_time = pygame.time.get_ticks()
        if self.health == 0:
            self.is_dead = True

    def heal(self, amount):
        if self.is_dead:
            return
        self.health = min(self.max_health, self.health + amount)