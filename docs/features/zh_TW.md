# MAKO 助手 — 功能介紹

[English](en.md) · **台灣正體中文** · [简体中文](zh_CN.md) · [日本語](ja.md) · [Deutsch](de.md) · [Français](fr.md) · [Español](es.md) · [Italiano](it.md) · [ไทย](th.md) · [Tiếng Việt](vi.md) · [Bahasa Melayu](ms.md) · [हिन्दी](hi.md)

**MAKO 助手**是一套 Linux 桌面圖形工具，讓你不用手動編輯任何設定檔，就能替 Steam 遊戲一鍵開啟或關閉 **MAKO Renderer 補幀（Mako FG）**。

## 這套工具是給誰用的

在 Steam Deck 的遊戲模式下，MAKO 有 Decky 外掛可以直接在遊戲中設定。但如果你用的是**一般 Linux 桌面電腦或筆電**（例如 Arch、Fedora、Ubuntu，搭配 KDE Plasma 或 GNOME），要讓一款遊戲用上 MAKO，通常得手動完成這些事：

1. 在 Steam 的「內容 → 啟動選項」加入 `~/.local/bin/mako-launch %command%`，還不能弄壞原本的參數。
2. 找出遊戲**實際執行的**程式名稱（很多遊戲先開啟動器，或是 Unreal 引擎的 `*-Shipping.exe`）。
3. 在 MAKO 設定中建立遊戲 profile，填入正確的比對程式（`active_in`）。
4. 遊戲更新後執行檔路徑或名稱改變時，再重做一次。
5. 遊戲開起來後，仍然不確定補幀到底有沒有在運作。

MAKO 助手把這些步驟整合成一個按鈕，並在遊戲執行時告訴你 MAKO **實際**啟用了哪些功能。

## 使用前必須先準備

> ⚠ **MAKO 助手不包含 MAKO Renderer，也不會替你安裝。** 它只是幫你管理 MAKO 的設定。

請先自行完成：

1. **安裝 MAKO Renderer（standalone 版）**，依照 MAKO 本身的安裝說明完成。安裝後應該要有 `~/.local/bin/mako-launch`。
2. **開啟一次 MAKO UI**，建立預設設定。這會產生 `~/.config/mako-render/conf.toml` 和預設 profile `mako`。MAKO 助手幫遊戲建立的 profile，都以這個預設 profile 為範本。
3. **安裝 Steam**。支援原生版（`~/.local/share/Steam`、`~/.steam`）、Flatpak 版與 Snap 版。

請確認以上都完成、MAKO 本身也能正常運作，再用 MAKO 助手幫遊戲安裝 Mako FG。

選用：**Decky Loader**。裝了之後，Steam 執行中也能即時套用啟動選項，不必關閉 Steam（詳見下方〈啟動選項的寫入方式〉）。

## 功能

### 1. 自動掃描 Steam 遊戲庫

- 第一次開啟時自動掃描**所有** Steam 遊戲庫（包含其他硬碟上的遊戲庫），之後可以按「⟳ 重新掃描 Steam 遊戲清單」。
- 自動排除 Proton、Steam Linux Runtime 這類工具，只列出遊戲。
- 遊戲名稱依介面語言顯示 Steam 官方的在地化名稱（例如「巫師3：狂獵」），並依該語言的習慣排序（正體中文依筆畫）。
- 每款遊戲都顯示封面、目前的啟動選項、MAKO 設定與偵測到的遊戲執行檔路徑。

### 2. 一鍵「安裝 Mako FG」

按一下「安裝 Mako FG」，工具會：

- **注入啟動選項**：在 Steam 啟動選項加入 `~/.local/bin/mako-launch %command%`，並**保留原有的設定**。例如 `FOO=1 %command% -dx11` 會變成 `FOO=1 ~/.local/bin/mako-launch %command% -dx11`。
- **偵測真正的遊戲執行檔**：從 Steam 的遊戲資訊判斷，能處理啟動器（自動改找安裝目錄中的實際遊戲程式）與 Unreal 引擎的 `*-Shipping.exe`，並排除常見的輔助程式。
- **建立 MAKO 遊戲設定**：以預設 profile `mako` 為範本，在 `conf.toml` 建立這款遊戲專屬的 profile，並寫入 MAKO 的 profile 中繼資料。**MAKO UI 和 Decky 外掛都看得到、也能直接修改**這個 profile。
- **避免重複比對**：如果預設 profile `mako` 也比對到這款遊戲的執行檔，會自動從 `mako` 移除，讓遊戲只套用自己的 profile。如果另一款遊戲的 profile 也比對到同一個執行檔，會提示你，但不會自動修改。

### 3. 啟動選項的寫入方式

Steam 只在啟動時讀取啟動選項，並在關閉時覆寫設定檔。為了不讓修改被 Steam 蓋掉，MAKO 助手會依 Steam 的狀態自動選擇寫入方式，狀態也會顯示在視窗上：

| Steam 狀態 | 寫入方式 |
|---|---|
| 未執行 | 直接修改 Steam 的 `localconfig.vdf`（先備份） |
| 執行中，且可連線到 Steam 用戶端（需 Decky Loader） | 透過 Steam 用戶端即時套用，不必重開 Steam |
| 執行中，但無法連線 | 詢問你是否要關閉 Steam → 套用 → 自動重新開啟 Steam |

### 4. 移除

- 「移除」只會從啟動選項拿掉 `mako-launch`，其他參數保持原樣。
- **預設保留** MAKO 中這款遊戲的設定，下次重新安裝時可以沿用。勾選「一併移除 MAKO Renderer 遊戲設定」才會一起刪掉。

### 5. 匯入既有設定

如果某款遊戲你以前就手動加過 `mako-launch`，它會顯示「匯入設定」按鈕。按下後，工具會替它建立 MAKO 遊戲設定，並納入之後的路徑自動更新。

### 6. 遊戲更新後自動更新路徑

- 每次重新掃描時，工具會重新偵測**透過本工具安裝過**的遊戲的執行檔。如果遊戲更新後執行檔改了位置或名稱，會自動更新 MAKO 的比對程式，並在記錄區列出變更。
- 你在 MAKO UI 中**手動加入**的比對程式會保留。
- 如果你在 MAKO UI 中刪除了某款遊戲的 profile，工具會尊重這個決定，不會自動重建。
- 遊戲庫暫時離線（例如外接硬碟沒接上）時，相關遊戲的設定維持不變。

### 7. 從列表直接啟動遊戲

每一列都有「▶ 啟動」按鈕，會透過 Steam 啟動遊戲。遊戲執行中時，按鈕會顯示「執行中」。

### 8. 即時顯示實際啟用的 MAKO 功能

「執行中的 MAKO 功能」欄位每 3 秒更新一次。顯示的是 MAKO 在遊戲中**實際套用**的狀態，不是設定檔裡寫了什麼：

- **補幀**：固定倍數（例如 ×2）或自適應（目標 FPS、最高倍數）、Flow 比例、效能模式。
- **縮放**：縮放方式與解析度（例如 1280×720 → 2560×1440）、超取樣。
- **其他圖層**：vkBasalt、Zink、ALSA 音訊。
- **待套用的變更**：例如「需重新啟動遊戲」「需重建交換鏈」，以及 MAKO 回報的錯誤。

如果遊戲裝了 Mako FG，卻沒有真正載入 MAKO，也會顯示出來，方便你找出問題。

### 9. 遊戲啟動浮水印

MAKO 助手開著時啟動遊戲，一偵測到 MAKO 已經在遊戲中運作，就會在畫面右下角顯示目前啟用的 MAKO 功能約 10 秒，然後淡出：

- 每次啟動只顯示一次，不會搶走鍵盤滑鼠焦點，滑鼠也能直接點穿。
- 可以疊在全螢幕的 Proton 遊戲上。
- 如果裝了 Mako FG 的遊戲啟動 90 秒後仍未載入 MAKO，會改顯示警告。
- 可以用工具列的「遊戲啟動浮水印」核取方塊關閉。

### 10. 搜尋與篩選

- 可以用遊戲名稱（任何語言的名稱都可以）或 App ID 搜尋。
- 篩選：全部遊戲、已安裝 Mako FG、未安裝 Mako FG、僅保留 MAKO 設定、執行中。

### 11. 12 種介面語言

台灣正體中文、简体中文、English、日本語、Deutsch、Français、Español、Italiano、ไทย、Tiếng Việt、Bahasa Melayu、हिन्दी。

第一次開啟時依系統語言自動選擇，之後可以在右上角切換，立即生效並記住選擇。

### 12. 安全設計

- 修改 `conf.toml` 和 Steam 的 `localconfig.vdf` 前，都會先備份（`*.mako-assistant.bak`）。
- 寫入 `conf.toml` 後，會用 `mako-cli validate` 驗證。MAKO 不接受的話，會自動還原。
- Steam 執行中時，絕不直接修改 `localconfig.vdf`。
- 按「安裝 Mako FG」時，會先確認 MAKO Renderer 已安裝（`~/.local/bin/mako-launch` 存在）且 MAKO UI 已建立設定。任一項不符合，就不會修改任何設定，並提示你先安裝 MAKO。

## 安裝 MAKO 助手

**AppImage（建議）**：已內含 Python 與 Qt，不需另外安裝。

1. 到 [Releases](https://github.com/mosesmoon/mako-assistant/releases) 頁面下載 `MAKO_Assistant-<版本>-x86_64.AppImage`。
2. 設為可執行：對檔案按右鍵 →「內容」→「權限」，勾選「允許作為程式執行」（各檔案管理員的用詞略有不同）。
3. 點兩下即可開啟 MAKO 助手。

也可以在終端機執行：

```bash
chmod +x MAKO_Assistant-*-x86_64.AppImage
./MAKO_Assistant-*-x86_64.AppImage
```

如果無法開啟，可能是系統缺少 FUSE，可改用 `./MAKO_Assistant-*-x86_64.AppImage --appimage-extract-and-run` 執行。

**從原始碼執行**：需要 Python 3.11 以上和 PyQt6（Arch：`sudo pacman -S python-pyqt6`）。

```bash
./mako-assistant    # 直接執行
./install.sh        # 安裝到 ~/.local/share/mako-assistant 並建立應用程式選單項目
```

## 已知限制

- **Steam Deck 遊戲模式（gamescope）不會顯示浮水印**。Steam Deck 上建議使用 MAKO 的 Decky 外掛。
- 以原生 Wayland 獨佔全螢幕執行的遊戲，可能蓋住浮水印。
- 即時套用啟動選項只支援 Decky Loader 開啟的 Steam 用戶端連線埠（8080）。沒有 Decky 時，請關閉 Steam 再套用，或讓工具代為關閉並重開 Steam。
- 「實際啟用功能」和 MAKO 設定中繼資料的格式，是依目前的 MAKO 版本解析的。MAKO 或 Steam 大幅更新後，可能暫時無法顯示（會顯示「—」），但不影響安裝與移除。
- 泰文、越南文、馬來文、印地文的右鍵選單是英文（Qt 沒有這幾種語言的官方翻譯）。Steam 沒有馬來文和印地文的遊戲名稱，這兩種語言一律顯示原文名稱。
- 備份檔只保留最近一份。

## 資料存放位置

| 位置 | 內容 |
|---|---|
| `~/.config/mako-assistant/state.json` | MAKO 助手自己的狀態：遊戲清單快取、透過本工具安裝過的遊戲、介面語言、浮水印開關 |
| `~/.config/mako-render/conf.toml` | MAKO Renderer 設定（各遊戲 profile） |
| `~/.config/mako-render/profile-metadata.json` | MAKO profile 中繼資料（遊戲名稱、Steam App ID） |
| `<Steam>/userdata/<使用者 ID>/config/localconfig.vdf` | Steam 啟動選項 |
