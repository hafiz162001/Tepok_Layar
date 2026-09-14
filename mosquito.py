import math
import random
import time

SCALE_LEVELS = [1.0, 1.6, 2.3, 3.2, 4.5]

LEVEL_TITLES = [
    "Normal (Level 1)",
    "Makin Gede! (Level 2 - 1.6x)",
    "Gendut Raksasa! (Level 3 - 2.3x)",
    "MONSTER TITAN! (Level 4 - 3.2x)",
    "DEWA RAKSASA MAX! (Level 5 - 4.5x)"
]

class Creature:
    def __init__(self, screen_w, screen_h, animal_type="nyamuk"):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.animal_type = animal_type
        
        # Mode: 'boss' (makin gede) or 'classic' (1x tepok mati)
        self.game_mode = 'boss'
        
        # Level: 1 to 5
        self.level = 1
        self.scale_mult = SCALE_LEVELS[0]
        
        # Motion & position
        self.x = screen_w / 2
        self.y = screen_h / 2
        self.vx = 0.0
        self.vy = 0.0
        self.angle = 0.0
        self.facing_left = False
        
        # Animation
        self.anim_frame = 0
        self.anim_tick = 0
        
        # Speed & stats
        self.speed_multiplier = 1.0
        self._init_animal_behavior()
        
        # Hitbox & state
        self.canvas_item = None
        self.is_alive = True
        self.flinch_timer = 0.0
        self.state = 'WALK' if self.is_ground else 'FLYING'
        self.state_timer = random.uniform(3.0, 6.0)

    def _get_ground_y(self):
        # Ground height so feet stay firmly on bottom of screen (above taskbar)
        ground_bottom = self.screen_h - 22
        if self.animal_type == "rubah":
            half_h = (85 / 2.0) * self.scale_mult
        else: # mammoth
            half_h = (150 / 2.0) * self.scale_mult
        return ground_bottom - half_h

    def _init_animal_behavior(self):
        self.is_ground = self.animal_type in ("rubah", "mammoth")
        
        if self.animal_type == "rubah":
            self.base_speed = 5.2
            self.facing_left = random.choice([True, False])
            self.vx = -self.base_speed if self.facing_left else self.base_speed
            self.y = self._get_ground_y()
            self.x = random.uniform(100, self.screen_w - 100)
            self.state = 'WALK'

        elif self.animal_type == "mammoth":
            self.base_speed = 2.4
            self.facing_left = random.choice([True, False])
            self.vx = -self.base_speed if self.facing_left else self.base_speed
            self.y = self._get_ground_y()
            self.x = random.uniform(150, self.screen_w - 150)
            self.state = 'WALK'

        elif self.animal_type == "laba_laba":
            self.base_speed = 3.6
            self.is_ground = False
            self.target_x = random.uniform(100, self.screen_w - 100)
            self.target_y = random.uniform(100, self.screen_h - 100)
            self.state = 'CRAWLING'

        else: # nyamuk
            self.base_speed = 4.8
            self.is_ground = False
            self.target_x = random.uniform(100, self.screen_w - 100)
            self.target_y = random.uniform(100, self.screen_h - 100)
            self.state = 'FLYING'

    def set_animal(self, new_type):
        self.animal_type = new_type
        self._init_animal_behavior()

    def set_speed_multiplier(self, mult):
        self.speed_multiplier = mult

    def hit(self):
        """Called when struck. Returns (new_level, exploded)."""
        if self.game_mode == 'classic':
            self.reset_size()
            self._teleport_fresh()
            return 1, True

        if self.level < len(SCALE_LEVELS):
            self.level += 1
            self.scale_mult = SCALE_LEVELS[self.level - 1]
            self.flinch_timer = 0.4
            
            if self.is_ground:
                # Adjust ground height for new scale
                self.y = self._get_ground_y()
                # Panic run away!
                self.facing_left = not self.facing_left
                self.state = 'RUN'
                self.state_timer = 2.5
                speed = self.base_speed * 1.8 * self.speed_multiplier
                self.vx = -speed if self.facing_left else speed
            else:
                self.state = 'FLINCH'
                self.target_x = random.uniform(100, self.screen_w - 100)
                self.target_y = random.uniform(100, self.screen_h - 100)
                
            return self.level, False
        else:
            # Reached max level -> K.O. Explosion!
            self.reset_size()
            self._teleport_fresh()
            return len(SCALE_LEVELS), True

    def reset_size(self):
        self.level = 1
        self.scale_mult = SCALE_LEVELS[0]
        if self.is_ground:
            self.y = self._get_ground_y()

    def _teleport_fresh(self):
        self.reset_size()
        if self.is_ground:
            self.x = random.uniform(150, self.screen_w - 150)
            self.y = self._get_ground_y()
            self.facing_left = random.choice([True, False])
            self.state = 'WALK'
            self.state_timer = random.uniform(3.0, 7.0)
        else:
            self.x = random.uniform(150, self.screen_w - 150)
            self.y = random.uniform(150, self.screen_h - 150)
            self.target_x = random.uniform(100, self.screen_w - 100)
            self.target_y = random.uniform(100, self.screen_h - 100)
            self.state = 'FLYING'
            self.state_timer = random.uniform(3.0, 6.0)

    def update(self, dt, sound_mgr=None):
        if not self.is_alive:
            return

        self.anim_tick += 1
        current_speed = self.base_speed * self.speed_multiplier

        # ==========================================
        # 1. GROUND ANIMALS (RUBAH & MAMMOTH)
        # ==========================================
        if self.is_ground:
            # Keep feet firmly on ground regardless of scale
            target_ground_y = self._get_ground_y()
            self.y = target_ground_y

            self.state_timer -= dt
            if self.state_timer <= 0:
                self._switch_ground_state()

            margin = int(80 * self.scale_mult)

            if self.state in ('WALK', 'RUN'):
                # Walking/running leg animation
                speed_factor = 2 if self.state == 'RUN' else 1
                anim_interval = 4 if self.state == 'RUN' else 6
                if self.anim_tick % anim_interval == 0:
                    self.anim_frame = (self.anim_frame + 1) % 4

                actual_speed = current_speed * (1.8 if self.state == 'RUN' else 1.0)
                self.vx = -actual_speed if self.facing_left else actual_speed
                self.x += self.vx

                # Screen wrap-around (nembus tepi layar: kiri tembus ke kanan, kanan ke kiri)
                wrap_margin = int(120 * self.scale_mult)
                if self.x < -wrap_margin:
                    self.x = self.screen_w + wrap_margin
                elif self.x > self.screen_w + wrap_margin:
                    self.x = -wrap_margin

            elif self.state == 'IDLE':
                # Resting standing frame
                self.anim_frame = 0
                self.vx = 0

            elif self.state == 'POUNCE':
                # Playful jump
                progress = 1.0 - (self.state_timer / 0.8)
                jump_height = 45 * self.scale_mult * math.sin(progress * math.pi)
                self.y = target_ground_y - jump_height
                self.anim_frame = 3
                self.x += (-current_speed if self.facing_left else current_speed) * 0.5
                wrap_margin = int(120 * self.scale_mult)
                if self.x < -wrap_margin:
                    self.x = self.screen_w + wrap_margin
                elif self.x > self.screen_w + wrap_margin:
                    self.x = -wrap_margin
                if self.state_timer <= 0:
                    self.state = 'WALK'
                    self.state_timer = random.uniform(3.0, 6.0)

        # ==========================================
        # 2. AERIAL & CRAWLING (NYAMUK & LABA-LABA)
        # ==========================================
        else:
            self.state_timer -= dt
            if self.state_timer <= 0 and self.state != 'FLINCH':
                self._switch_aerial_state()
                if sound_mgr and self.animal_type == 'nyamuk':
                    if self.state == 'LANDED':
                        sound_mgr.pause_buzz()
                    else:
                        sound_mgr.resume_buzz()

            if self.animal_type == "nyamuk":
                # 3-frame rapid wing beating
                if self.state in ('FLYING', 'HOVERING', 'FLINCH'):
                    if self.anim_tick % 2 == 0:
                        self.anim_frame = (self.anim_frame + 1) % 3
                else:
                    self.anim_frame = 1 # Folded wings when landed

                if self.state in ('FLYING', 'FLINCH'):
                    dx = self.target_x - self.x
                    dy = self.target_y - self.y
                    dist = math.hypot(dx, dy)
                    if dist < 45:
                        self.target_x = random.uniform(-60, self.screen_w + 60)
                        self.target_y = random.uniform(-40, self.screen_h + 40)
                    else:
                        target_ang = math.degrees(math.atan2(dx, -dy))
                        diff = (target_ang - self.angle + 180) % 360 - 180
                        self.angle += diff * 0.08

                    self.angle += math.sin(time.time() * 9) * 4.0
                    rad = math.radians(self.angle)
                    speed = current_speed * (1.6 if self.state == 'FLINCH' else 1.0)
                    self.vx = math.sin(rad) * speed
                    self.vy = -math.cos(rad) * speed
                    self.x += self.vx
                    self.y += self.vy

                elif self.state == 'HOVERING':
                    hover_drift = current_speed * 0.3
                    self.x += random.uniform(-hover_drift, hover_drift)
                    self.y += random.uniform(-hover_drift, hover_drift)
                    self.angle += math.sin(time.time() * 6) * 5.0

            elif self.animal_type == "laba_laba":
                # 4-frame crawl animation
                if self.anim_tick % 5 == 0:
                    self.anim_frame = (self.anim_frame + 1) % 4

                dx = self.target_x - self.x
                dy = self.target_y - self.y
                dist = math.hypot(dx, dy)
                if dist < 40:
                    self.target_x = random.uniform(-50, self.screen_w + 50)
                    self.target_y = random.uniform(-40, self.screen_h + 40)
                else:
                    target_ang = math.degrees(math.atan2(dx, -dy))
                    diff = (target_ang - self.angle + 180) % 360 - 180
                    self.angle += diff * 0.06

                rad = math.radians(self.angle)
                self.vx = math.sin(rad) * current_speed
                self.vy = -math.cos(rad) * current_speed
                self.x += self.vx
                self.y += self.vy

            # Boundaries: Screen wrap-around (nembus layar: kiri tembus ke kanan, kanan ke kiri, atas ke bawah, bawah ke atas)
            wrap_x = int(70 * self.scale_mult)
            wrap_y = int(70 * self.scale_mult)

            if self.x < -wrap_x:
                self.x = self.screen_w + wrap_x
            elif self.x > self.screen_w + wrap_x:
                self.x = -wrap_x

            if self.y < -wrap_y:
                self.y = self.screen_h + wrap_y
            elif self.y > self.screen_h + wrap_y:
                self.y = -wrap_y

    def _switch_ground_state(self):
        roll = random.random()
        if self.state in ('WALK', 'RUN'):
            if roll < 0.35:
                self.state = 'IDLE'
                self.state_timer = random.uniform(1.5, 3.5)
            elif roll < 0.55 and self.animal_type == 'rubah':
                self.state = 'POUNCE'
                self.state_timer = 0.8
            else:
                # Keep walking, maybe switch direction
                if random.random() < 0.4:
                    self.facing_left = not self.facing_left
                self.state = 'WALK'
                self.state_timer = random.uniform(3.0, 7.0)
        else: # From IDLE
            if random.random() < 0.5:
                self.facing_left = not self.facing_left
            self.state = 'WALK'
            self.state_timer = random.uniform(3.0, 8.0)

    def _switch_aerial_state(self):
        roll = random.random()
        if self.state == 'FLYING':
            if roll < 0.35:
                self.state = 'HOVERING'
                self.state_timer = random.uniform(1.2, 2.5)
            elif roll < 0.65 and self.animal_type == 'nyamuk':
                self.state = 'LANDED'
                self.state_timer = random.uniform(2.5, 5.0)
            else:
                self.target_x = random.uniform(-60, self.screen_w + 60)
                self.target_y = random.uniform(-40, self.screen_h + 40)
                self.state_timer = random.uniform(3.0, 7.0)
        else:
            self.state = 'FLYING'
            self.target_x = random.uniform(-60, self.screen_w + 60)
            self.target_y = random.uniform(-40, self.screen_h + 40)
            self.state_timer = random.uniform(3.0, 7.0)

    def check_hit(self, click_x, click_y):
        if not self.is_alive:
            return False
        
        if self.animal_type == "rubah":
            hw = (180 / 2.0) * self.scale_mult
            hh = (85 / 2.0) * self.scale_mult
        elif self.animal_type == "mammoth":
            hw = (240 / 2.0) * self.scale_mult
            hh = (150 / 2.0) * self.scale_mult
        elif self.animal_type == "nyamuk":
            hw = (85 / 2.0) * self.scale_mult
            hh = (85 / 2.0) * self.scale_mult
        else: # laba_laba
            hw = (90 / 2.0) * self.scale_mult
            hh = (90 / 2.0) * self.scale_mult

        # Generous padding so clicking anywhere on or near the animal is a guaranteed hit
        pad_x = max(35.0, hw * 0.35)
        pad_y = max(35.0, hh * 0.35)

        return (self.x - hw - pad_x <= click_x <= self.x + hw + pad_x) and \
               (self.y - hh - pad_y <= click_y <= self.y + hh + pad_y)

Mosquito = Creature
