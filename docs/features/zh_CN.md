# MAKO 助手 — 功能介绍

[English](en.md) · [台灣正體中文](zh_TW.md) · **简体中文** · [日本語](ja.md) · [Deutsch](de.md) · [Français](fr.md) · [Español](es.md) · [Italiano](it.md) · [ไทย](th.md) · [Tiếng Việt](vi.md) · [Bahasa Melayu](ms.md) · [हिन्दी](hi.md)

**MAKO 助手**是一款 Linux 桌面图形工具，无需手动编辑任何配置文件，就能为 Steam 游戏一键开启或关闭 **MAKO Renderer 补帧（Mako FG）**。

## 适用人群

在 Steam Deck 的游戏模式下，MAKO 有 Decky 插件，可以直接在游戏中设置。但如果你用的是**普通 Linux 台式机或笔记本**（例如 Arch、Fedora、Ubuntu，搭配 KDE Plasma 或 GNOME），要让一款游戏用上 MAKO，通常得手动完成这些事：

1. 在 Steam 的“属性 → 启动选项”中加入 `~/.local/bin/mako-launch %command%`，还不能破坏原有的参数。
2. 找出游戏**实际运行的**程序名称（很多游戏先打开启动器，或是 Unreal 引擎的 `*-Shipping.exe`）。
3. 在 MAKO 配置中创建游戏 profile，填入正确的匹配进程（`active_in`）。
4. 游戏更新后可执行文件路径或名称改变时，再重做一遍。
5. 游戏打开后，仍然不确定补帧到底有没有在工作。

MAKO 助手把这些步骤整合成一个按钮，并在游戏运行时告诉你 MAKO **实际**启用了哪些功能。

## 使用前必须先准备

> ⚠ **MAKO 助手不包含 MAKO Renderer，也不会替你安装。** 它只是帮你管理 MAKO 的配置。

请先自行完成：

1. **安装 MAKO Renderer（standalone 版）**，按照 MAKO 自身的安装说明完成。安装后应该会有 `~/.local/bin/mako-launch`。
2. **打开一次 MAKO UI**，创建默认配置。这会生成 `~/.config/mako-render/conf.toml` 和默认 profile `mako`。MAKO 助手为游戏创建的 profile，都以这个默认 profile 为模板。
3. **安装 Steam**。支持原生版（`~/.local/share/Steam`、`~/.steam`）、Flatpak 版和 Snap 版。

请确认以上都已完成、MAKO 本身也能正常工作，再用 MAKO 助手为游戏安装 Mako FG。

可选：**Decky Loader**。装了之后，Steam 运行中也能即时应用启动选项，无需关闭 Steam（详见下方“启动选项的写入方式”）。

## 功能

### 1. 自动扫描 Steam 游戏库

- 第一次打开时自动扫描**所有** Steam 游戏库（包括其他硬盘上的游戏库），之后可以点击“⟳ 重新扫描 Steam 游戏列表”。
- 自动排除 Proton、Steam Linux Runtime 这类工具，只列出游戏。
- 游戏名称按界面语言显示 Steam 官方的本地化名称（例如“巫师3：狂猎”），并按该语言的习惯排序。
- 每款游戏都显示封面、当前的启动选项、MAKO 配置以及检测到的游戏可执行文件路径。

### 2. 一键“安装 Mako FG”

点击“安装 Mako FG”后，工具会：

- **注入启动选项**：在 Steam 启动选项中加入 `~/.local/bin/mako-launch %command%`，并**保留原有设置**。例如 `FOO=1 %command% -dx11` 会变成 `FOO=1 ~/.local/bin/mako-launch %command% -dx11`。
- **检测真正的游戏可执行文件**：根据 Steam 的游戏信息判断，能处理启动器（自动改为查找安装目录中的实际游戏程序）和 Unreal 引擎的 `*-Shipping.exe`，并排除常见的辅助程序。
- **创建 MAKO 游戏配置**：以默认 profile `mako` 为模板，在 `conf.toml` 中创建这款游戏专属的 profile，并写入 MAKO 的 profile 元数据。**MAKO UI 和 Decky 插件都能看到、也能直接修改**这个 profile。
- **避免重复匹配**：如果默认 profile `mako` 也匹配到这款游戏的可执行文件，会自动从 `mako` 中移除，让游戏只使用自己的 profile。如果另一款游戏的 profile 也匹配到同一个可执行文件，会提示你，但不会自动修改。

### 3. 启动选项的写入方式

Steam 只在启动时读取启动选项，并在退出时覆盖配置文件。为了不让修改被 Steam 覆盖，MAKO 助手会根据 Steam 的状态自动选择写入方式，状态也会显示在窗口上：

| Steam 状态 | 写入方式 |
|---|---|
| 未运行 | 直接修改 Steam 的 `localconfig.vdf`（先备份） |
| 运行中，且能连接到 Steam 客户端（需要 Decky Loader） | 通过 Steam 客户端即时应用，无需重启 Steam |
| 运行中，但无法连接 | 询问你是否关闭 Steam → 应用 → 自动重新打开 Steam |

### 4. 移除

- “移除”只会从启动选项中去掉 `mako-launch`，其他参数保持不变。
- **默认保留** MAKO 中这款游戏的配置，下次重新安装时可以沿用。勾选“同时移除 MAKO Renderer 游戏配置”才会一起删除。

### 5. 导入已有配置

如果某款游戏你以前就手动加过 `mako-launch`，它会显示“导入配置”按钮。点击后，工具会为它创建 MAKO 游戏配置，并纳入之后的路径自动更新。

### 6. 游戏更新后自动更新路径

- 每次重新扫描时，工具会重新检测**通过本工具安装过**的游戏的可执行文件。如果游戏更新后可执行文件换了位置或名称，会自动更新 MAKO 的匹配进程，并在日志区列出变更。
- 你在 MAKO UI 中**手动添加**的匹配进程会保留。
- 如果你在 MAKO UI 中删除了某款游戏的 profile，工具会尊重这个决定，不会自动重建。
- 游戏库暂时离线（例如外接硬盘没有连接）时，相关游戏的配置保持不变。

### 7. 从列表直接启动游戏

每一行都有“▶ 启动”按钮，会通过 Steam 启动游戏。游戏运行时，按钮会显示“运行中”。

### 8. 实时显示实际启用的 MAKO 功能

“运行中的 MAKO 功能”一栏每 3 秒更新一次。显示的是 MAKO 在游戏中**实际应用**的状态，而不是配置文件里写了什么：

- **补帧**：固定倍数（例如 ×2）或自适应（目标 FPS、最高倍数）、Flow 比例、性能模式。
- **缩放**：缩放方式与分辨率（例如 1280×720 → 2560×1440）、超采样。
- **其他图层**：vkBasalt、Zink、ALSA 音频。
- **待应用的变更**：例如“需重启游戏”“需重建交换链”，以及 MAKO 报告的错误。

如果游戏装了 Mako FG，却没有真正加载 MAKO，也会显示出来，方便你排查问题。

### 9. 游戏启动水印

MAKO 助手开着时启动游戏，一检测到 MAKO 已经在游戏中工作，就会在屏幕右下角显示当前启用的 MAKO 功能约 10 秒，然后淡出：

- 每次启动只显示一次，不会抢占键盘鼠标焦点，鼠标也能直接点穿。
- 可以叠加在全屏的 Proton 游戏上。
- 如果装了 Mako FG 的游戏启动 90 秒后仍未加载 MAKO，会改为显示警告。
- 可以用工具栏的“游戏启动水印”复选框关闭。

### 10. 搜索与筛选

- 可以用游戏名称（任何语言的名称都可以）或 App ID 搜索。
- 筛选：全部游戏、已安装 Mako FG、未安装 Mako FG、仅保留 MAKO 配置、运行中。

### 11. 12 种界面语言

台灣正體中文、简体中文、English、日本語、Deutsch、Français、Español、Italiano、ไทย、Tiếng Việt、Bahasa Melayu、हिन्दी。

第一次打开时按系统语言自动选择，之后可以在右上角切换，立即生效并记住选择。

### 12. 安全设计

- 修改 `conf.toml` 和 Steam 的 `localconfig.vdf` 之前，都会先备份（`*.mako-assistant.bak`）。
- 写入 `conf.toml` 后，会用 `mako-cli validate` 验证。MAKO 不接受的话，会自动还原。
- Steam 运行时，绝不直接修改 `localconfig.vdf`。

## 安装 MAKO 助手

**AppImage（推荐）**：已内置 Python 和 Qt，无需另外安装。

```bash
chmod +x MAKO_Assistant-*-x86_64.AppImage
./MAKO_Assistant-*-x86_64.AppImage
```

**从源代码运行**：需要 Python 3.11 及以上版本和 PyQt6（Arch：`sudo pacman -S python-pyqt6`）。

```bash
./mako-assistant    # 直接运行
./install.sh        # 安装到 ~/.local/share/mako-assistant 并创建应用程序菜单项
```

## 已知限制

- **Steam Deck 游戏模式（gamescope）下不会显示水印**。Steam Deck 上建议使用 MAKO 的 Decky 插件。
- 以原生 Wayland 独占全屏运行的游戏，可能会遮住水印。
- 即时应用启动选项只支持 Decky Loader 打开的 Steam 客户端端口（8080）。没有 Decky 时，请关闭 Steam 后再应用，或让工具代为关闭并重新打开 Steam。
- “实际启用功能”和 MAKO 配置元数据的格式，是按当前 MAKO 版本解析的。MAKO 或 Steam 大幅更新后，可能暂时无法显示（会显示“—”），但不影响安装与移除。
- 泰语、越南语、马来语、印地语的右键菜单是英文（Qt 没有这几种语言的官方翻译）。Steam 没有马来语和印地语的游戏名称，这两种语言一律显示原文名称。
- 备份文件只保留最近一份。

## 数据存放位置

| 位置 | 内容 |
|---|---|
| `~/.config/mako-assistant/state.json` | MAKO 助手自身的状态：游戏列表缓存、通过本工具安装过的游戏、界面语言、水印开关 |
| `~/.config/mako-render/conf.toml` | MAKO Renderer 配置（各游戏 profile） |
| `~/.config/mako-render/profile-metadata.json` | MAKO profile 元数据（游戏名称、Steam App ID） |
| `<Steam>/userdata/<用户 ID>/config/localconfig.vdf` | Steam 启动选项 |
