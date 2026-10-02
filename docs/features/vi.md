# Trợ lý MAKO — Giới thiệu tính năng

[English](en.md) · [台灣正體中文](zh_TW.md) · [简体中文](zh_CN.md) · [日本語](ja.md) · [Deutsch](de.md) · [Français](fr.md) · [Español](es.md) · [Italiano](it.md) · [ไทย](th.md) · **Tiếng Việt** · [Bahasa Melayu](ms.md) · [हिन्दी](hi.md)

**Trợ lý MAKO** là công cụ đồ họa cho máy tính Linux, giúp bật hoặc tắt **tạo khung hình của MAKO Renderer (Mako FG)** cho game Steam chỉ bằng một cú nhấp, không cần tự tay sửa bất kỳ tệp cấu hình nào.

## Dành cho ai

Trên Steam Deck ở chế độ Game, MAKO có plugin Decky để chỉnh mọi thứ ngay trong game. Còn trên **máy tính để bàn hoặc laptop Linux thông thường** (ví dụ Arch, Fedora hay Ubuntu với KDE Plasma hoặc GNOME), muốn một game dùng được MAKO thường phải tự làm tất cả những việc sau:

1. Thêm `~/.local/bin/mako-launch %command%` vào tùy chọn khởi chạy Steam của game (Thuộc tính → Tùy chọn khởi chạy) mà không làm hỏng các tùy chọn sẵn có.
2. Tìm tên chương trình mà game **thực sự chạy** (nhiều game mở trình khởi chạy (launcher) trước, còn game Unreal Engine chạy tệp `*-Shipping.exe`).
3. Tạo hồ sơ game trong cấu hình MAKO và điền đúng tiến trình khớp (`active_in`).
4. Làm lại từ đầu khi bản cập nhật game đổi đường dẫn hoặc tên tệp thực thi.
5. Mở game lên rồi mà vẫn không chắc tính năng tạo khung hình có thật sự hoạt động hay không.

Trợ lý MAKO gộp các bước này vào một nút bấm, và khi game đang chạy sẽ cho bạn biết MAKO **thực sự** đang bật những tính năng nào.

## Cần chuẩn bị trước khi dùng

> ⚠ **Trợ lý MAKO không kèm theo MAKO Renderer và cũng không cài nó cho bạn.** Công cụ này chỉ quản lý cấu hình của MAKO.

Hãy tự làm trước những việc sau:

1. **Cài MAKO Renderer (bản standalone)** theo hướng dẫn cài đặt của chính MAKO. Sau khi cài, phải có tệp `~/.local/bin/mako-launch`.
2. **Mở MAKO UI một lần** để tạo cấu hình mặc định. Bước này tạo `~/.config/mako-render/conf.toml` và hồ sơ mặc định `mako`. Mọi hồ sơ game mà Trợ lý MAKO tạo đều được sao chép từ hồ sơ mặc định này.
3. **Cài Steam.** Hỗ trợ bản gốc (`~/.local/share/Steam`, `~/.steam`) cùng các bản Flatpak và Snap.

Hãy chắc chắn đã làm xong tất cả các bước trên và MAKO hoạt động bình thường rồi mới dùng Trợ lý MAKO để cài Mako FG cho game.

Tùy chọn: **Decky Loader**. Khi đã cài, tùy chọn khởi chạy có thể được áp dụng ngay trong lúc Steam đang chạy mà không cần đóng Steam (xem "Cách ghi tùy chọn khởi chạy" bên dưới).

## Tính năng

### 1. Tự động quét thư viện Steam

- Lần mở đầu tiên sẽ quét **toàn bộ** thư viện Steam (kể cả thư viện trên ổ đĩa khác). Sau đó bạn có thể bấm "⟳ Quét lại danh sách game Steam".
- Các công cụ như Proton và Steam Linux Runtime được lọc bỏ, chỉ hiển thị game.
- Tên game hiển thị theo tên bản địa hóa chính thức của Steam trong ngôn ngữ giao diện và được sắp xếp theo thói quen của ngôn ngữ đó.
- Mỗi game hiển thị ảnh bìa, tùy chọn khởi chạy hiện tại, hồ sơ MAKO và đường dẫn tệp thực thi được phát hiện.

### 2. "Cài Mako FG" chỉ với một cú nhấp

Khi bạn bấm "Cài Mako FG", công cụ sẽ:

- **Thêm tùy chọn khởi chạy** `~/.local/bin/mako-launch %command%` vào tùy chọn khởi chạy Steam của game và **giữ nguyên các thiết lập cũ**. Ví dụ `FOO=1 %command% -dx11` sẽ thành `FOO=1 ~/.local/bin/mako-launch %command% -dx11`.
- **Phát hiện đúng tệp thực thi của game** dựa trên thông tin ứng dụng của Steam. Công cụ xử lý được trình khởi chạy (khi đó sẽ tìm chương trình game thật trong thư mục cài đặt) và tệp `*-Shipping.exe` của Unreal Engine, đồng thời bỏ qua các chương trình phụ trợ thường gặp.
- **Tạo hồ sơ game của MAKO**: sao chép hồ sơ mặc định `mako` thành hồ sơ riêng của game trong `conf.toml` và ghi siêu dữ liệu hồ sơ của MAKO. **Cả MAKO UI lẫn plugin Decky đều thấy và có thể sửa trực tiếp hồ sơ này.**
- **Tránh khớp trùng**: nếu hồ sơ mặc định `mako` cũng khớp với tệp thực thi của game này, tệp đó sẽ được gỡ khỏi `mako` để game chỉ dùng hồ sơ riêng của nó. Nếu hồ sơ của một game khác cũng khớp với cùng tệp thực thi, bạn sẽ nhận được cảnh báo nhưng không có gì bị tự động thay đổi.

### 3. Cách ghi tùy chọn khởi chạy

Steam chỉ đọc tùy chọn khởi chạy khi khởi động và ghi đè tệp cấu hình khi thoát. Để Steam không ghi đè thay đổi của bạn, Trợ lý MAKO tự chọn cách ghi theo trạng thái của Steam và hiển thị trạng thái đó trên cửa sổ:

| Trạng thái Steam | Cách ghi |
|---|---|
| Không chạy | Sửa trực tiếp tệp `localconfig.vdf` của Steam (sau khi sao lưu) |
| Đang chạy và kết nối được với ứng dụng Steam (cần Decky Loader) | Áp dụng ngay qua ứng dụng Steam, không cần khởi động lại Steam |
| Đang chạy nhưng không kết nối được | Hỏi bạn có muốn đóng Steam không → áp dụng thay đổi → tự mở lại Steam |

### 4. Gỡ bỏ

- "Gỡ bỏ" chỉ xóa `mako-launch` khỏi tùy chọn khởi chạy, các tùy chọn khác giữ nguyên.
- Cấu hình MAKO của game **được giữ lại theo mặc định** để có thể dùng lại nếu bạn cài lại sau này. Đánh dấu "Đồng thời xóa cấu hình game trong MAKO Renderer" nếu muốn xóa luôn.

### 5. Nhập cấu hình có sẵn

Nếu trước đây bạn đã tự thêm `mako-launch` cho một game, game đó sẽ có nút "Nhập cấu hình". Khi bấm, công cụ sẽ tạo hồ sơ MAKO cho game và đưa game vào danh sách tự động cập nhật đường dẫn từ đó về sau.

### 6. Tự động cập nhật đường dẫn sau khi game cập nhật

- Mỗi lần quét lại, công cụ sẽ phát hiện lại tệp thực thi của các game **đã cài qua công cụ này**. Nếu bản cập nhật đã di chuyển hoặc đổi tên tệp thực thi, tiến trình khớp trong MAKO sẽ được cập nhật tự động và thay đổi được ghi trong khu vực nhật ký.
- Các tiến trình khớp bạn **tự thêm** trong MAKO UI sẽ được giữ lại.
- Nếu bạn đã xóa hồ sơ của một game trong MAKO UI, công cụ tôn trọng quyết định đó và không tạo lại.
- Nếu một thư viện tạm thời ngoại tuyến (ví dụ ổ cứng ngoài chưa cắm), cấu hình của các game đó được giữ nguyên.

### 7. Mở game ngay từ danh sách

Mỗi dòng có nút "▶ Chơi" để mở game qua Steam. Khi game đang chạy, nút sẽ hiển thị "Đang chạy".

### 8. Hiển thị theo thời gian thực các tính năng MAKO đang thực sự dùng

Cột "Tính năng MAKO đang hoạt động" cập nhật mỗi 3 giây. Cột này cho thấy MAKO **thực sự áp dụng** gì trong game, chứ không phải tệp cấu hình ghi gì:

- **Tạo khung hình**: hệ số cố định (ví dụ ×2) hoặc chế độ thích ứng (FPS mục tiêu và hệ số tối đa), tỉ lệ Flow, chế độ hiệu năng.
- **Co giãn hình ảnh**: phương pháp và độ phân giải (ví dụ 1280×720 → 2560×1440), siêu lấy mẫu (supersampling).
- **Các lớp khác**: vkBasalt, Zink, âm thanh ALSA.
- **Thay đổi đang chờ áp dụng**, như "cần khởi động lại game" hoặc "cần tạo lại swapchain", cùng các lỗi MAKO báo về.

Nếu game đã cài Mako FG nhưng MAKO không thực sự được nạp, điều đó cũng được hiển thị để bạn dễ tìm ra nguyên nhân.

### 9. Lớp phủ khi mở game

Nếu Trợ lý MAKO đang mở khi bạn khởi động game, ngay khi phát hiện MAKO đã hoạt động trong game, công cụ sẽ hiển thị các tính năng MAKO đang bật ở góc dưới bên phải màn hình khoảng 10 giây rồi mờ dần:

- Chỉ hiện một lần mỗi lần mở game, không chiếm tiêu điểm bàn phím hay chuột, và cú nhấp chuột đi xuyên qua.
- Có thể hiện đè lên game Proton toàn màn hình.
- Nếu một game đã cài Mako FG vẫn chưa nạp MAKO sau 90 giây kể từ khi mở, sẽ hiện cảnh báo thay thế.
- Có thể tắt bằng ô "Lớp phủ khi mở game" trên thanh công cụ.

### 10. Tìm kiếm và bộ lọc

- Tìm theo tên game (bằng bất kỳ ngôn ngữ nào) hoặc theo App ID.
- Bộ lọc: tất cả game, đã cài Mako FG, chưa cài Mako FG, chỉ còn cấu hình MAKO, đang chạy.

### 11. 12 ngôn ngữ giao diện

台灣正體中文, 简体中文, English, 日本語, Deutsch, Français, Español, Italiano, ไทย, Tiếng Việt, Bahasa Melayu, हिन्दी.

Lần mở đầu tiên, ngôn ngữ được chọn theo ngôn ngữ hệ thống. Bạn có thể đổi bất cứ lúc nào ở góc trên bên phải; thay đổi có hiệu lực ngay và được ghi nhớ.

### 12. Thiết kế an toàn

- `conf.toml` và `localconfig.vdf` của Steam luôn được sao lưu (`*.mako-assistant.bak`) trước mỗi lần thay đổi.
- Sau khi ghi `conf.toml`, công cụ kiểm tra bằng `mako-cli validate`. Nếu MAKO không chấp nhận, tệp gốc sẽ được tự động khôi phục.
- Không bao giờ sửa trực tiếp `localconfig.vdf` khi Steam đang chạy.

## Cài đặt Trợ lý MAKO

**AppImage (khuyên dùng)**: đã có sẵn Python và Qt, không cần cài thêm gì.

```bash
chmod +x MAKO_Assistant-*-x86_64.AppImage
./MAKO_Assistant-*-x86_64.AppImage
```

**Chạy từ mã nguồn**: cần Python 3.11 trở lên và PyQt6 (Arch: `sudo pacman -S python-pyqt6`).

```bash
./mako-assistant    # chạy trực tiếp
./install.sh        # cài vào ~/.local/share/mako-assistant và thêm mục vào menu ứng dụng
```

## Hạn chế đã biết

- **Lớp phủ không hiển thị trong chế độ Game của Steam Deck (gamescope).** Trên Steam Deck, hãy dùng plugin Decky của MAKO.
- Game chạy toàn màn hình độc quyền trên Wayland gốc có thể che mất lớp phủ.
- Chỉ có thể đổi tùy chọn khởi chạy ngay lập tức qua cổng ứng dụng Steam do Decky Loader mở (8080). Nếu không có Decky, hãy đóng Steam trước khi áp dụng, hoặc để công cụ tự đóng và mở lại Steam.
- Phần hiển thị tính năng đang thực sự dùng và siêu dữ liệu hồ sơ MAKO được đọc theo định dạng của phiên bản MAKO hiện tại. Sau một bản cập nhật lớn của MAKO hoặc Steam, chúng có thể tạm thời không hiển thị (bạn sẽ thấy "—"), nhưng việc cài và gỡ vẫn hoạt động bình thường.
- Với tiếng Thái, tiếng Việt, tiếng Mã Lai và tiếng Hindi, menu chuột phải là tiếng Anh (Qt không có bản dịch chính thức cho các ngôn ngữ này). Steam không có tên game bằng tiếng Mã Lai và tiếng Hindi, nên hai ngôn ngữ này luôn hiển thị tên gốc.
- Chỉ giữ lại bản sao lưu gần nhất.

## Nơi lưu dữ liệu

| Vị trí | Nội dung |
|---|---|
| `~/.config/mako-assistant/state.json` | Trạng thái riêng của Trợ lý MAKO: bộ nhớ đệm danh sách game, các game đã cài qua công cụ này, ngôn ngữ giao diện, thiết lập lớp phủ |
| `~/.config/mako-render/conf.toml` | Cấu hình MAKO Renderer (hồ sơ của từng game) |
| `~/.config/mako-render/profile-metadata.json` | Siêu dữ liệu hồ sơ MAKO (tên game, Steam App ID) |
| `<Steam>/userdata/<ID người dùng>/config/localconfig.vdf` | Tùy chọn khởi chạy Steam |
