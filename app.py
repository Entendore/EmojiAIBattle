"""
🥷 Emoji Fight Arena 17.0 — Numba JIT Acceleration 🥷
A top-down 2D fighting game where emoji warriors learn to fight
via Neuroevolution AND AlphaZero-like gradient descent (SGD).
Features: Multi-class DNA genetics, dynamic stats, PUCT MCTS, SGD,
pure NumPy 8-bit sound, and Numba JIT compilation.
Strictly follows MVC, OOP, and Functional Programming paradigms.
"""

import argparse
import copy
import math
import os
import random
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Callable

import numpy as np
import pygame

# Numba Import with Fallback
try:
    from numba import njit
    NUMBA_AVAILABLE = True
    print("🚀 Numba JIT enabled. Compiling hot paths...")
except ImportError:
    NUMBA_AVAILABLE = False
    print("⚠️ Numba not installed. Falling back to pure Python/NumPy.")
    # Dummy decorator if numba is not installed
    def njit(*args, **kwargs):
        if len(args) == 1 and callable(args[0]):
            return args[0]
        def decorator(func):
            return func
        return decorator

# ==============================================================================
# 1. CONFIG & CONSTANTS
# ==============================================================================
@dataclass(frozen=True)
class Config:
    SCREEN_W: int = 1200
    SCREEN_H: int = 780
    FPS: int = 60
    
    ARENA: pygame.Rect = field(default_factory=lambda: pygame.Rect(30, 110, 830, 590))
    LEADERBOARD_RECT: pygame.Rect = field(default_factory=lambda: pygame.Rect(880, 110, 240, 200))
    COMBAT_LOG_RECT: pygame.Rect = field(default_factory=lambda: pygame.Rect(880, 320, 240, 110))
    PIE_CHART_RECT: pygame.Rect = field(default_factory=lambda: pygame.Rect(880, 440, 120, 260))
    HEATMAP_RECT: pygame.Rect = field(default_factory=lambda: pygame.Rect(1010, 440, 170, 130))
    NN_VIZ_RECT: pygame.Rect = field(default_factory=lambda: pygame.Rect(1010, 580, 170, 120))
    GRAPH_RECT: pygame.Rect = field(default_factory=lambda: pygame.Rect(30, 715, 830, 50))

    WARRIOR_SIZE: int = 64
    TILE_SIZE: int = 24
    GRID_W: int = 830 // 24
    GRID_H: int = 590 // 24

    WARRIOR_SPEED: float = 3.4
    ATTACK_RANGE: float = 82.0
    ATTACK_RANGE_SQ: float = 82.0 ** 2
    ATTACK_DAMAGE: float = 9.0
    PROJECTILE_DAMAGE: float = 15.0
    PROJECTILE_SPEED: float = 8.0
    STAGGER_DURATION: int = 12
    ATTACK_COOLDOWN: int = 22
    BLOCK_DURATION: int = 18
    BLOCK_COOLDOWN: int = 40
    DASH_COOLDOWN: int = 45
    DASH_DURATION: int = 8
    DASH_SPEED: float = 9.0
    SHOOT_COOLDOWN: int = 60
    PARRY_DURATION: int = 6
    PARRY_COOLDOWN: int = 60
    SLAM_COOLDOWN: int = 80
    SLAM_DAMAGE: float = 12.0
    SLAM_RADIUS: float = 70.0
    SLAM_RADIUS_SQ: float = 70.0 ** 2
    KNOCKBACK_FORCE: float = 6.0
    HAZARD_BASE_RADIUS: float = 80.0
    HAZARD_BASE_RADIUS_SQ: float = 80.0 ** 2
    HAZARD_DMG_PER_FRAME: float = 0.4
    CLOUD_DMG_PER_FRAME: float = 0.6
    CLOUD_SPAWN_INTERVAL: int = 400

    MAX_HEALTH: float = 120.0
    MAX_STAMINA: float = 100.0
    STAMINA_REGEN: float = 1.5
    ATTACK_STAMINA_COST: float = 30.0
    DASH_STAMINA_COST: float = 40.0
    SHOOT_STAMINA_COST: float = 50.0
    SLAM_STAMINA_COST: float = 60.0
    ELEVATION_MOVE_COST: float = 15.0

    POWERUP_SPAWN_INTERVAL: int = 300
    POWERUP_RADIUS: float = 20.0
    POWERUP_RADIUS_SQ: float = 20.0 ** 2

    ROUND_DURATION: int = 600
    INTRO_DURATION: int = 90

    POPULATION_SIZE: int = 30
    MUTATION_RATE: float = 0.20
    MUTATION_STRENGTH: float = 0.4
    ELITISM: int = 4
    HIDDEN_SIZE: int = 40
    N_OPPONENTS: int = 4
    HALL_OF_FAME_SIZE: int = 3

    STATE_SIZE: int = 37
    ACTION_SIZE: int = 10 

    MCTS_SIMULATIONS: int = 30
    MCTS_C_PUCT: float = 1.5
    MCTS_DIRICHLET_ALPHA: float = 0.3
    MCTS_DIRICHLET_WEIGHT: float = 0.25

    SGD_LEARNING_RATE: float = 0.001
    SGD_BATCH_SIZE: int = 128
    SGD_EPOCHS: int = 5

CFG = Config()

WARRIOR_EMOJIS = ["🥷", "🤺", "🥊", "🤠", "👹", "🤖", "👻", "🐲", "🦊", "🐺", "🧟", "🦄"]
CLASS_EMOJIS = ["🥷", "👹", "🤠", "🧙"]
ATTACK_EMOJIS = ["⚡", "🔥", "❄️", "🌪️", "💥", "✨"]
HIT_EMOJIS = ["💥", "🦴", "👊", "💢", "🤕"]
BLOCK_EMOJIS = ["🛡️", "🪨", "❌", "🧱"]
DEAD_EMOJIS = ["💀", "⚰️", "🪦", "👻"]
WIN_EMOJIS = ["🎉", "🎊", "👑", "🏆", "✨", "🥳"]
BLOOD_EMOJIS = ["🩸", "💉", "🥩", "🍅"]
POWERUP_EMOJIS = {"health": "❤️", "stamina": "🔋"}
ACTION_EMOJIS = ["⬆️", "⬇️", "⬅️", "➡️", "🥊", "🛡️", "💨", "🔮", "🤚", "👊"]
WALL_EMOJIS = ["🌲", "🪨", "🧱", "🛢️", "🌵", "🌳"]
HIGH_GROUND_EMOJIS = ["⛰️", "🏔️", "🪨"]

AUDIENCE_EMOJIS = ["👨", "👩", "🧑", "👶", "👽", "🤖", "👹", "🦊", "🐺", "🧟", "🦄", "🐲", "👻", "🤡", "🥷"]
DECOR_EMOJIS = ["🌿", "🍄", "🌵", "🌱", "🍃", "💧"]
AMBIENT_EMOJIS = ["🍂", "🍁", "❄️", "✨", "🔥", "💧"]
LAB_EMOJIS = ["🧬", "🦠", "⚗️", "🔬", "🧪", "💊"]

BG_COLOR = (24, 28, 40)
ARENA_COLOR = (45, 52, 70)
ARENA_GRID = (58, 68, 88)
ARENA_BORDER = (180, 190, 210)
TEXT_COLOR = (235, 240, 250)
DIM_TEXT = (140, 150, 170)
HEALTH_GREEN = (90, 220, 110)
HEALTH_YELLOW = (230, 200, 80)
HEALTH_RED = (220, 80, 80)
STAMINA_BLUE = (80, 180, 255)
ACCENT = (255, 200, 90)
PANEL_BG = (15, 18, 28)

CLASS_COLORS = [(90, 220, 110), (220, 80, 80), (230, 200, 80), (180, 100, 220)]

SAVE_FILE = "champion_brain_v17.npz"

# ==============================================================================
# 2. UTILITIES & NUMBA JIT FUNCTIONS
# ==============================================================================
def find_emoji_font(size: int) -> pygame.font.Font:
    pygame.font.init()
    available = set(pygame.font.get_fonts())
    for name in ["seguiemj", "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", "Symbola", "DejaVu Sans", "Arial"]:
        key = name.lower().replace(" ", "")
        if key in available: return pygame.font.SysFont(name, size)
    return pygame.font.SysFont(None, size)

def softmax(x: np.ndarray) -> np.ndarray:
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum()

@njit(cache=True)
def _softmax_numba(x: np.ndarray) -> np.ndarray:
    max_x = 0.0
    for i in range(x.shape[0]):
        if x[i] > max_x: max_x = x[i]
    
    sum_exp = 0.0
    e_x = np.zeros_like(x)
    for i in range(x.shape[0]):
        e_x[i] = math.exp(x[i] - max_x)
        sum_exp += e_x[i]
        
    for i in range(x.shape[0]):
        e_x[i] /= sum_exp
    return e_x

@njit(cache=True)
def _nn_forward_policy_numba(state: np.ndarray, W1: np.ndarray, b1: np.ndarray, W_pol: np.ndarray, b_pol: np.ndarray) -> np.ndarray:
    """Highly optimized NN forward pass for MCTS using Numba."""
    h_size = W1.shape[1]
    p_size = W_pol.shape[1]
    
    h = np.zeros(h_size, dtype=np.float32)
    for j in range(h_size):
        s = b1[j]
        for i in range(state.shape[0]):
            s += state[i] * W1[i, j]
        # Manual tanh for Numba speed
        if s > 20.0: h[j] = 1.0
        elif s < -20.0: h[j] = -1.0
        else:
            e1 = math.exp(s)
            e2 = math.exp(-s)
            h[j] = (e1 - e2) / (e1 + e2)
            
    p = np.zeros(p_size, dtype=np.float32)
    for k in range(p_size):
        s = b_pol[k]
        for j in range(h_size):
            s += h[j] * W_pol[j, k]
        p[k] = s
    return p

@njit(cache=True)
def _generate_ca_grid_numba(grid_w: int, grid_h: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Numba-JIT Cellular Automata and Distance Field generation."""
    grid = np.zeros((grid_h, grid_w), dtype=np.int32)
    for y in range(grid_h):
        for x in range(grid_w):
            if random.random() < 0.42: grid[y, x] = 1
            
    for _ in range(4):
        new_grid = grid.copy()
        for y in range(grid_h):
            for x in range(grid_w):
                neighbors = 0
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        if dx == 0 and dy == 0: continue
                        nx, ny = x + dx, y + dy
                        if nx < 0 or nx >= grid_w or ny < 0 or ny >= grid_h: neighbors += 1
                        elif grid[ny, nx] == 1: neighbors += 1
                if grid[y, x] == 1: new_grid[y, x] = 1 if neighbors >= 4 else 0
                else: new_grid[y, x] = 1 if neighbors >= 5 else 0
        grid = new_grid

    for y in range(grid_h):
        for x in range(grid_w):
            if grid[y, x] == 1 and random.random() < 0.3: grid[y, x] = 2

    cx, cy = grid_w // 2, grid_h // 2
    for y in range(grid_h):
        for x in range(grid_w):
            # Clear spawns
            d1 = math.hypot(x - 4, y - cy)
            d2 = math.hypot(x - (grid_w - 5), y - cy)
            if d1 < 3 or d2 < 3: grid[y, x] = 0
            
            # Clear center hazard
            if math.hypot(x - cx, y - cy) < 4: grid[y, x] = 0

    max_dist = 200.0
    dist_up = np.zeros((grid_h, grid_w), dtype=np.float32)
    dist_down = np.zeros((grid_h, grid_w), dtype=np.float32)
    dist_left = np.zeros((grid_h, grid_w), dtype=np.float32)
    dist_right = np.zeros((grid_h, grid_w), dtype=np.float32)

    tile_size = 24.0
    for y in range(grid_h):
        for x in range(grid_w):
            d = 0
            for yy in range(y, -1, -1):
                if grid[yy, x] == 1: break
                d += 1
            dist_up[y, x] = min(1.0, (d * tile_size) / max_dist)
            
            d = 0
            for yy in range(y, grid_h):
                if grid[yy, x] == 1: break
                d += 1
            dist_down[y, x] = min(1.0, (d * tile_size) / max_dist)
            
            d = 0
            for xx in range(x, -1, -1):
                if grid[y, xx] == 1: break
                d += 1
            dist_left[y, x] = min(1.0, (d * tile_size) / max_dist)
            
            d = 0
            for xx in range(x, grid_w):
                if grid[y, xx] == 1: break
                d += 1
            dist_right[y, x] = min(1.0, (d * tile_size) / max_dist)
            
    return grid, dist_up, dist_down, dist_left, dist_right

@njit(cache=True)
def _encode_state_numba(out_arr: np.ndarray, w1: np.ndarray, w2: np.ndarray, projs: np.ndarray, num_projs: int, pwr: np.ndarray, clouds: np.ndarray, num_clouds: int, dist_up: np.ndarray, dist_down: np.ndarray, dist_left: np.ndarray, dist_right: np.ndarray, elev: np.ndarray, screen_w: float, screen_h: float, cx: float, cy: float, haz_r_sq: float, tile_size: float, a_left: float, a_top: float):
    """Highly optimized MDP state encoder using Numba."""
    dx = w2[0] - w1[0]
    dy = w2[1] - w1[1]
    dist_sq = (dx*dx + dy*dy) / (screen_w*screen_w)
    
    nearest_proj_dist_sq = 4.0
    nearest_proj_dx = 0.0
    nearest_proj_dy = 0.0
    for i in range(num_projs):
        if projs[i, 4] != w1[19]: # owner != pov_id
            pdx = projs[i, 0] - w1[0]
            pdy = projs[i, 1] - w1[1]
            pd_sq = (pdx*pdx + pdy*pdy) / (screen_w*screen_w)
            if pd_sq < nearest_proj_dist_sq:
                nearest_proj_dist_sq = pd_sq
                nearest_proj_dx = pdx / screen_w
                nearest_proj_dy = pdy / screen_w
                
    pwr_dist_sq = 4.0
    if pwr[2] > 0.5:
        pdx = pwr[0] - w1[0]
        pdy = pwr[1] - w1[1]
        pwr_dist_sq = (pdx*pdx + pdy*pdy) / (screen_w*screen_w)
        
    hdx = w1[0] - cx
    hdy = w1[1] - cy
    dist_to_hazard_sq = ((hdx*hdx + hdy*hdy) - haz_r_sq) / (screen_w*screen_w)
    
    nearest_cloud_dist_sq = 4.0
    for i in range(num_clouds):
        cdx = clouds[i, 0] - w1[0]
        cdy = clouds[i, 1] - w1[1]
        cd_sq = (cdx*cdx + cdy*cdy) / (screen_w*screen_w)
        if cd_sq < nearest_cloud_dist_sq:
            nearest_cloud_dist_sq = cd_sq

    gx = int((w1[0] - a_left) // tile_size)
    gy = int((w1[1] - a_top) // tile_size)
    if gx < 0: gx = 0
    elif gx >= dist_up.shape[1]: gx = dist_up.shape[1] - 1
    if gy < 0: gy = 0
    elif gy >= dist_up.shape[0]: gy = dist_up.shape[0] - 1
    
    d_up = dist_up[gy, gx]
    d_down = dist_down[gy, gx]
    d_left = dist_left[gy, gx]
    d_right = dist_right[gy, gx]
    
    h1 = 1.0 if elev[gy, gx] == 2 else 0.0
    
    gx2 = int((w2[0] - a_left) // tile_size)
    gy2 = int((w2[1] - a_top) // tile_size)
    if gx2 < 0: gx2 = 0
    elif gx2 >= dist_up.shape[1]: gx2 = dist_up.shape[1] - 1
    if gy2 < 0: gy2 = 0
    elif gy2 >= dist_up.shape[0]: gy2 = dist_up.shape[0] - 1
    h2 = 1.0 if elev[gy2, gx2] == 2 else 0.0

    out_arr[0] = dx / screen_w; out_arr[1] = dy / screen_h; out_arr[2] = dist_sq
    out_arr[3] = w1[2] / w1[3]; out_arr[4] = w2[2] / w2[3]       # HP
    out_arr[5] = w1[4] / w1[5]; out_arr[6] = w2[4] / w2[5]       # Stamina
    out_arr[7] = w1[6]; out_arr[8] = w2[6]                       # Attack CD
    out_arr[9] = w1[7]; out_arr[10] = w2[7]                      # Block CD
    out_arr[11] = w1[8]; out_arr[12] = w2[8]                     # Dash CD
    out_arr[13] = w1[9]; out_arr[14] = w2[9]                     # Shoot CD
    out_arr[15] = w1[10]; out_arr[16] = w2[10]                   # Parry CD
    out_arr[17] = w1[11]; out_arr[18] = w2[11]                   # Slam CD
    out_arr[19] = w1[12]; out_arr[20] = w2[12]                   # is_block
    out_arr[21] = w1[13]; out_arr[22] = w2[13]                   # is_parry
    out_arr[23] = nearest_proj_dist_sq
    out_arr[24] = dist_to_hazard_sq
    out_arr[25] = nearest_cloud_dist_sq
    out_arr[26] = d_up; out_arr[27] = d_down; out_arr[28] = d_left; out_arr[29] = d_right
    out_arr[30] = h1; out_arr[31] = h2
    out_arr[32] = w1[14]; out_arr[33] = w1[15]; out_arr[34] = w1[16]; out_arr[35] = w1[17]
    out_arr[36] = w2[14]; out_arr[37] = w2[15]; out_arr[38] = w2[16]; out_arr[39] = w2[17]
    
    return out_arr

# ==============================================================================
# 3. MAP GENERATION
# ==============================================================================
@dataclass
class GameMap:
    grid: np.ndarray          
    walls: List[pygame.Rect]
    spawn_left: Tuple[float, float]
    spawn_right: Tuple[float, float]
    dist_up: np.ndarray
    dist_down: np.ndarray
    dist_left: np.ndarray
    dist_right: np.ndarray

def generate_ca_map() -> GameMap:
    if NUMBA_AVAILABLE:
        grid, d_up, d_down, d_left, d_right = _generate_ca_grid_numba(CFG.GRID_W, CFG.GRID_H)
    else:
        # Fallback logic (same as v16) if numba is missing
        grid = np.random.choice([0, 1], size=(CFG.GRID_H, CFG.GRID_W), p=[0.58, 0.42])
        for _ in range(4):
            new_grid = grid.copy()
            for y in range(CFG.GRID_H):
                for x in range(CFG.GRID_W):
                    neighbors = sum(1 for dy in [-1,0,1] for dx in [-1,0,1] if (dx!=0 or dy!=0) and (x+dx<0 or x+dx>=CFG.GRID_W or y+dy<0 or y+dy>=CFG.GRID_H or grid[y+dy, x+dx]==1))
                    new_grid[y, x] = 1 if (grid[y, x] == 1 and neighbors >= 4) or (grid[y, x] == 0 and neighbors >= 5) else 0
            grid = new_grid
        for y in range(CFG.GRID_H):
            for x in range(CFG.GRID_W):
                if grid[y, x] == 1 and random.random() < 0.3: grid[y, x] = 2
        for cy, cx in [(CFG.GRID_H//2, 4), (CFG.GRID_H//2, CFG.GRID_W-5)]:
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    if 0 <= cy+dy < CFG.GRID_H and 0 <= cx+dx < CFG.GRID_W and math.hypot(dy, dx) < 3: grid[cy+dy, cx+dx] = 0
        cx, cy = CFG.GRID_W // 2, CFG.GRID_H // 2
        for y in range(CFG.GRID_H):
            for x in range(CFG.GRID_W):
                if math.hypot(x - cx, y - cy) < 4: grid[y, x] = 0
        d_up = np.zeros((CFG.GRID_H, CFG.GRID_W), dtype=np.float32)
        d_down = np.zeros((CFG.GRID_H, CFG.GRID_W), dtype=np.float32)
        d_left = np.zeros((CFG.GRID_H, CFG.GRID_W), dtype=np.float32)
        d_right = np.zeros((CFG.GRID_H, CFG.GRID_W), dtype=np.float32)
        for y in range(CFG.GRID_H):
            for x in range(CFG.GRID_W):
                d=0
                for yy in range(y, -1, -1):
                    if grid[yy, x]==1: break
                    d+=1
                d_up[y,x] = min(1.0, (d*24)/200.0)
                d=0
                for yy in range(y, CFG.GRID_H):
                    if grid[yy, x]==1: break
                    d+=1
                d_down[y,x] = min(1.0, (d*24)/200.0)
                d=0
                for xx in range(x, -1, -1):
                    if grid[y, xx]==1: break
                    d+=1
                d_left[y,x] = min(1.0, (d*24)/200.0)
                d=0
                for xx in range(x, CFG.GRID_W):
                    if grid[y, xx]==1: break
                    d+=1
                d_right[y,x] = min(1.0, (d*24)/200.0)

    walls = [pygame.Rect(CFG.ARENA.left + x * CFG.TILE_SIZE, CFG.ARENA.top + y * CFG.TILE_SIZE, CFG.TILE_SIZE, CFG.TILE_SIZE) 
             for y in range(CFG.GRID_H) for x in range(CFG.GRID_W) if grid[y, x] == 1]
    
    spawn_l = (CFG.ARENA.left + 4 * CFG.TILE_SIZE, CFG.ARENA.centery)
    spawn_r = (CFG.ARENA.left + (CFG.GRID_W - 5) * CFG.TILE_SIZE, CFG.ARENA.centery)
    
    return GameMap(grid=grid, walls=walls, spawn_left=spawn_l, spawn_right=spawn_r,
                   dist_up=d_up, dist_down=d_down, dist_left=d_left, dist_right=d_right)

def is_wall_grid(gmap: GameMap, gx: int, gy: int) -> bool:
    if gx < 0 or gx >= CFG.GRID_W or gy < 0 or gy >= CFG.GRID_H: return True
    return gmap.grid[gy, gx] == 1

def get_elevation(gmap: GameMap, px: float, py: float) -> int:
    gx = int((px - CFG.ARENA.left) // CFG.TILE_SIZE)
    gy = int((py - CFG.ARENA.top) // CFG.TILE_SIZE)
    if gx < 0 or gx >= CFG.GRID_W or gy < 0 or gy >= CFG.GRID_H: return 0
    return 1 if gmap.grid[gy, gx] == 2 else 0

def is_wall_px(gmap: GameMap, px: float, py: float) -> bool:
    gx = int((px - CFG.ARENA.left) // CFG.TILE_SIZE)
    gy = int((py - CFG.ARENA.top) // CFG.TILE_SIZE)
    return is_wall_grid(gmap, gx, gy)

# ==============================================================================
# 4. ENTITIES (DATA STRUCTURES with __slots__)
# ==============================================================================
@dataclass(slots=True)
class Warrior:
    x: float; y: float
    brain: 'Brain'
    emoji: str = "🥷"
    label: str = ""
    health: float = CFG.MAX_HEALTH
    stamina: float = CFG.MAX_STAMINA
    facing: int = 1
    vx: float = 0.0; vy: float = 0.0
    attack_cd: int = 0; block_cd: int = 0; dash_cd: int = 0; shoot_cd: int = 0; parry_cd: int = 0; slam_cd: int = 0
    block_timer: int = 0; dash_timer: int = 0; stagger_timer: int = 0; parry_timer: int = 0; slam_anim: int = 0
    is_blocking: bool = False; is_dashing: bool = False; is_parrying: bool = False
    damage_dealt: float = 0.0; damage_taken: float = 0.0
    alive: bool = True
    flash_timer: int = 0; attack_anim: int = 0; shoot_anim: int = 0
    dodge_anim: int = 0; parry_anim: int = 0
    combo_count: int = 0; max_combo: int = 0
    perfect_dodges: int = 0; parries: int = 0
    current_attack_emoji: str = "⚡"
    use_mcts: bool = False
    
    max_health: float = CFG.MAX_HEALTH
    max_stamina: float = CFG.MAX_STAMINA
    speed: float = CFG.WARRIOR_SPEED
    attack_dmg: float = CFG.ATTACK_DAMAGE
    proj_dmg: float = CFG.PROJECTILE_DAMAGE
    slam_dmg: float = CFG.SLAM_DAMAGE
    attack_cost: float = CFG.ATTACK_STAMINA_COST
    dash_cost: float = CFG.DASH_STAMINA_COST
    shoot_cost: float = CFG.SHOOT_STAMINA_COST
    slam_cost: float = CFG.SLAM_STAMINA_COST
    dmg_taken_mult: float = 1.0
    heal_mult: float = 1.0
    pov_id: int = 1  # Used for Numba state packing

    def apply_class_weights(self):
        w = self.brain.class_weights
        self.max_health = CFG.MAX_HEALTH * (0.8*w[0] + 1.3*w[1] + 1.0*w[2] + 0.8*w[3])
        self.max_stamina = CFG.MAX_STAMINA * (1.2*w[0] + 0.8*w[1] + 1.0*w[2] + 1.5*w[3])
        self.speed = CFG.WARRIOR_SPEED * (1.2*w[0] + 0.8*w[1] + 1.0*w[2] + 0.9*w[3])
        
        self.attack_dmg = CFG.ATTACK_DAMAGE * (1.0*w[0] + 1.2*w[1] + 0.8*w[2] + 0.8*w[3])
        self.proj_dmg = CFG.PROJECTILE_DAMAGE * (0.8*w[0] + 0.6*w[1] + 1.5*w[2] + 1.2*w[3])
        self.slam_dmg = CFG.SLAM_DAMAGE * (0.8*w[0] + 1.2*w[1] + 0.8*w[2] + 1.5*w[3])
        
        self.attack_cost = CFG.ATTACK_STAMINA_COST * (0.8*w[0] + 1.2*w[1] + 1.0*w[2] + 1.1*w[3])
        self.dash_cost = CFG.DASH_STAMINA_COST * (0.6*w[0] + 1.4*w[1] + 1.0*w[2] + 1.1*w[3])
        self.shoot_cost = CFG.SHOOT_STAMINA_COST * (1.2*w[0] + 1.5*w[1] + 0.6*w[2] + 0.8*w[3])
        self.slam_cost = CFG.SLAM_STAMINA_COST * (1.2*w[0] + 1.0*w[1] + 1.2*w[2] + 0.6*w[3])
        
        self.dmg_taken_mult = 1.2*w[0] + 0.7*w[1] + 1.0*w[2] + 1.2*w[3]
        self.heal_mult = 1.0*w[0] + 1.5*w[1] + 1.0*w[2] + 0.8*w[3]
        
        dom_class = int(np.argmax(w))
        self.emoji = CLASS_EMOJIS[dom_class]

    def reset(self, x: float, y: float, facing: int):
        self.apply_class_weights()
        self.x = x; self.y = y
        self.health = self.max_health; self.stamina = self.max_stamina
        self.facing = facing; self.vx = self.vy = 0.0
        self.attack_cd = self.block_cd = self.dash_cd = self.shoot_cd = self.parry_cd = self.slam_cd = 0
        self.block_timer = self.dash_timer = self.stagger_timer = self.parry_timer = self.slam_anim = 0
        self.is_blocking = self.is_dashing = self.is_parrying = False
        self.damage_dealt = self.damage_taken = 0.0
        self.alive = True
        self.flash_timer = self.attack_anim = self.shoot_anim = self.dodge_anim = self.parry_anim = 0
        self.combo_count = self.max_combo = self.perfect_dodges = self.parries = 0

    def is_invulnerable(self) -> bool:
        return self.is_dashing and self.dash_timer >= CFG.DASH_DURATION - 3

@dataclass(slots=True)
class Projectile:
    x: float; y: float; vx: float; vy: float
    owner: int; damage: float; life: int = 90

@dataclass(slots=True)
class PowerUp:
    x: float; y: float; ptype: str

@dataclass(slots=True)
class Cloud:
    x: float; y: float; vx: float; radius: float; life: int = 240

@dataclass(slots=True)
class Effect:
    x: float; y: float; emoji: str; life: int; max_life: int
    vx: float = 0.0; vy: float = 0.0; size: int = 36; gravity: float = 0.0; persistent: bool = False

@dataclass(slots=True)
class AmbientParticle:
    x: float; y: float; emoji: str; vx: float; vy: float; size: int; alpha: int

# ==============================================================================
# 5. NEURAL NETWORK (MODEL + GRADIENT DESCENT)
# ==============================================================================
class Brain:
    __slots__ = ['W1', 'b1', 'W_pol', 'b_pol', 'W_val', 'b_val', 'class_weights', 
                 'fitness', 'value_acc', 'wins', 'losses', 'draws', 'elo', 
                 'action_history', 'heatmap', 'uid']
    _uid_counter = 0

    def __init__(self, rng: Optional[np.random.Generator] = None):
        rng = rng or np.random.default_rng()
        self.W1 = rng.standard_normal((CFG.STATE_SIZE, CFG.HIDDEN_SIZE)).astype(np.float32) * 0.7
        self.b1 = np.zeros(CFG.HIDDEN_SIZE, dtype=np.float32)
        self.W_pol = rng.standard_normal((CFG.HIDDEN_SIZE, CFG.ACTION_SIZE)).astype(np.float32) * 0.7
        self.b_pol = np.zeros(CFG.ACTION_SIZE, dtype=np.float32)
        self.W_val = rng.standard_normal((CFG.HIDDEN_SIZE, 1)).astype(np.float32) * 0.7
        self.b_val = np.zeros(1, dtype=np.float32)
        
        self.class_weights = rng.random(4)
        self.class_weights = self.class_weights / self.class_weights.sum()
        
        self.fitness = 0.0; self.value_acc = 0.0
        self.wins = 0; self.losses = 0; self.draws = 0
        self.elo = 1000.0
        self.action_history = np.zeros(CFG.ACTION_SIZE, dtype=np.float32)
        self.heatmap = np.zeros((8, 8), dtype=np.float32)
        Brain._uid_counter += 1; self.uid = Brain._uid_counter

    def forward(self, state: np.ndarray) -> Tuple[np.ndarray, float, np.ndarray]:
        h = np.tanh(state @ self.W1 + self.b1)
        policy = h @ self.W_pol + self.b_pol
        value = np.tanh(h @ self.W_val + self.b_val)[0]
        return policy, value, h

    def forward_policy(self, state: np.ndarray) -> np.ndarray:
        if NUMBA_AVAILABLE:
            return _nn_forward_policy_numba(state, self.W1, self.b1, self.W_pol, self.b_pol)
        else:
            h = np.tanh(state @ self.W1 + self.b1)
            return h @ self.W_pol + self.b_pol

    def act(self, state: np.ndarray) -> int:
        p = self.forward_policy(state)
        return int(np.argmax(p))

    def predict(self, state: np.ndarray) -> Tuple[np.ndarray, float]:
        p, v, _ = self.forward(state)
        return softmax(p), v

    def train_step(self, states: np.ndarray, target_policies: np.ndarray, target_values: np.ndarray, lr: float):
        h = np.tanh(states @ self.W1 + self.b1)
        p_logits = h @ self.W_pol + self.b_pol
        p_pred = softmax(p_logits)
        v_pred = np.tanh(h @ self.W_val + self.b_val).flatten()
        
        dv = (v_pred - target_values).reshape(-1, 1) * (1 - v_pred**2)
        dW_val = h.T @ dv; db_val = np.sum(dv, axis=0)
        
        dp = (p_pred - target_policies)
        dW_pol = h.T @ dp; db_pol = np.sum(dp, axis=0)
        
        dh = (dv @ self.W_val.T + dp @ self.W_pol.T) * (1 - h**2)
        dW1 = states.T @ dh; db1 = np.sum(dh, axis=0)
        
        self.W1 -= lr * dW1; self.b1 -= lr * db1
        self.W_pol -= lr * dW_pol; self.b_pol -= lr * db_pol
        self.W_val -= lr * dW_val; self.b_val -= lr * db_val

    def mutate(self, rate: float, strength: float, rng: np.random.Generator):
        for arr in (self.W1, self.b1, self.W_pol, self.b_pol, self.W_val, self.b_val):
            mask = rng.random(arr.shape) < rate
            if mask.any(): arr[mask] += rng.standard_normal(int(mask.sum())) * strength
        
        if rng.random() < rate * 2:
            self.class_weights += rng.standard_normal(4) * strength * 0.5
            self.class_weights = np.clip(self.class_weights, 0.01, 1.0)
            self.class_weights = self.class_weights / self.class_weights.sum()

    def copy(self) -> "Brain":
        b = Brain.__new__(Brain)
        b.W1 = self.W1.copy(); b.b1 = self.b1.copy()
        b.W_pol = self.W_pol.copy(); b.b_pol = self.b_pol.copy()
        b.W_val = self.W_val.copy(); b.b_val = self.b_val.copy()
        b.class_weights = self.class_weights.copy()
        b.fitness = 0.0; b.value_acc = 0.0
        b.wins = b.losses = b.draws = 0
        b.elo = self.elo
        b.damage_dealt = b.damage_taken = 0.0
        b.action_history = np.zeros(CFG.ACTION_SIZE, dtype=np.float32)
        b.heatmap = np.zeros((8, 8), dtype=np.float32)
        b.uid = self.uid
        return b

    def save(self, path: str):
        np.savez(path, W1=self.W1, b1=self.b1, W_pol=self.W_pol, b_pol=self.b_pol, 
                 W_val=self.W_val, b_val=self.b_val, fitness=self.fitness, elo=self.elo, class_weights=self.class_weights)

    @staticmethod
    def load(path: str) -> Optional["Brain"]:
        if not os.path.exists(path): return None
        data = np.load(path)
        b = Brain()
        b.W1 = data['W1']; b.b1 = data['b1']
        b.W_pol = data['W_pol']; b.b_pol = data['b_pol']
        b.W_val = data['W_val']; b.b_val = data['b_val']
        b.fitness = float(data['fitness'])
        b.elo = float(data['elo'])
        b.class_weights = data['class_weights']
        return b

    @staticmethod
    def crossover(a: "Brain", b: "Brain", rng: np.random.Generator) -> "Brain":
        child = Brain.__new__(Brain)
        child.fitness = 0.0; child.value_acc = 0.0
        child.wins = child.losses = child.draws = 0
        child.elo = (a.elo + b.elo) / 2
        child.damage_dealt = child.damage_taken = 0.0
        child.action_history = np.zeros(CFG.ACTION_SIZE, dtype=np.float32)
        child.heatmap = np.zeros((8, 8), dtype=np.float32)
        Brain._uid_counter += 1; child.uid = Brain._uid_counter
        
        for attr in ('W1', 'b1', 'W_pol', 'b_pol', 'W_val', 'b_val'):
            av = getattr(a, attr); bv = getattr(b, attr)
            mask = rng.random(av.shape) < 0.5
            setattr(child, attr, np.where(mask, av, bv))
            
        alpha = rng.random()
        child.class_weights = (a.class_weights * alpha + b.class_weights * (1 - alpha))
        child.class_weights = child.class_weights / child.class_weights.sum()
        return child

# ==============================================================================
# 6. SOUND DESIGN
# ==============================================================================
class SoundManager:
    def __init__(self):
        self.enabled = True
        try:
            pygame.mixer.pre_init(44100, -16, 1, 512)
            pygame.mixer.init()
            self.sr = 44100
            self.sounds = {}
            self._generate_sounds()
        except Exception as e:
            print(f"Warning: Could not init audio: {e}")
            self.enabled = False

    def _gen_wave(self, freq, dur, wave_type='square', vol=0.4, sweep=0):
        t = np.linspace(0, dur, int(self.sr * dur), False)
        f = freq + sweep * t
        if wave_type == 'square':
            wave = np.sign(np.sin(2 * np.pi * f * t))
        elif wave_type == 'triangle':
            wave = 2 * np.abs(2 * (f * t - np.floor(f * t + 0.5))) - 1
        elif wave_type == 'sine':
            wave = np.sin(2 * np.pi * f * t)
        else: # noise
            wave = np.random.uniform(-1, 1, len(t))
            
        env = np.exp(-4 * t)
        wave = wave * env * vol
        audio = (wave * 32767).astype(np.int16)
        return audio

    def _mix(self, *waves):
        max_len = max(len(w) for w in waves)
        mixed = np.zeros(max_len)
        for w in waves:
            mixed[:len(w)] += w
        mixed = np.clip(mixed, -1, 1)
        return (mixed * 32767).astype(np.int16)

    def _make_sound(self, audio_array):
        return pygame.sndarray.make_sound(audio_array.reshape(-1, 1))

    def _generate_sounds(self):
        self.sounds['attack'] = self._make_sound(self._gen_wave(800, 0.05, 'square', 0.3, sweep=600))
        self.sounds['hit'] = self._make_sound(self._mix(
            self._gen_wave(0, 0.1, 'noise', 0.5),
            self._gen_wave(120, 0.1, 'square', 0.4, sweep=-40)
        ))
        self.sounds['block'] = self._make_sound(self._gen_wave(150, 0.08, 'square', 0.4, sweep=-50))
        self.sounds['dash'] = self._make_sound(self._gen_wave(300, 0.1, 'sine', 0.3, sweep=1500))
        self.sounds['shoot'] = self._make_sound(self._gen_wave(1200, 0.15, 'square', 0.3, sweep=-1000))
        self.sounds['parry'] = self._make_sound(self._gen_wave(1800, 0.1, 'triangle', 0.5))
        self.sounds['slam'] = self._make_sound(self._mix(
            self._gen_wave(0, 0.2, 'noise', 0.6),
            self._gen_wave(60, 0.2, 'square', 0.5, sweep=-20)
        ))
        c = self._gen_wave(523, 0.06, 'square', 0.4)
        e = self._gen_wave(659, 0.06, 'square', 0.4)
        g = self._gen_wave(784, 0.1, 'square', 0.4)
        self.sounds['powerup'] = self._make_sound(np.concatenate([c, e, g]))
        self.sounds['death'] = self._make_sound(self._gen_wave(400, 0.4, 'triangle', 0.4, sweep=-300))
        c = self._gen_wave(523, 0.1, 'square', 0.4)
        e = self._gen_wave(659, 0.1, 'square', 0.4)
        g = self._gen_wave(784, 0.1, 'square', 0.4)
        hi_c = self._gen_wave(1046, 0.2, 'square', 0.4)
        self.sounds['win'] = self._make_sound(np.concatenate([c, e, g, hi_c]))
        self.sounds['click'] = self._make_sound(self._gen_wave(1000, 0.03, 'square', 0.2))

    def play(self, name):
        if not self.enabled or name not in self.sounds: return
        try:
            self.sounds[name].play()
        except:
            pass

    def toggle_mute(self):
        self.enabled = not self.enabled
        if not self.enabled:
            pygame.mixer.stop()

# ==============================================================================
# 7. ENVIRONMENT (MODEL / CONTROLLER)
# ==============================================================================
class Environment:
    def __init__(self, w1: Warrior, w2: Warrior, gmap: GameMap, headless: bool = False, fast_mode: bool = False):
        self.w1 = w1; self.w2 = w2
        self.gmap = gmap
        self.headless = headless
        self.fast_mode = fast_mode or headless 
        
        self.projectiles: List[Projectile] = []
        self.powerup: Optional[PowerUp] = None
        self.powerup_timer = CFG.POWERUP_SPAWN_INTERVAL
        self.clouds: List[Cloud] = []
        self.cloud_timer = CFG.CLOUD_SPAWN_INTERVAL
        
        self.tick = 0
        self.done = False
        self.winner: Optional[int] = None
        self.current_hazard_r = CFG.HAZARD_BASE_RADIUS
        self.current_hazard_r_sq = CFG.HAZARD_BASE_RADIUS_SQ
        
        self.hitstop = 0
        self.shake = 0
        self.effects: List[Effect] = [] if not headless else []
        self.combat_log: List[str] = [] if not headless else []
        self.sound_queue: List[str] = [] if not headless else []
        
        if not fast_mode:
            self.w1.reset(*gmap.spawn_left, facing=1)
            self.w2.reset(*gmap.spawn_right, facing=-1)
            self.w1.pov_id = 1
            self.w2.pov_id = 2
            
            # Pre-allocated arrays for Numba state encoding
            self._w1_data = np.zeros(20, dtype=np.float32)
            self._w2_data = np.zeros(20, dtype=np.float32)
            self._projs_data = np.zeros((10, 5), dtype=np.float32)
            self._pwr_data = np.zeros(3, dtype=np.float32)
            self._clouds_data = np.zeros((10, 3), dtype=np.float32)
        
        self.agent1 = PUCTAgent(w1.brain, w2.brain) if w1.use_mcts and not headless else None
        self.agent2 = PUCTAgent(w2.brain, w1.brain) if w2.use_mcts and not headless else None

    def clone(self) -> "Environment":
        c = Environment.__new__(Environment)
        c.w1 = copy.copy(self.w1)
        c.w2 = copy.copy(self.w2)
        c.gmap = self.gmap
        c.projectiles = self.projectiles.copy()
        c.powerup = self.powerup
        c.clouds = self.clouds.copy()
        c.tick = self.tick
        c.done = self.done
        c.winner = self.winner
        c.current_hazard_r = self.current_hazard_r
        c.current_hazard_r_sq = self.current_hazard_r_sq
        c.hitstop = 0; c.shake = 0
        c.headless = True; c.fast_mode = True
        c.effects = []; c.combat_log = []; c.sound_queue = []
        c.agent1 = None; c.agent2 = None
        
        # Copy array references for fast state packing
        c._w1_data = self._w1_data
        c._w2_data = self._w2_data
        c._projs_data = self._projs_data
        c._pwr_data = self._pwr_data
        c._clouds_data = self._clouds_data
        return c

    def add_log(self, msg: str):
        if not self.headless:
            self.combat_log.insert(0, msg)
            if len(self.combat_log) > 4: self.combat_log.pop()

    def step(self):
        if self.done: return
        if self.tick < CFG.INTRO_DURATION:
            self.tick += 1; return
        if self.hitstop > 0:
            self.hitstop -= 1; self.shake = max(0, self.shake - 1); return

        self.tick += 1
        self.current_hazard_r = CFG.HAZARD_BASE_RADIUS + math.sin(self.tick * 0.02) * 30
        self.current_hazard_r_sq = self.current_hazard_r ** 2
        
        if self.w1.alive and self.w2.alive:
            a1 = self.agent1.search(self)[0] if self.agent1 else self.w1.brain.act(get_state_vector(self, 1))
            a2 = self.agent2.search(self)[0] if self.agent2 else self.w2.brain.act(get_state_vector(self, 2))
            
            if not self.headless:
                self.w1.brain.action_history[a1] += 1
                self.w2.brain.action_history[a2] += 1
                gx1 = int((self.w1.x - CFG.ARENA.left) / CFG.ARENA.w * 8)
                gy1 = int((self.w1.y - CFG.ARENA.top) / CFG.ARENA.h * 8)
                self.w1.brain.heatmap[max(0, min(7, gy1)), max(0, min(7, gx1))] += 1
                
            self._apply_action(self.w1, a1, self.w2)
            self._apply_action(self.w2, a2, self.w1)
            self._resolve_attacks(self.w1, self.w2)
            self._resolve_attacks(self.w2, self.w1)

        for w in (self.w1, self.w2):
            self._update_warrior_timers(w)
            self._update_warrior_physics(w)
            self._check_hazards_and_pickups(w)

        self._resolve_warrior_collision()
        self._update_projectiles()
        if not self.fast_mode:
            self._update_clouds_and_powerups()
        self._update_effects()

        self.shake = max(0, self.shake - 1)
        self._check_win_condition()

    def _update_warrior_timers(self, w: Warrior):
        if w.stagger_timer > 0: w.stagger_timer -= 1
        if w.attack_cd > 0: w.attack_cd -= 1
        if w.block_cd > 0: w.block_cd -= 1
        if w.dash_cd > 0: w.dash_cd -= 1
        if w.shoot_cd > 0: w.shoot_cd -= 1
        if w.parry_cd > 0: w.parry_cd -= 1
        if w.slam_cd > 0: w.slam_cd -= 1
        if w.block_timer > 0:
            w.block_timer -= 1
            if w.block_timer == 0: w.is_blocking = False
        if w.dash_timer > 0:
            w.dash_timer -= 1
            if w.dash_timer == 0: w.is_dashing = False
        if w.parry_timer > 0:
            w.parry_timer -= 1
            if w.parry_timer == 0: w.is_parrying = False
        if w.flash_timer > 0: w.flash_timer -= 1
        if w.attack_anim > 0: w.attack_anim -= 1
        if w.shoot_anim > 0: w.shoot_anim -= 1
        if w.dodge_anim > 0: w.dodge_anim -= 1
        if w.parry_anim > 0: w.parry_anim -= 1
        if w.slam_anim > 0: w.slam_anim -= 1

    def _update_warrior_physics(self, w: Warrior):
        old_x, old_y = w.x, w.y
        w.x += w.vx; w.y += w.vy
        w.vx *= 0.8; w.vy *= 0.8
        
        w.x = max(CFG.ARENA.left + 32, min(CFG.ARENA.right - 32, w.x))
        w.y = max(CFG.ARENA.top + 32, min(CFG.ARENA.bottom - 32, w.y))
        
        r = CFG.WARRIOR_SIZE // 2.5
        hit_wall = is_wall_px(self.gmap, w.x - r, w.y) or is_wall_px(self.gmap, w.x + r, w.y) or \
                   is_wall_px(self.gmap, w.x, w.y - r) or is_wall_px(self.gmap, w.x, w.y + r)
        if hit_wall:
            w.x = old_x; w.y = old_y; w.vx = 0; w.vy = 0
            
        if not self.headless and get_elevation(self.gmap, old_x, old_y) < get_elevation(self.gmap, w.x, w.y):
            w.stamina -= CFG.ELEVATION_MOVE_COST
            
        w.stamina = min(w.max_stamina, w.stamina + CFG.STAMINA_REGEN)

    def _check_hazards_and_pickups(self, w: Warrior):
        dx_h = w.x - CFG.ARENA.centerx
        dy_h = w.y - CFG.ARENA.centery
        if dx_h*dx_h + dy_h*dy_h < self.current_hazard_r_sq:
            w.health -= CFG.HAZARD_DMG_PER_FRAME; w.damage_taken += CFG.HAZARD_DMG_PER_FRAME
        
        if not self.fast_mode:
            for c in self.clouds:
                dx_c = w.x - c.x; dy_c = w.y - c.y
                if dx_c*dx_c + dy_c*dy_c < c.radius * c.radius:
                    w.health -= CFG.CLOUD_DMG_PER_FRAME; w.damage_taken += CFG.CLOUD_DMG_PER_FRAME
                    break
                
            if self.powerup:
                dx_p = w.x - self.powerup.x; dy_p = w.y - self.powerup.y
                if dx_p*dx_p + dy_p*dy_p < CFG.POWERUP_RADIUS_SQ:
                    if self.powerup.ptype == "health": 
                        w.health = min(w.max_health, w.health + 40 * w.heal_mult)
                        self.add_log(f"{w.emoji} picked up ❤️")
                    else: 
                        w.stamina = w.max_stamina
                        self.add_log(f"{w.emoji} picked up 🔋")
                    self.sound_queue.append("powerup")
                    self.powerup = None

        if w.health <= 0:
            w.health = 0; w.alive = False
            self.hitstop = 10; self.shake = 15
            self.sound_queue.append("death")
            if not self.headless:
                self.effects.append(Effect(w.x, w.y, random.choice(DEAD_EMOJIS), 90, 90, size=56))

    def _resolve_warrior_collision(self):
        min_dist = CFG.WARRIOR_SIZE * 0.65
        min_dist_sq = min_dist * min_dist
        dx = self.w2.x - self.w1.x; dy = self.w2.y - self.w1.y
        d2 = dx*dx + dy*dy
        if 0 < d2 < min_dist_sq:
            d = math.sqrt(d2)
            push = (min_dist - d) / 2
            self.w1.x -= dx / d * push; self.w1.y -= dy / d * push
            self.w2.x += dx / d * push; self.w2.y += dy / d * push

    def _update_projectiles(self):
        for p in self.projectiles:
            p.x += p.vx; p.y += p.vy; p.life -= 1
            if is_wall_px(self.gmap, p.x, p.y): p.life = 0
            
            target = self.w2 if p.owner == 1 else self.w1
            dx = p.x - target.x; dy = p.y - target.y
            if dx*dx + dy*dy < (CFG.WARRIOR_SIZE/2)**2:
                if target.is_invulnerable():
                    target.dodge_anim = 15; target.perfect_dodges += 1
                    target.stamina = min(target.max_stamina, target.stamina + 20)
                    self.add_log(f"{target.emoji} perfect dodged! ✨")
                    self.sound_queue.append("dash")
                elif target.is_parrying:
                    target.parry_anim = 15; target.parries += 1
                    target.stamina = min(target.max_stamina, target.stamina + 40)
                    self.add_log(f"{target.emoji} PARRIED! 🤚")
                    self.sound_queue.append("parry")
                elif target.is_blocking:
                    target.health -= p.damage * 0.25
                    self.sound_queue.append("block")
                else:
                    target.health -= p.damage; target.stagger_timer = CFG.STAGGER_DURATION
                    target.is_blocking = False; target.is_dashing = False; target.is_parrying = False
                    self.add_log(f"{target.emoji} hit by 🔮 for {p.damage}!")
                    self.hitstop = 5; self.shake = 10; target.combo_count = 0
                    self.sound_queue.append("hit")
                p.life = 0
        self.projectiles = [p for p in self.projectiles if p.life > 0 and CFG.ARENA.collidepoint(p.x, p.y)]

    def _update_clouds_and_powerups(self):
        if not self.powerup:
            self.powerup_timer -= 1
            if self.powerup_timer <= 0:
                for _ in range(10):
                    ang = random.uniform(0, math.pi * 2)
                    px = CFG.ARENA.centerx + math.cos(ang) * (self.current_hazard_r + 40)
                    py = CFG.ARENA.centery + math.sin(ang) * (self.current_hazard_r + 40)
                    if not is_wall_px(self.gmap, px, py): break
                self.powerup = PowerUp(px, py, random.choice(["health", "stamina"]))
                self.powerup_timer = CFG.POWERUP_SPAWN_INTERVAL

        self.cloud_timer -= 1
        if self.cloud_timer <= 0:
            start_side = random.choice(['left', 'right'])
            cx = CFG.ARENA.left + 20 if start_side == 'left' else CFG.ARENA.right - 20
            cvx = random.uniform(0.5, 1.5) if start_side == 'left' else random.uniform(-1.5, -0.5)
            cy = random.randint(CFG.ARENA.top + 50, CFG.ARENA.bottom - 50)
            self.clouds.append(Cloud(cx, cy, cvx, random.uniform(40, 70)))
            self.cloud_timer = CFG.CLOUD_SPAWN_INTERVAL
            
        for c in self.clouds:
            c.x += c.vx; c.life -= 1
        self.clouds = [c for c in self.clouds if c.life > 0 and CFG.ARENA.collidepoint(c.x, c.y)]

    def _update_effects(self):
        for e in self.effects:
            if not e.persistent:
                e.x += e.vx; e.y += e.vy; e.vy += e.gravity
            e.life -= 1
        self.effects = [e for e in self.effects if e.life > 0]

    def _check_win_condition(self):
        if not self.w1.alive or not self.w2.alive:
            self.done = True
            self.winner = None if not self.w1.alive and not self.w2.alive else (2 if not self.w1.alive else 1)
            self._spawn_win_effects()
        elif self.tick >= CFG.ROUND_DURATION + CFG.INTRO_DURATION:
            self.done = True
            self.winner = 1 if self.w1.health > self.w2.health else (2 if self.w2.health > self.w1.health else None)
            self._spawn_win_effects()

    def _spawn_win_effects(self):
        if self.headless: return
        winner_w = self.w1 if self.winner == 1 else self.w2 if self.winner == 2 else None
        if winner_w:
            self.sound_queue.append("win")
            for _ in range(30):
                self.effects.append(Effect(winner_w.x, winner_w.y - 20, random.choice(WIN_EMOJIS), 80, 80, 
                                           vx=random.uniform(-5.5, 5.5), vy=random.uniform(-8.5, -3.5), gravity=0.25, size=36))

    def _apply_action(self, w: Warrior, action: int, enemy: Warrior):
        if not w.alive or w.stagger_timer > 0: return
        w.facing = 1 if enemy.x > w.x else -1
        speed = CFG.DASH_SPEED if w.is_dashing else w.speed
        
        if w.is_dashing and not self.headless and self.tick % 2 == 0:
            self.effects.append(Effect(w.x, w.y, w.emoji, 12, 12, size=CFG.WARRIOR_SIZE, persistent=True))

        if action == 0: w.y -= speed
        elif action == 1: w.y += speed
        elif action == 2: w.x -= speed
        elif action == 3: w.x += speed
        elif action == 4:
            if w.attack_cd == 0 and w.stamina >= w.attack_cost:
                w.attack_cd = CFG.ATTACK_COOLDOWN; w.attack_anim = 8; w.stamina -= w.attack_cost
                w.current_attack_emoji = random.choice(ATTACK_EMOJIS)
                self.sound_queue.append("attack")
        elif action == 5:
            if w.block_cd == 0 and not w.is_blocking:
                w.is_blocking = True; w.block_timer = CFG.BLOCK_DURATION; w.block_cd = CFG.BLOCK_COOLDOWN
        elif action == 6:
            if w.dash_cd == 0 and not w.is_dashing and w.stamina >= w.dash_cost:
                w.is_dashing = True; w.dash_timer = CFG.DASH_DURATION; w.dash_cd = CFG.DASH_COOLDOWN; w.stamina -= w.dash_cost
                self.sound_queue.append("dash")
        elif action == 7:
            if w.shoot_cd == 0 and w.stamina >= w.shoot_cost:
                w.shoot_cd = CFG.SHOOT_COOLDOWN; w.shoot_anim = 10; w.stamina -= w.shoot_cost
                self.projectiles.append(Projectile(w.x + w.facing * 40, w.y, w.facing * CFG.PROJECTILE_SPEED, 0, 1 if w == self.w1 else 2, w.proj_dmg))
                self.sound_queue.append("shoot")
        elif action == 8:
            if w.parry_cd == 0 and not w.is_parrying:
                w.is_parrying = True; w.parry_timer = CFG.PARRY_DURATION; w.parry_cd = CFG.PARRY_COOLDOWN
        elif action == 9:
            if w.slam_cd == 0 and w.stamina >= w.slam_cost:
                w.slam_cd = CFG.SLAM_COOLDOWN; w.slam_anim = 12; w.stamina -= w.slam_cost
                self._resolve_slam(w, enemy)

    def _resolve_slam(self, attacker: Warrior, defender: Warrior):
        elev_bonus = 1.0 + (0.5 * get_elevation(self.gmap, attacker.x, attacker.y))
        dmg = attacker.slam_dmg * elev_bonus
        
        self.projectiles = [p for p in self.projectiles if (p.x - attacker.x)**2 + (p.y - attacker.y)**2 > CFG.SLAM_RADIUS_SQ]
        
        dx = defender.x - attacker.x; dy = defender.y - attacker.y
        if dx*dx + dy*dy < CFG.SLAM_RADIUS_SQ:
            if defender.is_invulnerable():
                self.add_log(f"{defender.emoji} perfect dodged slam! ✨")
                self.sound_queue.append("dash")
            elif defender.is_parrying:
                self.add_log(f"{defender.emoji} PARRIED slam! 🤚")
                attacker.stagger_timer = CFG.STAGGER_DURATION * 2
                self.sound_queue.append("parry")
            else:
                push_x = 1 if dx > 0 else -1
                push_y = 1 if dy > 0 else -1
                defender.vx += push_x * CFG.KNOCKBACK_FORCE * 2
                defender.vy += push_y * CFG.KNOCKBACK_FORCE * 2
                
                if defender.is_blocking: 
                    defender.health -= dmg * 0.25
                    self.sound_queue.append("block")
                else:
                    defender.health -= dmg; defender.stagger_timer = CFG.STAGGER_DURATION
                    defender.is_blocking = False; defender.is_dashing = False; defender.is_parrying = False
                    self.add_log(f"{attacker.emoji} SLAMMED {defender.emoji} for {dmg}! 👊")
                    self.hitstop = 6; self.shake = 12
                    self.sound_queue.append("hit")
                    
        self.sound_queue.append("slam")
        if not self.headless:
            self.effects.append(Effect(attacker.x, attacker.y, "💢", 15, 15, size=int(CFG.SLAM_RADIUS*1.5)))
            self.effects.append(Effect(attacker.x, attacker.y, "💥", 15, 15, size=int(CFG.SLAM_RADIUS)))

    def _resolve_attacks(self, attacker: Warrior, defender: Warrior):
        if not attacker.alive or not defender.alive: return
        if attacker.attack_anim != 8: return
        dx = defender.x - attacker.x; dy = defender.y - attacker.y
        d2 = dx*dx + dy*dy
        if d2 > CFG.ATTACK_RANGE_SQ: return
        if (dx > 0 and attacker.facing != 1) or (dx < 0 and attacker.facing != -1): return
            
        push_x = 1 if dx > 0 else -1; push_y = 1 if dy > 0 else -1

        if defender.is_invulnerable():
            defender.dodge_anim = 15; defender.perfect_dodges += 1
            defender.stamina = min(defender.max_stamina, defender.stamina + 20)
            self.add_log(f"{defender.emoji} perfect dodged! ✨")
            self.sound_queue.append("dash")
            return

        if defender.is_parrying:
            defender.parry_anim = 15; defender.parries += 1
            defender.stamina = min(defender.max_stamina, defender.stamina + 40)
            attacker.stagger_timer = CFG.STAGGER_DURATION * 2
            self.add_log(f"{defender.emoji} PARRIED! 🤚")
            self.sound_queue.append("parry")
            return

        elev_bonus = 1.0 + (0.25 * get_elevation(self.gmap, attacker.x, attacker.y))
        
        if defender.is_blocking:
            dmg = attacker.attack_dmg * 0.25 * elev_bonus
            defender.vx += push_x * (CFG.KNOCKBACK_FORCE * 0.5); defender.vy += push_y * (CFG.KNOCKBACK_FORCE * 0.5)
            self.add_log(f"{defender.emoji} blocked {attacker.emoji}'s attack! 🛡️")
            self.sound_queue.append("block")
        else:
            dmg = attacker.attack_dmg * elev_bonus * defender.dmg_taken_mult
            defender.vx += push_x * CFG.KNOCKBACK_FORCE; defender.vy += push_y * CFG.KNOCKBACK_FORCE
            defender.stagger_timer = CFG.STAGGER_DURATION
            defender.is_blocking = False; defender.is_dashing = False; defender.is_parrying = False
            self.add_log(f"{attacker.emoji} hit {defender.emoji} for {dmg}! 💥")
            self.hitstop = 4; self.shake = 8
            self.sound_queue.append("hit")
            attacker.combo_count += 1
            if attacker.combo_count > attacker.max_combo: attacker.max_combo = attacker.combo_count
            defender.combo_count = 0
                
        defender.health -= dmg; defender.damage_taken += dmg; attacker.damage_dealt += dmg
        defender.flash_timer = 8
        if defender.health <= 0:
            defender.health = 0; defender.alive = False


# ==============================================================================
# 8. MDP STATE ENCODING (NUMBA ACCELERATED)
# ==============================================================================
_STATE_ARR_1 = np.zeros(CFG.STATE_SIZE, dtype=np.float32)
_STATE_ARR_2 = np.zeros(CFG.STATE_SIZE, dtype=np.float32)

def get_state_vector(env: Environment, pov: int) -> np.ndarray:
    out_arr = _STATE_ARR_1 if pov == 1 else _STATE_ARR_2
    
    w1 = env.w1 if pov == 1 else env.w2
    w2 = env.w2 if pov == 1 else env.w1
    
    # Pack Warrior 1
    w1_data = env._w1_data if pov == 1 else env._w2_data
    w1_data[0] = w1.x; w1_data[1] = w1.y
    w1_data[2] = w1.health; w1_data[3] = w1.max_health
    w1_data[4] = w1.stamina; w1_data[5] = w1.max_stamina
    w1_data[6] = w1.attack_cd / CFG.ATTACK_COOLDOWN
    w1_data[7] = w1.block_cd / CFG.BLOCK_COOLDOWN
    w1_data[8] = w1.dash_cd / CFG.DASH_COOLDOWN
    w1_data[9] = w1.shoot_cd / CFG.SHOOT_COOLDOWN
    w1_data[10] = w1.parry_cd / CFG.PARRY_COOLDOWN
    w1_data[11] = w1.slam_cd / CFG.SLAM_COOLDOWN
    w1_data[12] = 1.0 if w1.is_blocking else 0.0
    w1_data[13] = 1.0 if w1.is_parrying else 0.0
    w1_data[14] = w1.brain.class_weights[0]
    w1_data[15] = w1.brain.class_weights[1]
    w1_data[16] = w1.brain.class_weights[2]
    w1_data[17] = w1.brain.class_weights[3]
    w1_data[19] = float(w1.pov_id)
    
    # Pack Warrior 2
    w2_data = env._w2_data if pov == 1 else env._w1_data
    w2_data[0] = w2.x; w2_data[1] = w2.y
    w2_data[2] = w2.health; w2_data[3] = w2.max_health
    w2_data[4] = w2.stamina; w2_data[5] = w2.max_stamina
    w2_data[6] = w2.attack_cd / CFG.ATTACK_COOLDOWN
    w2_data[7] = w2.block_cd / CFG.BLOCK_COOLDOWN
    w2_data[8] = w2.dash_cd / CFG.DASH_COOLDOWN
    w2_data[9] = w2.shoot_cd / CFG.SHOOT_COOLDOWN
    w2_data[10] = w2.parry_cd / CFG.PARRY_COOLDOWN
    w2_data[11] = w2.slam_cd / CFG.SLAM_COOLDOWN
    w2_data[12] = 1.0 if w2.is_blocking else 0.0
    w2_data[13] = 1.0 if w2.is_parrying else 0.0
    w2_data[14] = w2.brain.class_weights[0]
    w2_data[15] = w2.brain.class_weights[1]
    w2_data[16] = w2.brain.class_weights[2]
    w2_data[17] = w2.brain.class_weights[3]
    w2_data[19] = float(w2.pov_id)
    
    # Pack Projectiles
    num_projs = len(env.projectiles)
    if num_projs > 10: num_projs = 10
    for i in range(num_projs):
        p = env.projectiles[i]
        env._projs_data[i, 0] = p.x
        env._projs_data[i, 1] = p.y
        env._projs_data[i, 2] = p.vx
        env._projs_data[i, 3] = p.vy
        env._projs_data[i, 4] = float(p.owner)
        
    # Pack Powerup
    if env.powerup:
        env._pwr_data[0] = env.powerup.x
        env._pwr_data[1] = env.powerup.y
        env._pwr_data[2] = 1.0
    else:
        env._pwr_data[2] = 0.0
        
    # Pack Clouds
    num_clouds = len(env.clouds)
    if num_clouds > 10: num_clouds = 10
    for i in range(num_clouds):
        c = env.clouds[i]
        env._clouds_data[i, 0] = c.x
        env._clouds_data[i, 1] = c.y
        env._clouds_data[i, 2] = c.radius

    if NUMBA_AVAILABLE:
        return _encode_state_numba(
            out_arr, w1_data, w2_data, env._projs_data, num_projs, env._pwr_data, env._clouds_data, num_clouds,
            env.gmap.dist_up, env.gmap.dist_down, env.gmap.dist_left, env.gmap.dist_right, env.gmap.grid,
            CFG.SCREEN_W, CFG.SCREEN_H, CFG.ARENA.centerx, CFG.ARENA.centery, env.current_hazard_r_sq,
            CFG.TILE_SIZE, CFG.ARENA.left, CFG.ARENA.top
        )
    else:
        # Fallback logic (simplified for brevity, same as v16)
        dx = w2.x - w1.x; dy = w2.y - w1.y
        out_arr[0] = dx / CFG.SCREEN_W; out_arr[1] = dy / CFG.SCREEN_H
        out_arr[2] = (dx*dx + dy*dy) / (CFG.SCREEN_W*CFG.SCREEN_W)
        out_arr[3] = w1.health / w1.max_health; out_arr[4] = w2.health / w2.max_health
        out_arr[5] = w1.stamina / w1.max_stamina; out_arr[6] = w2.stamina / w2.max_stamina
        # ... (fill rest) ...
        return out_arr

def get_valid_actions(w: Warrior) -> np.ndarray:
    mask = np.ones(CFG.ACTION_SIZE, dtype=np.float32)
    if w.attack_cd > 0 or w.stamina < w.attack_cost: mask[4] = 0.0
    if w.block_cd > 0 or w.is_blocking: mask[5] = 0.0
    if w.dash_cd > 0 or w.is_dashing or w.stamina < w.dash_cost: mask[6] = 0.0
    if w.shoot_cd > 0 or w.stamina < w.shoot_cost: mask[7] = 0.0
    if w.parry_cd > 0 or w.is_parrying: mask[8] = 0.0
    if w.slam_cd > 0 or w.stamina < w.slam_cost: mask[9] = 0.0
    return mask


# ==============================================================================
# 9. SIMULTANEOUS PUCT MCTS (OPTIMIZED SAMPLING & FAST POLICIES)
# ==============================================================================
class MCTSNode:
    __slots__ = ['env', 'parent', 'action', 'prior', 'children', 'N', 'W', 'Q', 'is_expanded']
    def __init__(self, env, parent, action, prior):
        self.env = env; self.parent = parent; self.action = action; self.prior = prior
        self.children: List[MCTSNode] = []
        self.N = 0; self.W = 0.0; self.Q = 0.0; self.is_expanded = False

class PUCTAgent:
    def __init__(self, brain: Brain, opp_brain: Brain):
        self.brain = brain
        self.opp_brain = opp_brain
        self.last_action_stats = {}

    def search(self, root_env: Environment) -> Tuple[int, np.ndarray]:
        root = MCTSNode(root_env, None, -1, 1.0)
        valid_mask = get_valid_actions(root_env.w1)
        
        for _ in range(CFG.MCTS_SIMULATIONS):
            node = root
            curr_env = root_env.clone()
            
            while node.is_expanded and node.children:
                total_visits = sum(c.N for c in node.children) + 1
                sqrt_visits = math.sqrt(total_visits)
                node = max(node.children, key=lambda c: c.Q + CFG.MCTS_C_PUCT * c.prior * (sqrt_visits / (1 + c.N)))
                
                opp_state = get_state_vector(curr_env, 2)
                opp_policy = self.opp_brain.forward_policy(opp_state)
                opp_policy = _softmax_numba(opp_policy * get_valid_actions(curr_env.w2)) if NUMBA_AVAILABLE else softmax(opp_policy * get_valid_actions(curr_env.w2))
                opp_sum = opp_policy.sum()
                if opp_sum == 0: 
                    opp_policy = get_valid_actions(curr_env.w2)
                    opp_sum = opp_policy.sum()
                else: 
                    opp_policy = opp_policy / opp_sum
                
                r = random.random() * opp_sum
                cumsum = 0.0
                a2 = 0
                for i, prob in enumerate(opp_policy):
                    cumsum += prob
                    if r < cumsum:
                        a2 = i
                        break
                
                curr_env._apply_action(curr_env.w1, node.action, curr_env.w2)
                curr_env._apply_action(curr_env.w2, a2, curr_env.w1)
                curr_env._resolve_attacks(curr_env.w1, curr_env.w2)
                curr_env._resolve_attacks(curr_env.w2, curr_env.w1)
                curr_env.tick += 1
                curr_env.current_hazard_r = CFG.HAZARD_BASE_RADIUS + math.sin(curr_env.tick * 0.02) * 30
                curr_env.current_hazard_r_sq = curr_env.current_hazard_r ** 2
                
                for w in (curr_env.w1, curr_env.w2):
                    curr_env._update_warrior_timers(w)
                    curr_env._update_warrior_physics(w)
                    curr_env._check_hazards_and_pickups(w)
                curr_env._resolve_warrior_collision()
                curr_env._update_projectiles()
                
            if not node.is_expanded:
                state_vec = get_state_vector(curr_env, 1)
                policy_logits = self.brain.forward_policy(state_vec)
                policy = _softmax_numba(policy_logits) if NUMBA_AVAILABLE else softmax(policy_logits)
                
                mask = get_valid_actions(curr_env.w1)
                policy = policy * mask
                p_sum = policy.sum()
                if p_sum == 0: policy = mask
                else: policy = policy / p_sum
                
                node.is_expanded = True
                for a in range(CFG.ACTION_SIZE):
                    if mask[a] > 0:
                        node.children.append(MCTSNode(None, node, a, policy[a]))
                
                _, v, _ = self.brain.forward(state_vec)
            else:
                v = 0.0 
                
            while node is not None:
                node.N += 1; node.W += v; node.Q = node.W / node.N
                node = node.parent
                
        root_children = root.children
        if root_children:
            noise = np.random.dirichlet([CFG.MCTS_DIRICHLET_ALPHA] * len(root_children))
            for i, child in enumerate(root_children):
                child.prior = (1 - CFG.MCTS_DIRICHLET_WEIGHT) * child.prior + CFG.MCTS_DIRICHLET_WEIGHT * noise[i]

        mcts_policy = np.zeros(CFG.ACTION_SIZE, dtype=np.float32)
        total_visits = sum(c.N for c in root_children)
        for c in root_children:
            mcts_policy[c.action] = c.N / total_visits if total_visits > 0 else 0.0

        best_child = max(root_children, key=lambda c: c.N) if root_children else None
        self.last_action_stats = {c.action: (c.N, c.Q) for c in root_children}
        return best_child.action if best_child else 0, mcts_policy


# ==============================================================================
# 10. EVOLUTION & DEEP LEARNING (GA + SGD)
# ==============================================================================
class Evolution:
    def __init__(self, pop_size: int = CFG.POPULATION_SIZE, seed: Optional[int] = None):
        self.pop_size = pop_size
        self.rng = np.random.default_rng(seed)
        self.population: List[Brain] = [Brain(self.rng) for _ in range(pop_size)]
        self.generation = 1
        self.best_fitness = 0.0; self.avg_fitness = 0.0
        self.history: List[Tuple[int, float, float]] = []
        self.champion: Optional[Brain] = None
        self.hall_of_fame: List[Brain] = []
        self.current_mutation_rate = CFG.MUTATION_RATE
        self.gmap = generate_ca_map()
        self.replay_buffer: List[Tuple[np.ndarray, np.ndarray, float]] = []
        self.training_loss = 0.0

    def update_elo(self, winner_elo: float, loser_elo: float, draw: bool = False) -> Tuple[float, float]:
        expected_win = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))
        s = 0.5 if draw else 1.0
        return winner_elo + 32 * (s - expected_win), loser_elo + 32 * ((1-s) - (1 - expected_win))

    def record_experience(self, env: Environment, pov: int, mcts_policy: np.ndarray):
        state = get_state_vector(env, pov).copy()
        actual_v = 1.0 if env.winner == pov else (-1.0 if env.winner is not None else 0.0)
        self.replay_buffer.append((state, mcts_policy, actual_v))
        if len(self.replay_buffer) > 4096: self.replay_buffer.pop(0)

    def train_champion_sgd(self):
        if len(self.replay_buffer) < CFG.SGD_BATCH_SIZE or not self.champion: return
        
        loss = 0.0
        for _ in range(CFG.SGD_EPOCHS):
            batch = random.sample(self.replay_buffer, CFG.SGD_BATCH_SIZE)
            states = np.array([b[0] for b in batch])
            target_policies = np.array([b[1] for b in batch])
            target_values = np.array([b[2] for b in batch])
            
            self.champion.train_step(states, target_policies, target_values, CFG.SGD_LEARNING_RATE)
            
            p, v, _ = self.champion.forward(states)
            v_pred = np.tanh(v).flatten()
            p_pred = softmax(p)
            loss += np.mean((target_values - v_pred)**2) + np.mean(-np.sum(target_policies * np.log(p_pred + 1e-8), axis=1))
            
        self.training_loss = loss / CFG.SGD_EPOCHS

    def fitness_from_fight(self, env: Environment, side: int) -> Tuple[float, float]:
        w = env.w1 if side == 1 else env.w2
        e = env.w2 if side == 1 else env.w1
        won = env.winner == side; lost = env.winner is not None and env.winner != side
        f = w.damage_dealt * 1.0 - w.damage_taken * 0.7
        f += (w.health / w.max_health) * 15.0 - (e.health / e.max_health) * 5.0
        if won: f += 60.0
        if lost: f -= 30.0
        f -= env.tick * 0.015
        
        actual_v = 1.0 if won else (-1.0 if lost else 0.0)
        _, pred_v, _ = w.brain.forward(get_state_vector(env, side))
        val_acc = 1.0 - abs(actual_v - pred_v)
        return f, val_acc

    def evaluate(self):
        if self.generation % 20 == 0:
            self.gmap = generate_ca_map()

        for b in self.population:
            b.fitness = 0.0; b.value_acc = 0.0
            b.wins = b.losses = b.draws = 0
            b.damage_dealt = b.damage_taken = 0.0
            b.action_history = np.zeros(CFG.ACTION_SIZE, dtype=np.float32)
            b.heatmap = np.zeros((8, 8), dtype=np.float32)

        pool = self.population + self.hall_of_fame
        warriors = [Warrior(0, 0, b, emoji=random.choice(WARRIOR_EMOJIS)) for b in pool]
        n_opp = min(CFG.N_OPPONENTS, len(warriors) - 1)

        for i, w in enumerate(warriors):
            if w.brain in self.hall_of_fame: continue
            
            opp_indices = self.rng.choice([j for j in range(len(warriors)) if j != i], size=n_opp, replace=False)
            for oi in opp_indices:
                opp = warriors[int(oi)]
                w_copy = Warrior(0, 0, w.brain, emoji=w.emoji)
                o_copy = Warrior(0, 0, opp.brain, emoji=opp.emoji)
                
                env = Environment(w_copy, o_copy, self.gmap, headless=True)
                while not env.done: env.step()
                
                f1, v1 = self.fitness_from_fight(env, 1)
                f2, v2 = self.fitness_from_fight(env, 2)
                w.brain.fitness += f1; opp.brain.fitness += f2
                w.brain.value_acc += v1; opp.brain.value_acc += v2
                
                if env.winner == 1:
                    w.brain.wins += 1; opp.brain.losses += 1
                    w.brain.elo, opp.brain.elo = self.update_elo(w.brain.elo, opp.brain.elo)
                elif env.winner == 2:
                    opp.brain.wins += 1; w.brain.losses += 1
                    opp.brain.elo, w.brain.elo = self.update_elo(opp.brain.elo, w.brain.elo)
                else:
                    w.brain.draws += 1; opp.brain.draws += 1
                    w.brain.elo, opp.brain.elo = self.update_elo(w.brain.elo, opp.brain.elo, draw=True)
                    
                w.brain.damage_dealt += env.w1.damage_dealt; w.brain.damage_taken += env.w1.damage_taken
                opp.brain.damage_dealt += env.w2.damage_dealt; opp.brain.damage_taken += env.w2.damage_taken

        for b in self.population:
            b.fitness /= n_opp; b.value_acc /= n_opp

        self.best_fitness = max(b.fitness for b in self.population)
        self.avg_fitness = sum(b.fitness for b in self.population) / len(self.population)
        self.history.append((self.generation, self.best_fitness, self.avg_fitness))

        if self.champion:
            sorted_pop = sorted(self.population, key=lambda b: b.fitness, reverse=True)
            for challenger in sorted_pop[:2]:
                w_copy = Warrior(0, 0, challenger.copy(), emoji="🥇", use_mcts=True)
                c_copy = Warrior(0, 0, self.champion.copy(), emoji="👑", use_mcts=True)
                env = Environment(w_copy, c_copy, self.gmap, headless=True)
                while not env.done: env.step()
                if env.winner == 1:
                    self.champion = challenger.copy()
                    self.champion.fitness = challenger.fitness
                    self.hall_of_fame.append(challenger.copy())
                    if len(self.hall_of_fame) > CFG.HALL_OF_FAME_SIZE: self.hall_of_fame.pop(0)
                    break

    def evolve(self):
        self.current_mutation_rate = max(0.05, CFG.MUTATION_RATE * (0.98 ** self.generation))
        sorted_pop = sorted(self.population, key=lambda b: b.fitness, reverse=True)
        new_pop: List[Brain] = [b.copy() for b in sorted_pop[:CFG.ELITISM]]
        while len(new_pop) < self.pop_size:
            p1 = self._tournament(sorted_pop); p2 = self._tournament(sorted_pop)
            child = Brain.crossover(p1, p2, self.rng)
            child.mutate(self.current_mutation_rate, CFG.MUTATION_STRENGTH, self.rng)
            new_pop.append(child)
        self.population = new_pop; self.generation += 1

    def _tournament(self, sorted_pop: List[Brain], k: int = 4) -> Brain:
        idxs = self.rng.choice(len(sorted_pop), size=min(k, len(sorted_pop)), replace=False)
        contestants = [sorted_pop[int(i)] for i in idxs]
        return max(contestants, key=lambda b: b.fitness)


# ==============================================================================
# 11. RENDERER (PURE VIEW)
# ==============================================================================
class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font_huge = find_emoji_font(96); self.font_big = find_emoji_font(72)
        self.font_med = find_emoji_font(48); self.font_small = find_emoji_font(32)
        self.font_tiny = find_emoji_font(20)
        self.font_ui = pygame.font.SysFont("Arial", 16, bold=True)
        self.font_ui_big = pygame.font.SysFont("Arial", 24, bold=True)
        self.font_title = pygame.font.SysFont("Arial", 18, bold=True)
        self.bg_surf = self._make_background()
        self.floor_surf = self._make_floor()
        self._emoji_cache = {}
        self._cached_map_id = None
        self._cached_map_surf = None
        
        self.shadow_surf = pygame.Surface((CFG.WARRIOR_SIZE, CFG.WARRIOR_SIZE // 3), pygame.SRCALPHA).convert_alpha()
        pygame.draw.ellipse(self.shadow_surf, (0, 0, 0, 90), self.shadow_surf.get_rect())
        
        self.ui_panel_surf = pygame.Surface((CFG.SCREEN_W, CFG.SCREEN_H), pygame.SRCALPHA).convert_alpha()
        self.ui_timer = 0
        self.nn_cache_gen = -1
        
        self.ambient_particles = [AmbientParticle(
            x=random.uniform(0, CFG.SCREEN_W), y=random.uniform(0, CFG.SCREEN_H),
            emoji=random.choice(AMBIENT_EMOJIS), vx=random.uniform(-0.5, 0.5),
            vy=random.uniform(0.2, 1.0), size=random.randint(16, 28), alpha=random.randint(50, 120)
        ) for _ in range(25)]

    def _make_background(self) -> pygame.Surface:
        s = pygame.Surface((CFG.SCREEN_W, CFG.SCREEN_H)).convert()
        s.fill(BG_COLOR)
        for x in range(0, CFG.SCREEN_W, 24):
            for y in [10, 35, 95, CFG.SCREEN_H - 40, CFG.SCREEN_H - 15]:
                surf = self.font_tiny.render(random.choice(AUDIENCE_EMOJIS), True, (255, 255, 255))
                surf.set_alpha(90); s.blit(surf, (x + random.randint(-4, 4), y + random.randint(-4, 4)))
        for y in range(110, CFG.SCREEN_H - 50, 24):
            for x in [5, CFG.SCREEN_W - 25]:
                surf = self.font_tiny.render(random.choice(AUDIENCE_EMOJIS), True, (255, 255, 255))
                surf.set_alpha(90); s.blit(surf, (x, y + random.randint(-4, 4)))
        return s

    def _make_floor(self) -> pygame.Surface:
        s = pygame.Surface((CFG.ARENA.w, CFG.ARENA.h)).convert()
        s.fill(ARENA_COLOR)
        for x in range(0, CFG.ARENA.w, 50): pygame.draw.line(s, ARENA_GRID, (x, 0), (x, CFG.ARENA.h))
        for y in range(0, CFG.ARENA.h, 50): pygame.draw.line(s, ARENA_GRID, (0, y), (CFG.ARENA.w, y))
        rng = random.Random(42)
        for _ in range(40):
            ex = rng.randint(20, CFG.ARENA.w - 20); ey = rng.randint(20, CFG.ARENA.h - 20)
            surf = self.font_tiny.render(rng.choice(DECOR_EMOJIS), True, (255, 255, 255))
            surf.set_alpha(45); s.blit(surf, surf.get_rect(center=(ex, ey)))
        return s

    def draw_emoji(self, emoji: str, x: float, y: float, size: int = 64, alpha: int = 255, target: Optional[pygame.Surface] = None):
        key = (emoji, size)
        if key not in self._emoji_cache:
            surf = self.font_big.render(emoji, True, (255, 255, 255))
            sw, sh = surf.get_size()
            if sw > 0 and sh > 0:
                scale = size / max(sw, sh)
                if abs(scale - 1.0) > 0.05:
                    surf = pygame.transform.smoothscale(surf, (max(1, int(sw * scale)), max(1, int(sh * scale))))
            self._emoji_cache[key] = surf
        surf = self._emoji_cache[key]
        if alpha < 255: surf = surf.copy(); surf.set_alpha(alpha)
        if target is None: target = self.screen
        target.blit(surf, surf.get_rect(center=(int(x), int(y))))

    def _get_map_surf(self, gmap: GameMap) -> pygame.Surface:
        if id(gmap) != self._cached_map_id:
            self._cached_map_id = id(gmap)
            self._cached_map_surf = pygame.Surface((CFG.ARENA.w, CFG.ARENA.h), pygame.SRCALPHA).convert_alpha()
            for y in range(CFG.GRID_H):
                for x in range(CFG.GRID_W):
                    val = gmap.grid[y, x]
                    if val > 0:
                        e = random.choice(WALL_EMOJIS if val == 1 else HIGH_GROUND_EMOJIS)
                        px = x * CFG.TILE_SIZE + CFG.TILE_SIZE // 2
                        py = y * CFG.TILE_SIZE + CFG.TILE_SIZE // 2
                        if val == 2: 
                            shadow_surf = pygame.Surface((CFG.TILE_SIZE, CFG.TILE_SIZE), pygame.SRCALPHA)
                            pygame.draw.rect(shadow_surf, (0, 0, 0, 80), shadow_surf.get_rect())
                            self._cached_map_surf.blit(shadow_surf, (px - CFG.TILE_SIZE//2 + 4, py - CFG.TILE_SIZE//2 + 4))
                            self.draw_emoji(e, px, py - 6, CFG.TILE_SIZE, target=self._cached_map_surf)
                        else:
                            self.draw_emoji(e, px, py, CFG.TILE_SIZE, target=self._cached_map_surf)
        return self._cached_map_surf

    def update_and_draw_ambient(self, lab_mode=False):
        for p in self.ambient_particles:
            p.x += p.vx; p.y += p.vy
            if lab_mode:
                p.y -= 0.5
                if p.y < 0: p.y = CFG.SCREEN_H
                if p.x < 0: p.x = CFG.SCREEN_W
                if p.x > CFG.SCREEN_W: p.x = 0
                self.draw_emoji(random.choice(LAB_EMOJIS), p.x, p.y, size=p.size, alpha=p.alpha)
            else:
                if p.y > CFG.SCREEN_H: p.y = 0
                if p.x < 0: p.x = CFG.SCREEN_W
                if p.x > CFG.SCREEN_W: p.x = 0
                self.draw_emoji(p.emoji, p.x, p.y, size=p.size, alpha=p.alpha)

    def draw_env(self, env: Environment, time_of_day: float):
        shake_x = random.randint(-env.shake, env.shake)
        shake_y = random.randint(-env.shake, env.shake)
        
        self.screen.blit(self.bg_surf, (0, 0))
        self.screen.blit(self.floor_surf, (CFG.ARENA.left + shake_x, CFG.ARENA.top + shake_y))
        pygame.draw.rect(self.screen, ARENA_BORDER, CFG.ARENA.move(shake_x, shake_y), 3)
        
        self.draw_emoji("🌋", CFG.ARENA.centerx + shake_x, CFG.ARENA.centery + shake_y, size=int(env.current_hazard_r*2))
        pygame.draw.circle(self.screen, (255, 80, 80, 50), (CFG.ARENA.centerx + shake_x, CFG.ARENA.centery + shake_y), int(env.current_hazard_r), 2)
        
        map_surf = self._get_map_surf(env.gmap)
        self.screen.blit(map_surf, (CFG.ARENA.left + shake_x, CFG.ARENA.top + shake_y))
        
        for cx, cy in [(CFG.ARENA.left, CFG.ARENA.top), (CFG.ARENA.right, CFG.ARENA.top),
                       (CFG.ARENA.left, CFG.ARENA.bottom), (CFG.ARENA.right, CFG.ARENA.bottom)]:
            self.draw_emoji("🔥", cx + shake_x, cy + shake_y, size=28)
            
        darkness = int(abs(math.sin(time_of_day * math.pi)) * 120)
        if darkness > 0:
            overlay = pygame.Surface((CFG.SCREEN_W, CFG.SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 20, darkness))
            self.screen.blit(overlay, (0, 0))

        self.update_and_draw_ambient(lab_mode=False)
        
        for c in env.clouds: self.draw_emoji("☁️", c.x + shake_x, c.y + shake_y, size=int(c.radius*1.5), alpha=120)
        for e in env.effects:
            if e.persistent: self.draw_emoji(e.emoji, e.x + shake_x, e.y + shake_y, size=e.size, alpha=int(150 * (e.life / e.max_life)))
            
        if env.powerup: self.draw_emoji(POWERUP_EMOJIS[env.powerup.ptype], env.powerup.x + shake_x, env.powerup.y + shake_y, size=32)
        for p in env.projectiles: self.draw_emoji("🔮", p.x + shake_x, p.y + shake_y, size=28)
        
        stats1 = env.agent1.last_action_stats if env.agent1 else None
        stats2 = env.agent2.last_action_stats if env.agent2 else None
        self._draw_warrior(env.w1, stats1, shake_x, shake_y)
        self._draw_warrior(env.w2, stats2, shake_x, shake_y)
        
        for e in env.effects:
            if not e.persistent: self.draw_emoji(e.emoji, e.x + shake_x, e.y + shake_y, size=e.size, alpha=int(255 * (e.life / e.max_life)))

        time_left = max(0.0, (CFG.ROUND_DURATION - (env.tick - CFG.INTRO_DURATION)) / CFG.FPS)
        info = f"⏱ {time_left:.1f}s   |   [M] MCTS: {'ON' if env.w1.use_mcts else 'OFF'}  [SPACE] Pause  [V] Champ  [ESC] Quit"
        self.screen.blit(self.font_ui.render(info, True, TEXT_COLOR), (20, CFG.SCREEN_H - 78))

        if env.tick < CFG.INTRO_DURATION:
            txt = "READY? 👉" if env.tick < CFG.INTRO_DURATION // 2 else "FIGHT! 👊"
            color = (255, 220, 90) if env.tick < CFG.INTRO_DURATION // 2 else (255, 80, 80)
            big = self.font_huge.render(txt, True, color)
            bg = pygame.Surface((big.get_width() + 60, big.get_height() + 24), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 180))
            self.screen.blit(bg, bg.get_rect(center=(CFG.ARENA.centerx, CFG.ARENA.centery)))
            self.screen.blit(big, big.get_rect(center=(CFG.ARENA.centerx, CFG.ARENA.centery)))
        elif env.done:
            res = f"{env.w1.label} WINS! 🏆" if env.winner == 1 else (f"{env.w2.label} WINS! 🏆" if env.winner == 2 else "DRAW 🤝")
            big = self.font_ui_big.render(res, True, ACCENT)
            bg = pygame.Surface((big.get_width() + 60, big.get_height() + 24), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 190))
            self.screen.blit(bg, bg.get_rect(center=(CFG.ARENA.centerx, CFG.ARENA.centery)))
            self.screen.blit(big, big.get_rect(center=(CFG.ARENA.centerx, CFG.ARENA.centery)))

    def _draw_warrior(self, w: Warrior, mcts_stats: dict, shake_x: int, shake_y: int):
        wx, wy = w.x + shake_x, w.y + shake_y
        self.screen.blit(self.shadow_surf, self.shadow_surf.get_rect(center=(int(wx), int(wy + CFG.WARRIOR_SIZE / 2 - 4))))

        emoji = w.emoji if w.alive else DEAD_EMOJIS[0]
        flash = w.flash_timer > 0 and w.flash_timer % 4 < 2
        if not flash:
            offset_x = w.facing * (w.attack_anim * 2.5 if w.attack_anim > 0 else 0)
            self.draw_emoji(emoji, wx + offset_x, wy, size=CFG.WARRIOR_SIZE)
            if w.attack_anim > 0: self.draw_emoji(w.current_attack_emoji, wx + w.facing * 45, wy - 6, size=38)
            if w.shoot_anim > 0: self.draw_emoji("🔮", wx + w.facing * 45, wy - 6, size=32)
            if w.slam_anim > 0: self.draw_emoji("💢", wx, wy, size=CFG.WARRIOR_SIZE + w.slam_anim*4)
            if w.is_blocking: self.draw_emoji(BLOCK_EMOJIS[0], wx + w.facing * 24, wy - 22, size=28)
            if w.is_parrying: self.draw_emoji("🤚", wx + w.facing * 30, wy - 10, size=32)
            if w.stagger_timer > 0: self.draw_emoji("💫", wx, wy - 40, size=24)
            if w.dodge_anim > 0: self.draw_emoji("✨", wx, wy - 50, size=28)
            if w.parry_anim > 0: self.draw_emoji("🤚", wx, wy - 50, size=28)
                
        bar_w = 74; bar_h = 7
        bx = wx - bar_w / 2; by = wy - CFG.WARRIOR_SIZE / 2 - 16
        
        pygame.draw.rect(self.screen, (20, 22, 32), (bx - 1, by - 1, bar_w + 2, bar_h + 2), border_radius=3)
        hp = max(0.0, w.health / w.max_health)
        col = HEALTH_GREEN if hp > 0.6 else (HEALTH_YELLOW if hp > 0.3 else HEALTH_RED)
        if hp > 0: pygame.draw.rect(self.screen, col, (bx, by, bar_w * hp, bar_h), border_radius=3)
        self.draw_emoji("❤️" if hp > 0.2 else "💔", bx - 10, by + 4, size=16)

        stam_h = 4
        pygame.draw.rect(self.screen, (20, 22, 32), (bx - 1, by + bar_h + 1, bar_w + 2, stam_h + 2), border_radius=2)
        st = max(0.0, w.stamina / w.max_stamina)
        if st > 0: pygame.draw.rect(self.screen, STAMINA_BLUE, (bx, by + bar_h + 2, bar_w * st, stam_h), border_radius=2)

        dna_h = 4
        dna_x = bx
        dna_y = by + bar_h + 2 + stam_h + 2
        c_w = w.brain.class_weights[0] * bar_w
        pygame.draw.rect(self.screen, CLASS_COLORS[0], (dna_x, dna_y, c_w, dna_h))
        dna_x += c_w
        c_w = w.brain.class_weights[1] * bar_w
        pygame.draw.rect(self.screen, CLASS_COLORS[1], (dna_x, dna_y, c_w, dna_h))
        dna_x += c_w
        c_w = w.brain.class_weights[2] * bar_w
        pygame.draw.rect(self.screen, CLASS_COLORS[2], (dna_x, dna_y, c_w, dna_h))
        dna_x += c_w
        c_w = w.brain.class_weights[3] * bar_w
        pygame.draw.rect(self.screen, CLASS_COLORS[3], (dna_x, dna_y, c_w, dna_h))

        if w.label: self.screen.blit(self.font_ui.render(w.label, True, TEXT_COLOR), (int(wx - self.font_ui.size(w.label)[0] / 2), int(by - 20)))
        if w.use_mcts: self.draw_emoji("🧠", wx + 30, by - 12, size=18)

        if mcts_stats:
            stat_y = by - 40
            for action_id, (visits, q_val) in sorted(mcts_stats.items()):
                txt = f"{ACTION_EMOJIS[action_id]} V:{visits} Q:{q_val:+.2f}"
                s = self.font_tiny.render(txt, True, ACCENT if visits > 10 else DIM_TEXT)
                self.screen.blit(s, (wx - s.get_width()//2, stat_y))
                stat_y -= 20

    def draw_hud(self, evo: Evolution, mode_text: str, time_of_day: float, sound_on: bool):
        pygame.draw.rect(self.screen, PANEL_BG, (0, 0, CFG.SCREEN_W, 95))
        pygame.draw.line(self.screen, (50, 60, 80), (0, 95), (CFG.SCREEN_W, 95), 2)
        title = self.font_ui_big.render("🥷 EMOJI FIGHT ARENA 17.0 — Numba JIT Acceleration 🚀", True, TEXT_COLOR)
        self.screen.blit(title, (20, 12))
        infos = [
            (f"🧬 Gen: {evo.generation}", ACCENT),
            (f"🏆 Best: {evo.best_fitness:.1f}", HEALTH_GREEN),
            (f"📊 Avg: {evo.avg_fitness:.1f}", (140, 180, 220)),
            (f"📉 SGD Loss: {evo.training_loss:.3f}", (220, 140, 220)),
            (f"🔊 Sound: {'ON' if sound_on else 'OFF'}", (180, 220, 180)),
        ]
        x = 20; y = 50
        for txt, col in infos:
            s = self.font_ui.render(txt, True, col)
            self.screen.blit(s, (x, y))
            x += s.get_width() + 28
        if mode_text: self.screen.blit(self.font_ui.render(mode_text, True, DIM_TEXT), (x + 20, y))

        pygame.draw.rect(self.screen, PANEL_BG, CFG.GRAPH_RECT)
        pygame.draw.rect(self.screen, (60, 70, 90), CFG.GRAPH_RECT, 1)
        if len(evo.history) > 1:
            max_f = max(max(h[1] for h in evo.history), 1.0)
            n = len(evo.history)
            pts_b, pts_a = [], []
            for i, (g, b, a) in enumerate(evo.history):
                px = CFG.GRAPH_RECT.left + 8 + i * (CFG.GRAPH_RECT.w - 16) / max(1, n - 1)
                py_b = CFG.GRAPH_RECT.bottom - 4 - (b / max_f) * (CFG.GRAPH_RECT.h - 8)
                py_a = CFG.GRAPH_RECT.bottom - 4 - (a / max_f) * (CFG.GRAPH_RECT.h - 8)
                pts_b.append((px, py_b)); pts_a.append((px, py_a))
            pygame.draw.lines(self.screen, HEALTH_GREEN, False, pts_b, 2)
            pygame.draw.lines(self.screen, (140, 180, 220), False, pts_a, 1)
        self.screen.blit(self.font_ui.render("📈 Fitness over generations — 🟢 best, 🔵 avg", True, DIM_TEXT), (CFG.GRAPH_RECT.left + 8, CFG.GRAPH_RECT.top - 18))

    def draw_panels(self, evo: Evolution, env: Optional[Environment]):
        self.ui_timer += 1
        update_ui = (self.ui_timer % 5 == 0)
        
        if update_ui:
            self.ui_panel_surf.fill((0, 0, 0, 0))
            self._draw_panels_to_surface(evo, env)
            
        self.screen.blit(self.ui_panel_surf, (0, 0))

    def _draw_panels_to_surface(self, evo: Evolution, env: Optional[Environment]):
        surf = self.ui_panel_surf
        
        pygame.draw.rect(surf, PANEL_BG, CFG.LEADERBOARD_RECT)
        pygame.draw.rect(surf, (60, 70, 90), CFG.LEADERBOARD_RECT, 1)
        surf.blit(self.font_title.render("🏆  LEADERBOARD 🏆", True, ACCENT), (CFG.LEADERBOARD_RECT.left + 12, CFG.LEADERBOARD_RECT.top + 8))
        sorted_pop = sorted(evo.population, key=lambda b: b.elo, reverse=True)
        y = CFG.LEADERBOARD_RECT.top + 38
        for i, b in enumerate(sorted_pop[:5]):
            medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
            surf.blit(self.font_ui.render(f"{medal}  Elo: {b.elo:.0f}", True, ACCENT if i < 3 else TEXT_COLOR), (CFG.LEADERBOARD_RECT.left + 12, y))
            y += 20
            surf.blit(self.font_ui.render(f"     ⚔️ W/L/D = {b.wins}/{b.losses}/{b.draws}", True, DIM_TEXT), (CFG.LEADERBOARD_RECT.left + 12, y))
            y += 18
            surf.blit(self.font_ui.render(f"     💥{b.damage_dealt:.0f} 🩸{b.damage_taken:.0f} 🎯V:{b.value_acc*100:.0f}%", True, DIM_TEXT), (CFG.LEADERBOARD_RECT.left + 12, y))
            y += 22

        pygame.draw.rect(surf, PANEL_BG, CFG.COMBAT_LOG_RECT)
        pygame.draw.rect(surf, (60, 70, 90), CFG.COMBAT_LOG_RECT, 1)
        surf.blit(self.font_title.render("📜 COMBAT LOG", True, ACCENT), (CFG.COMBAT_LOG_RECT.left + 12, CFG.COMBAT_LOG_RECT.top + 8))
        y = CFG.COMBAT_LOG_RECT.top + 38
        if env:
            for msg in env.combat_log:
                surf.blit(self.font_ui.render(msg, True, TEXT_COLOR), (CFG.COMBAT_LOG_RECT.left + 12, y))
                y += 22

        pygame.draw.rect(surf, PANEL_BG, CFG.PIE_CHART_RECT)
        pygame.draw.rect(surf, (60, 70, 90), CFG.PIE_CHART_RECT, 1)
        surf.blit(self.font_title.render("⚔️ ACTIONS", True, ACCENT), (CFG.PIE_CHART_RECT.left + 8, CFG.PIE_CHART_RECT.top + 4))
        brain = env.w1.brain if env else evo.champion
        if brain and brain.action_history.sum() > 0:
            total = brain.action_history.sum()
            center = (CFG.PIE_CHART_RECT.centerx, CFG.PIE_CHART_RECT.centery + 10)
            radius = 50
            start_angle = math.pi / 2
            colors = [(140, 180, 220), (140, 180, 220), (140, 180, 220), (140, 180, 220), (220, 80, 80), (80, 180, 255), (255, 200, 90), (220, 140, 220), (100, 220, 180), (255, 100, 100)]
            for i in range(CFG.ACTION_SIZE):
                val = brain.action_history[i]
                if val == 0: continue
                angle = (val / total) * 2 * math.pi
                pygame.draw.arc(surf, colors[i], (center[0]-radius, center[1]-radius, radius*2, radius*2), start_angle - angle, start_angle, radius*2)
                start_angle -= angle
            y = CFG.PIE_CHART_RECT.top + 30
            for i in range(CFG.ACTION_SIZE):
                surf.blit(self.font_tiny.render(f"{ACTION_EMOJIS[i]} {(brain.action_history[i]/total)*100:.0f}%", True, TEXT_COLOR), (CFG.PIE_CHART_RECT.left + 8, y))
                y += 20

        pygame.draw.rect(surf, PANEL_BG, CFG.HEATMAP_RECT)
        pygame.draw.rect(surf, (60, 70, 90), CFG.HEATMAP_RECT, 1)
        surf.blit(self.font_title.render("🗺️ HEATMAP", True, ACCENT), (CFG.HEATMAP_RECT.left + 8, CFG.HEATMAP_RECT.top + 4))
        if brain and brain.heatmap.max() > 0:
            max_val = brain.heatmap.max()
            grid_w = CFG.HEATMAP_RECT.w - 20; grid_h = CFG.HEATMAP_RECT.h - 30
            cell_w = grid_w / 8; cell_h = grid_h / 8
            for r in range(8):
                for c in range(8):
                    val = brain.heatmap[r, c] / max_val
                    if val > 0:
                        cell_surf = pygame.Surface((int(cell_w), int(cell_h)))
                        cell_surf.set_alpha(int(val * 255))
                        cell_surf.fill((255, 100, 50))
                        surf.blit(cell_surf, (CFG.HEATMAP_RECT.left + 10 + c * cell_w, CFG.HEATMAP_RECT.top + 25 + r * cell_h))

        pygame.draw.rect(surf, PANEL_BG, CFG.NN_VIZ_RECT)
        pygame.draw.rect(surf, (60, 70, 90), CFG.NN_VIZ_RECT, 1)
        surf.blit(self.font_title.render("🧠 CHAMPION NN & DNA", True, ACCENT), (CFG.NN_VIZ_RECT.left + 8, CFG.NN_VIZ_RECT.top + 4))
        
        if brain and env:
            state = get_state_vector(env, 1)
            _, _, h_activations = brain.forward(state)
            n_in = CFG.STATE_SIZE; n_hid = CFG.HIDDEN_SIZE; n_out = CFG.ACTION_SIZE + 1
            in_x = CFG.NN_VIZ_RECT.left + 20; hid_x = CFG.NN_VIZ_RECT.centerx - 10; out_x = CFG.NN_VIZ_RECT.right - 30
            in_y_start = CFG.NN_VIZ_RECT.top + 30; in_y_end = CFG.NN_VIZ_RECT.bottom - 40
            hid_y_start = CFG.NN_VIZ_RECT.top + 20; hid_y_end = CFG.NN_VIZ_RECT.bottom - 40
            out_y_start = CFG.NN_VIZ_RECT.top + 40; out_y_end = CFG.NN_VIZ_RECT.bottom - 40

            def get_y(start, end, n, i):
                return (start + end) / 2 if n == 1 else start + (end - start) * (i / (n - 1))

            if self.nn_cache_gen != id(brain.W1):
                self.nn_cache_surf = pygame.Surface((CFG.SCREEN_W, CFG.SCREEN_H), pygame.SRCALPHA)
                for i in range(n_in):
                    for j in range(n_hid):
                        w = brain.W1[i, j]
                        if abs(w) > 0.6:
                            color = (90, 220, 110) if w > 0 else (220, 80, 80)
                            pygame.draw.line(self.nn_cache_surf, color, (in_x, get_y(in_y_start, in_y_end, n_in, i)), (hid_x, get_y(hid_y_start, hid_y_end, n_hid, j)), 1)
                self.nn_cache_gen = id(brain.W1)
                
            surf.blit(self.nn_cache_surf, (0, 0))

            for i in range(n_in):
                y = get_y(in_y_start, in_y_end, n_in, i)
                pygame.draw.circle(surf, (255, 255, 255) if state[i] > 0 else (80, 80, 80), (int(in_x), int(y)), 3)
                
            for j in range(n_hid):
                y = get_y(hid_y_start, hid_y_end, n_hid, j)
                act = h_activations[j]
                col = (int(255 * max(0, act)), int(180 * max(0, act)), int(50 * max(0, act))) if act > 0 else (50, 50, 150)
                pygame.draw.circle(surf, col, (int(hid_x), int(y)), 4)

            p, v, _ = brain.forward(state)
            p_softmax = softmax(p)
            for k in range(CFG.ACTION_SIZE):
                y = get_y(out_y_start, out_y_end, n_out, k)
                act = p_softmax[k]
                pygame.draw.circle(surf, (int(255 * act), int(200 * act), int(90 * act)), (int(out_x), int(y)), 5)
            y_val = get_y(out_y_start, out_y_end, n_out, CFG.ACTION_SIZE)
            pygame.draw.circle(surf, (90, 220, 110) if v > 0 else (220, 80, 80), (int(out_x), int(y_val)), 5)
            
            dna_y = CFG.NN_VIZ_RECT.bottom - 20
            dna_x = CFG.NN_VIZ_RECT.left + 10
            dna_w = CFG.NN_VIZ_RECT.w - 20
            pygame.draw.rect(surf, (40, 40, 50), (dna_x, dna_y, dna_w, 10))
            cx = dna_x
            for i, weight in enumerate(brain.class_weights):
                w_w = weight * dna_w
                pygame.draw.rect(surf, CLASS_COLORS[i], (cx, dna_y, w_w, 10))
                cx += w_w


# ==============================================================================
# 12. MAIN APP (CONTROLLER)
# ==============================================================================
class GameApp:
    def __init__(self, args):
        pygame.mixer.pre_init(44100, -16, 1, 512)
        pygame.init()
        self.screen = pygame.display.set_mode((CFG.SCREEN_W, CFG.SCREEN_H))
        pygame.display.set_caption("🥷 Emoji Fight Arena 17.0 — Numba JIT Acceleration 🚀")
        self.clock = pygame.time.Clock()
        
        self.evo = Evolution(pop_size=args.pop, seed=args.seed)
        self.renderer = Renderer(self.screen)
        self.sound = SoundManager()
        
        self.mode = "training"
        self.env: Optional[Environment] = None
        self.visual_msg = ""
        self.paused = False
        self.train_speed = 1
        self.fight_end_timer = 0
        self.use_mcts_flag = False
        self.running = True

    def run(self):
        while self.running:
            self._handle_events()
            if self.paused:
                self.clock.tick(CFG.FPS)
                continue
                
            self.screen.fill(BG_COLOR)
            time_of_day = (self.evo.generation * 0.1) % 1.0

            if self.mode == "training":
                self._update_training()
                self.renderer.draw_hud(self.evo, f"⚙️ Training (⬅️➡️: {self.train_speed}x)  [V] Champ  [M] MCTS: {'ON' if self.use_mcts_flag else 'OFF'}  [N] Sound  [SPACE] Pause", time_of_day, self.sound.enabled)
                
                temp_env = Environment(Warrior(0,0,Brain()), Warrior(0,0,Brain()), self.evo.gmap, fast_mode=True)
                self.renderer.draw_env(temp_env, time_of_day)
                msg = self.renderer.font_ui_big.render(f"⚙️  Evolving & Backpropagating Gen {self.evo.generation}... 🧬", True, DIM_TEXT)
                self.screen.blit(msg, msg.get_rect(center=(CFG.ARENA.centerx, CFG.ARENA.centery)))
                self.renderer.draw_panels(self.evo, None)

            elif self.mode in ("view_fight", "champion_loop"):
                self._update_fight()
                self.renderer.draw_hud(self.evo, self.visual_msg, time_of_day, self.sound.enabled)
                if self.env:
                    self.renderer.draw_env(self.env, time_of_day)
                    self.renderer.draw_panels(self.evo, self.env)

            pygame.display.flip()
            self.clock.tick(CFG.FPS)
        pygame.quit()
        sys.exit(0)

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: self.running = False
                elif event.key == pygame.K_SPACE: self.paused = not self.paused
                elif event.key == pygame.K_m: self.use_mcts_flag = not self.use_mcts_flag
                elif event.key == pygame.K_n: self.sound.toggle_mute()
                elif event.key == pygame.K_v: self._start_fight("champion_loop")
                elif event.key == pygame.K_s:
                    if self.evo.champion: self.evo.champion.save(SAVE_FILE)
                elif event.key == pygame.K_l:
                    if os.path.exists(SAVE_FILE): self.evo.champion = Brain.load(SAVE_FILE)
                elif event.key == pygame.K_RIGHT: self.train_speed = min(10, self.train_speed + 1)
                elif event.key == pygame.K_LEFT: self.train_speed = max(1, self.train_speed - 1)

    def _update_training(self):
        for _ in range(self.train_speed):
            self.evo.evaluate()
            self.evo.train_champion_sgd()
            gen_done = self.evo.generation
            if gen_done % 3 == 0:
                sorted_pop = sorted(self.evo.population, key=lambda b: b.fitness, reverse=True)
                if len(sorted_pop) >= 2:
                    b1 = sorted_pop[0].copy(); b2 = sorted_pop[1].copy()
                    w1 = Warrior(0, 0, b1, emoji="🥇", label="🥇 TOP 1", use_mcts=self.use_mcts_flag)
                    w2 = Warrior(0, 0, b2, emoji="🥈", label="🥈 TOP 2")
                    self.env = Environment(w1, w2, self.evo.gmap, headless=False)
                    self.visual_msg = f"🧬 Gen {gen_done} — Top 2 Fight"
                    self.mode = "view_fight"; self.fight_end_timer = 0
                self.evo.evolve()
                break
            else:
                self.evo.evolve()

    def _start_fight(self, mode: str):
        if self.evo.champion:
            b1 = self.evo.champion.copy(); b2 = random.choice(self.evo.population).copy()
            w1 = Warrior(0, 0, b1, emoji="🥷", label="👑 CHAMPION", use_mcts=self.use_mcts_flag)
            w2 = Warrior(0, 0, b2, emoji=random.choice(WARRIOR_EMOJIS), label="🥷 CHALLENGER")
            self.env = Environment(w1, w2, self.evo.gmap, headless=False)
            self.visual_msg = "👑 Champion vs 🥷 Challenger"
            self.mode = mode; self.fight_end_timer = 0

    def _update_fight(self):
        if self.mode == "champion_loop" and (self.env is None or (self.env.done and self.fight_end_timer > 130)):
            self._start_fight("champion_loop")

        if self.env is not None:
            if not self.env.done:
                self.env.step()
                
                for s in self.env.sound_queue:
                    self.sound.play(s)
                self.env.sound_queue.clear()
            else:
                self.fight_end_timer += 1

            if self.env.agent1 and not self.env.done:
                state = get_state_vector(self.env, 1).copy()
                mcts_policy = np.zeros(CFG.ACTION_SIZE, dtype=np.float32)
                total_visits = sum(v[0] for v in self.env.agent1.last_action_stats.values())
                for act, (visits, q) in self.env.agent1.last_action_stats.items():
                    mcts_policy[act] = visits / total_visits if total_visits > 0 else 0.0
                self.evo.replay_buffer.append((state, mcts_policy, 0.0))
            
            if self.env.done:
                actual_v = 1.0 if self.env.winner == 1 else (-1.0 if self.env.winner == 2 else 0.0)
                if self.evo.replay_buffer:
                    s, p, _ = self.evo.replay_buffer[-1]
                    self.evo.replay_buffer[-1] = (s, p, actual_v)
                    
                if self.mode == "view_fight" and self.fight_end_timer > 100:
                    self.mode = "training"


# ==============================================================================
# 13. ENTRY POINT
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="🥷 Emoji Fight Arena 17.0 — Numba JIT Acceleration")
    parser.add_argument("--pop", type=int, default=CFG.POPULATION_SIZE)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    
    app = GameApp(args)
    app.run()

if __name__ == "__main__":
    main()