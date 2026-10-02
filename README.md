# MAKO 助手 (MAKO Assistant)

為 Steam 遊戲一鍵安裝 / 移除 MAKO Renderer 補幀（Mako FG）的桌面工具（PyQt6）。

## 功能

- **自動掃描**：第一次開啟時自動掃描所有 Steam 遊戲庫（`libraryfolders.vdf` + `appmanifest_*.acf`），之後可按「重新掃描 Steam 遊戲清單」。
- **安裝 Mako FG**
  - 在 Steam 啟動選項注入 `~/.local/bin/mako-launch %command%`（保留原有的環境變數與參數，例如 `FOO=1 %command%` → `FOO=1 ~/.local/bin/mako-launch %command%`）。
  - 從 `appinfo.vdf` 偵測遊戲實際執行檔（含啟動器→真正的遊戲 exe、Unreal `*-Shipping.exe`），以 MAKO 預設 profile（`mako`）為範本，在 `~/.config/mako-render/conf.toml` 建立遊戲 profile，並寫入 `profile-metadata.json`（`kind: game`、`steam_app_id`），MAKO UI / Decky 都能辨識。
  - 若預設 profile `mako` 的比對程式也包含這個遊戲的執行檔，會從 `mako` 移除，讓遊戲只套用自己的 profile（重新掃描時也會修正既有的重複）。若其他遊戲的 profile 也比對到同一個執行檔，只會提示、不自動修改。
- **移除**：只從啟動選項移除 `mako-launch`；勾選「一併移除 MAKO Renderer 遊戲設定」才會刪除該遊戲的 profile。
- **自動更新遊戲路徑**：每次重新掃描時，對「透過本工具安裝過 Mako FG」的遊戲重新偵測執行檔，更新 `active_in`；使用者在 MAKO UI 手動加入的比對程式會保留。
- **啟動遊戲**：遊戲列表每一列都有「▶ 啟動」按鈕（透過 `steam://rungameid/<AppID>`），遊戲執行中會顯示「執行中」。
- **執行中的 MAKO 功能（實際狀態，非設定檔）**：每 3 秒偵測一次執行中的 Steam 遊戲：
  - 以程序環境變數 `SteamAppId` 對應遊戲；以 `/proc/<pid>/maps` 確認 `libmako-render.so`、vkBasalt 真的被載入。
  - 讀取 MAKO 圖層寫出的 `~/.config/mako-render/runtime-state/*.json`（套用中的補幀倍數 / 自適應目標、Flow、效能模式、縮放方式與解析度、待套用變更、錯誤）。這些檔案在遊戲結束後會殘留，所以只採用 PID 仍存活且啟動時間（`process_start_ticks`）相符的檔案。
- **遊戲啟動浮水印**：MAKO 助手開著時啟動遊戲，一偵測到 MAKO 已在遊戲中建立畫面，就在右下角顯示執行中的 MAKO 功能約 10 秒後淡出（每次啟動只顯示一次；開啟助手前就在跑的遊戲不顯示）。已裝 Mako FG 的遊戲若 90 秒後仍未載入 MAKO，會顯示警告。浮水印用獨立的 X11（XWayland）視窗，才能疊在全螢幕遊戲上，且不搶焦點、滑鼠可穿透；可在工具列的核取方塊關閉。Steam Deck 遊戲模式（gamescope）下不會顯示。
- **多國語言**：台灣正體中文、简体中文、English、日本語、Deutsch、Français、Español、Italiano、ไทย、Tiếng Việt、Bahasa Melayu、हिन्दी。首次依系統語系自動選擇，可在右上角切換（即時生效並記住）。Qt 內建文字（右鍵選單等）在前 7 種語言也會翻譯；Qt 官方沒有泰、越、馬來、印地語翻譯，這幾種語言的右鍵選單會是英文。

## 啟動選項的寫入方式

Steam 只在啟動時讀取 `localconfig.vdf`，並在關閉時覆寫它，因此：

| Steam 狀態 | 寫入方式 |
|---|---|
| 未執行 | 直接修改 `userdata/<id>/config/localconfig.vdf`（先備份為 `.mako-assistant.bak`） |
| 執行中且 CEF 除錯埠可用（Decky Loader 會開啟） | 透過 `SteamClient.Apps.SetAppLaunchOptions` 即時套用 |
| 執行中但無法連線 | 詢問是否關閉 Steam → 套用 → 重新開啟 Steam |

寫入 `conf.toml` 前會備份為 `conf.toml.mako-assistant.bak`，寫入後以 `mako-cli validate` 驗證，失敗會自動還原。

## 安裝與執行

```bash
./install.sh        # 安裝到 ~/.local/share/mako-assistant，並建立選單項目
mako-assistant      # 或直接在原始碼目錄執行 ./mako-assistant
```

需求：Python 3.11+、PyQt6（`sudo pacman -S python-pyqt6`）。

## AppImage

```bash
./build-appimage.sh   # 輸出 dist/MAKO_Assistant-<版本>-x86_64.AppImage
```

AppImage 內含可攜式 CPython 3.13（uv / python-build-standalone）與精簡過的 PyQt6，目標機器不需安裝 Python 或 Qt。建置需要 `uv` 與網路（下載 PyQt6 wheel 與 appimagetool）。

## 測試

```bash
python3 -m unittest discover -s tests -v
```

本工具的狀態（已管理的遊戲、遊戲清單快取）存在 `~/.config/mako-assistant/state.json`。
