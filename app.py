import tkinter as tk
import math
import random
import time

import ctypes

from assets import AssetLibrary
from sound_manager import SoundManager
from mosquito import Creature, SCALE_LEVELS, LEVEL_TITLES

user32 = ctypes.windll.user32
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

TRANSPARENT_COLOR = "#010203"

ANIMALS = [
    ("nyamuk", "🦟 Nyamuk"),
    ("laba_laba", "🕷️ Laba-laba"),
    ("rubah", "🦊 Rubah"),
    ("mammoth", "🦣 Mammoth")
]

WEAPONS = [
    ("tepokan", "🏸 Raket Listrik"),
    ("pistol", "🔫 Pistol"),
    ("palu", "🔨 Palu"),
    ("tangan", "🖐️ Tangan")
]

class MosquitoApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Nyamuk & Hewan Layar")

        # Screen dimensions
        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()

        # Configure transparent fullscreen overlay
        self.root.geometry(f"{self.screen_w}x{self.screen_h}+0+0")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", TRANSPARENT_COLOR)
        self.root.config(bg=TRANSPARENT_COLOR)

        # Allow background applications to be 100% clickable through the transparent overlay
        self.root.update_idletasks()
        try:
            hwnd = user32.GetParent(self.root.winfo_id())
            GWL_EXSTYLE = -20
            WS_EX_TRANSPARENT = 0x00000020
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_TRANSPARENT)
        except Exception as e:
            print("Notice: could not set WS_EX_TRANSPARENT:", e)

        # Main transparent canvas
        self.canvas = tk.Canvas(
            self.root,
            width=self.screen_w,
            height=self.screen_h,
            bg=TRANSPARENT_COLOR,
            highlightthickness=0,
            cursor="none"
        )
        self.canvas.pack(fill="both", expand=True)
        self.root.config(cursor="none")

        # Assets and Sounds
        self.assets = AssetLibrary(transparent_hex=TRANSPARENT_COLOR)
        self.sound = SoundManager()

        # Game mode: 'boss' (makin gede) or 'classic' (1x tepok)
        self.game_mode = 'boss'

        # Multi-creature storage (supports multiple animals simultaneously!)
        self.creatures = []

        # Current weapon (Tepokan, Pistol, Palu, Tangan)
        self.current_weapon_idx = 0
        self.current_weapon = WEAPONS[self.current_weapon_idx][0]

        # Start sound manager
        self.sound.start_buzz()

        # Persistent Weapon Cursor Sprite following mouse
        self.cursor_x = self.screen_w // 2
        self.cursor_y = self.screen_h // 2
        self.is_weapon_attacking = False
        self._last_lbutton_state = False
        self._last_attack_time = 0.0
        self._last_keys_down = set()

        w_photo = self.assets.get_weapon_photo(self.current_weapon, is_attacking=False)
        self.weapon_cursor_item = self.canvas.create_image(
            self.cursor_x, self.cursor_y,
            image=w_photo,
            tags="cursor_weapon"
        )

        # Precision Gaming Crosshair Reticle (Dead Center)
        self.crosshair_circle = self.canvas.create_oval(
            self.cursor_x - 16, self.cursor_y - 16,
            self.cursor_x + 16, self.cursor_y + 16,
            outline="#ff2222", width=2,
            tags="cursor_weapon"
        )
        self.crosshair_dot = self.canvas.create_oval(
            self.cursor_x - 3, self.cursor_y - 3,
            self.cursor_x + 3, self.cursor_y + 3,
            fill="#ff2222", outline="#ffffff", width=1,
            tags="cursor_weapon"
        )
        self.crosshair_top = self.canvas.create_line(self.cursor_x, self.cursor_y - 24, self.cursor_x, self.cursor_y - 8, fill="#ff2222", width=2, tags="cursor_weapon")
        self.crosshair_bottom = self.canvas.create_line(self.cursor_x, self.cursor_y + 8, self.cursor_x, self.cursor_y + 24, fill="#ff2222", width=2, tags="cursor_weapon")
        self.crosshair_left = self.canvas.create_line(self.cursor_x - 24, self.cursor_y, self.cursor_x - 8, self.cursor_y, fill="#ff2222", width=2, tags="cursor_weapon")
        self.crosshair_right = self.canvas.create_line(self.cursor_x + 8, self.cursor_y, self.cursor_x + 24, self.cursor_y, fill="#ff2222", width=2, tags="cursor_weapon")

        # Statistics
        self.score = 0
        self.slap_count = 0

        # Speed settings
        self.speed_levels = [("Santai", 0.7), ("Normal", 1.0), ("Cepat", 1.5)]
        self.current_speed_idx = 1

        # Blood splats & floating text popups
        self.blood_splats = []
        self.popups = []

        # Floating HUD Window
        self.hud_minimized = False
        self._create_hud()

        # Spawn initial creature
        self.add_creature("nyamuk", initial=True)

        # Event Bindings: Motion & Attack
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.tag_bind("cursor_weapon", "<Motion>", self.on_mouse_move)

        self.canvas.bind("<Button-1>", self.on_click_attack)
        self.canvas.tag_bind("cursor_weapon", "<Button-1>", self.on_click_attack)

        for target in (self.root, self.hud):
            target.bind("<Escape>", lambda e: self.quit())
            target.bind("q", lambda e: self.quit())
            target.bind("Q", lambda e: self.quit())
            target.bind("<space>", lambda e: self.clear_blood_splats())
            target.bind("r", lambda e: self.reset_creature_size())
            target.bind("R", lambda e: self.reset_creature_size())
            target.bind("m", lambda e: self.toggle_hud_minimize())
            target.bind("M", lambda e: self.toggle_hud_minimize())
            target.bind("<Tab>", lambda e: self.cycle_weapon())
            target.bind("w", lambda e: self.cycle_weapon())
            target.bind("W", lambda e: self.cycle_weapon())
            target.bind("c", lambda e: self.remove_creature())
            target.bind("C", lambda e: self.remove_creature())
            target.bind("<BackSpace>", lambda e: self.remove_creature())
            target.bind("<Delete>", lambda e: self.remove_creature())
            for idx in range(len(ANIMALS)):
                key = str(idx + 1)
                target.bind(key, lambda e, i=idx: self.add_creature(i))

        # Main update loop
        self.is_running = True
        self.last_frame_time = time.time()
        self._game_loop()

    def _create_hud(self):
        self.hud = tk.Toplevel(self.root)
        self.hud.overrideredirect(True)
        self.hud.attributes("-topmost", True)

        hud_w = 590
        hud_h = 148
        hud_x = self.screen_w - hud_w - 30
        hud_y = 25
        self.hud.geometry(f"{hud_w}x{hud_h}+{hud_x}+{hud_y}")
        self.hud.configure(bg="#141720", highlightthickness=1, highlightbackground="#363c4e", cursor="arrow")

        # Draggable HUD logic
        self._hud_drag_data = {"x": 0, "y": 0}
        self.hud.bind("<Button-1>", self._start_hud_drag)
        self.hud.bind("<B1-Motion>", self._do_hud_drag)

        # Row 1: Stats & Close
        row1 = tk.Frame(self.hud, bg="#141720")
        row1.pack(fill="x", padx=10, pady=(6, 2))
        row1.bind("<Button-1>", self._on_hud_clicked)
        row1.bind("<B1-Motion>", self._do_hud_drag)

        btn_close = tk.Label(
            row1,
            text=" ✕ ",
            font=("Segoe UI", 9, "bold"),
            fg="#f87171",
            bg="#212533",
            cursor="hand2",
            padx=4, pady=1
        )
        btn_close.pack(side="right", padx=(5, 0))
        btn_close.bind("<Button-1>", lambda e: self.quit())

        self.btn_min = tk.Label(
            row1,
            text=" 🗕 ",
            font=("Segoe UI", 9, "bold"),
            fg="#94a3b8",
            bg="#212533",
            cursor="hand2",
            padx=6, pady=1
        )
        self.btn_min.pack(side="right", padx=(3, 0))
        self.btn_min.bind("<Button-1>", lambda e: self.toggle_hud_minimize())

        self.lbl_stats = tk.Label(
            row1,
            text="",
            font=("Segoe UI", 9, "bold"),
            fg="#4ade80",
            bg="#141720",
            anchor="w"
        )
        self.lbl_stats.pack(side="left", fill="x", expand=True)
        self.lbl_stats.bind("<Button-1>", self._on_hud_clicked)
        self.lbl_stats.bind("<B1-Motion>", self._do_hud_drag)

        # Row 2: Animal Addition Buttons (Click to ADD animal!)
        row2 = tk.Frame(self.hud, bg="#141720")
        row2.pack(fill="x", padx=10, pady=(3, 2))

        lbl_pilih_h = tk.Label(row2, text="➕ Tambah:", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#141720")
        lbl_pilih_h.pack(side="left", padx=(0, 6))

        for idx, (code, label) in enumerate(ANIMALS):
            btn = tk.Label(
                row2,
                text=f"+ {label}",
                font=("Segoe UI", 8, "bold"),
                fg="#f1f5f9",
                bg="#1e293b",
                cursor="hand2",
                padx=6,
                pady=2,
                relief="groove",
                bd=1
            )
            btn.bind("<Button-1>", lambda e, i=idx: self.add_creature(i))
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#2563eb", fg="#ffffff"))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg="#1e293b", fg="#f1f5f9"))
            btn.pack(side="left", padx=2)

        # Quick remove button
        btn_sub = tk.Label(
            row2,
            text="🗑️ -1",
            font=("Segoe UI", 8, "bold"),
            fg="#f87171",
            bg="#2a1b1b",
            cursor="hand2",
            padx=6,
            pady=2,
            relief="groove",
            bd=1
        )
        btn_sub.bind("<Button-1>", lambda e: self.remove_creature())
        btn_sub.bind("<Enter>", lambda e, b=btn_sub: b.config(bg="#dc2626", fg="#ffffff"))
        btn_sub.bind("<Leave>", lambda e, b=btn_sub: b.config(bg="#2a1b1b", fg="#f87171"))
        btn_sub.pack(side="left", padx=(4, 2))

        # Row 3: Weapon Selector Buttons
        row3 = tk.Frame(self.hud, bg="#141720")
        row3.pack(fill="x", padx=10, pady=(3, 2))

        lbl_pilih_w = tk.Label(row3, text="Senjata:", font=("Segoe UI", 8, "bold"), fg="#f59e0b", bg="#141720")
        lbl_pilih_w.pack(side="left", padx=(0, 4))

        self.weapon_btns = []
        for idx, (code, label) in enumerate(WEAPONS):
            btn = tk.Label(
                row3,
                text=label,
                font=("Segoe UI", 8, "bold" if idx == 0 else "normal"),
                fg="#ffffff" if idx == 0 else "#94a3b8",
                bg="#f59e0b" if idx == 0 else "#1e2230",
                cursor="hand2",
                padx=6,
                pady=2,
                relief="groove",
                bd=1
            )
            btn.bind("<Button-1>", lambda e, i=idx: self.switch_weapon(i))
            btn.pack(side="left", padx=2)
            self.weapon_btns.append(btn)

        # Row 4: Mode, Speed, Sound, Clear
        row4 = tk.Frame(self.hud, bg="#141720")
        row4.pack(fill="x", padx=10, pady=(4, 6))

        self.btn_mode = self._make_hud_btn(row4, "👑 Mode: Boss (Makin Gede)", self.toggle_game_mode)
        self.btn_mode.pack(side="left", padx=2)

        self.btn_speed = self._make_hud_btn(row4, "⚡ Normal", self.cycle_speed)
        self.btn_speed.pack(side="left", padx=2)

        self.btn_buzz = self._make_hud_btn(row4, "🔊 Suara", self.toggle_buzz)
        self.btn_buzz.pack(side="left", padx=2)

        btn_clear = self._make_hud_btn(row4, "🧹 Darah", self.clear_blood_splats)
        btn_clear.pack(side="left", padx=2)

        btn_reset_all = self._make_hud_btn(row4, "🔄 Reset (1)", self.reset_all_creatures)
        btn_reset_all.pack(side="left", padx=2)

        self._update_stats_label()

    def _make_hud_btn(self, parent, text, command):
        btn = tk.Label(
            parent,
            text=text,
            font=("Segoe UI", 8),
            fg="#cbd5e1",
            bg="#212636",
            cursor="hand2",
            padx=7,
            pady=2,
            relief="groove",
            bd=1
        )
        btn.bind("<Button-1>", lambda e: command())
        btn.bind("<Enter>", lambda e: btn.config(bg="#333a50"))
        btn.bind("<Leave>", lambda e: btn.config(bg="#212636"))
        return btn

    def _on_hud_clicked(self, event):
        if self.hud_minimized:
            self.toggle_hud_minimize()
        else:
            self._start_hud_drag(event)

    def _start_hud_drag(self, event):
        self._hud_drag_data["x"] = event.x
        self._hud_drag_data["y"] = event.y

    def _do_hud_drag(self, event):
        x = self.hud.winfo_x() + (event.x - self._hud_drag_data["x"])
        y = self.hud.winfo_y() + (event.y - self._hud_drag_data["y"])
        self.hud.geometry(f"+{x}+{y}")

    def toggle_hud_minimize(self):
        self.hud_minimized = not self.hud_minimized
        if self.hud_minimized:
            self.hud.geometry("450x38")
            if hasattr(self, 'btn_min') and self.btn_min:
                self.btn_min.config(text=" 🗖 BUKA ", fg="#38bdf8", bg="#1e293b")
        else:
            self.hud.geometry("590x148")
            if hasattr(self, 'btn_min') and self.btn_min:
                self.btn_min.config(text=" 🗕 ", fg="#94a3b8", bg="#212533")
        self._update_stats_label()

    def _update_stats_label(self):
        if not hasattr(self, 'lbl_stats') or not self.lbl_stats:
            return
        total_creatures = len(self.creatures)
        weapon_name = WEAPONS[self.current_weapon_idx][1]
        weapon_icon = weapon_name.split()[0]
        mode_str = "Boss" if self.game_mode == 'boss' else "1x Tepok"

        # Count per animal type
        counts = {}
        icons = {"nyamuk": "🦟", "laba_laba": "🕷️", "rubah": "🦊", "mammoth": "🦣"}
        for c in self.creatures:
            counts[c.animal_type] = counts.get(c.animal_type, 0) + 1

        summary_parts = []
        for code, label in ANIMALS:
            if code in counts:
                ic = icons.get(code, "🐾")
                summary_parts.append(f"{ic}x{counts[code]}")
        summary_str = " ".join(summary_parts) if summary_parts else "0"

        if self.hud_minimized:
            self.lbl_stats.config(
                text=f"🐾 {total_creatures} Hewan ({summary_str}) | {weapon_icon} | 🩸 {self.slap_count}"
            )
            return

        self.lbl_stats.config(
            text=f"🐾 {total_creatures} Hewan ({summary_str}) | {weapon_name} | Mode: {mode_str} | 🩸 {self.slap_count}"
        )

    def toggle_game_mode(self):
        if self.game_mode == 'boss':
            self.game_mode = 'classic'
            self.btn_mode.config(text="🎯 Mode: 1x Tepok Mati")
            self._create_popup(self.screen_w // 2, 80, "Mode: 1x Tepok Langsung Mati!", "#38bdf8", duration=1.2)
        else:
            self.game_mode = 'boss'
            self.btn_mode.config(text="👑 Mode: Boss (Makin Gede)")
            self._create_popup(self.screen_w // 2, 80, "Mode: Boss (Makin Ditepok Makin Gede!)", "#f59e0b", duration=1.2)
        for c in self.creatures:
            c.game_mode = self.game_mode
            c.reset_size()
        self._update_stats_label()

    def add_creature(self, animal_idx_or_type, initial=False):
        if len(self.creatures) >= 30:
            self._create_popup(self.screen_w // 2, 80, "⚠️ Maksimal 30 hewan di layar!", "#ef4444", duration=1.5)
            return

        if isinstance(animal_idx_or_type, int):
            if 0 <= animal_idx_or_type < len(ANIMALS):
                animal_type = ANIMALS[animal_idx_or_type][0]
                animal_label = ANIMALS[animal_idx_or_type][1]
            else:
                return
        else:
            animal_type = animal_idx_or_type
            animal_label = next((label for code, label in ANIMALS if code == animal_type), animal_type)

        creature = Creature(self.screen_w, self.screen_h, animal_type=animal_type)
        creature.game_mode = self.game_mode
        creature.set_speed_multiplier(self.speed_levels[self.current_speed_idx][1])

        # Randomize initial positions so new animals don't overlap completely
        if creature.is_ground:
            creature.x = random.uniform(120, self.screen_w - 120)
            creature.facing_left = random.choice([True, False])
        else:
            creature.x = random.uniform(100, self.screen_w - 100)
            creature.y = random.uniform(100, self.screen_h - 220)

        photo = self.assets.get_animal_photo(
            creature.animal_type,
            creature.anim_frame,
            creature.angle,
            creature.scale_mult,
            facing_left=creature.facing_left
        )
        creature.canvas_item = self.canvas.create_image(creature.x, creature.y, image=photo)
        self.canvas.tag_bind(creature.canvas_item, "<Motion>", self.on_mouse_move)
        self.canvas.tag_bind(creature.canvas_item, "<Button-1>", self.on_click_attack)

        self.creatures.append(creature)

        # Synchronize multi-animal audio across all creatures
        self.sound.sync_creatures(self.creatures)

        if not initial:
            self._create_popup(
                creature.x,
                max(60, min(creature.y - 25, self.screen_h - 130)),
                f"+1 {animal_label} Ditambahkan!\n(Total: {len(self.creatures)} Hewan)",
                "#4ade80",
                duration=1.2,
                font_size=12
            )

        self._update_stats_label()

    def remove_creature(self):
        if not self.creatures:
            return
        removed = self.creatures.pop()
        self.canvas.delete(removed.canvas_item)
        self.sound.sync_creatures(self.creatures)
        label = next((lbl for code, lbl in ANIMALS if code == removed.animal_type), removed.animal_type)
        self._create_popup(
            self.screen_w // 2, 80,
            f"🗑️ -1 {label} Dihapus (Sisa: {len(self.creatures)} Hewan)",
            "#f87171",
            duration=1.0,
            font_size=11
        )
        self._update_stats_label()

    def reset_all_creatures(self):
        for c in self.creatures:
            self.canvas.delete(c.canvas_item)
        self.creatures.clear()
        self.add_creature("nyamuk", initial=True)
        self._create_popup(self.screen_w // 2, 80, "🔄 Reset ke 1 Nyamuk", "#38bdf8", duration=1.0)
        self._update_stats_label()

    def on_mouse_move(self, event):
        self.cursor_x = event.x
        self.cursor_y = event.y
        self._update_weapon_cursor_pos()

    def _update_weapon_cursor_pos(self):
        if not hasattr(self, 'weapon_cursor_item') or not self.weapon_cursor_item:
            return

        cx, cy = self.cursor_x, self.cursor_y

        # If hovering over HUD, hide custom cursor items and ensure HUD is on top
        if self._is_click_on_hud(cx, cy):
            self.canvas.itemconfigure("cursor_weapon", state="hidden")
            try:
                self.hud.lift()
            except Exception:
                pass
            return
        else:
            self.canvas.itemconfigure("cursor_weapon", state="normal")

        # 1. Weapon sprite positioning:
        # Pistol barrel tip is aligned with crosshair center
        if self.current_weapon == "pistol":
            self.canvas.coords(self.weapon_cursor_item, cx - 85, cy)
        else:
            self.canvas.coords(self.weapon_cursor_item, cx, cy)

        # 2. Precision laser crosshair centered directly at mouse!
        if hasattr(self, 'crosshair_dot'):
            self.canvas.coords(self.crosshair_dot, cx - 3, cy - 3, cx + 3, cy + 3)
            self.canvas.coords(self.crosshair_circle, cx - 16, cy - 16, cx + 16, cy + 16)
            self.canvas.coords(self.crosshair_top, cx, cy - 24, cx, cy - 8)
            self.canvas.coords(self.crosshair_bottom, cx, cy + 8, cx, cy + 24)
            self.canvas.coords(self.crosshair_left, cx - 24, cy, cx - 8, cy)
            self.canvas.coords(self.crosshair_right, cx + 8, cy, cx + 24, cy)

    def switch_weapon(self, idx):
        if 0 <= idx < len(WEAPONS):
            self.current_weapon_idx = idx
            self.current_weapon = WEAPONS[idx][0]

            for i, btn in enumerate(self.weapon_btns):
                if i == idx:
                    btn.config(bg="#f59e0b", fg="#ffffff", font=("Segoe UI", 8, "bold"))
                else:
                    btn.config(bg="#1e2230", fg="#94a3b8", font=("Segoe UI", 8, "normal"))

            # Update weapon cursor sprite
            idle_photo = self.assets.get_weapon_photo(self.current_weapon, is_attacking=False)
            self.canvas.itemconfig(self.weapon_cursor_item, image=idle_photo)
            self._update_weapon_cursor_pos()
            self._update_stats_label()

    def cycle_weapon(self):
        next_idx = (self.current_weapon_idx + 1) % len(WEAPONS)
        self.switch_weapon(next_idx)

    def _is_click_on_hud(self, x, y):
        if not hasattr(self, 'hud') or not self.hud.winfo_exists():
            return False
        try:
            hx = self.hud.winfo_rootx()
            hy = self.hud.winfo_rooty()
            hw = self.hud.winfo_width()
            hh = self.hud.winfo_height()
            return (hx - 2 <= x <= hx + hw + 2) and (hy - 2 <= y <= hy + hh + 2)
        except Exception:
            return False

    def _trigger_attack_at(self, click_x, click_y):
        now = time.time()
        if now - self._last_attack_time < 0.10:
            return
        self._last_attack_time = now

        self.cursor_x = click_x
        self.cursor_y = click_y

        # 1. Play weapon sound
        self.sound.play_weapon(self.current_weapon)

        # 2. Trigger visual attack animation on weapon cursor
        self.is_weapon_attacking = True
        atk_photo = self.assets.get_weapon_photo(self.current_weapon, is_attacking=True)
        self.canvas.itemconfig(self.weapon_cursor_item, image=atk_photo)
        if hasattr(self, 'crosshair_circle'):
            self.canvas.itemconfigure(self.crosshair_circle, outline="#ffff55")
            self.canvas.itemconfigure(self.crosshair_dot, fill="#ffff55")
        self._update_weapon_cursor_pos()

        # Weapon-specific impact visual at crosshair
        attack_tag = f"atk_{int(time.time()*1000)}"
        if self.current_weapon == "pistol":
            self.canvas.create_oval(click_x-10, click_y-10, click_x+10, click_y+10, fill="#fef08a", outline="#fb923c", width=2, tags=attack_tag)
            for _ in range(6):
                rx = click_x + random.randint(-24, 24)
                ry = click_y + random.randint(-24, 24)
                self.canvas.create_line(click_x, click_y, rx, ry, fill="#fb923c", width=2, tags=attack_tag)
        elif self.current_weapon == "tepokan":
            for _ in range(8):
                rx = click_x + random.randint(-30, 30)
                ry = click_y + random.randint(-30, 30)
                self.canvas.create_line(click_x, click_y, rx, ry, fill="#38bdf8", width=3, tags=attack_tag)
        elif self.current_weapon == "palu":
            for ang in [0, 45, 90, 135, 180, 225, 270, 315]:
                rad = math.radians(ang)
                self.canvas.create_line(
                    click_x + 6*math.cos(rad), click_y + 6*math.sin(rad),
                    click_x + 30*math.cos(rad), click_y + 30*math.sin(rad),
                    fill="#facc15", width=3, tags=attack_tag
                )
        else: # tangan
            self.canvas.create_oval(click_x-20, click_y-20, click_x+20, click_y+20, outline="#ffffff", width=3, tags=attack_tag)

        self.root.after(140, lambda: self.canvas.delete(attack_tag))

        # Revert weapon sprite back to idle
        def _revert_weapon():
            if self.is_running:
                self.is_weapon_attacking = False
                idle_photo = self.assets.get_weapon_photo(self.current_weapon, is_attacking=False)
                self.canvas.itemconfig(self.weapon_cursor_item, image=idle_photo)
                if hasattr(self, 'crosshair_circle'):
                    self.canvas.itemconfigure(self.crosshair_circle, outline="#ff2222")
                    self.canvas.itemconfigure(self.crosshair_dot, fill="#ff2222")
                self._update_weapon_cursor_pos()
        self.root.after(140, _revert_weapon)

        # 3. Check hit on any creature
        hit_candidates = []
        for c in self.creatures:
            if c.check_hit(click_x, click_y):
                dist = math.hypot(click_x - c.x, click_y - c.y)
                hit_candidates.append((dist, c))

        if hit_candidates:
            hit_candidates.sort(key=lambda item: item[0])
            target_creature = hit_candidates[0][1]
            self._handle_creature_hit(target_creature, click_x, click_y)

    def on_click_attack(self, event):
        self._trigger_attack_at(event.x, event.y)

    def _handle_creature_hit(self, creature, hit_x, hit_y):
        self.slap_count += 1
        current_scale = creature.scale_mult
        old_level = creature.level

        new_level, exploded = creature.hit()
        label = next((lbl for code, lbl in ANIMALS if code == creature.animal_type), creature.animal_type)

        if exploded:
            # Reached max level or classic 1x hit -> explosion!
            self.sound.play_boom()
            self.score += 5000

            # Splatter large vector blood
            for _ in range(4):
                bx = hit_x + random.randint(-35, 35)
                by = hit_y + random.randint(-35, 35)
                splat_tag = f"blood_{int(time.time()*1000)}_{random.randint(100,999)}"
                self.assets.draw_canvas_blood(self.canvas, bx, by, scale_mult=2.5, tag=splat_tag)
                self.blood_splats.append({"tag": splat_tag, "time": time.time()})

            if self.game_mode == 'classic':
                # Remove creature in 1x tepok mode
                self.canvas.delete(creature.canvas_item)
                if creature in self.creatures:
                    self.creatures.remove(creature)
                self.sound.sync_creatures(self.creatures)
                self._create_popup(
                    hit_x, hit_y - 35,
                    f"💥 {label} K.O.!\nSisa: {len(self.creatures)} Hewan (+5000 Poin!)",
                    "#ef4444",
                    duration=1.8,
                    font_size=13
                )
                if len(self.creatures) == 0:
                    self.root.after(400, lambda: self.add_creature("nyamuk"))
            else:
                self._create_popup(
                    hit_x, hit_y - 35,
                    f"💥 BOOOMM! {label} K.O.!\nTITAN DEFEATED! (+5000 Poin!)",
                    "#ef4444",
                    duration=2.0,
                    font_size=14
                )
        else:
            # Creature inflates and grows!
            self.sound.play_grow()

            # Small blood droplet
            splat_tag = f"blood_{int(time.time()*1000)}_{random.randint(100,999)}"
            self.assets.draw_canvas_blood(self.canvas, hit_x, hit_y, scale_mult=current_scale * 0.75, tag=splat_tag)
            self.blood_splats.append({"tag": splat_tag, "time": time.time()})

            level_name = LEVEL_TITLES[min(new_level - 1, len(LEVEL_TITLES) - 1)]
            w_icon = WEAPONS[self.current_weapon_idx][1].split()[0]
            msg = f"{w_icon} {label} MAKIN GEDE!\n{level_name} ({creature.scale_mult:.1f}x)"
            color = "#ef4444" if new_level >= 4 else ("#f59e0b" if new_level >= 3 else "#38bdf8")

            self._create_popup(hit_x, max(60, hit_y - 30), msg, color, duration=1.4, font_size=13)

        # Immediately update visual sprite and coordinates so scale change is instant
        photo = self.assets.get_animal_photo(
            creature.animal_type,
            creature.anim_frame,
            creature.angle,
            creature.scale_mult,
            facing_left=creature.facing_left
        )
        self.canvas.itemconfig(creature.canvas_item, image=photo)
        self.canvas.coords(creature.canvas_item, creature.x, creature.y)

        # Keep creature on top
        if creature.canvas_item:
            self.canvas.tag_raise(creature.canvas_item)
        self._update_stats_label()

    def reset_creature_size(self):
        for c in self.creatures:
            c.reset_size()
        self._update_stats_label()
        self._create_popup(
            self.screen_w // 2, 80,
            "Ukuran Semua Hewan Direset ke Normal!",
            "#4ade80",
            duration=1.0
        )

    def cycle_speed(self):
        self.current_speed_idx = (self.current_speed_idx + 1) % len(self.speed_levels)
        name, mult = self.speed_levels[self.current_speed_idx]
        self.btn_speed.config(text=f"⚡ {name}")
        for c in self.creatures:
            c.set_speed_multiplier(mult)

    def toggle_buzz(self):
        on = self.sound.toggle_buzz()
        self.btn_buzz.config(text="🔊 Suara" if on else "🔇 Senyap", fg="#4ade80" if on else "#94a3b8")

    def _create_popup(self, x, y, text, color, duration=1.2, font_size=12):
        item = self.canvas.create_text(
            x, y,
            text=text,
            font=("Segoe UI Black", font_size, "bold"),
            fill=color,
            justify="center"
        )
        self.popups.append({
            "item": item,
            "x": x,
            "y": y,
            "start_time": time.time(),
            "duration": duration
        })

    def clear_blood_splats(self):
        self.canvas.delete("blood")
        self.blood_splats.clear()

    def _game_loop(self):
        if not self.is_running:
            return

        now = time.time()
        dt = max(0.001, min(0.1, now - self.last_frame_time))
        self.last_frame_time = now

        # 1. Hardware Mouse Position Tracking across desktop
        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        self.cursor_x = pt.x
        self.cursor_y = pt.y
        self._update_weapon_cursor_pos()

        # 2. Hardware Click Detection (works even through transparent canvas pass-through!)
        lbutton = bool(user32.GetAsyncKeyState(0x01) & 0x8000)
        if lbutton and not self._last_lbutton_state:
            if not self._is_click_on_hud(pt.x, pt.y):
                self._trigger_attack_at(pt.x, pt.y)
        self._last_lbutton_state = lbutton

        # 2b. Global Shortcut Detection (M to toggle menu, Esc to quit)
        m_down = bool(user32.GetAsyncKeyState(0x4D) & 0x8000)
        if m_down and 0x4D not in self._last_keys_down:
            self._last_keys_down.add(0x4D)
            self.toggle_hud_minimize()
        elif not m_down and 0x4D in self._last_keys_down:
            self._last_keys_down.discard(0x4D)

        esc_down = bool(user32.GetAsyncKeyState(0x1B) & 0x8000)
        if esc_down and 0x1B not in self._last_keys_down:
            self._last_keys_down.add(0x1B)
            self.quit()
        elif not esc_down and 0x1B in self._last_keys_down:
            self._last_keys_down.discard(0x1B)

        # 3. Update all creatures physics & natural movement
        for c in list(self.creatures):
            c.update(dt, sound_mgr=self.sound)
            photo = self.assets.get_animal_photo(
                c.animal_type,
                c.anim_frame,
                c.angle,
                c.scale_mult,
                facing_left=c.facing_left
            )
            self.canvas.itemconfig(c.canvas_item, image=photo)
            self.canvas.coords(c.canvas_item, c.x, c.y)

        # Keep cursor weapon and laser crosshair above creature and blood
        self.canvas.tag_raise("cursor_weapon")
        self.canvas.tag_raise(self.weapon_cursor_item)
        if hasattr(self, 'crosshair_circle'):
            self.canvas.tag_raise(self.crosshair_circle)
        if hasattr(self, 'crosshair_dot'):
            self.canvas.tag_raise(self.crosshair_dot)
            self.canvas.tag_raise(self.crosshair_top)
            self.canvas.tag_raise(self.crosshair_bottom)
            self.canvas.tag_raise(self.crosshair_left)
            self.canvas.tag_raise(self.crosshair_right)

        # Update floating popups
        for p in list(self.popups):
            elapsed = now - p["start_time"]
            if elapsed > p["duration"]:
                self.canvas.delete(p["item"])
                self.popups.remove(p)
            else:
                offset_y = (elapsed / p["duration"]) * 30.0
                self.canvas.coords(p["item"], p["x"], p["y"] - offset_y)

        # Limit old blood splats
        if len(self.blood_splats) > 35:
            oldest = self.blood_splats.pop(0)
            self.canvas.delete(oldest["tag"])

        # Periodic audio synchronization (ensures all alive animal sounds stay active)
        if not hasattr(self, '_frame_count'):
            self._frame_count = 0
        self._frame_count += 1
        if self._frame_count % 25 == 0:
            self.sound.sync_creatures(self.creatures)

        # 60 FPS
        self.root.after(16, self._game_loop)

    def quit(self):
        self.is_running = False
        self.sound.cleanup()
        try:
            self.hud.destroy()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = MosquitoApp()
    app.run()
