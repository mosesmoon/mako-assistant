# Pembantu MAKO — Pengenalan Ciri

[English](en.md) · [台灣正體中文](zh_TW.md) · [简体中文](zh_CN.md) · [日本語](ja.md) · [Deutsch](de.md) · [Français](fr.md) · [Español](es.md) · [Italiano](it.md) · [ไทย](th.md) · [Tiếng Việt](vi.md) · **Bahasa Melayu** · [हिन्दी](hi.md)

**Pembantu MAKO** ialah alat grafik untuk desktop Linux yang menghidupkan atau mematikan **penjanaan bingkai MAKO Renderer (Mako FG)** bagi permainan Steam anda dengan satu klik, tanpa perlu menyunting sebarang fail konfigurasi sendiri.

## Untuk siapa

Pada Steam Deck dalam mod Permainan, MAKO mempunyai pemalam Decky yang membolehkan anda menetapkan semuanya semasa bermain. Tetapi pada **PC desktop atau komputer riba Linux biasa** (contohnya Arch, Fedora atau Ubuntu dengan KDE Plasma atau GNOME), untuk membolehkan sesuatu permainan menggunakan MAKO, anda biasanya perlu melakukan semua ini sendiri:

1. Menambah `~/.local/bin/mako-launch %command%` pada pilihan pelancaran Steam permainan itu (Sifat → Pilihan Pelancaran) tanpa merosakkan pilihan yang sedia ada.
2. Mencari nama program yang **sebenarnya dijalankan** oleh permainan (banyak permainan membuka pelancar dahulu, dan permainan Unreal Engine menjalankan `*-Shipping.exe`).
3. Mencipta profil permainan dalam tetapan MAKO dan mengisi proses dipadankan (`active_in`) yang betul.
4. Mengulang semuanya apabila kemas kini permainan mengubah laluan atau nama fail boleh laku.
5. Selepas permainan dibuka, anda masih tidak pasti sama ada penjanaan bingkai benar-benar berfungsi.

Pembantu MAKO menggabungkan langkah-langkah ini ke dalam satu butang, dan semasa permainan berjalan ia menunjukkan ciri MAKO yang **benar-benar** aktif.

## Persediaan sebelum digunakan

> ⚠ **Pembantu MAKO tidak termasuk MAKO Renderer dan tidak akan memasangnya untuk anda.** Ia hanya mengurus tetapan MAKO.

Lakukan perkara berikut dahulu:

1. **Pasang MAKO Renderer (versi standalone)** mengikut arahan pemasangan MAKO sendiri. Selepas dipasang, fail `~/.local/bin/mako-launch` sepatutnya wujud.
2. **Buka MAKO UI sekali** untuk mencipta tetapan lalai. Langkah ini mencipta `~/.config/mako-render/conf.toml` dan profil lalai `mako`. Setiap profil permainan yang dicipta oleh Pembantu MAKO ialah salinan profil lalai ini.
3. **Pasang Steam.** Pakej asli (`~/.local/share/Steam`, `~/.steam`) serta versi Flatpak dan Snap disokong.

Pastikan semua langkah di atas telah selesai dan MAKO sendiri berfungsi sebelum anda menggunakan Pembantu MAKO untuk memasang Mako FG bagi sesuatu permainan.

Pilihan: **Decky Loader**. Dengan Decky Loader, pilihan pelancaran boleh digunakan serta-merta semasa Steam sedang berjalan, tanpa menutup Steam (lihat "Cara pilihan pelancaran ditulis" di bawah).

## Ciri-ciri

### 1. Imbasan automatik pustaka Steam

- Kali pertama dibuka, ia mengimbas **semua** pustaka Steam anda (termasuk pustaka pada pemacu lain). Selepas itu anda boleh klik "⟳ Imbas semula permainan Steam".
- Alat seperti Proton dan Steam Linux Runtime ditapis keluar, jadi hanya permainan disenaraikan.
- Nama permainan dipaparkan mengikut nama tempatan rasmi Steam dalam bahasa antara muka dan disusun mengikut kebiasaan bahasa itu. (Steam tiada nama permainan dalam Bahasa Melayu, jadi nama asal dipaparkan.)
- Setiap permainan memaparkan gambar muka depan, pilihan pelancaran semasa, profil MAKO dan laluan fail boleh laku yang dikesan.

### 2. "Pasang Mako FG" dengan satu klik

Apabila anda klik "Pasang Mako FG", alat ini akan:

- **Menambah pilihan pelancaran** `~/.local/bin/mako-launch %command%` pada pilihan pelancaran Steam permainan dan **mengekalkan tetapan sedia ada**. Contohnya, `FOO=1 %command% -dx11` menjadi `FOO=1 ~/.local/bin/mako-launch %command% -dx11`.
- **Mengesan fail boleh laku permainan yang sebenar** berdasarkan maklumat aplikasi Steam. Ia mengendalikan pelancar (dengan mencari program permainan sebenar dalam folder pemasangan) dan `*-Shipping.exe` Unreal Engine, serta melangkau program pembantu yang biasa.
- **Mencipta profil permainan MAKO**: menyalin profil lalai `mako` menjadi profil khas permainan itu dalam `conf.toml` dan menulis metadata profil MAKO. **MAKO UI dan pemalam Decky kedua-duanya dapat melihat dan menyunting profil ini secara terus.**
- **Mengelakkan padanan berganda**: jika profil lalai `mako` juga memadankan fail boleh laku permainan ini, fail itu dibuang daripada `mako` supaya permainan hanya menggunakan profilnya sendiri. Jika profil permainan lain memadankan fail boleh laku yang sama, anda akan diberi amaran, tetapi tiada apa-apa yang diubah secara automatik.

### 3. Cara pilihan pelancaran ditulis

Steam hanya membaca pilihan pelancaran semasa ia bermula dan menulis ganti fail konfigurasinya semasa ditutup. Supaya perubahan anda tidak ditulis ganti oleh Steam, Pembantu MAKO memilih cara menulis berdasarkan keadaan Steam dan memaparkan keadaan itu dalam tetingkap:

| Keadaan Steam | Cara menulis |
|---|---|
| Tidak berjalan | Menyunting `localconfig.vdf` Steam secara terus (selepas membuat sandaran) |
| Sedang berjalan dan klien Steam boleh dihubungi (perlu Decky Loader) | Menggunakan perubahan serta-merta melalui klien Steam, tanpa memulakan semula Steam |
| Sedang berjalan tetapi klien tidak boleh dihubungi | Bertanya sama ada mahu menutup Steam → menggunakan perubahan → membuka semula Steam |

### 4. Buang

- "Buang" hanya mengeluarkan `mako-launch` daripada pilihan pelancaran; pilihan lain kekal seperti asal.
- Tetapan MAKO permainan itu **dikekalkan secara lalai** supaya boleh digunakan semula jika anda memasangnya semula kemudian. Tandakan "Buang juga tetapan permainan dalam MAKO Renderer" untuk memadamkannya sekali.

### 5. Import tetapan sedia ada

Jika anda pernah menambah `mako-launch` pada sesuatu permainan secara manual, permainan itu akan memaparkan butang "Import tetapan". Apabila diklik, alat ini mencipta profil MAKO untuk permainan itu dan memasukkannya dalam kemas kini laluan automatik selepas itu.

### 6. Kemas kini laluan automatik selepas permainan dikemas kini

- Setiap kali imbasan semula, alat ini mengesan semula fail boleh laku bagi permainan yang **dipasang melalui alat ini**. Jika kemas kini permainan memindahkan atau menamakan semula fail boleh laku, proses dipadankan MAKO dikemas kini secara automatik dan perubahan itu disenaraikan dalam ruang log.
- Proses dipadankan yang anda **tambah secara manual** dalam MAKO UI dikekalkan.
- Jika anda memadamkan profil sesuatu permainan dalam MAKO UI, alat ini menghormati keputusan itu dan tidak menciptanya semula.
- Jika pustaka berada di luar talian buat sementara waktu (contohnya pemacu luaran tidak disambungkan), tetapan permainan tersebut tidak diubah.

### 7. Lancarkan permainan terus dari senarai

Setiap baris mempunyai butang "▶ Main" yang melancarkan permainan melalui Steam. Semasa permainan berjalan, butang itu memaparkan "Sedang berjalan".

### 8. Paparan masa nyata ciri MAKO yang benar-benar digunakan

Lajur "Ciri MAKO yang aktif" dikemas kini setiap 3 saat. Lajur ini menunjukkan apa yang **benar-benar digunakan** oleh MAKO dalam permainan, bukan apa yang tertulis dalam fail konfigurasi:

- **Penjanaan bingkai**: pendarab tetap (contohnya ×2) atau mod adaptif (FPS sasaran dan pendarab maksimum), skala Flow dan mod prestasi.
- **Penskalaan**: kaedah penskalaan dan resolusi (contohnya 1280×720 → 2560×1440), serta supersampling.
- **Lapisan lain**: vkBasalt, Zink, audio ALSA.
- **Perubahan yang belum digunakan**, seperti "perlu mulakan semula permainan" atau "perlu bina semula swapchain", serta ralat yang dilaporkan oleh MAKO.

Jika sesuatu permainan sudah dipasang Mako FG tetapi MAKO tidak benar-benar dimuatkan, perkara itu juga dipaparkan supaya anda mudah mengesan punca masalah.

### 9. Tindanan semasa permainan bermula

Jika Pembantu MAKO sedang dibuka semasa anda melancarkan permainan, sebaik sahaja ia mengesan MAKO berfungsi dalam permainan, ia memaparkan ciri MAKO yang aktif di sudut kanan bawah skrin selama kira-kira 10 saat, kemudian pudar:

- Ia muncul sekali bagi setiap pelancaran, tidak mengambil fokus papan kekunci atau tetikus, dan klik tetikus menembusinya.
- Ia boleh muncul di atas permainan Proton skrin penuh.
- Jika permainan yang dipasang Mako FG masih belum memuatkan MAKO 90 saat selepas dilancarkan, amaran akan dipaparkan sebagai ganti.
- Anda boleh mematikannya dengan kotak semak "Tindanan semasa permainan bermula" pada bar alat.

### 10. Carian dan penapis

- Cari mengikut nama permainan (dalam apa-apa bahasa) atau App ID.
- Penapis: semua permainan, Mako FG dipasang, Mako FG belum dipasang, tetapan MAKO sahaja, sedang berjalan.

### 11. Dua belas bahasa antara muka

台灣正體中文, 简体中文, English, 日本語, Deutsch, Français, Español, Italiano, ไทย, Tiếng Việt, Bahasa Melayu, हिन्दी.

Kali pertama dibuka, bahasa mengikut bahasa sistem. Anda boleh menukarnya pada bila-bila masa di penjuru kanan atas; perubahan berkuat kuasa serta-merta dan diingati.

### 12. Direka untuk keselamatan

- `conf.toml` dan `localconfig.vdf` Steam disandarkan (`*.mako-assistant.bak`) sebelum setiap perubahan.
- Selepas menulis `conf.toml`, alat ini menyemaknya dengan `mako-cli validate`. Jika MAKO menolaknya, fail asal dipulihkan secara automatik.
- `localconfig.vdf` tidak pernah disunting secara terus semasa Steam sedang berjalan.

## Memasang Pembantu MAKO

**AppImage (disyorkan)**: Python dan Qt sudah disertakan, tiada apa-apa lagi yang perlu dipasang.

```bash
chmod +x MAKO_Assistant-*-x86_64.AppImage
./MAKO_Assistant-*-x86_64.AppImage
```

**Daripada kod sumber**: memerlukan Python 3.11 atau lebih baharu dan PyQt6 (Arch: `sudo pacman -S python-pyqt6`).

```bash
./mako-assistant    # jalankan terus
./install.sh        # pasang ke ~/.local/share/mako-assistant dan tambah entri dalam menu aplikasi
```

## Had yang diketahui

- **Tindanan tidak dipaparkan dalam mod Permainan Steam Deck (gamescope).** Pada Steam Deck, gunakan pemalam Decky MAKO.
- Permainan yang berjalan dalam skrin penuh eksklusif pada Wayland asli mungkin menutup tindanan.
- Pilihan pelancaran hanya boleh diubah serta-merta melalui port klien Steam yang dibuka oleh Decky Loader (8080). Tanpa Decky, tutup Steam sebelum menggunakan perubahan, atau biarkan alat ini menutup dan membuka semula Steam.
- Paparan ciri yang benar-benar digunakan dan metadata profil MAKO dibaca mengikut format versi MAKO semasa. Selepas kemas kini besar MAKO atau Steam, ia mungkin tidak dipaparkan buat sementara waktu (anda akan nampak "—"), tetapi pemasangan dan pembuangan tetap berfungsi.
- Dalam bahasa Thai, Vietnam, Melayu dan Hindi, menu klik kanan adalah dalam bahasa Inggeris (Qt tiada terjemahan rasmi untuk bahasa-bahasa ini). Steam tiada nama permainan dalam Bahasa Melayu dan Hindi, jadi kedua-dua bahasa ini sentiasa memaparkan nama asal.
- Hanya sandaran terkini disimpan.

## Lokasi data disimpan

| Lokasi | Kandungan |
|---|---|
| `~/.config/mako-assistant/state.json` | Keadaan Pembantu MAKO sendiri: cache senarai permainan, permainan yang dipasang melalui alat ini, bahasa antara muka, tetapan tindanan |
| `~/.config/mako-render/conf.toml` | Tetapan MAKO Renderer (profil setiap permainan) |
| `~/.config/mako-render/profile-metadata.json` | Metadata profil MAKO (nama permainan, Steam App ID) |
| `<Steam>/userdata/<ID pengguna>/config/localconfig.vdf` | Pilihan pelancaran Steam |
