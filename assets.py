import os
import math
import random
from PIL import Image, ImageDraw, ImageTk, ImageOps

class AssetLibrary:
    def __init__(self, transparent_hex="#010203", assets_dir="assets"):
        self.transparent_hex = transparent_hex
        self.assets_dir = os.path.abspath(assets_dir)
        self.anim_dir = os.path.join(self.assets_dir, "anim")
        
        # Cache for PhotoImage objects
        self.sprite_cache = {}
        
        # Animal multi-frame image storage: { animal_name: [PIL.Image, ...] }
        self.animal_frames = {
            "nyamuk": [],
            "laba_laba": [],
            "rubah": [],
            "mammoth": []
        }
        
        # Weapon images: { weapon_name: PIL.Image }
        self.weapon_raw = {}
        
        self._load_all_assets()

    def _load_all_assets(self):
        # 1. Load multi-frame animations
        counts = {
            "nyamuk": 3,
            "laba_laba": 4,
            "rubah": 4,
            "mammoth": 4
        }
        for animal, count in counts.items():
            frames = []
            for i in range(count):
                p = os.path.join(self.anim_dir, f"{animal}_{i}.png")
                if os.path.exists(p):
                    try:
                        frames.append(Image.open(p).convert("RGBA"))
                    except Exception as e:
                        print(f"Error loading {p}: {e}")
            if not frames:
                # Fallback to single clean image
                single_p = os.path.join(self.assets_dir, f"clean_{animal}.png")
                if os.path.exists(single_p):
                    frames.append(Image.open(single_p).convert("RGBA"))
                else:
                    frames.append(Image.new("RGBA", (64, 64), (200, 50, 50, 255)))
            self.animal_frames[animal] = frames

        # 2. Load weapon sprites
        weapon_files = {
            "tepokan": "clean_raket.png",
            "pistol": "clean_pistol.png",
            "tangan": "clean_tangan.png",
            "palu": "clean_palu.png",
        }
        for code, fname in weapon_files.items():
            p = os.path.join(self.assets_dir, fname)
            if os.path.exists(p):
                try:
                    self.weapon_raw[code] = Image.open(p).convert("RGBA")
                except Exception as e:
                    print(f"Error loading weapon {p}: {e}")

    def get_animal_photo(self, animal_type, frame_idx, angle_deg=0, scale_mult=1.0, facing_left=False):
        """Returns pre-cached ImageTk.PhotoImage for animal with full frame animation."""
        scale_key = round(scale_mult, 1)
        frames = self.animal_frames.get(animal_type, self.animal_frames["nyamuk"])
        f_idx = frame_idx % len(frames)
        
        # Ground animals face left or right
        if animal_type in ("rubah", "mammoth"):
            cache_key = (animal_type, f_idx, scale_key, facing_left)
            if cache_key in self.sprite_cache:
                return self.sprite_cache[cache_key]

            base_img = frames[f_idx]
            img = base_img.copy()
            # Rubah natively faces LEFT in base sprites; Mammoth natively faces RIGHT
            should_mirror = (not facing_left) if animal_type == "rubah" else facing_left
            if should_mirror:
                img = ImageOps.mirror(img)

            # Target base size for ground walk
            if animal_type == "rubah":
                base_w, base_h = 180, 85
            else: # mammoth
                base_w, base_h = 240, 150

            tw = max(32, int(base_w * scale_mult))
            th = max(24, int(base_h * scale_mult))
            scaled = img.resize((tw, th), Image.Resampling.LANCZOS)

        else:
            # Top-down flying/crawling animals (nyamuk, laba_laba): rotate to travel angle
            angle_bucket = int(round(angle_deg / 15.0) * 15) % 360
            cache_key = (animal_type, f_idx, angle_bucket, scale_key)
            if cache_key in self.sprite_cache:
                return self.sprite_cache[cache_key]

            base_img = frames[f_idx]
            rotated = base_img.rotate(-angle_bucket, resample=Image.Resampling.BICUBIC, expand=True)

            if animal_type == "nyamuk":
                base_size = 85
            else: # laba_laba
                base_size = 90

            target_size = max(30, int(base_size * scale_mult))
            scaled = rotated.resize((target_size, target_size), Image.Resampling.LANCZOS)

        # 1-bit alpha threshold for 100% borderless transparency on Windows
        r, g, b, a = scaled.split()
        a = a.point(lambda p: 0 if p < 45 else 255)
        clean_scaled = Image.merge('RGBA', (r, g, b, a))

        photo = ImageTk.PhotoImage(clean_scaled)
        self.sprite_cache[cache_key] = photo
        return photo

    def get_weapon_photo(self, weapon_type, is_attacking=False):
        """Returns held/striking weapon sprite following cursor."""
        cache_key = ("weapon", weapon_type, is_attacking)
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        raw = self.weapon_raw.get(weapon_type)
        size = 220
        
        if raw:
            img = raw.copy()
            if weapon_type == "pistol":
                # Pistol angled so barrel points UP-RIGHT towards crosshair
                scaled = img.resize((175, 95), Image.Resampling.LANCZOS)
                canvas_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
                canvas_img.paste(scaled, (15, 80), scaled)
                rot_angle = 12 if is_attacking else 24
                rotated = canvas_img.rotate(rot_angle, resample=Image.Resampling.BICUBIC)
                
                if is_attacking:
                    # Explosive forward muzzle flash at front barrel tip (on the RIGHT!)
                    draw = ImageDraw.Draw(rotated)
                    fx, fy = 195, 110
                    draw.polygon([(fx-8, fy-18), (fx+48, fy-22), (fx+18, fy+18), (fx-5, fy+8)], fill=(255, 230, 80, 255))
                    draw.polygon([(fx+5, fy-12), (fx+62, fy-28), (fx+15, fy+6)], fill=(255, 120, 20, 255))
                    draw.ellipse([fx-8, fy-10, fx+16, fy+10], fill=(255, 255, 255, 255))
                    for _ in range(8):
                        sx = fx + 20 + _ * 5
                        sy = fy - 15 - _ * 3 + random.randint(-8, 8)
                        draw.line([(fx, fy), (sx, sy)], fill=(255, 240, 150, 255), width=2)

            elif weapon_type == "tepokan":
                # Big Electric Racket centered on crosshair
                tilt = -45 if is_attacking else -12
                scaled = img.resize((110, 195), Image.Resampling.LANCZOS)
                canvas_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
                canvas_img.paste(scaled, (55, 45), scaled)
                
                if is_attacking:
                    draw = ImageDraw.Draw(canvas_img)
                    for _ in range(12):
                        sx = random.randint(55, 165)
                        sy = random.randint(45, 155)
                        draw.line([(sx, sy), (sx + random.randint(-20, 20), sy + random.randint(-20, 20))],
                                  fill=(140, 235, 255, 255), width=3)
                        draw.line([(sx, sy), (sx + random.randint(-10, 10), sy + random.randint(-10, 10))],
                                  fill=(255, 255, 255, 255), width=2)
                        
                rotated = canvas_img.rotate(tilt, resample=Image.Resampling.BICUBIC)

            elif weapon_type == "palu":
                # Giant Sledgehammer centered on crosshair
                tilt = -60 if is_attacking else -18
                scaled = img.resize((160, 160), Image.Resampling.LANCZOS)
                canvas_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
                canvas_img.paste(scaled, (30, 30), scaled)
                
                if is_attacking:
                    draw = ImageDraw.Draw(canvas_img)
                    draw.line([(35, 25), (5, 5)], fill=(255, 230, 50, 255), width=5)
                    draw.line([(35, 70), (5, 90)], fill=(255, 230, 50, 255), width=5)
                    for _ in range(6):
                        draw.line([(50, 50), (random.randint(5, 80), random.randint(5, 80))], fill=(255, 200, 30, 255), width=2)
                    
                rotated = canvas_img.rotate(tilt, resample=Image.Resampling.BICUBIC)

            else: # "tangan"
                tilt = -35 if is_attacking else 0
                scaled = img.resize((145, 175), Image.Resampling.LANCZOS)
                canvas_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
                canvas_img.paste(scaled, (37, 22), scaled)
                if is_attacking:
                    draw = ImageDraw.Draw(canvas_img)
                    for y_line in (45, 85, 125):
                        draw.line([(30, y_line), (8, y_line + 15)], fill=(255, 255, 255, 200), width=3)
                rotated = canvas_img.rotate(tilt, resample=Image.Resampling.BICUBIC)

        else:
            canvas_img = Image.new('RGBA', (size, size), (255, 0, 0, 180))
            rotated = canvas_img

        r, g, b, a = rotated.split()
        a = a.point(lambda p: 0 if p < 45 else 255)
        clean = Image.merge('RGBA', (r, g, b, a))

        photo = ImageTk.PhotoImage(clean)
        self.sprite_cache[cache_key] = photo
        return photo

    def draw_canvas_blood(self, canvas, cx, cy, scale_mult=1.0, tag='blood'):
        """Draws organic vector blood splatters directly on the canvas with ZERO background box."""
        dark_blood = '#7d0d12'
        fresh_blood = '#c9161d'
        bright_blood = '#e82e2e'
        
        num_blobs = random.randint(7, 10)
        for _ in range(num_blobs):
            bx = cx + random.uniform(-6 * scale_mult, 6 * scale_mult)
            by = cy + random.uniform(-6 * scale_mult, 6 * scale_mult)
            rw = random.uniform(6 * scale_mult, 13 * scale_mult)
            rh = random.uniform(6 * scale_mult, 13 * scale_mult)
            canvas.create_oval(bx - rw, by - rh, bx + rw, by + rh, fill=fresh_blood, outline='', tags=(tag, 'blood'))
            
        cr = 6.5 * scale_mult
        canvas.create_oval(cx - cr, cy - cr, cx + cr, cy + cr, fill=dark_blood, outline='', tags=(tag, 'blood'))
        
        num_droplets = random.randint(12, 18)
        for _ in range(num_droplets):
            ang = random.uniform(0, 2 * math.pi)
            dist = random.uniform(9 * scale_mult, 26 * scale_mult)
            dx = cx + dist * math.cos(ang)
            dy = cy + dist * math.sin(ang)
            dr = random.uniform(1.2 * scale_mult, 3.2 * scale_mult)
            canvas.create_oval(dx - dr, dy - dr, dx + dr, dy + dr, fill=bright_blood, outline='', tags=(tag, 'blood'))
            if random.random() > 0.4:
                canvas.create_line(cx, cy, dx, dy, fill=fresh_blood, width=max(1, int(1.4 * scale_mult)), tags=(tag, 'blood'))
                
        canvas.create_oval(cx - 3*scale_mult, cy - 3*scale_mult, cx + 3*scale_mult, cy + 3*scale_mult, fill='#1c1512', outline='', tags=(tag, 'blood'))
        for _ in range(4):
            ang = random.uniform(0, 2 * math.pi)
            canvas.create_line(cx, cy, cx + math.cos(ang)*7*scale_mult, cy + math.sin(ang)*7*scale_mult, fill='#1c1512', width=max(1, int(scale_mult)), tags=(tag, 'blood'))
