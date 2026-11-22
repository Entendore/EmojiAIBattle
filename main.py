#!/usr/bin/env python3
"""
EMOJI AI ARENA 🥊 — utility-brained emoji fighter classes battle it out.
Modes: DUEL · MELEE · TEAMS · TOURNAMENT · 👹 BOSS FIGHT.
Features: procedural arenas, biome hazards, power-ups, crowd favor, stats.

Run:   python emoji_ai_arena.py
Keys:  1 duel · 2 melee · 3 teams · 4 tourney · 5 boss · -/+ size · H hazards
       F speed · T brains · S slow-mo · P pause · M mute · N new · ESC quit
"""
import math, random, re, struct, os
import pygame

W, H = 960, 600
FLOOR = 508
FPS = 60
RING_L, RING_R = 96, W - 96
TEAM_COLS = [(255, 95, 95), (95, 150, 255)]
TEAM_ICONS = ["🔴", "🔵"]
TEAM_NAMES = ["RED", "BLUE"]

os.environ.setdefault("SDL_VIDEO_CENTERED", "1")

# ---------------------------------------------------------------- sound synth
try:
    pygame.mixer.pre_init(44100, -16, 1, 512)
except Exception:
    pass
pygame.init()
try:
    pygame.mixer.set_num_channels(16)
    SOUND = pygame.mixer.get_init() is not None
except Exception:
    SOUND = False
MUTED = False
SR = 44100

def _tone(freq=440, dur=0.15, vol=0.4, wave="sine", slide=0.0):
    n = max(1, int(SR * dur))
    out, ph = bytearray(), 0.0
    for i in range(n):
        t = i / SR
        ph += 2 * math.pi * (freq + slide * t) / SR
        if   wave == "sine":   v = math.sin(ph)
        elif wave == "square": v = 1.0 if math.sin(ph) >= 0 else -1.0
        elif wave == "saw":    v = 2 * ((ph / (2 * math.pi)) % 1) - 1
        else:                  v = random.uniform(-1, 1)
        s = int(v * vol * (1 - i / n) * 32767)
        out += struct.pack("<h", max(-32767, min(32767, s)))
    return bytes(out)

SOUNDS = {}
if SOUND:
    _spec = {
        "whoosh": dict(freq=0,    dur=0.10, vol=0.14, wave="noise"),
        "hit":    dict(freq=175,  dur=0.13, vol=0.50, wave="square", slide=-240),
        "heavy":  dict(freq=95,   dur=0.24, vol=0.62, wave="square", slide=-70),
        "block":  dict(freq=1400, dur=0.05, vol=0.24, wave="square", slide=300),
        "dash":   dict(freq=0,    dur=0.16, vol=0.20, wave="noise"),
        "charge": dict(freq=180,  dur=0.45, vol=0.26, wave="saw",    slide=720),
        "boom":   dict(freq=0,    dur=0.42, vol=0.50, wave="noise"),
        "bell":   dict(freq=784,  dur=0.60, vol=0.34, wave="sine"),
        "ko":     dict(freq=320,  dur=0.80, vol=0.50, wave="square", slide=-280),
        "cheer":  dict(freq=0,    dur=0.90, vol=0.22, wave="noise"),
        "heal":   dict(freq=520,  dur=0.40, vol=0.30, wave="sine",   slide=420),
        "shoot":  dict(freq=900,  dur=0.18, vol=0.28, wave="saw",    slide=-500),
    }
    for name, kw in _spec.items():
        try:
            SOUNDS[name] = pygame.mixer.Sound(buffer=_tone(**kw))
        except Exception:
            pass

def sfx(name):
    if SOUND and not MUTED and name in SOUNDS:
        SOUNDS[name].play()

screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("EMOJI AI ARENA 🥊 duel · melee · teams · tourney · boss")

# ---------------------------------------------------------------- emoji engine
EMOJI_CANDIDATES = ("Segoe UI Emoji, Noto Color Emoji, Apple Color Emoji, "
                    "Twemoji, Mozilla Twemoji, JoyPixels, Android Emoji, Symbola, DejaVu Sans")
_emoji_fonts, _glyph_ok_cache, _emoji_cache = {}, {}, {}

def emoji_font(sz):
    if sz not in _emoji_fonts:
        _emoji_fonts[sz] = pygame.font.SysFont(EMOJI_CANDIDATES, sz)
    return _emoji_fonts[sz]

def _glyph_ok(ch):
    if ch in _glyph_ok_cache:
        return _glyph_ok_cache[ch]
    ok = False
    try:
        f = emoji_font(64)
        s = f.render(ch, True, (255, 255, 255))
        b1 = f.render("\uFFFE", True, (255, 255, 255))
        b2 = f.render("\uFFFF", True, (255, 255, 255))
        if s.get_width() > 2 and s.get_height() > 2:
            key = lambda x: pygame.image.tostring(x.convert_alpha(), "RGBA")
            ok = key(s) != key(b1) and key(s) != key(b2)
    except Exception:
        ok = False
    _glyph_ok_cache[ch] = ok
    return ok

def _S(size):
    return pygame.Surface((size, size), pygame.SRCALPHA)

def _star(s, cx, cy, r, col):
    pts = []
    for i in range(8):
        a = math.pi * i / 4 - math.pi / 2
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    pygame.draw.polygon(s, col, pts)

def _star5_surf(size, col=(255, 210, 70), core=(255, 250, 220)):
    s = _S(size)
    pts = []
    for i in range(10):
        a = math.pi * i / 5 - math.pi / 2
        r = (0.44 if i % 2 == 0 else 0.19) * size
        pts.append((size / 2 + math.cos(a) * r, size / 2 + math.sin(a) * r))
    pygame.draw.polygon(s, col, pts)
    if core:
        pygame.draw.circle(s, core, (size // 2, size // 2), max(1, size // 10))
    return s

def _cape(s, K):
    pygame.draw.polygon(s, (72, 22, 44), [(K(2), K(62)), (K(32), K(36)), (K(62), K(62))])

def _tears(s, K):
    pygame.draw.ellipse(s, (110, 180, 240), (K(5), K(30), K(9), K(14)))
    pygame.draw.ellipse(s, (110, 180, 240), (K(50), K(30), K(9), K(14)))

def _p_face(size, eyes, mouth, base=(255, 213, 74), deco=None):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.circle(s, base, (K(32), K(34)), K(28))
    pygame.draw.circle(s, (0, 0, 0, 55), (K(32), K(34)), K(28), max(1, K(2)))
    if deco: deco(s, K)
    ey, ex = K(26), K(12)
    for sgn in (-1, 1):
        cx = K(32) + sgn * ex
        if eyes == "dot":   pygame.draw.circle(s, (45, 32, 12), (cx, ey), K(4))
        elif eyes == "arc": pygame.draw.arc(s, (45, 32, 12), (cx - K(6), ey - K(6), K(12), K(12)), math.radians(20), math.radians(160), max(1, K(3)))
        elif eyes == "big": pygame.draw.circle(s, (255, 255, 255), (cx, ey), K(7)); pygame.draw.circle(s, (45, 32, 12), (cx, ey + K(1)), K(4))
        elif eyes == "wide":pygame.draw.circle(s, (255, 255, 255), (cx, ey), K(8)); pygame.draw.circle(s, (30, 30, 45), (cx, ey + K(2)), K(4))
        elif eyes == "x":
            pygame.draw.line(s, (45, 32, 12), (cx - K(5), ey - K(5)), (cx + K(5), ey + K(5)), max(1, K(3)))
            pygame.draw.line(s, (45, 32, 12), (cx + K(5), ey - K(5)), (cx - K(5), ey + K(5)), max(1, K(3)))
        elif eyes == "star": _star(s, cx, ey, K(7), (255, 240, 150))
        elif eyes == "angry":
            pygame.draw.circle(s, (45, 32, 12), (cx, ey + K(2)), K(3))
            pygame.draw.line(s, (45, 32, 12), (cx - sgn * K(6), ey - K(8)), (cx + sgn * K(5), ey - K(3)), max(1, K(3)))
    my = K(45)
    if mouth == "smile": pygame.draw.arc(s, (60, 40, 10), (K(20), my - K(9), K(24), K(18)), math.radians(200), math.radians(340), max(1, K(3)))
    elif mouth == "frown": pygame.draw.arc(s, (60, 40, 10), (K(20), my - K(2), K(24), K(18)), math.radians(20), math.radians(160), max(1, K(3)))
    elif mouth == "flat": pygame.draw.line(s, (60, 40, 10), (K(22), my), (K(42), my), max(1, K(3)))
    elif mouth == "o": pygame.draw.ellipse(s, (60, 40, 10), (K(27), my - K(5), K(10), K(12)))
    elif mouth in ("open", "wide"):
        w = K(26) if mouth == "wide" else K(20)
        pygame.draw.ellipse(s, (70, 35, 15), (K(32) - w // 2, my - K(7), w, K(16)))
        pygame.draw.ellipse(s, (230, 110, 100), (K(32) - w // 4, my + K(2), w // 2, K(6)))
    elif mouth == "zig":
        pygame.draw.lines(s, (60, 40, 10), False, [(K(20), my), (K(26), my - K(4)), (K(32), my), (K(38), my - K(4)), (K(44), my)], max(1, K(2)))
    elif mouth == "fangs":
        pygame.draw.ellipse(s, (70, 20, 30), (K(21), my - K(5), K(22), K(11)))
        pygame.draw.polygon(s, (255, 255, 255), [(K(24), my - K(3)), (K(29), my - K(3)), (K(26), my + K(4))])
        pygame.draw.polygon(s, (255, 255, 255), [(K(35), my - K(3)), (K(40), my - K(3)), (K(38), my + K(4))])
    return s

def _party_hat(s, K):
    pygame.draw.polygon(s, (90, 140, 240), [(K(22), K(12)), (K(42), K(12)), (K(32), K(-8))])
    pygame.draw.circle(s, (255, 230, 90), (K(32), K(-8)), K(4))

def paint_head(kind, size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    C, R, L, Pg, A = pygame.draw.circle, pygame.draw.rect, pygame.draw.line, pygame.draw.polygon, pygame.draw.arc
    cx, cy = K(32), K(34)
    if kind == "bot":
        L(s, (150, 170, 195), (cx, K(14)), (cx, K(6)), max(1, K(3))); C(s, (120, 225, 255), (cx, K(5)), K(4))
        R(s, (150, 170, 195), (K(10), K(14), K(44), K(40)), border_radius=K(8))
        C(s, (90, 240, 255), (K(22), K(30)), K(6)); C(s, (90, 240, 255), (K(42), K(30)), K(6))
        R(s, (55, 66, 88), (K(20), K(42), K(24), K(8)), border_radius=K(2))
        for tx in (K(26), K(32), K(38)): L(s, (150, 170, 195), (tx, K(42)), (tx, K(50)), max(1, K(2)))
    elif kind == "alien":
        for sgn in (-1, 1):
            L(s, (150, 95, 215), (cx + sgn * K(12), K(12)), (cx + sgn * K(18), K(2)), max(1, K(3)))
            C(s, (200, 140, 255), (cx + sgn * K(18), K(2)), K(3))
        C(s, (150, 95, 215), (cx, K(36)), K(26))
        for sgn in (-1, 1):
            C(s, (255, 255, 255), (cx + sgn * K(11), K(32)), K(8))
            C(s, (20, 20, 35), (cx + sgn * K(11), K(33)), K(4))
        pygame.draw.lines(s, (20, 20, 35), False, [(K(20), K(48)), (K(26), K(44)), (K(32), K(48)), (K(38), K(44)), (K(44), K(48))], max(1, K(2)))
    elif kind == "oni":
        for sgn in (-1, 1): Pg(s, (250, 240, 220), [(cx + sgn * K(14), K(13)), (cx + sgn * K(11), K(0)), (cx + sgn * K(5), K(12))])
        C(s, (226, 68, 68), (cx, cy), K(27))
        for sgn in (-1, 1):
            L(s, (40, 20, 90), (cx + sgn * K(5), K(22)), (cx + sgn * K(14), K(26)), max(1, K(3)))
            C(s, (255, 235, 130), (cx + sgn * K(10), K(30)), K(4))
        R(s, (60, 15, 15), (K(20), K(44), K(24), K(9)), border_radius=K(2))
        Pg(s, (255, 255, 255), [(K(22), K(44)), (K(27), K(44)), (K(24), K(50))])
        Pg(s, (255, 255, 255), [(K(37), K(44)), (K(42), K(44)), (K(40), K(50))])
    elif kind == "frog":
        C(s, (96, 196, 92), (K(18), K(14)), K(10)); C(s, (96, 196, 92), (K(46), K(14)), K(10))
        C(s, (96, 196, 92), (cx, K(38)), K(25))
        for sgn in (-1, 1):
            C(s, (255, 255, 255), (K(32) + sgn * K(14), K(14)), K(6))
            C(s, (25, 35, 25), (K(32) + sgn * K(14), K(15)), K(3))
        A(s, (30, 90, 35), (K(16), K(30), K(32), K(24)), math.radians(200), math.radians(340), max(1, K(3)))
    elif kind == "cat":
        for sgn in (-1, 1):
            Pg(s, (240, 158, 66), [(cx + sgn * K(20), K(16)), (cx + sgn * K(16), K(0)), (cx + sgn * K(6), K(10))])
            Pg(s, (250, 190, 170), [(cx + sgn * K(17), K(13)), (cx + sgn * K(15), K(5)), (cx + sgn * K(9), K(10))])
        C(s, (240, 158, 66), (cx, K(36)), K(25))
        for sgn in (-1, 1): C(s, (40, 30, 15), (cx + sgn * K(10), K(30)), K(4))
        Pg(s, (235, 110, 120), [(cx - K(3), K(38)), (cx + K(3), K(38)), (cx, K(42))])
        for sgn in (-1, 1):
            L(s, (255, 255, 255), (cx + sgn * K(8), K(40)), (cx + sgn * K(22), K(38)), max(1, K(2)))
            L(s, (255, 255, 255), (cx + sgn * K(8), K(44)), (cx + sgn * K(22), K(46)), max(1, K(2)))
    elif kind == "ape":
        C(s, (120, 88, 66), (K(8), K(32)), K(8)); C(s, (120, 88, 66), (K(56), K(32)), K(8))
        C(s, (139, 105, 80), (cx, K(34)), K(26))
        R(s, (212, 182, 152), (K(17), K(34), K(30), K(20)), border_radius=K(10))
        for sgn in (-1, 1):
            C(s, (30, 22, 15), (cx + sgn * K(9), K(30)), K(3))
            L(s, (60, 40, 25), (cx + sgn * K(4), K(24)), (cx + sgn * K(12), K(27)), max(1, K(3)))
        C(s, (60, 40, 25), (cx - K(4), K(42)), K(2)); C(s, (60, 40, 25), (cx + K(4), K(42)), K(2))
        L(s, (60, 40, 25), (K(24), K(48)), (K(40), K(48)), max(1, K(2)))
    elif kind == "ghost":
        C(s, (232, 238, 255), (cx, K(28)), K(24))
        R(s, (232, 238, 255), (K(8), K(28), K(48), K(24)))
        for bx in (K(14), K(26), K(38), K(50)): C(s, (232, 238, 255), (bx, K(52)), K(7))
        C(s, (35, 35, 60), (K(24), K(28)), K(4)); C(s, (35, 35, 60), (K(40), K(28)), K(4))
        pygame.draw.ellipse(s, (35, 35, 60), (K(28), K(36), K(8), K(10)))
        C(s, (255, 180, 200, 150), (K(16), K(36)), K(4)); C(s, (255, 180, 200, 150), (K(48), K(36)), K(4))
    elif kind == "skull":
        C(s, (238, 238, 228), (cx, K(30)), K(25))
        R(s, (238, 238, 228), (K(20), K(48), K(24), K(11)), border_radius=K(3))
        C(s, (25, 25, 30), (K(22), K(28)), K(7)); C(s, (25, 25, 30), (K(42), K(28)), K(7))
        Pg(s, (25, 25, 30), [(cx - K(3), K(36)), (cx + K(3), K(36)), (cx, K(42))])
        for tx in (K(24), K(29), K(34), K(39)): L(s, (120, 120, 115), (tx, K(48)), (tx, K(58)), max(1, K(2)))
    elif kind == "jack":
        R(s, (90, 140, 60), (K(29), K(3), K(7), K(11)), border_radius=K(2))
        C(s, (245, 140, 32), (cx, K(36)), K(26))
        pygame.draw.ellipse(s, (200, 100, 20), (K(16), K(12), K(32), K(48)), max(1, K(2)))
        pygame.draw.ellipse(s, (200, 100, 20), (K(24), K(11), K(16), K(50)), max(1, K(2)))
        Pg(s, (255, 220, 90), [(K(16), K(32)), (K(26), K(32)), (K(21), K(24))])
        Pg(s, (255, 220, 90), [(K(38), K(32)), (K(48), K(32)), (K(43), K(24))])
        Pg(s, (255, 220, 90), [(K(18), K(44)), (K(24), K(48)), (K(30), K(44)), (K(36), K(48)), (K(42), K(44)), (K(46), K(46)), (K(42), K(50)), (K(30), K(52)), (K(20), K(50))])
    elif kind == "dragon":
        for sgn in (-1, 1): Pg(s, (230, 220, 170), [(cx + sgn * K(14), K(14)), (cx + sgn * K(20), K(0)), (cx + sgn * K(6), K(12))])
        C(s, (88, 176, 96), (cx, K(34)), K(26))
        R(s, (128, 206, 128), (K(19), K(38), K(26), K(15)), border_radius=K(7))
        for sgn in (-1, 1):
            C(s, (255, 235, 130), (cx + sgn * K(11), K(26)), K(5))
            pygame.draw.rect(s, (25, 40, 25), (cx + sgn * K(11) - K(1), K(22), K(2), K(8)))
            C(s, (40, 90, 45), (cx + sgn * K(5), K(44)), K(2))
    elif kind == "octo":
        for bx in (K(14), K(26), K(38), K(50)): C(s, (240, 120, 170), (bx, K(52)), K(8))
        C(s, (240, 120, 170), (cx, K(32)), K(24))
        for sgn in (-1, 1):
            C(s, (255, 255, 255), (cx + sgn * K(10), K(30)), K(7))
            C(s, (35, 25, 45), (cx + sgn * K(10), K(31)), K(3.5))
        C(s, (255, 160, 190), (K(14), K(40)), K(4)); C(s, (255, 160, 190), (K(50), K(40)), K(4))
    elif kind == "snake":
        C(s, (110, 190, 90), (cx, K(34)), K(25))
        for sgn in (-1, 1):
            C(s, (255, 235, 130), (cx + sgn * K(10), K(28)), K(5))
            pygame.draw.rect(s, (25, 40, 25), (cx + sgn * K(10) - K(1), K(24), K(2), K(8)))
        L(s, (230, 80, 90), (cx, K(46)), (cx, K(56)), max(1, K(3)))
        L(s, (230, 80, 90), (cx, K(56)), (cx - K(4), K(60)), max(1, K(2)))
        L(s, (230, 80, 90), (cx, K(56)), (cx + K(4), K(60)), max(1, K(2)))
    elif kind == "fox":
        for sgn in (-1, 1):
            Pg(s, (238, 120, 50), [(cx + sgn * K(22), K(22)), (cx + sgn * K(17), K(0)), (cx + sgn * K(5), K(12))])
            Pg(s, (90, 45, 30), [(cx + sgn * K(19), K(17)), (cx + sgn * K(16), K(6)), (cx + sgn * K(9), K(12))])
        C(s, (238, 120, 50), (cx, K(36)), K(24))
        C(s, (250, 245, 235), (cx, K(46)), K(12))
        C(s, (40, 30, 30), (cx, K(42)), K(3))
        for sgn in (-1, 1): C(s, (40, 30, 30), (cx + sgn * K(11), K(30)), K(3.5))
    elif kind == "panda":
        C(s, (30, 30, 35), (K(13), K(13)), K(9)); C(s, (30, 30, 35), (K(51), K(13)), K(9))
        C(s, (245, 245, 245), (cx, K(34)), K(25))
        pygame.draw.ellipse(s, (30, 30, 35), (K(13), K(24), K(17), K(14)))
        pygame.draw.ellipse(s, (30, 30, 35), (K(34), K(24), K(17), K(14)))
        C(s, (255, 255, 255), (K(22), K(31)), K(3)); C(s, (255, 255, 255), (K(42), K(31)), K(3))
        C(s, (30, 30, 35), (cx, K(43)), K(4))
    elif kind == "lion":
        for i in range(12):
            a = math.pi * 2 * i / 12
            x0, y0 = cx + math.cos(a) * K(22), cy + math.sin(a) * K(22)
            Pg(s, (205, 140, 40), [(x0 + math.cos(a + 0.4) * K(8), y0 + math.sin(a + 0.4) * K(8)),
                                   (x0 + math.cos(a) * K(15), y0 + math.sin(a) * K(15)),
                                   (x0 + math.cos(a - 0.4) * K(8), y0 + math.sin(a - 0.4) * K(8))])
        C(s, (240, 190, 70), (cx, cy), K(21))
        for sgn in (-1, 1): C(s, (40, 30, 12), (cx + sgn * K(8), K(30)), K(3))
        C(s, (250, 220, 150), (cx, K(42)), K(8)); C(s, (90, 55, 25), (cx, K(39)), K(3))
    elif kind == "unicorn":
        Pg(s, (255, 215, 100), [(K(28), K(16)), (K(36), K(16)), (K(32), K(-2))])
        C(s, (250, 190, 225), (cx, K(36)), K(24))
        for i, col in enumerate([(255, 120, 140), (140, 220, 255), (170, 255, 170)]):
            A(s, col, (K(2), K(18 + i * 4), K(20), K(28)), math.radians(60), math.radians(300), max(1, K(4)))
        for sgn in (-1, 1):
            pygame.draw.arc(s, (60, 35, 50), (cx + sgn * K(12) - K(5), K(26), K(10), K(8)), math.radians(200), math.radians(340), max(1, K(2)))
        C(s, (255, 150, 190, 160), (K(16), K(42)), K(4)); C(s, (255, 150, 190, 160), (K(48), K(42)), K(4))
    elif kind == "bee":
        pygame.draw.ellipse(s, (210, 232, 255, 210), (K(4), K(8), K(24), K(16)))
        pygame.draw.ellipse(s, (210, 232, 255, 210), (K(36), K(8), K(24), K(16)))
        C(s, (255, 205, 70), (cx, K(38)), K(23))
        R(s, (45, 38, 30), (K(13), K(31), K(38), K(6)), border_radius=K(3))
        R(s, (45, 38, 30), (K(16), K(45), K(32), K(6)), border_radius=K(3))
        C(s, (35, 28, 20), (K(24), K(24)), K(3.5)); C(s, (35, 28, 20), (K(40), K(24)), K(3.5))
        L(s, (45, 38, 30), (K(26), K(16)), (K(22), K(8)), max(1, K(2)))
        L(s, (45, 38, 30), (K(38), K(16)), (K(42), K(8)), max(1, K(2)))
        Pg(s, (60, 50, 35), [(K(28), K(59)), (K(36), K(59)), (K(32), K(66))])
    elif kind == "shark":
        Pg(s, (140, 165, 195), [(K(26), K(12)), (K(38), K(0)), (K(41), K(15))])
        C(s, (150, 175, 205), (cx, K(36)), K(26))
        pygame.draw.ellipse(s, (235, 242, 248), (K(14), K(40), K(36), K(20)))
        C(s, (25, 30, 45), (K(20), K(26)), K(3.5)); C(s, (25, 30, 45), (K(44), K(26)), K(3.5))
        A(s, (40, 50, 70), (K(18), K(34), K(28), K(20)), math.radians(200), math.radians(340), max(1, K(3)))
        for tx in (K(22), K(30), K(38)):
            Pg(s, (255, 255, 255), [(tx, K(45)), (tx + K(6), K(45)), (tx + K(3), K(52))])
    elif kind == "penguin":
        C(s, (38, 44, 64), (cx, K(34)), K(26))
        pygame.draw.ellipse(s, (246, 248, 252), (K(16), K(28), K(32), K(30)))
        C(s, (25, 28, 40), (K(24), K(26)), K(3)); C(s, (25, 28, 40), (K(40), K(26)), K(3))
        Pg(s, (250, 160, 60), [(K(27), K(32)), (K(37), K(32)), (K(32), K(42))])
        C(s, (255, 175, 185, 170), (K(17), K(35)), K(3)); C(s, (255, 175, 185, 170), (K(47), K(35)), K(3))
    elif kind == "trex":
        C(s, (110, 195, 105), (cx, K(34)), K(26))
        pygame.draw.ellipse(s, (140, 215, 130), (K(18), K(38), K(28), K(16)))
        L(s, (35, 80, 35), (K(20), K(46)), (K(44), K(46)), max(1, K(3)))
        for tx in (K(22), K(29), K(36)):
            Pg(s, (255, 255, 245), [(tx, K(46)), (tx + K(5), K(46)), (tx + K(2), K(41))])
        C(s, (255, 235, 130), (K(22), K(22)), K(4.5)); C(s, (255, 235, 130), (K(42), K(22)), K(4.5))
        pygame.draw.rect(s, (30, 50, 25), (K(21), K(21), K(2), K(6)))
        pygame.draw.rect(s, (30, 50, 25), (K(41), K(21), K(2), K(6)))
        L(s, (35, 80, 35), (K(16), K(16)), (K(26), K(19)), max(1, K(3)))
        L(s, (35, 80, 35), (K(48), K(16)), (K(38), K(19)), max(1, K(3)))
    elif kind == "turtle":
        pygame.draw.ellipse(s, (120, 160, 90), (K(8), K(4), K(48), K(36)))
        L(s, (85, 120, 60), (K(32), K(6)), (K(32), K(26)), max(1, K(2)))
        L(s, (85, 120, 60), (K(17), K(14)), (K(30), K(26)), max(1, K(2)))
        L(s, (85, 120, 60), (K(47), K(14)), (K(34), K(26)), max(1, K(2)))
        C(s, (130, 200, 110), (cx, K(45)), K(16))
        C(s, (30, 45, 30), (K(26), K(41)), K(2.5)); C(s, (30, 45, 30), (K(38), K(41)), K(2.5))
        A(s, (45, 90, 45), (K(25), K(44), K(14), K(10)), math.radians(200), math.radians(340), max(1, K(2)))
    elif kind == "owl":
        Pg(s, (150, 110, 75), [(K(12), K(16)), (K(17), K(2)), (K(24), K(13))])
        Pg(s, (150, 110, 75), [(K(52), K(16)), (K(47), K(2)), (K(40), K(13))])
        C(s, (170, 130, 90), (cx, K(36)), K(26))
        C(s, (250, 245, 230), (K(22), K(29)), K(9)); C(s, (250, 245, 230), (K(42), K(29)), K(9))
        C(s, (40, 30, 20), (K(22), K(29)), K(4)); C(s, (40, 30, 20), (K(42), K(29)), K(4))
        Pg(s, (240, 180, 80), [(K(29), K(35)), (K(35), K(35)), (K(32), K(43))])
        pygame.draw.ellipse(s, (200, 165, 125), (K(22), K(44), K(20), K(16)))
        A(s, (150, 110, 75), (K(24), K(46), K(16), K(10)), math.radians(200), math.radians(340), max(1, K(2)))
    elif kind == "crab":
        C(s, (220, 75, 60), (K(8), K(38)), K(9)); C(s, (220, 75, 60), (K(56), K(38)), K(9))
        for sgn in (-1, 1):
            for i in range(3):
                L(s, (180, 60, 50), (cx + sgn * K(16), K(48 + i * 3)), (cx + sgn * K(28), K(54 + i * 3)), max(1, K(2)))
        L(s, (180, 60, 50), (K(24), K(20)), (K(22), K(10)), max(1, K(3)))
        L(s, (180, 60, 50), (K(40), K(20)), (K(42), K(10)), max(1, K(3)))
        C(s, (250, 250, 250), (K(22), K(9)), K(4.5)); C(s, (250, 250, 250), (K(42), K(9)), K(4.5))
        C(s, (30, 25, 35), (K(22), K(9)), K(2)); C(s, (30, 25, 35), (K(42), K(9)), K(2))
        C(s, (235, 85, 70), (cx, K(36)), K(22))
        L(s, (120, 35, 30), (K(26), K(44)), (K(38), K(44)), max(1, K(2)))
    elif kind == "clown":
        for sgn in (-1, 1):
            C(s, (240, 110, 70), (cx + sgn * K(24), K(18)), K(8))
            C(s, (240, 110, 70), (cx + sgn * K(27), K(28)), K(7))
        C(s, (250, 246, 242), (cx, K(36)), K(25))
        C(s, (40, 35, 50), (K(24), K(28)), K(3.5)); C(s, (40, 35, 50), (K(40), K(28)), K(3.5))
        C(s, (235, 70, 70), (cx, K(38)), K(6))
        A(s, (220, 60, 70), (K(18), K(36), K(28), K(20)), math.radians(200), math.radians(340), max(1, K(4)))
    elif kind == "cowboy":
        C(s, (228, 190, 140), (cx, K(40)), K(23))
        pygame.draw.ellipse(s, (140, 95, 55), (K(4), K(18), K(56), K(12)))
        R(s, (140, 95, 55), (K(18), K(2), K(28), K(18)), border_radius=K(6))
        R(s, (90, 60, 35), (K(18), K(14), K(28), K(5)))
        C(s, (45, 32, 18), (K(24), K(34)), K(3)); C(s, (45, 32, 18), (K(40), K(34)), K(3))
        L(s, (90, 60, 35), (K(24), K(48)), (K(40), K(48)), max(1, K(2)))
        L(s, (90, 60, 35), (K(28), K(52)), (K(36), K(52)), max(1, K(3)))
    elif kind == "imp":
        for sgn in (-1, 1):
            Pg(s, (120, 50, 160), [(cx + sgn * K(14), K(16)), (cx + sgn * K(18), K(0)), (cx + sgn * K(6), K(13))])
        C(s, (185, 95, 225), (cx, K(36)), K(25))
        for sgn in (-1, 1):
            L(s, (60, 20, 80), (cx + sgn * K(4), K(24)), (cx + sgn * K(13), K(28)), max(1, K(3)))
            C(s, (255, 230, 120), (cx + sgn * K(9), K(31)), K(3.5))
        pygame.draw.ellipse(s, (60, 15, 40), (K(20), K(44), K(24), K(10)))
        Pg(s, (255, 255, 255), [(K(23), K(45)), (K(28), K(45)), (K(25), K(51))])
        Pg(s, (255, 255, 255), [(K(36), K(45)), (K(41), K(45)), (K(39), K(51))])
    elif kind == "bat":
        Pg(s, (80, 62, 112), [(K(12), K(22)), (K(2), K(34)), (K(12), K(34)), (K(8), K(46)), (K(22), K(38))])
        Pg(s, (80, 62, 112), [(K(52), K(22)), (K(62), K(34)), (K(52), K(34)), (K(56), K(46)), (K(42), K(38))])
        Pg(s, (95, 75, 125), [(K(22), K(16)), (K(25), K(2)), (K(31), K(13))])
        Pg(s, (95, 75, 125), [(K(42), K(16)), (K(39), K(2)), (K(33), K(13))])
        C(s, (95, 75, 125), (cx, K(34)), K(20))
        C(s, (255, 120, 120), (K(26), K(30)), K(3.5)); C(s, (255, 120, 120), (K(38), K(30)), K(3.5))
        Pg(s, (255, 255, 255), [(K(28), K(44)), (K(32), K(44)), (K(30), K(49))])
        Pg(s, (255, 255, 255), [(K(34), K(44)), (K(38), K(44)), (K(36), K(49))])
    elif kind == "alien2":
        pygame.draw.ellipse(s, (140, 220, 140), (K(12), K(6), K(40), K(50)))
        pygame.draw.ellipse(s, (20, 25, 35), (K(15), K(22), K(13), K(20)))
        pygame.draw.ellipse(s, (20, 25, 35), (K(36), K(22), K(13), K(20)))
        C(s, (200, 255, 200), (K(19), K(26)), K(2)); C(s, (200, 255, 200), (K(45), K(26)), K(2))
        L(s, (60, 110, 60), (K(28), K(50)), (K(36), K(50)), max(1, K(2)))
    elif kind == "zombie":
        C(s, (150, 200, 120), (cx, K(34)), K(26))
        L(s, (70, 100, 55), (K(18), K(14)), (K(46), K(18)), max(1, K(2)))
        for tx in (K(24), K(32), K(40)):
            L(s, (70, 100, 55), (tx, K(13)), (tx, K(20)), max(1, K(2)))
        C(s, (245, 245, 240), (K(22), K(29)), K(5)); C(s, (40, 50, 35), (K(22), K(31)), K(2.5))
        L(s, (40, 50, 35), (K(37), K(26)), (K(45), K(32)), max(1, K(3)))
        L(s, (40, 50, 35), (K(45), K(26)), (K(37), K(32)), max(1, K(3)))
        pygame.draw.lines(s, (50, 75, 40), False, [(K(20), K(46)), (K(27), K(49)), (K(34), K(45)), (K(42), K(48))], max(1, K(2)))
        R(s, (245, 245, 235), (K(30), K(46), K(5), K(5)))
    elif kind == "pig":
        for sgn in (-1, 1):
            Pg(s, (240, 140, 160), [(cx + sgn * K(18), K(16)), (cx + sgn * K(14), K(2)), (cx + sgn * K(5), K(12))])
        C(s, (250, 165, 180), (cx, K(36)), K(25))
        C(s, (45, 30, 35), (K(22), K(28)), K(3.5)); C(s, (45, 30, 35), (K(42), K(28)), K(3.5))
        pygame.draw.ellipse(s, (235, 130, 150), (K(22), K(36), K(20), K(14)))
        C(s, (160, 70, 85), (K(28), K(43)), K(2.5)); C(s, (160, 70, 85), (K(36), K(43)), K(2.5))
    return s

def _burst(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    def star(col, r1, r2, n=10):
        pts = []
        for i in range(n * 2):
            a = math.pi * i / n - math.pi / 2
            rr = r1 if i % 2 == 0 else r2
            pts.append((K(32) + math.cos(a) * K(rr), K(32) + math.sin(a) * K(rr)))
        pygame.draw.polygon(s, col, pts)
    star((255, 140, 40), 30, 14); star((255, 220, 80), 18, 8)
    pygame.draw.circle(s, (255, 255, 230), (K(32), K(32)), K(6))
    return s

def _sparkle(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.polygon(s, (255, 250, 200), [(K(32), K(2)), (K(38), K(26)), (K(62), K(32)), (K(38), K(38)), (K(32), K(62)), (K(26), K(38)), (K(2), K(32)), (K(26), K(26))])
    pygame.draw.circle(s, (255, 255, 255), (K(32), K(32)), K(5))
    return s

def _fire(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.polygon(s, (255, 120, 30), [(K(32), K(2)), (K(14), K(34)), (K(50), K(34))])
    pygame.draw.circle(s, (255, 120, 30), (K(32), K(40)), K(18))
    pygame.draw.polygon(s, (255, 220, 90), [(K(32), K(20)), (K(22), K(40)), (K(42), K(40))])
    pygame.draw.circle(s, (255, 220, 90), (K(32), K(44)), K(10))
    return s

def _bolt(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.polygon(s, (255, 220, 60), [(K(38), K(2)), (K(14), K(36)), (K(30), K(36)), (K(26), K(62)), (K(52), K(24)), (K(34), K(24))])
    pygame.draw.polygon(s, (210, 150, 20), [(K(38), K(2)), (K(14), K(36)), (K(30), K(36)), (K(26), K(62)), (K(52), K(24)), (K(34), K(24))], max(1, K(2)))
    return s

def _heart(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.circle(s, (235, 60, 80), (K(22), K(24)), K(13))
    pygame.draw.circle(s, (235, 60, 80), (K(42), K(24)), K(13))
    pygame.draw.polygon(s, (235, 60, 80), [(K(10), K(30)), (K(54), K(30)), (K(32), K(56))])
    pygame.draw.circle(s, (255, 180, 190), (K(18), K(19)), K(4))
    return s

def _bheart(size):
    s = _heart(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.lines(s, (60, 8, 18), False, [(K(32), K(16)), (K(26), K(30)), (K(36), K(38)), (K(30), K(52))], max(1, K(3)))
    return s

def _shield(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pts = [(K(32), K(4)), (K(56), K(11)), (K(56), K(33)), (K(32), K(60)), (K(8), K(33)), (K(8), K(11))]
    pygame.draw.polygon(s, (120, 152, 205), pts)
    pygame.draw.polygon(s, (70, 92, 140), pts, max(1, K(3)))
    pygame.draw.line(s, (70, 92, 140), (K(32), K(8)), (K(32), K(56)), max(1, K(3)))
    return s

def _dizzy(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.ellipse(s, (255, 230, 100), (K(6), K(26), K(52), K(22)), max(1, K(3)))
    _star(s, K(40), K(20), K(12), (255, 220, 80))
    return s

def _dash(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.circle(s, (200, 205, 220, 150), (K(18), K(36)), K(13))
    pygame.draw.circle(s, (215, 220, 235, 170), (K(36), K(30)), K(10))
    pygame.draw.circle(s, (230, 235, 245, 190), (K(50), K(40)), K(7))
    return s

def _trophy(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.polygon(s, (255, 200, 60), [(K(15), K(8)), (K(49), K(8)), (K(44), K(34)), (K(20), K(34))])
    pygame.draw.circle(s, (255, 200, 60), (K(13), K(17)), K(7), max(1, K(3)))
    pygame.draw.circle(s, (255, 200, 60), (K(51), K(17)), K(7), max(1, K(3)))
    pygame.draw.rect(s, (230, 170, 40), (K(29), K(34), K(6), K(10)))
    pygame.draw.rect(s, (255, 200, 60), (K(21), K(44), K(22), K(7)), border_radius=K(2))
    pygame.draw.line(s, (255, 240, 170), (K(21), K(12)), (K(24), K(28)), max(1, K(3)))
    return s

def _glove(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.circle(s, (220, 60, 60), (K(26), K(28)), K(18))
    pygame.draw.circle(s, (220, 60, 60), (K(43), K(22)), K(8))
    pygame.draw.rect(s, (240, 240, 240), (K(36), K(38), K(18), K(14)), border_radius=K(4))
    pygame.draw.line(s, (255, 210, 210), (K(16), K(20)), (K(30), K(16)), max(1, K(3)))
    return s

def _anger(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        r = pygame.Rect(0, 0, K(30), K(30))
        r.center = (K(32) + dx * K(12), K(32) + dy * K(12))
        a0 = {(1, 1): 0, (-1, 1): 90, (-1, -1): 180, (1, -1): 270}[(dx, dy)]
        pygame.draw.arc(s, (235, 70, 60), r, math.radians(a0), math.radians(a0 + 90), max(1, K(5)))
    return s

def _swords(size):
    s = _S(size); k = size / 64.0
    def blade(ang):
        b = _S(64)
        pygame.draw.rect(b, (212, 218, 232), (29, 3, 6, 38), border_radius=3)
        pygame.draw.rect(b, (168, 128, 66), (24, 41, 16, 5), border_radius=2)
        pygame.draw.rect(b, (122, 86, 44), (29, 46, 6, 13), border_radius=2)
        b = pygame.transform.rotozoom(b, ang, k)
        s.blit(b, (size // 2 - b.get_width() // 2, size // 2 - b.get_height() // 2))
    blade(45); blade(-45)
    return s

def _clock(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.rect(s, (200, 205, 220), (K(26), K(2), K(12), K(8)), border_radius=K(2))
    pygame.draw.circle(s, (235, 238, 245), (K(32), K(36)), K(24))
    pygame.draw.circle(s, (90, 95, 120), (K(32), K(36)), K(24), max(1, K(4)))
    pygame.draw.line(s, (60, 60, 80), (K(32), K(36)), (K(32), K(22)), max(1, K(3)))
    pygame.draw.line(s, (60, 60, 80), (K(32), K(36)), (K(42), K(40)), max(1, K(3)))
    return s

def _popper(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.polygon(s, (240, 190, 60), [(K(8), K(56)), (K(30), K(34)), (K(22), K(56))])
    pygame.draw.polygon(s, (230, 90, 90), [(K(14), K(50)), (K(27), K(37)), (K(23), K(52))])
    for p, c in [((K(38), K(20)), (255, 120, 120)), ((K(50), K(30)), (120, 220, 255)),
                 ((K(44), K(8)), (150, 255, 150)), ((K(58), K(16)), (255, 230, 100))]:
        pygame.draw.circle(s, c, p, K(4))
    return s

def _crown(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.polygon(s, (255, 205, 70), [(K(6), K(48)), (K(6), K(20)), (K(19), K(34)), (K(32), K(14)), (K(45), K(34)), (K(58), K(20)), (K(58), K(48))])
    for gx in (K(16), K(32), K(48)): pygame.draw.circle(s, (230, 90, 110), (gx, K(42)), K(3))
    return s

def _brain(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.circle(s, (240, 130, 160), (K(22), K(30)), K(15))
    pygame.draw.circle(s, (240, 130, 160), (K(42), K(28)), K(13))
    pygame.draw.circle(s, (240, 130, 160), (K(32), K(44)), K(12))
    for p0, p1 in [((K(18), K(24)), (K(28), K(30))), ((K(38), K(22)), (K(46), K(30))), ((K(26), K(44)), (K(38), K(48)))]:
        pygame.draw.line(s, (190, 80, 115), p0, p1, max(1, K(3)))
    return s

def _ninja(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.circle(s, (45, 48, 62), (K(32), K(34)), K(26))
    pygame.draw.rect(s, (62, 66, 84), (K(8), K(26), K(48), K(14)))
    pygame.draw.rect(s, (235, 220, 190), (K(16), K(29), K(11), K(6)), border_radius=K(2))
    pygame.draw.rect(s, (235, 220, 190), (K(37), K(29), K(11), K(6)), border_radius=K(2))
    return s

def _die(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.rect(s, (245, 245, 250), (K(10), K(10), K(44), K(44)), border_radius=K(9))
    pygame.draw.rect(s, (140, 145, 165), (K(10), K(10), K(44), K(44)), max(1, K(3)), border_radius=K(9))
    for p in ((K(21), K(21)), (K(43), K(21)), (K(32), K(32)), (K(21), K(43)), (K(43), K(43))):
        pygame.draw.circle(s, (40, 42, 55), p, K(4))
    return s

def _target(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.circle(s, (240, 90, 80), (K(32), K(32)), K(26))
    pygame.draw.circle(s, (250, 250, 250), (K(32), K(32)), K(18))
    pygame.draw.circle(s, (240, 90, 80), (K(32), K(32)), K(10))
    pygame.draw.circle(s, (250, 250, 250), (K(32), K(32)), K(4))
    return s

def _bell(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.rect(s, (230, 180, 60), (K(28), K(4), K(8), K(8)), border_radius=K(3))
    pygame.draw.circle(s, (255, 205, 70), (K(32), K(32)), K(20))
    pygame.draw.rect(s, (255, 205, 70), (K(12), K(36), K(40), K(12)), border_radius=K(5))
    pygame.draw.circle(s, (200, 150, 40), (K(32), K(52)), K(5))
    return s

def _popcorn(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    for px, pr in ((K(20), K(7)), (K(32), K(8)), (K(44), K(7)), (K(26), K(6)), (K(39), K(6))):
        pygame.draw.circle(s, (255, 236, 170), (px, K(22)), pr)
    pygame.draw.rect(s, (220, 60, 60), (K(14), K(28), K(36), K(28)), border_radius=K(3))
    for i in range(3): pygame.draw.rect(s, (250, 250, 250), (K(19 + i * 10), K(28), K(5), K(28)))
    return s

def _muscle(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    skin = (240, 190, 150)
    pygame.draw.circle(s, skin, (K(40), K(24)), K(15))
    pygame.draw.rect(s, skin, (K(8), K(30), K(38), K(18)), border_radius=K(9))
    pygame.draw.circle(s, skin, (K(12), K(39)), K(10))
    pygame.draw.circle(s, (190, 130, 100), (K(40), K(24)), K(15), max(1, K(2)))
    pygame.draw.arc(s, (190, 130, 100), (K(30), K(14), K(20), K(20)), math.radians(30), math.radians(150), max(1, K(2)))
    return s

def _bomb(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.circle(s, (45, 48, 58), (K(28), K(38)), K(20))
    pygame.draw.circle(s, (95, 100, 118), (K(21), K(31)), K(5))
    pygame.draw.rect(s, (95, 100, 118), (K(34), K(12), K(12), K(11)), border_radius=K(3))
    pygame.draw.line(s, (180, 150, 95), (K(45), K(14)), (K(55), K(6)), max(1, K(3)))
    _star(s, K(56), K(5), K(7), (255, 200, 90))
    return s

def _blood(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.polygon(s, (220, 50, 60), [(K(32), K(4)), (K(18), K(34)), (K(46), K(34))])
    pygame.draw.circle(s, (220, 50, 60), (K(32), K(40)), K(15))
    pygame.draw.circle(s, (255, 160, 165), (K(26), K(36)), K(4))
    return s

def _drop(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.polygon(s, (90, 170, 240), [(K(32), K(6)), (K(20), K(36)), (K(44), K(36))])
    pygame.draw.circle(s, (90, 170, 240), (K(32), K(42)), K(14))
    pygame.draw.circle(s, (200, 232, 255), (K(26), K(38)), K(4))
    return s

def _camera(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.rect(s, (60, 64, 82), (K(6), K(18), K(52), K(34)), border_radius=K(5))
    pygame.draw.rect(s, (84, 88, 108), (K(22), K(10), K(16), K(10)), border_radius=K(3))
    pygame.draw.circle(s, (34, 38, 54), (K(32), K(35)), K(13))
    pygame.draw.circle(s, (120, 180, 235), (K(32), K(35)), K(9))
    pygame.draw.circle(s, (220, 240, 255), (K(32), K(35)), K(4))
    pygame.draw.circle(s, (255, 235, 130), (K(50), K(25)), K(3))
    return s

def _firework(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    cols = [(255, 120, 120), (255, 220, 120), (130, 230, 150), (130, 190, 255), (250, 150, 230)]
    cx = K(32)
    for i in range(12):
        a = math.pi * 2 * i / 12
        c = cols[i % 5]
        pygame.draw.line(s, c, (cx + math.cos(a) * K(7), cx + math.sin(a) * K(7)),
                         (cx + math.cos(a) * K(26), cx + math.sin(a) * K(26)), max(1, K(3)))
        pygame.draw.circle(s, c, (int(cx + math.cos(a) * K(29)), int(cx + math.sin(a) * K(29))), max(1, K(3)))
    return s

def _snow(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    col = (205, 232, 255)
    cx = K(32)
    for i in range(3):
        a = math.radians(60 * i)
        dx, dy = math.cos(a) * K(26), math.sin(a) * K(26)
        pygame.draw.line(s, col, (cx - dx, cx - dy), (cx + dx, cx + dy), max(1, K(4)))
    for i in range(6):
        a = math.radians(60 * i)
        ex, ey = cx + math.cos(a) * K(16), cx + math.sin(a) * K(16)
        for da in (0.7, -0.7):
            pygame.draw.line(s, col, (ex, ey), (ex + math.cos(a + math.pi + da) * K(8), ey + math.sin(a + math.pi + da) * K(8)), max(1, K(2)))
    pygame.draw.circle(s, (255, 255, 255), (cx, cx), max(1, K(3)))
    return s

def _megaphone(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.polygon(s, (235, 235, 242), [(K(8), K(26)), (K(32), K(12)), (K(32), K(52)), (K(8), K(38))])
    pygame.draw.rect(s, (90, 95, 122), (K(1), K(26), K(9), K(12)), border_radius=K(2))
    pygame.draw.arc(s, (255, 220, 120), (K(36), K(18), K(22), K(28)), math.radians(-50), math.radians(50), max(1, K(3)))
    pygame.draw.arc(s, (255, 220, 120), (K(42), K(12), K(26), K(40)), math.radians(-50), math.radians(50), max(1, K(2)))
    return s

def _meteor(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.polygon(s, (255, 170, 80), [(K(10), K(6)), (K(38), K(26)), (K(26), K(38))])
    pygame.draw.polygon(s, (255, 220, 130), [(K(16), K(10)), (K(36), K(27)), (K(28), K(35))])
    pygame.draw.circle(s, (200, 120, 90), (K(40), K(40)), K(16))
    pygame.draw.circle(s, (240, 170, 130), (K(36), K(36)), K(6))
    pygame.draw.circle(s, (150, 80, 60), (K(46), K(44)), K(4))
    return s

def _coconut(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.circle(s, (120, 80, 50), (K(32), K(36)), K(22))
    pygame.draw.circle(s, (90, 58, 36), (K(26), K(28)), K(3))
    pygame.draw.circle(s, (90, 58, 36), (K(38), K(28)), K(3))
    pygame.draw.circle(s, (90, 58, 36), (K(32), K(40)), K(3))
    pygame.draw.arc(s, (160, 120, 80), (K(14), K(18), K(36), K(36)), math.radians(30), math.radians(120), max(1, K(3)))
    return s

def _warnsign(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.polygon(s, (255, 210, 60), [(K(32), K(4)), (K(60), K(56)), (K(4), K(56))])
    pygame.draw.polygon(s, (120, 80, 10), [(K(32), K(4)), (K(60), K(56)), (K(4), K(56))], max(1, K(3)))
    pygame.draw.rect(s, (60, 40, 10), (K(29), K(22), K(6), K(18)), border_radius=K(2))
    pygame.draw.circle(s, (60, 40, 10), (K(32), K(48)), K(3.5))
    return s

def _medal(size, col):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.polygon(s, (120, 80, 200), [(K(18), K(0)), (K(28), K(0)), (K(36), K(22)), (K(26), K(22))])
    pygame.draw.polygon(s, (200, 80, 90), [(K(46), K(0)), (K(36), K(0)), (K(28), K(22)), (K(38), K(22))])
    pygame.draw.circle(s, col, (K(32), K(40)), K(18))
    pygame.draw.circle(s, darken(col, 0.6), (K(32), K(40)), K(18), max(1, K(3)))
    pygame.draw.circle(s, (min(255, col[0] + 60), min(255, col[1] + 60), min(255, col[2] + 60)), (K(27), K(34)), K(5))
    return s

def _slate(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.rect(s, (70, 76, 100), (K(6), K(6), K(52), K(52)), border_radius=K(6))
    pygame.draw.rect(s, (240, 244, 252), (K(12), K(14), K(40), K(38)), border_radius=K(3))
    for i in range(3):
        pygame.draw.rect(s, (120, 128, 150), (K(16), K(20 + i * 10), K(32 - i * 6), K(4)), border_radius=K(2))
    pygame.draw.circle(s, (255, 210, 80), (K(32), K(8)), K(5))
    return s

def _fastf(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.polygon(s, (250, 250, 255), [(K(6), K(14)), (K(30), K(32)), (K(6), K(50))])
    pygame.draw.polygon(s, (250, 250, 255), [(K(32), K(14)), (K(56), K(32)), (K(32), K(50))])
    return s

def _arrow(size, flip=False):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.rect(s, (250, 250, 255), (K(6), K(26), K(34), K(12)), border_radius=K(4))
    pygame.draw.polygon(s, (250, 250, 255), [(K(38), K(14)), (K(60), K(32)), (K(38), K(50))])
    if flip:
        s = pygame.transform.flip(s, True, False)
    return s

def _pause(size):
    s = _S(size); k = size / 64.0
    K = lambda v: int(v * k)
    pygame.draw.rect(s, (250, 250, 255), (K(18), K(14), K(10), K(36)), border_radius=K(3))
    pygame.draw.rect(s, (250, 250, 255), (K(36), K(14), K(10), K(36)), border_radius=K(3))
    return s

def _dot(size):
    s = _S(size)
    pygame.draw.circle(s, (170, 175, 190), (size // 2, size // 2), size // 2 - 1)
    return s

_face_map = {
    "😀": ("dot", "open", None), "😄": ("arc", "open", None), "😆": ("arc", "wide", None),
    "😮": ("big", "o", None), "😱": ("wide", "o", None), "🤩": ("star", "smile", None),
    "🥳": ("dot", "smile", _party_hat), "😖": ("angry", "zig", None), "😵": ("x", "o", None),
    "😤": ("angry", "flat", None),
}

PAINTERS = {
    "💥": _burst, "✨": _sparkle, "🔥": _fire, "⚡": _bolt, "❤": _heart, "💔": _bheart,
    "🛡": _shield, "💫": _dizzy, "💨": _dash, "🏆": _trophy, "🥊": _glove, "👊": _glove,
    "🤜": _glove, "💢": _anger, "⚔": _swords, "⏱": _clock, "🎉": _popper, "👑": _crown,
    "🧠": _brain, "🥷": _ninja, "🎲": _die, "🎯": _target, "🔔": _bell, "🍿": _popcorn,
    "💪": _muscle, "💣": _bomb, "🩸": _blood, "➡": _arrow, "⬅": (lambda sz: _arrow(sz, True)),
    "⏸": _pause, "💧": _drop, "📸": _camera, "🎆": _firework, "❄": _snow, "📣": _megaphone,
    "🌠": _meteor, "🍃": _leaf, "☄": _meteor, "🥥": _coconut, "⚠": _warnsign,
    "📊": _slate, "⏩": _fastf,
    "🥇": (lambda sz: _medal(sz, (255, 205, 70))), "🥈": (lambda sz: _medal(sz, (205, 210, 220))),
    "🥉": (lambda sz: _medal(sz, (205, 140, 90))),
    "🌟": (lambda sz: _star5_surf(sz, (255, 215, 80), (255, 250, 220))),
    "⭐": (lambda sz: _star5_surf(sz, (255, 205, 60), None)),
    "👻": lambda sz: paint_head("ghost", sz), "💀": lambda sz: paint_head("skull", sz),
    "👹": lambda sz: paint_head("oni", sz),
    "🧛": lambda sz: _p_face(sz, "angry", "fangs", base=(238, 226, 216), deco=_cape),
    "😂": lambda sz: _p_face(sz, "arc", "wide", deco=_tears),
    "😡": lambda sz: _p_face(sz, "angry", "frown", base=(235, 85, 75)),
}
for _ch, (_e, _m, _d) in _face_map.items():
    PAINTERS[_ch] = (lambda e, m, d: lambda sz: _p_face(sz, e, m, deco=d))(_e, _m, _d)
for _hd in [("🤖", "bot"), ("👾", "alien"), ("👹", "oni"), ("🐸", "frog"), ("🐱", "cat"),
            ("🦍", "ape"), ("🎃", "jack"), ("🐲", "dragon"), ("🐙", "octo"), ("🐍", "snake"),
            ("🦊", "fox"), ("🐼", "panda"), ("🦁", "lion"), ("🦄", "unicorn"),
            ("🐝", "bee"), ("🦈", "shark"), ("🐧", "penguin"), ("🦖", "trex"), ("🐢", "turtle"),
            ("🦉", "owl"), ("🦀", "crab"), ("🤡", "clown"), ("🤠", "cowboy"), ("😈", "imp"),
            ("🦇", "bat"), ("👽", "alien2"), ("🧟", "zombie"), ("🐷", "pig")]:
    PAINTERS[_hd[0]] = (lambda kind: lambda sz: paint_head(kind, sz))(_hd[1])

def get_emoji(ch, size):
    key = (ch, size)
    if key in _emoji_cache:
        return _emoji_cache[key]
    surf = None
    if _glyph_ok(ch):
        try:
            surf = emoji_font(size).render(ch, True, (255, 255, 255)).convert_alpha()
        except Exception:
            surf = None
    if surf is None:
        surf = PAINTERS.get(ch, _dot)(size)
    _emoji_cache[key] = surf
    return surf

EMOJI_RE = re.compile(r"([\u2300-\u23FF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u2764\U0001F000-\U0001FAFF]+)")
_ui_cache = {}

def ui_font(sz):
    if sz not in _ui_cache:
        _ui_cache[sz] = pygame.font.SysFont("arialblack, arialroundedmtbold, verdana, arial", sz)
    return _ui_cache[sz]

def rich_render(text, size, color=(255, 255, 255)):
    parts = EMOJI_RE.split(text)
    surfs = []
    for p in parts:
        if not p:
            continue
        if EMOJI_RE.fullmatch(p):
            for ch in p:
                if ch != "\uFE0F":
                    surfs.append(get_emoji(ch, int(size * 1.08)))
        else:
            surfs.append(ui_font(size).render(p, True, color))
    if not surfs:
        return pygame.Surface((1, 1), pygame.SRCALPHA)
    tw = sum(s.get_width() for s in surfs)
    th = max(s.get_height() for s in surfs)
    out = pygame.Surface((max(1, tw), max(1, th)), pygame.SRCALPHA)
    x = 0
    for s in surfs:
        out.blit(s, (x, (th - s.get_height()) // 2))
        x += s.get_width()
    return out

def lerp(a, b, t): return a + (b - a) * t
def clamp(v, a, b): return max(a, min(b, v))
def ease_out(t): return 1 - (1 - t) ** 2
def darken(c, f): return (int(c[0] * f), int(c[1] * f), int(c[2] * f))
def gauss(x): return math.exp(-x * x)

# ---------------------------------------------------------------- data
HEADS = [
    ("GLITCH", "🤖", (130, 225, 255)), ("ZORGBLAT", "👾", (178, 120, 255)),
    ("AKA-ONI", "👹", (255, 95, 85)), ("SIR CROAK", "🐸", (120, 230, 110)),
    ("MEOW-TRON", "🐱", (250, 175, 80)), ("KONG.BYTE", "🦍", (190, 150, 115)),
    ("BOO-2000", "👻", (200, 215, 255)), ("BONES", "💀", (235, 235, 225)),
    ("PUMPK1N", "🎃", (255, 160, 60)), ("DRAGO", "🐲", (110, 210, 120)),
    ("OCTO-JAB", "🐙", (255, 140, 185)), ("SNEK.EXE", "🐍", (140, 220, 110)),
    ("REYNARD", "🦊", (255, 145, 75)), ("PANDA-MONIUM", "🐼", (240, 240, 240)),
    ("LIONEL 3000", "🦁", (255, 205, 90)), ("UNICORN PRIME", "🦄", (255, 175, 220)),
    ("STINGER", "🐝", (255, 210, 80)), ("CHOMPER", "🦈", (150, 180, 210)),
    ("SIR WADDLES", "🐧", (130, 150, 185)), ("REX.EXE", "🦖", (120, 200, 110)),
    ("SHELLDON", "🐢", (130, 190, 120)), ("PROF HOOT", "🦉", (195, 155, 115)),
    ("PINCH", "🦀", (240, 95, 80)), ("BOZO-TRON", "🤡", (250, 150, 150)),
    ("COLT-45", "🤠", (220, 180, 120)), ("IMP.EXE", "😈", (190, 110, 230)),
    ("NIGHTBITE", "🦇", (155, 135, 205)), ("GREY-1", "👽", (140, 220, 140)),
    ("ZOMBO", "🧟", (150, 200, 120)), ("HAMHOCK", "🐷", (250, 160, 180)),
]

SPECIALS = {
    "FIRE":    ("🔥", "FIREBALL"),   "VOLT": ("⚡", "THUNDER DASH"),
    "CHI":     ("❤", "INNER HEAL"),  "RAGE": ("💢", "RAGE FLURRY"),
    "SLAM":    ("🤜", "SLAM GRAB"),  "DRAIN": ("🩸", "LIFE DRAIN"),
    "FORTIFY": ("🛡", "AEGIS WALL"), "BOMB": ("💣", "CLUSTER BOMB"),
    "IAIDO":   ("⚔", "IAI SLASH"),   "ICE": ("❄", "ICE SHARD"),
}

CLASSES = {
    "BERSERKER": dict(icon="😤", aggr=1.00, guard=0.15, reflex=0.30, pace=1.22, noise=0.10, range=70,
                      hp=100, special="RAGE", blurb="all gas, no brakes",
                      passive="FRENZY — hits harder as HP drops"),
    "TACTICIAN": dict(icon="🧠", aggr=0.45, guard=0.62, reflex=0.72, pace=0.92, noise=0.12, range=150,
                      hp=100, special="CHI", blurb="calculating...",
                      passive="FORESIGHT — gains 30% more energy"),
    "COUNTER":   dict(icon="🥷", aggr=0.60, guard=0.52, reflex=0.90, pace=0.96, noise=0.10, range=120,
                      hp=100, special="VOLT", blurb="waits for the whiff",
                      passive="PUNISHER — +40% dmg vs recovering foes"),
    "WILDCARD":  dict(icon="🎲", aggr=0.75, guard=0.35, reflex=0.50, pace=1.10, noise=0.45, range=100,
                      hp=100, special=None, blurb="chaos incarnate",
                      passive="CHAOS — utility weights re-roll constantly"),
    "SNIPER":    dict(icon="🎯", aggr=0.50, guard=0.42, reflex=0.62, pace=1.00, noise=0.15, range=270,
                      hp=100, special="FIRE", blurb="space away, then burn",
                      passive="DEADEYE — projectiles hit +3 harder"),
    "GRAPPLER":  dict(icon="💪", aggr=0.85, guard=0.30, reflex=0.40, pace=1.05, noise=0.15, range=55,
                      hp=115, special="SLAM", blurb="get over here",
                      passive="THICK SKIN — jabs deal 40% less to it"),
    "VAMPIRE":   dict(icon="🧛", aggr=0.75, guard=0.30, reflex=0.55, pace=1.08, noise=0.15, range=90,
                      hp=95, special="DRAIN", blurb="your HP is my HP",
                      passive="LEECH — heals 35% of damage dealt"),
    "PALADIN":   dict(icon="🛡", aggr=0.40, guard=0.75, reflex=0.55, pace=0.85, noise=0.10, range=95,
                      hp=135, special="FORTIFY", blurb="unbreakable wall",
                      passive="AEGIS PLATING — -15% dmg, jabs can't flinch"),
    "SAMURAI":   dict(icon="⚔", aggr=0.65, guard=0.45, reflex=0.70, pace=1.00, noise=0.12, range=140,
                      hp=100, special="IAIDO", blurb="one cut is all it takes",
                      passive="LONG BLADE — huge heavy reach"),
    "BOMBER":    dict(icon="💣", aggr=0.55, guard=0.40, reflex=0.55, pace=0.98, noise=0.18, range=240,
                      hp=105, special="BOMB", blurb="fire in the hole",
                      passive="MAD BOMBER — bigger blast radius"),
    "FREEZER":   dict(icon="❄", aggr=0.50, guard=0.50, reflex=0.60, pace=0.95, noise=0.15, range=230,
                      hp=100, special="ICE", blurb="stay cool",
                      passive="PERMAFROST — chills last 40% longer"),
}

ACT_META = {
    "in": ("➡", (120, 225, 130)), "out": ("⬅", (235, 185, 110)), "jab": ("👊", (255, 205, 100)),
    "heavy": ("💥", (255, 125, 85)), "block": ("🛡", (135, 175, 255)), "dodge": ("💨", (185, 235, 255)),
    "special": ("⚡", (255, 240, 130)), "taunt": ("😤", (255, 150, 205)), "wait": ("⏸", (170, 170, 185)),
}

ACT = {"jab": 0.10, "heavy": 0.13}
REC = {"jab": 0.24, "heavy": 0.50}
DMG_JAB = (5, 8)
STUN = {"jab": 0.30, "heavy": 0.50, "fire": 0.50, "bomb": 0.55, "grab": 0.80, "slash": 0.50, "drain": 0.40, "ice": 0.40}
CAST_T = {"IAIDO": 0.35, "BOMB": 0.45}
CROWD_FACES = ["😀", "😄", "😆", "😮", "🤩", "😱", "🥳", "🍿", "😂", "😡", "📣", "📸"]

HIT_L = ["{a} slips one in 👊", "{a} pokes {b} 👊", "{b} walks right into a 👊", "clean jab by {a} 👊"]
HVY_L = ["{a} LANDS A HAYMAKER 💥", "OH! {b} felt that one 🤯", "{a} drops the hammer 💥", "BIG shot by {a} 💥"]
BLK_L = ["{b} shells up 🛡️", "CLANK 🛡️ denied!", "{b} eats it on the guard 🛡️"]
DGE_L = ["{b} slips away 💨", "whiff! {a} hits nothing but air 🌬️", "{b} phases out 💨"]
KO_L = ["K.O.! {l} is DONE 😵", "{w} SENDS {l} TO THE JUNKYARD 🏆", "GOODNIGHT! {l} is seeing stars 💫"]
SLAM_L = ["{a} SLAMS {b} into the mat 🤜", "GRAVITY WINS — {b} gets SLAMMED 🤜"]
SLASH_L = ["{a} draws the blade ⚔", "ONE CUT! ⚔ {b} feels the steel"]
PUNISH_L = ["{a} PUNISHES the whiff 💢", "read like a book! {a} counters 💢"]
CHATTER = ["the crowd smells a FINISH 🍿", "tension rising in the arena 😬",
           "what a matchup 🔥", "the AIs are recalculating 🧠", "someone throw a punch!! 😤",
           "the popcorn is FLYING 🍿🍿", "📸 flash bulbs going off in the stands",
           "someone's catching FIRE 🔥", "the stands are SHAKING 😱"]
CAST_L = {"FIRE": "{a} hurls FIRE 🔥", "VOLT": "{a} becomes LIGHTNING ⚡",
          "CHI": "{a} channels inner HP ❤", "RAGE": "{a} enters RAGE MODE 💢",
          "SLAM": "{a} winds up a GRAB 🤜", "DRAIN": "{a} thirsts for HP 🩸",
          "FORTIFY": "{a} raises the AEGIS 🛡", "BOMB": "{a} lobs live ordnance 💣",
          "IAIDO": "{a} lowers the blade ⚔", "ICE": "{a} hurls a freezing shard ❄"}

MODE_LABEL = {"duel": "DUEL 1v1", "ffa": "MELEE", "team": "TEAM BATTLE", "boss": "BOSS FIGHT"}

HAZ_INFO = {
    "surge":   dict(ch="⚡", fall=False, dmg=(12, 16), r=58, warn=1.1, active=0.35, line="⚡ GRID SURGE!"),
    "geyser":  dict(ch="🔥", fall=False, dmg=(13, 17), r=62, warn=1.2, active=0.45, line="🌋 LAVA GEYSER!"),
    "icicle":  dict(ch="❄", fall=True,  dmg=(11, 15), r=52, warn=1.0, active=0.0,  line="❄ ICICLES FALLING!"),
    "meteor":  dict(ch="☄", fall=True,  dmg=(16, 20), r=70, warn=1.4, active=0.0,  line="☄ METEOR INBOUND!"),
    "pumpkin": dict(ch="🎃", fall=True,  dmg=(12, 16), r=60, warn=1.1, active=0.0,  line="🎃 PUMPKIN DROP!"),
    "coconut": dict(ch="🥥", fall=True,  dmg=(11, 14), r=50, warn=0.9, active=0.0,  line="🥥 COCONUTS!"),
}

PU_INFO = {"heal": ("❤", "HEART"), "energy": ("⚡", "ENERGY CORE"), "might": ("💪", "MIGHT")}

# ---------------------------------------------------------------- arena themes
ARENA_THEMES = {
    "NEON CITY": dict(
        sky=((12, 10, 36), (44, 20, 72)), stand=(22, 20, 46), wall=(38, 30, 70),
        mat=(28, 26, 58), matline=(110, 80, 190), glow=(170, 90, 240),
        ropes=((255, 80, 150), (80, 220, 255)), posts=(255, 205, 80),
        bulbs=[(255, 120, 190), (120, 220, 255), (255, 220, 120), (170, 255, 160)],
        spot=(210, 220, 255), build="city", ambient="glitter", hazard="surge",
        props=["✨", "⭐", "📸"], emblem=["🥊", "⚔", "🤖", "👾", "🎯"]),
    "VOLCANO": dict(
        sky=((30, 10, 12), (70, 26, 18)), stand=(38, 20, 20), wall=(58, 28, 24),
        mat=(46, 26, 26), matline=(160, 80, 60), glow=(255, 120, 50),
        ropes=((255, 120, 60), (255, 200, 80)), posts=(255, 170, 60),
        bulbs=[(255, 140, 70), (255, 200, 90), (255, 100, 60)],
        spot=(255, 200, 150), build="volcano", ambient="embers", hazard="geyser",
        props=["🔥", "💥", "⭐"], emblem=["🔥", "💥", "💪", "👹"]),
    "FROSTPEAK": dict(
        sky=((16, 26, 50), (60, 90, 130)), stand=(24, 32, 54), wall=(36, 46, 74),
        mat=(34, 44, 72), matline=(110, 150, 210), glow=(130, 190, 255),
        ropes=((150, 210, 255), (230, 240, 255)), posts=(200, 225, 255),
        bulbs=[(170, 220, 255), (230, 245, 255), (140, 190, 255)],
        spot=(200, 230, 255), build="mountains", ambient="snow", hazard="icicle",
        props=["❄", "⭐", "✨"], emblem=["❄", "⭐", "🛡", "🏆"]),
    "DEEP SPACE": dict(
        sky=((4, 6, 18), (20, 14, 44)), stand=(16, 16, 36), wall=(28, 26, 54),
        mat=(24, 22, 48), matline=(90, 90, 170), glow=(120, 110, 255),
        ropes=((140, 130, 255), (255, 210, 120)), posts=(200, 190, 255),
        bulbs=[(150, 150, 255), (255, 220, 140), (140, 255, 220)],
        spot=(190, 190, 255), build="space", ambient="stars", hazard="meteor",
        props=["⭐", "✨", "🌟"], emblem=["⭐", "🌟", "👾", "🎲"]),
    "SPOOKYARD": dict(
        sky=((16, 10, 26), (44, 20, 52)), stand=(26, 18, 40), wall=(40, 28, 58),
        mat=(34, 26, 48), matline=(120, 90, 160), glow=(180, 120, 255),
        ropes=((255, 150, 60), (170, 110, 220)), posts=(220, 180, 90),
        bulbs=[(255, 160, 70), (180, 120, 230), (140, 230, 140)],
        spot=(230, 200, 255), build="spooky", ambient="spook", hazard="pumpkin",
        props=["🎃", "👻", "💀"], emblem=["🎃", "👻", "💀", "🦇"]),
    "JUNGLE RUINS": dict(
        sky=((10, 24, 18), (34, 60, 36)), stand=(20, 32, 24), wall=(32, 48, 34),
        mat=(28, 44, 30), matline=(90, 150, 90), glow=(120, 220, 120),
        ropes=((140, 220, 110), (240, 220, 110)), posts=(210, 190, 110),
        bulbs=[(150, 230, 130), (250, 220, 120), (120, 200, 255)],
        spot=(210, 240, 190), build="jungle", ambient="leaves", hazard="coconut",
        props=["🍃", "🐸", "🐍", "✨"], emblem=["🍃", "🐸", "🐍", "🦖"]),
}

# ---------------------------------------------------------------- particles
class Part:
    def __init__(self, x, y, ch=None, vx=0, vy=0, g=0, life=0.6, size=22, spin=0, color=None, r=3, rect=False):
        self.x, self.y, self.vx, self.vy, self.g = x, y, vx, vy, g
        self.t, self.life, self.ch, self.size = 0.0, life, ch, size
        self.ang, self.spin, self.color, self.r, self.rect = 0, spin, color, r, rect
    def update(self, dt):
        self.t += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.g * dt
        self.ang += self.spin * dt
    @property
    def dead(self): return self.t >= self.life
    def draw(self, view):
        a = clamp(1 - self.t / self.life, 0, 1)
        if self.ch:
            surf = pygame.transform.rotozoom(get_emoji(self.ch, self.size), self.ang, 0.55 + 0.45 * a)
            surf.set_alpha(int(255 * a))
            view.blit(surf, (self.x - surf.get_width() / 2, self.y - surf.get_height() / 2))
        else:
            col = tuple(int(c * (0.25 + 0.75 * a)) for c in self.color)
            if self.rect:
                pygame.draw.rect(view, col, (self.x - self.r, self.y - self.r, self.r * 2, self.r * 2))
            else:
                pygame.draw.circle(view, col, (int(self.x), int(self.y)), max(1, int(self.r * (0.4 + 0.6 * a))))

class Ftext:
    def __init__(self, x, y, txt, col=(255, 255, 255), size=20):
        self.x, self.y, self.t, self.life = x, y, 0.0, 0.9
        self.surf = rich_render(txt, size, col)
    def update(self, dt):
        self.t += dt
        self.y -= 46 * dt
    @property
    def dead(self): return self.t >= self.life
    def draw(self, view):
        a = clamp(1 - self.t / self.life, 0, 1)
        s = self.surf.copy()
        s.set_alpha(int(255 * a))
        view.blit(s, (self.x - s.get_width() / 2, self.y))

class Fireball:
    def __init__(self, owner):
        self.owner = owner
        self.x = owner.x + owner.facing * 46
        self.y = FLOOR - 66
        self.vx = owner.facing * 470
        self.age, self.dead = 0.0, False
    def update(self, dt, game):
        self.age += dt
        self.x += self.vx * dt
        if random.random() < 0.8:
            game.parts.append(Part(self.x, self.y + random.randint(-6, 6), "🔥", -self.vx * 0.15,
                                   random.randint(-30, 30), life=0.35, size=16))
        for e in game.fighters:
            if e is self.owner or e.team == self.owner.team or e.hp <= 0:
                continue
            if abs(self.x - e.x) < 44 and e.invuln <= 0:
                dmg = random.randint(14, 18) + (3 if self.owner.cls == "SNIPER" else 0)
                e.receive_hit(self.owner, dmg, "fire")
                game.burst(self.x, self.y, big=True)
                self.dead = True
                break
        if self.x < -60 or self.x > W + 60:
            self.dead = True
    def draw(self, view):
        surf = pygame.transform.rotozoom(get_emoji("🔥", 36), self.age * 560, 1)
        view.blit(surf, (self.x - surf.get_width() / 2, self.y - surf.get_height() / 2))

class IceShard:
    def __init__(self, owner):
        self.owner = owner
        self.x = owner.x + owner.facing * 46
        self.y = FLOOR - 66
        self.vx = owner.facing * 430
        self.age, self.dead = 0.0, False
    def update(self, dt, game):
        self.age += dt
        self.x += self.vx * dt
        if random.random() < 0.7:
            game.parts.append(Part(self.x, self.y + random.randint(-6, 6), "❄", -self.vx * 0.1,
                                   random.randint(-25, 25), life=0.4, size=14))
        for e in game.fighters:
            if e is self.owner or e.team == self.owner.team or e.hp <= 0:
                continue
            if abs(self.x - e.x) < 44 and e.invuln <= 0:
                e.receive_hit(self.owner, random.randint(11, 14), "ice")
                dur = 2.5 * (1.4 if self.owner.cls == "FREEZER" else 1.0)
                e.apply_chill(dur)
                game.burst(self.x, self.y)
                self.dead = True
                break
        if self.x < -60 or self.x > W + 60:
            self.dead = True
    def draw(self, view):
        surf = pygame.transform.rotozoom(get_emoji("❄", 32), self.age * 620, 1)
        view.blit(surf, (self.x - surf.get_width() / 2, self.y - surf.get_height() / 2))

class Bomb:
    def __init__(self, owner):
        self.owner = owner
        self.x = owner.x + owner.facing * 36
        self.y = FLOOR - 100
        self.vx = owner.facing * random.uniform(250, 340)
        self.vy = -280
        self.age, self.fuse, self.spin = 0.0, 1.25, 0.0
        self.dead = False
    def update(self, dt, game):
        if self.dead:
            return
        self.age += dt
        self.spin += 430 * dt
        self.vy += 880 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        if random.random() < 0.5:
            game.parts.append(Part(self.x, self.y - 14, "✨", random.randint(-20, 20), -30, life=0.25, size=12))
        hit_someone = False
        for e in game.fighters:
            if e is self.owner or e.team == self.owner.team or e.hp <= 0:
                continue
            if abs(self.x - e.x) < 42 and abs(self.y - (FLOOR - 70)) < 64 and e.invuln <= 0:
                hit_someone = True
                break
        if (self.y >= FLOOR - 14 and self.vy > 0) or self.age > self.fuse or hit_someone:
            self.explode(game)
    def explode(self, game):
        if self.dead:
            return
        self.dead = True
        game.burst(self.x, min(self.y, FLOOR - 20), big=True)
        game.shake = max(game.shake, 9)
        sfx("boom")
        radius = 95 if self.owner.cls == "BOMBER" else 75
        for e in game.fighters:
            if e is self.owner or e.team == self.owner.team or e.hp <= 0 or e.invuln > 0:
                continue
            if abs(self.x - e.x) < radius:
                e.receive_hit(self.owner, random.randint(14, 18), "bomb")
    def draw(self, view):
        surf = pygame.transform.rotozoom(get_emoji("💣", 30), self.spin, 1)
        view.blit(surf, (self.x - surf.get_width() / 2, self.y - surf.get_height() / 2))

class Hazard:
    def __init__(self, kind, x):
        self.kind, self.x = kind, x
        self.info = HAZ_INFO[kind]
        self.r = self.info["r"]
        self.warn = self.info["warn"] * random.uniform(0.9, 1.15)
        self.active_t = self.info["active"]
        self.t, self.phase, self.done = 0.0, "warn", False
        self.fy, self.fvy, self.exploded = -30.0, 60.0, False
    def update(self, dt, game):
        self.t += dt
        if self.phase == "warn":
            if random.random() < dt * 8:
                game.parts.append(Part(self.x + random.randint(-self.r, self.r), FLOOR - 8, "✨", 0, -30, life=0.3, size=12))
            if self.t >= self.warn:
                self.phase = "live"
                self.t = 0.0
                game.say(self.info["line"])
                game.ex = min(1.0, game.ex + 0.15)
                if not self.info["fall"]:
                    sfx("boom")
                    game.shake = max(game.shake, 7)
                    for f in game.fighters:
                        if f.hp > 0 and abs(f.x - self.x) < self.r and f.invuln <= 0:
                            f.receive_hazard(random.randint(*self.info["dmg"]), self.x)
        elif self.phase == "live":
            if self.info["fall"]:
                self.fvy += 1400 * dt
                self.fy += self.fvy * dt
                if self.fy >= FLOOR - 12:
                    self.exploded = True
                    game.burst(self.x, FLOOR - 30, big=True)
                    game.shake = max(game.shake, 8)
                    sfx("boom")
                    for f in game.fighters:
                        if f.hp > 0 and abs(f.x - self.x) < self.r and f.invuln <= 0:
                            f.receive_hazard(random.randint(*self.info["dmg"]), self.x)
                    self.done = True
            else:
                if random.random() < dt * 40:
                    game.parts.append(Part(self.x + random.randint(-24, 24), FLOOR - random.randint(10, 130),
                                           self.info["ch"], random.randint(-40, 40), -random.randint(60, 160),
                                           life=0.45, size=random.randint(16, 30)))
                if self.t >= self.active_t:
                    self.done = True
    def draw(self, view, t):
        if self.phase == "warn":
            p = 0.5 + 0.5 * math.sin(self.t * 12)
            col = (255, 90, 80) if p > 0.5 else (255, 200, 90)
            pygame.draw.ellipse(view, col, (self.x - self.r, FLOOR - 14, self.r * 2, 26), 2)
            ws = get_emoji("⚠", 22)
            view.blit(ws, (self.x - 11, FLOOR - 54 - abs(math.sin(self.t * 6)) * 8))
            if self.info["fall"]:
                pygame.draw.line(view, col, (self.x, 126), (self.x, FLOOR - 30), 1)
            else:
                gs = pygame.Surface((self.r * 2, 120), pygame.SRCALPHA)
                pygame.draw.rect(gs, (255, 120, 80, int(30 * p)), (0, 0, self.r * 2, 120))
                view.blit(gs, (self.x - self.r, FLOOR - 120))
        elif self.phase == "live":
            if self.info["fall"]:
                if not self.exploded:
                    surf = pygame.transform.rotozoom(get_emoji(self.info["ch"], 34), self.t * 400, 1)
                    view.blit(surf, (self.x - surf.get_width() // 2, self.fy - surf.get_height() // 2))
            else:
                if self.kind == "surge":
                    for i in range(4):
                        b = get_emoji("⚡", 52)
                        view.blit(b, (self.x - 26 + random.randint(-4, 4), FLOOR - 44 - i * 46))
                    fl = pygame.Surface((26, 190), pygame.SRCALPHA)
                    pygame.draw.rect(fl, (255, 255, 230, 70), (0, 0, 26, 190))
                    view.blit(fl, (self.x - 13, FLOOR - 190))
                else:
                    for i in range(3):
                        b = get_emoji("🔥", 46)
                        yy = FLOOR - 30 - i * 40 - int(self.t * 160 % 30)
                        view.blit(b, (self.x - 23 + random.randint(-6, 6), yy))

class PowerUp:
    def __init__(self, kind, x):
        self.kind, self.x = kind, x
        self.t, self.life, self.done = 0.0, 12.0, False
    def update(self, dt, game):
        self.t += dt
        self.life -= dt
        if self.life <= 0:
            self.done = True
        if random.random() < dt * 3:
            game.parts.append(Part(self.x + random.randint(-14, 14), FLOOR - 70 + random.randint(-20, 10),
                                   "✨", 0, -30, life=0.4, size=12))
    def draw(self, view, t):
        a = clamp(self.life / 2, 0, 1)
        y = FLOOR - 70 + math.sin(self.t * 3) * 8
        gl = pygame.Surface((44, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(gl, (255, 255, 255, int(50 * a)), (0, 0, 44, 12))
        view.blit(gl, (self.x - 22, FLOOR - 10))
        surf = get_emoji(PU_INFO[self.kind][0], 26).copy()
        surf.set_alpha(int(255 * a))
        view.blit(surf, (self.x - 13, y - 13))

def make_glow(col):
    s = pygame.Surface((130, 130), pygame.SRCALPHA)
    for i in range(16):
        pygame.draw.circle(s, (*col, 3), (65, 65), 64 - i * 4)
    return s

# ---------------------------------------------------------------- fighter
class Fighter:
    def __init__(self, game, index, team, info, cls_name, x0):
        self.game, self.index, self.team = game, index, team
        self.name, self.head, self.col = info[0], info[1], info[2]
        self.cls, self.cd = cls_name, CLASSES[cls_name]
        self.special = self.cd["special"] or random.choice(["FIRE", "VOLT", "CHI", "RAGE", "BOMB", "ICE"])
        self.max_hp = self.cd["hp"]
        self.hp = float(self.max_hp)
        self.aggr_r, self.guard_r, self.reflex_r = self.cd["aggr"], self.cd["guard"], self.cd["reflex"]
        self.x, self.x0 = x0, x0
        self.vx, self.z, self.vz = 0.0, 0.0, 0.0
        self.energy, self.wins = 0.0, 0
        self.state, self.t = "idle", 0.0
        self.attack, self.wT, self.attack_hit, self.attack_token = None, 0.1, False, 0
        self.combo, self.buff_t, self.shield_t, self.might_t = 0, 0.0, 0.0, 0.0
        self.streak, self.chill_t = 0, 0.0
        self.facing = 1 if index % 2 == 0 else -1
        self.dodge_cd, self.invuln = 0.0, 0.0
        self.plan, self.think_t = None, random.uniform(0.1, 0.3)
        self.react_map, self.ghost = {}, False
        self.ko_t, self.win_t = 0.0, 0.0
        self.dash_kind, self.dash_T, self.volt_from, self.volt_to = None, 0.1, 0, 0
        self.util, self.target = [], None
        self.hz_pending, self.hz_dir = None, None
        self.pu_dir = None
        self.spec = None
        self.boss, self.boss_scale, self.dmg_mult, self.super_armor = False, 1.0, 1.0, False
        self.stats = dict(dmg=0, hits=0, crits=0, ko=0)
        self.head_surf = get_emoji(self.head, 76)
        g = get_emoji("🥊", 42)
        self.glove = {"L": g, "R": pygame.transform.flip(g, True, False)}
        self.glow = make_glow(self.col)

    def make_boss(self):
        self.boss, self.boss_scale, self.dmg_mult, self.super_armor = True, 1.7, 1.7, True
        self.max_hp, self.hp = 420, 420.0
        self.head_surf = get_emoji(self.head, int(76 * self.boss_scale))
        g = get_emoji("🥊", int(42 * self.boss_scale))
        self.glove = {"L": g, "R": pygame.transform.flip(g, True, False)}

    # ---------- relationships ----------
    def foes(self):
        return [f for f in self.game.fighters if f is not self and f.team != self.team and f.hp > 0]
    def allies(self):
        return [f for f in self.game.fighters if f is not self and f.team == self.team and f.hp > 0]
    def pick_target(self):
        foes = self.foes()
        if not foes:
            self.target = None
            return
        best, bs = None, -1.0
        for e in foes:
            d = abs(e.x - self.x)
            s = 1.0 / (1.0 + d / 220)
            s *= 1 + 0.9 * (1 - e.hp / e.max_hp)
            if e.target is self:
                s *= 1.25
            for a in self.allies():
                if a.target is e:
                    s *= 1.35
            s *= random.uniform(0.85, 1.15)
            if s > bs:
                bs, best = s, e
        self.target = best
    def nearest_foe(self, rng):
        best, bd = None, 1e9
        for e in self.foes():
            d = abs(e.x - self.x)
            if d < bd:
                bd, best = d, e
        return best if (best is not None and bd < rng) else None

    # ---------- parameters ----------
    def heavy_reach(self): return {"SAMURAI": 178, "GRAPPLER": 120}.get(self.cls, 132)
    def heavy_windup(self): return {"SAMURAI": 0.58}.get(self.cls, 0.46)
    def heavy_dmg(self): return {"SAMURAI": (14, 20)}.get(self.cls, (12, 17))

    def gain_energy(self, amt):
        if self.cls == "TACTICIAN":
            amt *= 1.3
        if self.game.ex >= 0.7:   # crowd favor
            amt *= 1.5
        self.energy = min(100.0, self.energy + amt)

    def apply_chill(self, dur):
        self.chill_t = max(self.chill_t, dur)
        for i in range(4):
            self.game.parts.append(Part(self.x + random.randint(-24, 24), FLOOR - 90 + random.randint(-30, 20),
                                        "❄", random.randint(-20, 20), random.randint(-40, 10), life=0.5, size=14))

    # ---------- actions ----------
    def start_attack(self, kind, fast=False):
        self.state, self.attack = "windup", kind
        if fast:
            w = 0.09
        elif kind == "heavy":
            w = self.heavy_windup()
        else:
            w = 0.16
        if self.chill_t > 0:
            w *= 1.35
        self.wT = w * random.uniform(0.9, 1.15)
        self.t, self.attack_hit = self.wT, False
        self.attack_token += 1
        self.plan = None
        sfx("whoosh")

    def start_block(self):
        self.state, self.t, self.plan = "block", random.uniform(0.5, 0.9), None

    def start_taunt(self):
        self.state, self.t, self.plan = "taunt", 0.9, None
        self.gain_energy(12)
        if random.random() < 0.6:
            self.game.say(f"{self.name} taunts! 😤")
        sfx("dash")

    def do_dodge(self, direction):
        self.state, self.t, self.plan = "dodge", 0.26, None
        self.vx = direction * 560 * (0.65 if self.chill_t > 0 else 1.0)
        self.invuln, self.dodge_cd = 0.30, 1.5
        self.game.parts.append(Part(self.x, FLOOR - 60, "💨", -direction * 60, 0, life=0.4, size=30))
        sfx("dash")

    def start_cast(self):
        self.state, self.plan = "cast", None
        self.t = CAST_T.get(self.special, 0.55)
        sfx("charge")
        self.game.say(f"{self.name} is charging something ⚡")

    def fire_special(self):
        self.energy = 0
        g, tg, sp = self.game, self.target, self.special
        g.say(CAST_L[sp].format(a=self.name))
        if sp == "FIRE":
            g.projectiles.append(Fireball(self))
            sfx("shoot")
        elif sp == "ICE":
            g.projectiles.append(IceShard(self))
            sfx("shoot")
        elif sp in ("VOLT", "SLAM", "DRAIN", "IAIDO"):
            sign = self.facing
            off = {"VOLT": 72, "SLAM": 60, "DRAIN": 72, "IAIDO": 92}[sp]
            T = {"VOLT": 0.16, "SLAM": 0.20, "DRAIN": 0.16, "IAIDO": 0.12}[sp]
            if tg is not None and tg.hp > 0:
                sign = 1 if tg.x >= self.x else -1
                tgt = tg.x - sign * off
            else:
                tgt = self.x + sign * 220
            self.state, self.dash_kind, self.dash_T, self.t = "dash", sp, T, T
            self.volt_from = self.x
            self.volt_to = clamp(clamp(tgt, self.x - 460, self.x + 460), RING_L, RING_R)
            self.invuln = 0.22
            sfx("shoot" if sp in ("VOLT", "IAIDO") else "dash")
        elif sp == "CHI":
            heal = min(self.max_hp - self.hp, 26)
            self.hp += heal
            self.buff_t = 4.5
            for i in range(8):
                g.parts.append(Part(self.x + random.randint(-30, 30), FLOOR - 90 + random.randint(-30, 30),
                                    random.choice(["❤", "✨"]), random.randint(-30, 30), -random.randint(40, 110), life=0.8, size=20))
            g.texts.append(Ftext(self.x, FLOOR - 140, f"+{int(heal)}", (130, 255, 150)))
            sfx("heal")
        elif sp == "RAGE":
            self.combo = 4
            g.burst(self.x, FLOOR - 80)
            self.start_attack("jab", fast=True)
            sfx("boom")
        elif sp == "FORTIFY":
            heal = min(12, self.max_hp - self.hp)
            self.hp += heal
            self.shield_t = 4.0
            for i in range(6):
                g.parts.append(Part(self.x + random.randint(-34, 34), FLOOR - 80 + random.randint(-30, 20),
                                    "🛡", 0, -random.randint(30, 80), life=0.7, size=18))
            sfx("heal")
        elif sp == "BOMB":
            g.bombs.append(Bomb(self))
            sfx("whoosh")

    def resolve_dash(self):
        g, k = self.game, self.dash_kind
        rad = {"VOLT": 115, "SLAM": 125, "DRAIN": 115, "IAIDO": 200}[k]
        e = self.nearest_foe(rad)
        if k == "VOLT":
            if e and e.invuln <= 0:
                e.receive_hit(self, random.randint(15, 19), "heavy")
            sfx("boom")
        elif k == "SLAM":
            if e and e.invuln <= 0:
                e.receive_hit(self, random.randint(17, 21), "grab", unblockable=True)
                g.burst(e.x, FLOOR - 80, big=True)
                if random.random() < 0.7:
                    g.say(random.choice(SLAM_L).format(a=self.name, b=e.name))
            sfx("heavy")
        elif k == "DRAIN":
            if e and e.invuln <= 0:
                e.receive_hit(self, random.randint(12, 15), "drain")
            sfx("hit")
        elif k == "IAIDO":
            if e and e.invuln <= 0:
                e.receive_hit(self, random.randint(19, 23), "slash", unblockable=True)
                for i in range(3):
                    g.parts.append(Part(e.x + random.randint(-30, 30), FLOOR - 90 + random.randint(-20, 20),
                                        "⚔", random.randint(-60, 60), random.randint(-90, 0), life=0.4, size=26, spin=random.randint(-400, 400)))
                if random.random() < 0.7:
                    g.say(random.choice(SLASH_L).format(a=self.name, b=e.name))
            sfx("heavy")

    # ---------- combat ----------
    def try_hit(self):
        if self.attack_hit:
            return
        if self.attack == "jab":
            reach, dr = 104, DMG_JAB
        else:
            reach, dr = self.heavy_reach(), self.heavy_dmg()
        if self.boss:
            reach = int(reach * 1.35)
        foe = None
        bd = 1e9
        for e in self.foes():
            if e.invuln > 0:
                continue
            d = abs(e.x - self.x)
            if d <= reach and (e.x - self.x) * self.facing >= -12 and d < bd:
                bd, foe = d, e
        if foe is None:
            return
        self.attack_hit = True
        dmg = random.randint(*dr)
        crit = random.random() < 0.08
        if crit:
            dmg = int(dmg * 1.6)
        if self.buff_t > 0:
            dmg = int(dmg * 1.3)
        if self.might_t > 0:
            dmg = int(dmg * 1.3)
        if self.cls == "BERSERKER":
            dmg = int(dmg * (1 + 0.5 * (1 - self.hp / self.max_hp)))
        if self.cls == "COUNTER" and foe.state == "recover":
            dmg = int(dmg * 1.4)
            self.game.texts.append(Ftext(foe.x, FLOOR - 150, "PUNISH!", (255, 240, 120), 18))
            if random.random() < 0.6:
                self.game.say(random.choice(PUNISH_L).format(a=self.name))
        if self.streak >= 3:
            dmg = int(dmg * 1.15)
        dmg = int(dmg * self.dmg_mult)
        self.streak += 1
        if self.streak == 5:
            self.game.say(f"{self.name} is ON A RAMPAGE 🔥")
        elif self.streak == 8:
            self.game.say(f"{self.name} is UNSTOPPABLE 😱")
        self.stats["dmg"] += dmg
        self.stats["hits"] += 1
        if crit:
            self.stats["crits"] += 1
        self.gain_energy(10 if self.attack == "jab" else 15)
        if crit:
            self.game.texts.append(Ftext(foe.x, FLOOR - 160, "CRIT! 🌟", (255, 235, 130), 22))
            self.game.shake = max(self.game.shake, 8)
            self.game.ex = min(1.0, self.game.ex + 0.1)
            sfx("heavy")
        if self.cls == "SAMURAI" and self.attack == "heavy" and random.random() < 0.5:
            self.game.say(random.choice(SLASH_L).format(a=self.name, b=foe.name))
        foe.receive_hit(self, dmg, self.attack)

    def receive_hit(self, src, dmg, kind, unblockable=False):
        g = self.game
        facing_ok = (src.x - self.x) * self.facing >= 0
        sneak = not facing_ok
        if self.state == "block" and not unblockable and facing_ok:
            dmg = max(1, int(dmg * 0.15))
            self.hp -= dmg
            self.gain_energy(6)
            src.gain_energy(4)
            self.vx = src.facing * 100
            g.parts.append(Part((self.x + src.x) / 2, FLOOR - 70, "🛡", 0, -30, life=0.35, size=30))
            g.texts.append(Ftext(self.x, FLOOR - 130, "BLOCK", (150, 190, 255), 16))
            sfx("block")
            if random.random() < 0.35:
                g.say(random.choice(BLK_L).format(b=self.name))
        else:
            if sneak:
                dmg = int(dmg * 1.25)
                if random.random() < 0.5:
                    g.texts.append(Ftext(self.x, FLOOR - 155, "SNEAKY!", (255, 160, 220), 16))
            if kind == "jab" and self.cls == "GRAPPLER":
                dmg = max(1, int(dmg * 0.6))
            if self.cls == "PALADIN":
                dmg = max(1, int(dmg * 0.85))
            if self.shield_t > 0:
                dmg = max(1, int(dmg * 0.5))
            self.hp -= dmg
            self.gain_energy(9)
            self.streak = 0
            armor = (kind == "jab" and (self.cls == "PALADIN" or self.super_armor) and self.hp > 0)
            if armor:
                g.parts.append(Part(self.x, FLOOR - 80, "🛡", 0, -40, life=0.3, size=22))
                sfx("block")
            else:
                self.state = "hit"
                self.t = STUN.get(kind, 0.4)
                self.attack, self.plan = None, None
                self.vx = src.facing * (170 if kind == "jab" else 340)
            g.burst((self.x + src.x) / 2, FLOOR - 75, big=(kind != "jab"))
            g.texts.append(Ftext(self.x, FLOOR - 135, f"-{dmg}", (255, 235, 120), 22 if kind != "jab" else 18))
            g.shake = max(g.shake, 10 if kind != "jab" else 4)
            g.freeze = max(g.freeze, 0.085 if kind != "jab" else 0.045)
            g.ex = min(1.0, g.ex + dmg * 0.028)
            sfx("heavy" if kind != "jab" else "hit")
            if kind != "jab" and random.random() < 0.55:
                g.say(random.choice(HVY_L).format(a=src.name, b=self.name))
            elif random.random() < 0.12:
                g.say(random.choice(HIT_L).format(a=src.name, b=self.name))
            if self.hp > 0 and self.hp < self.max_hp * 0.25 and random.random() < 0.5:
                g.parts.append(Part(self.x + random.randint(-16, 16), FLOOR - 120, "💧", random.randint(-20, 20), 60, 200, life=0.5, size=14))
            if src.cls == "VAMPIRE":
                h = dmg * 0.35
                src.hp = min(src.max_hp, src.hp + h)
                if random.random() < 0.45:
                    g.texts.append(Ftext(src.x, FLOOR - 140, f"+{max(1, int(h))}", (140, 255, 160), 15))
                if random.random() < 0.5:
                    g.parts.append(Part(src.x, FLOOR - 110, "❤", 0, -60, life=0.5, size=16))
        if self.hp <= 0:
            g.do_ko(self, src)

    def receive_hazard(self, dmg, hx):
        if self.invuln > 0 or self.hp <= 0:
            return
        g = self.game
        blocked = self.state == "block" and (hx - self.x) * self.facing >= 0
        if blocked:
            dmg = max(1, int(dmg * 0.3))
            g.texts.append(Ftext(self.x, FLOOR - 130, "BLOCK", (150, 190, 255), 16))
            sfx("block")
        self.hp -= dmg
        self.streak = 0
        self.gain_energy(8)
        if not blocked:
            self.state = "hit"
            self.t = 0.45
            self.attack, self.plan = None, None
            self.vx = -math.copysign(260, (hx - self.x) if hx != self.x else 1)
        g.burst(self.x, FLOOR - 70)
        g.texts.append(Ftext(self.x, FLOOR - 135, f"-{dmg} ⚠", (255, 180, 120), 20))
        g.shake = max(g.shake, 6)
        g.ex = min(1.0, g.ex + 0.1)
        sfx("hit")
        if self.hp <= 0:
            g.do_ko(self, None)

    # ---------- utility AI ----------
    def utility(self):
        g, c, tg = self.game, self.cd, self.target
        if tg is None or tg.hp <= 0:
            self.pick_target()
            tg = self.target
        d = abs(tg.x - self.x) if tg else 300.0
        cl = lambda v: max(0.0, min(1.0, v))

        threat = 0.0
        for e in self.foes():
            de = abs(e.x - self.x)
            if e.state == "windup" and e.attack:
                rng = e.heavy_reach() if e.attack == "heavy" else 104
                if de < rng + 50:
                    threat = max(threat, (0.9 if e.attack == "heavy" else 0.45) * cl((rng + 50 - de) / 90 + 0.25))
            elif e.state == "active" and de < 170:
                threat = max(threat, 1.0)
        for p in g.projectiles:
            if p.owner.team != self.team and abs(p.x - self.x) < 230 and (self.x - p.x) * p.vx > 0:
                threat = max(threat, 0.75)
        for b in g.bombs:
            if b.owner.team != self.team and abs(b.x - self.x) < 160:
                threat = max(threat, 0.7)

        lowhp = 1 - self.hp / self.max_hp
        o_lowhp = (1 - tg.hp / tg.max_hp) if tg else 0.0
        finish = 1 + o_lowhp * 0.8
        desired = c["range"]
        vuln = 1.5 if tg and tg.state in ("recover", "taunt", "cast") else 1.0
        u = {}

        s = 0.0
        if tg and d > desired:
            s = cl((d - desired) / 240) * (0.45 + 0.55 * self.aggr_r)
        if tg and tg.state in ("recover", "cast") and d < 280:
            s += 0.3 * self.aggr_r
        u["in"] = s
        s = 0.0
        if tg and d < desired:
            s = cl((desired - d) / max(60.0, desired)) * (0.35 + 0.6 * self.guard_r + lowhp * 0.55)
        if threat > 0.6:
            s += 0.25
        u["out"] = s

        blk = 0.4 if tg and tg.state == "block" else 1.0
        u["jab"] = gauss((d - 88) / 55) * (0.45 + 0.55 * self.aggr_r) * finish * vuln * blk
        hr = self.heavy_reach()
        u["heavy"] = gauss((d - hr * 0.82) / 72) * (0.30 + 0.45 * self.aggr_r) * finish * vuln * (0.25 if tg and tg.state == "block" else 1.0)
        if tg and tg.state == "windup":
            u["heavy"] *= 0.6
        if self.cls == "SAMURAI":
            u["heavy"] *= 1.12

        u["block"] = threat * (0.35 + 0.7 * self.guard_r) * (1 + lowhp * 0.6) * (0.3 if tg and tg.state == "block" else 1.0)
        back_space = (self.x - RING_L) if self.facing == 1 else (RING_R - self.x)
        corner = 1.0 if back_space > 95 else 0.35
        u["dodge"] = threat * (0.3 + 0.7 * self.reflex_r) * corner if self.dodge_cd <= 0 else 0.0

        if self.energy >= 100:
            sp = self.special
            if sp == "FIRE":    s = 1.05 * gauss((d - 290) / 170) + (0.25 if tg and tg.state == "block" else 0)
            elif sp == "ICE":   s = 1.05 * gauss((d - 280) / 170) + (0.3 if tg and tg.state == "block" else 0)
            elif sp == "VOLT":  s = 1.05 * gauss((d - 210) / 170)
            elif sp == "CHI":   s = 1.7 * lowhp + 0.05
            elif sp == "RAGE":  s = 1.15 * gauss((d - 95) / 95)
            elif sp == "SLAM":  s = 1.25 * gauss((d - 150) / 150) + (0.35 if tg and tg.state == "block" else 0)
            elif sp == "DRAIN": s = 1.0 * gauss((d - 150) / 140) + 0.6 * lowhp
            elif sp == "FORTIFY": s = 0.3 + 1.1 * lowhp + 0.35 * threat
            elif sp == "BOMB":  s = 1.1 * gauss((d - 250) / 180) + 0.15
            elif sp == "IAIDO": s = 1.2 * gauss((d - 160) / 140) + (0.35 if tg and tg.state in ("recover", "cast") else 0)
            else:               s = 0.4
            u["special"] = s

        lead = cl((self.hp - (tg.hp if tg else self.hp)) / 70)
        u["taunt"] = 0.14 * lead * (1 - threat)
        u["wait"] = 0.09 * self.guard_r + 0.02

        hz_danger, hz_x = 0.0, None
        for h in g.hazards:
            r = h.r + 26
            if h.t < h.warn + h.active_t and abs(h.x - self.x) < r:
                dgr = 1.0 if abs(h.x - self.x) < h.r else 0.5
                if dgr > hz_danger:
                    hz_danger, hz_x = dgr, h.x
        if hz_danger > 0:
            u["in"] *= 1 - 0.8 * hz_danger
            u["jab"] *= 1 - 0.7 * hz_danger
            u["heavy"] *= 1 - 0.7 * hz_danger
            u["block"] *= 0.4
            u["out"] += 0.9 * hz_danger
            u["dodge"] += 1.0 * hz_danger
        self.hz_pending = hz_x

        n = c["noise"]
        best, bs, scored = None, -1.0, []
        for a, val in u.items():
            val = max(0.0, val * random.uniform(1 - n, 1 + n))
            scored.append((a, val))
            if val > bs:
                bs, best = val, a
        scored.sort(key=lambda kv: -kv[1])
        return best, scored[:5]

    def decide(self):
        g = self.game
        self.think_t = random.uniform(0.09, 0.18)
        if self.cls == "WILDCARD" and random.random() < 0.30:
            self.aggr_r = random.uniform(0.2, 1.0)
            self.guard_r = random.uniform(0.1, 0.8)
            self.reflex_r = random.uniform(0.25, 0.9)
        else:
            self.aggr_r, self.guard_r, self.reflex_r = self.cd["aggr"], self.cd["guard"], self.cd["reflex"]
        self.pick_target()
        action, scores = self.utility()
        self.util = scores
        hz_x = self.hz_pending
        self.hz_dir = (-1 if hz_x > self.x else 1) if hz_x is not None else None
        # --- power-up seeking ---
        self.pu_dir = None
        best_pu, best_want = None, 0.0
        for pu in g.powerups:
            if abs(pu.x - self.x) < 280:
                if pu.kind == "heal":
                    want = (1 - self.hp / self.max_hp) * 1.4
                elif pu.kind == "energy":
                    want = 0.7 if self.energy < 70 else 0.15
                else:
                    want = 0.5
                if want > best_want:
                    best_want, best_pu = want, pu
        if best_pu is not None and best_want > 0.4:
            self.pu_dir = 1 if best_pu.x > self.x else -1
        if action == "in":
            self.plan = "in"
            if self.target and abs(self.target.x - self.x) > 240 and random.random() < 0.15:
                self.vz = 300
        elif action == "out":
            self.plan = "out"
        elif action == "jab":
            self.start_attack("jab")
        elif action == "heavy":
            self.start_attack("heavy")
        elif action == "block":
            self.start_block()
        elif action == "dodge":
            if hz_x is not None:
                direction = -1 if hz_x > self.x else 1
            else:
                back_space = (self.x - RING_L) if self.facing == 1 else (RING_R - self.x)
                direction = -self.facing if back_space > 95 else self.facing
            self.do_dodge(direction)
        elif action == "special":
            self.start_cast()
        elif action == "taunt":
            self.start_taunt()
        else:
            self.plan = None

    # ---------- update ----------
    def update(self, dt, act):
        g = self.game
        self.dodge_cd = max(0, self.dodge_cd - dt)
        self.invuln = max(0, self.invuln - dt)
        self.buff_t = max(0, self.buff_t - dt)
        self.shield_t = max(0, self.shield_t - dt)
        self.chill_t = max(0, self.chill_t - dt)
        self.might_t = max(0, self.might_t - dt)
        if self.target is None or self.target.hp <= 0:
            self.pick_target()
        if self.state not in ("dodge", "dash", "ko") and self.target is not None:
            self.facing = 1 if self.target.x >= self.x else -1
        if self.z > 0 or self.vz > 0:
            self.z += self.vz * dt
            self.vz -= 1500 * dt
            if self.z <= 0:
                self.z, self.vz = 0, 0
        st = self.state
        if st == "ko":
            self.ko_t += dt
            if self.ko_t > 0.75 and not self.ghost:
                self.ghost = True
                g.parts.append(Part(self.x, FLOOR - 50, "👻", 0, -55, life=2.2, size=34))
            return
        if st == "win":
            self.win_t += dt
            if random.random() < dt * 3:
                g.parts.append(Part(self.x + random.randint(-40, 40), FLOOR - 130, "✨", 0, -40, life=0.6, size=18))
            return
        if st == "hit":
            self.x += self.vx * dt
            self.vx *= max(0, 1 - 8 * dt)
            if self.t <= 0: self.state = "idle"
        elif st == "dodge":
            self.x += self.vx * dt
            self.vx *= max(0, 1 - 5 * dt)
            if self.t <= 0: self.state = "idle"
        elif st == "windup":
            if self.t <= 0:
                self.state = "active"
                self.t = ACT[self.attack]
                self.vx = self.facing * (150 if self.attack == "jab" else 250)
                if self.attack == "heavy":
                    sfx("whoosh")
                    if self.cls == "SAMURAI":
                        g.parts.append(Part(self.x + self.facing * 40, FLOOR - 90, "⚔", self.facing * 80, -20, life=0.25, size=24))
        elif st == "active":
            self.x += self.vx * dt
            self.try_hit()
            if self.t <= 0:
                self.state = "recover"
                self.t = REC[self.attack]
                self.vx = 0
        elif st == "recover":
            if self.t <= 0:
                if self.combo > 0:
                    self.combo -= 1
                    self.start_attack("jab", fast=True)
                else:
                    self.state = "idle"
        elif st == "block":
            if self.t <= 0: self.state = "idle"
        elif st == "taunt":
            if self.t <= 0: self.state = "idle"
        elif st == "cast":
            if random.random() < 0.5:
                g.parts.append(Part(self.x + random.randint(-26, 26), FLOOR - 60 + random.randint(-40, 20),
                                    "✨", 0, -60, life=0.4, size=14))
            if self.t <= 0: self.fire_special()
        elif st == "dash":
            p = ease_out(clamp(1 - self.t / self.dash_T, 0, 1))
            self.x = lerp(self.volt_from, self.volt_to, p)
            ch = {"VOLT": "⚡", "SLAM": "💨", "DRAIN": "🩸", "IAIDO": "✨"}[self.dash_kind]
            g.parts.append(Part(self.x + random.randint(-14, 14), FLOOR - 70 + random.randint(-20, 20), ch,
                                random.randint(-30, 30), random.randint(-30, 30), life=0.3, size=18))
            if self.t <= 0:
                self.resolve_dash()
                self.state = "idle"
        else:  # idle
            if act:
                self.gain_energy(2.2 * dt)
                for h in g.hazards:
                    if h.t > h.warn - 0.3 and h.t < h.warn and abs(h.x - self.x) < h.r + 24 and self.dodge_cd <= 0:
                        if random.random() < self.reflex_r * 0.85:
                            self.do_dodge(-1 if h.x > self.x else 1)
                            return
                for e in self.foes():
                    if e.state == "windup" and self.react_map.get(id(e)) != e.attack_token and abs(e.x - self.x) < 175:
                        self.react_map[id(e)] = e.attack_token
                        chance = self.reflex_r * (0.85 if e.attack == "heavy" else 0.30)
                        if random.random() < chance:
                            direction = -1 if e.x > self.x else 1
                            if self.dodge_cd <= 0 and random.random() < 0.55:
                                self.do_dodge(direction)
                            else:
                                self.start_block()
                            return
                chilled = self.chill_t > 0
                self.think_t -= dt * (0.7 if chilled else 1.0)
                if self.think_t <= 0:
                    self.decide()
                spd = 205 * self.cd["pace"] * (0.55 if chilled else 1.0) * (0.7 if self.boss else 1.0)
                if self.hz_dir is not None:
                    self.x += self.hz_dir * spd * 1.15 * dt
                elif self.pu_dir is not None:
                    self.x += self.pu_dir * spd * 1.1 * dt
                elif self.plan == "in":
                    self.x += self.facing * spd * dt
                elif self.plan == "out":
                    self.x -= self.facing * spd * 0.8 * dt
        self.t -= dt
        self.x = clamp(self.x, RING_L, RING_R)

    # ---------- draw ----------
    def draw(self, view, t):
        g, f, x, z = self.game, self.facing, self.x, self.z
        gy = FLOOR
        sc = self.boss_scale
        sh = g.shadow
        ssc = 1.0 - min(0.4, z / 240)
        s2 = pygame.transform.smoothscale(sh, (int(92 * sc * ssc), int(20 * ssc)))
        view.blit(s2, (x - s2.get_width() // 2, gy - 9))

        if self.state == "ko":
            p = ease_out(clamp(self.ko_t / 0.5, 0, 1))
            if p < 0.6:
                pygame.draw.rect(view, darken(self.col, 0.45),
                                 (x - int(19 * sc), gy - int(58 * sc) * (1 - p), int(38 * sc), max(2, int(58 * sc) * (1 - p))), border_radius=12)
            head = pygame.transform.rotozoom(self.head_surf, -f * 88 * p, 1)
            view.blit(head, (x - f * 30 * p - head.get_width() // 2, lerp(gy - int(96 * sc), gy - head.get_height() // 3, p) - head.get_height() // 2))
            for i in range(2):
                a = t * 3 + i * math.pi
                ds = get_emoji("💫", 22)
                view.blit(ds, (x + math.cos(a) * (44 * sc) - 11, gy - 44 + math.sin(a) * 14 - 11))
            return

        bob = math.sin(t * 5 + self.index * 2.1) * 3
        bounce = abs(math.sin(self.win_t * 6)) * 24 if self.state == "win" else 0
        zd = z + bounce
        lean = 0
        if self.state == "windup": lean = -f * (9 if self.attack == "heavy" else 4)
        elif self.state == "active": lean = f * (15 if self.attack == "heavy" else 8)
        elif self.state == "hit": lean = -f * 10
        elif self.state == "block": lean = -f * 5

        gl = self.glow
        view.blit(gl, (x - gl.get_width() // 2, gy - int(92 * sc) - zd - gl.get_height() // 2 + bob))
        bx, by = x + lean // 2 - int(19 * sc), gy - int(58 * sc) - zd + bob
        pygame.draw.rect(view, darken(self.col, 0.42), (bx, by, int(38 * sc), int(46 * sc)), border_radius=int(13 * sc))
        pygame.draw.rect(view, self.col, (bx + int(5 * sc), by + int(5 * sc), int(28 * sc), int(36 * sc)), border_radius=int(10 * sc))

        if self.shield_t > 0:
            r = 56 + math.sin(t * 7) * 3
            pygame.draw.circle(view, (120, 210, 255), (x, gy - 70 - zd), int(r), 2)
            view.blit(get_emoji("🛡", 20), (x - 10, gy - 150 - zd))

        hx, hy = x + lean, gy - int(96 * sc) - zd + bob
        if self.state == "hit":
            hx += random.randint(-3, 3)
            hy += random.randint(-2, 2)
        head = self.head_surf
        if self.invuln > 0 and int(t * 30) % 2 == 0:
            head = head.copy(); head.set_alpha(120)
        if self.buff_t > 0:
            ring = pygame.Surface((96, 96), pygame.SRCALPHA)
            pygame.draw.circle(ring, (255, 220, 120, 90), (48, 48), 46, 3)
            view.blit(ring, (hx - 48, hy - 48))
        if self.might_t > 0:
            pygame.draw.circle(view, (255, 170, 110), (hx, hy), int(48 * sc), 2)
            view.blit(get_emoji("💪", 20), (hx - 10, hy - int(58 * sc) + math.sin(t * 7) * 4))
        view.blit(head, (hx - head.get_width() // 2, hy - head.get_height() // 2))

        ext, gs = 0.0, 1.0
        if self.state == "windup":
            p = clamp(1 - self.t / self.wT, 0, 1)
            ext = (-28 if self.attack == "heavy" else -10) * p
        elif self.state == "active":
            p = clamp(1 - self.t / ACT[self.attack], 0, 1)
            R = 72 if self.attack == "jab" else (self.heavy_reach() - 34)
            ext = R * ease_out(p)
            gs = 1.0 if self.attack == "jab" else 1.35
        elif self.state == "recover":
            R = 72 if self.attack == "jab" else (self.heavy_reach() - 34)
            ext = R * clamp(self.t / REC[self.attack], 0, 1)
        gf = self.glove["R"] if f == 1 else self.glove["L"]
        if gs != 1.0:
            gf = pygame.transform.rotozoom(gf, 0, gs)
        if self.state == "win":
            for sgn in (-1, 1):
                view.blit(gf, (x + sgn * int(30 * sc) - gf.get_width() // 2, gy - int(128 * sc) - zd - gf.get_height() // 2))
        elif self.state == "block":
            view.blit(gf, (x + f * int(20 * sc) - gf.get_width() // 2, gy - int(58 * sc) - zd + bob - gf.get_height() // 2))
            view.blit(gf, (x + f * int(14 * sc) - gf.get_width() // 2, gy - int(84 * sc) - zd + bob - gf.get_height() // 2))
        else:
            view.blit(gf, (x + f * int((30 + ext) * sc) - gf.get_width() // 2, gy - int(52 * sc) - zd + bob - gf.get_height() // 2))
            gr = self.glove["L"] if f == 1 else self.glove["R"]
            view.blit(gr, (x - f * int(24 * sc) - gr.get_width() // 2, gy - int(44 * sc) - zd + bob * 0.7 - gr.get_height() // 2))

        if self.state == "block":
            sd = get_emoji("🛡", int(58 * sc))
            view.blit(sd, (x + f * int(46 * sc) - sd.get_width() // 2, gy - int(70 * sc) - zd + bob - sd.get_height() // 2))
        if self.state == "windup" and self.attack == "heavy":
            view.blit(get_emoji("💢", 30), (hx - 15, hy - int(58 * sc)))
        if self.state == "hit":
            d = pygame.transform.rotozoom(get_emoji("💫", 26), t * 300, 1)
            view.blit(d, (hx - d.get_width() // 2, hy - 56))
        if self.state == "taunt":
            pygame.draw.rect(view, (255, 255, 255), (hx - 6, hy - 74, 46, 38), border_radius=10)
            pygame.draw.polygon(view, (255, 255, 255), [(hx + 6, hy - 36), (hx + 18, hy - 36), (hx + 2, hy - 24)])
            view.blit(get_emoji("😤", 26), (hx, hy - 68))
        if self.state == "win":
            tr = get_emoji("🏆", 44)
            view.blit(tr, (x - tr.get_width() // 2, gy - int(176 * sc) - zd + math.sin(self.win_t * 6) * 5))
            view.blit(get_emoji("👑", 30), (hx - 15, hy - 52))
        if self.energy >= 100 and self.state == "idle":
            view.blit(get_emoji("⚡", 24), (hx - 12, hy - 60 + math.sin(t * 8) * 4))
        if self.streak >= 3:
            fs = pygame.transform.rotozoom(get_emoji("🔥", 24), math.sin(t * 12) * 8, 1)
            view.blit(fs, (hx - fs.get_width() // 2, hy - 64 + math.sin(t * 9) * 3))
        if self.chill_t > 0:
            pygame.draw.circle(view, (150, 215, 255), (x, gy - 70 - zd), int(48 * sc), 2)
            view.blit(get_emoji("❄", 18), (hx - 9, hy - 60 + math.sin(t * 6) * 3))
        if self.boss:
            view.blit(get_emoji("👹", 22), (hx - 11, hy - int(64 * sc) + math.sin(t * 5) * 3))

# ---------------------------------------------------------------- game
class Game:
    def __init__(self):
        self.parts, self.texts, self.projectiles, self.bombs, self.hazards, self.powerups = [], [], [], [], [], []
        self.shake, self.freeze, self.ex = 0.0, 0.0, 0.15
        self.msgs, self.banner = [], None
        self.phase, self.pt, self.age = "intro", 0.0, 0.0
        self.round, self.rtime = 1, 60.0
        self.paused, self.slowmo, self.show_ai = False, False, False
        self.hazards_on = True
        self.hazard_t, self.pu_t = 5.0, 6.0
        self.speed = 1
        self.chatter_t = 6.0
        self._fight_announced = False
        self.mode, self.n_ffa, self.n_team = "duel", 4, 3
        self.team_wins = [0, 0]
        self.round_winner, self.match_winner = None, None
        self.fighters = []
        self.tour = None
        self.arena = ARENA_THEMES["NEON CITY"]
        self.hazard_kind = "surge"
        self.view = pygame.Surface((W, H))
        self._build_crowd()
        sh = pygame.Surface((92, 20), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (5, 6, 16, 110), (0, 0, 92, 20))
        self.shadow = sh
        self.dim = pygame.Surface((W, H))
        self.dim.fill((8, 8, 20)); self.dim.set_alpha(205)
        self.plate_bg = pygame.Surface((346, 70), pygame.SRCALPHA)
        pygame.draw.rect(self.plate_bg, (16, 16, 34, 210), (0, 0, 346, 70), border_radius=12)
        pygame.draw.rect(self.plate_bg, (80, 85, 130), (0, 0, 346, 70), 2, border_radius=12)
        self.chip_bg = pygame.Surface((150, 36), pygame.SRCALPHA)
        pygame.draw.rect(self.chip_bg, (16, 16, 34, 210), (0, 0, 150, 36), border_radius=9)
        self.new_match()

    def _build_crowd(self):
        self.crowd = []
        for row, y0 in enumerate((150, 182)):
            for x in range(24, W - 20, 30):
                self.crowd.append(dict(x=x + random.randint(-6, 6), y0=y0 + random.randint(-4, 4),
                                       ch=random.choice(CROWD_FACES), phase=random.uniform(0, 6.28),
                                       spd=random.uniform(2.2, 3.6)))
        for c in self.crowd:
            c["surf"] = get_emoji(c["ch"], 26)

    # ---------- procedural arena ----------
    def gen_arena(self):
        name = random.choice(list(ARENA_THEMES))
        th = dict(ARENA_THEMES[name])
        th["name"] = name
        self.arena = th
        self.hazard_kind = th["hazard"]
        self.hazards = []
        bg = pygame.Surface((W, H))
        top, bot = th["sky"]
        for y in range(H):
            t = y / H
            bg.fill((int(lerp(top[0], bot[0], t)), int(lerp(top[1], bot[1], t)), int(lerp(top[2], bot[2], t))), (0, y, W, 1))

        b = th["build"]
        if b == "city":
            mx = random.randint(120, W - 120)
            pygame.draw.circle(bg, (240, 235, 220), (mx, 44), 24)
            pygame.draw.circle(bg, (205, 200, 185), (mx - 8, 38), 5)
            pygame.draw.circle(bg, (205, 200, 185), (mx + 7, 50), 4)
            x = 0
            while x < W:
                bw = random.randint(34, 72)
                bh = random.randint(34, 96)
                col = (random.randint(16, 26), random.randint(14, 22), random.randint(36, 52))
                pygame.draw.rect(bg, col, (x, 122 - bh, bw, bh))
                for _ in range(random.randint(3, 8)):
                    wx = x + random.randint(4, max(5, bw - 8))
                    wy = 122 - bh + random.randint(4, max(5, bh - 8))
                    pygame.draw.rect(bg, random.choice([(255, 220, 120), (120, 220, 255), (255, 120, 190)]), (wx, wy, 3, 3))
                if random.random() < 0.3:
                    pygame.draw.line(bg, (80, 80, 110), (x + bw // 2, 122 - bh), (x + bw // 2, 122 - bh - 10), 2)
                x += bw + random.randint(2, 10)
        elif b == "volcano":
            pygame.draw.polygon(bg, (40, 16, 16), [(0, 122), (int(W * 0.2), 70), (int(W * 0.45), 122)])
            vx = random.randint(int(W * 0.5), int(W * 0.72))
            pygame.draw.polygon(bg, (52, 22, 20), [(vx - 150, 122), (vx - 20, 26), (vx + 10, 26), (vx + 160, 122)])
            pygame.draw.circle(bg, (255, 140, 50), (vx - 5, 30), 10)
            pygame.draw.circle(bg, (255, 220, 120), (vx - 5, 30), 5)
            for i in range(3):
                sx = vx - 5 + random.randint(-8, 8)
                pygame.draw.lines(bg, (255, 120, 50), False,
                                  [(sx, 36), (sx + random.randint(-22, 22), 72), (sx + random.randint(-32, 32), 122)], 3)
            for _ in range(30):
                pygame.draw.circle(bg, (255, 150, 80), (random.randint(0, W), random.randint(0, 118)), 1)
        elif b == "mountains":
            def ridge(col, lo, hi, caps):
                pts = [(0, 122)]
                x = 0
                while x < W:
                    x += random.randint(70, 140)
                    pts.append((x, random.randint(lo, hi)))
                pts.append((W, 122))
                pygame.draw.polygon(bg, col, pts)
                if caps:
                    for p in pts[1:-1]:
                        pygame.draw.polygon(bg, (235, 245, 255),
                                            [(p[0] - 14, p[1] + 12), (p[0], p[1]), (p[0] + 14, p[1] + 12)])
            ridge((70, 100, 150), 38, 90, False)
            ridge((95, 130, 180), 58, 108, True)
        elif b == "space":
            for _ in range(90):
                pygame.draw.circle(bg, (255, 255, 255), (random.randint(0, W), random.randint(0, 118)), random.choice((1, 1, 2)))
            for _ in range(4):
                nc = random.choice([(60, 40, 110), (30, 60, 120), (90, 40, 90)])
                ns = pygame.Surface((160, 90), pygame.SRCALPHA)
                pygame.draw.ellipse(ns, (*nc, 42), (0, 0, 160, 90))
                bg.blit(ns, (random.randint(0, W - 160), random.randint(0, 55)))
            px, py = random.randint(140, W - 140), random.randint(30, 78)
            pr = random.randint(14, 24)
            pcol = random.choice([(220, 160, 120), (140, 190, 230), (230, 200, 140), (170, 140, 220)])
            if random.random() < 0.6:
                rs = pygame.Surface((pr * 5, pr * 2), pygame.SRCALPHA)
                rc = tuple(min(255, c + 70) for c in pcol)
                pygame.draw.ellipse(rs, (*rc, 190), (0, 0, pr * 5, pr * 2), 2)
                rs = pygame.transform.rotozoom(rs, random.randint(-25, 25), 1)
                bg.blit(rs, (px - rs.get_width() // 2, py - rs.get_height() // 2))
            pygame.draw.circle(bg, pcol, (px, py), pr)
        elif b == "spooky":
            pygame.draw.circle(bg, (250, 240, 205), (random.randint(140, W - 140), 44), 34)
            pygame.draw.polygon(bg, (22, 14, 34), [(0, 122), (int(W * 0.3), 86), (int(W * 0.6), 122)])
            pygame.draw.polygon(bg, (26, 16, 40), [(int(W * 0.5), 122), (int(W * 0.8), 80), (W, 122)])
            for _ in range(4):
                tx = random.randint(30, W - 30)
                th_ = random.randint(30, 60)
                pygame.draw.line(bg, (20, 12, 26), (tx, 122), (tx, 122 - th_), 4)
                for _ in range(3):
                    by = 122 - th_ + random.randint(6, max(7, th_ - 6))
                    pygame.draw.line(bg, (20, 12, 26), (tx, by),
                                     (tx + random.choice((-1, 1)) * random.randint(8, 18), by - random.randint(6, 14)), 3)
            for _ in range(5):
                bx, by = random.randint(0, W), random.randint(20, 90)
                pygame.draw.lines(bg, (30, 20, 44), False, [(bx - 6, by), (bx, by + 3), (bx + 6, by)], 2)
        elif b == "jungle":
            x = 0
            while x < W + 30:
                r = random.randint(18, 34)
                pygame.draw.circle(bg, (random.randint(18, 30), random.randint(50, 70), random.randint(24, 38)), (x, 122 - r // 2), r)
                x += random.randint(20, 36)
            for _ in range(8):
                fx = random.randint(70, W - 70)
                for a in range(-2, 3):
                    ang = -math.pi / 2 + a * 0.35
                    ex = fx + math.cos(ang) * random.randint(18, 30)
                    ey = 302 + math.sin(ang) * random.randint(18, 30)
                    pygame.draw.line(bg, (40, 90, 48), (fx, 302), (ex, ey), 3)

        pygame.draw.rect(bg, th["stand"], (0, 122, W, 92))
        pygame.draw.rect(bg, th["wall"], (0, 214, W, 14))
        for i, lx in enumerate(range(12, W, 26)):
            c = th["bulbs"][i % len(th["bulbs"])]
            pygame.draw.circle(bg, c, (lx, 118), 3)
            halo = pygame.Surface((14, 14), pygame.SRCALPHA)
            pygame.draw.circle(halo, (*c, 55), (7, 7), 7)
            bg.blit(halo, (lx - 7, 111))
        marquees = [f"🎪 {name} ARENA 🎪", "🍿 TONIGHT: AI vs AI 🍿", "⚔ BATTLE NIGHT ⚔", "🔥 NO MERCY 🔥"]
        bn = rich_render(random.choice(marquees), 18, (160, 150, 210))
        bg.blit(bn, (W // 2 - bn.get_width() // 2, 215))

        for i in range(random.randint(7, 10)):
            ch = random.choice(th["props"])
            sz = random.randint(26, 44)
            surf = get_emoji(ch, sz).copy()
            surf.set_alpha(235)
            px = random.randint(80, W - 80)
            py = random.randint(238, 288)
            bg.blit(surf, (px - sz // 2, py - sz // 2))

        matrect = pygame.Rect(60, 306, W - 120, H - 306 - 44)
        pygame.draw.rect(bg, th["mat"], matrect, border_radius=26)
        ov = pygame.Surface((matrect.w, matrect.h), pygame.SRCALPHA)
        c = (*th["matline"], 26)
        pat = random.choice(["plain", "stripes", "checker", "burst"])
        if pat == "stripes":
            for x in range(0, matrect.w, 48):
                pygame.draw.rect(ov, c, (x, 0, 24, matrect.h))
        elif pat == "checker":
            for x in range(0, matrect.w, 44):
                for y in range(0, matrect.h, 44):
                    if (x // 44 + y // 44) % 2 == 0:
                        pygame.draw.rect(ov, c, (x, y, 44, 44))
        elif pat == "burst":
            cx0, cy0 = matrect.w // 2, matrect.h // 2
            for i in range(14):
                a = math.pi * 2 * i / 14
                a2 = a + math.pi / 14
                pygame.draw.polygon(ov, c, [(cx0, cy0),
                                            (cx0 + math.cos(a) * 700, cy0 + math.sin(a) * 700),
                                            (cx0 + math.cos(a2) * 700, cy0 + math.sin(a2) * 700)])
        mask = pygame.Surface((matrect.w, matrect.h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255), (0, 0, matrect.w, matrect.h), border_radius=26)
        ov.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        bg.blit(ov, matrect.topleft)
        pygame.draw.rect(bg, th["matline"], matrect, 3, border_radius=26)
        emb = get_emoji(random.choice(th["emblem"]), 64).copy()
        emb.set_alpha(110)
        bg.blit(emb, (W // 2 - 32, FLOOR - 48))
        pygame.draw.ellipse(bg, th["matline"], (W // 2 - 90, FLOOR - 26, 180, 52), 3)

        topper = random.choice(th["props"])
        for px in (108, W - 108):
            pygame.draw.rect(bg, th["posts"], (px - 4, FLOOR - 104, 8, 108), border_radius=3)
            tp = get_emoji(topper, 18)
            bg.blit(tp, (px - 9, FLOOR - 122))
        for ry, rc in ((FLOOR - 88, th["ropes"][0]), (FLOOR - 52, th["ropes"][1])):
            pygame.draw.line(bg, rc, (108, ry), (W - 108, ry), 3)
        pygame.draw.line(bg, th["glow"], (0, FLOOR + 26), (W, FLOOR + 26), 2)
        pygame.draw.rect(bg, darken(th["wall"], 0.6), (0, H - 40, W, 40))
        self.bg = bg

    # ---------- match flow ----------
    def new_match(self):
        self.gen_arena()
        self.tour = None
        mode = self.mode
        if mode == "duel":
            total, teams, xs = 2, [0, 1], [W * 0.32, W * 0.68]
        elif mode == "boss":
            total, teams, xs = 2, [0, 1], [W * 0.30, W * 0.72]
        elif mode == "ffa":
            n = self.n_ffa
            total = n
            teams = list(range(n))
            xs = [lerp(W * 0.18, W * 0.82, i / max(1, n - 1)) for i in range(n)]
        else:
            k = self.n_team
            total = 2 * k
            teams = [0] * k + [1] * k
            xs = [W * 0.20 + i * 46 for i in range(k)] + [W * 0.80 - i * 46 for i in range(k)]
        heads = random.sample(HEADS, total)
        clist = random.sample(list(CLASSES), total)
        self.fighters = [Fighter(self, i, teams[i], heads[i], clist[i], xs[i]) for i in range(total)]
        if mode == "boss":
            self.fighters[1].make_boss()
        for f in self.fighters:
            f.pick_target()
        if mode in ("duel", "boss"):
            self.f1, self.f2 = self.fighters[0], self.fighters[1]
        self.round = 1
        self.team_wins = [0, 0]
        self.round_winner, self.match_winner = None, None
        self.parts.clear(); self.texts.clear(); self.projectiles.clear(); self.bombs.clear()
        self.hazards = []
        self.powerups = []
        self.hazard_t = random.uniform(3, 5)
        self.pu_t = random.uniform(4, 7)
        self.msgs.clear()
        self.phase, self.pt = "intro", 0.0
        label = MODE_LABEL[mode]
        if mode == "ffa":
            label += f" — {total} WARRIORS"
        elif mode == "team":
            label += f" — {self.n_team} vs {self.n_team}"
        self.say(f"🥊 {label} — FIGHT!")
        self.say(f"🎪 ARENA: {self.arena['name']}")
        if mode == "boss":
            self.say(f"👹 BOSS: {self.fighters[1].name} — HP {self.fighters[1].max_hp}!")
            self.say(f"🦸 HERO: {self.fighters[0].name} — good luck!")
        sfx("bell")

    def start_round(self, advance=False):
        if advance:
            self.round += 1
        for f in self.fighters:
            f.hp = float(f.max_hp)
            f.energy = 0.0
            f.x = f.x0
            f.state, f.t, f.plan = "idle", 0, None
            f.vx, f.z, f.vz, f.combo, f.buff_t, f.shield_t, f.might_t = 0, 0, 0, 0, 0, 0, 0
            f.streak, f.chill_t = 0, 0.0
            f.ko_t, f.win_t, f.ghost, f.attack = 0, 0, False, None
            f.util, f.target, f.react_map = [], None, {}
            f.pu_dir, f.hz_dir = None, None
        for f in self.fighters:
            f.pick_target()
        self.projectiles.clear(); self.bombs.clear()
        self.hazards = []
        self.powerups = []
        self.hazard_t = random.uniform(3, 5)
        self.pu_t = random.uniform(4, 7)
        self.rtime = 60.0
        self.phase, self.pt = "round_in", 0.0
        self._fight_announced = False
        self.set_banner(f"ROUND {self.round}", (255, 255, 255), 0.85, size=54)
        sfx("bell")

    # ---------- tournament ----------
    def start_tournament(self):
        self.gen_arena()
        heads = random.sample(HEADS, 8)
        clist = random.sample(list(CLASSES), 8)
        specs = [dict(head=h, cls=c) for h, c in zip(heads, clist)]
        random.shuffle(specs)
        self.tour = dict(bracket=[], alive=specs, next=[], idx=0, champion=None)
        self.mode = "duel"
        self.say("🏆 TOURNAMENT — 8 CHALLENGERS ENTER!")
        self.say(f"🎪 STAGE: {self.arena['name']} (fixed)")
        self._tour_round_start()

    def _tour_round_start(self):
        alive = self.tour["alive"]
        pairs = [dict(a=alive[i], b=alive[i + 1], winner=None) for i in range(0, len(alive), 2)]
        self.tour["bracket"].append(pairs)
        self.tour["idx"] = 0
        self.tour["next"] = []
        label = {4: "QUARTERFINALS", 2: "SEMIFINALS", 1: "GRAND FINAL"}.get(len(pairs), "ROUND")
        self.say(f"🏆 {label}!")
        self._tour_load()

    def _tour_load(self):
        pairs = self.tour["bracket"][-1]
        m = pairs[self.tour["idx"]]
        self._setup_duel(m["a"], m["b"])
        self.say(f"NEXT ⚔ {m['a']['head'][0]} vs {m['b']['head'][0]}")

    def _setup_duel(self, specA, specB):
        self.mode = "duel"
        self.fighters = [Fighter(self, 0, 0, specA["head"], specA["cls"], W * 0.32),
                         Fighter(self, 1, 1, specB["head"], specB["cls"], W * 0.68)]
        self.fighters[0].spec, self.fighters[1].spec = specA, specB
        for f in self.fighters:
            f.pick_target()
        self.f1, self.f2 = self.fighters
        self.round = 1
        self.team_wins = [0, 0]
        self.round_winner, self.match_winner = None, None
        self.parts.clear(); self.texts.clear(); self.projectiles.clear(); self.bombs.clear()
        self.hazards = []
        self.powerups = []
        self.hazard_t = random.uniform(3, 5)
        self.pu_t = random.uniform(4, 7)
        self.phase, self.pt = "intro", 0.0
        sfx("bell")

    def _tour_match_done(self):
        kind, obj = self.match_winner
        pairs = self.tour["bracket"][-1]
        m = pairs[self.tour["idx"]]
        m["winner"] = 0 if obj is self.f1 else 1
        self.tour["next"].append(obj.spec)
        self.tour["idx"] += 1
        if self.tour["idx"] < len(pairs):
            self._tour_load()
            return
        winners = self.tour["next"]
        if len(winners) == 1:
            self.tour["champion"] = winners[0]
            self.phase, self.pt = "champ", 0.0
            self.set_banner(f"{winners[0]['head'][0]} IS CHAMPION! 🏆", (255, 210, 90), 7.5,
                            sub="TOURNAMENT COMPLETE — new bracket incoming…")
            self.say(f"👑 {winners[0]['head'][0]} TAKES THE TOURNAMENT!")
            self.confetti(150)
            sfx("cheer")
        else:
            self.tour["alive"] = winners
            self._tour_round_start()

    def set_banner(self, text, color, dur, sub=None, size=58):
        main = rich_render(text, size, color)
        sub_s = rich_render(sub, 20) if sub else None
        self.banner = [main, sub_s, 0.0, dur]

    def say(self, text):
        self.msgs.append([text, self.age])
        self.msgs = self.msgs[-4:]

    def burst(self, x, y, big=False):
        for ch, n, sz in (("💥", 1, 44 if big else 30), ("✨", 5 if big else 3, 18)):
            for _ in range(n):
                self.parts.append(Part(x + random.randint(-8, 8), y + random.randint(-8, 8), ch,
                                       random.randint(-90, 90), random.randint(-120, 40), 200,
                                       life=random.uniform(0.3, 0.6), size=sz, spin=random.randint(-300, 300)))
        for _ in range(6 if big else 3):
            self.parts.append(Part(x, y, None, random.randint(-160, 160), random.randint(-160, 60), 300,
                                   life=0.4, color=(255, 220, 130), r=3))

    # ---------- multi-fighter flow ----------
    def round_over(self):
        return len(set(f.team for f in self.fighters if f.hp > 0)) <= 1

    def do_ko(self, loser, src=None):
        if self.phase != "fight":
            return
        loser.hp, loser.state, loser.plan = 0, "ko", None
        loser.ko_t = 0.0
        if src is not None:
            src.stats["ko"] += 1
        killer = src.name if src is not None else "THE ARENA"
        self.say(random.choice(KO_L).format(w=killer, l=loser.name))
        self.shake = max(self.shake, 12)
        self.ex = min(1.0, self.ex + 0.3)
        sfx("ko")
        if self.round_over():
            self.end_round()

    def end_round(self):
        survivors = [f for f in self.fighters if f.hp > 0]
        self.phase, self.pt = "rend", 0.0
        self.projectiles.clear(); self.bombs.clear()
        self.hazards = []
        self.powerups = []
        for f in survivors:
            f.state, f.win_t, f.plan = "win", 0.0, None
        for f in self.fighters:
            if f.hp <= 0:
                f.state = "ko"
        t = survivors[0].team if survivors else 0
        if self.mode == "team":
            self.round_winner = ("team", t)
            self.set_banner("K.O.!!", (255, 90, 80), 2.0,
                            sub=f"{TEAM_ICONS[t]} TEAM {TEAM_NAMES[t]} takes round {self.round}")
        else:
            w = survivors[0]
            self.round_winner = ("fighter", w)
            if self.mode == "boss":
                sub = "THE BOSS BATTLE ENDS!"
            elif self.mode == "ffa":
                sub = f"{w.name} is LAST ONE STANDING"
            else:
                sub = f"{w.name} takes round {self.round}"
            self.set_banner("K.O.!!", (255, 90, 80), 2.0, sub=sub)
        self.ex = 1.0
        sfx("cheer")

    def time_up(self):
        self.say("⏱ TIME! health decides it")
        if self.mode == "team":
            hp = [sum(f.hp for f in self.fighters if f.team == i and f.hp > 0) for i in (0, 1)]
            wt = 0 if hp[0] >= hp[1] else 1
            for f in self.fighters:
                if f.team != wt and f.hp > 0:
                    f.hp, f.state = 0, "ko"
        else:
            alive = [f for f in self.fighters if f.hp > 0]
            best = max(alive, key=lambda f: f.hp)
            for f in alive:
                if f is not best:
                    f.hp, f.state = 0, "ko"
        self.end_round()

    def award_round(self):
        kind, obj = self.round_winner
        need = 1 if self.mode == "boss" else 2
        if kind == "team":
            self.team_wins[obj] += 1
            done = self.team_wins[obj] >= need
        else:
            obj.wins += 1
            done = obj.wins >= need
        if not done:
            self.start_round(advance=True)
            return
        self.match_winner = self.round_winner
        self.phase, self.pt = "mend", 0.0
        if self.mode == "boss":
            if obj.boss:
                self.set_banner("💀 THE HERO FALLS!", (255, 120, 90), 9, sub="THE BOSS REIGNS — new challenger incoming…")
                self.say("👹 THE BOSS IS VICTORIOUS!")
            else:
                self.set_banner("🎉 BOSS DEFEATED!", (255, 210, 90), 9, sub=f"{obj.name} saves the arena — new challenger incoming…")
                self.say(f"🦸 {obj.name} SLAYS THE BOSS!")
        elif kind == "team":
            self.set_banner(f"{TEAM_ICONS[obj]} TEAM {TEAM_NAMES[obj]} WINS!", (255, 210, 90), 9,
                            sub=f"match {self.team_wins[0]}–{self.team_wins[1]} 🏆 new challengers incoming…")
            self.say(f"TEAM {TEAM_NAMES[obj]} TAKES THE MATCH 👑")
        else:
            sub = "CHAMPION OF THE MELEE 🏆 new challengers incoming…" if self.mode == "ffa" \
                  else f"match {obj.wins}–{2 - obj.wins} 🏆 new challengers incoming…"
            self.set_banner(f"{obj.name} WINS!", (255, 210, 90), 9, sub=sub)
            self.say(f"{obj.name} TAKES THE MATCH 👑")
        self.confetti(130)
        sfx("cheer")

    def confetti(self, n):
        for _ in range(n):
            self.parts.append(Part(random.randint(0, W), random.randint(-40, 0), None,
                                   random.randint(-40, 40), random.randint(60, 170), 120,
                                   life=random.uniform(2.5, 4.5),
                                   color=random.choice([(255, 120, 120), (255, 220, 110), (130, 230, 150), (130, 190, 255), (250, 150, 230)]),
                                   r=random.randint(2, 4), rect=True))

    # ---------- update ----------
    def update(self, dt):
        dt *= self.speed
        self.age += dt
        self.pt += dt
        if self.banner:
            self.banner[2] += dt
            if self.banner[2] > self.banner[3]:
                self.banner = None
        self.shake = max(0, self.shake - 42 * dt)

        if self.phase == "intro":
            if self.pt > (3.6 if self.tour else 3.0):
                self.start_round()
        elif self.phase == "round_in":
            if self.pt > 0.9 and not self._fight_announced:
                self._fight_announced = True
                self.set_banner("FIGHT! 🥊", (255, 220, 90), 0.7, size=64)
                sfx("bell")
            if self.pt > 1.6:
                self.phase = "fight"
        elif self.phase == "fight":
            if self.freeze > 0:
                self.freeze -= dt
            else:
                wdt = dt * (0.35 if self.slowmo else 1.0)
                self.world(wdt, act=True)
                self.rtime -= wdt
                if self.rtime <= 0 and self.phase == "fight":
                    self.time_up()
                self.chatter_t -= dt
                if self.chatter_t <= 0:
                    self.chatter_t = random.uniform(6, 11)
                    if random.random() < 0.6:
                        self.say(random.choice(CHATTER))
        elif self.phase == "rend":
            self.world(dt * (0.25 if self.pt < 0.9 else 1.0), act=False)
            if self.pt > 2.6:
                self.award_round()
        elif self.phase == "mend":
            self.world(dt, act=False)
            if int(self.pt * 2) != int((self.pt - dt) * 2):
                self.parts.append(Part(random.randint(120, W - 120), random.randint(70, 190), "🎆", 0, -15,
                                       life=0.9, size=random.randint(40, 64), spin=random.randint(-60, 60)))
                self.confetti(8)
            if self.pt > 5.5:
                if self.tour:
                    self._tour_match_done()
                else:
                    self.new_match()
        elif self.phase == "champ":
            self.world(dt, act=False)
            if int(self.pt * 2) != int((self.pt - dt) * 2):
                self.parts.append(Part(random.randint(120, W - 120), random.randint(70, 190), "🎆", 0, -15,
                                       life=0.9, size=random.randint(40, 64), spin=random.randint(-60, 60)))
                self.confetti(10)
            if self.pt > 8.0:
                self.tour = None
                self.new_match()

        self.ex = max(0.12, self.ex - 0.22 * dt)

    def world(self, dt, act):
        for f in self.fighters:
            f.update(dt, act)
        fs = self.fighters
        for i in range(len(fs)):
            for j in range(i + 1, len(fs)):
                a, b = fs[i], fs[j]
                if a.state in ("dodge", "dash", "ko") or b.state in ("dodge", "dash", "ko"):
                    continue
                mind = int(62 * (a.boss_scale + b.boss_scale) / 2)
                d = b.x - a.x
                if abs(d) < mind:
                    push = (mind - abs(d)) / 2
                    s = 1 if d >= 0 else -1
                    a.x = clamp(a.x - push * s, RING_L, RING_R)
                    b.x = clamp(b.x + push * s, RING_L, RING_R)
        for p in self.projectiles[:]:
            p.update(dt, self)
            if p.dead:
                self.projectiles.remove(p)
        for b in self.bombs[:]:
            b.update(dt, self)
            if b.dead:
                self.bombs.remove(b)
        if act and self.hazards_on:
            self.hazard_t -= dt
            if self.hazard_t <= 0 and len(self.hazards) < 3:
                self.hazard_t = random.uniform(3.5, 7.0)
                if random.random() < 0.6:
                    f = random.choice(self.fighters)
                    hx = clamp(f.x + random.randint(-70, 70), RING_L + 30, RING_R - 30)
                else:
                    hx = random.randint(RING_L + 30, RING_R - 30)
                self.hazards.append(Hazard(self.hazard_kind, hx))
                sfx("dash")
        for h in self.hazards[:]:
            h.update(dt, self)
            if h.done:
                self.hazards.remove(h)
        # power-ups
        if act:
            self.pu_t -= dt
            if self.pu_t <= 0 and len(self.powerups) < 2:
                self.pu_t = random.uniform(7, 12)
                kind = random.choices(["heal", "energy", "might"], weights=[35, 35, 30])[0]
                self.powerups.append(PowerUp(kind, random.randint(RING_L + 40, RING_R - 40)))
        for pu in self.powerups[:]:
            pu.update(dt, self)
            if pu.done:
                self.powerups.remove(pu)
                continue
            for f in self.fighters:
                if f.hp > 0 and f.state != "ko" and abs(f.x - pu.x) < 38:
                    if pu.kind == "heal":
                        h = int(min(22, f.max_hp - f.hp))
                        f.hp += h
                        self.texts.append(Ftext(f.x, FLOOR - 140, f"+{h} ❤", (140, 255, 160), 18))
                        sfx("heal")
                    elif pu.kind == "energy":
                        f.energy = 100
                        self.texts.append(Ftext(f.x, FLOOR - 140, "⚡ FULL ENERGY", (255, 240, 140), 16))
                        sfx("charge")
                    else:
                        f.might_t = 5.0
                        self.texts.append(Ftext(f.x, FLOOR - 140, "💪 MIGHT!", (255, 170, 120), 18))
                        sfx("heavy")
                    if random.random() < 0.5:
                        self.say(f"{f.name} grabs the {PU_INFO[pu.kind][1]} {PU_INFO[pu.kind][0]}")
                    self.ex = min(1.0, self.ex + 0.1)
                    self.burst(pu.x, FLOOR - 60)
                    pu.done = True
                    break
        for p in self.parts[:]:
            p.update(dt)
            if p.dead:
                self.parts.remove(p)
        for t in self.texts[:]:
            t.update(dt)
            if t.dead:
                self.texts.remove(t)
        if self.ex > 0.55 and random.random() < dt * 6:
            c = random.choice(self.crowd)
            self.parts.append(Part(c["x"], c["y0"] - 20, "✨", 0, -30, life=0.5, size=14))
        if self.ex > 0.5 and random.random() < dt * 4:
            c = random.choice(self.crowd)
            self.parts.append(Part(c["x"], c["y0"] - 24, "📸", 0, -25, life=0.45, size=18))
            self.parts.append(Part(c["x"], c["y0"] - 28, None, 0, -20, life=0.15, color=(255, 255, 255), r=6))
        amb = self.arena.get("ambient")
        if amb == "embers" and random.random() < dt * 5:
            self.parts.append(Part(random.randint(60, W - 60), random.randint(FLOOR - 40, FLOOR + 20), None,
                                   random.randint(-15, 15), -random.randint(30, 70), -20,
                                   life=random.uniform(0.8, 1.6),
                                   color=random.choice([(255, 160, 70), (255, 120, 50), (255, 210, 110)]), r=2))
        elif amb == "snow" and random.random() < dt * 8:
            self.parts.append(Part(random.randint(0, W), -10, "❄", random.randint(-20, 20), random.randint(35, 75), 0,
                                   life=8.0, size=random.randint(10, 16), spin=random.randint(-80, 80)))
        elif amb == "stars" and random.random() < dt * 0.5:
            self.parts.append(Part(random.randint(W // 2, W), random.randint(20, 120), "🌠",
                                   -random.randint(320, 520), random.randint(90, 150), 0, life=0.9, size=26))
        elif amb == "leaves" and random.random() < dt * 2:
            self.parts.append(Part(random.randint(0, W), -10, "🍃", random.randint(-30, 30), random.randint(25, 55), 0,
                                   life=9.0, size=random.randint(12, 18), spin=random.randint(-140, 140)))
        elif amb == "spook" and random.random() < dt * 0.3:
            sx, svx = random.choice([(30, 25), (W - 30, -25)])
            self.parts.append(Part(sx, random.randint(150, 320), "👻", svx, random.randint(-15, -5), 0, life=6.0, size=24))
        elif amb == "glitter" and random.random() < dt * 1.5:
            self.parts.append(Part(random.randint(0, W), random.randint(10, 110), "✨", 0, 10, 0, life=1.2, size=12))

    # ---------- draw ----------
    def draw_ai_debug(self, v, f):
        rows = getattr(f, "util", None)
        if not rows:
            return
        maxs = max(s for _, s in rows) or 1.0
        pw, rh = 168, 15
        px = clamp(int(f.x) - pw // 2, 8, W - pw - 8)
        py = int(FLOOR - 230 - f.z)
        if f.target is not None:
            hd = rich_render(f"🎯 {f.target.name}", 11, (220, 220, 240))
            v.blit(hd, (px, py - 15))
        panel = pygame.Surface((pw, rh * len(rows) + 10), pygame.SRCALPHA)
        pygame.draw.rect(panel, (10, 10, 26, 215), (0, 0, pw, rh * len(rows) + 10), border_radius=8)
        pygame.draw.rect(panel, (*f.col, 160), (0, 0, pw, rh * len(rows) + 10), 1, border_radius=8)
        for i, (a, s) in enumerate(rows):
            ch, col = ACT_META.get(a, ("⏸", (200, 200, 200)))
            y = 6 + i * rh
            panel.blit(get_emoji(ch, 12), (5, y))
            bw = int(92 * clamp(s / maxs, 0.04, 1))
            pygame.draw.rect(panel, (40, 40, 60), (24, y + 1, 92, 9), border_radius=4)
            pygame.draw.rect(panel, col if i else (255, 255, 255), (24, y + 1, bw, 9), border_radius=4)
            num = ui_font(10).render(f"{s:.2f}", True, (210, 210, 230) if i else (255, 255, 255))
            panel.blit(num, (122, y - 1))
        v.blit(panel, (px, py))

    def draw_plate(self, v, f, x):
        v.blit(self.plate_bg, (x, 10))
        v.blit(get_emoji(f.head, 44), (x + 12, 22))
        v.blit(rich_render(f.name, 19, (255, 255, 255)), (x + 64, 16))
        tag = rich_render(f"{f.cd['icon']} {f.cls} · {SPECIALS[f.special][0]} {SPECIALS[f.special][1]}", 12, (150, 155, 190))
        v.blit(tag, (x + 64, 40))
        bx, bw = x + 64, 268
        r = clamp(f.hp / f.max_hp, 0, 1)
        pygame.draw.rect(v, (24, 22, 40), (bx - 1, 58, bw + 2, 12), border_radius=6)
        if r > 0:
            col = (int(lerp(235, 90, r)), int(lerp(70, 230, r)), int(lerp(60, 120, r)))
            pygame.draw.rect(v, col, (bx, 59, int(bw * r), 10), border_radius=5)
        pygame.draw.rect(v, (90, 90, 130), (bx - 1, 58, bw + 2, 12), 1, border_radius=6)
        v.blit(get_emoji("❤", 14), (bx - 22, 56))
        if 0 < f.hp < f.max_hp * 0.25:
            hb = pygame.transform.rotozoom(get_emoji("💔", 16), 0, 1 + 0.15 * math.sin(self.age * 8))
            v.blit(hb, (bx + bw + 6, 54))
        er = clamp(f.energy / 100, 0, 1)
        pygame.draw.rect(v, (24, 22, 40), (bx - 1, 73, bw + 2, 6), border_radius=3)
        ecol = (255, 240, 140) if er >= 1 else (95, 200, 255)
        if er > 0:
            pygame.draw.rect(v, ecol, (bx, 74, int(bw * er), 4), border_radius=2)
        if er >= 1 and int(self.age * 4) % 2 == 0:
            v.blit(get_emoji("⚡", 14), (bx + bw + 4, 68))
        for i in range(2):
            px = bx + bw - 14 - i * 16
            if f.wins > i:
                v.blit(get_emoji("⭐", 14), (px - 7, 17))
            else:
                pygame.draw.circle(v, (40, 40, 62), (px, 24), 6)
                pygame.draw.circle(v, (200, 200, 230), (px, 24), 6, 1)

    def draw_chip(self, v, f, x, y):
        dead = f.hp <= 0
        ch = self.chip_bg.copy()
        bc = TEAM_COLS[f.team] if self.mode == "team" else f.col
        if dead:
            bc = (90, 90, 100)
        pygame.draw.rect(ch, bc, (0, 0, 150, 36), 2, border_radius=9)
        v.blit(ch, (x, y))
        head = get_emoji(f.head, 24)
        if dead:
            head = head.copy(); head.set_alpha(90)
        v.blit(head, (x + 5, y + 6))
        if dead:
            v.blit(get_emoji("💀", 16), (x + 9, y + 10))
        nm = ui_font(11).render(f.name[:12], True, (255, 255, 255) if not dead else (120, 120, 130))
        v.blit(nm, (x + 33, y + 2))
        r = clamp(f.hp / f.max_hp, 0, 1)
        pygame.draw.rect(v, (24, 22, 40), (x + 33, y + 17, 86, 7), border_radius=3)
        if r > 0:
            col = (int(lerp(235, 90, r)), int(lerp(70, 230, r)), int(lerp(60, 120, r)))
            pygame.draw.rect(v, col, (x + 33, y + 18, int(84 * r), 5), border_radius=2)
        if 0 < f.hp < f.max_hp * 0.25:
            v.blit(get_emoji("💔", 12), (x + 108, y + 15))
        er = clamp(f.energy / 100, 0, 1)
        pygame.draw.rect(v, (24, 22, 40), (x + 33, y + 27, 86, 3), border_radius=1)
        if er > 0:
            pygame.draw.rect(v, (255, 240, 140) if er >= 1 else (95, 200, 255), (x + 33, y + 27, int(86 * er), 3))
        v.blit(get_emoji(f.cd["icon"], 14), (x + 123, y + 3))
        wins = f.wins if self.mode != "team" else self.team_wins[f.team]
        for i in range(2):
            if wins > i:
                v.blit(get_emoji("⭐", 10), (x + 122 + i * 12, y + 22))
            else:
                pygame.draw.circle(v, (40, 40, 62), (x + 127 + i * 12, y + 27), 4)

    def draw_center_duel(self, v):
        t = rich_render(f"⏱ {max(0, math.ceil(self.rtime))}", 26)
        v.blit(t, (W // 2 - t.get_width() // 2, 14))
        vs = rich_render("⚔", 20)
        v.blit(vs, (W // 2 - vs.get_width() // 2, 48))
        if self.tour:
            tg = rich_render("🏆 TOURNAMENT", 13, (255, 210, 90))
            v.blit(tg, (W // 2 - tg.get_width() // 2, 76))

    def draw_boss_bar(self, v):
        boss = next((f for f in self.fighters if f.boss), None)
        if boss is None:
            return
        nm = rich_render(f"👹 {boss.name} — THE BOSS", 15, (255, 200, 120))
        v.blit(nm, (W // 2 - nm.get_width() // 2, 84))
        bw = 440
        x = W // 2 - bw // 2
        r = clamp(boss.hp / boss.max_hp, 0, 1)
        pygame.draw.rect(v, (24, 22, 40), (x - 2, 106, bw + 4, 16), border_radius=8)
        if r > 0:
            col = (int(lerp(235, 120, r)), int(lerp(70, 40, r)), int(lerp(60, 160, r)))
            pygame.draw.rect(v, col, (x, 108, int(bw * r), 12), border_radius=6)
        pygame.draw.rect(v, (200, 120, 80), (x - 2, 106, bw + 4, 16), 2, border_radius=8)

    def draw_center_multi(self, v):
        if self.mode == "team":
            sc = rich_render(f"{TEAM_ICONS[0]} {self.team_wins[0]}  :  {self.team_wins[1]} {TEAM_ICONS[1]}", 26)
            v.blit(sc, (W // 2 - sc.get_width() // 2, 8))
        t = rich_render(f"⏱ {max(0, math.ceil(self.rtime))}", 22)
        v.blit(t, (W // 2 - t.get_width() // 2, 46))
        label = MODE_LABEL[self.mode]
        if self.mode == "ffa":
            label += f" {len(self.fighters)}"
        elif self.mode == "team":
            label += f" {self.n_team}v{self.n_team}"
        tag = ui_font(12).render(f"{label} · [-]/[+] size · [1]/[2]/[3] mode", True, (120, 120, 150))
        v.blit(tag, (W // 2 - tag.get_width() // 2, 74))

    def draw_hype(self, v):
        bw = 180
        x = W // 2 - bw // 2
        y = H - 34
        pygame.draw.rect(v, (20, 18, 36), (x - 2, y - 2, bw + 4, 12), border_radius=6)
        hot = self.ex >= 0.7
        col = (255, 120, 60) if hot else (120, 110, 180)
        if int(self.age * 6) % 2 == 0 or not hot:
            pygame.draw.rect(v, col, (x, y, int(bw * clamp(self.ex, 0, 1)), 8), border_radius=4)
        v.blit(get_emoji("🔥" if hot else "📣", 14), (x - 20, y - 4))
        if hot:
            lb = rich_render("CROWD ON FIRE! +ENERGY", 11, (255, 190, 90))
            v.blit(lb, (x + bw + 8, y - 2))

    def draw_stats(self, v):
        rows = sorted(self.fighters, key=lambda f: -f.stats["dmg"])[:3]
        medals = ["🥇", "🥈", "🥉"]
        ph = 30 + len(rows) * 20
        panel = pygame.Surface((470, ph), pygame.SRCALPHA)
        pygame.draw.rect(panel, (14, 14, 32, 225), (0, 0, 470, ph), border_radius=10)
        pygame.draw.rect(panel, (110, 110, 160), (0, 0, 470, ph), 1, border_radius=10)
        tt = rich_render("📊 MATCH STATS", 13, (200, 200, 230))
        panel.blit(tt, (12, 6))
        for i, f in enumerate(rows):
            line = rich_render(f"{medals[i]} {f.name}  DMG {f.stats['dmg']} · HITS {f.stats['hits']} · CRITS {f.stats['crits']} · KO {f.stats['ko']}",
                               12, (235, 235, 245))
            panel.blit(line, (12, 28 + i * 20))
        v.blit(panel, (W // 2 - 235, H - 170))

    def draw_feed(self, v):
        y = H - 44
        for text, born in list(self.msgs)[-3:]:
            age = self.age - born
            alpha = clamp(1 - max(0, age - 5) / 1.5, 0, 1)
            if alpha <= 0:
                continue
            s = rich_render(text, 16, (235, 235, 245))
            s.set_alpha(int(255 * alpha))
            v.blit(s, (14, y))
            y -= 22

    def draw_intro_card(self, v, f, x, y, border):
        card = pygame.Surface((190, 60), pygame.SRCALPHA)
        pygame.draw.rect(card, (18, 18, 38, 225), (0, 0, 190, 60), border_radius=10)
        pygame.draw.rect(card, border, (0, 0, 190, 60), 2, border_radius=10)
        v.blit(card, (x, y))
        v.blit(get_emoji(f.head, 40), (x + 8, y + 10))
        v.blit(rich_render(f.name, 14, (255, 255, 255)), (x + 56, y + 6))
        v.blit(rich_render(f"{f.cd['icon']} {f.cls}", 11, (170, 175, 205)), (x + 56, y + 26))
        v.blit(rich_render(f"{SPECIALS[f.special][0]} {SPECIALS[f.special][1]}", 10, (255, 235, 160)), (x + 56, y + 43))

    def draw_bracket(self, v, cx, top):
        slot_w = 168
        xs = [cx - 280, cx - 60, cx + 160]
        for r, pairs in enumerate(self.tour["bracket"][:3]):
            x = xs[r]
            for i, m in enumerate(pairs):
                y = top + (i + 0.5) * 56 * (2 ** r)
                for j, key in enumerate(("a", "b")):
                    spec = m[key]
                    sy = y - 26 + j * 26
                    won = m["winner"] == j
                    lost = m["winner"] is not None and not won
                    slot = pygame.Surface((slot_w, 24), pygame.SRCALPHA)
                    pygame.draw.rect(slot, (16, 16, 36, 225), (0, 0, slot_w, 24), border_radius=6)
                    if won:
                        pygame.draw.rect(slot, (255, 210, 90), (0, 0, slot_w, 24), 2, border_radius=6)
                    v.blit(slot, (x, int(sy)))
                    nm = rich_render(f"{CLASSES[spec['cls']]['icon']} {spec['head'][0]}", 12,
                                     (255, 255, 255) if not lost else (110, 110, 125))
                    v.blit(nm, (x + 8, int(sy) + 4))
                    if won:
                        v.blit(get_emoji("⭐", 12), (x + slot_w - 18, int(sy) + 6))
                if r < 2:
                    x2 = xs[r + 1]
                    mx = x + slot_w + (x2 - x - slot_w) // 2
                    pygame.draw.line(v, (90, 90, 130), (x + slot_w, y), (mx, y), 2)
                    if i % 2 == 1:
                        y1 = top + (i - 0.5) * 56 * (2 ** r)
                        pygame.draw.line(v, (90, 90, 130), (mx, y1), (mx, y), 2)
                        yc = top + (i // 2 + 0.5) * 56 * (2 ** (r + 1))
                        pygame.draw.line(v, (90, 90, 130), (mx, yc), (x2, yc), 2)
        if len(self.tour["bracket"]) == 3:
            y = top + 0.5 * 56 * 4
            v.blit(get_emoji("🏆", 30), (xs[2] + slot_w + 24, int(y) - 15))

    def draw_intro(self, v):
        v.blit(self.dim, (0, 0))
        p = ease_out(clamp(self.pt / 0.7, 0, 1))
        if self.tour:
            title = rich_render("🏆 EMOJI TOURNAMENT 🏆", 30, (255, 220, 90))
            v.blit(title, (W // 2 - title.get_width() // 2, 34))
            n = len(self.tour["bracket"][-1])
            rl = {4: "QUARTERFINALS", 2: "SEMIFINALS", 1: "GRAND FINAL"}.get(n, "ROUND")
            sub = ui_font(14).render(f"{rl} — same arena, one champion", True, (150, 150, 185))
            v.blit(sub, (W // 2 - sub.get_width() // 2, 72))
            self.draw_bracket(v, W // 2, 108)
            self.draw_intro_card(v, self.f1, W // 2 - 230, 430, self.f1.col)
            self.draw_intro_card(v, self.f2, W // 2 + 40, 430, self.f2.col)
            vs = rich_render("⚔", 40)
            v.blit(vs, (W // 2 - vs.get_width() // 2, 438))
        elif self.mode in ("duel", "boss"):
            if self.mode == "boss":
                title = rich_render("👹 BOSS FIGHT 👹", 34, (255, 130, 90))
                subtxt = "the hero must fell the giant — one round, no mercy"
            else:
                title = rich_render("🥊 EMOJI AI ARENA 🥊", 34, (255, 220, 90))
                subtxt = "utility-brained fighter classes — sit back and watch"
            v.blit(title, (W // 2 - title.get_width() // 2, 54))
            sub = ui_font(15).render(subtxt, True, (150, 150, 185))
            v.blit(sub, (W // 2 - sub.get_width() // 2, 100))
            for f, sgn in ((self.f1, -1), (self.f2, 1)):
                tx = W // 2 + sgn * lerp(W * 0.75, 200, p)
                hsz = 104 if not f.boss else 150
                head = pygame.transform.rotozoom(get_emoji(f.head, hsz), sgn * (1 - p) * 30, 1)
                v.blit(head, (tx - head.get_width() // 2, 225 - head.get_height() // 2))
                nm = rich_render(f.name, 25, (255, 255, 255))
                v.blit(nm, (tx - nm.get_width() // 2, 310))
                if f.boss:
                    tag = rich_render(f"👹 THE BOSS · HP {f.max_hp}", 15, (255, 150, 110))
                else:
                    tag = rich_render(f"{f.cd['icon']} THE {f.cls}", 17, f.col)
                v.blit(tag, (tx - tag.get_width() // 2, 342))
                sp = rich_render(f"{SPECIALS[f.special][0]} {SPECIALS[f.special][1]}", 14, (255, 235, 160))
                v.blit(sp, (tx - sp.get_width() // 2, 366))
                blurb = ui_font(12).render(f.cd["blurb"], True, (150, 150, 175))
                v.blit(blurb, (tx - blurb.get_width() // 2, 388))
                pas = ui_font(12).render(f.cd["passive"], True, (120, 205, 140))
                v.blit(pas, (tx - pas.get_width() // 2, 406))
            vs = rich_render("⚔", 58)
            vs2 = pygame.transform.rotozoom(vs, 0, 1 + 0.08 * math.sin(self.age * 6))
            v.blit(vs2, (W // 2 - vs2.get_width() // 2, 225 - vs2.get_height() // 2))
        else:
            if self.mode == "team":
                k = self.n_team
                title = rich_render(f"{TEAM_ICONS[0]} TEAM BATTLE {TEAM_ICONS[1]}  {k} vs {k}", 32, (255, 220, 90))
            else:
                title = rich_render(f"⚔ MELEE ⚔ {len(self.fighters)} WARRIORS — LAST ONE STANDING", 30, (255, 220, 90))
            v.blit(title, (W // 2 - title.get_width() // 2, 60))
            sub = ui_font(14).render("utility-brained fighter classes — sit back and watch", True, (150, 150, 185))
            v.blit(sub, (W // 2 - sub.get_width() // 2, 106))
            if self.mode == "team":
                k = self.n_team
                step = min(72, 300 // max(1, k))
                y0 = 250 - (k - 1) * step / 2
                for i in range(k):
                    self.draw_intro_card(v, self.fighters[i], int(W // 2 - 210 - 190 * p), int(y0 + i * step), TEAM_COLS[0])
                    self.draw_intro_card(v, self.fighters[k + i], int(W // 2 + 210 * p), int(y0 + i * step), TEAM_COLS[1])
                vs = rich_render("⚔", 52)
                v.blit(vs, (W // 2 - vs.get_width() // 2, 250 - vs.get_height() // 2))
            else:
                n = len(self.fighters)
                cols = min(3, n)
                for i, f in enumerate(self.fighters):
                    cx = W // 2 + (i % cols - (cols - 1) / 2) * 210 - 95
                    cy = 170 + (i // cols) * 76
                    self.draw_intro_card(v, f, int(cx), int(cy + (1 - p) * 40), f.col)
        al = ui_font(13).render(f"ARENA: {self.arena['name']}", True, self.arena["glow"])
        v.blit(al, (W // 2 - al.get_width() // 2, 134))
        dots = "." * (1 + int(self.age * 2) % 3)
        ld = ui_font(14).render(f"loading fight.exe {dots}", True, (110, 200, 130))
        v.blit(ld, (W // 2 - ld.get_width() // 2, H - 56))

    def draw_champ(self, v):
        v.blit(self.dim, (0, 0))
        title = rich_render("🏆 TOURNAMENT CHAMPION 🏆", 32, (255, 220, 90))
        v.blit(title, (W // 2 - title.get_width() // 2, 30))
        self.draw_bracket(v, W // 2, 90)
        champ = self.tour["champion"]
        bob = math.sin(self.age * 4) * 8
        head = get_emoji(champ["head"][1], 100)
        v.blit(head, (W // 2 - 50, 400 - head.get_height() // 2 + bob))
        cr = get_emoji("👑", 36)
        v.blit(cr, (W // 2 - 18, 400 - head.get_height() // 2 - 30 + bob))
        nm = rich_render(champ["head"][0], 24, (255, 255, 255))
        v.blit(nm, (W // 2 - nm.get_width() // 2, 465))
        cl = rich_render(f"{CLASSES[champ['cls']]['icon']} THE {champ['cls']}", 14, (255, 235, 160))
        v.blit(cl, (W // 2 - cl.get_width() // 2, 498))
        hint = ui_font(13).render("new bracket incoming…", True, (140, 140, 170))
        v.blit(hint, (W // 2 - hint.get_width() // 2, 528))

    def draw(self):
        v = self.view
        v.blit(self.bg, (0, 0))
        for c in self.crowd:
            y = c["y0"] + math.sin(self.age * c["spd"] + c["phase"]) * (1.5 + self.ex * 6)
            v.blit(c["surf"], (c["x"] - 13, y - 13))
        fx = pygame.Surface((W, H), pygame.SRCALPHA)
        spot = self.arena.get("spot", (255, 240, 200))
        for f in self.fighters:
            pygame.draw.polygon(fx, (*spot, 12), [(f.x - 6, 0), (f.x - 80, FLOOR), (f.x + 80, FLOOR)])
        v.blit(fx, (0, 0))
        for pu in self.powerups:
            pu.draw(v, self.age)
        for f in self.fighters:
            f.draw(v, self.age)
        for p in self.projectiles:
            p.draw(v)
        for b in self.bombs:
            b.draw(v)
        for h in self.hazards:
            h.draw(v, self.age)
        for p in self.parts:
            p.draw(v)
        for t in self.texts:
            t.draw(v)
        if self.show_ai:
            for f in self.fighters:
                self.draw_ai_debug(v, f)
        if self.mode in ("duel", "boss"):
            self.draw_plate(v, self.f1, 14)
            self.draw_plate(v, self.f2, W - 14 - 346)
            self.draw_center_duel(v)
            if self.mode == "boss":
                self.draw_boss_bar(v)
        else:
            if self.mode == "team":
                ys = [10, 52, 94, 136]
                for i, f in enumerate(self.fighters):
                    if f.team == 0:
                        self.draw_chip(v, f, 10, ys[i])
                    else:
                        self.draw_chip(v, f, W - 160, ys[i - len(self.fighters) // 2])
            else:
                n = len(self.fighters)
                x0 = W // 2 - n * 154 // 2
                for i, f in enumerate(self.fighters):
                    self.draw_chip(v, f, x0 + i * 154, 10)
            self.draw_center_multi(v)
        self.draw_feed(v)
        self.draw_hype(v)
        if self.phase == "mend":
            self.draw_stats(v)
        hint = ui_font(11).render("1 duel · 2 melee · 3 teams · 4 tourney · 5 boss · -/+ size · H hazards · F speed · T brains · S slow · P pause · M sound · ESC quit", True, (120, 120, 150))
        v.blit(hint, (W - hint.get_width() - 12, H - 16))
        if self.speed > 1:
            s = rich_render("⏩ 2X", 14, (140, 220, 255))
            v.blit(s, (W - s.get_width() - 12, H - 58))
        if self.slowmo and self.phase == "fight":
            s = ui_font(14).render("SLOW-MO", True, (140, 220, 255))
            v.blit(s, (W - s.get_width() - 12, H - 40))
        if self.phase == "intro":
            self.draw_intro(v)
        elif self.phase == "champ" and self.tour:
            self.draw_champ(v)
        if self.banner:
            main, sub, age, dur = self.banner
            pop = 1 + 0.5 * max(0, 1 - age / 0.18)
            m2 = pygame.transform.rotozoom(main, 0, pop) if pop > 1.001 else main
            by = int(H * 0.34)
            v.blit(m2, (W // 2 - m2.get_width() // 2, by))
            if sub:
                v.blit(sub, (W // 2 - sub.get_width() // 2, by + m2.get_height() + 10))
        if self.paused:
            v.blit(self.dim, (0, 0))
            p = rich_render("⏸ PAUSED", 46)
            v.blit(p, (W // 2 - p.get_width() // 2, H // 2 - 40))
            for i, ln in enumerate(["SPACE skip · N new · 1-5 modes · -/+ roster size",
                                    "H hazards · F speed · T brains · S slow-mo · M sound"]):
                t = ui_font(14).render(ln, True, (170, 170, 200))
                v.blit(t, (W // 2 - t.get_width() // 2, H // 2 + 16 + i * 22))
        ox = random.randint(-int(self.shake), int(self.shake)) // 2 if self.shake > 1 else 0
        oy = random.randint(-int(self.shake), int(self.shake)) // 2 if self.shake > 1 else 0
        screen.fill((5, 6, 14))
        screen.blit(v, (ox, oy))

# ---------------------------------------------------------------- main
def main():
    global MUTED
    g = Game()
    clock = pygame.time.Clock()
    while True:
        dt = min(clock.tick(FPS) / 1000, 1 / 30)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); return
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_ESCAPE, pygame.K_q):
                    pygame.quit(); return
                elif e.key == pygame.K_p:
                    g.paused = not g.paused
                elif e.key == pygame.K_m:
                    MUTED = not MUTED
                    g.say("sound off 🔕" if MUTED else "sound on 🔔")
                elif e.key == pygame.K_s:
                    g.slowmo = not g.slowmo
                elif e.key == pygame.K_f:
                    g.speed = 2 if g.speed == 1 else 1
                    g.say("⏩ 2X SPEED" if g.speed == 2 else "▶ normal speed")
                elif e.key == pygame.K_t:
                    g.show_ai = not g.show_ai
                    g.say("AI brain view ON 🧠" if g.show_ai else "AI brain view OFF")
                elif e.key == pygame.K_h:
                    g.hazards_on = not g.hazards_on
                    g.say("⚠ hazards ON" if g.hazards_on else "⚠ hazards OFF")
                elif e.key == pygame.K_1:
                    g.tour = None
                    g.mode = "duel"
                    g.new_match()
                elif e.key == pygame.K_2:
                    g.tour = None
                    g.mode = "ffa"
                    g.new_match()
                elif e.key == pygame.K_3:
                    g.tour = None
                    g.mode = "team"
                    g.new_match()
                elif e.key == pygame.K_4:
                    g.start_tournament()
                elif e.key == pygame.K_5:
                    g.tour = None
                    g.mode = "boss"
                    g.new_match()
                elif e.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    if g.mode == "ffa":
                        g.n_ffa = max(3, g.n_ffa - 1)
                    elif g.mode == "team":
                        g.n_team = max(2, g.n_team - 1)
                    if g.mode not in ("duel", "boss"):
                        g.new_match()
                elif e.key in (pygame.K_EQUALS, pygame.K_KP_PLUS):
                    if g.mode == "ffa":
                        g.n_ffa = min(6, g.n_ffa + 1)
                    elif g.mode == "team":
                        g.n_team = min(4, g.n_team + 1)
                    if g.mode not in ("duel", "boss"):
                        g.new_match()
                elif e.key == pygame.K_n:
                    if g.tour:
                        g.start_tournament()
                    else:
                        g.new_match()
                elif e.key == pygame.K_SPACE:
                    if g.phase == "mend":
                        if g.tour:
                            g.pt = 99
                        else:
                            g.new_match()
                    elif g.phase == "champ":
                        g.pt = 99
                    elif g.phase == "intro":
                        g.start_round()
        if not g.paused:
            g.update(dt)
        g.draw()
        pygame.display.flip()

if __name__ == "__main__":
    main()