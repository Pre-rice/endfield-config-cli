# 明日方舟终末地外部自动化配置脚本

在**游戏外**直接修改终末地的画面、分辨率、语言等设置。编辑配置文件 → 运行脚本 → 自动写入，无需进游戏手动调。

## 原理

设置存储在 Windows 注册表 `HKEY_CURRENT_USER\SOFTWARE\Hypergryph\Endfield`（Unity PlayerPrefs，REG_DWORD）。注册表键名与游戏内显示不一致（如「帧率」=`video_frame_rate_8`），脚本内置映射表自动换算，可安全新增 / 修改设置键。

## 环境要求

- Windows + Python 3
- 仅使用 Python 标准库，**零第三方依赖**

## 快速开始

1. 首次使用前，请确保**曾经启动过终末地**，让游戏生成注册表配置。
2. 编辑 `config.json`：把要修改的项从 `null` 改为目标值，不动的项保持 `null`。
3. 建议先**退出游戏**再运行（终末地只在**启动时读取**注册表，修改后需重启游戏生效；游戏退出时**不会**覆盖脚本写入的修改）。
4. 运行：

   ```
   python endfield_config.py
   ```

5. 脚本会自动备份原配置到 `backups\`，写入后打印变更摘要。

## 配置文件说明

配置文件是 JSON 对象，`null` = 不修改该项。根目录 `config.json` 是参考模板，自定义配置放在 `config\` 目录里。用 `--config` 指定时不用写目录、可省略后缀，脚本会自动查找，方便准备多套配置切换。

示例（`高画质.conf`）：

```
分辨率: 2560×1440
帧率: 60
各向异性采样: x8
游戏语音: 日语
```

**键和值都可以不用写引号**（宽松格式）：分隔符可用 `:`、`：` 或 `=`，`#` 后可写注释，行尾逗号可省。标准 JSON 写法同样兼容。宽松格式建议用 `.conf` 后缀，避免编辑器按 JSON 校验标红。

### 键与合法取值

名称、取值和顺序皆与游戏内一致。配置文件里写**中文键名**即可（左侧内部键名仅供对照）。

| 内部键名 | 官方中文名 | 合法取值 |
|---|---|---|
| `video_quality_main` | 画面质量 | `极低` / `低` / `中` / `高` / `极高` / `自定义`（自定义只切状态键） |
| `fullscreen` | 显示模式 | `窗口` / `全屏` |
| `resolution` | 分辨率 | 字符串 `"宽×高"`，如 `"1920×1080"` |
| `video_frame_rate_8` | 帧率 | `30` / `60` / `120` |
| `video_quality_effect_1` | 全局特效质量 | `低` / `中` / `高` / `极高` |
| `teammate_skill_effect_strength` | 队友技能特效质量 | `低` / `中` / `高` |
| `teammate_skill_effect_opacity` | 队友技能特效不透明度 | ❌ 不可用（见下文「无法外部修改」） |
| `video_quality_vsync_v2_2` | 垂直同步 | `开` / `关` |
| `video_quality_shadowmap_1` | 阴影质量 | `极低` / `低` / `中` / `高` |
| `video_texture_quality_1` | 纹理质量 | `低` / `中` / `高` |
| `video_quality_volumetricfog_1` | 体积雾 | `关闭` / `低` / `中` / `高` / `极高` |
| `video_quality_volumetriccloud_1` | 体积云 | `极低` / `低` / `中` / `高` / `极高` |
| `video_quality_anisoLevel_1` | 各向异性采样 | `x1` / `x2` / `x4` / `x8` |
| `video_quality_ao_1` | 环境光遮蔽 | `极低` / `低` / `中` / `高` |
| `video_quality_scene_detail_1` | 场景细节 | `低` / `中` / `高` / `极高` |
| `video_quality_environment_renderfeature_1` | 环境细节 | `低` / `中` / `高` |
| `video_quality_grass_sparsity_1` | 植被密度 | `低` / `高` |
| `video_quality_chromatic_aberration_1` | 色差 | `开` / `关` |
| `video_quality_screenspacereflection_1` | 屏幕空间反射 | `关闭` / `低` / `中` / `高` / `极高` |
| `video_quality_upscaler_2` | 画质提升 | `NVIDIA DLSS` / `TAAU` / `AMD FSR3` |
| `video_quality_dlss_mode_1` | DLSS超分辨模式 | `DLAA` / `质量` / `平衡` / `性能` / `超级性能` |
| `video_quality_sharpness_1` | 锐化程度 | 0.0 ~ 1.0 |
| `video_quality_framegen_1` | 帧生成 | `FSR3 Frame Generation` / `DLSS Frame Generation` / `关闭` |
| `video_quality_dlssg_mode_1` | DLSS帧生成模式 | `自动` / `2x` / `3x` / `4x` |
| `video_quality_reflex_1` | NVIDIA Reflex | `开启+增强` / `开启` / `关闭` |
| `video_quality_contactshadow_1` | 接触阴影 | `开` / `关` |
| `audio_suite_mode` | 输出模式 | `桌面音箱` / `家庭影院` / `电视` / `耳机` |
| `audio_suspend_unfocused` | 非当前窗口时静音 | `开` / `关` |
| `audio_controller` | 控制器喇叭 | `开` / `关` |
| `audio_spatial` | 空间音频渲染 | `开` / `关` |
| `language_text_change` | 游戏语言 | `简体中文` / `英语` / `日语` / `韩语` / `繁体中文` |
| `language_audio` | 游戏语音 | `中文` / `英语` / `日语` / `韩语` |
| `controller_keyboard_type` | 键盘布局 | `默认` / `德语` / `法语` |

**显示模式 / 分辨率**：分辨率写 `宽×高`（`*` 或 `×` 分隔皆可），脚本会同步写入宽、高四个注册表键；显示模式「窗口」/「全屏」会同步写两个键。

**画面质量**：预设档（`极低`~`极高`）一键应用整套。设置**受预设控制的单项**（全局特效质量、阴影质量、体积雾、体积云、环境光遮蔽、场景细节、环境细节、植被密度、屏幕空间反射）或写 `自定义` 时，脚本自动切到自定义档（`video_custom_quality=1`）；写 `自定义` 时不修改主档位值。其余画质键及声音、语言设置为**独立设置**，不受档位影响，随时可改。

### 重要行为

- **游戏运行时**：终末地运行中会把游戏内改动**实时写回**注册表，但只在**启动时读取**。因此运行中用脚本修改是安全的（不会被游戏退出覆盖），只是需重启游戏生效；之后在游戏内调整会覆盖脚本刚写入的对应键。
- **受档位控制的 9 个单项**只在「画面质量 = 自定义」并在游戏中调整过对应项后才会出现在注册表中；不调整则不生成。
- **未知设置名**：配置文件里写了表格之外的键名会报错。
- 脚本不会删除注册表中的未知 / 未来字段，只会按需追加或修改。

### 无法外部修改

**音量（总音量 / 语音 / 音乐 / 音效）**和**队友技能特效不透明度**不存储在注册表中，本脚本无法修改（实测确认：注册表相关键是引擎实时状态、不反映滑块数值；音量真实持久化在游戏数据目录的加密数据库中），只能在**游戏内**调整。上文表格保留「队友技能特效不透明度」一行仅为对照游戏内设置顺序。

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
| `--wait-game` | 若终末地正在运行，等待其退出后再应用设置 |
| `--registry-path PATH` | 覆盖注册表键路径（默认 `SOFTWARE\Hypergryph\Endfield`），用于调试 |

**退出码**：`0` = 成功；`1` = 输入 / 校验错误；`2` = 注册表 / 解析错误；`130` = 用户中断。

## 多套配置

把配置复制到 `config\` 目录下分别命名，用 `--config` 切换：

```
python endfield_config.py --config 高画质
python endfield_config.py --config 低画质
```

## 备份与恢复

每次应用前自动备份到 `backups\`，备份为可读的中文键清单。恢复或回滚：

```
python endfield_config.py --restore backups\endfield_backup_时间戳.json
python endfield_config.py --rollback
```

## 声明

本脚本为非官方工具，与鹰角网络（Hypergryph）无任何关联。
