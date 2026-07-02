# Issue: On-Premise Indonesian VoIP Hotline Voice Agent for Hospital

## Ringkasan

Ini adalah POC on-premise untuk voice agent hotline rumah sakit yang memproses percakapan bahasa Indonesia secara streaming, dengan prioritas utama pada jalur ASR yang di-chunking hingga menghasilkan TTS dengan latensi serendah mungkin.

Seluruh pemrosesan data harus tetap berada di jaringan internal rumah sakit. Tidak boleh ada audio, transkrip, prompt, metadata percakapan, atau output model yang keluar ke layanan cloud atau third-party SaaS.

Target alur utama:

1. Pasien menelepon nomor hotline via VoIP.
2. Sistem memutar greeting awal yang sifatnya statis, sebaiknya dari aset rekaman lokal.
3. Percakapan live dimulai.
4. Audio pasien diproses secara streaming dan di-chunk.
5. ASR mengubah audio menjadi teks bahasa Indonesia.
6. Teks bahasa Indonesia diterjemahkan ke bahasa yang paling optimal untuk LLM.
7. LLM menghasilkan jawaban.
8. Jawaban diterjemahkan kembali ke bahasa Indonesia jika diperlukan.
9. TTS menghasilkan audio respons bahasa Indonesia secara on-premise.
10. Audio respons diputar kembali ke penelepon.

## Tujuan Implementasi

Tujuan issue ini adalah menyiapkan pondasi teknis dan arsitektur POC yang bisa diimplementasikan bertahap oleh junior engineer tanpa perlu menebak-nebak alur sistem.

Fokus utama:

- arsitektur streaming yang benar untuk voice agent,
- jalur ASR chunking sampai TTS sebagai prioritas implementasi,
- pemisahan jelas antara telephony, ASR, translation, LLM, dan TTS,
- semua komponen berjalan di on-premise,
- repository workflow yang mendukung mode kerja senior engineer -> issue.md -> junior engineer -> pull request -> review -> iterasi.

## Constraint Utama

- Semua data harus diproses on-premise.
- Tidak boleh ada telemetri cloud yang membawa isi percakapan.
- Latensi harus rendah, sehingga pipeline harus streaming, bukan tunggu utterance selesai penuh.
- Input awal pada fase POC boleh berasal dari mikrofon untuk mempercepat validasi end-to-end sebelum sepenuhnya dihubungkan ke VoIP.
- Bahasa percakapan utama adalah bahasa Indonesia.
- Sistem harus aman untuk konteks rumah sakit.
- Greeting awal boleh memakai rekaman statis jika memang tidak perlu dinamis.
- Implementasi harus siap untuk review bertahap dan PR kecil.

## Rekomendasi Arsitektur Tingkat Tinggi

### 1. Telephony layer

Gunakan gateway VoIP yang bisa menghubungkan panggilan masuk ke aplikasi voice agent secara realtime. Layer ini bertugas menangani:

- inbound call,
- media stream audio,
- bridging ke worker aplikasi,
- kontrol call lifecycle,
- audio playback ke penelepon.

### 2. Realtime audio pipeline

Pakai pola event-driven dan streaming pipeline agar audio bisa diproses per chunk.

Karakteristik yang diinginkan:

- audio masuk sebagai frame kecil,
- chunk diarahkan ke ASR secara incremental,
- partial transcript bisa dipakai untuk memulai reasoning lebih cepat,
- respons LLM dapat di-streaming sebelum seluruh jawaban final selesai,
- TTS bisa menyiapkan output per segmen.

Untuk POC, input audio boleh berasal dari mikrofon lokal sebelum integrasi penuh ke alur VoIP.

### 3. ASR

Model kandidat:

- faster-whisper-large-v3-turbo-ct2

Tugas ASR:

- menerima chunk audio,
- menghasilkan partial dan final transcript,
- mendukung bahasa Indonesia,
- menandai endpoint utterance bila ada jeda bicara.

### 4. Translation

Karena model LLM yang dipilih belum tentu optimal untuk bahasa Indonesia, buat layer translation terpisah.

Model kandidat:

- facebook/nllb-200-distilled-600M,
- tencent/Hy-MT2-1.8B.

Tugas translation:

- ID -> target language untuk LLM,
- target language -> ID untuk respons akhir,
- menjaga arti medis tetap konsisten,
- tidak mengubah istilah klinis penting secara sembarangan.

### 5. LLM serving

Model kandidat:

- NVIDIA/NVIDIA-Nemotron-3-Super-120B-A12B-BF16.

Tugas LLM:

- menerima context percakapan,
- menghasilkan jawaban berbasis instruksi dan konteks rumah sakit,
- mendukung streaming token output,
- dijalankan sepenuhnya di infrastruktur internal.

Catatan penting:

- junior engineer harus memverifikasi kelayakan hardware, VRAM, dan throughput model ini,
- jika hardware tidak cukup, issue implementasi harus mencatat opsi fallback tanpa mengubah prinsip on-prem.

### 6. TTS

Model kandidat:

- Eempostor/F5-TTS-INDO-FINETUNE-V2.

Tugas TTS:

- mengubah teks respons ke audio bahasa Indonesia,
- berjalan lokal,
- mendukung karakter suara yang jelas untuk penggunaan hotline,
- dapat memakai rekaman static greeting untuk sapaan awal.

## Integrasi dengan LiveKit Agents

Gunakan LiveKit Agents sebagai framework orchestration untuk voice agent karena cocok untuk realtime media handling dan event-driven workflow.

Junior engineer perlu memeriksa:

- bagaimana LiveKit Agents menangani audio in/out,
- bagaimana hook untuk ASR partial result,
- bagaimana streaming response dari LLM masuk ke TTS,
- bagaimana lifecycle call dan turn-taking diatur.

Jika ada bagian yang tidak cocok dengan target on-prem atau dengan transport internal, dokumentasikan secara eksplisit di issue turunan.

## Desain Alur Percakapan

### Fase 1: Greeting awal

- Saat call terhubung, putar greeting statis.
- Gunakan file audio lokal agar murah, cepat, dan konsisten.
- Greeting tetap harus disimpan dan di-serve on-premise.

### Fase 2: Input pasien

- Setelah greeting selesai, aktifkan mode listen.
- Audio masuk di-chunk per frame kecil.
- Jalankan VAD atau mekanisme deteksi jeda jika diperlukan agar utterance tidak menunggu terlalu lama.

### Fase 3: ASR streaming

- Kirim chunk ke ASR worker.
- Keluarkan partial transcript secepat mungkin.
- Simpan final transcript per turn.

### Fase 4: Translation to LLM language

- Terjemahkan transcript Indonesia ke bahasa target LLM.
- Simpan juga versi asli bahasa Indonesia untuk audit internal dan debugging.

### Fase 5: LLM inference

- Susun prompt sistem yang menempatkan LLM sebagai asisten hotline rumah sakit.
- Tambahkan guardrail untuk tidak memberikan instruksi medis berisiko tinggi tanpa eskalasi yang tepat.
- Stream output token jika stack mendukung.

### Fase 6: Translation back to Indonesian

- Terjemahkan output LLM ke bahasa Indonesia yang natural.
- Jaga tone tetap sopan, profesional, dan mudah dipahami.

### Fase 7: TTS

- Generate audio respons.
- Jika TTS mendukung streaming, gunakan segmentasi agar respons tidak menunggu teks final terlalu lama.
- Jika tidak, gunakan strategi chunked synthesis per kalimat.

## Non-Functional Requirements

- Latensi end-to-end harus serendah mungkin untuk percakapan natural.
- Sistem harus dapat dipantau secara lokal.
- Log harus aman dan dibatasi untuk kebutuhan operasional.
- Sensitif data pasien tidak boleh dipindahkan ke layanan eksternal.
- Pipeline harus mudah di-debug per komponen.
- Implementasi harus modular agar model bisa diganti tanpa rewrite total.

## Security dan Kepatuhan

Hal yang wajib diperhatikan pada implementasi:

- semua dependency model dan artifact harus disimpan lokal,
- tidak ada outbound request yang mengirim audio/transkrip ke luar,
- log harus disanitasi,
- cache model harus berada di storage internal,
- prompt dan history percakapan harus diperlakukan sebagai data sensitif,
- akses ke worker internal harus dibatasi.

## Breakdown Implementasi Bertahap

### Phase 0: Discovery dan baseline

- Konfirmasi target stack repo dan cara run lokal/on-prem.
- Identifikasi komponen telephony yang akan dipakai.
- Identifikasi kebutuhan hardware minimal untuk ASR, translation, LLM, dan TTS.
- Tetapkan boundary mana yang harus streaming dan mana yang boleh batch.
- Tentukan input awal POC, dengan mikrofon sebagai jalur validasi paling cepat untuk membuktikan alur ASR -> TTS.

### Phase 1: Skeleton project

- Buat struktur project dasar.
- Tambahkan konfigurasi environment.
- Tambahkan abstraction layer untuk audio pipeline.
- Siapkan interface untuk ASR, translation, LLM, dan TTS.

### Phase 2: Voice pipeline MVP

- Hubungkan incoming audio ke ASR streaming.
- Tampilkan partial transcript.
- Hubungkan transcript ke stub LLM.
- Kembalikan audio respons sederhana.

### Phase 3: Model integration

- Integrasikan faster-whisper.
- Integrasikan translation model pilihan.
- Integrasikan LLM on-prem.
- Integrasikan TTS on-prem.

### Phase 4: Turn-taking and streaming optimization

- Tambahkan chunking strategy yang lebih baik.
- Tambahkan VAD atau endpointing.
- Optimalkan token streaming dan audio playback.
- Kurangi delay antar komponen.

### Phase 5: Safety and hospital workflow

- Tambahkan prompt system untuk konteks rumah sakit.
- Tambahkan eskalasi ke operator manusia jika diperlukan.
- Tambahkan guardrail untuk pertanyaan sensitif.
- Tambahkan audit trail lokal.

### Phase 6: Hardening

- Tambahkan observability lokal.
- Tambahkan retry dan timeout per komponen.
- Tambahkan fallback bila model gagal memproses.
- Uji beban dan latensi.

## Definition of Done

Issue ini dianggap selesai jika:

- ada pipeline VoIP inbound ke voice agent yang berjalan on-premise,
- greeting awal dapat diputar,
- ASR streaming bekerja untuk bahasa Indonesia,
- translation layer tersedia,
- LLM on-prem terhubung,
- TTS on-prem menghasilkan respons audio,
- tidak ada data percakapan keluar dari jaringan rumah sakit,
- implementasi dapat direview dalam PR kecil,
- semua langkah implementasi terdokumentasi jelas untuk iterasi berikutnya.

## Deliverable Untuk Junior Engineer

Junior engineer harus menghasilkan:

- perubahan codebase yang sesuai dengan issue ini,
- dokumentasi konfigurasi runtime,
- catatan asumsi hardware dan model,
- catatan bagian yang masih dummy atau stub,
- pull request terpisah untuk review.

## Catatan Implementasi Penting

- Jangan implementasikan semua komponen sekaligus dalam satu PR besar.
- Utamakan interface dan skeleton dulu sebelum optimisasi model.
- Jangan menulis dependency ke layanan cloud.
- Jika sebuah model terlalu berat untuk hardware saat ini, dokumentasikan gap-nya dan siapkan fallback yang tetap on-prem.
- Jika ada keputusan arsitektur yang belum pasti, buat catatan eksplisit di issue turunan agar review lebih mudah.

## Implementation Plan Untuk Iterasi Berikutnya

Rencana ini dipakai sebagai urutan kerja untuk implementasi berikutnya agar setiap perubahan tetap kecil, mudah direview, dan tetap sesuai scope POC.

### Step 1: Kunci baseline POC

- Pertahankan pipeline minimal yang sudah ada sebagai baseline runnable.
- Pastikan input sederhana bisa masuk ke pipeline tanpa bergantung pada VoIP.
- Jadikan alur text-in -> chunking -> ASR mock -> translation mock -> LLM mock -> TTS mock sebagai patokan awal.

### Step 2: Tambah input mikrofon lokal

- Buat jalur input dari mikrofon sebagai sumber audio POC.
- Chunk audio masuk secara kecil dan berulang.
- Simpan jalur ini tetap lokal dan tidak bergantung pada layanan eksternal.

### Step 3: Ganti mock dengan adapter nyata secara bertahap

- Buat interface tipis untuk ASR, translation, LLM, dan TTS.
- Ganti mock satu per satu, dimulai dari ASR karena itu jalur utama POC.
- Pertahankan fallback mock agar pipeline tetap bisa dijalankan saat model nyata belum siap.

### Step 4: Validasi streaming dan turn-taking

- Pastikan partial transcript keluar sebelum utterance selesai penuh.
- Tambahkan endpointing atau VAD hanya jika memang diperlukan untuk mengurangi latensi.
- Jaga agar respons TTS bisa dimulai sesegera mungkin setelah teks cukup stabil.

### Step 5: Siapkan integrasi VoIP terakhir

- Setelah alur mikrofon stabil, sambungkan ke transport VoIP.
- Jangan ubah logika inti pipeline; hanya ganti source audio dan sink audio.
- Simpan greeting statis sebagai aset lokal.

### Step 6: Tambahkan validasi minimal di setiap perubahan

- Setiap PR harus punya satu check runnable yang membuktikan alur yang disentuh masih bekerja.
- Jika perubahan hanya menambah satu bagian kecil, cukup satu test sederhana atau demo script.
- Hindari menambah framework testing atau struktur baru bila belum diperlukan.

### Step 7: Dokumentasikan gap hardware dan model

- Jika model target terlalu berat untuk mesin lokal, catat gap-nya di issue turunan.
- Simpan semua keputusan penting di issue agar review berikutnya tidak mengulang analisis yang sama.
