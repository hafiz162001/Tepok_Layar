import os
import time
import wave
import math
import struct
import random
import ctypes
import threading

winmm = ctypes.windll.winmm

class SoundManager:
    def __init__(self, assets_dir="assets"):
        self.root_assets = os.path.abspath(assets_dir)
        self.sounds_dir = os.path.join(self.root_assets, "sounds")
        os.makedirs(self.sounds_dir, exist_ok=True)
        
        self.buzz_enabled = True
        self.sfx_enabled = True
        self.channel_counter = 0
        self._lock = threading.Lock()
        
        self.slap_files = []
        self.gunshot_file = None
        self.zap_file = None
        self.hammer_file = None
        self.boom_file = None
        self.pop_file = None
        self.buzz_files = {}
        self.current_animal = "nyamuk"
        
        # Multi-animal audio system
        self._active_animal_types = set()
        self._running_loops = set()
        self._next_rubah_time = 0.0
        self._next_mammoth_time = 0.0
        self._worker_thread = None
        self._stop_buzz_event = threading.Event()
        self._buzz_paused = False
        
        self._setup_sounds()

    def _setup_sounds(self):
        # 1. Animal Sounds - Check for user uploaded MP3s first, fallback to synthesized WAVs
        
        # Nyamuk (Mosquito)
        nyamuk_mp3 = os.path.join(self.root_assets, "freesound_community-flying-mosquito-105770.mp3")
        if os.path.exists(nyamuk_mp3):
            self.buzz_files["nyamuk"] = nyamuk_mp3
        else:
            p = os.path.join(self.sounds_dir, "buzz_nyamuk.wav")
            if not os.path.exists(p):
                self._create_natural_buzz_wav(p, 520.0)
            self.buzz_files["nyamuk"] = p

        # Rubah (Fox)
        fox_mp3 = os.path.join(self.root_assets, "freesound_community-004027_quarrelling-foxes-52000.mp3")
        if os.path.exists(fox_mp3):
            self.buzz_files["rubah"] = fox_mp3
        else:
            p = os.path.join(self.sounds_dir, "buzz_rubah.wav")
            if not os.path.exists(p):
                self._create_fox_wav(p)
            self.buzz_files["rubah"] = p

        # Mammoth
        mammoth_mp3 = os.path.join(self.root_assets, "sondangsirait419-gajah-220044.mp3")
        if os.path.exists(mammoth_mp3):
            self.buzz_files["mammoth"] = mammoth_mp3
        else:
            p = os.path.join(self.sounds_dir, "buzz_mammoth.wav")
            if not os.path.exists(p):
                self._create_mammoth_wav(p)
            self.buzz_files["mammoth"] = p

        # Laba-laba (Spider)
        p_spider = os.path.join(self.sounds_dir, "buzz_laba_laba.wav")
        if not os.path.exists(p_spider):
            self._create_natural_buzz_wav(p_spider, 95.0)
        self.buzz_files["laba_laba"] = p_spider

        # 2. Weapon SFX
        # Pistol
        for candidate in ["mrfriends-pistol-shot-233473.mp3", "freesound_community-9mm-pistol-shoot-short-reverb-7152.mp3"]:
            c_path = os.path.join(self.root_assets, candidate)
            if os.path.exists(c_path):
                self.gunshot_file = c_path
                break
        if not self.gunshot_file:
            self.gunshot_file = os.path.join(self.sounds_dir, "gunshot.wav")
            if not os.path.exists(self.gunshot_file):
                self._create_gunshot_wav(self.gunshot_file)

        # Tepokan / Raket
        raket_mp3 = os.path.join(self.root_assets, "dragon-studio-tennis-ball-hit-386155.mp3")
        if os.path.exists(raket_mp3):
            self.zap_file = raket_mp3
        else:
            self.zap_file = os.path.join(self.sounds_dir, "zap.wav")
            if not os.path.exists(self.zap_file):
                self._create_zap_wav(self.zap_file)

        # Tangan / Clap
        clap_mp3 = os.path.join(self.root_assets, "rajatchoudhary-single-clap-sound-effect-355862.mp3")
        if os.path.exists(clap_mp3):
            self.slap_files = [clap_mp3]
        else:
            for i, (pitch, thud_f) in enumerate([(1.0, 115), (1.2, 140), (0.85, 95)], 1):
                p = os.path.join(self.sounds_dir, f"slap{i}.wav")
                if not os.path.exists(p):
                    self._create_slap_wav(p, pitch, thud_f)
                self.slap_files.append(p)

        # Palu (Hammer)
        self.hammer_file = os.path.join(self.sounds_dir, "hammer.wav")
        if not os.path.exists(self.hammer_file):
            self._create_hammer_wav(self.hammer_file)

        # Pop / Growth
        self.pop_file = os.path.join(self.sounds_dir, "pop.wav")
        if not os.path.exists(self.pop_file):
            self._create_pop_wav(self.pop_file)

        # Boom / Explosion
        self.boom_file = os.path.join(self.sounds_dir, "boom.wav")
        if not os.path.exists(self.boom_file):
            self._create_boom_wav(self.boom_file)

    def _create_slap_wav(self, filename, pitch=1.0, thud_freq=115):
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            n_samples = int(44100 * 0.16)
            data = []
            for i in range(n_samples):
                t = i / 44100
                env_crack = math.exp(-65 * t * pitch)
                crack = random.uniform(-1, 1) * env_crack
                env_thud = math.exp(-22 * t)
                thud = math.sin(2 * math.pi * thud_freq * max(0, 1 - t * 4) * t) * env_thud
                val = int(32767 * 0.9 * (0.65 * crack + 0.55 * thud))
                val = max(-32767, min(32767, val))
                data.append(struct.pack('<h', val))
            wf.writeframes(b''.join(data))

    def _create_gunshot_wav(self, filename):
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            n_samples = int(44100 * 0.35)
            data = []
            for i in range(n_samples):
                t = i / 44100
                blast_env = math.exp(-40 * t)
                blast = random.uniform(-1, 1) * blast_env
                body_env = math.exp(-12 * t)
                body = math.sin(2 * math.pi * 95 * max(0, 1 - t * 2.5) * t) * body_env
                val = int(32767 * 0.95 * (0.6 * blast + 0.6 * body))
                val = max(-32767, min(32767, val))
                data.append(struct.pack('<h', val))
            wf.writeframes(b''.join(data))

    def _create_zap_wav(self, filename):
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            n_samples = int(44100 * 0.25)
            data = []
            for i in range(n_samples):
                t = i / 44100
                env = math.exp(-25 * t)
                noise = random.uniform(-1, 1) * 0.5
                zap = math.sin(2 * math.pi * (2400 - 1500 * t) * t)
                buzz = math.sin(2 * math.pi * 120 * t)
                val = int(32767 * 0.85 * (zap + buzz * 0.5 + noise) * env)
                val = max(-32767, min(32767, val))
                data.append(struct.pack('<h', val))
            wf.writeframes(b''.join(data))

    def _create_hammer_wav(self, filename):
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            n_samples = int(44100 * 0.3)
            data = []
            for i in range(n_samples):
                t = i / 44100
                clang = math.sin(2 * math.pi * 1200 * t) * math.exp(-60 * t)
                thud = math.sin(2 * math.pi * 75 * max(0, 1 - t * 2) * t) * math.exp(-15 * t)
                val = int(32767 * 0.9 * (0.35 * clang + 0.8 * thud))
                val = max(-32767, min(32767, val))
                data.append(struct.pack('<h', val))
            wf.writeframes(b''.join(data))

    def _create_pop_wav(self, filename):
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            n_samples = int(44100 * 0.18)
            data = []
            for i in range(n_samples):
                t = i / 44100
                env = math.sin(math.pi * (t / 0.18))
                f = 240 + 680 * (t / 0.18)
                val = int(28000 * math.sin(2 * math.pi * f * t) * env)
                val = max(-32767, min(32767, val))
                data.append(struct.pack('<h', val))
            wf.writeframes(b''.join(data))

    def _create_boom_wav(self, filename):
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            n_samples = int(44100 * 0.55)
            data = []
            for i in range(n_samples):
                t = i / 44100
                env = math.exp(-7 * t)
                noise = random.uniform(-1, 1) * math.exp(-12 * t)
                sub = math.sin(2 * math.pi * 55 * max(0, 1 - t) * t) * env
                val = int(32767 * 0.95 * (0.5 * noise + 0.6 * sub))
                val = max(-32767, min(32767, val))
                data.append(struct.pack('<h', val))
            wf.writeframes(b''.join(data))

    def _create_natural_buzz_wav(self, filename, base_freq=520.0):
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(22050)
            n_samples = int(22050 * 2.5)
            data = []
            for i in range(n_samples):
                t = i / 22050
                f_inst = base_freq + 22.0 * math.sin(2 * math.pi * 3.4 * t)
                s1 = math.sin(2 * math.pi * f_inst * t)
                s2 = 0.35 * math.sin(2 * math.pi * (f_inst * 2) * t)
                s3 = 0.15 * math.sin(2 * math.pi * (f_inst * 3) * t)
                buzz = (s1 + s2 + s3) / 1.5
                tremolo = 0.85 + 0.15 * math.sin(2 * math.pi * 4.2 * t)
                val = int(18000 * buzz * tremolo)
                val = max(-32767, min(32767, val))
                data.append(struct.pack('<h', val))
            wf.writeframes(b''.join(data))

    def _create_fox_wav(self, filename):
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(22050)
            n_samples = int(22050 * 2.2)
            data = []
            for i in range(n_samples):
                t = i / 22050
                val = int(12000 * math.sin(2 * math.pi * 220 * t))
                val = max(-32767, min(32767, val))
                data.append(struct.pack('<h', val))
            wf.writeframes(b''.join(data))

    def _create_mammoth_wav(self, filename):
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(22050)
            n_samples = int(22050 * 2.5)
            data = []
            for i in range(n_samples):
                t = i / 22050
                val = int(15000 * math.sin(2 * math.pi * 65 * t))
                val = max(-32767, min(32767, val))
                data.append(struct.pack('<h', val))
            wf.writeframes(b''.join(data))

    def play_sound_file(self, sound_path):
        if not self.sfx_enabled or not sound_path or not os.path.exists(sound_path):
            return
        with self._lock:
            self.channel_counter = (self.channel_counter + 1) % 15
            alias = f"fx_ch_{self.channel_counter}"
        def _play():
            try:
                winmm.mciSendStringW(f'close {alias}', None, 0, 0)
                winmm.mciSendStringW(f'open "{sound_path}" alias {alias}', None, 0, 0)
                winmm.mciSendStringW(f'play {alias}', None, 0, 0)
            except Exception:
                pass
        threading.Thread(target=_play, daemon=True).start()

    def play_weapon(self, weapon_type):
        if weapon_type == "pistol":
            self.play_sound_file(self.gunshot_file)
        elif weapon_type == "tepokan":
            self.play_sound_file(self.zap_file)
        elif weapon_type == "palu":
            self.play_sound_file(self.hammer_file)
        else:
            if self.slap_files:
                self.play_sound_file(random.choice(self.slap_files))

    def play_grow(self):
        if self.pop_file:
            self.play_sound_file(self.pop_file)

    def play_boom(self):
        if self.boom_file:
            self.play_sound_file(self.boom_file)

    def _start_loop(self, animal_type):
        path = self.buzz_files.get(animal_type)
        if not path or not os.path.exists(path):
            return
        alias = f"loop_{animal_type}"
        try:
            winmm.mciSendStringW(f'close {alias}', None, 0, 0)
            winmm.mciSendStringW(f'open "{path}" type mpegvideo alias {alias}', None, 0, 0)
            winmm.mciSendStringW(f'setaudio {alias} volume to 850', None, 0, 0)
            winmm.mciSendStringW(f'play {alias} repeat', None, 0, 0)
            self._running_loops.add(animal_type)
        except Exception:
            pass

    def _stop_loop(self, animal_type):
        alias = f"loop_{animal_type}"
        try:
            winmm.mciSendStringW(f'stop {alias}', None, 0, 0)
            winmm.mciSendStringW(f'close {alias}', None, 0, 0)
        except Exception:
            pass
        self._running_loops.discard(animal_type)

    def _set_channel_volume(self, alias, vol):
        try:
            winmm.mciSendStringW(f'setaudio {alias} volume to {vol}', None, 0, 0)
        except Exception:
            pass

    def _play_fox_sound(self):
        path = self.buzz_files.get("rubah")
        if not path or not os.path.exists(path):
            return
        start_ms = random.randint(2000, 180000)
        end_ms = start_ms + 3500
        def _worker():
            try:
                winmm.mciSendStringW('close ch_rubah', None, 0, 0)
                winmm.mciSendStringW(f'open "{path}" type mpegvideo alias ch_rubah', None, 0, 0)
                winmm.mciSendStringW('set ch_rubah time format ms', None, 0, 0)
                winmm.mciSendStringW('setaudio ch_rubah volume to 800', None, 0, 0)
                winmm.mciSendStringW(f'play ch_rubah from {start_ms} to {end_ms}', None, 0, 0)
            except Exception:
                pass
        threading.Thread(target=_worker, daemon=True).start()

    def _play_mammoth_sound(self):
        path = self.buzz_files.get("mammoth")
        if not path or not os.path.exists(path):
            return
        def _worker():
            try:
                winmm.mciSendStringW('close ch_mammoth', None, 0, 0)
                winmm.mciSendStringW(f'open "{path}" type mpegvideo alias ch_mammoth', None, 0, 0)
                winmm.mciSendStringW('setaudio ch_mammoth volume to 900', None, 0, 0)
                winmm.mciSendStringW('play ch_mammoth from 0', None, 0, 0)
            except Exception:
                pass
        threading.Thread(target=_worker, daemon=True).start()

    def _periodic_animal_worker(self):
        while not self._stop_buzz_event.is_set():
            time.sleep(0.4)
            if not self.buzz_enabled:
                continue

            now = time.time()
            with self._lock:
                types = set(self._active_animal_types)

            # 1. Fox vocalization
            if 'rubah' in types:
                if now >= self._next_rubah_time:
                    self._play_fox_sound()
                    self._next_rubah_time = now + random.uniform(5.5, 9.5)

            # 2. Mammoth trumpet roar
            if 'mammoth' in types:
                if now >= self._next_mammoth_time:
                    self._play_mammoth_sound()
                    self._next_mammoth_time = now + random.uniform(6.0, 11.0)

    def sync_creatures(self, creatures):
        """Synchronizes and mixes audio for all currently active animal species on screen simultaneously."""
        if not self.buzz_enabled:
            self._stop_all_animal_loops()
            return

        alive_types = set()
        has_flying_nyamuk = False
        for c in creatures:
            if getattr(c, 'is_alive', True):
                alive_types.add(c.animal_type)
                if c.animal_type == 'nyamuk' and getattr(c, 'state', None) != 'LANDED':
                    has_flying_nyamuk = True

        new_animals = alive_types - self._active_animal_types
        with self._lock:
            self._active_animal_types = alive_types

        now = time.time()
        # Immediate audio feedback when a new species is summoned
        if 'rubah' in new_animals:
            self._play_fox_sound()
            self._next_rubah_time = now + random.uniform(5.0, 8.5)
        if 'mammoth' in new_animals:
            self._play_mammoth_sound()
            self._next_mammoth_time = now + random.uniform(5.5, 9.5)

        # Continuous loops: Nyamuk
        if 'nyamuk' in alive_types:
            if 'nyamuk' not in self._running_loops:
                self._start_loop('nyamuk')
            if has_flying_nyamuk:
                self._set_channel_volume('loop_nyamuk', 850)
            else:
                self._set_channel_volume('loop_nyamuk', 350)
        else:
            if 'nyamuk' in self._running_loops:
                self._stop_loop('nyamuk')

        # Continuous loops: Laba-laba
        if 'laba_laba' in alive_types:
            if 'laba_laba' not in self._running_loops:
                self._start_loop('laba_laba')
        else:
            if 'laba_laba' in self._running_loops:
                self._stop_loop('laba_laba')

    def set_animal(self, animal_name):
        self.current_animal = animal_name

    def start_buzz(self):
        self._stop_buzz_event.clear()
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._worker_thread = threading.Thread(target=self._periodic_animal_worker, daemon=True)
            self._worker_thread.start()

    def pause_buzz(self):
        """Softens nyamuk buzz without killing sound or causing thread crashes."""
        self._set_channel_volume('loop_nyamuk', 350)

    def resume_buzz(self):
        self._set_channel_volume('loop_nyamuk', 850)

    def _stop_all_animal_loops(self):
        for animal in list(self._running_loops):
            self._stop_loop(animal)
        try:
            winmm.mciSendStringW('close ch_rubah', None, 0, 0)
            winmm.mciSendStringW('close ch_mammoth', None, 0, 0)
        except Exception:
            pass

    def stop_buzz(self):
        self._stop_all_animal_loops()

    def restart_buzz(self):
        self.stop_buzz()
        if self.buzz_enabled:
            self.start_buzz()

    def toggle_buzz(self):
        self.buzz_enabled = not self.buzz_enabled
        if not self.buzz_enabled:
            self._stop_all_animal_loops()
        return self.buzz_enabled

    def cleanup(self):
        self._stop_buzz_event.set()
        self._stop_all_animal_loops()
        for i in range(15):
            try:
                winmm.mciSendStringW(f'close fx_ch_{i}', None, 0, 0)
            except Exception:
                pass
