#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
明日方舟：终末地（Arknights: Endfield）外部自动化配置脚本：在游戏外直接修改
终末地的画面、分辨率、音量、语言等设置。编辑配置文件 → 运行脚本 → 自动写入，
无需进游戏手动调。不含解帧功能。
"""

import sys
import json
import time
import base64
import argparse
import subprocess
import traceback
import winreg
from pathlib import Path

# Windows 控制台默认 GBK，强制 UTF-8 避免中文乱码
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ---------- 常量 ----------
# 注册表路径：Unity PlayerPrefs 存储于 HKCU\SOFTWARE\Hypergryph\Endfield
REG_PATH = r"SOFTWARE\Hypergryph\Endfield"

# ---------- 配置键（对应 config.json 字段，顺序 = 游戏内官方面板顺序） ----------
# 注：阴影质量/体积雾/体积云/环境光遮蔽/场景细节/环境细节/植被密度/屏幕空间反射/
#     全局特效质量/队友技能特效质量 等单项注册表无对应键，暂不在配置中暴露。
CONFIG_KEYS = [
    "video_quality_main",               # 画面质量
    "fullscreen",                       # 显示模式（特殊键：双注册表键）
    "resolution",                       # 分辨率（特殊键：四注册表键）
    "video_frame_rate_8",               # 帧率
    "teammate_skill_effect_opacity",    # 队友技能特效不透明度
    "video_quality_vsync_v2_2",         # 垂直同步
    "video_texture_quality_1",          # 纹理质量
    "video_quality_anisoLevel_1",       # 各向异性采样
    "video_quality_chromatic_aberration_1",  # 色差
    "video_quality_upscaler_2",         # 画质提升
    "video_quality_dlss_mode_1",        # DLSS超分辨模式
    "video_quality_sharpness_1",        # 锐化程度
    "video_quality_framegen_1",         # 帧生成
    "video_quality_dlssg_mode_1",       # DLSS帧生成模式
    "video_quality_reflex_1",           # NVIDIA Reflex
    "video_quality_contactshadow_1",    # 接触阴影
    "audio_global",                     # 总音量
    "audio_voice",                      # 语音音量
    "audio_music",                      # 音乐音量
    "audio_sfx",                        # 音效音量
    "audio_suite_mode",                 # 输出模式
    "audio_suspend_unfocused",          # 非当前窗口时静音
    "audio_controller",                 # 控制器喇叭
    "audio_spatial",                    # 空间音频渲染
    "language_text_change",             # 游戏语言
    "language_audio",                   # 游戏语音
    "controller_keyboard_type",         # 键盘布局
]

# 注册表键名 → 中文名（config.json 里用中文键，脚本内部用注册表键名）
KEY_CN = {
    "video_quality_main": "画面质量",
    "fullscreen": "显示模式",
    "resolution": "分辨率",
    "video_frame_rate_8": "帧率",
    "teammate_skill_effect_opacity": "队友技能特效不透明度",
    "video_quality_vsync_v2_2": "垂直同步",
    "video_texture_quality_1": "纹理质量",
    "video_quality_anisoLevel_1": "各向异性采样",
    "video_quality_chromatic_aberration_1": "色差",
    "video_quality_upscaler_2": "画质提升",
    "video_quality_dlss_mode_1": "DLSS超分辨模式",
    "video_quality_sharpness_1": "锐化程度",
    "video_quality_framegen_1": "帧生成",
    "video_quality_dlssg_mode_1": "DLSS帧生成模式",
    "video_quality_reflex_1": "NVIDIA Reflex",
    "video_quality_contactshadow_1": "接触阴影",
    "audio_global": "总音量",
    "audio_voice": "语音音量",
    "audio_music": "音乐音量",
    "audio_sfx": "音效音量",
    "audio_suite_mode": "输出模式",
    "audio_suspend_unfocused": "非当前窗口时静音",
    "audio_controller": "控制器喇叭",
    "audio_spatial": "空间音频渲染",
    "language_text_change": "游戏语言",
    "language_audio": "游戏语音",
    "controller_keyboard_type": "键盘布局",
}
CN_TO_KEY = {cn: k for k, cn in KEY_CN.items()}   # 中文键 → 内部键
KNOWN_NAMES = set(CONFIG_KEYS)                    # 配置文件中允许的内部键名
KNOWN_CN = set(KEY_CN.values())                   # 允许的中文键名

# ---------- 设置映射表（核心） ----------
# 每项：
#   cn      中文名
#   kind    enum（档位映射）/ switch（开/关）/ scale（小数×factor）/ reverse（反向）
#   conf    anchored（已标定）/ infer（推断，待验证）/ todo（待标定）
#   allowed 档位 → 注册表原始值（None = 尚未标定，选中即报错）
#   factor  scale 用的放大倍数；min/max scale 与 reverse 用的范围
# 未标定档位的逃生通道：配置里直接填整数 = 原始值透传（原样写注册表）。
SETTINGS_TABLE = {
    "video_quality_main": {
        "cn": "画面质量", "kind": "enum", "conf": "anchored",
        "allowed": {"自定义": None, "极低": None, "低": None, "中": None, "高": 2, "极高": None},
    },
    "video_frame_rate_8": {
        "cn": "帧率", "kind": "enum", "conf": "anchored",
        "allowed": {"30": 1000, "60": 2000, "120": 3000},
    },
    "teammate_skill_effect_opacity": {
        "cn": "队友技能特效不透明度", "kind": "scale", "conf": "infer",
        "factor": 1000, "min": 0.1, "max": 1.0,
    },
    "video_quality_vsync_v2_2": {
        "cn": "垂直同步", "kind": "switch", "conf": "todo",
        "allowed": {"开": None, "关": None},
    },
    "video_texture_quality_1": {
        "cn": "纹理质量", "kind": "enum", "conf": "anchored",
        "allowed": {"低": None, "中": None, "高": 1000},
    },
    "video_quality_anisoLevel_1": {
        "cn": "各向异性采样", "kind": "enum", "conf": "anchored",
        "allowed": {"x1": 1000, "x2": 2000, "x4": 4000, "x8": 8000},
    },
    "video_quality_chromatic_aberration_1": {
        "cn": "色差", "kind": "switch", "conf": "todo",
        "allowed": {"开": None, "关": None},
    },
    "video_quality_upscaler_2": {
        "cn": "画质提升", "kind": "enum", "conf": "anchored",
        "allowed": {"NVIDIA DLSS": 1000, "TAAU": 2000, "AMD FSR3": 3000},
    },
    "video_quality_dlss_mode_1": {
        "cn": "DLSS超分辨模式", "kind": "enum", "conf": "todo",
        "allowed": {"DLAA": None, "质量": None, "平衡": None, "性能": None, "超级性能": None},
    },
    "video_quality_sharpness_1": {
        "cn": "锐化程度", "kind": "scale", "conf": "anchored",
        "factor": 1000, "min": 0.0, "max": 1.0,
    },
    "video_quality_framegen_1": {
        "cn": "帧生成", "kind": "enum", "conf": "todo",
        "allowed": {"FSR3 Frame Generation": None, "DLSS Frame Generation": None, "关闭": None},
    },
    "video_quality_dlssg_mode_1": {
        "cn": "DLSS帧生成模式", "kind": "enum", "conf": "todo",
        "allowed": {"自动": None, "2x": None, "3x": None, "4x": None},
    },
    "video_quality_reflex_1": {
        "cn": "NVIDIA Reflex", "kind": "enum", "conf": "todo",
        "allowed": {"开启+增强": None, "开启": None, "关闭": None},
    },
    "video_quality_contactshadow_1": {
        "cn": "接触阴影", "kind": "switch", "conf": "todo",
        "allowed": {"开": None, "关": None},
    },
    "audio_global": {"cn": "总音量", "kind": "reverse", "conf": "anchored", "min": 0, "max": 10},
    "audio_voice": {"cn": "语音音量", "kind": "reverse", "conf": "anchored", "min": 0, "max": 10},
    "audio_music": {"cn": "音乐音量", "kind": "reverse", "conf": "anchored", "min": 0, "max": 10},
    "audio_sfx": {"cn": "音效音量", "kind": "reverse", "conf": "anchored", "min": 0, "max": 10},
    "audio_suite_mode": {
        "cn": "输出模式", "kind": "enum", "conf": "anchored",
        "allowed": {"桌面音箱": None, "家庭影院": None, "电视": None, "耳机": 1},
    },
    "audio_suspend_unfocused": {
        "cn": "非当前窗口时静音", "kind": "switch", "conf": "todo",
        "allowed": {"开": None, "关": None},
    },
    "audio_controller": {
        "cn": "控制器喇叭", "kind": "switch", "conf": "todo",
        "allowed": {"开": None, "关": None},
    },
    "audio_spatial": {
        "cn": "空间音频渲染", "kind": "switch", "conf": "todo",
        "allowed": {"开": None, "关": None},
    },
    "language_text_change": {
        "cn": "游戏语言", "kind": "enum", "conf": "todo",
        "allowed": {},  # 选项未提供，README 标注待确认；可填整数原始值透传
    },
    "language_audio": {
        "cn": "游戏语音", "kind": "enum", "conf": "anchored",
        "allowed": {"中文": 1, "英语": None, "日语": None, "韩语": None},
    },
    "controller_keyboard_type": {
        "cn": "键盘布局", "kind": "enum", "conf": "todo",
        "allowed": {"默认": None, "德语": None, "法语": None},
    },
}

# 分辨率：写四键同步（Screenmanager 系 + video 系）
RES_SYNC_KEYS = {
    "width":  ("Screenmanager Resolution Width", "video_resolution_width"),
    "height": ("Screenmanager Resolution Height", "video_resolution_height"),
}
# 显示模式：video_full_screen(0=窗口已标定, 1=全屏推断) + Screenmanager Fullscreen mode(3=窗口已标定, 全屏待标定)
FULLSCREEN_KEYS = [
    ("video_full_screen", 0, 1),
    ("Screenmanager Fullscreen mode", 3, None),
]
BACKUP_DIR = Path(__file__).resolve().parent / "backups"
DEFAULT_CONFIG = Path(__file__).resolve().parent / "config.json"  # 根目录参考模板
CONFIG_DIR = Path(__file__).resolve().parent / "config"           # 自定义配置目录
# --config 不带扩展名时自动尝试的后缀：宽松格式建议用 .conf（编辑器不会按 JSON 校验）
CONFIG_SUFFIXES = (".json", ".conf", ".txt", ".cfg")

GAME_EXES = ("Endfield.exe",)


# ---------- 异常与输出 ----------
class UserError(Exception):
    """输入 / 校验错误 → 退出码 1。"""

class ConfigError(Exception):
    """注册表 / 解析错误 → 退出码 2。"""

def warn(msg):
    print(f"[警告] {msg}", file=sys.stderr)

def info(msg):
    print(msg)


# ---------- ① 注册表读写（Unity PlayerPrefs） ----------
def unity_hash(name):
    """Unity 的 djb2-xor 哈希（已验证与游戏写入的值名后缀一致）。"""
    h = 5381
    for c in name:
        h = ((h * 33) ^ ord(c)) & 0xFFFFFFFF
    return h

def value_name(name):
    """注册表值名 = 键名_h<哈希>。"""
    return f"{name}_h{unity_hash(name)}"

# 脚本可能写入的全部值名（恢复时删除脚本新建、备份中不存在的键）
KNOWN_VALUE_NAMES = {value_name(k) for k in SETTINGS_TABLE} | {
    value_name(k) for pair in RES_SYNC_KEYS.values() for k in pair
} | {value_name(k[0]) for k in FULLSCREEN_KEYS}

def open_key():
    """打开 HKCU\\SOFTWARE\\Hypergryph\\Endfield（读写）。"""
    try:
        return winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0,
                              winreg.KEY_READ | winreg.KEY_WRITE)
    except OSError as e:
        raise ConfigError(f"无法打开注册表键 {REG_PATH}：{e}\n"
                          f"请先启动一次游戏，让游戏生成注册表配置后再运行本脚本。")

def snapshot_all(key):
    """枚举该键下全部值 → {键名(去 _h 后缀): (值名, 原始值, 类型码)}。"""
    snap = {}
    n = winreg.QueryInfoKey(key)[1]
    for i in range(n):
        name, val, typ = winreg.EnumValue(key, i)
        base = name.rsplit("_h", 1)[0] if "_h" in name else name
        snap[base] = (name, val, typ)
    return snap

def read_dword(snap, key_name):
    """按键名读 REG_DWORD。不存在 → None；类型不符 → 警告 + None。"""
    item = snap.get(key_name)
    if item is None:
        return None
    _, val, typ = item
    if typ != winreg.REG_DWORD:
        warn(f"键 '{key_name}' 类型不是 REG_DWORD（类型 {typ}），跳过。")
        return None
    return int(val)

def write_dword(key, key_name, value, snap=None):
    """写 REG_DWORD。snap 提供时先做安全校验：同名键已存在但哈希值名对不上
    → 键名推断有误，拒绝写入以防写坏设置。"""
    vn = value_name(key_name)
    if snap is not None:
        exist = snap.get(key_name)
        if exist is not None and exist[0] != vn:
            raise ConfigError(
                f"键 '{key_name}' 在注册表中的值名是 '{exist[0]}'，"
                f"与脚本计算的 '{vn}' 不一致。哈希算法或键名可能有误，已中止写入。")
    winreg.SetValueEx(key, vn, 0, winreg.REG_DWORD, int(value))


# ---------- ② 数值换算 ----------
def _is_bool(v):
    return isinstance(v, bool)

def resolve_open_close(name, val):
    """开/关 类开关：接受 true/false、0/1、开/关。"""
    if isinstance(val, bool):
        return val
    if isinstance(val, int) and val in (0, 1):
        return bool(val)
    if isinstance(val, str):
        s = val.strip().lower()
        if s in ("1", "true", "开", "打开", "on"):
            return True
        if s in ("0", "false", "关", "关闭", "off"):
            return False
    raise UserError(f"'{KEY_CN.get(name, name)}' 取值 '{val}' 非法。合法：开/关 或 true/false 或 0/1。")

def resolve_fullscreen(val):
    """显示模式：接受 窗口/全屏、0/1、true/false。"""
    if isinstance(val, bool):
        return int(val)
    if isinstance(val, int) and val in (0, 1):
        return int(val)
    if isinstance(val, str):
        s = val.strip().lower()
        if s in ("全屏", "fullscreen", "true", "1", "开", "打开", "on"):
            return 1
        if s in ("窗口", "window", "false", "0", "关", "关闭", "off"):
            return 0
    raise UserError(f"「显示模式」取值 '{val}' 非法。合法：窗口 / 全屏。")

def resolve_resolution(val):
    """解析 "宽*高" 形式的分辨率（支持 * 与 × 两种分隔符）。"""
    if not isinstance(val, str):
        raise UserError(f"「分辨率」须为 '宽*高' 字符串（如 '1920*1080'），当前为 '{val}'。")
    parts = [p.strip() for p in val.replace("×", "*").split("*")]
    if len(parts) != 2:
        raise UserError(f"「分辨率」须为 '宽*高'（如 '1920*1080'），当前为 '{val}'。")
    try:
        w, h = int(parts[0]), int(parts[1])
    except ValueError:
        raise UserError(f"「分辨率」的宽和高须为整数，当前为 '{val}'。")
    if w < 640 or h < 640:
        raise UserError(f"分辨率宽高须 ≥640，当前为 '{val}'。")
    return w, h

def to_raw(name, val):
    """把用户配置值换算为注册表原始整数。整数透传是未标定档位的逃生通道。"""
    spec = SETTINGS_TABLE[name]
    kind = spec["kind"]
    cn = spec["cn"]

    if kind == "reverse":
        # 音量反向：游戏内滑块 0~10 → 存储 10-滑块值（真机校准，存储 0 = 滑块 10）
        if _is_bool(val):
            raise UserError(f"「{cn}」须为 {spec['min']}~{spec['max']} 的整数。")
        try:
            iv = int(val)
        except (TypeError, ValueError):
            raise UserError(f"「{cn}」须为 {spec['min']}~{spec['max']} 的整数，当前为 '{val}'。")
        if not (spec["min"] <= iv <= spec["max"]):
            raise UserError(f"「{cn}」应在 {spec['min']}~{spec['max']} 之间，当前为 '{iv}'。")
        return spec["max"] - iv

    if kind == "scale":
        # 整数直接透传（逃生通道）；小数按 factor 放大
        if not _is_bool(val) and isinstance(val, int):
            return val
        if _is_bool(val):
            raise UserError(f"「{cn}」须为 {spec['min']}~{spec['max']} 的数值。")
        try:
            f = float(val)
        except (TypeError, ValueError):
            raise UserError(f"「{cn}」须为 {spec['min']}~{spec['max']} 的数值，当前为 '{val}'。")
        if not (spec["min"] <= f <= spec["max"]):
            raise UserError(f"「{cn}」应在 {spec['min']}~{spec['max']} 之间，当前为 '{f}'。")
        return int(round(f * spec["factor"]))

    if kind == "switch":
        # 整数直接透传（逃生通道）；字符串/布尔走开/关映射
        if not _is_bool(val) and isinstance(val, int):
            return val
        b = resolve_open_close(name, val)
        raw = spec["allowed"]["开" if b else "关"]
        if raw is None:
            raise UserError(f"「{cn}」的「{'开' if b else '关'}」档位尚未标定，无法写入。"
                            f"可用 --read 查看该档位实际原始值，或直接在配置里填整数原始值（透传）。")
        return raw

    # kind == "enum"
    allowed = spec["allowed"]
    if isinstance(val, str):
        if val in allowed:
            raw = allowed[val]
            if raw is None:
                raise UserError(f"「{cn}」档位「{val}」尚未标定，无法写入。"
                                f"可用 --read 查看该档位实际原始值，或直接在配置里填整数原始值（透传）。")
            return raw
        if not allowed:
            raise UserError(f"「{cn}」尚未提供档位信息，无法写入。"
                            f"可用 --read 查看原始值，或直接在配置里填整数原始值（透传）。")
        raise UserError(f"「{cn}」取值 '{val}' 非法。合法取值：{'/'.join(allowed)}")
    if not _is_bool(val) and isinstance(val, (int, float)):
        if str(val) in allowed:
            return allowed[str(val)]  # 数字"显示值"（如帧率填 60 → 原始 2000）
        if isinstance(val, int) and val in allowed.values():
            return val  # 内部枚举值
        if isinstance(val, int):
            return val  # 原始值透传（逃生通道）
        raise UserError(f"「{cn}」须填整数原始值，当前为 '{val}'。")
    raise UserError(f"「{cn}」取值 '{val}' 非法。合法取值：{'/'.join(allowed) or '（待提供）'}")

def from_raw(name, raw):
    """把注册表原始整数换算为可读的中文档位/数值（未标定档位原样显示）。"""
    if raw is None:
        return "（无键/未生成）"
    spec = SETTINGS_TABLE[name]
    kind = spec["kind"]
    if kind in ("enum", "switch"):
        for cn, r in spec["allowed"].items():
            if r == raw:
                return cn
        return f"{raw}（未标定档位）"
    if kind == "reverse":
        return str(spec["max"] - raw)
    if kind == "scale":
        return str(raw / spec["factor"])
    return str(raw)


# ---------- ③ 校验 ----------
def validate_changes(changes):
    """把 {配置名: 用户值} 标准化为可直接写入的原始整数分组。"""
    validated = {
        "values": {},      # {注册表键名: 原始整数}
        "resolution": {},  # {width/height/fullscreen: int}
    }
    for name, val in changes.items():
        if name == "resolution":
            w, h = resolve_resolution(val)
            validated["resolution"]["width"] = w
            validated["resolution"]["height"] = h
        elif name == "fullscreen":
            validated["resolution"]["fullscreen"] = resolve_fullscreen(val)
        elif name in SETTINGS_TABLE:
            validated["values"][name] = to_raw(name, val)
        else:
            raise UserError(f"未知设置名 '{name}'。")
    return validated


# ---------- ④ 加载与应用 ----------
def load_all():
    """读取注册表全部设置 → state dict。"""
    key = open_key()
    try:
        snap = snapshot_all(key)
    finally:
        key.Close()
    state = {
        "snapshot": snap,                       # {键名(去 _h): (值名, 值, 类型码)}
        "settings": {},                         # {注册表键名: 原始值}
        "resolution": {},                       # {width/height/fullscreen: int}
    }
    for k in SETTINGS_TABLE:
        state["settings"][k] = read_dword(snap, k)
    state["resolution"]["width"] = read_dword(snap, "video_resolution_width")
    state["resolution"]["height"] = read_dword(snap, "video_resolution_height")
    state["resolution"]["fullscreen"] = read_dword(snap, "video_full_screen")
    return state

def apply_all(validated):
    """把校验后的设置写入注册表。"""
    key = open_key()
    try:
        snap = snapshot_all(key)
        for name, raw in validated["values"].items():
            write_dword(key, name, raw, snap)
        res = validated["resolution"]
        if "width" in res:
            for k in RES_SYNC_KEYS["width"]:
                write_dword(key, k, res["width"], snap)
        if "height" in res:
            for k in RES_SYNC_KEYS["height"]:
                write_dword(key, k, res["height"], snap)
        if "fullscreen" in res:
            fs = res["fullscreen"]
            for k, win_val, full_val in FULLSCREEN_KEYS:
                if fs == 0:
                    write_dword(key, k, win_val, snap)
                elif full_val is not None:
                    write_dword(key, k, full_val, snap)
                else:
                    warn(f"显示模式「全屏」下注册表键 '{k}' 的全屏原始值尚未标定，已跳过该键。")
    finally:
        key.Close()


# ---------- ⑤ 展示与摘要 ----------
def display_current(state):
    """--read：中文友好展示当前全部设置。"""
    print("=" * 52)
    print("终末地当前设置（来源：注册表 Hypergryph\\Endfield）")
    print("=" * 52)

    res = state["resolution"]
    w, h, fs = res.get("width"), res.get("height"), res.get("fullscreen")
    fs_name = "窗口" if fs == 0 else ("全屏" if fs == 1 else f"值 {fs}")
    print(f"[显示] 分辨率 = {w}*{h}   显示模式 = {fs_name}（原始 {fs}）")

    order = {k: i for i, k in enumerate(CONFIG_KEYS)}
    for name in sorted(SETTINGS_TABLE, key=lambda k: order.get(k, 999)):
        spec = SETTINGS_TABLE[name]
        raw = state["settings"].get(name)
        print(f"[{spec['cn']}] {from_raw(name, raw)}（原始 {raw}）")

def print_summary(validated, backup_path):
    """应用成功后打印变更摘要。"""
    print("\n已写入以下设置：")
    res = validated["resolution"]
    if res:
        if "width" in res and "height" in res:
            print(f"  · 分辨率 → {res['width']}*{res['height']}")
        if "fullscreen" in res:
            print(f"  · 显示模式 → {'全屏' if res['fullscreen'] else '窗口'}")
    order = {k: i for i, k in enumerate(CONFIG_KEYS)}
    for name in sorted(validated["values"], key=lambda k: order.get(k, 999)):
        spec = SETTINGS_TABLE[name]
        raw = validated["values"][name]
        print(f"  · {spec['cn']} → {from_raw(name, raw)}（原始值 {raw}）")
    if backup_path:
        print(f"\n原配置已备份到：{backup_path}")


# ---------- ⑥ 备份与恢复 ----------
def snapshot_to_config(state):
    """把注册表快照转成与 config 同形式的中文键可读清单，便于阅读备份。"""
    cfg = {}
    res = state["resolution"]
    if res.get("width") is not None and res.get("height") is not None:
        cfg["分辨率"] = f"{res['width']}*{res['height']}"
    if res.get("fullscreen") is not None:
        cfg["显示模式"] = "全屏" if res["fullscreen"] else "窗口"
    order = {k: i for i, k in enumerate(CONFIG_KEYS)}
    for name in sorted(SETTINGS_TABLE, key=lambda k: order.get(k, 999)):
        spec = SETTINGS_TABLE[name]
        raw = state["settings"].get(name)
        cfg[spec["cn"]] = from_raw(name, raw)
    return cfg

def _encode_raw(raw):
    """备份里 REG_BINARY 用 base64 编码（JSON 不能直接序列化 bytes）。"""
    if isinstance(raw, bytes):
        return {"b64": base64.b64encode(raw).decode("ascii")}
    return raw

def _decode_raw(item):
    if isinstance(item, dict) and "b64" in item:
        return base64.b64decode(item["b64"])
    return item

def make_backup(state):
    """把当前配置备份到 backups/：可读 settings + 全量键值（精确恢复用）。"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    snap = {
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "registry_path": REG_PATH,
        "settings": snapshot_to_config(state),
        "values": [
            {"name": vn, "raw": _encode_raw(val), "type": typ}
            for _key, (vn, val, typ) in state["snapshot"].items()
        ],
    }
    path = BACKUP_DIR / f"endfield_backup_{time.strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)

def do_restore(path):
    """从备份 JSON 恢复全部键值，并删除脚本新建、备份中不存在的已知键。"""
    p = Path(path)
    if not p.exists():
        raise UserError(f"备份文件不存在：{path}")
    try:
        snap = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise UserError(f"备份文件解析失败：{e}")
    values = snap.get("values")
    if not values:
        raise UserError("备份文件缺少原始数据（values），无法精确恢复。")
    key = open_key()
    try:
        backed = set()
        for it in values:
            winreg.SetValueEx(key, it["name"], 0, it["type"], _decode_raw(it["raw"]))
            backed.add(it["name"])
        # 删除脚本可能新建的已知键（备份中不存在）
        cur = {winreg.EnumValue(key, i)[0] for i in range(winreg.QueryInfoKey(key)[1])}
        removed = 0
        for vn in KNOWN_VALUE_NAMES:
            if vn not in backed and vn in cur:
                winreg.DeleteValue(key, vn)
                removed += 1
        if removed:
            info(f"已删除 {removed} 个脚本新建的注册表值。")
    finally:
        key.Close()
    info(f"已从 {path} 恢复原配置。")

def find_latest_backup():
    """返回 backups/ 目录中最新（最近修改）的备份文件路径。"""
    if not BACKUP_DIR.is_dir():
        raise UserError(f"backups 目录不存在：{BACKUP_DIR}")
    files = sorted(BACKUP_DIR.glob("endfield_backup_*.json"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise UserError("backups 目录中没有备份文件。")
    return str(files[0])


# ---------- ⑦ 游戏进程检测 ----------
def is_game_running():
    """检测终末地进程是否在运行（Endfield.exe）。"""
    for exe in GAME_EXES:
        try:
            flag = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            out = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {exe}"],
                capture_output=True, text=True, creationflags=flag, timeout=10,
            )
            if exe.lower() in out.stdout.lower():
                return True
        except Exception:
            pass
    return False


# ---------- ⑧ 宽松 JSON 与配置加载（原样复用 genshin-config-cli） ----------
def ensure_default_config():
    """默认配置文件不存在时生成模板（中文键，全部值为 null）。"""
    if not DEFAULT_CONFIG.exists():
        template = {KEY_CN[k]: None for k in CONFIG_KEYS}
        DEFAULT_CONFIG.write_text(
            json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
        info(f"默认配置文件不存在，已生成模板：{DEFAULT_CONFIG}")
        info("请编辑该文件，把要修改的项从 null 改为目标值后重新运行。")

def _lenient_value(v):
    """宽松解析单个值：引号串、数字、布尔、null、嵌套 JSON，其余按字符串。"""
    v = v.strip()
    if not v or v.lower() in ("null", "none"):
        return None
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
        return v[1:-1]
    if v.lower() == "true":
        return True
    if v.lower() == "false":
        return False
    if v[0] in "[{":
        try:
            return json.loads(v)
        except ValueError:
            return v
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        return v

def _parse_lenient_json(text):
    """宽松 JSON：键和字符串值不用写引号；支持 # 注释、行尾逗号、大括号可省。"""
    data = {}
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        line = line.lstrip("{").strip().rstrip(",").rstrip("}").rstrip(",").strip()
        # 优先 = 分隔：值含冒号时不会被误切
        sep = "=" if "=" in line else (":" if ":" in line else None)
        if not sep:
            continue
        key, _, val = line.partition(sep)
        key = key.strip().strip('"\'')
        if not key:
            continue
        data[key] = _lenient_value(val)
    if not data:
        raise ValueError("宽松 JSON 中未解析出任何键值对")
    return data

def _translate_keys(data):
    """把配置文件里的中文键翻译成内部键（内部键原样保留）。"""
    out = {}
    for k, v in data.items():
        out[CN_TO_KEY.get(k, k)] = v
    return out

def _resolve_config_path(name):
    """把 --config 参数解析为实际路径：依次在根目录与 config/ 目录查找；不带扩展名自动补后缀。"""
    if not name:
        return DEFAULT_CONFIG
    p = Path(name)
    if p.is_absolute() or p.exists():
        return p
    cands = [name]
    if not p.suffix:
        cands += [name + s for s in CONFIG_SUFFIXES]
    for cand in cands:
        for base in (Path(__file__).resolve().parent, CONFIG_DIR):
            f = base / cand
            if f.exists():
                return f
    # 找不到：返回根目录推测路径，供报错提示
    return Path(__file__).resolve().parent / cands[-1]

def load_config(config_path):
    """读取配置文件，返回 {内部键: 值}（中文键自动翻译）。"""
    path = _resolve_config_path(config_path)
    if not path.exists():
        raise UserError(
            f"配置文件不存在：{path}\n"
            f"--config 会在根目录与 config/ 目录中查找（可不写目录、可不带扩展名）。\n"
            f"可把配置模板 config.json 复制到 config/ 目录后修改，或用 --config 指定已有配置文件。")
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise UserError(f"配置文件 '{path}' 编码异常（须为 UTF-8）：{e}")
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        # 标准 JSON 失败 → 尝试宽松格式（键和值不用写引号）
        try:
            data = _parse_lenient_json(text)
        except Exception:
            raise UserError(f"配置文件 '{path}' 解析失败（标准 JSON 或宽松格式均不合法）：{e}")
    if not isinstance(data, dict):
        raise UserError(f"配置文件 '{path}' 的顶层必须是 JSON 对象。")
    data = _translate_keys(data)
    for k in data:
        if k not in KNOWN_NAMES:
            raise UserError(f"配置文件中含未知设置名 '{k}'。可选：{'/'.join(sorted(KNOWN_CN))}")
    return data

def build_changes(config_path):
    """读取配置文件，只保留非 null（要修改）的项。"""
    config = load_config(config_path)
    return {name: val for name, val in config.items() if val is not None}


# ---------- ⑨ CLI ----------
def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="endfield_config",
        description="明日方舟：终末地外部自动化配置：直接读写注册表，修改画面/声音/语言设置。",
    )
    parser.add_argument("--read", action="store_true",
                        help="只读展示当前全部设置，不做任何写入。")
    parser.add_argument("--restore", metavar="FILE",
                        help="从指定备份 JSON 恢复配置后退出。")
    parser.add_argument("--rollback", action="store_true",
                        help="恢复上一个备份（backups/ 中最新的一个）后退出。")
    parser.add_argument("--no-backup", action="store_true",
                        help="应用前跳过备份。")
    parser.add_argument("--config", metavar="FILE",
                        help="使用指定配置文件（在根目录与 config/ 目录中查找，可不写目录/后缀；默认 config.json）。")
    parser.add_argument("--registry-path", metavar="PATH",
                        help="指定注册表键路径（默认 SOFTWARE\\Hypergryph\\Endfield），用于调试。")
    parser.add_argument("--quiet", action="store_true",
                        help="只输出必要信息，抑制变更摘要。")
    parser.add_argument("--wait-game", action="store_true",
                        help="若终末地正在运行，等待其退出后再应用设置（避免游戏退出时写回覆盖）。")
    return parser.parse_args(argv)

def main(argv=None):
    global REG_PATH
    args = parse_args(argv)
    if args.registry_path:
        REG_PATH = args.registry_path

    try:
        # 恢复模式：指定文件或回滚到上一个备份
        if args.restore:
            if args.read or args.rollback:
                raise UserError("--restore 与 --read / --rollback 不能同时使用。")
            do_restore(args.restore)
            return 0
        if args.rollback:
            if args.read:
                raise UserError("--rollback 与 --read 不能同时使用。")
            latest = find_latest_backup()
            do_restore(latest)
            return 0

        state = load_all()

        # 只读模式
        if args.read:
            display_current(state)
            return 0

        # 应用模式：确保自定义配置目录存在；默认配置缺失且未指定其它 → 生成参考模板
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if args.config is None and not DEFAULT_CONFIG.exists():
            ensure_default_config()
            return 0

        config_path = _resolve_config_path(args.config)
        changes = build_changes(args.config)
        if not changes:
            info("未配置任何修改（配置文件中全部为 null）。"
                 f"请编辑 {config_path} 后重试。")
            return 0

        validated = validate_changes(changes)

        if is_game_running():
            if args.wait_game:
                info("检测到终末地正在运行：等待其退出后再修改设置…")
                while is_game_running():
                    time.sleep(3)
                info("终末地已退出，继续应用设置。")
            else:
                warn("检测到终末地正在运行：游戏退出时会把它内存里的设置写回注册表，"
                     "可能覆盖本次修改。建议先退出游戏再应用。")

        backup_path = None
        if not args.no_backup:
            backup_path = make_backup(state)

        apply_all(validated)

        if not args.quiet:
            print_summary(validated, backup_path)
        elif backup_path:
            info(f"原配置已备份到：{backup_path}")
        return 0

    except UserError as e:
        print(f"[错误] {e}", file=sys.stderr)
        return 1
    except ConfigError as e:
        print(f"[错误] {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\n已取消。", file=sys.stderr)
        return 130
    except Exception:
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
