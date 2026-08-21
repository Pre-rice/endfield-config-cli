# 明日方舟：终末地外部自动化配置脚本

在**游戏外**直接修改《明日方舟：终末地》的画面、分辨率、语言等设置。编辑配置文件 → 运行脚本 → 自动写入，无需进游戏手动调。

## 原理

终末地的设置存储在 Windows 注册表 `HKEY_CURRENT_USER\SOFTWARE\Hypergryph\Endfield` 下（Unity PlayerPrefs 格式）。

- 每个设置是一个 **REG_DWORD**（32 位整数）值。
- 值名 = `键名_h<哈希>`，哈希是 Unity 的 **djb2-xor** 算法（`h=5381; h=(h*33)^ord(c)`）。脚本按同样的算法计算值名，因此可以安全地新增 / 修改任意设置键。
- 键名不与游戏内显示一致：例如游戏内「帧率」对应注册表键 `video_frame_rate_8`，「画面质量」对应 `video_quality_main`。脚本内置了键名映射表。

## 环境要求

- Windows + Python 3
- 仅使用 Python 标准库（`winreg` / `json` / `base64` / `argparse`），**零第三方依赖**

## 快速开始

1. 首次使用前，请确保**曾经启动过终末地**，让游戏生成注册表配置。
2. 编辑 `config.json`（与脚本同目录）：把要修改的项从 `null` 改为目标值，不动的项保持 `null`。
3. 确保已经**退出游戏**（游戏运行时会把它内存里的设置写回注册表，覆盖修改；脚本检测到游戏运行会给出警告）。
4. 运行：

   ```
   python endfield_config.py
   ```

5. 脚本会自动备份原配置到 `backups\`，写入后打印变更摘要。

## 配置文件说明

配置文件是 JSON 对象，`null` = 不修改该项。根目录 `config.json` 是参考模板，自定义配置放在 `config\` 目录里（该目录不参与版本控制）。用 `--config` 指定时**不用写目录**：脚本会在根目录与 `config\` 目录中查找，文件名也**可不带后缀**。可准备多套配置，切换方便。

示例（`高画质.json`）：

```json
{
  "分辨率": "2560×1440",
  "帧率": "60",
  "各向异性采样": "x8",
  "游戏语音": "日语"
}
```

**键和值都可以不用写引号**（宽松格式）：冒号换成 `:` 或 `=`，`#` 后可写注释，行尾逗号可省。标准 JSON 写法同样兼容。

宽松格式的文件建议用 **`.conf` 后缀**（如 `高画质.conf`）——编辑器不会把它当 JSON 校验标红；若用 `.json` 后缀，编辑器会按 JSON 校验报错（脚本本身两种都能读）。`--config 高画质` 会自动在 `.json` / `.conf` / `.txt` / `.cfg` 中查找。

### 键与合法取值

名称、取值和顺序皆与游戏内一致。「待标定」表示该档位的注册表原始值尚未确认，选中会报错（见下文「待标定档位」）。内部键名（左侧代码列）仅供对照，配置文件里写**中文键名**即可。

| 内部键名 | 官方中文名 | 合法取值 |
|---|---|---|
| `video_quality_main` | 画面质量 | `自定义` / `极低` / `低` / `中` / `高` / `极高`（仅 `高` 已标定） |
| `fullscreen` | 显示模式 | `窗口` / `全屏`（全屏下个别键待标定） |
| `resolution` | 分辨率 | 字符串 `"宽×高"`，如 `"1920×1080"` |
| `video_frame_rate_8` | 帧率 | `30` / `60` / `120` |
| `video_quality_effect_1` | 全局特效质量 | `低` / `中` / `高` / `极高` |
| `teammate_skill_effect_strength` | 队友技能特效质量 | `低` / `中` / `高`（1/2/3 编码，非 ×1000） |
| `teammate_skill_effect_opacity` | 队友技能特效不透明度 | 0.1 ~ 1.0（×1000 换算为推断） |
| `video_quality_vsync_v2_2` | 垂直同步 | `开` / `关`（待标定） |
| `video_quality_shadowmap_1` | 阴影质量 | `极低` / `低` / `中` / `高` |
| `video_texture_quality_1` | 纹理质量 | `低` / `中` / `高`（仅 `高` 已标定） |
| `video_quality_volumetricfog_1` | 体积雾 | `关闭` / `低` / `中` / `高` / `极高` |
| `video_quality_volumetriccloud_1` | 体积云 | `极低` / `低` / `中` / `高` / `极高` |
| `video_quality_anisoLevel_1` | 各向异性采样 | `x1` / `x2` / `x4` / `x8` |
| `video_quality_ao_1` | 环境光遮蔽 | `极低` / `低` / `中` / `高` |
| `video_quality_scene_detail_1` | 场景细节 | `低` / `中` / `高` / `极高` |
| `video_quality_environment_renderfeature_1` | 环境细节 | `低` / `中` / `高` |
| `video_quality_grass_sparsity_1` | 植被密度 | `低` / `高` |
| `video_quality_chromatic_aberration_1` | 色差 | `开` / `关`（待标定） |
| `video_quality_screenspacereflection_1` | 屏幕空间反射 | `关闭` / `低` / `中` / `高` / `极高` |
| `video_quality_upscaler_2` | 画质提升 | `NVIDIA DLSS` / `TAAU` / `AMD FSR3` |
| `video_quality_dlss_mode_1` | DLSS超分辨模式 | `DLAA` / `质量` / `平衡` / `性能` / `超级性能`（待标定） |
| `video_quality_sharpness_1` | 锐化程度 | 0.0 ~ 1.0（×1000 换算） |
| `video_quality_framegen_1` | 帧生成 | `FSR3 Frame Generation` / `DLSS Frame Generation` / `关闭`（待标定） |
| `video_quality_dlssg_mode_1` | DLSS帧生成模式 | `自动` / `2x` / `3x` / `4x`（待标定） |
| `video_quality_reflex_1` | NVIDIA Reflex | `开启+增强` / `开启` / `关闭`（待标定） |
| `video_quality_contactshadow_1` | 接触阴影 | `开` / `关`（待标定） |
| `audio_suite_mode` | 输出模式 | `桌面音箱` / `家庭影院` / `电视` / `耳机`（仅 `耳机` 已标定） |
| `audio_suspend_unfocused` | 非当前窗口时静音 | `开` / `关`（待标定） |
| `audio_controller` | 控制器喇叭 | `开` / `关`（待标定） |
| `audio_spatial` | 空间音频渲染 | `开` / `关`（待标定） |
| `language_text_change` | 游戏语言 | 待确认（游戏内档位信息未提供，可填整数原始值） |
| `language_audio` | 游戏语音 | `中文` / `英语` / `日语` / `韩语`（仅 `中文` 已标定） |
| `controller_keyboard_type` | 键盘布局 | `默认` / `德语` / `法语`（待标定） |

**显示模式**：游戏内的「显示模式」由两个注册表键组成——`video_full_screen` 与 `Screenmanager Fullscreen mode`。两者均已标定「窗口」；「全屏」下 `Screenmanager Fullscreen mode` 的原始值尚未标定，脚本会写入 `video_full_screen` 并跳过未标定的键（附警告）。

**分辨率**：宽/高会同步写入四个注册表键（`Screenmanager Resolution Width/Height` + `video_resolution_width/height`）。字符串用 `*` 或 `×` 分隔皆可。

### 数值换算

- **锐化程度 / 队友技能特效不透明度**：按 ×1000 换算（游戏内 0.5 → 注册表 500）。
- **画质档位**：各向异性 `x4` → 4000、帧率 `60` → 2000、画质提升 `NVIDIA DLSS` → 1000 等（映射见脚本 SETTINGS_TABLE）。

### 待标定档位

部分档位的注册表原始值尚未逐一确认（表格中标注「待标定」）。选中未标定的档位时脚本会**报错退出**（退出码 1），并提示两种办法：

1. **`--read` 查看原始值**：把游戏内切到该档位，运行 `python endfield_config.py --read`，读取该设置的「原始」值，再把这个值填回 config（见下一条），或按「标定指南」回填到脚本映射表。
2. **整数透传**：配置里直接填一个整数（如 `"帧生成": 1000`），脚本会**原样写入**注册表，不做任何换算。这是给高级用户 / 标定用的逃生通道，风险自负。

### 重要行为

- **单项画质键在「自定义」档下才生成**：阴影质量、体积雾、体积云、环境光遮蔽、场景细节、环境细节、植被密度、屏幕空间反射、全局特效质量、队友技能特效质量等键，只在「画面质量 = 自定义」并在游戏中调整过对应项后才会出现在注册表中；不调整则不生成。各键档位映射见上文表格。
- **画面质量「自定义」不改变 `video_quality_main`**：切换自定义后该键仍保留原预设档位的值，自定义状态由单独的状态键表达。因此用脚本统一调整画质时，直接写 `video_quality_main` 的档位即可（预设档优先，会覆盖单项自定义）。
- **未知设置名**：配置文件里写了表格之外的键名会报错。
- 脚本不会删除注册表中的未知 / 未来字段，只会按需追加或修改，保证兼容性。

### 无法外部修改：音量

总音量 / 语音音量 / 音乐音量 / 音效音量**不存储在注册表中**，本脚本无法修改。经多轮实验确认：

- 注册表 `audio_global` / `audio_voice` / `audio_music` / `audio_sfx` 键是**音频引擎的实时状态**，不是音量滑块：滑块全拖到 10 时它们均为 0.0f；写入任意值游戏启动即覆盖；运行时调整音量，注册表全部键快照对比无任何变化。
- 音量真实持久化在游戏数据目录的**加密数据库**（`Endfield_Data/Persistent/eld_Endfield.db` 等，AES 级全加密），外部无法读取或写入。
- 因此四个音量只能在**游戏内**调整，脚本不包含音量项。

## 命令行参数

| 参数 | 说明 |
|---|---|
| （无参数） | 应用 `config.json`，自动备份后写入 |
| `--config FILE` | 使用指定配置文件（支持多套配置） |
| `--read` | 只读展示当前全部设置，不做任何写入 |
| `--restore FILE` | 从指定备份文件恢复配置后退出 |
| `--rollback` | 回滚到**上一个备份**（`backups\` 中最新一个）后退出 |
| `--no-backup` | 应用前跳过自动备份 |
| `--quiet` | 抑制变更摘要，只输出必要信息 |
| `--wait-game` | 若终末地正在运行，等待其退出后再应用设置（避免游戏退出时写回覆盖） |
| `--registry-path PATH` | 覆盖注册表键路径（默认 `SOFTWARE\Hypergryph\Endfield`），用于调试 |

**退出码**：`0` = 成功；`1` = 输入 / 校验错误；`2` = 注册表 / 解析错误；`130` = 用户中断。

## 多套配置

把 `config.json` 复制到 `config\` 目录下，分别命名并编辑：

```
python endfield_config.py --config 高画质
python endfield_config.py --config 低画质
```

## 备份与恢复

每次应用前，脚本自动把当前配置备份到 `backups\endfield_backup_时间戳.json`，备份里 `settings` 是**与 config 同形式的中文键可读清单**（可直接阅读），另附全部键值（REG_BINARY 用 base64 编码）用于精确恢复。恢复时还会**删除脚本新建、备份中不存在的已知键**。

恢复（指定文件，或直接回滚到上一个备份）：

```
python endfield_config.py --restore backups\endfield_backup_20260821_211109.json
python endfield_config.py --rollback
```

## 标定指南（补全待标定档位）

脚本的映射表在 `endfield-config.py` 的 `SETTINGS_TABLE` 中。补全某个待标定档位：

1. 进入游戏，把该设置切到目标档位，然后退出游戏（或保持运行，注册表会实时更新）。
2. 运行 `python endfield_config.py --read`，记下该设置的「原始」值。
3. 打开脚本，把原始值填到 `SETTINGS_TABLE` 里对应档位（如 `"高": 2`），`conf` 改为 `"anchored"`。
4. 重新运行脚本验证该档位可正常写入。

## 声明

本脚本为非官方工具，与鹰角网络（Hypergryph）无任何关联。
